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
import threading
import time
import json
import shutil
import traceback
import base64
import urllib2
from cStringIO import StringIO
import spynner
import sys
import zipfile
import spkwifi
import spkserver
import common
from spkserial import ThreadsafeSerial, DeadSerialException
import os.path
import spkcutter
VERSIONFILE="client_version"

class RoutineThread(threading.Thread):

    def __init__(self,routine_type,job_id=None,arguments={}):
        threading.Thread.__init__(self)
        self.kill=False
        self.type=routine_type
        self.job_id=job_id
        self.daemon=False
        self.job=spkcutter.Routine(routine_type,arguments)
        self.status=self.job.status
        
    def run(self):

        try:
            self.job.run()
        except (SystemExit,KeyboardInterrupt,GeneratorExit):
            self.status.end_requested()
        except Exception,info:
            
            exc_type, exc_value, exc_traceback = sys.exc_info()
            trace=str.decode(traceback.format_exc(),"utf-8")
            fullerror=unicode.join(u"\n",trace.splitlines()[3:])
            try:
                line=info[1][1] #la vida...
            except:
                line=traceback.extract_tb(exc_traceback)[-1][1]#...es complicada  
            #y obtener la linea correcta... tambien              
            self.status.end_error({"line":line,"fullInfo":fullerror,"exception":str(exc_value)})   
            common.internet_thread.show_message("error","Hubo un error:",str(exc_value))
        else:
            self.status.end_success()
            if self.type=="cut":
                common.internet_thread.show_message("success","Corte finalizado","El tiempo de corte fue de "+str(self.status.ending["cut_time"])+" segundos.")
            elif self.type=="home":
                common.internet_thread.show_message("success","Ejes medidos","El cero está en la posición actual.")
            elif self.type=="probe":
                common.internet_thread.show_message("success","Herramienta medida","Cero del eje Z ajustado")
        finally:
            common.internet_thread.last_job_status=self.status
            common.internet_thread.routine=None  
            
            common.internet_thread.required_post=True

                          

class ChannelApiThread(threading.Thread):
    
    def __init__(self,message_callback):
        threading.Thread.__init__(self)
        self.connected=False
        self.connecting=False
        
        self.kill=False
        self.token=None
        self.bad_token=None
        self.message_callback=message_callback
        self._browser=None
    def _message_listener(self,a,message,b):
        message=json.loads(message)
        if message["state"]=="open":

            self.connected=True
            self.connecting=False
        elif message["state"]=="message":

            self.connected=True
            self.connecting=False
            self.message_callback(base64.b64decode(message["data"]))
        elif message["state"]=="error":
            
            error_code=message["error"]["code"]
            self.connected=False
            self.connecting=False
            print "channel_error",message
            if str(error_code).strip()=="401":
                self.bad_token=self.token
                self.token=None
        elif message["state"]=="close":
            self.connected=False
            self.retry()
            

        
    def run(self):
        url=os.path.join(common.URL,"_cnc/channelclient")

        browser=spynner.Browser()
        browser.create_webview(True)
        browser.load(url,load_timeout=30,tries=True)
        browser.set_javascript_prompt_callback(self._message_listener)
        while self.kill==False:
            if self.token and not self.connected and self.connecting:
                browser.runjs("openChannel('"+self.token+"')")
                self.connected=True
                self.connecting=False
            if self.token==None and self.connected:
                browser.runjs("closeSocket()")
            browser.wait(1)

        browser.close()
    def connect(self,token):

        self.token=token
        self.bad_token=None
        self.retry()
    def retry(self):
        if not self.connected and self.token:        
            self.connecting=True
    def disconnect(self):
        self.token=None
        


