from easytello import tello
import time
import cv2
import threading


class Vision:
    def __init__(self, drone):
        self.drone = drone

        self.response = input('Input order of balloons to pop e.g. RGBY')
        self.current_target_index = 0
        self.current_target = self.response[0]
        target_color = {  # in BGR values
            'R': ((0, 0, 200), (50, 50, 255)),
            'B': ((200, 0, 0), (255, 50, 50)),
            'Y': ((0, 200, 200), (50, 255, 255)),
            'G': ((0, 200, 0), (50, 255, 50))
        }
        self.running = True
        self.look = threading.Thread(target=self.exist).start()


    def switchtarget(self):
        if self.current_target_index < len(self.response):
            self.current_target_index += 1
            self.current_target = self.response[self.current_target_index]

    # def start(self): #consider moving this to own drone class
      #  self.drone.streamon()

     #   self.drone.takeoff()
      #  self.running = True

    def exist(self): #TODO: locate the balloon and command drone to move
        while self.running:
            # get picture
            if self.drone.last_frame is None: continue

            frame = self.drone.last_frame.copy()

            # do some vision
            # filter for target balloon BGR
            filtered = cv2.inRange(frame, *self.target_color[self.current_target])

            # find

            # perform action
            # drone.go(...)

            # wait
            time.sleep(0.1)

        self.drone.land()

