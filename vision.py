from easytello import tello
import time
import cv2
import numpy as np
import threading
import queue
import time


def start(q, order):
    # Start UDP server to receive video from Tello
    cap = cv2.VideoCapture('udp://192.168.10.1:11111')
    i = 0

    cv2.namedWindow("Display")

    try:
        # Main vision loop
        while cap.isOpened():
            # Read image
            ret, frame = cap.read()

            process(q, frame)

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
    cv2.destroyAllWindows()
    q.put({'type': 'quit'})


last_frame_time = None
def process(q, frame):
    global last_frame_time
    # Processing...
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    threshR = cv2.bitwise_or(
            cv2.inRange(hsv, (0, 150, 100), (20, 255, 255)),
            cv2.inRange(hsv, (160, 150, 100), (180, 255, 255)))
    threshG = cv2.inRange(hsv, (45-10, 50, 100), (45+10, 200, 255))
    threshB = cv2.inRange(hsv, (105-10, 150, 0), (105+10, 255, 255))
    threshY = cv2.inRange(hsv, (25-10, 150, 150), (25+10, 255, 255))

    display = frame.copy()
    results = {
            'type': 'data',
            'red': track_balloon(threshR, display),
            'green': track_balloon(threshG, display),
            'blue': track_balloon(threshB, display),
            'yellow': track_balloon(threshY, display),
            }

    # Send results to control loop
    try:
        q.put(results, block=False)
    except queue.Full:
        pass

    # Debugging client display
    now = time.time()
    if last_frame_time is not None:
        interframe = now - last_frame_time
        fps = int(1/interframe)
        cv2.putText(display, f"{fps}FPS - Press ESC to land drone and exit",
                (20,20), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255,0,255))
    last_frame_time = now
    cv2.imshow('Display', display)


CONTOUR_MIN_AREA = 1000
BALLOON_CENTER_DIAMETER_CM = 33.422  # circ 105cm
FOCAL_LENGTH_PX = 711  # curve fit result
def track_balloon(thresh, debug):
    # Find contours in binary image
    contours, hierarchy = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filtered = [c for c in contours if cv2.contourArea(c) > CONTOUR_MIN_AREA]
    if len(filtered) > 0:
        contour = max(filtered, key=lambda c: cv2.contourArea(c))
        # find the center of the balloon
        mu = cv2.moments(contour)
        cx = int(mu['m10'] / mu['m00'])
        cy = int(mu['m01'] / mu['m00'])
        x = cx - thresh.shape[1]//2
        y = -cy + thresh.shape[0]//2
        # find the rotation (in degrees) from camera center to target
        xrot = x / thresh.shape[1] * 82.6
        yrot = y / thresh.shape[0] * 82.6
        # find distance to target
        rect = cv2.fitEllipse(contour)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        center, size, angle = rect
        minoraxis = min(size)  # need a good shot of the balloon for this to make sense
        distance = (BALLOON_CENTER_DIAMETER_CM * FOCAL_LENGTH_PX) / minoraxis
        # find the height of the balloon (center vs camera center)
        height = distance * np.sin(yrot)

        if debug is not None:
            cv2.drawContours(debug, [contour], 0, (255,0,255), 3)
            cv2.drawContours(debug, [box], 0, (127,0,127), 1)
            cv2.putText(debug, f"XR {xrot:.1f}deg", (cx-50,cy-20), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255,0,255))
            cv2.putText(debug, f"D {distance:.1f}cm", (cx-50,cy), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255,0,255))
            cv2.putText(debug, f"H {height:.1f}cm", (cx-50,cy+20), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255,0,255))

        return xrot, height, distance

    else:
        return None
