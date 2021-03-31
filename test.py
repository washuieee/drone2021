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


def droneloop():
    # Wait for the user to switch WiFi networks
    while ping('192.168.10.1') == False:
        print('Drone is offline, retrying...')
    print('Connected!')

    status = None
    def handler(event, sender, data, **args):
        drone = sender
        if event is drone.EVENT_FLIGHT_DATA:
            status = str(data)

    # Connect to Tello
    drone = tellopy.Tello()

    try:
        drone.subscribe(drone.EVENT_FLIGHT_DATA, handler)

        drone.connect()
        drone.wait_for_connection(60.0)

        v = vision.Vision(record=True)
        q = queue.Queue(maxsize=1)
        v.open_input(drone.get_video_stream())

        
        # Wait for video to stabilize
        expiry = time.time() + 10 
        while time.time() < expiry:
            v.check_new_frame(q, status)

        print("Initial video stabilization finished...")

        # Main control loop
        while True:
            # Get vision sol'n
            while q.empty():
                v.check_new_frame(q, status)
            data = q.get()
            if data['type'] == 'quit':
                print("ESC")
                break
       
        print("Landing")
        cv2.destroyAllWindows()
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
