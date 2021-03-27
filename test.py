from easytello import tello
import cv2
import multiprocessing as mp
import queue
import platform
import subprocess
import time
import vision

def droneloop():
    # Wait for the user to switch WiFi networks
    while ping('192.168.10.1') == False:
        print('Drone is offline, retrying...')
    print('Connected!')

    # Connect to Tello
    drone = tello.Tello()
    drone.command()

    # Start the vision subprocess
    q = mp.Queue(maxsize=1)
    p = mp.Process(target=vision.start, args=(q, None))
    p.start()

    time.sleep(0.2)

    drone.send_command('streamon')

    # Wait a bit for vision to stabilize
    time.sleep(10)

    start_time = time.time()

    # Main control loop
    while True:
        current_time = time.time()
        try:
            data = q.get(True, 1.0)
            print(data)
            if data['type'] == 'quit':
                break;
        except queue.Empty:
            print("no new vision data")
        except KeyboardInterrupt:
            print("Graceful shutdown!")
            break


    print('Cleaning up')
    drone.send_command('streamoff')

    # Stop vision
    p.terminate()


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
