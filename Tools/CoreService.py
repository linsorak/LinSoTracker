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
        self.app_name = "LinSoTracker"
        self.version = "2.0b"
        self.temp_path = tempfile.gettempdir()

        path = os.path.expanduser(os.path.join("~", "." + self.app_name))
        print(path)

        if platform == "win32":
            #path = os.path.join(os.getenv('APPDATA'),appName)
            self.temp_path = os.path.join(self.temp_path, self.app_name)
        else:
            self.temp_path = os.path.expanduser(os.path.join(self.temp_path, self.app_name))

        self.create_directory(path=self.temp_path)

    def get_temp_path(self):
        return self.temp_path

    def get_window_title(self):
        return "{} v{}".format(self.app_name, self.version)

    @staticmethod
    def create_directory(path):
        if not os.path.exists(path):
            os.makedirs(path)
