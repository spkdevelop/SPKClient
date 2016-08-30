import os
import subprocess
process= os.popen("sudo ps -e").read().splitlines()
for i in  ["python","Xvfb","xvfb-run"]:
    for prs in process:
        try:
            
            pid = int(prs.strip().split(" ")[0].strip())
        except:
            pid = None
        if i in prs and pid:
            try:

                if pid != os.getpid():
                	os.kill(pid,9)
			print i
            except:
                pass          
subprocess.Popen(["sudo","python","start.py"])
