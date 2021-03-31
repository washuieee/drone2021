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
v = vision.Vision(record=False)
v.frame_skip = 0
q = queue.Queue(maxsize=1)
v.open_input(args.file)
status = ""
while True:
    v.check_new_frame(q, status)
    try:
        data = q.get(block=False)
        if data['type'] == 'quit':
            break
    except queue.Empty:
        pass
