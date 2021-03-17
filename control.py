from easytello import tello
import cv2
import multiprocessing as mp
import queue
import platform
import subprocess
import time
import vision

def droneloop():
    # Get the configuration for this match
    order = input('Input balloon popping order e.g. RGBY  >')

    # Wait for the user to switch WiFi networks
    while ping('192.168.10.1') == False:
        print('Drone is offline, retrying...')
    print('Connected!')

    # Connect to Tello
    drone = tello.Tello()
    drone.command()
    drone.send_command('streamon')

    # Start the vision subprocess
    q = mp.Queue(maxsize=1)
    p = mp.Process(target=vision.start, args=(q, order))
    p.start()

    drone.takeoff()
    start_time = time.time()

    # Main control loop
    while True:
        current_time = time.time()
        try:
            data = q.get(True, 1.0)
            print("got data")
            if data['red'] is not None:
                x, y = data['red']
                print(f"Red balloon at {data['red']}")
                xrot = x / 960 * 82.6
                print(xrot)
                if xrot < -2:
                    drone.ccw(int(abs(xrot)))
                elif xrot > 2:
                    drone.cw(int(abs(xrot)))
                else:
                    print("Right on target")
                    drone.forward(50)
                time.sleep(2)
                # we went to sleep, so ignore the stale vision frame
                q.get(False)
            if data['type'] == 'quit':
                break;
        except queue.Empty:
            print("no new vision data")
        except KeyboardInterrupt:
            print("Graceful shutdown!")
            break
        if current_time - start_time > 20:
            break

    drone.land()
        

    print('Cleaning up')
    drone.send_command('streamoff')
    p.join()


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
