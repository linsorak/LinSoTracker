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
        self.checked = False
        self.conditions = conditions
        # self.conditions = "have('Giant Bomb Bag') or have('Bomb Bag') or have('Bomb') or have('Water Bomb')"
        if type(self.conditions) == str:
            self.conditions = self.conditions.replace("have(", "self.map.tracker.have(")
            self.conditions = self.conditions.replace("do(", "self.map.tracker.do(")

    def update(self):
        font = self.map.tracker.core_service.get_font("mapFont")
        self.all_logic = False

        if eval(self.conditions):
            self.state = ConditionsType.LOGIC
            self.pin_color = self.map.tracker.core_service.get_color_from_font(font, "Logic")
        else:
            self.state = ConditionsType.NOT_LOGIC
            self.pin_color = self.map.tracker.core_service.get_color_from_font(font, "NotLogic")

        if self.checked:
            self.pin_color = self.map.tracker.core_service.get_color_from_font(font, "Done")

        simple_check_datas = self.map.tracker.tracker_json_data[4]["SizeSimpleCheck"]
        x = (self.map.index_positions[0] * self.map.tracker.core_service.zoom) + (
                    self.positions["x"] * self.map.tracker.core_service.zoom)
        x = x + ((simple_check_datas["w"] * self.map.tracker.core_service.zoom) / 2)
        y = (self.map.index_positions[1] * self.map.tracker.core_service.zoom) + (
                    self.positions["y"] * self.map.tracker.core_service.zoom)
        y = y + ((simple_check_datas["h"] * self.map.tracker.core_service.zoom) / 2)

        self.pin_rect = pygame.Rect(x, y,
                                    ((simple_check_datas["w"] * 2) * self.map.tracker.core_service.zoom),
                                    ((simple_check_datas["h"] * 2) * self.map.tracker.core_service.zoom))

    def draw(self, screen):
        pygame.draw.circle(screen, self.pin_color,
                           (self.pin_rect.x + (self.pin_rect.w / 2), self.pin_rect.y + (self.pin_rect.h / 2)),
                           self.pin_rect.w / 2)
        pygame.draw.circle(screen, pygame.Color("black"),
                           (self.pin_rect.x + (self.pin_rect.w / 2), self.pin_rect.y + (self.pin_rect.h / 2)),
                           self.pin_rect.w / 2, int(1 * self.map.tracker.core_service.zoom))
        # pygame.draw.circle(screen, self.pin_color, (self.pin_rect.x + (self.pin_rect.w / 2), self.pin_rect.y + (self.pin_rect.h / 2)), self.pin_rect.w / 2)
        # pygame.draw.circle(screen, pygame.Color("black"), (self.pin_rect.x + (self.pin_rect.w / 2), self.pin_rect.y + (self.pin_rect.h / 2)), self.pin_rect.w / 2, 1)

    def left_click(self, mouse_position):
        if self.checked:
            self.checked = False
        else:
            self.checked = True

        self.update()

    def get_rect(self):
        return self.pin_rect

    def get_position(self):
        return (self.pin_rect.x, self.pin_rect.y)

    def get_data(self):
        data = {
            "id": self.id,
            "name": self.name,
            "checked": self.checked
        }
        return data

    def set_data(self, datas):
        self.checked = datas["checked"]
        self.update()
