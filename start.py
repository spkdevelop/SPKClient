import time,os
time.sleep(15)
f=os.path.join(os.path.dirname(os.path.abspath(__file__)),"main.py")

os.system("sudo xvfb-run python '"+f+"'")

