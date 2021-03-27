from easytello import tello
import cv2
import multiprocessing as mp
import queue
import platform
import subprocess
import time
import vision

# Make the drone land after 20 seconds in case it went rogue
EXPERIMENT_TIMEOUT = 60*3

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

    bat = drone.get_battery()
    print(f"Battery level: {bat}")


    # Wait a bit for vision to stabilize
    time.sleep(10)

    drone.takeoff()
    time.sleep(1)

    drone.up(150)

    start_time = time.time()

    time.sleep(3)
    q.get(False)

    # Main control loop
    while True:
        current_time = time.time()
        try:
            # get new vision data (wait)
            data = q.get(True, 1.0)

            # quit by pressing ESC on vision window
            if data['type'] == 'quit':
                break;

            colors = ['red', 'green', 'blue', 'yellow']
            # track the closest balloon
            balloons = [data[color] for color in colors if data[color] is not None]

            # align ourselves with the balloon
            if len(balloons) > 0:
                track = min(balloons, key=lambda t: t[2])
                xrot, height, distance = track
                # rotate to face the balloon if needed
                if xrot < -6:
                    # every drone actuation command blocks until the drone finishes moving
                    drone.ccw(int(abs(xrot)))
                elif xrot > 6:
                    drone.cw(int(abs(xrot)))
                # change elevation to match balloon if needed
                elif height < -20:
                    drone.down(max(int(abs(height * 0.75)), 20))
                elif height > 20:
                    drone.up(max(int(abs(height * 0.75)), 20))
                # head in for the kill
                elif distance > 100:
                    drone.forward(100)
                elif distance > 20:
                    drone.forward(int(abs(distance)))
                else:
                    drone.forward(20)
                # sleep briefly so vision doesn't get motion blur
                time.sleep(3)
                # ignore the stale vision frame
                q.get(False)

        except queue.Empty:
            print("Vision is not responding")
        except KeyboardInterrupt:
            print("Graceful shutdown!")
            break
        if current_time - start_time > EXPERIMENT_TIMEOUT:
            print("Experiment timed out")
            break

    print('Landing drone')
    drone.land()
        

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
