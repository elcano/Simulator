import carla
import time
import pygame
import cv2
import numpy as np

from pygame.locals import KMOD_CTRL
from pygame.locals import KMOD_SHIFT
from pygame.locals import K_0
from pygame.locals import K_9
from pygame.locals import K_BACKQUOTE
from pygame.locals import K_BACKSPACE
from pygame.locals import K_COMMA
from pygame.locals import K_DOWN
from pygame.locals import K_ESCAPE
from pygame.locals import K_F1
from pygame.locals import K_LEFT
from pygame.locals import K_PERIOD
from pygame.locals import K_RIGHT
from pygame.locals import K_SLASH
from pygame.locals import K_SPACE
from pygame.locals import K_TAB
from pygame.locals import K_UP
from pygame.locals import K_a
from pygame.locals import K_c
from pygame.locals import K_g
from pygame.locals import K_d
from pygame.locals import K_h
from pygame.locals import K_m
from pygame.locals import K_n
from pygame.locals import K_p
from pygame.locals import K_q
from pygame.locals import K_r
from pygame.locals import K_s
from pygame.locals import K_w
from pygame.locals import K_l
from pygame.locals import K_i
from pygame.locals import K_z
from pygame.locals import K_x
from pygame.locals import K_MINUS
from pygame.locals import K_EQUALS


class Autopilot:

    def __init__(self, simVehicle, start_in_autopilot = False):
        self.simVehicle = simVehicle
        self.autopilot_enabled = start_in_autopilot
        self._steer_cache = 0.0
        self.vision = Vision()
        
    def _parse_vehicle_keys(self, keys):
        self.simVehicle.updateThrottle(1.0) if keys[K_UP] or keys[K_w] else self.simVehicle.updateThrottle(0.0)
        steer_increment = 0.01
        if keys[K_LEFT] or keys[K_a]:
            if self._steer_cache > 0:
                self._steer_cache = 0
            else:
                self._steer_cache -= steer_increment
        elif keys[K_RIGHT] or keys[K_d]:
            if self._steer_cache < 0:
                self._steer_cache = 0
            else:
                self._steer_cache += steer_increment
        else:
            self._steer_cache = 0.0
        self._steer_cache = min(1.0, max(-1.0, self._steer_cache))
        self.simVehicle.updateSteering(round(self._steer_cache, 1)) 
        self.simVehicle.updateBraking(1.0) if keys[K_DOWN] or keys[K_s] else self.simVehicle.updateBraking(0.0)

    def mainloop(self, keys, states):
        self.simVehicle.updateReverse(states['reverse_engaged'])
        self.vision.grab_frame(self.simVehicle.RGBSensor.get_frame())
        self._parse_vehicle_keys(keys)

    def destroy(self):
        self.vision.destroy()


class Vision:

    def __init__(self):
        self.rgb_frame = None
        
    def grab_frame(self, rgb_frame):
        self.rgb_frame = rgb_frame
        cv2.imshow("RGBSensor", self.rgb_frame)
        cv2.waitKey(1)

    def destroy(self):
        cv2.destroyAllWindows()