class InternetThread (threading.Thread):
    
    def __init__(self):
        threading.Thread.__init__(self)
        self.kill=False
        self.ui = None
        self.last_job_status=None
        self.channel_api_token=None
        self.channel_thread=None
        self.required_post=True
        self.routine=None
        self.message=None
    def channel_api_message(self,message):
        self.manage_response(json.loads(message))
    def run(self):
        self.check_version()
        self.channel_thread=ChannelApiThread(self.channel_api_message)
        self.channel_thread.start()
        print u"Cliente conectado con servidor"
        while not self.kill:
            
            self.required_post=False

            response=self.send_prescence()
            self.manage_response(response)
            time.sleep(1)
             
            for _ in range(200): 
                if common.get_id() is not None or self.kill: break
                time.sleep(5) #cuando no hay id, esperamos 5 segundos y solo mandamos el ip paque nos configuren
            while self.kill==False and self.required_post==False and (self.channel_thread.connected==True or self.channel_thread.connecting==True):
                time.sleep(0.1)
                pass
            if self.required_post==True:
                time.sleep(0.1) #para que si se marco el required post antes de que acabara de hacer cosas otro thread, las acabe

    def send_prescence(self):
        data={"id":common.get_id(),"local_ip":spkwifi.get_ip_adress()}
        if common.get_id() is not None:
            if self.channel_thread.token==None:
                if self.channel_thread.bad_token!=None:
                    data["bad_token"]=self.channel_thread.bad_token
                data["get_token"]=True
                
            if self.routine!=None:
                data["routine"]=self.routine.type
                
                data["current_cut_job"]=self.routine.job_id
                data["can_stop"]=self.routine.status.can_stop
                data["stop_requested"]=self.routine.status.stop_requested
                data["cut_fase"]=self.routine.status.fase
            if self.last_job_status is not None:
                data["last_job_status"]=self.last_job_status.as_dict()
                                         
                self.last_job_status=None
            if self.message is not None:
                data["popup_message"]=self.message
                self.message=None
        try:
            #print data
            response_object=common.send_data(data)
            #print data
            #print response_object
        except Exception as error:
            print error
            response_object={}
            time.sleep(1) #durmamos 10 segundos, hubo un error con el servidor
        return response_object

   
    def manage_response(self,data):
        if "local_connection_token" in data:
            spkserver.local_connection_token=data["local_connection_token"]
        if "channel_api_token" in data:
            self.channel_thread.connect(data["channel_api_token"])   
        if "command" in data:

            if data["command"]=="re_configure":
                    common.set_id(None)
                    self.channel_thread.disconnect()
                    #common.restart_please() segun yo no es necesario
            if data["command"]=="invalidate_config_info":
                    print u"Parece que hay un problema con la configuración, el servidor contestó: %s"%data["reason"]
            if data["command"]=="update_id":
                if "new_id" in data:
                    common.set_id(data["new_id"])
            elif data["command"]=="pause" or data["command"]=="unpause":
                if self.routine!=None:
                    self.routine.job.buffer_manager.send_line("!" if data["command"]=="pause" else "~")
            elif data["command"]=="send_gcode":
                if self.routine is None:
                    try:
                        code=data.get("code",None)
                        if code is None:
                            parser=common.get_parser()
                            code=data.get(parser,None)
                        if code is not None:
                            
                            code=code.strip()+"\n"
                            
                            ThreadsafeSerial.get().write(code)
                            if "success_message" in data:
                                message= data["success_message"]
                                try:
                                    self.show_message("success",message.get("title",""),message.get("description",""),message.get("timeout",5000))
                                except:
                                    pass
                    except DeadSerialException:
                        self.show_message("error","El puerto serial está desconectado")
            elif data["command"]=="stop_job":
                if self.routine!=None:
                    self.routine.status.stop_please()
            elif data["command"]=="run_queue":
                if "job_data" in data:
                    self.start_routine("cut",job_id=data["job_data"]["job_id"],arguments=data["job_data"]["arguments"])
            elif data["command"]=="do_homing":
                self.start_routine("home",arguments=data.get("arguments",None))
            elif data["command"]=="do_probing":
                self.start_routine("probe",arguments=data.get("arguments",None))
                     
    def start_routine(self,routine_type,job_id=None,arguments={}):
        if self.routine is not None: return
        self.routine=RoutineThread(routine_type,job_id=job_id,arguments=arguments)
        self.required_post=True
        self.last_run_ending=None
        self.routine.start()
    def show_message(self,type,title,description="",timeonscreen=10000):
        #type es error,warning,info, o success
        self.message=[type,title,description,timeonscreen]
        self.required_post=True
    def check_version(self):
        with open(os.path.join(common.get_current_path(),VERSIONFILE), 'r') as f:
            version=f.read().strip()
        print u"Verificando actualizaciones"
        data={"checking_version":True,"version":version}
        try:
            response= common.send_data(data)
        except:
            return 
        if response.get("command",None)=="update":
            print u"Nueva version disponible (Actual: %s,Nueva: %s)"%(version,response["new_version"])
            file_url=common.URL+response["file_url"]
            response = urllib2.urlopen(file_url)
            _file = StringIO(response.read())
            if zipfile.is_zipfile(_file):
                
                
                zfl=zipfile.ZipFile(_file)
                members=zfl.namelist()[:]
                root_path=None
                for n in members[:]:
                    if os.path.basename(n)=="cncid":
                        members.remove(n)
                    elif os.path.basename(n)=="main.py":
                        if not root_path:
                            root_path=os.path.dirname(n)
                if root_path is not None:
                    for n in members[:]:
                        if not n.startswith(root_path):
                            members.remove(n)
                for m in members:       
                    source = zfl.open(m)
                    file_target=os.path.join(common.get_current_path(),os.path.relpath(m, root_path))
                    if os.path.basename(m)=="": #es directorio
                        if not os.path.exists(file_target):
                            os.makedirs(file_target)
                    else: #es archivo
                        target = file(file_target, "wb")
                        with source, target:
                            shutil.copyfileobj(source, target)  
                print u"Reiniciando script..."
                common.restart_please()
        else:
            print u"Versión más reciente (%s)"%version

