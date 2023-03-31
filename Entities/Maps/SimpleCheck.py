from enum import Enum

import pygame
from pygame import gfxdraw


class ConditionsType(Enum):
    DONE = 0
    LOGIC = 1
    NOT_LOGIC = 2


class SimpleCheck:
    def __init__(self, ident, name, positions, linked_map, conditions, hide=False):
        self.state = None
        self.id = ident
        self.name = name
        self.positions = positions
        self.map = linked_map
        self.pin = None
        self.pin_color = None
        self.pin_rect = None
        self.checked = False
        self.conditions = conditions
        self.hide = hide
        self.focused = False
        # self.conditions = "have('Giant Bomb Bag') or have('Bomb Bag') or have('Bomb') or have('Water Bomb')"
        if type(self.conditions) == str:
            self.conditions = self.conditions.replace("have(", "self.map.tracker.have(")
            self.conditions = self.conditions.replace("do(", "self.map.tracker.do(")
            self.conditions = self.conditions.replace("rules(", "self.map.tracker.rules(")
            self.conditions = self.conditions.replace("haveCheck(", "self.map.tracker.have_check(")

    def update(self):
        font = self.map.tracker.core_service.get_font("mapFont")
        core_service = self.map.tracker.core_service
        zoom = core_service.zoom
        index_positions = self.map.index_positions
        simple_check_datas = self.map.tracker.tracker_json_data[4]["SizeSimpleCheck"]

        if eval(self.conditions):
            self.state = ConditionsType.LOGIC
            self.pin_color = self.map.tracker.core_service.get_color_from_font(font, "Logic")
        else:
            self.state = ConditionsType.NOT_LOGIC
            self.pin_color = self.map.tracker.core_service.get_color_from_font(font, "NotLogic")

        if self.checked:
            self.state = ConditionsType.DONE
            self.pin_color = self.map.tracker.core_service.get_color_from_font(font, "Done")
            self.focused = False

        simple_check_datas = self.map.tracker.tracker_json_data[4]["SizeSimpleCheck"]
        x = (index_positions[0] * zoom + self.positions["x"] * zoom) + (simple_check_datas["w"] * zoom) / 2
        y = (index_positions[1] * zoom + self.positions["y"] * zoom) + (simple_check_datas["h"] * zoom) / 2
        self.pin_rect = pygame.Rect(x, y, (simple_check_datas["w"] * 2) * zoom, (simple_check_datas["h"] * 2) * zoom)

    def draw(self, screen):
        if not self.hide:
            # zoom = self.map.tracker.core_service.zoom
            zoom = 1.0

            if self.map.tracker.core_service.zoom < 1.0:
                zoom = 1.5

            pin_center = (
                (self.pin_rect.x + (self.pin_rect.w // 2) * zoom),
                (self.pin_rect.y + (self.pin_rect.h // 2) * zoom)
            )
            pin_radius = self.pin_rect.w // 2

            if self.focused:
                font = self.map.tracker.core_service.get_font("mapFont")
                pygame.gfxdraw.filled_circle(screen, int(pin_center[0]), int(pin_center[1]), int((pin_radius + 3) * zoom),
                                             self.map.tracker.core_service.get_color_from_font(font, "Focused"))
                pygame.gfxdraw.aacircle(screen, int(pin_center[0]), int(pin_center[1]), int((pin_radius + 3) * zoom),
                                        pygame.Color("black"))

            pygame.gfxdraw.filled_circle(screen, int(pin_center[0]), int(pin_center[1]), int(pin_radius * zoom), self.pin_color)
            pygame.gfxdraw.aacircle(screen, int(pin_center[0]), int(pin_center[1]), int(pin_radius * zoom),
                                         pygame.Color("black"))

    def draw_circle_with_thickness(self, surface, color, center, radius, thickness):
        for i in range(thickness):
            pygame.gfxdraw.aacircle(surface, int(center[0]), int(center[1]), int(radius + i), color)
        pygame.gfxdraw.aacircle(surface, int(center[0]), int(center[1]), int(radius + thickness), pygame.Color("black"))

    def left_click(self, mouse_position):
        self.checked = not self.checked
        self.update()

    def wheel_click(self, mouse_position):
        if not self.checked:
            self.focused = not self.focused

    def get_rect(self):
        return self.pin_rect

    def get_position(self):
        return self.pin_rect.x, self.pin_rect.y

    def get_data(self):
        data = {
            "id": self.id,
            "name": self.name,
            "checked": self.checked,
            "hide": self.hide,
            "focused": self.focused
        }
        return data

    def set_data(self, datas):
        self.checked = datas.get("checked", False)
        self.hide = datas.get("hide", False)
        self.focused = datas.get("focused", False)
        self.update()

    def all_check_hidden(self):
        return False
