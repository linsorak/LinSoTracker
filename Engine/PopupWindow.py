import os
from math import ceil

import pygame

from Engine import MainMenu


class PopupWindow:
    def __init__(self, tracker, index_positions):
        self.tracker = tracker
        self.index_positions = index_positions
        self.title_font = None
        self.title = None
        self.arrow_right_image_path = None
        self.arrow_left_image_path = None
        self.background_image_path = None
        self.list_items = None
        self.open = False
        self.box_rect = None
        # CHECKS PAGES
        self.current_check_page = 1
        self.check_page_max = 1
        self.check_per_page = 1
        # END CHECKS PAGES
        self.left_arrow = None
        self.left_arrow_base = None
        self.right_arrow = None
        self.right_arrow_base = None

        self.left_arrow_positions = None
        self.right_arrow_positions = None

        self.background_image = None

    def set_background_image_path(self, background_image_path):
        self.background_image_path = background_image_path

    def set_arrow_left_image_path(self, arrow_left_image_path):
        self.arrow_left_image_path = arrow_left_image_path

    def set_arrow_right_image_path(self, arrow_right_image_path):
        self.arrow_right_image_path = arrow_right_image_path

    def set_title(self, title):
        self.title = title

    def set_title_font(self, title_font):
        self.title_font = title_font

    def set_title_label_position_y(self, title_label_position_y):
       self.title_label_position_y = title_label_position_y

    def update(self):
        self.background_image = self.tracker.bank.addZoomImage(
            os.path.join(self.tracker.resources_path, self.background_image_path))

        self.left_arrow = self.tracker.bank.addZoomImage(
            os.path.join(self.tracker.resources_path, self.arrow_left_image_path))

        self.right_arrow = self.tracker.bank.addZoomImage(
            os.path.join(self.tracker.resources_path, self.arrow_right_image_path))

        self.left_arrow_base = self.left_arrow.copy()
        self.right_arrow_base = self.right_arrow.copy()

        temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32)
        temp_surface = temp_surface.convert_alpha()
        font_path = os.path.join(self.tracker.core_service.get_tracker_temp_path(), self.title_font["Name"])
        color = self.tracker.core_service.get_color_from_font(self.title_font, "Normal")

        self.surface_label, self.position_draw = MainMenu.MainMenu.draw_text(
            text=self.title,
            font_name=font_path,
            color=color,
            font_size=self.title_font["Size"] * self.tracker.core_service.zoom,
            surface=temp_surface,
            position=(0, self.title_label_position_y),
            outline=2 * self.tracker.core_service.zoom)

        base_x = self.index_positions[0] * self.tracker.core_service.zoom
        base_x = base_x + (self.background_image.get_rect().w / 2)
        base_x = base_x - (self.surface_label.get_rect().w / 2)
        self.position_draw = (base_x / self.tracker.core_service.zoom, self.position_draw[1])

        try:
            get_check = self.list_items.get_checks()
        except AttributeError:
            get_check = self.list_items

        first_check = get_check[0].get_surface_label()
        self.check_per_page = int(self.box_rect.h / first_check.get_rect().h)
        self.check_page_max = ceil(len(get_check) / self.check_per_page)

        # self.current_check_page = 1
        index_start = 1 * ((self.current_check_page - 1) * self.check_per_page)
        index_end = index_start + self.check_per_page
        if index_end > len(get_check):
            index_end = len(get_check)

        for check in get_check:
            check.update()
            check.show = False

        for i in range(index_start, index_end):
            index = 0 + (i - index_start)
            check = get_check[i]
            label_surface = check.get_surface_label()
            x = self.box_rect.x + (self.box_rect.w / 2) - (label_surface.get_rect().w / 2)
            y = self.box_rect.y + (label_surface.get_rect().h * index + 5)
            check.set_position_draw(x, y)
            check.show = True
        self.left_arrow = self.left_arrow_base.copy()
        self.right_arrow = self.right_arrow_base.copy()
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
        x = (x_space_between_arrows / 2) - (self.surface_pages_information.get_rect().w / 2) + (
                    x_left + self.left_arrow.get_rect().w)
        y = y_left + ((self.left_arrow.get_rect().h / 2) - (self.surface_pages_information.get_rect().h / 2))
        self.position_pages_information = (x, y)

    def draw(self, screen):
        screen.blit(self.background_image, (self.index_positions[0] * self.tracker.core_service.zoom,
                                            self.index_positions[1] * self.tracker.core_service.zoom))

        screen.blit(self.surface_label, (self.position_draw[0] * self.tracker.core_service.zoom,
                                         self.position_draw[1] * self.tracker.core_service.zoom))

        # pygame.draw.rect(screen, (255, 255, 255), self.box_rect)
        try:
            for check in self.list_items.get_checks():
                if check.show:
                    check.draw(screen)
        except AttributeError:
            for check in self.list_items:
                if check.show:
                    check.draw(screen)

        x_left, y_left, x_right, y_right = self.get_arrows_positions()

        screen.blit(self.left_arrow, (x_left, y_left))
        screen.blit(self.right_arrow, (x_right, y_right))
        screen.blit(self.surface_pages_information, self.position_pages_information)

    def is_open(self):
        return self.open

    def get_box_rect(self):
        return self.box_rect

    def set_box_rect(self, box_rect):
        self.box_rect = box_rect

    def left_click(self, mouse_position):
        click_found = False
        try:
            get_check = self.list_items.get_checks()
        except AttributeError:
            get_check = self.list_items

        for check in get_check:
            if self.tracker.core_service.is_on_element(mouse_positions=mouse_position,
                                                                       element_positons=check.get_position_draw(),
                                                                       element_dimension=check.get_dimensions()):
                click_found = True
                check.left_click()
            # self.right_arrow_click()

        x_left, y_left, x_right, y_right = self.get_arrows_positions()

        if self.tracker.core_service.is_on_element(mouse_positions=mouse_position,
                                                       element_positons=(x_left, y_left),
                                                       element_dimension=(
                                                               self.left_arrow.get_rect().w,
                                                               self.left_arrow.get_rect().h)):
            self.left_arrow_click()
            click_found = True
        elif self.tracker.core_service.is_on_element(mouse_positions=mouse_position,
                                                         element_positons=(x_right, y_right),
                                                         element_dimension=(
                                                                 self.right_arrow.get_rect().w,
                                                                 self.right_arrow.get_rect().h)):
            self.right_arrow_click()
            click_found = True

        if not click_found:
            self.open = False
            self.current_check_page = 1
    def set_list_items(self, list_items):
        self.list_items = list_items

    def set_arrows_positions(self, left, right):
        self.left_arrow_positions = ((left[0] + self.index_positions[0]) * self.tracker.core_service.zoom, (left[1] + self.index_positions[1]) * self.tracker.core_service.zoom)
        self.right_arrow_positions = ((right[0] + self.index_positions[0]) * self.tracker.core_service.zoom, (right[1] + self.index_positions[1]) * self.tracker.core_service.zoom)

    def get_arrows_positions(self):
        return self.left_arrow_positions[0], self.left_arrow_positions[1], self.right_arrow_positions[0], \
               self.right_arrow_positions[1]

    def left_arrow_click(self):
        if self.current_check_page > 1:
            self.current_check_page -= 1
            self.update()

    def right_arrow_click(self):
        if self.current_check_page < self.check_page_max:
            self.current_check_page += 1
            self.update()

    def get_data(self):
        try:
            get_check = self.list_items.get_checks()
        except AttributeError:
            get_check = self.list_items

        checks_save = []

        for check in get_check:
            checks_save.append(check.get_data())

        data = {
            "title": self.title,
            "checks": checks_save
        }
        return data

    def set_data(self, datas):
        try:
            get_check = self.list_items.get_checks()
        except AttributeError:
            get_check = self.list_items

        checks_datas = datas["checks"]

        for data in checks_datas:
            for check in get_check:
                if (data["id"] == check.id) and (data["name"] == check.name):
                    check.set_data(data)
                    break

        self.update()

