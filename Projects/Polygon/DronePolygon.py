#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# Import socket and time modules
import socket
import time

# Configure IP and port of Tello
tello_address = ('192.168.10.1', 8889)

# Create a UDP connection that we'll send the command to
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to a local UDP server
sock.bind(('', 9000))


# In[ ]:


# Function to send messages to Tello
def send(message, delay):
    try:
        sock.sendto(message.encode(), tello_address)
        print("Sending message: " + message)
    except Exception as e:
        print("Error sending: " + str(e))
    # Wait for tello to finish processing the message
    time.sleep(delay)


# Function that listens for messages from Tello and prints them to the screen
def receive(delay):
    try:
        response, ip_address = sock.recvfrom(128)
        print("Received message: " + response.decode(encoding='utf-8') + " from Tello with IP: " + str(ip_address))
    except Exception as e:
        print("Error receiving: " + str(e))
    # Wait for tello to finish sending the message
    time.sleep(delay)


# In[ ]:


# Receive input from user on polygon sides
n = int(input("Enter the number of sides in the polygon: "))


# In[ ]:


# Calculate interior angle using formula
interior_angle = (n-2)*(180)//n
# Angle to turn is 180-interior angle
turning_angle = 180-interior_angle
# The length of 1 side of the polygon
step = 30


# In[ ]:


# Send Tello into command mode
send("command",2)


# In[ ]:


# Takeoff!
send("takeoff", 4)
# For every side of the polygon
for i in range(n):
    # Turn
    send("cw {}".format(turning_angle), 3)
    # Move forward
    send("forward {}".format(step), 3)

# Land after finishing polygon
send("land",1)

