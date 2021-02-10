from easytello import tello
import time
import cv2
import threading


class Vision:
    def __init__(self):
        #self.response = input('Input order of balloons to pop e.g. RGBY')
        self.current_target_index = 0
        #self.current_target = self.response[0]
        target_color = {  # in BGR values
            'R': ((0, 0, 200), (50, 50, 255)),
            'B': ((200, 0, 0), (255, 50, 50)),
            'Y': ((0, 200, 200), (50, 255, 255)),
            'G': ((0, 200, 0), (50, 255, 50))
        }


    def switchtarget(self):
        if self.current_target_index < len(self.response):
            self.current_target_index += 1
            self.current_target = self.response[self.current_target_index]


def start(queue, order):
    # Start UDP server to receive video from Tello
    cap = cv2.VideoCapture('udp://192.168.10.1:11111')
    i = 0

    # Main vision loop
    while cap.isOpened():
        # Read image
        ret, frame = cap.read()

        # Processing...

        # Send results to control loop
        queue.put({'type': 'data', 'red': None, 'green': None, 'blue': None, 'yellow': None})

        # Debugging client display
        cv2.imshow('Image', frame)
        key = cv2.waitKey(1) & 0xFF
        # Quit early if user presses ESC on the window
        if key == 27:
            break
        # Save a screenshot if the user presses SPACEBAR on the window
        if key == 32:
            cv2.imwrite(f'img_{i:05d}.jpg', frame)
            i += 1

    cap.release()
    queue.put({'type': 'quit'})

