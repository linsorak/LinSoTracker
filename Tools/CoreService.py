import os
from sys import platform
import tempfile

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

        self.app_path = os.path.abspath(os.path.dirname(__file__)).replace("{}{}".format(os.sep, "Tools"), os.sep)

        if platform == "win32":
            #path = os.path.join(os.getenv('APPDATA'),appName)
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
        return ((mouse_positions[0] >= element_positons[0]) & (mouse_positions[0]  <= (element_positons[0] + element_dimension[0])) &
            (mouse_positions[1] >= element_positons[1]) & (mouse_positions[1] <= (element_positons[1] + element_dimension[1])))

