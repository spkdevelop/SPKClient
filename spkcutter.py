# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2015 Daniel Fernández (daniel@spkautomatizacion.com), Saúl Pilatowsky (saul@spkautomatizacion.com) 
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

import common
import urllib2
import time
import threading
from spkserial import DeadSerialException,ThreadsafeSerial
import re
import json


persistent_vars = {}


PROBE_CODE2=[
        "G38.2F250Z-100", #hacemos un probe cycle, rapido (feed 250)
        "G28.3 Xprobe_x_pos Yprobe_y_pos Zprobe_z_pos", #marcamos la posicion actual como (X0,Yprobe_y_pos,Zprobe_z_pos)
        "G0 Ffeed_rapid_movement Zprobe_security_plane", #Subimos a plano de seguridad 
        "G0X0Y0"
        ]
HALF_FILE_CODE_FIRST=["G21",
                "G90",
                "G54",
                "M5",
                "G1 LAST_X LAST_Y LAST_F"]
                
HALF_FILE_CODE_SECOND=["M3",
                "LAST_F LAST_S",
                "LAST_G LAST_Z",
                ]
    
class JobStatus():
    _cutting_since=0
    _cutting_time=0
    fase=None
    line=None
    line_total=None
    ending=None
    can_stop=False
    stop_requested=False
    def as_dict(self):
        return {"fase": self.fase,
                "line": self.line,
                "line_total":self.line_total,
                "ending":self.ending,
                "can_stop":self.can_stop,
                "stop_requested":self.stop_requested
                }
    def set_fase(self,fase):
        #fases que reconoce el servidor: preparing,downloading,probe,homing,tool-change,cutting,paused
        if self.fase!=fase:
            if self.fase=="cutting":
                self._add_to_cutting_time()
            self.fase=fase
            if fase=="cutting":
                self._cutting_since=time.time()
            common.internet_thread.required_post=True
    def set_can_stop(self,can_stop):
        if self.can_stop!=can_stop:
            self.can_stop=can_stop
            common.internet_thread.required_post=True
        self.can_stop=can_stop
    def set_current_line(self,line):
        self.line=line
    def set_line_total(self,line_total):
        self.line_total=line_total
    def end_error(self,error={}):
        error["type"]="error"
        self.ending=error
    def end_success(self):
        self._add_to_cutting_time()
        self.ending={"type":"success","cut_time":round(self._cutting_time,2)}
    def end_requested(self):
        self.ending={"type":"stop"}
    def stop_please(self):
        if self.can_stop and not self.stop_requested:
            self.stop_requested=True
            common.internet_thread.required_post=True
    def _add_to_cutting_time(self):
        self._cutting_time+=(time.time()-self._cutting_since)
            
