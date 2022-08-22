import os

import pygame

from Engine import MainMenu
from Entities.Maps.BlockChecks import BlockChecks
from Entities.Maps.CheckListItem import CheckListItem
from Entities.Maps.SimpleCheck import SimpleCheck


class Map:
    def __init__(self, map_datas, index_positions, tracker, active=False):
        self.box_checks = None
        self.position_draw = None
        self.surface_label = None
        self.checks_list_background_filename = None
        self.checks_list_background = None
        self.map_background = None
        self.map_image_filename = None
        self.map_datas = map_datas
        self.tracker = tracker
        self.index_positions = index_positions
        self.active = active
        self.checks_list_open = False
        self.checks_list = []
        self.current_block_checks = None
        self.processing()
        self.processing_checks()
        self.update()

    def processing(self):
        self.map_image_filename = self.map_datas[0]["Datas"]["Background"]
        self.checks_list_background_filename = self.map_datas[0]["Datas"]["SubMenuBackground"]
        self.update()

    def processing_checks(self):
        for check in self.map_datas[0]["ChecksList"]:
            if "Block" in check:
                block = BlockChecks(check["Block"]["Id"], check["Block"]["Name"], check["Block"]["Positions"], self)

                for check_item in check["Block"]["Checks"]:
                    temp_check = CheckListItem(check_item["Id"], check_item["Name"], check["Block"]["Positions"],
                                               check_item["Conditions"], self.tracker)
                    block.add_check(temp_check)

                self.checks_list.append(block)

            if "SimpleCheck" in check:
                simple_check = SimpleCheck(check["SimpleCheck"]["Id"], check["SimpleCheck"]["Name"], check["SimpleCheck"]["Positions"], self, check["SimpleCheck"]["Conditions"])
                self.checks_list.append(simple_check)


    def update(self):
        self.map_background = self.tracker.bank.addZoomImage(
            os.path.join(self.tracker.resources_path, self.map_image_filename))
        # if self.checks_list_open:
        self.checks_list_background = self.tracker.bank.addZoomImage(
            os.path.join(self.tracker.resources_path, self.checks_list_background_filename))

        if self.current_block_checks:
            temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32)
            temp_surface = temp_surface.convert_alpha()
            font = self.tracker.core_service.get_font("mapFontTitle")
            font_path = os.path.join(self.tracker.core_service.get_tracker_temp_path(), font["Name"])
            # color = (font["Colors"]["Normal"]["r"], font["Colors"]["Normal"]["g"], font["Colors"]["Normal"]["b"])
            color = self.tracker.core_service.get_color_from_font(font, "Normal")

            self.surface_label, self.position_draw = MainMenu.MainMenu.draw_text(
                text=self.current_block_checks.name,
                font_name=font_path,
                color=color,
                font_size=font["Size"] * self.tracker.core_service.zoom,
                surface=temp_surface,
                position=(0, self.map_datas[0]["Datas"]["LabelY"]),
                outline=2 * self.tracker.core_service.zoom)

            base_x = self.index_positions[0] * self.tracker.core_service.zoom
            base_x = base_x + (self.checks_list_background.get_rect().w / 2)
            base_x = base_x - (self.surface_label.get_rect().w / 2)
            self.position_draw = (base_x / self.tracker.core_service.zoom, self.position_draw[1])

            box_rect = self.map_datas[0]["Datas"]["DrawBoxRect"]
            self.box_checks = pygame.Rect(
                (box_rect["x"] * self.tracker.core_service.zoom) + self.checks_list_background.get_rect().x + (
                        self.index_positions[0] * self.tracker.core_service.zoom),
                (box_rect["y"] * self.tracker.core_service.zoom) + self.checks_list_background.get_rect().y + (
                        self.index_positions[1] * self.tracker.core_service.zoom),
                box_rect["w"] * self.tracker.core_service.zoom,
                box_rect["h"] * self.tracker.core_service.zoom)

            for check in self.checks_list:
                check.update()
            #     label_surface = check.get_surface_label()
            for i in range(0, len(self.current_block_checks.get_checks())):
                check = self.current_block_checks.get_checks()[i]
                label_surface = check.get_surface_label()
                #x = self.box_checks.x
                x = self.box_checks.x + (self.box_checks.w / 2) - (label_surface.get_rect().w / 2)
                y = self.box_checks.y + (label_surface.get_rect().h * i + 5)
                check.set_position_draw(x, y)
        else:
            for check in self.checks_list:
                check.update()

    def draw(self, screen):
        if self.active:
            screen.blit(self.map_background, (self.index_positions[0] * self.tracker.core_service.zoom,
                                              self.index_positions[1] * self.tracker.core_service.zoom))

            for check in self.checks_list:
                #if type(check) == BlockChecks:
                #    check.draw(screen)
                check.draw(screen)

            if self.current_block_checks:
                screen.blit(self.checks_list_background, (self.index_positions[0] * self.tracker.core_service.zoom,
                                                          self.index_positions[1] * self.tracker.core_service.zoom))

                screen.blit(self.surface_label, (self.position_draw[0] * self.tracker.core_service.zoom,
                                                 self.position_draw[1] * self.tracker.core_service.zoom))

                # pygame.draw.rect(screen, (255, 255, 255), self.box_checks)
                for check in self.current_block_checks.get_checks():
                    check.draw(screen)

    def click(self, mouse_position, button):
        # self.checks_list_open = True
        for check in self.checks_list:
            if type(check) == BlockChecks:
                if not self.checks_list_open:
                    if self.tracker.core_service.is_on_element(mouse_positions=mouse_position,
                                                               element_positons=check.get_position(),
                                                               element_dimension=(check.get_rect().w, check.get_rect().h)):
                        if button == 1:
                            print(check.name)
                            check.left_click(mouse_position)
                else:
                    if button == 1:
                        self.current_block_checks.left_click(mouse_position)

            if type(check) == SimpleCheck:
                if self.tracker.core_service.is_on_element(mouse_positions=mouse_position,
                                                           element_positons=check.get_position(),
                                                           element_dimension=(check.get_rect().w, check.get_rect().h)):
                    if button == 1:
                        check.left_click(mouse_position)


            # else:
            #     self.checks_list_open = False
            #     self.current_block_checks = None

        self.update()

    def get_name(self):
        return self.map_datas[0]["Datas"]["Name"]
