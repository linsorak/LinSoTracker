import pygame

from Tools.CoreService import CoreService


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Bank(metaclass=Singleton):
    def __init__(self):
        self.core_service = CoreService()
        self.bank = {}
    def addImage(self, path):
        if path in self.bank:
            return self.bank[path]
        else:
            imageTemp = pygame.image.load(path).convert_alpha()
            self.bank[path] = imageTemp
            return imageTemp

    def addZoomImage(self, path):
        if path in self.bank:
            return self.core_service.zoom_image(self.bank[path])
        else:
            imageTemp = self.core_service.zoom_image(pygame.image.load(path).convert_alpha())
            self.bank[path] = imageTemp
            return imageTemp



