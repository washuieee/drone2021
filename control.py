import tellopy
import cv2
import numpy as np
import queue
import platform
import subprocess
import time
import vision
import traceback

# Make the drone land after 20 seconds in case it went rogue
EXPERIMENT_TIMEOUT = 60*3

def orderselectui():
    selections = []
    regions = {
            'red': ((20,60), (20+150, 60+150)),
            'green': ((190,60), (190+150, 60+150)),
            'blue': ((360,60), (360+150, 60+150)),
            'yellow': ((530,60), (530+150, 60+150)),
            }
    def select(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            for sel, ((sx, sy), (ex, ey)) in regions.items():
                if sel in selections:
                    continue
                if sx <= x <= ex and sy <= y <= ey:
                    selections.append(sel)
                    return

    def draw():
        display = np.ones((230, 700, 3), dtype=np.uint8)*255
        cv2.putText(display, f"Select colors in popping order", (40,40), cv2.FONT_HERSHEY_COMPLEX, 1, (255,0,255))
        cv2.rectangle(display, *regions['red'], (0,0,255),-1)
        cv2.rectangle(display, *regions['green'], (0,255,0),-1)
        cv2.rectangle(display, *regions['blue'], (255,0,0),-1)
        cv2.rectangle(display, *regions['yellow'], (0,255,255),-1)
        for i, sel in enumerate(selections):
            cv2.rectangle(display, *regions[sel], (0,0,0), 3)
            pt = regions[sel][0]
            pt = (pt[0] + 70, pt[1] + 70)
            cv2.putText(display, f"{i+1}", pt, cv2.FONT_HERSHEY_COMPLEX, 1, (0,0,0))
        cv2.imshow('Display', display)
        key = cv2.waitKey(50)
        if key == 27:
            raise Exception("Not all order selections made")

    cv2.namedWindow("Display")
    cv2.setMouseCallback("Display", select)
    while len(selections) < 4:
        draw()
    return selections


def statusmessageui(message):
    display = np.ones((230, 700, 3), dtype=np.uint8)*255
    cv2.putText(display, message, (40,40), cv2.FONT_HERSHEY_COMPLEX, 1, (255,0,255))
    cv2.imshow('Display', display)
    cv2.waitKey(1)


def handlaunchui(drone):
    display = np.ones((230, 700, 3), dtype=np.uint8)*255
    cv2.putText(display, "Place the drone in the palm on your hand, then", (40,40), cv2.FONT_HERSHEY_COMPLEX, 1, (255,0,255))
    cv2.putText(display, "press SPACEBAR when ready.", (40,80), cv2.FONT_HERSHEY_COMPLEX, 1, (255,0,255))
    cv2.putText(display, "After the propellers start,", (40,120), cv2.FONT_HERSHEY_COMPLEX, 1, (255,0,255))
    cv2.putText(display, "toss the drone up.", (40,160), cv2.FONT_HERSHEY_COMPLEX, 1, (255,0,255))
    cv2.imshow('Display', display)
    key = cv2.waitKey()
    if key == 32:
        drone.throw_and_go()
        display = np.ones((230, 700, 3), dtype=np.uint8)*255
        cv2.putText(display, "After the propellers start,", (40,40), cv2.FONT_HERSHEY_COMPLEX, 1, (255,0,255))
        cv2.putText(display, "toss the drone up.", (40,80), cv2.FONT_HERSHEY_COMPLEX, 1, (255,0,255))
        cv2.putText(display, f"Do this within 5 seconds!", (40,120), cv2.FONT_HERSHEY_COMPLEX, 1, (255,0,255))
        cv2.imshow('Display', display)
        cv2.waitKey(1)
        time.sleep(5)
    else:
        raise Exception("Early quit")


status = None

def droneloop():
    # Get the configuration for this match
    remainingBalloons = orderselectui()
   
    statusmessageui("Waiting for WiFi network switch...")
    # Wait for the user to switch WiFi networks
    while ping('192.168.10.1') == False:
        print('Drone is offline, retrying...')
    print('Connected!')

    statusmessageui("Connecting to drone...")

    def handler(event, sender, data, **args):
        global status
        drone = sender
        if event is drone.EVENT_FLIGHT_DATA:
            status = data

    # Connect to Tello
    drone = tellopy.Tello()

    try:
        drone.subscribe(drone.EVENT_FLIGHT_DATA, handler)

        drone.connect()
        drone.wait_for_connection(60.0)

        statusmessageui("Connected to drone!")

        v = vision.Vision(record=True)
        q = queue.Queue(maxsize=1)
        v.open_input(drone.get_video_stream())

        handlaunchui(drone)
        statusmessageui("Video feed starting...")

        
        def dronesleep(t):
            expiry = time.time() + t
            while time.time() < expiry:
                v.check_new_frame(q, status)
            if q.full():
                q.get()
            v.check_new_frame(q, status)

        # Wait for video to stabilize
        dronesleep(10)

        drone.up(20)

        dronesleep(1.5)

        print("Initial video stabilization finished...")

        # Main control loop
        while len(remainingBalloons) > 0:
            target = remainingBalloons[0]

            # Get vision sol'n
            while q.empty():
                v.check_new_frame(q, status)
            data = q.get()
            if data['type'] == 'quit':
                print("ESC")
                break
            elif data[target] is None:
                print(f"Can't see {target} balloon")
                # Spin clockwise slowly
                drone.right(0)
                drone.forward(0)
                drone.up(0)
                drone.clockwise(20)
                continue
            # Align with balloon
            xrot, height, distance = data[target]
            rot_ontarget = False
            height_ontarget = False

            # Rotate to face the balloon if needed
            if xrot < -3:
                # Drone actuation commands are now non-blocking
                drone.counter_clockwise(10)
            elif xrot > 3:
                drone.clockwise(10)
            else:
                drone.clockwise(0)
                rot_ontarget = True

            # change elevation to match balloon if needed
            if height < -20:
                drone.down(20)
            elif height > 20:
                drone.up(20)
            else:
                drone.up(0)
                height_ontarget = True

            # head in for the kill
            if distance > 100:
                print('slow', distance)
                drone.forward(20)
            elif distance > 40:
                if rot_ontarget and height_ontarget:
                    drone.forward(50)
                else:
                    drone.forward(0)
            else:
                print('final', xrot, height, distance)
                # final kill
                drone.forward(75)
                dronesleep(5)
                remainingBalloons.pop(0)
                drone.backward(30)
                dronesleep(8)
                drone.up(20)
                dronesleep(2)
                drone.up(0)
       
        print("Landing")
        cv2.destroyAllWindows()
        drone.right(0)
        drone.forward(0)
        drone.up(0)
        drone.clockwise(0)
        drone.land()
        time.sleep(5)
    except Exception as ex:
        traceback.print_exc()
    finally:
        drone.quit()


def ping(host):
    """
    Returns True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP) request even if the host name is valid.
    """

    # Option for the number of packets as a function of
    param = '-n' if platform.system().lower()=='windows' else '-c'

    # Building the command. Ex: "ping -c 1 google.com"
    command = ['ping', param, '1', host]

    return subprocess.call(command) == 0


if __name__ == "__main__":
    droneloop()
