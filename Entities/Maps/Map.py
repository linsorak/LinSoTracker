import os
from math import ceil

import pygame

from Engine import MainMenu
from Entities.Maps.BlockChecks import BlockChecks
from Entities.Maps.CheckListItem import CheckListItem
from Entities.Maps.SimpleCheck import SimpleCheck


class Map:
    def __init__(self, map_datas, index_positions, tracker, active=False):
        self.position_pages_information = None
        self.surface_pages_information = None
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
        # CHECKS PAGES
        self.current_check_page = 1
        self.check_page_max = 1
        self.check_per_page = 1
        # END CHECKS PAGES
        self.left_arrow = None
        self.left_arrow_base = None
        self.right_arrow = None
        self.right_arrow_base = None
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
                simple_check = SimpleCheck(check["SimpleCheck"]["Id"], check["SimpleCheck"]["Name"],
                                           check["SimpleCheck"]["Positions"], self, check["SimpleCheck"]["Conditions"])
                self.checks_list.append(simple_check)

    def update(self):
        self.map_background = self.tracker.bank.addZoomImage(
            os.path.join(self.tracker.resources_path, self.map_image_filename))
        # if self.checks_list_open:
        self.checks_list_background = self.tracker.bank.addZoomImage(
            os.path.join(self.tracker.resources_path, self.checks_list_background_filename))

        self.left_arrow = self.tracker.bank.addZoomImage(
            os.path.join(self.tracker.resources_path, self.map_datas[0]["Datas"]["LeftArrow"]["Image"]))

        self.right_arrow = self.tracker.bank.addZoomImage(
            os.path.join(self.tracker.resources_path, self.map_datas[0]["Datas"]["RightArrow"]["Image"]))

        self.left_arrow_base = self.left_arrow.copy()
        self.right_arrow_base = self.right_arrow.copy()

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

            for check in self.current_block_checks.get_checks():
                check.update()
                check.show = False

            first_check = self.current_block_checks.get_checks()[0].get_surface_label()
            self.check_per_page = int(self.box_checks.h / first_check.get_rect().h)
            self.check_page_max = ceil(len(self.current_block_checks.get_checks()) / self.check_per_page)

            # self.current_check_page = 1
            index_start = 1 * ((self.current_check_page - 1) * self.check_per_page)
            index_end = index_start + self.check_per_page
            if index_end > len(self.current_block_checks.get_checks()):
                index_end = len(self.current_block_checks.get_checks())

            for i in range(index_start, index_end):
                index = 0 + (i - index_start)
                check = self.current_block_checks.get_checks()[i]
                label_surface = check.get_surface_label()
                x = self.box_checks.x + (self.box_checks.w / 2) - (label_surface.get_rect().w / 2)
                y = self.box_checks.y + (label_surface.get_rect().h * index + 5)
                check.set_position_draw(x, y)
                check.show = True

            if self.current_check_page == 1:
                self.tracker.core_service.convert_to_gs(self.left_arrow)
                self.left_arrow = self.tracker.core_service.set_image_transparent(image=self.left_arrow,
                                                                                  opacity_disable=0.6)
            if self.current_check_page != 1:
                self.left_arrow = self.left_arrow_base.copy()

            if self.current_check_page != self.check_page_max:
                self.right_arrow = self.right_arrow_base.copy()

            if self.current_check_page == self.check_page_max:
                self.tracker.core_service.convert_to_gs(self.right_arrow)
                self.right_arrow = self.tracker.core_service.set_image_transparent(image=self.right_arrow,
                                                                                   opacity_disable=0.6)


            temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32)
            temp_surface = temp_surface.convert_alpha()

            font = self.tracker.core_service.get_font("mapFontPagesIndicator")
            map_font_path = os.path.join(self.tracker.core_service.get_tracker_temp_path(), font["Name"])

            self.surface_pages_information, self.position_pages_information = MainMenu.MainMenu.draw_text(
                text="{}/{}".format(self.current_check_page, self.check_page_max),
                font_name=map_font_path,
                color=self.tracker.core_service.get_color_from_font(font, "Normal"),
                font_size=font["Size"] * self.tracker.core_service.zoom,
                surface=temp_surface,
                position=(0, 0),
                outline=1 * self.tracker.core_service.zoom)

            x_left, y_left, x_right, y_right = self.get_arrows_positions()
            x_space_between_arrows = x_right - (x_left + self.left_arrow.get_rect().w)
            x = (x_space_between_arrows / 2) - (self.surface_pages_information.get_rect().w / 2) + (x_left + self.left_arrow.get_rect().w)
            y = y_left + ((self.left_arrow.get_rect().h / 2) - (self.surface_pages_information.get_rect().h / 2))
            self.position_pages_information = (x, y)
        else:
            for check in self.checks_list:
                check.update()

    def draw(self, screen):
        if self.active:
            screen.blit(self.map_background, (self.index_positions[0] * self.tracker.core_service.zoom,
                                              self.index_positions[1] * self.tracker.core_service.zoom))

            for check in self.checks_list:
                # if type(check) == BlockChecks:
                #    check.draw(screen)
                check.draw(screen)

            if self.current_block_checks:
                screen.blit(self.checks_list_background, (self.index_positions[0] * self.tracker.core_service.zoom,
                                                          self.index_positions[1] * self.tracker.core_service.zoom))

                screen.blit(self.surface_label, (self.position_draw[0] * self.tracker.core_service.zoom,
                                                 self.position_draw[1] * self.tracker.core_service.zoom))

                # pygame.draw.rect(screen, (255, 255, 255), self.box_checks)
                for check in self.current_block_checks.get_checks():
                    if check.show:
                        check.draw(screen)

                # self.map_datas[0]["Datas"]["LeftArrow"]["Image"])
                x_left, y_left, x_right, y_right = self.get_arrows_positions()

                screen.blit(self.left_arrow, (x_left, y_left))
                screen.blit(self.right_arrow, (x_right, y_right))
                screen.blit(self.surface_pages_information, self.position_pages_information)

    def get_positions_from_index_positions(self, index_positions_index, position):
        return (self.index_positions[index_positions_index] * self.tracker.core_service.zoom) + (
                position * self.tracker.core_service.zoom)

    def get_arrows_positions(self):
        x_left = self.get_positions_from_index_positions(0, self.map_datas[0]["Datas"]["LeftArrow"][
            "Positions"][
            "x"])
        y_left = self.get_positions_from_index_positions(1, self.map_datas[0]["Datas"]["LeftArrow"][
            "Positions"][
            "y"])

        x_right = self.get_positions_from_index_positions(0, self.map_datas[0]["Datas"]["RightArrow"][
            "Positions"][
            "x"])
        y_right = self.get_positions_from_index_positions(1, self.map_datas[0]["Datas"]["RightArrow"][
            "Positions"][
            "y"])

        return x_left, y_left, x_right, y_right

    def click(self, mouse_position, button):
        # self.checks_list_open = True
        for check in self.checks_list:
            if type(check) == BlockChecks:
                if not self.checks_list_open:
                    if self.tracker.core_service.is_on_element(mouse_positions=mouse_position,
                                                               element_positons=check.get_position(),
                                                               element_dimension=(
                                                                       check.get_rect().w, check.get_rect().h)):
                        if button == 1:
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

        self.update()

    def left_arrow_click(self):
        if self.current_check_page > 1:
            self.current_check_page -= 1
            self.update()

    def right_arrow_click(self):
        if self.current_check_page < self.check_page_max:
            self.current_check_page += 1
            self.update()

    def get_name(self):
        return self.map_datas[0]["Datas"]["Name"]
