# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2015 Daniel Fernandez (daniel@spkautomatizacion.com), Saul Pilatowsky (saul@spkautomatizacion.com) 
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Find us at: http://www.spkautomatizacion.com


import urllib2
import time
import serial
import threading
import re

PROBE_CODE=[
        "G90",
        "G0Ffeed_rapid_movement ZSEC_PLANE",
        "G0Ffeed_rapid_movement Xprobe_x_pos Yprobe_y_pos",#avanzamos al sensor de probe con incremental
        "G91G38.2F250Z-150", #hacemos un probe cycle, rapido (feed 500)
        "G91G0F500Z2",#subimos un poco (2mm) para ahora hacer uno lento
        "G91G38.2F50Z-10", #hacemos un probe muy lento (feed 50)
        "G10L20P1 Xprobe_x_pos Yprobe_y_pos Zprobe_z_pos", #marcamos la posicion actual como (X0,Yprobe_y_pos,Zprobe_z_pos)
        "G90G0 Ffeed_rapid_movement Zprobe_security_plane", #Subimos a plano de seguridad 
        "G0X0Y0"
        ]
TOOL_CHANGE_CODE=[
        "G90",
        "G0ZSEC_PLANE",
        "G0 Ffeed_rapid_movement Xtool_change_x_pos Ytool_change_y_pos",
        "M0",
        "G0 Ffeed_rapid_movement tool_change_x_pos Ytool_change_y_pos",
        ]
HALF_FILE_CODE_FIRST=["G21",
                "G90",
                "G54",
                "G0 ZSEC_PLANE",
                "G0 LAST_X LAST_Y",
                "M0",
                "G0 LAST_X LAST_Y"]
                
HALF_FILE_CODE_SECOND=["M3",
                "LAST_F LAST_S",
                "LAST_G LAST_Z",
                ]

def exit_if_requested(s=None):#esta función checa si tenemos que salir porque el usuario lo pidió y sale si sí...
    if get_requested_exit(): #dada por el script del yun, nos avisa si el servidor pide salir 
        if s: #si hay saerial
            s.write("\x18") #mandamos un reset al GRBL
        exit()  #salimos
        
def replace_variable(lines,string,variable):
    for i in range(len(lines)):
        while string in lines[i]:
            
            lines[i]=lines[i].replace(string,str(variable))
    return lines
def clean_line(line):
    return re.sub('\s|\(.*?\)','',line).upper() #magicamente esto quita comentarios, espacios y pone mayusculas
def clean_lines(lines):
    l= [clean_line(line) for line in lines] #hacemos una lista de lineas limpias
    while "" in l: l.remove("") #quitamos lineas vacias
    return l
def extract_float(lines,string):
    number=None
    for line in lines:
        if string in line:
            start =line.index(string)+len(string)
            found_number=False
            number=None
            for end in range(start,len(line)):
                substring=line[start:end+1]
                try:
                    float(substring)
                except ValueError:
                    if found_number:break
                else:
                    number=substring
                    found_number=True
            if number:break
    return number 
def extract_first_match(lines,strings):
    for line in lines:
        for string in strings:
            if string in line: return string   
def slow_down(lines,percentage):
    for i in range(len(lines)):
        if "F" in lines[i]:
            f=extract_float([lines[i]], "F")  
            if f:
                lines[i]=lines[i].replace("F"+f,"F"+str(float(f)*percentage))
    return lines
