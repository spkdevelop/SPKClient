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


import threading
import logging
import time
import urllib
import json
import codecs
import traceback
import sys
import base64
import os
import serial
import urllib2
from cStringIO import StringIO
import spynner
import cutter
import zipfile
from hashlib import sha1

#URL="http://localhost:8080"
#URL="https://spksandbox.appspot.com"
URL="https://spkcloud.appspot.com"
channelUrl=os.path.join(URL,"_cnc/backhandler")
USER_AGENT="SPK CNC-client" #esto lo checa el servidor, no cambiar
CNCIDFILENAME="cncid"
class ScriptThread(threading.Thread):
    def __init__(self,job_id,arguments):
        threading.Thread.__init__(self)
        self.kill=False
        self.job_id=job_id
        self.stop_script=False
        self.can_stop=True
        self.daemon=True
        self.arguments=arguments
    def run(self):
        try:

            added_functions={"set_status":thread.set_status,
                       "set_can_stop":self.set_can_stop,
                       "get_requested_exit":self.get_requested_exit,
                       "get_serial":thread.get_serial,
                       "get_variable":thread.get_peristent_variable,
                       "set_variable":thread.set_persistent_variable}
            for f in added_functions:
                setattr(cutter,f,added_functions[f])
            try:
                cutter.run(*self.arguments)
            except (SystemExit,KeyboardInterrupt,GeneratorExit):
                pass
            except Exception,info:
                
                exc_type, exc_value, exc_traceback = sys.exc_info()
                trace=str.decode(traceback.format_exc(),"utf-8")
                fullerror=unicode.join(u"\n",trace.splitlines()[3:])
                try:
                    line=info[1][1] #la vida...
                except:
                    line=traceback.extract_tb(exc_traceback)[-1][1]#...es complicada  
                #y obtener la linea correcta... tambien              
                thread.script_error({"line":line,"fullInfo":fullerror,"exception":str(exc_value)})   
            else:
                thread.script_success()
            thread.script_status=None
            try:
                os.remove(filename)
            except:
                pass
            thread.scriptThread=None  
            thread.required_post_important=True
        except Exception as e:
            logger.error(e)
                          
    def set_can_stop(self,can_stop):
        if self.can_stop!=can_stop:
            self.can_stop=can_stop
            thread.required_post_important=True
    def get_requested_exit(self):
        return self.stop_script and self.can_stop
class ChannelApiThread(threading.Thread):
    
    def __init__(self,message_callback):
        threading.Thread.__init__(self)
        self.connected=False
        self.connecting=False

        self.kill=False
        self.token=None
        self.bad_token=None
        self.message_callback=message_callback
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
            if error_code==401:
                self.bad_token=self.token
                self.token=None
        elif message["state"]=="close":

            self.connected=False
            self.retry()
            

        
    def run(self):
        url=os.path.join(URL,"_cnc/channelclient")

        browser=spynner.Browser()
        browser.create_webview(True)
        browser.load(url,load_timeout=30)
        browser.set_javascript_prompt_callback(self._message_listener)
        while self.kill==False:
            if self.token and not self.connected and self.connecting:
                browser.runjs("openChannel('"+self.token+"')")
                self.connected=True
                self.connecting=False
                
            browser.wait(1)

        browser.close()
    def connect(self,token):

        self.token=token
        self.bad_token=None
        self.retry()
    def retry(self):
        if not self.connected and self.token:        
            self.connecting=True

        
        
