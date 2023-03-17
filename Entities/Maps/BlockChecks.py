import os

import pygame

from Engine import MainMenu
from Entities.Maps.SimpleCheck import SimpleCheck, ConditionsType


class BlockChecks(SimpleCheck):
    def __init__(self, ident, name, positions, linked_map):
        SimpleCheck.__init__(self, ident, name, positions, linked_map, True)
        self.position_logic_indicator = None
        self.surface_logic_indicator = None
        self.list_checks = []
        self.show_checks = False
        self.all_logic = False
        self.logic_cpt = 0

    def add_check(self, check):
        self.list_checks.append(check)
        self.update()

    def get_checks(self):
        return self.list_checks

    def update(self):
        self.logic_cpt = 0
        self.all_logic = True
        self.checked = True

        for check in self.list_checks:
            check.update()
            self.checked &= check.checked
            self.all_logic &= check.state == ConditionsType.LOGIC
            self.logic_cpt += check.state == ConditionsType.LOGIC

        font = self.map.tracker.core_service.get_font("mapFont")
        map_font_path = os.path.join(self.map.tracker.core_service.get_tracker_temp_path(), font["Name"])
        font_number = self.map.tracker.core_service.get_font("mapFontChecksNumber")
        font_path = os.path.join(self.map.tracker.core_service.get_tracker_temp_path(), font_number["Name"])
        groups_datas = self.map.tracker.tracker_json_data[4]["SizeGroupChecks"]
        zoom = self.map.tracker.core_service.zoom
        index_positions = self.map.index_positions

        self.pin_rect = pygame.Rect(
            (index_positions[0] * zoom) + (self.positions["x"] * zoom),
            (index_positions[1] * zoom) + (self.positions["y"] * zoom),
            groups_datas["w"] * zoom,
            groups_datas["h"] * zoom
        )

        self.pin_color = self.map.tracker.core_service.get_color_from_font(
            font, "Done" if self.checked else ("Logic" if self.all_logic else "NotLogic")
        )

        temp_surface = pygame.Surface((0, 0), pygame.SRCALPHA, 32).convert_alpha()

        self.surface_logic_indicator, self.position_logic_indicator = MainMenu.MainMenu.draw_text(
            text=f"{self.logic_cpt}",
            font_name=font_path,
            color=self.map.tracker.core_service.get_color_from_font(font_number, "Normal"),
            font_size=font_number["Size"] * zoom,
            surface=temp_surface,
            position=(self.pin_rect.x, self.pin_rect.y),
            outline=0.5 * zoom
        )

        rect = self.surface_logic_indicator.get_rect()
        x_number = self.pin_rect.x + (self.pin_rect.w / 2) - (rect.w / 2) + (0.5 * zoom)
        y_number = self.pin_rect.y + (self.pin_rect.h / 2) - (rect.h / 2) + (1.5 * zoom)
        self.position_logic_indicator = (x_number, y_number)

    def draw(self, screen):
        if not self.all_check_hidden():
            self.draw_rect(screen, self.pin_color, (0, 0, 0), self.pin_rect, 2 * self.map.tracker.core_service.zoom)
            if self.logic_cpt > 0:
                screen.blit(self.surface_logic_indicator, self.position_logic_indicator)

    def left_click(self, mouse_position):
        if not self.map.current_block_checks:
            self.map.current_block_checks = self
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            self.update()
            self.map.update()

    def get_rect(self):
        return self.pin_rect

    @staticmethod
    def draw_rect(surface, fill_color, outline_color, rect, border=1):
        surface.fill(outline_color, rect)
        surface.fill(fill_color, rect.inflate(-border * 2, -border * 2))

    def get_data(self):
        checks_datas = []
        for check in self.list_checks:
            checks_datas.append(check.get_data())

        data = {
            "id": self.id,
            "name": self.name,
            "checks_datas": checks_datas
        }
        return data

    def set_data(self, datas):
        i = 0
        for data in datas["checks_datas"]:
            for check in self.list_checks:
                if (check.id == data["id"]) and (check.name == data["name"]):
                    i = i + 1
                    check.set_data(data)
                    break

    def all_check_hidden(self):
        hidden = 0
        for check in self.list_checks:
            if check.hide:
                hidden = hidden + 1

        return hidden == len(self.list_checks)