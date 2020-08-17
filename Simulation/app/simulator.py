
'''

Elcano Carla Simulator Capstone
UW Bothell, 2020

Advisor : Tyler Folsom

Team 2019 : Zach Gale, Jonah Lim, Matthew Moscola, Francisco Navarro-Diaz
Team 2020 : Colton Sellers, Brandon Thompson, Mariah Files, Will Song, Launnie Ginn

simulator.py

Version: 2.0

The main purposes of this program are:
    - Create client connection with display to Carla.
    - Control creation of actors within Carla.
    - Collect data from actor sensors and send to router board.
    - Interpret actuation data from router board and send actuation commands to Carla.


Much of the code that prepares the simulation (spawning actors and sensors) can be found in the examples
that come with the CARLA simulator download.

CARLA open-source simulator can be found here: http://Carla.org/

'''

# External imports
import sys
import logging
import pygame
import datetime
import time
import math
import os
import numpy as np
import weakref
from pygame.locals import K_r
from pygame.locals import K_p

# Local imports
import Carla
from Carla import ColorConverter as cc
import Elcano
from Elcano import custom_controller


def main(COMPort='COM7', host='localhost', port=2000, select_controller='default'):
    """
    Take in settings from form or command line, start logging, build client object
    enter control loop

    Accepted Params:
    COMPort - The native port on the routerboard Due to communicate through (Default = COM14)
    Host - IP address of the Carla server to connect to (Default = localhost)
    Port - Port on the host to connect to (Default = 2000)
    """

    # Set logging level
    logging.basicConfig(
        format='%(levelname)s: %(message)s', level=logging.INFO)
    logging.info('listening to server %s:%s', host, port)

    # Initialize some important variables
    client = None
    controller = None

    try:
        # Create client object to interact with server
        client = Client(host, port)
        client.connectToVehicle()
        print('success')

        # Define the controller of the vehicle
        # Intend to add the option for manual control here later with a given param
        if select_controller == 'custom_controller':
            controller = custom_controller.Autopilot(client.vehicle, False)
        else:
            controller = Elcano.RouterboardInterface(COMPort, client.vehicle)

        # Give it one second to catch up, I find without this sometimes I will run into issues
        time.sleep(1)

        # Continously render
        while True:
            client.clock.tick_busy_loop(60)
            client.render()
            try:
                controller.mainloop(client.getKeys(), client.states)
            except:
                print("Unexpected error:", sys.exc_info())
                raise

    finally:
        # Once we are done, destroy the client and controller
        if client is not None:
            client.destroy()

        if controller is not None:
            controller.destroy()

        return


# ==============================================================================
# -- Client ---------------------------------------------------------------------
# ==============================================================================


class Client(object):
    """
    Client acts as the connection to Carla.
    It owns the display, camera_manager, hud, and the vehicle

    Accepted Params:
    Host - IP address of the Carla server to connect to (Default = localhost)
    Port - Port on the host to connect to (Default = 2000)
    """

    def __init__(self, host, port):

        # Initialize some variables
        self.camera_manager = None
        self.vehicle = None

        # Attempt to connect to the Carla server, timeout after 5 seconds
        self.client = Carla.Client(host, port)
        self.client.set_timeout(5.0)

        # Start pygame and build window and hud
        pygame.init()
        pygame.font.init()

        self.display = pygame.display.set_mode(
            (1280, 720), pygame.HWSURFACE | pygame.DOUBLEBUF)
        self.clock = pygame.time.Clock()
        self.hud = HUD(1280, 720)

        # Get the world from the server
        self.world = self.client.get_world()
        self.world.on_tick(self.hud.on_world_tick)

        #vehicle states
        self.states = {'autopilot_engaged' : False,
                         'reverse_engaged' : False,
                         'destination_set' : False}

    def connectToVehicle(self):

        # Create the vehicle
        self.vehicle = Elcano.SimulatedVehicle(self.world)

        # Create the camera for the client
        self.camera_manager = CameraManager(
            self.vehicle.actor, self.world, self.hud, 2.2)
        self.camera_manager.transform_index = 0
        self.camera_manager.set_sensor(0, notify=False)

        # Recording variables
        self.recording_enabled = False
        self.recording_start = 0

    def render(self):

        # Update hud with latest values
        self.hud.tick(self.world, self.vehicle, self.clock)

        # Render our camera and hud
        self.camera_manager.render(self.display)
        self.hud.render(self.display)

        # Update the screen
        pygame.display.flip()

        # Read events from pygame window
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return 
            elif event.type == pygame.KEYUP:
                if event.key == K_r:
                    self.states['reverse_engaged'] = not self.states['reverse_engaged']
                elif event.key == K_p:
                    self.states['autopilot_engaged'] = not self.states['autopilot_engaged']

    def getKeys(self):
        return pygame.key.get_pressed()

    def destroy(self):
        """
        In order to remove everything from the server destroy the camera then the vehicle.
        """

        if(self.camera_manager is not None):
            self.camera_manager.sensor.destroy()

        if(self.vehicle is not None):
            self.vehicle.destroy()


