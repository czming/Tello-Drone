#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import time
import threading

import numpy as np
import cv2
import imutils
import tellopy
import av


# In[ ]:


class DroneWrapper:
    def __init__(self):
        # Set up pre-trained model for faces
        CAFFE_PROTOTXT = "deploy.prototxt.txt"
        CAFFE_MODEL = "face.caffemodel"
        self.model = cv2.dnn.readNetFromCaffe(CAFFE_PROTOTXT, CAFFE_MODEL)
        # Minimum threshold for faces
        self.CONFIDENCE = 0.5
        
        # Drone movement states
        # Up & down
        self.throttle = 0
        # Forward & backward
        self.pitch = 0
        # Right & left
        self.roll = 0
        
        # Set up drone object
        self.drone = tellopy.Tello()
        self.drone.set_loglevel(0)
        
    # Connect to drone & set up video feed    
    def connect(self):
        # Put drone in command mode
        self.drone.connect()
        self.drone.wait_for_connection(3)
        # Turn on video feed of drone and access it
        self.drone.start_video()
        retry = 3
        self.video = None
        while self.video is None and retry > 0:
            retry -= 1
            try:
                self.video = av.open(self.drone.get_video_stream())
                self.video.streams.video[0].thread_type = 'AUTO'
            except av.AVError as ave:
                print(ave)
                print('retry...')

    def takeoff(self):
        self.drone.takeoff()
        # Move a little higher
        time.sleep(4)
        self.drone.up(30)
        time.sleep(3)
        self.drone.up(0)
        # Start thread to update drone movement periodically
        t = threading.Thread(target=self.update_drone_movement)
        t.start()
        
    def land(self):
        self.drone.land()
        
    def set_next_move(self, area, cx, cy, w, h):
        # Backwards/forwards sensitivity
        REF_AREA = 15000
        AREA_BUFFER = 2500
        MIN_AREA = 5000

        # Left/right sensitivity
        REF_X = w//2
        REF_Y = h//2
        TRANSLATE_BUFFER = 100
        
        # Speed
        TRANSLATIONAL_SPEED = 0.1
        THROTTLE_SPEED = 0.2
        
        # Reset all movement values first
        self.pitch = 0
        self.throttle = 0
        self.roll = 0
        
        # Move back
        if area > REF_AREA + AREA_BUFFER:
            self.pitch = -TRANSLATIONAL_SPEED
        # Move front
        elif MIN_AREA < area < REF_AREA - AREA_BUFFER:
            self.pitch = TRANSLATIONAL_SPEED
        
        # Move down
        if cy > REF_Y + TRANSLATE_BUFFER:
            self.throttle = -THROTTLE_SPEED
        # Move up
        elif cy < REF_Y - TRANSLATE_BUFFER:
            self.throttle = THROTTLE_SPEED
            
        # Move right
        if cx > REF_X + TRANSLATE_BUFFER:
            self.roll = TRANSLATIONAL_SPEED
        # Move left
        elif cx < REF_X - TRANSLATE_BUFFER:
            self.roll = -TRANSLATIONAL_SPEED
            
    def update_drone_movement(self):
        while True:
            self.drone.set_throttle(self.throttle)
            self.drone.set_pitch(self.pitch)
            self.drone.set_roll(self.roll)
            # Wait before updating again to give drone time to process
            time.sleep(0.2)
        
    def start_tracking(self):
        self.takeoff()
        running = True
        while running:
            frame_skip = 300
            try:
                for frame in self.video.decode(video=0):
                    # Skip some initial frames
                    if frame_skip > 0:
                        frame_skip -= 1
                        continue

                    # Get an image from frame
                    image = cv2.cvtColor(np.array(frame.to_image()), cv2.COLOR_RGB2BGR)
                    # Resize the image
                    image = imutils.resize(image, width=800)
                    # Get dimensions of image
                    (h, w) = image.shape[:2]

                    # Convert image to blob and identify face with model
                    blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0,
                                                 (300, 300), (104.0, 177.0, 123.0))
                    self.model.setInput(blob)
                    detections = self.model.forward()

                    # Get closest face
                    largest_area = 0
                    # loop over the detections and find best
                    for i in range(0, detections.shape[2]):
                        # extract the confidence of the detection
                        confidence = detections[0, 0, i, 2]
                        # If confidence of detection is above our threshold
                        if confidence > self.CONFIDENCE:
                            # compute the (x, y)-coordinates of the bounding box for the
                            # object
                            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                            (x1, y1, x2, y2) = box.astype("int")

                            # Process the bounding box to find area
                            area = (x2-x1)*(y2-y1)
                            # If current detected face is the closest to drone
                            if area > largest_area:
                                largest_area = area
                                # Find center point of face
                                cx, cy = (x1+x2)//2, (y1+y2)//2
                            # Display bounding box around detected face
                            cv2.rectangle(image, (x1, y1), (x2, y2),
                                      (0, 0, 255), 2)

                    # If we can find a face
                    if largest_area != 0:
                        # Get the next move the drone should make
                        move = self.set_next_move(largest_area, cx, cy, w, h)
                        
                    # If we cannot find any face
                    else:
                        self.pitch = 0
                        self.throttle = 0
                        self.roll = 0

                    # Display movement info
                    cv2.putText(image, "throttle(up-down): {}".format(self.throttle), (20, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 0), 2)
                    cv2.putText(image, "pitch(front-back): {}".format(self.pitch), (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 0), 2)
                    cv2.putText(image, "roll(right-left): {}".format(self.roll), (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 0), 2)
                    
                    # Display current frame on screen
                    cv2.imshow("image", image)
                    key = cv2.waitKey(1) & 0xFF

                    # Land drone if "q" is pressed
                    if key == ord("q"):
                        self.land()
                        running = False
                        break

                    # Skip some frames to keep up with drone
                    frame_skip = 5
            except Exception as e:
                print(e)


# In[ ]:


my_drone = DroneWrapper()


# In[ ]:


my_drone.connect()
my_drone.start_tracking()


# In[ ]:


my_drone.land()

