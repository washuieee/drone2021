from easytello import tello
import time
import cv2
import threading
import queue


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


def start(q, order):
    # Start UDP server to receive video from Tello
    cap = cv2.VideoCapture('udp://192.168.10.1:11111')
    i = 0

    try:
        # Main vision loop
        while cap.isOpened():
            # Read image
            ret, frame = cap.read()

            results = {'type': 'data', 'red': None, 'green': None, 'blue': None, 'yellow': None}

            # Processing...
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            thresh1 = cv2.bitwise_or(
                    cv2.inRange(hsv, (0, 150, 100), (20, 255, 255)),
                    cv2.inRange(hsv, (160, 150, 100), (180, 255, 255)))
            contours, hierarchy = cv2.findContours(
                    thresh1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            filtered = [c for c in contours if cv2.contourArea(c) > 1000]
            if len(filtered) > 0:
                contour = max(filtered, key=lambda c: cv2.contourArea(c))
                # find the center of the balloon
                mu = cv2.moments(contour)
                x = int(mu['m10'] / mu['m00']) - frame.shape[1]//2
                y = -int(mu['m01'] / mu['m00']) + frame.shape[0]//2

                xrot = x / 960 * 82.6
                yrot = y / 720 * 82.6

                results['red'] = (xrot, yrot)

            thresh3 = cv2.inRange(hsv, (25-10, 150, 150), (25+10, 255, 255))
            contours, hierarchy = cv2.findContours(
                    thresh3, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            filtered = [c for c in contours if cv2.contourArea(c) > 1000]
            if len(filtered) > 0:
                contour = max(filtered, key=lambda c: cv2.contourArea(c))
                # find the center of the balloon
                mu = cv2.moments(contour)
                x = int(mu['m10'] / mu['m00']) - frame.shape[1]//2
                y = -int(mu['m01'] / mu['m00']) + frame.shape[0]//2

                xrot = x / 960 * 82.6
                yrot = y / 720 * 82.6

                results['yellow'] = (xrot, yrot)

            # Send results to control loop
            try:
                q.put(results, block=False)
            except queue.Full:
                pass

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
    except KeyboardInterrupt:
        print("Vision exiting")

    cap.release()
    q.put({'type': 'quit'})