class Routine():
    def __init__(self,routine_type,arguments={}):
        self.status=JobStatus()
        self.routine_type=routine_type
        #self.gcode_url=gcode_url
        #self.start_line=start_line
        #self.speed=speed
        #self.config_vars=config_vars
        self.arguments=arguments
        self.parser=None
        set_variable("security_plane", 6)
    def run(self):
        self.status.set_can_stop(True)
        try:
            usb= ThreadsafeSerial.get()
            usb.flushInput()
            usb.flushOutput()
        except DeadSerialException:
            raise Exception("El puerto serial está desconectado")
        self.parser=common.get_parser()
        self.buffer_manager = BufferManager(self.parser)
        self.prepare_cnc()
        if self.routine_type=="cut":
            self.status.set_fase('downloading')
            g_code= urllib2.urlopen(self.arguments["gcode_url"]).read() #descargamos el código G
            lines=clean_lines(g_code.split("\n"))#lista de líneas de código
            self.exit_if_requested()
        
            with PeriodicQuestion(self.parser):
                speed=self.arguments["speed"]
                if speed!= 1:
                    lines=slow_down(lines, speed)
                start_line=self.arguments["start_line"]
                if start_line>len(lines):
                    raise Exception("La línea inicial es %d, pero el archivo sólo tiene %d líneas."%(start_line,len(lines)))
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
                    for h in [HALF_FILE_CODE_FIRST]:
                        header=h[:]
                        header=replace_variable(header,"LAST_X","X"+last_X if last_X else "")
                        header=replace_variable(header,"LAST_Y","Y"+last_Y if last_Y else "")
                        header=replace_variable(header,"LAST_Z","Z"+last_Z if last_Z else "")
                        header=replace_variable(header,"LAST_F","F"+last_F if last_F else "")
                        header=replace_variable(header,"LAST_S","S"+last_S if last_S else "")
                        header=replace_variable(header,"LAST_G",last_G if last_G else "")
                        header=replace_variable(header,"SEC_PLANE",str(get_variable("security_plane")))
                    self.send_gcode(clean_lines(header),"preparing")
            

                self.send_gcode(lines,"cutting",start_line=start_line)    

        elif self.routine_type=="home":

            self.home()
        elif self.routine_type=="probe":
            self.probe()

        
    def should_stop(self):
        return self.status.stop_requested and self.status.can_stop
    def exit_if_requested(self):
        if self.should_stop(): 
            s=ThreadsafeSerial.get()
            if self.parser == "tiny-g":
                s.write("!\n")
                s.write("%\n")
                s.write("M5\n")
            else:
                s.write("!\n")
                s.write("\x18\n")
                time.sleep(2)
                s.write("$x\n")
            s.flushInput()
            s.flushOutput()
            exit()  #salimos
        
    def prepare_cnc(self):
        self.status.set_fase("preparing")
        s=ThreadsafeSerial.get()
        if self.parser =="grbl":
            s.flushInput()
            s.write("\x18\n")
            time.sleep(5)
            s.write("$x\n")
            s.flushInput()
        elif self.parser=="tiny-g":
            config_lines=["$ej=1\n"]+\
                         [json.dumps({k:v})+"\n" for k,v in {"fd":0,"sv":2,"si":250,"tv":1,"jv":1,"qv":2,"js":1,"ex":2}.iteritems()]+\
                         [json.dumps({"sr":{"stat":True,"n":True,"qr":True,"qo":True,"qi":True}})+"\n"]
            for retry in range(2):
                s.write("%\n")
                time.sleep(0.2)
                s.flushInput()
                if self.send_lines_and_wait(config_lines,1):
                    break
                self.buffer_manager.reset()
            else: raise Exception("El %s no responde, reincialo y vuelve a intentar" % self.parser)

        s.flushInput() 
        s.flushOutput()
    def send_lines_and_wait(self,lines,timeout=None):
        #envia las lineas y espera a que se procesen. 
        #si se pasa timeout, devuleve True si se enviaron,
        #False si se paso el tiempo
        s=ThreadsafeSerial.get()
        start_time=time.time()
        for line in lines:
            while not self.buffer_manager.send_line(line):
                while s.inWaiting()!=0:
                    self.exit_if_requested()
                    self.buffer_manager.manage_report(s.readline(timeout=0.1))
                if timeout is not None and time.time()-start_time> timeout:
                    return False
        while not self.buffer_manager.buffer_is_empty():
            self.exit_if_requested()
            if timeout is not None and time.time()-start_time> timeout:
                return False
            self.buffer_manager.manage_report(s.readline(timeout=0.1))

        return True
    def home(self):
    
        s=ThreadsafeSerial.get()
        self.status.set_can_stop(True)
        config_vars=self.arguments["config_vars"]
        if self.parser=="tiny-g":
            #lines=["G28.3X0Y0Z40\n"]
            #lines=["G28.2X0Y0Z0\n","G28.3X0Y0Z20\n","G0Z6\n"]
            lines=["G28.2X0Y0Z0\n","G92X0Y0Z40\n","G0Z%s\n"%config_vars["probe_security_plane"]]
            self.send_lines_and_wait(lines)
        else:
            #lines=["$H\","G10L20P1X0Y0Z0\n"]

            s.write("$H\n")
            time.sleep(2)
            while True:
                intro = s.readline(timeout=1)

                self.exit_if_requested()
                if "ok" in intro:
                    break
            
