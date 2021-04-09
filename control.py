import tellopy
import cv2
import numpy as np
import queue
import platform
import subprocess
import time
import vision
import traceback
import enum
import logging

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


class FinalAttackState(enum.Enum):
    THRUST = 1
    REVERSE = 2
    CONFIRM = 3


status = None

def droneloop():
    logging.basicConfig(filename=f"{time.time()}.txt", filemode='w',
            level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    logger = logging.getLogger(__name__)

    resting_height = 6

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

        logger.info("Connected to drone")
        statusmessageui("Connected to drone!")
        handlaunchui(drone)
        logger.info("Hand launch completed")
        statusmessageui("Video feed starting...")


        v = vision.Vision(record=True)
        q = queue.Queue(maxsize=1)
        v.open_input(drone.get_video_stream())

       
        def droneclear():
            if q.full():
                q.get()
            v.check_new_frame(q, str(status))

        def dronesleep(t):
            expiry = time.time() + t
            while time.time() < expiry:
                v.check_new_frame(q, str(status))
            droneclear()

        # Wait for video to stabilize
        dronesleep(10)
        logger.info("Vision presumed stable")

        last_xrot = 0
        final_state = None
        final_target = None
        final_timer = 0
        start_time = time.time()

        # Main control loop
        while len(remainingBalloons) > 0:
            target = remainingBalloons[0]

            # Get vision sol'n
            while q.empty():
                v.check_new_frame(q, str(status))
            data = q.get()

            # Check for early exit
            if data['type'] == 'quit':
                logger.info("User initiated shutdown by ESC")
                break

            logger.info("Vision solutions: "
                    + ",".join({c for c in {'red','green','blue','yellow'} if data[c] is not None}))

            # Check for final attack state
            if final_state is not None:
                logger.info(f"In final attack state {final_state}")
                if final_state == FinalAttackState.THRUST:
                    if time.time() < final_timer + 6:
                        # move forward slowly for 6 seconds
                        drone.forward(6)
                    else:
                        # next state transition
                        drone.forward(0)
                        final_state = FinalAttackState.REVERSE
                        final_timer = time.time()

                elif final_state == FinalAttackState.REVERSE:
                    if time.time() < final_timer + 1:
                        # back up quickly for 1 second
                        drone.backward(20)
                    else:
                        # next state transition
                        drone.backward(0)
                        final_state = FinalAttackState.CONFIRM
                        final_timer = time.time()

                elif final_state == FinalAttackState.CONFIRM:
                    # check vision to make sure we popped it
                    if data[final_target] is None:
                        # we did
                        remainingBalloons.pop(0)
                        # if this list gets to len 0, then it will land next loop iter
                    else:
                        # damn, guess we gotta go for it again
                        pass
                    final_state = None

                continue

            # If we only have 20 seconds left, pop whatever we can find
            if data[target] is None and (time.time() - start_time) > 160:
                for c in {'red', 'green', 'blue', 'yellow'}:
                    if data[c] is not None:
                        target = c
                        break

            # Check for search state
            if data[target] is None:
                logger.info(f"Current target {target} not in sight")
                drone.right(0)
                drone.forward(6)
                # Spin clockwise slowly (or in the direction of last seen balloon
                if last_xrot < 0:
                    drone.counter_clockwise(20)
                else:
                    drone.clockwise(20)
                # Ascend to "10"
                if status.height < resting_height:
                    drone.up(20)
                else:
                    drone.up(0)
                continue

            # Align with balloon
            xrot, height, distance = data[target]
            rot_ontarget = False
            height_ontarget = False

            logger.info(f"Tracking target {target}: xrot={xrot}deg height={height}cm, dist={distance}cm")

            max_xrot = 4
            if distance < 50:
                max_xrot = 8

            # Rotate to face the balloon if needed
            if xrot < max_xrot * -1:
                drone.counter_clockwise(20)
            elif xrot > max_xrot:
                drone.clockwise(20)
            else:
                drone.clockwise(0)
                rot_ontarget = True

            elevSpeeed = 8
            if distance < 100:
                elevSpeeed = 25

            # change elevation to match balloon if needed
            if height < -17: # increase this to favor attacking from bottom
                drone.down(elevSpeeed)
            elif height > 17: # decrease this to favor attacking from top
                drone.up(elevSpeeed)
            else:
                drone.up(0)
                height_ontarget = True

            # head in for the kill
            if distance > 100:
                logger.info("Moving forward, 1st stage")
                drone.forward(20)
            elif distance > 50 and rot_ontarget and height_ontarget:
                logger.info("Moving forward, locked on")
                drone.forward(20)
            elif rot_ontarget and height_ontarget:
                print('\a')
                logger.info("Taking the shot")
                # final kill for 6 seconds
                final_state = FinalAttackState.THRUST
                final_timer = time.time()
                final_target = target
            else:
                logger.info("Still aligning with target")
                drone.forward(0)

            last_xrot = xrot
      
        logger.info("Landing drone")
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

    logger.info("Connection closed")


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
