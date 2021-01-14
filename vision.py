from easytello import tello
import time
import cv2

drone = tello.Tello()

response = input('Input order of balloons to pop e.g. RGBY')
current_target = response[0]
target_color = {
    'R': ((0, 0, 200), (50, 50, 255)),
}

drone.streamon()

drone.takeoff()

running = True
while running:
    # get picture
    if drone.last_frame is None: continue
    
    frame = drone.last_frame.copy()
    
    # do some vision
    #filter for target balloon BGR
    filtered = cv2.inRange(frame, *target_color[current_target])
    
    #find 
    
    
    
    # perform action
    #drone.go(...)
    
    # wait
    time.sleep(0.1)

drone.land()
