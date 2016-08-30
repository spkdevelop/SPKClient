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
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from SocketServer import ThreadingMixIn

import cgi
import json
import spkwifi
import threading
import collections
import time
from spkserial import ThreadsafeSerial,DeadSerialException
import common


PORT_NUMBER = 80
ALLOWED_CONFIG_ORIGINS=[common.URL,common.URL.replace("https", "http"),"http://www.spkautomatizacion.com"]

local_connection_token=""
class ConsoleManager():
    lock= threading.RLock()
    dictlock= threading.RLock()
    lines=collections.OrderedDict()
    lineid=0
    def _get_prev_lines(self,lastlineid=None):
        if lastlineid!=None:
            with self.dictlock:
                keys=self.lines.keys()
                if lastlineid in keys:
                    i=keys.index(lastlineid)
                    if i<len(keys)-1:
                        return keys[-1],[self.lines[keys[i+j]] for j in range(1,len(keys)-i)]
        return None
    def readlines(self,lastlineid=None):
        s=ThreadsafeSerial.get()
        prevs=self._get_prev_lines(lastlineid)
        if prevs is not None: return prevs #checamos si no hay lineas guardadas
        with self.lock:#esperamos al lock de lectura
            prevs=self._get_prev_lines(lastlineid) #volvemos a checar si no se guardaron lineas miesntras esperabamos el lock
            if prevs is not None: return prevs
            newlines=[]
            time_reading=time.time()
            while True:
                if common.internet_thread.routine is not None: break
                l =s.readline(timeout=1)
                if l.endswith("\n"):
                    newlines.append(l[0:-1]) #leemos mas
                else:
                    break
                if s.inWaiting()==0 or time.time()-time_reading>1:
                    break
            if len(newlines):
                with self.dictlock:
                    for newline in newlines:
                        if len(self.lines)>100:
                            self.lines.popitem(False)
                        self.lineid+=1
                        self.lines[self.lineid]=newline
                    return self.lineid,newlines
            else:
                return lastlineid,None
    def writeline(self,data):
        if data == "reset":
            ThreadsafeSerial.get().write("\x18\n")
        else:
            ThreadsafeSerial.get().write(data+"\n")

class ServerHandler(BaseHTTPRequestHandler):
    console_manager=ConsoleManager()
    def log_message(self, f, *args):
        #BaseHTTPRequestHandler.log_message(self, f, *args)
        pass
#    def do_GET(self):
#         if self.path=="/":
#             self.path="/index.html"
# 
#         try:
#             #Check the file extension required and
#             #set the right mime type
# 
#             sendReply = False
#             if self.path.endswith(".html"):
#                 mimetype='text/html'
#                 sendReply = True
#             if self.path.endswith(".jpg"):
#                 mimetype='image/jpg'
#                 sendReply = True
#             if self.path.endswith(".gif"):
#                 mimetype='image/gif'
#                 sendReply = True
#             if self.path.endswith(".js"):
#                 mimetype='application/javascript'
#                 sendReply = True
#             if self.path.endswith(".css"):
#                 mimetype='text/css'
#                 sendReply = True
# 
#             if sendReply == True:
#                 #Open the static file requested and send it
#                 f = open(curdir + sep + self.path) 
#                 index_file = f.read() % ("Ethernet IP: %s \n WiFi IP: %s" % spkwifi.get_ip_adresses())
#                 f.close()
#                 
#                 self.send_response(200)
#                 self.send_header('Content-type',mimetype)
#                 self.end_headers()
#                 self.wfile.write(index_file)
#             
#                 
#             return
# 
#         except IOError:
#             self.send_error(404,'File Not Found: %s' % self.path)
# 
    def do_POST(self):
