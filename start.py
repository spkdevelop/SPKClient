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


import time,os
import subprocess
import sys
import apt
print "SPKClient:."
time.sleep(1)




def check_updates():
    
    print "Actualizando apt"

    dependencies_apt = ["libqt4-dev","libxml2-dev","libxslt1-dev","python-qt4","libxtst-dev","xvfb","x11-xkb-utils","python-dev","python-setuptools","python-pip"]
    dependencies_pip = ["pbkdf2","pyserial","spynner"]
    cache = apt.cache.Cache()
    print "Updating cache..."
    try:
        cache.update(raise_on_error=False)
        print "Cache updated."
    except:
        print "Error updating"
        
    for pkg_name in dependencies_apt:
        print "apt: %s" % pkg_name
        pkg = cache[pkg_name]
        if pkg.is_installed:
            print "{pkg_name} already installed".format(pkg_name=pkg_name)
        else:
            pkg.mark_install()
            try:
                cache.commit()
            except Exception, arg:
                print >> sys.stderr, "Sorry, package installation failed [{err}]".format(err=str(arg))
    
    for pip_pkg in dependencies_pip:
        print "pip: %s" % pip_pkg
        try:
            import pip
            pip.main(["install","--upgrade",pip_pkg])
        except:
            print "error"

try:
   check_updates()
except:
   pass
#j=os.path.join(os.path.dirname(os.path.abspath(__file__)),"json_tinyg")
f=os.path.join(os.path.dirname(os.path.abspath(__file__)),"main.py")
#s=os.path.join(os.path.dirname(os.path.abspath(__file__)),"spkserver.py")

subprocess.Popen(["sudo","xvfb-run","python",f])
#os.system("sudo '"+j+"'")
#subprocess.Popen("sudo ./json_tinyg",stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True) 
#os.popen("/home/pi/SPKClient./json_tinyg")
#os.system("sudo python '"+s+"'")

