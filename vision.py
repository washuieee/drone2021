from easytello import tello
import time
import cv2
import av
import numpy as np
import threading
import queue
import time
import itertools
import functools


class Vision(object):
    def __init__(self, record=True):
        self.frame_skip = 300
        if record:
            self.out = cv2.VideoWriter(f"{time.time()}.avi",
                    cv2.VideoWriter_fourcc("M","J","P","G"), 30, (960, 720), True)
        else:
            self.out = None

    def open_input(self, source, retry = 3):
        self.container = None
        ave = None
        while self.container is None and 0 < retry:
            retry -= 1
            try:
                self.container = av.open(source)
            except av.AVError as ave:
                print(ave)
                print('retry...')
        if self.container is None:
            raise ave
        self.stream = self.container.decode(video=0)

    def check_new_frame(self, q, status):
        frame = next(self.stream)
        self.new_frame(frame, q, status)

    def new_frame(self, frame, q, status):
        if 0 < self.frame_skip:
            self.frame_skip = self.frame_skip - 1
            return

        image = cv2.cvtColor(np.array(frame.to_image()), cv2.COLOR_RGB2BGR)

        start_time = time.time()
        if self.out is not None:
            self.out.write(image)

        results = process(q, image, status)
        # Send results to control loop
        try:
            q.put(results, block=False)
        except queue.Full:
            pass

        key = cv2.waitKey(1) & 0xFF
        # Quit early if user presses ESC on the window
        if key == 27:
            q.get(block=False)
            q.put({'type': 'quit'}, timeout=5)
        # Save a screenshot if the user presses SPACEBAR on the window
        if key == 32:
            cv2.imwrite(f'img_{time.time()}.jpg', image)
        # Recalculate frame skip depending on how fast we're going
        if frame.time_base < 1.0/60:
            time_base = 1.0/60
        else:
            time_base = frame.time_base
        self.frame_skip = int((time.time() - start_time)/time_base)


def start(q, order, source):
    # Start UDP server to receive video from Tello
    out = None
    i = 0


    try:
        # Main vision loop
        frame_skip = 300
        running = True
        cv2.namedWindow("Display")
        while running:
            for frame in container.decode(video=0):
                pass
    except KeyboardInterrupt:
        print("Vision exiting from CTRL-C")
    finally:
        if out is not None:
            out.release()
        cv2.destroyAllWindows()

    q.put({'type': 'quit'}, timeout=5)


last_frame_time = None
def process(q, frame, status):
    global last_frame_time
    # Processing...
    frame = cv2.GaussianBlur(frame, (11, 11), 0)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
#    threshR = cv2.bitwise_or(
#            cv2.inRange(hsv, (0, 150, 100), (20, 255, 255)),
#            cv2.inRange(hsv, (160, 150, 100), (180, 255, 255)))
#    threshG = cv2.inRange(hsv, (40, 0, 0), (70, 255, 255))
#    threshB = cv2.inRange(hsv, (105-10, 150, 0), (105+10, 255, 255))
#    threshY = cv2.inRange(hsv, (25-10, 150, 150), (25+10, 255, 255))
    #DUC
    threshR = cv2.bitwise_or(
            cv2.inRange(hsv, (0, 150, 100), (10, 255, 255)),
            cv2.inRange(hsv, (160, 150, 100), (180, 255, 255)))
    threshG = cv2.inRange(hsv, (38, 50, 104), (72, 255, 255))
    threshB = cv2.inRange(hsv, (102, 150, 100), (119, 255, 255))
    threshY = cv2.inRange(hsv, (25, 150, 119), (34, 255, 255))

    #kernel = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8)
    kernel = np.ones((5,5),np.uint8)
    threshR = cv2.morphologyEx(threshR, cv2.MORPH_OPEN, kernel)
    threshG = cv2.morphologyEx(threshG, cv2.MORPH_OPEN, kernel)
    threshB = cv2.morphologyEx(threshB, cv2.MORPH_OPEN, kernel)
    threshY = cv2.morphologyEx(threshY, cv2.MORPH_OPEN, kernel)

