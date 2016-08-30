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

#URL="http://localhost:8080"
#URL="https://spksandbox.appspot.com"
URL="https://spkcloud.appspot.com"

from os import execl
import sys
import os.path
from spkserial import ThreadsafeSerial, DeadSerialException
import json
import urllib,urllib2
import spkthreads
import spkserver


CNCIDFILENAME="cncid"
USER_AGENT="SPK CNC-client" #esto lo checa el servidor, no cambiar

channelUrl=os.path.join(URL,"_cnc/backhandler")

def restart_please():
    exit_routine()
    execl(sys.executable, *([sys.executable]+sys.argv))
def set_id(new_id):
    global _cnc_id
    _cnc_id=new_id
    with open(os.path.join(get_current_path(),CNCIDFILENAME), 'w') as f:
        f.write("" if new_id ==None else new_id)
_cnc_id=None
def load_id():
    global _cnc_id
    if(os.path.exists(os.path.join(get_current_path(),CNCIDFILENAME))):
        with open(os.path.join(get_current_path(),CNCIDFILENAME), 'r') as f:
            _cnc_id=f.read()
            if _cnc_id=="":
                _cnc_id=None
def get_id():
    return _cnc_id
def get_current_path():
    return os.path.dirname(os.path.abspath(__file__))


def exit_routine():
    try:
        server_thread.server.shutdown()
    except:
        pass
    try:
        internet_thread.kill=True
        try: ThreadsafeSerial.get().close()
        except DeadSerialException:pass
        if internet_thread.channel_thread:
            internet_thread.channel_thread.kill=True
    except:
        pass
def send_config_info(info):
    
    data={"config_info":info}
    response= send_data(data)
    if response["command"]=="update_id":
        if "new_id" in response:
            set_id(response["new_id"])
        
    return response
def send_data(data):
    
    jsonData=json.dumps(data)

    urldata=urllib.urlencode({"data":jsonData})
    request=urllib2.Request(channelUrl,urldata, { 'User-Agent' : USER_AGENT})
    response=urllib2.urlopen(request).read()
    return json.loads(response)
server_thread=None
internet_thread=None
def start_threads():
    global internet_thread,server_thread
    internet_thread = spkthreads.InternetThread()
    internet_thread.start()
        
    server_thread = spkserver.ServerThread()
    server_thread.start()
def get_parser():
    usb=ThreadsafeSerial.get()
    if "USB" in usb.getPort():
        parser = "tiny-g"
    elif "ACM" in usb.getPort():
        parser = "grbl"
    else:
        raise Exception(u"No se pudo identificar el procesador de código G")
    return parser