#             idle_count = 0
#             while idle_count < 5:
#                 intro = s.readline(timeout=1)
#                 print intro
#                 if "Idle" in intro:
#                     idle_count += 1
            s.write("G10L20P1X0Y0Z40\n")
            s.readline()
        
        
    
    def probe(self):
        
        config_vars=self.arguments["config_vars"]
        self.status.set_can_stop(True)
        s=ThreadsafeSerial.get()
        if self.parser =="tiny-g":
            lines=["G0X%sY%s\n"%(config_vars["probe_x_pos"],config_vars["probe_y_pos"]),"G38.2F250Z-200\n","G92Z%s\n" % config_vars["probe_z_pos"],"G0Z%s\n"%config_vars["probe_security_plane"]]
            
        else:
            lines=["G0X%sY%s\n"%(config_vars["probe_x_pos"],config_vars["probe_y_pos"]),"G38.2F250Z-200\n","G10L20P1Z0\n","G0Z%s\n"%config_vars["probe_security_plane"]]
        self.send_lines_and_wait(lines)
        
    
    def send_gcode(self,lines,fase=False,start_line=0):
        

        usb = ThreadsafeSerial.get()
        if fase == "cutting":
            lines = ["N%s%s\n" % (i,lines[i]) if not "N" in lines[i] else lines[i] for i in range(len(lines))]

        current_line = 0
        total_lines = len(lines)       
        last_report_time=time.time()

        self.status.set_fase(fase)
        self.status.set_can_stop(False)
        self.status.set_line_total(total_lines+start_line)
        state=None
        #if self.parser == "tiny-g":
        #    time.sleep(1)
        #    self.buffer_manager.send_line(json.dumps({"sr":None}) + "\n")

        
        
        while True:
            while current_line < total_lines and self.buffer_manager.send_line(lines[current_line]):
                
                current_line+=1
            self.exit_if_requested()

            if usb.inWaiting()==0: 
                if state != "pause" and time.time()-last_report_time>5:
                    raise Exception("El %s no responde, reincialo y vuelve a intentar" % self.parser)
                continue #para que se actualice el controlFlow del tiny lo antes posible
            last_report_time=time.time()
            
            rline = usb.readline(timeout=1)
            
            if rline:
                new_sate=self.parse_state(rline)
                state=new_sate if new_sate is not None else state      
            if fase == "cutting":
                current_aprox=current_line+start_line-self.buffer_manager.lines_in_buffer
                if current_aprox>self.status.line:
                    self.status.set_current_line(current_aprox)
            
            if fase == "homing" or fase == "probing":
                time.sleep(.5)
                
            

            if state=="pause":
                self.status.set_fase("paused")
                self.status.set_can_stop(True)#podemos detenernos
            elif state=="run":
                self.status.set_fase(fase)
                self.status.set_can_stop(False)
            elif state=="error":
                raise(Exception("Hubo un problema, la ultima linea enviada fue la %s"%current_line))
            

            if current_line >= total_lines and (self.buffer_manager.buffer_is_empty() or state == "idle" or state == "cycling") and state != "homing" and state != "probing":
                break 
        
    def parse_state(self,rline):
        state=None
        if self.parser == "tiny-g":        
            if "Limit switch hit" in rline:
                state = "error"
            try:
                rline = json.loads(rline)
                if "er" in rline:
                    if rline["er"].get("st",0) not in [0,9]:
                        self.state = "error"
                        
                self.buffer_manager.manage_report(rline)
                status_report= rline.get("r",rline).get("sr",rline)
                if "stat" in status_report:
                    _state_int=status_report["stat"]
                    state=["run","run","error","cycling","run","run","pause","probing","run","homing"][_state_int]
            except:
                pass
    
        else:
    
            
            if "error:Alarm lock" in rline:
                state = "error"
            
            if "<" in rline: #es un status 
                new_state =self.line.strip("<").strip(">").split(",")[0]
                if new_state == "Run": state = "run"
                if new_state == "Hold": state = "pause"
                if new_state == "Queue": state = "pause"
                if new_state == "Idle": state = "idle"
                if new_state == "Alarm": state = "error"
    
            self.buffer_manager.manage_report(rline)
        return state
