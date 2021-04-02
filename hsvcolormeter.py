import cv2

import argparse

parser = argparse.ArgumentParser(description='Replay vision')
parser.add_argument('file')
args = parser.parse_args()

image = cv2.imread(args.file)
hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

def select(event, x, y, flags, param):
    print(f"H {hsv[y, x, 0]} S {hsv[y,x,1]} V {hsv[y,x,2]}")

cv2.namedWindow("Display")
cv2.setMouseCallback("Display", select)
while True:
    cv2.imshow("Display", image)
    key = cv2.waitKey(50)
    if key == 27:
        break
