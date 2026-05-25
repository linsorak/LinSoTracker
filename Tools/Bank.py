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
        self.zoom_bank = {}

    def addImage(self, path):
        if path in self.bank:
            return self.bank[path]
        else:
            imageTemp = pygame.image.load(path).convert_alpha()
            self.bank[path] = imageTemp
            return imageTemp

    def addZoomImage(self, path):
        zoom = self.core_service.zoom
        key = (path, zoom)
        cached = self.zoom_bank.get(key)
        if cached is not None:
            return cached
        if path in self.bank:
            base = self.bank[path]
        else:
            base = pygame.image.load(path).convert_alpha()
            self.bank[path] = base
        zoomed = self.core_service.zoom_image(base)
        self.zoom_bank[key] = zoomed
        return zoomed

    def unloadImages(self):
        self.bank.clear()
        self.zoom_bank.clear()