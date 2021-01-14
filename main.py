from easytello import tello

drone = tello.Tello()

drone.streamon()

drone.takeoff()

for i in range(4):
    drone.forward(20)
    drone.cw(50)

drone.land()