# ==============================================================================
# -- HUD -----------------------------------------------------------------------
# ==============================================================================


class HUD(object):

    def __init__(self, width, height):
        self.dim = (width, height)
        font = pygame.font.Font(pygame.font.get_default_font(), 20)
        font_name = 'courier' if os.name == 'nt' else 'mono'
        fonts = [x for x in pygame.font.get_fonts() if font_name in x]
        default_font = 'ubuntumono'
        mono = default_font if default_font in fonts else fonts[0]
        mono = pygame.font.match_font(mono)
        self._font_mono = pygame.font.Font(mono, 12 if os.name == 'nt' else 14)
        self._notifications = FadingText(font, (width, 40), (0, height - 40))
        self.help = HelpText(pygame.font.Font(mono, 16), width, height)
        self.server_fps = 0
        self.frame = 0
        self.simulation_time = 0
        self._show_info = True
        self._info_text = []
        self._server_clock = pygame.time.Clock()

    def on_world_tick(self, timestamp):
        self._server_clock.tick()
        self.server_fps = self._server_clock.get_fps()
        self.frame = timestamp.frame
        self.simulation_time = timestamp.elapsed_seconds

    def tick(self, world, vehicle, clock):
        self._notifications.tick(world, clock)
        if not self._show_info:
            return
        t = vehicle.actor.get_transform()
        v = vehicle.actor.get_velocity()
        c = vehicle.actor.get_control()

        # Handling compass from IMU
        compass = vehicle.IMUSensor.compass
        heading = 'N' if compass > 270.5 or compass < 89.5 else ''
        heading += 'S' if 90.5 < compass < 269.5 else ''
        heading += 'E' if 0.5 < compass < 179.5 else ''
        heading += 'W' if 180.5 < compass < 359.5 else ''

        self._info_text = [
            'Server:  % 16.0f FPS' % self.server_fps,
            'Client:  % 16.0f FPS' % clock.get_fps(),
            '',
            'Vehicle: % 20s' % "Elcano",
            'Simulation time: % 12s' % datetime.timedelta(
                seconds=int(self.simulation_time)),
            '',
            'Speed:   % 15.0f km/h' % (3.6 *
                                       math.sqrt(v.x**2 + v.y**2 + v.z**2)),
            u'Compass:% 17.0f\N{DEGREE SIGN} % 2s' % (compass, heading),
            'Accelero: (%5.1f,%5.1f,%5.1f)' % (
                vehicle.IMUSensor.accelerometer),
            'Gyroscop: (%5.1f,%5.1f,%5.1f)' % (vehicle.IMUSensor.gyroscope),
            'Location:% 20s' % ('(% 5.1f, % 5.1f)' %
                                (t.location.x, t.location.y)),
            'GNSS:% 24s' % ('(% 2.6f, % 3.6f)' % (
                vehicle.GNSSSensor.latitude, vehicle.GNSSSensor.longitude)),
            'Height:  % 18.0f m' % t.location.z,
            '']

        if isinstance(c, Carla.VehicleControl):
            self._info_text += [
                ('Throttle:', c.throttle, 0.0, 1.0),
                ('Steer:', c.steer, -1.0, 1.0),
                ('Brake:', c.brake, 0.0, 1.0),
                ('Reverse:', c.reverse),
                ('Hand brake:', c.hand_brake),
                ('Manual:', c.manual_gear_shift),
                'Gear:        %s' % {-1: 'R', 0: 'N'}.get(c.gear, c.gear)]

        elif isinstance(c, Carla.WalkerControl):
            self._info_text += [
                ('Speed:', c.speed, 0.0, 5.556),
                ('Jump:', c.jump)]

    def toggle_info(self):
        self._show_info = not self._show_info

    def notification(self, text, seconds=2.0):
        self._notifications.set_text(text, seconds=seconds)

    def error(self, text):
        self._notifications.set_text('Error: %s' % text, (255, 0, 0))

    def render(self, display):
        if self._show_info:
            info_surface = pygame.Surface((220, self.dim[1]))
            info_surface.set_alpha(100)
            display.blit(info_surface, (0, 0))
            v_offset = 4
            bar_h_offset = 100
            bar_width = 106
            for item in self._info_text:
                if v_offset + 18 > self.dim[1]:
                    break
                if isinstance(item, list):
                    if len(item) > 1:
                        points = [(x + 8, v_offset + 8 + (1.0 - y) * 30)
                                  for x, y in enumerate(item)]
                        pygame.draw.lines(
                            display, (255, 136, 0), False, points, 2)
                    item = None
                    v_offset += 18
                elif isinstance(item, tuple):
                    if isinstance(item[1], bool):
                        rect = pygame.Rect(
                            (bar_h_offset, v_offset + 8), (6, 6))
                        pygame.draw.rect(display, (255, 255, 255),
                                         rect, 0 if item[1] else 1)
                    else:
                        rect_border = pygame.Rect(
                            (bar_h_offset, v_offset + 8), (bar_width, 6))
                        pygame.draw.rect(
                            display, (255, 255, 255), rect_border, 1)
                        f = (item[1] - item[2]) / (item[3] - item[2])
                        if item[2] < 0.0:
                            rect = pygame.Rect(
                                (bar_h_offset + f * (bar_width - 6), v_offset + 8), (6, 6))
                        else:
                            rect = pygame.Rect(
                                (bar_h_offset, v_offset + 8), (f * bar_width, 6))
                        pygame.draw.rect(display, (255, 255, 255), rect)
                    item = item[0]
                if item:  # At this point has to be a str.
                    surface = self._font_mono.render(
                        item, True, (255, 255, 255))
                    display.blit(surface, (8, v_offset))
                v_offset += 18
        self._notifications.render(display)
        self.help.render(display)


