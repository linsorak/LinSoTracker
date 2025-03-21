from enum import Enum

import pygame
from pygame import gfxdraw


class ConditionsType(Enum):
    DONE = 0
    LOGIC = 1
    NOT_LOGIC = 2


class SimpleCheck:
    def __init__(self, ident, name, positions, linked_map, conditions, hide=False, zone=None, group=None):
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
        self.zone = zone
        self.group = group
        self.zoom = self.map.tracker.core_service.zoom
        self.pin_rect = pygame.Rect(0, 0, 1, 1)
        self.dragged_item_name = None
        self.dragged_item_basename = None
        self.dragged_item_index = None
        self.dragged_icon_item_image = None

        if type(self.conditions) == str:
            self.conditions = self.conditions.replace("have(", "self.map.tracker.have(")
            self.conditions = self.conditions.replace("do(", "self.map.tracker.do(")
            self.conditions = self.conditions.replace("rules(", "self.map.tracker.rules(")
            self.conditions = self.conditions.replace("haveCheck(", "self.map.tracker.have_check(")
            self.conditions = self.conditions.replace("haveAlternateValue(", "self.map.tracker.haveAlternateValue(")
            self.conditions = self.conditions.replace("isChecked(", "self.map.tracker.isChecked(")
            self.conditions = self.conditions.replace("isVisible(", "self.map.tracker.isVisible(")

    def update(self):
        font = self.map.tracker.core_service.get_font("mapFont")
        core_service = self.map.tracker.core_service
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
        x = (index_positions[0] * core_service.zoom + self.positions["x"] * core_service.zoom) + (simple_check_datas["w"] * self.zoom) / 2
        y = (index_positions[1] * core_service.zoom + self.positions["y"] * core_service.zoom) + (simple_check_datas["h"] * self.zoom) / 2
        self.pin_rect = pygame.Rect(x, y, (simple_check_datas["w"] * 2) * self.zoom, (simple_check_datas["h"] * 2) * self.zoom)
        self.update_dragged_image()

    def draw_dragged_image(self, screen):
        if self.dragged_icon_item_image:
            dragged_x = self.pin_rect.x - (self.dragged_icon_item_image.get_rect().w / 3)
            dragged_y = self.pin_rect.y - (self.dragged_icon_item_image.get_rect().h / 3)
            screen.blit(self.dragged_icon_item_image, (dragged_x, dragged_y))

    def draw(self, screen):
        if not self.hide:
            # zoom = self.map.tracker.core_service.zoom
            zoom = 1.0

            if self.map.tracker.core_service.zoom < 1.0:
                zoom = 1.0

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
        self.map.tracker.reset_hint()
        self.update()

        if self.group:
            grouped_checks = self.map.get_all_group_checks(self, self.group)
            for group_check in grouped_checks:
                group_check.checked = self.checked
                group_check.update()

    def right_click(self, mouse_position):
        if self.dragged_item_name:
            self.dragged_item_name = None
            self.dragged_item_basename = None
            self.dragged_item_index = None
            self.dragged_icon_item_image = None
            self.update()

    def wheel_click(self, mouse_position):
        if not self.checked:
            self.focused = not self.focused

    def update_dragged_image(self):
        if self.dragged_item_name:
            item = self.map.tracker.find_item(self.dragged_item_name, self.dragged_item_name == self.dragged_item_basename)
            if item:
                if hasattr(item, "next_item_index"):
                    if self.dragged_item_index > -1:
                        self.dragged_icon_item_image = item.next_items[self.dragged_item_index]["Image"]
                    else:
                        self.dragged_icon_item_image = item.colored_image
                else:
                    self.dragged_icon_item_image = item.colored_image

            self.dragged_icon_item_image = pygame.transform.smoothscale(self.dragged_icon_item_image, (30 * self.map.tracker.core_service.zoom, 30 * self.map.tracker.core_service.zoom))


    def set_new_current_image(self, name, base_name, index=None):
        self.dragged_item_name = name
        self.dragged_item_basename = base_name
        self.dragged_item_index = index
        self.update()


    def get_rect(self):
        return self.pin_rect

    def get_position(self):
        return self.pin_rect.x, self.pin_rect.y

    def get_data(self):
        data = {"id": self.id,
                "name": self.name,
                "checked": self.checked,
                "hide": self.hide,
                "focused": self.focused,
                "dragged_item_name": self.dragged_item_name,
                "dragged_item_basename": self.dragged_item_basename,
                "dragged_item_index": self.dragged_item_index}
        return data

    def set_data(self, datas):
        self.checked = datas.get("checked", False)
        self.hide = datas.get("hide", False)
        self.focused = datas.get("focused", False)
        self.dragged_item_name = datas.get("dragged_item_name", None)
        self.dragged_item_basename = datas.get("dragged_item_basename", None)
        self.dragged_item_index = datas.get("dragged_item_index", None)
        self.update()
        self.update_dragged_image()

    def all_check_hidden(self):
        return False