#    cv2.imshow("Red", threshR)
#    cv2.imshow("Green", threshG)
#    cv2.imshow("Blue", threshB)
#    cv2.imshow("Yellow", threshY)

    display = frame.copy()
    results = {
            'type': 'data',
            'red': track_balloon(threshR, display, (0,0,255)),
            'green': track_balloon(threshG, display, (0,255,0)),
            'blue': track_balloon(threshB, display, (255,0,0)),
            'yellow': track_balloon(threshY, display, (0,255,255)),
            }


    # Debugging client display
    now = time.time()
    if last_frame_time is not None:
        interframe = now - last_frame_time
        fps = int(1/interframe)
        cv2.putText(display, f"{fps}FPS - Press ESC to land drone and exit",
                (20,20), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255,0,255))

    print(status)
    cv2.putText(display, status,
            (20,700), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255,0,255))
    last_frame_time = now
    cv2.imshow('Display', display)

    return results


CONTOUR_MIN_AREA = 1000
#BALLOON_CENTER_DIAMETER_CM = 33.422  # circ 105cm
BALLOON_CENTER_DIAMETER_CM = 21  # circ 105cm
#FOCAL_LENGTH_PX = 711  # curve fit result
FOCAL_LENGTH_PX = 904  # camera calibration result
CENTER_X = 480
CENTER_Y = 150
def track_balloon(thresh, debug, color):
    # Find contours in binary image
    contours, hierarchy = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(debug, contours, -1, color, 1)
    # Filtering
    filtered = filter(lambda c: len(c) > 5, contours)
    # Remove small contours
    filtered = filter(lambda c: cv2.contourArea(c) > CONTOUR_MIN_AREA, filtered)
    # Remove contours that don't look like a balloon
    def is_like_balloon(contour):
        rect = cv2.fitEllipse(contour)
        center, size, angle = rect
        # Check that the ellipse is close-ish to a circle
        if max(size)/min(size) - 1 > 0.5:
            return False
        # Check that ellipse well fits the contour
        ellipse_area = np.pi * size[0] * size[1] / 4
        contour_area = cv2.contourArea(contour)
        if abs(ellipse_area/contour_area - 1) > 0.25:
            return False
        return True
    filtered = filter(is_like_balloon, filtered)

    filtered = list(filtered)
    if len(filtered) > 0:
        contour = max(filtered, key=lambda c: cv2.contourArea(c))
        contour_area = cv2.contourArea(contour)
        # find the center of the balloon
        mu = cv2.moments(contour)
        cx = int(mu['m10'] / mu['m00'])
        cy = int(mu['m01'] / mu['m00'])
        x = cx - CENTER_X
        y = -cy + CENTER_Y
        # find the rotation (in degrees) from camera center to target
        xrot = x / thresh.shape[1] * 82.6
        yrot = y / thresh.shape[0] * 82.6
        # find distance to target
        rect = cv2.fitEllipse(contour)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        center, size, angle = rect
        ellipse_area = np.pi * size[0] * size[1] / 4
        minoraxis = min(size)  # need a good shot of the balloon for this to make sense
        distance = (BALLOON_CENTER_DIAMETER_CM * FOCAL_LENGTH_PX) / minoraxis
        # find the height of the balloon (center vs camera center)
        height = distance * np.sin(yrot * np.pi/180)

        if debug is not None:
            cv2.line(debug, (0, CENTER_Y), (debug.shape[1]-1, CENTER_Y), (255,0,255), 1)
            cv2.line(debug, (CENTER_X, 0), (CENTER_X, debug.shape[0]-1), (255,0,255), 1)
            cv2.drawContours(debug, [contour], 0, color, 3)
            cv2.drawContours(debug, [box], 0, (127,0,127), 1)
            cv2.putText(debug, f"XR {xrot:.1f}deg", (cx-50,cy-20), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255,0,255))
            cv2.putText(debug, f"D {distance:.1f}cm", (cx-50,cy), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255,0,255))
            cv2.putText(debug, f"H {height:.1f}cm", (cx-50,cy+20), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255,0,255))
#            cv2.putText(debug, f"AR {ellipse_area/contour_area:.4f}", (cx-50,cy+40), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255,0,255))
#            cv2.putText(debug, f"Rd {max(size)/min(size):.4f}", (cx-50,cy+40), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255,0,255))

        return xrot, height, distance

    else:
        return None