# ==============================================================================
# -- FadingText ----------------------------------------------------------------
# ==============================================================================


class FadingText(object):
    def __init__(self, font, dim, pos):
        self.font = font
        self.dim = dim
        self.pos = pos
        self.seconds_left = 0
        self.surface = pygame.Surface(self.dim)

    def set_text(self, text, color=(255, 255, 255), seconds=2.0):
        text_texture = self.font.render(text, True, color)
        self.surface = pygame.Surface(self.dim)
        self.seconds_left = seconds
        self.surface.fill((0, 0, 0, 0))
        self.surface.blit(text_texture, (10, 11))

    def tick(self, _, clock):
        delta_seconds = 1e-3 * clock.get_time()
        self.seconds_left = max(0.0, self.seconds_left - delta_seconds)
        self.surface.set_alpha(500.0 * self.seconds_left)

    def render(self, display):
        display.blit(self.surface, self.pos)


# ==============================================================================
# -- HelpText ------------------------------------------------------------------
# ==============================================================================


class HelpText(object):
    """Helper class to handle text output using pygame"""

    def __init__(self, font, width, height):
        lines = __doc__.split('\n')
        self.font = font
        self.line_space = 18
        self.dim = (780, len(lines) * self.line_space + 12)
        self.pos = (0.5 * width - 0.5 *
                    self.dim[0], 0.5 * height - 0.5 * self.dim[1])
        self.seconds_left = 0
        self.surface = pygame.Surface(self.dim)
        self.surface.fill((0, 0, 0, 0))
        for n, line in enumerate(lines):
            text_texture = self.font.render(line, True, (255, 255, 255))
            self.surface.blit(text_texture, (22, n * self.line_space))
            self._render = False
        self.surface.set_alpha(220)

    def toggle(self):
        self._render = not self._render

    def render(self, display):
        if self._render:
            display.blit(self.surface, self.pos)


# ==============================================================================
# -- CameraManager -------------------------------------------------------------
# ==============================================================================


