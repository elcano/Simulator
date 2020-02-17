
'''

Elcano Carla Simulator Capstone
UW Bothell, 2020

Advisor : Tyler Folsom

Team 1 : Zach Gale, Jonah Lim, Matthew Moscola, Francisco Navarro-Diaz
Team 2 : Colton Sellers, 

simulator.py

Version: 1.0

The main purposes of this program are:
    - Control creation of actors within Carla.
    - Retrieve simulated sensor data from actors and send to router board.
    - Interpret actuation data from router board and send actuation commands to Carla.

Much of the code that prepares the simulation (spawning actors and sensors) can be found in the examples
that come with the CARLA simulator download.

CARLA open-source simulator can be found here: http://Carla.org/

BEFORE RUNNING : 
** Change the default IP address to the address of the PC running Carla.
** Change COM used (USB port) to the one connected with the router board.

'''

#External imports
import glob
import os
import sys
import serial
import logging
import random
import time
import math
from data_logger import DataLogger

#import Carla and and Sensors
import Carla
import Sensors
import Elcano


#Wait for input before attempting to connect
print("Welcome to the Elcano Project Simulation")
input("Press enter when prepared to connect to server")

#Create the vehicle and spawn in server
trike = Elcano.Vehicle()
trike.initialize()

#Data Logger logging functions, not 100% sure how this operates
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

#Attempt to connect to the Carla server, timeout after 5 seconds
client = Carla.Client('localhost', 2000)
client.set_timeout(5.0)

#Get the world from the server
world = client.get_world()

#Enable headless mode
#settings = world.get_settings()
#settings.no_rendering_mode = True
#world.apply_settings(settings)

#Load Carlas blueprint library
blueprint_library = world.get_blueprint_library()

#Grab all the car blueprints from library
vehicle = blueprint_library.find('vehicle.bmw.isetta')

#Gather possible spawn points
spawn_points = world.get_map().get_spawn_points()
number_of_spawn_points = len(spawn_points)

#Set COM port for router communication
ser = serial.Serial('COM4',baudrate = 115200,timeout=1)

#CLI when starting script
print("Successful connection")     

#Spawns trike at spawn point
spawn = Carla.Transform(Carla.Location(x=15, y=20, z=5), Carla.Rotation(yaw=180))
actor = world.spawn_actor(vehicle, spawn)

#Logging Data from the actor
logger = DataLogger(actor)


# Attach nmeaSensor to trike (speed directly taken from trike actor)
blueprint = world.get_blueprint_library().find('sensor.other.gnss')
transform = Carla.Transform(Carla.Location(x=0.8, z=1.7))
nmeaSensor = world.spawn_actor(blueprint,transform,actor)
sensors.append(nmeaSensor)


#speedSensor = world.spawn_actor(blueprint,transform,actor)

### SET SIM VIEWPOINT TO VEHICLE ####
world.get_spectator().set_transform(actor.get_transform())

try:
    time.sleep(5)
    ser.write('f'.encode('utf-8'))  #Notify Due that system is starting
    
    ##### FOR GPS SENSOR USAGE ####
    logger.setListen()
    logger.setNmea('Test@')  # Fill private member to avoid error
    #nmeaSensor.listen(lambda data: nmeaGPS.consoleout(data,logger))
    ##########################
    
    while True:
        # Wait for ready queue from due
        if ser.in_waiting:
            ### FOR GPS SENSOR USAGE (Set the stop variable to short the listener func) ###
            logger.setStopListen()
            #nmeaSensor.stop()
            ###########
            
            ''' 
            ADD SERIAL READS FOR ACTUATION HERE 
            
            Currently just clears an arbitrary char in buffer sent from
            router Due
            '''

            ## Receive in order: throttle, steer, brake
            t = float(ser.readline().decode('ASCII'))
            s = float(ser.readline().decode('ASCII'))
            b = float(ser.readline().decode('ASCII'))
            
            actor.apply_control(Carla.VehicleControl(throttle=t,steer=s,brake=b))

            ''' 
            Finish processing actuation commands here
            
            Here's how data is sent from Due:
            - Throttle : float (-1 to 1)
            - Steering : float (-1 to 1)
            - Brakes   : float (0 for off 0.3 for on) <- because current implementation of brake
                is siimply on/off.  Feel free to change on value of 0.3.
            '''
            
            ### ACCESS/SEND LAT/LONG FROM LAST TICK ###
            ### Can use for location if disabling GPS Sensor

            #geo = world.get_map().transform_to_geolocation(logger.actorId.get_location())
            #msg = geo.__str__() + '@'
            #logger.setNmea(msg)
            ###########
            
            ### ACCESS/SEND X/Y/Z FROM LAST TICK  #####
            ### Can use for location if disabling GPS Sensor

            #msg = logger.actorId.get_location().__str__() + '@'
            #logger.setNmea(msg)
            ########
            
            # Get the speed of Trike
            getSpeed(logger.actorId, logger)
            
            # Send most current data
            # ORDER MATTERS FOR ARDUINO CODE
            logger.sendCyclometer(ser)
            logger.sendNmea(ser)
            
            ### FOR SENSOR USAGE ###
            logger.setListen()
            #nmeaSensor.listen(lambda data: nmeaGPS.consoleout(data,logger))
            #############

except KeyboardInterrupt:
    print('\ndestroying %d sensors' % len(sensors))
    for x in sensors:
        Carla.command.DestroyActor(x)
    print('\ndestroying vehicle')
    actor.destroy()
    sys.exit()
    
'''
Executes each time CARLA updates sensor data.  Obtains the speed of actor it is attached to.
'''

    
if __name__ == '__main__':

    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        print('\ndone.')