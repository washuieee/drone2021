from easytello import tello

from drone import Drone


def main():

    tempname = Drone()
    tempname.start()

    for i in range(4):
        tempname.drone.forward(20)
        tempname.drone.cw(50)

    tempname.drone.land()


if __name__ == "__main__":
    main()