def send_gcode(lines,auto_run=False,report_status=True,no_pause=False,line_offset=0):
    RX_BUFFER_SIZE = 128 #tamaño del búfer
    g_count = 0 #contador que medirá las líneas ejecutadas
    c_line = [] #aquí vamos a contar el número de caracteres en el búfer
    total_lines=len(lines) #contamos las lineas
    state=None
    s = get_serial()
    while g_count<(total_lines-1) or state!="Idle": #loop principal
        l_block=None #la línea actual
        if len(lines)>0: #todavia no enviamos todas las líneas
            line=lines.pop(0) #sacamos la primera línea
            l_block = line.strip()
            c_line.append(len(l_block)+1) # Track number of characters in grbl serial read buffer
        while sum(c_line) >= RX_BUFFER_SIZE-1 or s.inWaiting(): #si exedemos el tamaño del búfer o GRBL nos quiere decir algo
            exit_if_requested(s) #salimos si nos lo pidieron (NOTA: si no podemos salir, esta función no lo hará nunca, ver ayuda
            out_temp = s.readline().strip() # Esperamos que nos diga algo
            if out_temp.find('ok') < 0 and out_temp.find('error') < 0 : #no es ok ni error
                
                if "ALARM:" in out_temp: #LÍMITE ACTIVADO, salimos y con error
                    s.write("\x18") #reseteamos
                    raise(Exception("Se activó un sensor de límite inesperadamente")) #sacamos un error
                if "<" in out_temp: #es un status 
                    new_state=out_temp.strip("<").strip(">").split(",")[0] #lo leemos
                    if state!=new_state: #es diferente al que teníamos
                        if new_state=="Idle": 
                            if state==None:
                                new_state=None #no hemos iniciado, no permitimos el estado Idle
                            elif total_lines-g_count<=1: 
                                pass #terminamos, el loop sale solo
                            else:
                                new_state="Alarm" #salimos, hubo un reset y fingimos que es una alarma para que se active el siguiente if
                        if new_state=="Alarm": #hubo un soft reset, ya sea en pleno movimiento o tras detenerse
                            s.write("\x18") #reseteamos
                            raise(Exception("La máquina se reinició inesperadamente")) #sacamos un error
                        
                        if new_state=="Queue": #estamos en feed hold
                            if auto_run or no_pause:
                                s.write("~")
                                auto_run=False
                            else:
                                if state=="Idle" or state==None:#primera vez
                                    set_status("Código cargado, presione el botón verde para iniciar")
                                else:#fue una pausa
                                    set_status("En pausa, presione el botón verde para continuar")
                                set_can_stop(True)#podemos detenernos
                        if new_state=="Hold": #deteniendo para entrar en hold
                            set_can_stop(False)#no podemos detenernos
                            
                        if new_state=="Run": #corriendo normalmente
                            auto_run=False
                            if report_status:
                                report_line(g_count,total_lines,line_offset)
                            
                            set_can_stop(False)#no podemos detenernos
                    state=new_state #actualizamos el estado
            else: #es un ok o error
                g_count += 1 # sumamos para llevar cuenta del número de líneas
                del c_line[0] # Delete the block character count corresponding to the last 'ok'
        if state=="Run" and report_status: report_line(g_count,total_lines,line_offset) #actualizamos el status
        if l_block: #si todavía hay líneas
            print l_block
            s.write(l_block + '\n') # Send g-code block to grbl
            l_block=None
def report_line(line_number,line_total,line_offset):
    set_status("Cortando ("+ str(max(1,line_number+line_offset))+"/"+str(line_total+line_offset)+" líneas)","line",max(1,line_number+line_offset))
class periodic_question:
    periodic_continue=True
    def __enter__(self):
        self.periodic_continue=True
        self.periodic()
    def __exit__(self, type, value, traceback):
        self.periodic_continue=False
    def periodic(self): #esta función le pregunta el estado cada 300ms al GRBL, solita se reinicia
        try:
            if not self.periodic_continue: return
            s = get_serial()
            s.write('?')#preguntamos
            t = threading.Timer(0.3, self.periodic) #creamos un timer para dentro de 300ms
            t.daemon=True
            t.start()
        except:
            pass
def prepare_cnc():
    s = get_serial()
    set_status('Preparando CNC')
    s.flushInput()
    s.flushOutput()
    s.write("\x18") #iniciamos GRBL
    time.sleep(2)  #esperamos a que inicie
    s.flushInput() #eliminamos el texto de entrada
    s.flushOutput() #limpiamos el serial
