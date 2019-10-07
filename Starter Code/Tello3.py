#
# Tello Python3 Control Demo 
#
# http://www.ryzerobotics.com/
#
# 1/1/2018

#uses text commands to control the drone


import threading 
import socket
import sys
import time

#empty host means referring to own IP address
host = ''
port = 9000
locaddr = (host,port) 


# Create a UDP socket, AF_INET for IPv4 addresses and SOCK_DGRAM for datagram oriented socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

#default gateway for tello on its on network
#can use packet sender program to send the packets and have a UDP server set up to
#receive the reply from tello
tello_address = ('192.168.10.1', 8889)

#I think this creates the server for device connected to Tello to receive packets back
#binds socket to the locaddr
sock.bind(locaddr)

def recv():
    count = 0
    #listening for packets from the tello at port 1518
    while True: 
        try:
            #recv from returns a tuple with the data as the first element
            #and the source, (ip_addr, port) as the second element
            #sock is binded to port 9000, 1518 specifies number of bytes for reply
            #wait for response from sock
            data, server = sock.recvfrom(1518)
            print(data.decode(encoding="utf-8"))
        except Exception as e:
            print (str(e))
            print ('\nExit . . .\n')
            break


print ('\r\n\r\nTello Python3 Demo.\r\n')

print ('Tello: command takeoff land flip forward back left right \r\n       up down cw ccw speed speed?\r\n')

print ('end -- quit demo.\r\n')


#recvThread create, runs on another thread (should be parallel to the main one)
#this new thread is passed the recv function to listen on the socket
#while we are sending it commands
recvThread = threading.Thread(target=recv)
#specify that it is a daemon thread listening in the background
recvThread.daemon = True
recvThread.start()

while True: 

    try:
        #note: tello works in units of cm and degrees
        #if sending instructions programatically, use time.delay to delay the instructions
        #to allow tello to complete previous instruction before giving it a new instruction
        #not sure what happens if instructions contradict though (it will still
        #acknowledge but not sure which instruction will it execute)
        time.sleep(0.5)
        msg = input("Command: ");

        if not msg:
            break  

        if 'end' in msg:
            print ('...')
            sock.close()  
            break

        #encodes message for tello
        msg = msg.encode(encoding="utf-8")
        #sends the message
        sent = sock.sendto(msg, tello_address)
    except KeyboardInterrupt:
        print ('\n . . .\n')
        sock.close()  
        break




