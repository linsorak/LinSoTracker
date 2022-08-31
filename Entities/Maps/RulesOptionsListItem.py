import os

import pygame

from Engine import MainMenu
from Entities.Maps.CheckListItem import CheckListItem


class RulesOptionsListItem(CheckListItem):
    def __init__(self, ident, name, position, tracker, checked):
        super().__init__(ident, name, position, None, tracker)
        self.checked = checked

    def update(self):
        font = self.tracker.core_service.get_font("mapFont")
        font_path = os.path.join(self.tracker.core_service.get_tracker_temp_path(), font["Name"])

        self.color = self.tracker.core_service.get_color_from_font(font, "Normal")

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

    def left_click(self):
        if self.checked:
            self.checked = True
        else:
            self.checked = False
        self.update()