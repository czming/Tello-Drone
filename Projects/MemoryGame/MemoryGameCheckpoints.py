#!/usr/bin/env python
# coding: utf-8

# In[1]:


# Configure the connection to the Tello Drone
# Import the necessary modules
import socket
import threading
import time

# IP and port of Tello
tello_address = ('192.168.10.1', 8889)

# IP and port of local computer
local_address = ('', 9000)

# Create a UDP connection that we'll send the command to
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind to the local address and port
sock.bind(local_address)

# Send the message to Tello and allow for a delay in seconds
def send(message, delay):
  # Try to send the message otherwise print the exception
  try:
    sock.sendto(message.encode(), tello_address)
    print("Sending command: " + message)
  except Exception as e:
    print("Error sending: " + str(e))

  # Delay for a user-defined period of time
  time.sleep(delay)

# Received messages
responses = []

# Receive the message from Tello
def receive():
  # Continuously loop and listen for incoming messages
  while True:
    # Try to receive the message otherwise print the exception
    try:
      response, ip_address = sock.recvfrom(128)
      print("Received message: " + response.decode(encoding='utf-8'))
      responses.append(response.decode(encoding='utf-8'))
    except Exception as e:
      # If there's an error close the socket and break out of the loop
      sock.close()
      print("Error receiving: " + str(e))
      break

# Create and start a listening thread that runs in the background
# This utilizes our receive functions and will continuously monitor for incoming messages
receiveThread = threading.Thread(target=receive)
receiveThread.daemon = True
receiveThread.start()


# In[2]:


# Memory game with Tello
import random

# Randomly pick Tello moves and have the user recall and type them out

# moving in 6 directions (coordinates change)
basic_choices = "right left up down forward back".split()
coord_changes = [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]
distance = 20

def basic_move():
    # select an index
    move_index = random.choice(range(6))
    move = basic_choices[move_index]
    
    global current_pos # since current_pos is defined below
    # track the position so Tello won't have a different starting point
    # tuples, like strings, can only be concatenated and not edited element-wise unless you reassign something entirely new
    # (1,2,3)*3 for instance gives (1,2,3,1,2,3,1,2,3) and (1,2,3) + (4,5,6) == (1,2,3,4,5,6)
    current_pos = tuple(current_pos[i] + distance*coord_changes[move_index][i] for i in range(3))
    
    command = move + " " + str(distance)
    send(command, 3)
    return move[0] # represented by the first letter

# spinnning cw ccw
spin_choices = "cw ccw".split()
spin_angle = 360

def spin_move():
    move = random.choice(spin_choices)
    command = move + " " + str(spin_angle)
    send(command, 5)
    return move

# flipping in any 1 direction
direction_choices = "f b l r".split()

def flip_move():
    flip_direction = random.choice(direction_choices)
    move = "f" + flip_direction
    command = "flip " + flip_direction
    send(command, 4)
    return move

def original_pos():
    global current_pos
    # after shifting around
    for i in range(3):
        coord = current_pos[i]
        
        # only adjust if there has been any changes, i.e. non-zero coordinates
        if abs(coord):
            while abs(coord) > 500:
                # reduce coord
                coord = coord + 500 * (-1)**(coord < 0)
                
                print("Somebody is a pro gamer! monkaS")
                
                # explained below
                adjustment = basic_choices[i*2 + coord > 0] + " 500"
                send(adjustment, 10)
                # you can try and use Tello's "go" command instead of relying on current_pos.
            
            # if coord is positive, we need a negative change and vice versa.
            adjustment = basic_choices[i*2 + coord > 0] + " " + str(abs(coord))
            send(adjustment, 6)


# In[3]:


# Main
# seed for better randomness using the current system time
random.seed()

# so every direction of every move is represented by equal chance
total_choices = [basic_move]*6 + [spin_move]*2 + [flip_move]*4
move_history = []
current_pos = (0,0,0)

# the higher the level, the longer the move chain. Start with 4.
_start_level = 4
level = _start_level
highest_level = 0
lives = 3 # if failed 3 times in a level then the level will drop

# set drone to command and query the battery and takeoff
send("command", 3)
send("battery?", 3)
if int(responses[-1]) > 70:
    send("takeoff", 8)
else:
    print("Please charge the drone first!")
    time.sleep(20)
    sock.close()
    assert(False)

print("Tello will now bamboozle you with lengthy dances. Try to remember what Tello did!")

print("\nTello moves forward (f), back (b), left (l), right (r), up (u), down (d),\n"
      " spins clockwise (cw), counter-clockwise (ccw), and flips forward (ff), back (fb),\n"
      " left (fl), right (fr)")

print("After Tello performs the moves, enter the moves in order, separated by spaces, like so:\nf fl ccw")

print("\nEnter 'end' or use the keyboard interrupt (ctrl+C) to end the program")

# game loop
while True:
    # "level" starts at 1 for the player
    print("\n--~=LEVEL " + str(level - _start_level + 1) + "=~--\n")
        
    try:
        for i in range(level):
            move_chosen = random.choice(total_choices)
            print(move_chosen)
            while True:
                prev_pos = current_pos
                # the move function sends the command to Tello and if applicable updates current_pos
                move_made = move_chosen() 
                if responses[-1] == "ok":
                    # sometimes Tello doesn't take the command
                    break
                current_pos = prev_pos # revert any incorrect changes

            # track moves
            move_history.append(move_made)

        msg = input("What do you think Tello just did?\n")
        
        # if the user wishes to, stop the game
        if msg == "end":
            assert(False)
        
        if msg == ' '.join(move_history):
            print("Correct! Time to up the difficulty!")
            highest_level = max(level, highest_level)
            level += 1
            lives = 3 # reset lives
        
        else:
            print("Wrong! The actual moves made were:\n", ' '.join(move_history))
            lives -= 1
            if not lives:
                # dies
                print("You failed 3 times at this level! Dropping difficulty (if possible)")
                
                # minimum level. git gud pls.
                level = max(level-1, _start_level)
                lives = 3
        
        print("\nWe're gonna play again! Your current record level is: LEVEL " + str(highest_level))
        
        # reset move_history
        move_history = []
        # reset position
        original_pos()
        
    except (KeyboardInterrupt, AssertionError):
        send("land", 8)
        print("\nGame Over\n")
        print("Your highscore: " + str(highest_level))
        sock.close()
        break


# In[ ]:




