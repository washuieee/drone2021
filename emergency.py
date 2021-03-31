from easytello import tello
import cv2
import multiprocessing as mp
import queue
import platform
import subprocess
import time
import vision

def droneloop():
    # Connect to Tello
    drone = tello.Tello()
    drone.command()
    drone.emergency()
    drone.send_command('streamoff')

if __name__ == "__main__":
    droneloop()
