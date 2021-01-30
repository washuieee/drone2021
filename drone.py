from easytello import tello
import time
import cv2
import threading

from vision import Vision


class Drone:
    def __init__(self):
        self.drone = tello.Tello()
        self.vision = Vision(self.drone)
        # self.move = threading.Thread(target=self.path, args=).start() TODO: need to decide if vision is always running and how to pathfind

    def start(self):
        self.drone.streamon()
        self.takeoff()

    def path(self):  # TODO: decide what args necessary and how to get them from vision
        pass
