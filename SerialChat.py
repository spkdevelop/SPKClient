# -*- coding: utf-8 -*-
import serial
import time

def get_serial():
    
    for i in range(0,100):
        try:
            usb=serial.Serial(
            port='/dev/ttyACM%s'%i,
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1)
            usb.open()
        except:
            pass

    while True:
        text_in = usb.readline()
        if not text_in.strip():
            text_out = raw_input("Serial write:").strip()
            usb.write(text_out + "\n")
            if text_out == "close":
                break
            if text_out == "read":
                for i in range(0,10):
                    print usb.readline()
            elif text_out == "file":
                lines = open("codigo_g.txt").read().split("\n")
                print "sending file..."
                for line in lines:
                    print "-----------"
                    print line
                    usb.write(line + "\n")
                    usb.write("$qr\n")
                    buffer = int(usb.readline().split(":")[1])
                    print "buffer: " + str(buffer)
                    if buffer < 6:
                        print "buffer exceeded"
                        while buffer < 6:
                            usb.write("$qr\n")
                            buffer = int(usb.readline().split(":")[1])
                            print "buffer exceeded"
                        
        
        else:
            print text_in
    usb.close()
    
if __name__ == "__main__":
    get_serial()

    
    
