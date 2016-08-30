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
import wifi
import os
import socket
import fcntl
import struct
import subprocess
from wifi.exceptions import InterfaceError
default_network_file ="""\
auto lo
iface lo inet loopback
iface eth0 inet dhcp
auto wlan0
allow-hotplug wlan0
"""

WLAN = "wlan0"
extra_name = "-False"

INTERFACES_FILE =  "/etc/network/interfaces"
def check_interfaces_file():
    if not os.path.exists(INTERFACES_FILE):
        f = open(INTERFACES_FILE,"w")
        with f: f.write(default_network_file)

def remove_extra_name():
    f = open(INTERFACES_FILE,"r")
    network_file = f.read()
    f.close()
    
    if extra_name in network_file:
        f = open(INTERFACES_FILE,"w")
        f.write(network_file.replace(extra_name,""))
        f.close()
    

def get_ip_address_for(ifname):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24])
    except IOError:
        return None
def get_ip_adresses():
    return (get_ip_address_for("eth0"),get_ip_address_for(WLAN))
def get_ip_adress():
    eth0,wlan0=get_ip_adresses()
    return eth0 if eth0 is not None else wlan0 #le damos preferencia a la direccion ethernet

def set_wifi_network(network,password):
        cells=get_available_networks() #buscamos la red
        
        for cell in cells:
            if cell.ssid==network: break
        else: return False
        
        last_scheme=wifi.Scheme.find(WLAN,None)
        
        if last_scheme is not None:
            last_scheme.delete()
        scheme=wifi.Scheme.for_cell(WLAN,False,cell,password)
        scheme.save()
        
        try:
            scheme.activate()
            #remove_extra_name()
            return True
        except:
            scheme.delete()
            if last_scheme is not None:
                try:
                    last_scheme.save()
                    last_scheme.activate()
                except:pass
            return False
        
def get_available_networks():
    try:
        cells=wifi.Cell.all(WLAN)
        
        try:
            cells =[d for d in sorted(cells, key=lambda k: -k.signal if hasattr(k,"signal") else 0)]
        except:
            pass
        cells_widthout_duplicates=[]
        ssids=[]
        for cell in cells:
            if not cell.encrypted:
                continue #no permitimos redes abiertas
            if not cell.ssid in ssids:
                cells_widthout_duplicates.append(cell)
                ssids.append(cell.ssid)
        return cells_widthout_duplicates
    except InterfaceError:
        return []

def get_current_connected_network():
    try:
        curr= subprocess.check_output("sudo iwgetid -r", shell=True).strip()
        if curr=="":
            return None
        return curr
    except:
        return None
