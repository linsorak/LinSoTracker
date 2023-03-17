from enum import Enum

import pygame


class ConditionsType(Enum):
    DONE = 0
    LOGIC = 1
    NOT_LOGIC = 2


class SimpleCheck:
    def __init__(self, ident, name, positions, linked_map, conditions, hide=False):
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

        simple_check_datas = self.map.tracker.tracker_json_data[4]["SizeSimpleCheck"]
        x = (index_positions[0] * zoom + self.positions["x"] * zoom) + (simple_check_datas["w"] * zoom) / 2
        y = (index_positions[1] * zoom + self.positions["y"] * zoom) + (simple_check_datas["h"] * zoom) / 2
        self.pin_rect = pygame.Rect(x, y, (simple_check_datas["w"] * 2) * zoom, (simple_check_datas["h"] * 2) * zoom)

    def draw(self, screen):
        if not self.hide:
            pin_center = (
                self.pin_rect.x + (self.pin_rect.w // 2),
                self.pin_rect.y + (self.pin_rect.h // 2)
            )
            pin_radius = self.pin_rect.w // 2
            zoom = self.map.tracker.core_service.zoom

            pygame.draw.circle(screen, self.pin_color, pin_center, pin_radius)
            pygame.draw.circle(screen, pygame.Color("black"), pin_center, pin_radius, int(1 * zoom))

    def left_click(self, mouse_position):
        if self.checked:
            self.checked = False
        else:
            self.checked = True

        self.update()

    def get_rect(self):
        return self.pin_rect

    def get_position(self):
        return self.pin_rect.x, self.pin_rect.y

    def get_data(self):
        data = {
            "id": self.id,
            "name": self.name,
            "checked": self.checked,
            "hide": self.hide
        }
        return data

    def set_data(self, datas):
        self.checked = datas["checked"]
        self.hide = datas["hide"]
        self.update()

    def all_check_hidden(self):
        return False