from enum import Enum

import pygame


class ConditionsType(Enum):
    DONE = 0
    LOGIC = 1
    NOT_LOGIC = 2


class SimpleCheck:
    def __init__(self, ident, name, positions, linked_map, conditions):
        self.id = ident
        self.name = name
        self.positions = positions
        self.map = linked_map
        self.pin = None
        self.pin_color = None
        self.pin_rect = None
        self.all_logic = False
        self.checked = False
        self.conditions = conditions

    def update(self):
        font = self.map.tracker.core_service.get_font("mapFont")

        if self.all_logic:
            self.pin_color = self.map.tracker.core_service.get_color_from_font(font, "Logic")
        else:
            self.pin_color = self.map.tracker.core_service.get_color_from_font(font, "NotLogic")

        if self.checked:
            self.pin_color = self.map.tracker.core_service.get_color_from_font(font, "Done")

        simple_check_datas = self.map.tracker.tracker_json_data[4]["SizeSimpleCheck"]
        self.pin_rect = pygame.Rect((self.map.index_positions[0] * self.map.tracker.core_service.zoom) + (
                self.positions["x"] * self.map.tracker.core_service.zoom) + (
                                            (simple_check_datas["w"] * self.map.tracker.core_service.zoom) / 2),
                                    (self.map.index_positions[1] * self.map.tracker.core_service.zoom) + (
                                            self.positions["y"] * self.map.tracker.core_service.zoom) + (
                                            (simple_check_datas["w"] * self.map.tracker.core_service.zoom) / 2),
                                    (simple_check_datas["w"] * self.map.tracker.core_service.zoom),
                                    (simple_check_datas["h"] * self.map.tracker.core_service.zoom))

    def draw(self, screen):
        pygame.draw.circle(screen, self.pin_color, (self.pin_rect.x, self.pin_rect.y), self.pin_rect.w / 2)

    def left_click(self, mouse_position):
        print(type(self), "KOOKOO")

    def get_rect(self):
        return self.pin_rect

    def get_position(self):
        return (self.pin_rect.x, self.pin_rect.y)
