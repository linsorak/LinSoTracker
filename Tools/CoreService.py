import json
import os
import shutil
import sys
import tempfile
import platform

from urllib.error import URLError
from urllib.request import urlopen

import pygame


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class CoreService(metaclass=Singleton):
    def __init__(self):
        self.official_template = None
        self.new_version = None
        self.background_color = (0, 0, 0)
        self.tracker_temp_path = None
        self.app_name = "LinSoTracker"
        self.version = "2.0.4-BETA"
        self.temp_path = tempfile.gettempdir()
        self.json_data = None
        self.zoom = 1
        self.zoom_index = 0
        self.sound_active = False
        self.draw_esc_menu_label = True
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
        self.read_checker()
        self.load_default_configuration()


    def save_configuration(self, session, value):
        user_configuration = os.path.join(self.temp_path, "user.conf")
        if os.path.exists(user_configuration):
            data = []
            with open(user_configuration) as f:
                data = json.load(f)
                data[session] = value

            with open(user_configuration, 'w') as f:
                json.dump(data, f, indent=2)

    def load_default_configuration(self):
        user_configuration = os.path.join(self.temp_path, "user.conf")
        if not os.path.exists(user_configuration):
            data = {}
            data["defaultZoom"] = 0
            data["soundWhenItemActive"] = False
            data["showESCLabel"] = True

            with open(user_configuration, 'w') as f:
                json.dump(data, f, indent=2)

            self.zoom_index = data["defaultZoom"]
            self.sound_active = data["soundWhenItemActive"]
            self.draw_esc_menu_label = data["showESCLabel"]
        else:
            with open(user_configuration) as f:
                data = json.load(f)

                if "defaultZoom" in data:
                    self.zoom_index = data["defaultZoom"]
                else:
                    self.zoom_index = 0

                if "soundWhenItemActive" in data:
                    self.sound_active = data["soundWhenItemActive"]
                else:
                    self.sound_active = False

                if "showESCLabel" in data:
                    self.draw_esc_menu_label = data["showESCLabel"]
                else:
                    self.draw_esc_menu_label = True


    def read_checker(self):
        url = "http://linsotracker.com/tracker_data/checker.json"
        try:
            response = urlopen(url)
            data_json = json.loads(response.read())

            if "lastest_version" in data_json:
                if self.get_version() != data_json["lastest_version"]:
                    self.new_version = data_json["lastest_version"]

            if "official_template" in data_json:
                self.official_template = data_json["official_template"]
        except URLError:
            pass

    def get_new_version(self):
        return self.new_version

    def get_official_template(self):
        return self.official_template

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

    def get_version(self):
        return self.version

    def zoom_image(self, image):
        return pygame.transform.smoothscale(image, (image.get_rect().w * self.zoom, image.get_rect().h * self.zoom))

    def get_background_color(self):
        return self.background_color

    def set_background_color(self, r, g, b):
        self.background_color = (r, g, b)

    def is_update(self):
        if self.get_new_version():
            return False
        else:
            return True

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
    def delete_directory(path):
        if os.path.exists(path):
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path, ignore_errors=True)
                except Exception as e:
                    pass

    @staticmethod
    def is_on_element(mouse_positions, element_positons, element_dimension):
        deadzone = 2
        return ((mouse_positions[0] >= element_positons[0] + deadzone) & (
                    mouse_positions[0] <= (element_positons[0] + element_dimension[0]) - deadzone) &
                (mouse_positions[1] >= element_positons[1] + deadzone) & (
                            mouse_positions[1] <= (element_positons[1] + element_dimension[1]) - deadzone))

    @staticmethod
    def launch_app(path):
        if os.path.exists(path):
            os.startfile(path)

    @staticmethod
    def isMac():
        return platform.system() == "Darwin"
