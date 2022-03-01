import os
import sys
import tempfile
from sys import platform

import pygame


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class CoreService(metaclass=Singleton):
    def __init__(self):
        self.tracker_temp_path = None
        self.app_name = "LinSoTracker"
        self.version = "2.0b"
        self.temp_path = tempfile.gettempdir()
        self.json_data = None
        self.zoom = 1
        self.app_path = os.path.abspath(os.path.dirname(__file__)).replace("{}{}".format(os.sep, "Tools"), os.sep)

        if getattr(sys, 'frozen', False):
            self.app_path = os.path.dirname(sys.executable)
        elif __file__:
            self.app_path = os.path.dirname(__file__).replace("Tools", "")

        if platform == "win32":
            self.temp_path = os.path.join(self.temp_path, self.app_name)
        else:
            self.temp_path = os.path.expanduser(os.path.join(self.temp_path, self.app_name))

        self.create_directory(path=self.temp_path)

    def get_temp_path(self):
        return self.temp_path

    def set_tracker_temp_path(self, value):
        self.tracker_temp_path = value

    def get_tracker_temp_path(self):
        return self.tracker_temp_path

    def get_app_path(self):
        return self.app_path

    def get_window_title(self):
        return "{} v{}".format(self.app_name, self.version)

    def set_json_data(self, value):
        self.json_data = value

    def get_json_data(self):
        return self.json_data

    def get_font(self, session):
        return self.json_data[2]["Fonts"][session]

    def zoom_image(self, image):
        return pygame.transform.smoothscale(image, (image.get_rect().w * self.zoom, image.get_rect().h * self.zoom))

    @staticmethod
    def setgamewindowcenter(x=500, y=100):
        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (x, y)

    @staticmethod
    def set_image_transparent(opacity_disable, image):
        transparent_image = image.copy()
        transparent_image.fill((255, 255, 255, 255 * opacity_disable), special_flags=pygame.BLEND_RGBA_MULT)
        return transparent_image

    @staticmethod
    def convert_to_gs(surf):
        width, height = surf.get_size()
        for x in range(width):
            for y in range(height):
                red, green, blue, alpha = surf.get_at((x, y))
                average = (red + green + blue) // 3
                gs_color = (average, average, average, alpha)
                surf.set_at((x, y), gs_color)

    @staticmethod
    def create_directory(path):
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def is_on_element(mouse_positions, element_positons, element_dimension):
        return ((mouse_positions[0] >= element_positons[0]) & (
                    mouse_positions[0] <= (element_positons[0] + element_dimension[0])) &
                (mouse_positions[1] >= element_positons[1]) & (
                            mouse_positions[1] <= (element_positons[1] + element_dimension[1])))