class BufferManager():
    GRBL_BUFFER_SIZE=127
    TINYG_QUEUE_BUFFER_SIZE=32
    TINYG_QUEUE_BUFFER_MIN=4
    
    TINYG_SERIAL_BUFFER_SIZE=254
    TINYG_SERIAL_BUFFER_MIN=10

    def __init__(self,parser):
        self.parser=parser
        self.grbl_sentchars=[]
        
        self.tiny_g_available_queue_buffer=BufferManager.TINYG_QUEUE_BUFFER_SIZE
        self.tiny_g_serial_buffer_available=BufferManager.TINYG_SERIAL_BUFFER_SIZE
        self.tiny_g_unresponded_lines=0
    def reset(self):
        self.__init__(self.parser)
    def manage_report(self,report):
        if report is None:
            return False
        #devuelve True si se uso el reporte, False si no.
        if self.parser=="grbl":
            if "ok" in report:
                self.grbl_sentchars.pop()
                return True
        elif self.parser=="tiny-g":

            try:
                if isinstance(report,basestring):
                    report=json.loads(report)

                status_report=report.get("r",report).get("sr",report)
                if "qr" in status_report:
                    self.tiny_g_available_queue_buffer=status_report["qr"]
                
                if "f" in report:
                    self.tiny_g_serial_buffer_available+=report["f"][2]
                    if self.tiny_g_serial_buffer_available>BufferManager.TINYG_SERIAL_BUFFER_SIZE:
                        self.tiny_g_serial_buffer_available=BufferManager.TINYG_SERIAL_BUFFER_SIZE
                    self.tiny_g_unresponded_lines-=1
                    if self.tiny_g_unresponded_lines<0:self.tiny_g_unresponded_lines=0
                if "rx" in report:
                        self.tiny_g_serial_buffer_available=report.get("rx")
                return True
            except: pass
        return False
    def send_line(self,line):
        #devuelve True si se envio la linea, False si el buffer no lo permitio
        if not line.endswith("\n"): line=line+"\n"

        if self.parser=="grbl":
            if sum(self.grbl_sentchars)+len(line) >=BufferManager.GRBL_BUFFER_SIZE:
                return False
            else:
                grbl_sentchars.append(len(line))
        elif self.parser=="tiny-g":
            linelen=line.replace("!","").replace("~","").replace("%","").strip() #el tiny-g no mete estos comandos al serial
            if (linelen #si la linea que va al serial tiene longitud y
                and (self.tiny_g_available_queue_buffer-self.tiny_g_unresponded_lines<=BufferManager.TINYG_QUEUE_BUFFER_MIN 
                or not ThreadsafeSerial.get().cts
                or len(line)+BufferManager.TINYG_SERIAL_BUFFER_MIN>self.tiny_g_serial_buffer_available)):
                
                return False #no podemos meterla
            
            if linelen: #si la linea sin esos caracteres tiene longitud
                self.tiny_g_serial_buffer_available-=len(line)
                self.tiny_g_unresponded_lines+=1
        ThreadsafeSerial.get().write(line)
        return True
    def buffer_is_empty(self):
        if self.parser=="grbl":
            return len(self.grbl_sentchars)==0
        elif self.parser=="tiny-g":
            return (self.tiny_g_available_queue_buffer==BufferManager.TINYG_QUEUE_BUFFER_SIZE and 
                    (self.tiny_g_serial_buffer_available>=240 or self.tiny_g_unresponded_lines==0)) #240 por si se nos dasfaza
    
    @property
    def lines_in_buffer(self): #es un aproximado!
        if self.parser=="grbl":
            return len(self.grbl_sentchars)
        elif self.parser=="tiny-g":
            return  (BufferManager.TINYG_QUEUE_BUFFER_SIZE-self.tiny_g_available_queue_buffer+self.tiny_g_unresponded_lines)

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
def set_variable(variable,value):
    global persistent_vars
    persistent_vars[variable]=value
def get_variable(variable):
    return persistent_vars[variable] if variable in persistent_vars else None
    #print "---------------GCODE-Fin---------------"
class PeriodicQuestion:
    periodic_continue=True
    def __init__(self,parser):
        if parser=="tiny-g": 
            self.question=json.dumps({"sr":None})#{"qr":True,"stat":True}})
            self.periodic_continue=False #usamos el interval del tiny-g
        elif parser=="grbl":
            self.question="?"
        else:
            raise(Exception("Parser desconocido"))
    def __enter__(self):
        self.periodic()
    def __exit__(self, type, value, traceback):
        self.periodic_continue=False
    def periodic(self): #esta función le pregunta el estado cada 300ms al GRBL, solita se reinicia
        if not self.periodic_continue: return
        try:
            ThreadsafeSerial.get().write(self.question)
            #ThreadsafeSerial.get().readline(timeout=.1)
        except DeadSerialException: pass
        t = threading.Timer(.3, self.periodic) #creamos un timer para dentro de 300ms
        t.daemon=True
        t.start()
