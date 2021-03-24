from easytello import tello
import cv2
import multiprocessing as mp
import queue
import platform
import subprocess
import time
import vision
import argparse

parser = argparse.ArgumentParser(description='Replay vision')
parser.add_argument('file')
args = parser.parse_args()
q = mp.Queue(maxsize=1)

vision.start(q, '', args.file)
