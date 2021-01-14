from easytello import tello
import time

drone = tello.Tello()

response = input('Input order of balloons to pop e.g. RGBY')

drone.streamon()

drone.takeoff()

running = True
while running:
    # get picture
    if self.last_frame is None: continue
    
    frame = self.last_frame.copy()
    
    # do some vision
    # HoughCircles
    
    # perform action
    #drone.go(...)
    
    # wait
    time.sleep(0.1)

drone.land()
