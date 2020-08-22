import math
import Carla
import weakref
import pygame
import numpy as np

IMG_WIDTH = 640
IMG_HEIGHT = 480

class SimulatedVehicle:
    """
    Vehicle class for simulator, acts as the vehicle object in carla. Contains
    all the sensors we place on vehicle in the simulator and their data. Will
    be used to execute commands and give data on vehicle.
    """

    #Constructor for vehicle class
    def __init__(self, world):

        self.world = world

        #Variables related to simulated vehicle
        self.sensors = []
        self.speed = 0
        self.steeringangle = 0
        self.throttle = 0
        self.steering = 0
        self.braking = 0
        self.reverse = False


        #Load Carlas blueprint library
        self.blueprint_library = self.world.get_blueprint_library()

        #Grab all the car blueprints from library
        vehicle = self.blueprint_library.find('vehicle.bmw.isetta')

        #Spawns trike at spawn point
        spawn = Carla.Transform(Carla.Location(x=34, y=7, z=1), Carla.Rotation(yaw=0))
        self.actor = self.world.spawn_actor(vehicle, spawn)

        # Set up the sensors.
        self.GNSSSensor = GNSSSensor(self.world, self.actor)
        self.IMUSensor = IMUSensor(self.world, self.actor)
        self.RGBSensor = RGBSensor(self.world, self.actor)


    #For destroying the vehicle in simulator
    def destroy(self):
    
        self.GNSSSensor.sensor.destroy()
        self.IMUSensor.sensor.destroy()
        self.RGBSensor.sensor.destroy()

        self.actor.destroy()
        
    def getSpeed(self):
        #Convert velocity into speed (m/s)
        velocity = self.actor.get_velocity()
        self.speed = math.sqrt(velocity.x**2 + velocity.y**2+velocity.z**2)
        return self.speed

    def getSteeringAngle(self):
        #Convert steering -1 to 1 to -90 to 90 degrees
        self.steeringangle = self.steering*90
        return self.steeringangle

    def updateThrottle(self, t):
        self.throttle = t
        self.actor.apply_control(Carla.VehicleControl(throttle=self.throttle,steer=self.steering,brake=self.braking,reverse=self.reverse))

    def updateSteering(self, s):
        
        self.steering = s
        self.actor.apply_control(Carla.VehicleControl(throttle=self.throttle,steer=self.steering,brake=self.braking,reverse=self.reverse))
    
    def updateBraking(self, b):
        self.braking = b
        self.actor.apply_control(Carla.VehicleControl(throttle=self.throttle,steer=self.steering,brake=self.braking,reverse=self.reverse))

    def updateReverse(self, r):
        self.reverse = r
        self.actor.apply_control(Carla.VehicleControl(throttle=self.throttle,steer=self.steering,brake=self.braking,reverse=self.reverse))


################################# SENSORS  #####################################

# ==============================================================================
# -- GNSSSensor ----------------------------------------------------------------
# ==============================================================================

class GNSSSensor:
    """
    Sensor class for collecting GNSS data from Carla
    """

    def __init__(self, world, actor):


        # Init default values
        self.latitude = 0
        self.longitude = 0

        # Attach nmeaSensor to trike (speed directly taken from trike actor)
        blueprint = world.get_blueprint_library().find('sensor.other.gnss')
        transform = Carla.Transform(Carla.Location(x=1.0, z=2.8))
        self.sensor = world.spawn_actor(blueprint,transform,attach_to=actor)

        #To avoid circular ref we are going to use a weak reference.
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda event: GNSSSensor._on_gnss_event(weak_self, event))

    #Storing the gps info on every update
    @staticmethod
    def _on_gnss_event(weak_self, event):
        """
        To store the GNSS data every time it changes in CARLA
        """

        self = weak_self()
        if not self:
            return

        self.latitude = event.latitude
        self.longitude = event.longitude
        self.altitude = event.altitude
    
        
# ==============================================================================
# -- IMUSensor -----------------------------------------------------------------
# ==============================================================================

class IMUSensor(object):
    """
    Sensor class for collecting IMU data from Carla
    """

    def __init__(self, world, actor):

        #Default values
        self.accelerometer = (0.0, 0.0, 0.0)
        self.gyroscope = (0.0, 0.0, 0.0)
        self.compass = 0.0
        self.radiansCompass = 0.0

        # Attach the sensor to the vehicle
        bp = world.get_blueprint_library().find('sensor.other.imu')
        self.sensor = world.spawn_actor(bp, Carla.Transform(), attach_to=actor)


        # We need to pass the lambda a weak reference to self to avoid circular
        # reference.
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda sensor_data: IMUSensor._IMU_callback(weak_self, sensor_data))

    @staticmethod
    def _IMU_callback(weak_self, sensor_data):
        """
        To store the IMU data every time it changes in CARLA
        """

        self = weak_self()
        if not self:
            return

        limits = (-99.9, 99.9)
        self.accelerometer = (
            max(limits[0], min(limits[1], sensor_data.accelerometer.x)),
            max(limits[0], min(limits[1], sensor_data.accelerometer.y)),
            max(limits[0], min(limits[1], sensor_data.accelerometer.z)))
        self.gyroscope = (
            max(limits[0], min(limits[1], math.degrees(sensor_data.gyroscope.x))),
            max(limits[0], min(limits[1], math.degrees(sensor_data.gyroscope.y))),
            max(limits[0], min(limits[1], math.degrees(sensor_data.gyroscope.z))))
        self.compass = math.degrees(sensor_data.compass)
        self.radiansCompass = sensor_data.compass


# ==============================================================================
# -- RGBSensor -----------------------------------------------------------------
# ==============================================================================

class RGBSensor(object):
    '''
    To process and return a frame from the RGBSensor in Carla
    '''
    def __init__(self, world, actor):

        bp = world.get_blueprint_library().find('sensor.camera.rgb')
        bp.set_attribute('image_size_x', str(IMG_WIDTH))
        bp.set_attribute('image_size_y', str(IMG_HEIGHT))
        bp.set_attribute('fov', '110')
        self.sensor = world.spawn_actor(bp, Carla.Transform(Carla.Location(x=2.5, z=0.7)), attach_to=actor)

        weak_self = weakref.ref(self)
        self.sensor.listen(lambda raw_data: RGBSensor._process_rgb(weak_self, raw_data))

    @staticmethod
    def _process_rgb(weak_self, raw_data):

        self = weak_self()
        if not self:
            return

        raw_input = np.array(raw_data.raw_data)
        input_frame = raw_input.reshape((IMG_HEIGHT, IMG_WIDTH, 4))
        self.frame = input_frame[:, :, :3]
        
    def get_frame(self):
        return self.frame


