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
import serial,threading

class ThreadsafeSerial(serial.Serial):
    _serial=None
    wlock = threading.RLock()
    rlock = threading.RLock()
    def readline(self,**kargs):
        timeout=kargs.get("timeout",None)
        if "timeout" in kargs:
            del kargs["timeout"]
        with self.rlock:
            
            if self.getTimeout()!=timeout:self.setTimeout(timeout)
            return serial.Serial.readline(self,**kargs)
     
    def read(self,size=1):
        with self.rlock:
            try:
                return serial.Serial.read(self,size)
            except serial.SerialException:
                self.close()
                raise DeadSerialException()
    def write(self,data):

        with self.wlock:
            try:
                serial.Serial.write(self,str(data))

            except serial.SerialException:
                self.close()
                raise DeadSerialException()
    #pyserial cambio la implementacion y nos paso a joder
    #la nueva es self.timeout
    #cuando todo este actualizado, se puede cambiar por esa
    def getTimeout(self):
        try:
            return serial.Serial.getTimeout(self)
        except:
            return self.timeout
    def setTimeout(self,timeout):
            try:
                return serial.Serial.setTimeout(self,timeout)
            except:
                self.timeout=timeout
    def getPort(self):
        try:
            return serial.Serial.getPort(self)
        except:
            return self.port
    
    
    @classmethod 
    def get(cls):
        if cls._serial is not None and not cls._serial.isOpen():
            cls._serial=None
        if not cls._serial:
            for l in (s % str(c) for c in range(0,100) for s in ["/dev/ttyUSB%s","/dev/ttyACM%s"]):
                try:
                    cls._serial=ThreadsafeSerial(l,115200,rtscts=True)
                    if not cls._serial.isOpen():
                        cls._serial.open()
                    cls._serial.flush()
                    break
              
                except Exception:
                    continue
            else:
                raise DeadSerialException() 
    
        return cls._serial

class DeadSerialException(Exception):
    pass
