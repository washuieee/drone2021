import numpy as np
import cv2
import glob

import argparse

parser = argparse.ArgumentParser(description='Replay vision')
parser.add_argument('file')
args = parser.parse_args()

# termination criteria
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
objp = np.zeros((6*9,3), np.float32)
objp[:,:2] = np.mgrid[0:9,0:6].T.reshape(-1,2)

# Arrays to store object points and image points from all the images.
objpoints = [] # 3d point in real world space
imgpoints = [] # 2d points in image plane.

cap = cv2.VideoCapture(args.file)
while cap.isOpened():
    retval, img = cap.read()
    if img is None or img.size == 0:
        break
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    # Find the chess board corners
    ret, corners = cv2.findChessboardCorners(gray, (9,6))

    # If found, add object points, image points (after refining them)
    if ret == True:
        objpoints.append(objp)

        corners2 = cv2.cornerSubPix(gray,corners,(11,11),(-1,-1),criteria)
        imgpoints.append(corners2)

        # Draw and display the corners
        img = cv2.drawChessboardCorners(img, (9,6), corners2,ret)
        cv2.imshow('img',img)
        key = cv2.waitKey(10)
        if key == 27:
            break
    else:
        print("Nothing found in this frame")
        cv2.imshow('img',img)
        key = cv2.waitKey(10)
        if key == 27:
            break

cv2.destroyAllWindows()
imgpoints = imgpoints[::10]
objpoints = objpoints[::10]
print(f"Starting calibration with {len(objpoints)} object pts")
retval, cameraMatrix, distCoeffs, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1],None,None)
print("Camera matrix")
print(cameraMatrix)
print("Distortion coefficients")
print(distCoeffs)
print("Rotation vectors")
print(rvecs)
print("Translation vectors")
print(tvecs)
np.savez("calibration.npz", cameraMatrix=cameraMatrix, distCoeffs=distCoeffs, rvecs=rvecs, tvecs=tvecs)


