import os

import pygame
from pygame.sprite import Sprite

from Engine import MainMenu
from Entities.Maps.SimpleCheck import ConditionsType
from Tools.CoreService import CoreService


class CheckListItem(Sprite):
    def __init__(self, ident, name, position, conditions, tracker):
        Sprite.__init__(self)
        self.y_line_end = None
        self.x_line_end = None
        self.y_line_start = None
        self.x_line_start = None
        self.state = None
        self.surface_shadow = None
        self.surface = None
        self.position_draw = None
        self.id = ident
        self.name = name
        self.position = position
        self.conditions = conditions
        self.tracker = tracker
        self.checked = False
        self.is_logic = False
        self.color = None
        self.show = False

        if type(self.conditions) == str:
            self.conditions = self.conditions.replace("have(", "self.tracker.have(")
            self.conditions = self.conditions.replace("do(", "self.tracker.do(")
        self.update()


    def update(self):
        self.color = None
        font = self.tracker.core_service.get_font("mapFont")
        font_path = os.path.join(self.tracker.core_service.get_tracker_temp_path(), font["Name"])

        if eval(self.conditions):
            self.state = ConditionsType.LOGIC
            self.color = self.tracker.core_service.get_color_from_font(font, "Logic")
            self.is_logic = True
        else:
            self.state = ConditionsType.NOT_LOGIC
            self.color = self.tracker.core_service.get_color_from_font(font, "NotLogic")
            self.is_logic = False

        if self.checked:
            self.state = ConditionsType.DONE
            self.color = self.tracker.core_service.get_color_from_font(font, "Done")

        temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32)
        temp_surface = temp_surface.convert_alpha()
        self.surface, self.position_draw = MainMenu.MainMenu.draw_text(
            text=self.name,
            font_name=font_path,
            color=self.color,
            font_size=font["Size"] * self.tracker.core_service.zoom,
            surface=temp_surface,
            position=(self.position["x"], self.position["y"]),
            outline=1 * self.tracker.core_service.zoom)

        # font = pygame.font.Font(font_path, font["Size"] * self.tracker.core_service.zoom)
        # self.surface = font.render(self.name, True, color)
        # self.surface_shadow = font.render(self.name, True, pygame.Color("black"))

    def left_click(self):
        if self.checked:
            self.checked = False
        else:
            self.checked = True
        self.update()

    def get_surface_label(self):
        return self.surface

    def set_position_draw(self, x, y):
        self.position_draw = (x, y)
        self.x_line_start = x
        self.y_line_start = y + (self.surface.get_rect().h / 2)
        self.x_line_end = x + self.surface.get_rect().w
        self.y_line_end = self.y_line_start

    def get_position_draw(self):
        return self.position_draw

    def get_dimensions(self):
        return (self.surface.get_rect().w, self.surface.get_rect().h)

    def draw(self, screen):
        # screen.blit(self.surface_shadow, (self.position_draw[0] + 1, self.position_draw[1] + 1))
        screen.blit(self.surface, self.position_draw)
        if self.checked:
            #pygame.draw.line(screen, pygame.Color("black"), (self.x_line_start, self.y_line_start), (self.x_line_end , self.y_line_end ), int(4 * self.tracker.core_service.zoom))
            pygame.draw.line(screen, self.color, (self.x_line_start, self.y_line_start), (self.x_line_end , self.y_line_end), int(2 * self.tracker.core_service.zoom))
