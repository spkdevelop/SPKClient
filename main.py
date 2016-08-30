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


import logging
import spkwifi
import common
import os.path
import time

print "Iniciando"

spkwifi.check_interfaces_file()
common.load_id()

logging.basicConfig(filename=os.path.join(common.get_current_path(),'errors.log'), level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger(__name__)
try:
    common.start_threads()

    while common.internet_thread.isAlive(): 
        #time.sleep(1)
        #pass
        common.internet_thread.join(1)  
        
except (KeyboardInterrupt, SystemExit):
    pass
except Exception as e:
    print e
    logger.error(e)
finally:
    common.exit_routine()
        