class CameraManager(object):
    """
    Sensor class for collecting camera data from Carla
    """

    def __init__(self, actor, world, hud, gamma_correction):
        self.sensor = None
        self.surface = None
        self.actor = actor
        self.hud = hud
        self.recording = False

        bound_y = 0.5 + self.actor.bounding_box.extent.y
        Attachment = Carla.AttachmentType

        self._camera_transforms = [
            (Carla.Transform(Carla.Location(x=-5.5, z=2.5),
                             Carla.Rotation(pitch=8.0)), Attachment.SpringArm),
            (Carla.Transform(Carla.Location(x=1.6, z=1.7)), Attachment.Rigid),
            (Carla.Transform(Carla.Location(x=5.5, y=1.5, z=1.5)), Attachment.SpringArm),
            (Carla.Transform(Carla.Location(x=-8.0, z=6.0),
                             Carla.Rotation(pitch=6.0)), Attachment.SpringArm),
            (Carla.Transform(Carla.Location(x=-1, y=-bound_y, z=0.5)), Attachment.Rigid)]
        self.transform_index = 1
        self.sensors = [
            ['sensor.camera.rgb', cc.Raw, 'Camera RGB', {}],
            ['sensor.camera.depth', cc.Raw, 'Camera Depth (Raw)', {}],
            ['sensor.camera.depth', cc.Depth, 'Camera Depth (Gray Scale)', {}],
            ['sensor.camera.depth', cc.LogarithmicDepth,
                'Camera Depth (Logarithmic Gray Scale)', {}],
            ['sensor.camera.semantic_segmentation', cc.Raw,
                'Camera Semantic Segmentation (Raw)', {}],
            ['sensor.camera.semantic_segmentation', cc.CityScapesPalette,
                'Camera Semantic Segmentation (CityScapes Palette)', {}],
            ['sensor.lidar.ray_cast', None, 'Lidar (Ray-Cast)', {}],
            ['sensor.camera.rgb', cc.Raw, 'Camera RGB Distorted',
                {'lens_circle_multiplier': '3.0',
                 'lens_circle_falloff': '3.0',
                 'chromatic_aberration_intensity': '0.5',
                 'chromatic_aberration_offset': '0'}]]
        bp_library = world.get_blueprint_library()

        for item in self.sensors:
            bp = bp_library.find(item[0])
            if item[0].startswith('sensor.camera'):
                bp.set_attribute('image_size_x', str(hud.dim[0]))
                bp.set_attribute('image_size_y', str(hud.dim[1]))
                if bp.has_attribute('gamma'):
                    bp.set_attribute('gamma', str(gamma_correction))
                for attr_name, attr_value in item[3].items():
                    bp.set_attribute(attr_name, attr_value)
            elif item[0].startswith('sensor.lidar'):
                bp.set_attribute('range', '50')
            item.append(bp)

        self.index = None

    def toggle_camera(self):
        self.transform_index = (self.transform_index +
                                1) % len(self._camera_transforms)
        self.set_sensor(self.index, notify=False, force_respawn=True)

    def set_sensor(self, index, notify=True, force_respawn=False):
        index = index % len(self.sensors)
        needs_respawn = True if self.index is None else \
            (force_respawn or (self.sensors[index]
                               [2] != self.sensors[self.index][2]))
        if needs_respawn:
            if self.sensor is not None:
                self.sensor.destroy()
                self.surface = None
            self.sensor = self.actor.get_world().spawn_actor(
                self.sensors[index][-1],
                self._camera_transforms[self.transform_index][0],
                attach_to=self.actor,
                attachment_type=self._camera_transforms[self.transform_index][1])

            weak_self = weakref.ref(self)
            self.sensor.listen(
                lambda image: CameraManager._parse_image(weak_self, image))
        if notify:
            self.hud.notification(self.sensors[index][2])
        self.index = index

    def next_sensor(self):
        self.set_sensor(self.index + 1)

    def toggle_recording(self):
        self.recording = not self.recording
        self.hud.notification('Recording %s' %
                              ('On' if self.recording else 'Off'))

    def render(self, display):
        if self.surface is not None:
            display.blit(self.surface, (0, 0))

    @staticmethod
    def _parse_image(weak_self, image):
        self = weak_self()
        if not self:
            return
        if self.sensors[self.index][0].startswith('sensor.lidar'):
            points = np.frombuffer(image.raw_data, dtype=np.dtype('f4'))
            points = np.reshape(points, (int(points.shape[0] / 3), 3))
            lidar_data = np.array(points[:, :2])
            lidar_data *= min(self.hud.dim) / 100.0
            lidar_data += (0.5 * self.hud.dim[0], 0.5 * self.hud.dim[1])
            lidar_data = np.fabs(lidar_data)  # pylint: disable=E1111
            lidar_data = lidar_data.astype(np.int32)
            lidar_data = np.reshape(lidar_data, (-1, 2))
            lidar_img_size = (self.hud.dim[0], self.hud.dim[1], 3)
            lidar_img = np.zeros((lidar_img_size), dtype=int)
            lidar_img[tuple(lidar_data.T)] = (255, 255, 255)
            self.surface = pygame.surfarray.make_surface(lidar_img)
        else:
            image.convert(self.sensors[self.index][1])
            array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
            array = np.reshape(array, (image.height, image.width, 4))
            array = array[:, :, :3]
            array = array[:, :, ::-1]
            self.surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))
        if self.recording:
            image.save_to_disk('_out/%08d' % image.frame)


# If running the script internally this will just point it to main.
if __name__ == '__main__':

    main()
