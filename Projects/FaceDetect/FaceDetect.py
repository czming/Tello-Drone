#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import argparse
import cv2
import imutils
import time
import tellopy
import av
import threading


# In[ ]:


# Constants to access pre-trained models
CAFFE_PROTOTXT = "deploy.prototxt.txt"
CAFFE_MODEL = "face.caffemodel"
CONFIDENCE = 0.5

# Global variables to check state of drone
movement_state = "standby"
drone_lock = False


# In[ ]:


# Function to stop movement of drone
def drone_stop():
    global movement_state
    if movement_state == "left":
        drone.left(0)
    elif movement_state == "right":
        drone.right(0)
    elif movement_state == "front":
        drone.forward(0)
    elif movement_state == "back":
        drone.backward(0)
    elif movement_state == "up":
        drone.up(0)
    elif movement_state == "down":    
        drone.down(0)

# Function to calculate where the drone should move next
def get_move(area, cx, cy, w, h):
    # Backwards/forwards sensitivity
    REF_AREA = 15000
    AREA_BUFFER = 2500
    MIN_AREA = 5000

    # Left/right sensitivity
    REF_X = w//2
    REF_Y = h//2
    TRANSLATE_BUFFER = 100
    
    # Move down
    if cy > REF_Y + TRANSLATE_BUFFER:
        return "down"
    # Move up
    elif cy < REF_Y - TRANSLATE_BUFFER:
        return "up"
    # Move right
    elif cx > REF_X + TRANSLATE_BUFFER:
        return "right"
    # Move left
    elif cx < REF_X - TRANSLATE_BUFFER:
        return "left"
    # Move back
    elif area > REF_AREA + AREA_BUFFER:
        return "back"
    # Move front
    elif MIN_AREA < area < REF_AREA - AREA_BUFFER:
        return "front"
    # Stop moving
    else:
        return "standby"

# Threaded function to move drone
def drone_move(move):
    # Access global variable
    global drone_lock
    
    SPEED = 10
    
    # Stop the drone's previous motion before performing a different one
    drone_stop()
    drone_lock = True
    
    # Give the drone time to stop
    time.sleep(0.1)
    
    # Perform new movement
    if move == "front":
        drone.forward(SPEED)
    elif move == "back":
        drone.backward(SPEED)
    elif move == "down":
        drone.down(SPEED*2)
    elif move == "up":
        drone.up(SPEED*2)
    elif move == "left":
        drone.left(SPEED)
    elif move == "right":
        drone.right(SPEED)

    # Give the drone time to move
    if move != "standby":
        time.sleep(0.1)
    
    # Everything's done, ready for next move
    drone_lock = False
  


# In[ ]:


# Set up machine learning model
net = cv2.dnn.readNetFromCaffe(CAFFE_PROTOTXT, CAFFE_MODEL)


# In[ ]:


# Set up drone
drone = tellopy.Tello()
drone.set_loglevel(0)


# In[ ]:


# Put drone in command mode
drone.connect()
drone.wait_for_connection(3)


# In[ ]:


# Turn on video feed of drone and access it
drone.start_video()
retry = 3
container = None
while container is None and 0 < retry:
    retry -= 1
    try:
        container = av.open(drone.get_video_stream())
        container.streams.video[0].thread_type = 'AUTO'
    except av.AVError as ave:
        print(ave)
        print('retry...')


# In[ ]:


# Takeoff!
drone.takeoff()


# In[ ]:


while True:
    frame_skip = 300
    try:
        for frame in container.decode(video=0):
            # Skip some initial frames
            if frame_skip > 0:
                frame_skip -= 1
                continue

            # Get an image from frame
            image = cv2.cvtColor(np.array(frame.to_image()), cv2.COLOR_RGB2BGR)
            # Resize for better performance
            image = imutils.resize(image, width=800)
            # Get dimensions of image
            (h, w) = image.shape[:2]

            # Convert image to blob and identify face with model
            blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0,
                                         (300, 300), (104.0, 177.0, 123.0))
            net.setInput(blob)
            detections = net.forward()
            
            # Get best detection of face
            best_detection = None
            best_confidence = 0
            # loop over the detections and find best
            for i in range(0, detections.shape[2]):
                # extract the confidence of the detection
                confidence = detections[0, 0, i, 2]
                # Assign the best detection
                if confidence > CONFIDENCE and confidence > best_confidence:
                    best_detection = detections[0,0,i]
                    best_confidence = confidence

            # If we can find a face
            if best_detection is not None:
                # compute the (x, y)-coordinates of the bounding box for the
                # object
                box = best_detection[3:7] * np.array([w, h, w, h])
                (x1, y1, x2, y2) = box.astype("int")

                # Process the bounding box to find area and center point
                area = (x2-x1)*(y2-y1)
                cx, cy = (x1+x2)//2, (y1+y2)//2
                
                # Get the next move of the drone
                move = get_move(area, cx, cy, w, h)
                # If the move is different
                # (i.e. drone not already performing the move)
                if not drone_lock and movement_state != move:
                    # Move the drone in a separate thread as delay is involved
                    thread = threading.Thread(target=drone_move, args=(move,))
                    thread.start()
                    # Record down the move for comparison in the next frame
                    movement_state = move
                    
                # Display movement state of drone
                cv2.putText(image, movement_state, (cx, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)

                # Display bounding box around detected face
                cv2.rectangle(image, (x1, y1), (x2, y2),
                              (0, 0, 255), 2)
            # If we cannot find any face and drone is moving
            elif movement_state != "standby":
                drone_stop()
                movement_state = "standby"

            # Display current frame on screen
            cv2.imshow("image", image)
            key = cv2.waitKey(1) & 0xFF

            # Land drone if "q" is pressed
            if key == ord("q"):
                drone.land()

            # Skip some frames to keep up with drone
            frame_skip = 5
    except Exception as e:
        print(e)


# In[ ]:


drone.land()