#         if self.path=="/send_web":
#            
#             form = cgi.FieldStorage(
#                 fp=self.rfile, 
#                 headers=self.headers,
#                 environ={'REQUEST_METHOD':'POST',
#                          'CONTENT_TYPE':self.headers['Content-Type'],
#             })
#             self.send_response(200)
#             self.end_headers()
#             textout = ["Nombre red: %s",
#                     "Pswd: %s\n",
#                     "Tu raspberry se esta conectando...",
#                     "Si cometiste algun error, conectate al cable de Ethernet recarga la pagina y repite los pasos.",
#                     ]
#             
#             self.wfile.write("SPKClient:. \n\n" + "\n".join(textout) % (form["ssid"].value,form["psk"].value))
#         
#             if not spkwifi.set_wifi_network(form["ssid"].value.strip(), form["psk"].value.strip()):
#                 self.wfile.write("Algo salio mal...")
#             
#                 
#             return        
#         if self.path=="/send_cncid":
#                 form = cgi.FieldStorage(
#                     fp=self.rfile, 
#                     headers=self.headers,
#                     environ={'REQUEST_METHOD':'POST',
#                              'CONTENT_TYPE':self.headers['Content-Type'],
#                 })
#                 
#                 cncid=  form["cncid"].value
#                 
#                 try:
#                     if cncid.startswith("sudo"):
#                         cncid = cncid.split("\"")[1]
#                     
#                     f = open(main.NEWCNCIDFILENAME,"w")
#                     f.write(cncid)
#                     f.close
#                     
#                     self.send_response(200)
#                     self.end_headers()
#                     
#                     textout = ["ID: %s\n",
#                     "Recarga la pagina en unos momentos.",
#                     "Tu raspberry se esta reiniciando...",
#                     "Revisa tu nueva maquina en el taller correspondiente."
#                     ]
#                     self.wfile.write("SPKClient:. \n\n" + "\n".join(textout) % (cncid))
#                     
#                     common.restart_please()
#                     #system("reboot")
#                     #execl(sys.executable, *([sys.executable]+sys.argv))
#                     
#                 except:
#                     self.send_response(200)
#                     self.end_headers()
#                     self.wfile.write("Error, revisa el contenido de tu id")
#                 
#                     
#                 return
#         if self.path=="/reset_client":
#                 form = cgi.FieldStorage(
#                     fp=self.rfile, 
#                     headers=self.headers,
#                     environ={'REQUEST_METHOD':'POST',
#                              'CONTENT_TYPE':self.headers['Content-Type'],
#                 })
#                 
#                 
#                 self.send_response(200)
#                 self.end_headers()
#                 self.wfile.write("El script de spkclient se esta reiniciando, ve a la pagina principal y recargala.")
#                 common.restart_please()
#                 return
#         if self.path=="/reset_pi":
#                 form = cgi.FieldStorage(
#                     fp=self.rfile, 
#                     headers=self.headers,
#                     environ={'REQUEST_METHOD':'POST',
#                              'CONTENT_TYPE':self.headers['Content-Type'],
#                 })
#                 
#                 
#                 self.send_response(200)
#                 self.end_headers()
#                 self.wfile.write("La raspberrypi se reiniciara...")
#                 system("reboot")
#                 return
#             
        if self.path=="/spkwizardsetup":
            data = cgi.FieldStorage(
                    fp=self.rfile, 
                    headers=self.headers,
                    environ={'REQUEST_METHOD':'POST',
                             'CONTENT_TYPE':self.headers['Content-Type'],
                })
                
            action=  data.getfirst("action", None)
            origin= self.headers.get("Origin",None)
            if not origin in ALLOWED_CONFIG_ORIGINS:
                self.send_response(403)
                return
            self.send_response(200)
            self.send_header('Content-type',"application/json")
            self.send_header('Access-Control-Allow-Origin',origin)
            self.end_headers()
            
            if action=="marco":
                if common.get_id()!=None:
                    self.wfile.write(json.dumps({"status":"already_configured"}))
                else:
                    self.wfile.write(json.dumps({"status":"polo","current_network":spkwifi.get_current_connected_network()}))
                    
                    
            elif action=="get_network_status":
                self.wfile.write(json.dumps({"status":"success","available_networks":[n.ssid for n in spkwifi.get_available_networks()],"current_network":spkwifi.get_current_connected_network()}))
            elif action=="set_wifi_network":
                ssid=  data.getfirst("ssid", None)
                password=  data.getfirst("password", None)
                if spkwifi.set_wifi_network(ssid, password):
                    self.wfile.write(json.dumps({"status":"success","current_network":spkwifi.get_current_connected_network()}))
                else:
                    self.wfile.write(json.dumps({"status":"error","current_network":spkwifi.get_current_connected_network()}))
            elif action=="send_workshop":
                config_data=  json.loads(data.getfirst("config_data", "{}"))
                
                response=common.send_config_info(config_data)
                if "extra_info" in response:
                    self.wfile.write(json.dumps({"status":"success","extra_info":response["extra_info"]}))
                else:
                    self.wfile.write(json.dumps({"status":"error","reason":response.get("reason","")}))
            else:
                self.wfile.write(json.dumps({"status":"error"}))
        elif self.path=="/spkcnclocalcommandreceiver":
            data = cgi.FieldStorage(
                    fp=self.rfile, 
                    headers=self.headers,
                    environ={'REQUEST_METHOD':'POST',
                             'CONTENT_TYPE':self.headers['Content-Type'],
                })
            origin= self.headers.get("Origin",None)
            local_token=  data.getfirst("_local_token", None)
            prev_local_token=  data.getfirst("_prev_local_token", None)
            
            if not origin in ALLOWED_CONFIG_ORIGINS or local_token==None or (local_token!=local_connection_token!=prev_local_token):
                self.send_response(403)
                return
            self.send_response(200)
            self.send_header('Content-type',"application/json")
            self.send_header('Access-Control-Allow-Origin',origin)
            self.end_headers()
            message=  json.loads(data.getfirst("message", None))
            command=message.get("command",None)
            if command=="checking_same_network":
                self.wfile.write(json.dumps({"status":"sure :)"}))
            elif command=="lifeline":
                time.sleep(60)
                self.wfile.write(json.dumps({"status":"sure :)"}))
            elif command=="get_network_status":
                self.wfile.write(json.dumps({"status":"success","available_networks":[n.ssid for n in spkwifi.get_available_networks()],"current_network":spkwifi.get_current_connected_network()}))
            elif command=="get_current_network":
                self.wfile.write(json.dumps({"status":"success","current_network":spkwifi.get_current_connected_network()}))
            elif command=="set_wifi_network":
                ssid=  message.get("ssid", None)
                password=  message.get("password", None)
                if spkwifi.set_wifi_network(ssid, password):
                    self.wfile.write(json.dumps({"status":"success","current_network":spkwifi.get_current_connected_network()}))
                else:
                    self.wfile.write(json.dumps({"status":"error","current_network":spkwifi.get_current_connected_network()}))
            elif command=="get_script_status_change":

                while True:
                    if common.internet_thread.routine is None or common.internet_thread.routine.status.as_dict()!=message.get("last_status",None):
                        break
                    else:
                        time.sleep(.01)
                if common.internet_thread.routine is not None:
                    self.wfile.write(json.dumps({"status":common.internet_thread.routine.status.as_dict()}))
                else:
                    self.wfile.write(json.dumps({"status":common.internet_thread.last_job_status.as_dict() if common.internet_thread.last_job_status is not None else None}))
            
            elif command=="send_console_line":

                if common.internet_thread.routine is None:
                    try:
                        self.console_manager.writeline(message.get("line",""))
                    except:
                        pass
                self.wfile.write(json.dumps({}))
            elif command=="console_line_poll":
                    try:
                        lines=None
                        lastid=message.get("lastlineid",None)
                        counter=0
                        response={"status":"success"}
                        
                        while common.internet_thread.routine is None and lines is None and counter <3:
                            if message.get("i_think_there_is_no_serial",False):
                                response["parser"]=common.get_parser()
                                break  #para que se quite el mensaje de que no hay serial
                            lastid,lines=self.console_manager.readlines(lastid)
                            counter+=1

                        response["lines"]=lines
                        response["lastlineid"]=lastid
                        self.wfile.write(json.dumps(response))
                    except DeadSerialException:
                        self.wfile.write(json.dumps({"status":"error","reason":"no-serial"}))
                    except:

                        self.wfile.write(json.dumps({"status":"error"}))
            elif command =="jog_pressed_key":
                global current_jogging
                global jogging_cancel_timer
                try:
                    if common.internet_thread.routine is None:
                        key=message.get("key",None)
                        pressed=message.get("pressed",None)
                        possibles={38:"Y",40:"Y-",37:"X-",39:"X",33:"Z",34:"Z-"} #http://keycode.info/
                        usb=ThreadsafeSerial.get()
                        parser=common.get_parser()
                        if key in possibles and pressed is not None:
                            if jogging_cancel_timer is not None:
                                jogging_cancel_timer.cancel()
                            if not pressed or (current_jogging is not None and current_jogging!=key):
                                if parser=="tiny-g":
                                    usb.write("!%\n")
                                #grbl mandar (! y ctrl x? cuando se frene?)
                                current_jogging=None
                            else:
                                if message.get("new_pressed",False) and current_jogging is None:
                                    if parser=="tiny-g":
                                        usb.write("G91 G0 "+possibles[key]+"1000\nG90\n")
                                    
                                    #grbl mandar lo mismo?
                                    current_jogging=key
                                jogging_cancel_timer=threading.Timer(0.5,lambda: usb.write("!%\n" if parser=="tiny-g" else ""))
                                jogging_cancel_timer.start()
                                
                            usb.flushInput()
                except DeadSerialException:
                    pass
                self.wfile.write(json.dumps({}))     
                    
               
            else:
                common.internet_thread.manage_response(message)
                self.wfile.write(json.dumps({}))
  
                        
current_jogging=None
jogging_cancel_timer=None
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads=True
class ServerThread (threading.Thread):
    
    def __init__(self):
        threading.Thread.__init__(self)
        self.port = PORT_NUMBER
        self.server = ThreadedHTTPServer(('', PORT_NUMBER), ServerHandler)
    def run(self):    
            
        try:
            self.server.serve_forever()
        finally:
            try:
                self.server.socket.close()
            except:
                pass