def home():
    s=get_serial() 
    set_status("Midiendo ejes","homing")
    s.flushInput()
    s.write("$H\n")
    
    while True: #esperamos a que nos diga ok
        st=s.readline().strip() #esperamos respuesta
        if "<" in st: #es un reporte de estado
            state=st.strip().strip("<").strip(">").split(",")[0]
        else:
            break #es un ok
    s.write("G10L20P1X0Y0Z0\n")
    while True: #esperamos a que nos diga ok
        st=s.readline().strip() #esperamos respuesta
        if "<" in st: #es un reporte de estado
            state=st.strip().strip("<").strip(">").split(",")[0]
        else:
            break #es un ok
    set_variable("security_plane",0)
def run(gcode_url,homing,tool_change,probe,start_line,speed,config_vars):
    state=None
    
    set_status('Descargando código "G"',"")
    set_can_stop(True) #podemos detenernos, la descarga no es nada serio (ver ayuda)
    g_code= urllib2.urlopen(gcode_url).read() #descargamos el código G
    exit_if_requested() #buen momento para salir si nos lo piden
    s = get_serial() #puerto del grbl, nos lo da el yun, no hay que cerrarlo ni abrirlo
    lines=clean_lines(g_code.split("\n"))#lista de líneas de código G
    
    prepare_cnc()
    exit_if_requested(s) #otro buen momento para salir
    

    with periodic_question(): # iniciamos la pregunta de status periódica
        while state==None:#esperamos el estado
            st=s.readline() #esperamos una respuesta a la pregunta periodica
            if "<" in st: #significa que es reporte de estado 
                state=st.strip().strip("<").strip(">").split(",")[0]#obtenemos el estado
        if state=="Alarm" or get_variable("security_plane")==None or homing: #no hay posición 
            home()
            
                
        if tool_change:
            tool_change_code=TOOL_CHANGE_CODE[:]
            for name in config_vars:tool_change_code=replace_variable(tool_change_code,name,config_vars[name])
            set_status("Cambiando herramienta","tool-change")
            send_gcode(clean_lines(replace_variable(tool_change_code,"SEC_PLANE",str(get_variable("security_plane")))), True,False)
            home()
        if probe:
            probe_code=PROBE_CODE[:]
            for name in config_vars:probe_code=replace_variable(probe_code,name,config_vars[name])
            set_status("Midiendo herramienta","probe")  
            send_gcode(clean_lines(replace_variable(probe_code,"SEC_PLANE",str(get_variable("security_plane")))), True,False,no_pause=True)
            set_variable("security_plane",config_vars["probe_security_plane"])
        if speed!= 1:
            lines=slow_down(lines, speed)
        if start_line>0:
            previous_lines=lines[:start_line+1] #es mas uno para incluir la actual en las busqedas
            lines=lines[start_line:]
            
            previous_lines.reverse()
            last_G=extract_first_match(previous_lines,["G0","G1","G00","G01"])
            last_X=extract_float(previous_lines, "X")
            last_Y=extract_float(previous_lines, "Y")
            last_Z=extract_float(previous_lines, "Z")
            last_F=extract_float(previous_lines, "F")
            last_S=extract_float(previous_lines, "S")
            for h in [HALF_FILE_CODE_FIRST,HALF_FILE_CODE_SECOND]:
                header=h[:]
                header=replace_variable(header,"LAST_X","X"+last_X if last_X else "")
                header=replace_variable(header,"LAST_Y","Y"+last_Y if last_Y else "")
                header=replace_variable(header,"LAST_Z","Z"+last_Z if last_Z else "")
                header=replace_variable(header,"LAST_F","F"+last_F if last_F else "")
                header=replace_variable(header,"LAST_S","S"+last_S if last_S else "")
                header=replace_variable(header,"LAST_G",last_G if last_G else "")
                header=replace_variable(header,"SEC_PLANE",str(get_variable("security_plane")))
                send_gcode(clean_lines(header),report_status=False)
    
        else:
            send_gcode(["M0","G0X0Y0"],report_status=False)
    
        set_status("Preparando Corte","")
        
        send_gcode(lines,line_offset=start_line)    
    #BYE, todo chido