class InternetThread (threading.Thread):
    
    def __init__(self):
        threading.Thread.__init__(self)
        self.kill=False
        self.scriptThread=None
        self.script_status=None
        self.last_run_ending=None
        self.serial=None
        self.persistent_vars={}
        self.channel_api_token=None
        self.channel_thread=None
        self.required_post=True
        self.required_post_important=True
    def set_persistent_variable(self,variable,value):
        self.persistent_vars[variable]=value
    def get_peristent_variable(self,variable):
        return self.persistent_vars[variable] if variable in self.persistent_vars else None
    def get_serial(self):
        if not self.serial:
            #self.serial=serial.Serial("/dev/pts/13",115200)
            self.serial=serial.Serial("/dev/ttyACM0",115200)
	if not self.serial.isOpen(): 
	    self.serial.open()
        return self.serial
    def set_status(self,text,fase=None,data=None):
        assert(isinstance(text, basestring))
        status ={"text":text}
        if fase != None:
            status["fase"]=fase
        if data != None:
            status["data"]=data
        if self.script_status==status: return
        self.script_status=status
        self.required_post=True
    def script_error(self,error):
        error["type"]="error"
        self.last_run_ending=error
        self.scriptThread=None
    def script_success(self):
        self.last_run_ending={"type":"success"}
        self.scriptThread=None
    def channel_api_message(self,message):
        #print message
        self.manage_response(json.loads(message))
    def run(self):
        try:
            self.cnc_id=""
            if(os.path.exists(os.path.join(get_current_path(),CNCIDFILENAME))):
                file = open(os.path.join(get_current_path(),CNCIDFILENAME), 'r')
                self.cnc_id=file.read()
                file.close()
            self.channel_thread=ChannelApiThread(self.channel_api_message)
            self.channel_thread.start()
            while not self.kill:
                self.required_post=False
                self.required_post_important=False
                response=self.send_prescence()
                self.manage_response(response)
                
                i=0
                while self.kill==False and self.required_post_important==False and (self.required_post==False or i<10) and (self.channel_thread.connected==True or self.channel_thread.connecting==True):
                    i+=1
                    time.sleep(0.1)
        except ZeroDivisionError as e:
            logger.error(e)
    def send_prescence(self):
        if self.cnc_id==None and config_data==None:
            print "Debes configurar esta máquina, ve a http://www.spkautomatizacion.com/new-cnc y sigue las instrucciones"
            exit()
        data={"id":self.cnc_id}
        if self.cnc_id==None:
            data["config_info"]=config_data
        if self.channel_thread.token==None:
            if self.channel_thread.bad_token!=None:
                data["bad_token"]=self.channel_thread.bad_token
            data["get_token"]=True
            
        if self.scriptThread!=None:
            data["current_cut_job"]=self.scriptThread.job_id
            data["can_stop_script"]=self.scriptThread.can_stop
            data["request_script_stop"]=self.scriptThread.stop_script
            if self.scriptThread.can_stop==False:
                self.scriptThread.stop_script=False
            
            if self.scriptThread.stop_script:
                data["stop_requested"]=True
            if self.script_status!=None:             
                data["script_status"]=self.script_status
            
        else:
            data["running_script"]=None
        if self.last_run_ending:
            data["last_run_ending"]=self.last_run_ending
            self.last_run_ending=None
        try:
            #print data
            response=self.send_data(data)
            #print response
            response_object=json.loads(response)
        except Exception as error:
            #print error
            response_object={}
            time.sleep(10) #durmamos 10 segundos, hubo un error con el servidor
        return response_object
    def send_data(self,data):
        
        jsonData=json.dumps(data)

        urldata=urllib.urlencode({"data":jsonData})
        request=urllib2.Request(channelUrl,urldata, { 'User-Agent' : USER_AGENT})
        response=urllib2.urlopen(request).read()
        return response
    @staticmethod
    def on_rasp():
        #Hay que buscar una manera de que esta funcion nos diga si estamos en la raspberry, esto no es muy buena idea que digamos. 
        return os.uname()[4].startswith("arm")
    def manage_response(self,data): 
        if "channel_api_token" in data:
            self.channel_thread.connect(data["channel_api_token"])   
        if "command" in data:
            if data["command"]=="update_main_script":
                file_url=URL+data["file_url"]
                response = urllib2.urlopen(file_url)
                _file = StringIO(response.read())
                self.send_data({"id":self.cnc_id,"received_update":True})
                if zipfile.is_zipfile(_file):
                    zfl=zipfile.ZipFile(_file)
                    members=zfl.namelist()[:]
                    for n in members[:]:
                        if not n.endswith(".py"):
                            members.remove(n) #solo remplazamos los archivos.py
                    zfl.extractall(get_current_path(),members)
                    print u"Actualización recibida, reiniciando script..."
                    os.execl(sys.executable, *([sys.executable]+sys.argv)) #reiniciaimos
            if data["command"]=="re_configure":
                    file = open(os.path.join(get_current_path(),CNCIDFILENAME), 'w')
                    file.write("")
                    self.cnc_id=None
                    file.close()
            if data["command"]=="invalidate_config_info":
                    config_data=None
                    print u"Parece que hay un problema con la configuración, el servidor contestó: %s"%data["reason"]
            if data["command"]=="update_id":
                if "new_id" in data:
                    file = open(os.path.join(get_current_path(),CNCIDFILENAME), 'w')
                    file.write(data["new_id"])
                    self.cnc_id=data["new_id"]
                    file.close()
            elif data["command"]=="stop_script":
                if self.scriptThread!=None and self.scriptThread.can_stop:
                    self.scriptThread.stop_script=True
                    self.script_status=None
                    self.required_post_important=True

            elif data["command"]=="run_script":
                if self.scriptThread==None:
                    if "script_data" in data:
                        scriptThread=ScriptThread(job_id=data["script_data"]["job_id"],arguments=data["script_data"]["arguments"])
                        self.scriptThread=scriptThread
                        self.last_run_ending=None
                        self.required_post_important=True
                        
                        scriptThread.start()
    
                    



def get_current_path():
    return os.path.dirname(os.path.abspath(__file__))

args= sys.argv
if len(args)>1:
    extra_data=args[1]
    try:
        extra_data=base64.urlsafe_b64decode(extra_data)
        extra_data=urllib.unquote(extra_data)
        config_data=json.loads(extra_data)
    except:
        config_data=None
else:
    config_data=None

logging.basicConfig(filename=os.path.join(get_current_path(),'errors.log'), level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger(__name__)
try:
    thread = InternetThread()

    thread.start()
    while thread.isAlive(): 
        thread.join(1)  
except (KeyboardInterrupt, SystemExit):
    pass
except ZeroDivisionError:
    logger.error(e)
finally:
    if thread.serial and thread.serial.isOpen():
        thread.serial.close()
    thread.kill=True
    if thread.channel_thread:
        thread.channel_thread.kill=True
    
