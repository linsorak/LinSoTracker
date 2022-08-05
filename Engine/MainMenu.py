import glob
import io
import json
import os
from urllib.error import URLError
from urllib.request import urlopen
from zipfile import ZipFile

import pygame
from pygame.rect import Rect

from Engine.FadeAnimation import FadeAnimation, FadeMode
from Engine.Menu import Menu
from Engine.Tracker import Tracker
from Tools import ptext
from Tools.Bank import Bank
from Tools.CoreService import CoreService
from Tools.TemplateChecker import TemplateChecker


class MainMenu:
    def __init__(self):
        # OFFSETS
        self.x_offset = -60
        self.y_offset = 60
        self.space_offset = 10

        self.max_row = 3
        self.max_column = 5

        self.max_icon_per_page = self.max_row * self.max_column
        self.current_page = 1
        self.max_pages = None


        self.official_template = None
        self.new_version = None
        self.menu_content = []
        self.menu_a = None
        self.right_arrow_positions = None
        self.left_arrow_positions = None
        self.draw_templates = 0
        self.font_data = None
        self.selected_error = None
        self.selected = None
        self.selected_position = None
        self.content_error = None
        self.content = None
        self.arrow_right = None
        self.arrow_left = None
        self.icon = None
        self.background_image = None
        self.description_menu = None
        self.menu_json_data = None
        self.resources_path = None
        self.selected_menu_index = None
        self.fade_engine = FadeAnimation(fadeStart=0, fadeEnd=255, fadeStep=45, mode=FadeMode.FADE)
        self.illustration = None
        self.moved_tracker = None
        self.fade_value = self.fade_engine.getFadeValue()
        self.core_service = CoreService()
        self.bank = Bank()
        self.template_directory = os.path.join(self.core_service.get_app_path(), "templates")
        self.template_list = []
        self.extract_data()
        self.init_menu()
        self.set_check()
        self.process_templates_list()
        self.loaded_tracker = None
        self.btn_paypal = None
        self.btn_discord = None
        self.init_btns()

    def init_btns(self):
        dimensions = self.get_dimension()
        btn_paypal_w = 200
        btn_paypal_h = 100
        self.btn_paypal = Rect(0, dimensions[1] - btn_paypal_h, btn_paypal_w, btn_paypal_h)
        btn_discord_w = 120
        btn_discord_h = 100
        self.btn_discord = Rect(dimensions[0] - btn_discord_w, dimensions[1] - btn_discord_h, btn_discord_w,
                                btn_discord_h)

    def extract_data(self):
        filename = os.path.join(self.core_service.get_app_path(), "tracker.data")
        self.resources_path = os.path.join(self.core_service.get_temp_path(), "tracker")
        self.core_service.create_directory(self.resources_path)
        if os.path.isfile(filename):
            zip = ZipFile(filename)
            zip.extractall(self.resources_path)
            zip.close()

    def init_menu(self):
        filename = os.path.join(self.resources_path, "home.json")
        if os.path.isfile(filename):
            with open(filename, 'r') as file:
                self.menu_json_data = json.load(file)

    def set_check(self):
        self.new_version = self.core_service.get_new_version()
        self.official_template = self.core_service.get_official_template()

    def initialization(self):
        self.background_image = self.menu_json_data[0]["BackgroundImage"]
        self.background_image = self.bank.addImage(os.path.join(self.resources_path, self.background_image))
        self.icon = self.menu_json_data[0]["Icon"]
        self.icon = self.bank.addImage(os.path.join(self.resources_path, self.icon))
        self.arrow_left = self.bank.addImage(os.path.join(self.resources_path, "arrow-left.png"))
        self.arrow_right = self.bank.addImage(os.path.join(self.resources_path, "arrow-right.png"))
        self.content = self.menu_json_data[0]["BoxTrackerContentImage"]
        self.content = self.bank.addImage(os.path.join(self.resources_path, self.content))
        self.content_error = self.menu_json_data[0]["BoxTrackerContentImageNotCompatible"]
        self.content_error = self.bank.addImage(os.path.join(self.resources_path, self.content_error))
        self.selected = self.bank.addImage(os.path.join(self.resources_path, "glow.png"))
        self.selected_error = self.bank.addImage(os.path.join(self.resources_path, "glow-error.png"))
        self.description_menu = self.bank.addImage(os.path.join(self.resources_path, self.menu_json_data[0]["DescriptionBox"]))

        session_font = self.menu_json_data[0]["HomeMenuFont"]
        session_font_color = session_font["Colors"]
        self.font_data = {
            "path": os.path.join(self.resources_path, session_font["Name"]),
            "size": session_font["Size"],
            "description_size": session_font["DescriptionSize"],
            "page_size": session_font["PageSize"],
            "title_size": session_font["TitleSize"],
            "color_normal": (
                session_font_color["Normal"]["r"], session_font_color["Normal"]["g"],
                session_font_color["Normal"]["b"]),
            "color_error": (
                session_font_color["Error"]["r"], session_font_color["Error"]["g"], session_font_color["Error"]["b"]),
            "color_update": (
                session_font_color["Update"]["r"], session_font_color["Update"]["g"],
                session_font_color["Update"]["b"]),
            "color_official": (
                session_font_color["Official"]["r"], session_font_color["Official"]["g"],
                session_font_color["Official"]["b"])
        }

    def get_dimension(self):
        dimension = self.menu_json_data[0]["Dimensions"]
        return dimension["width"], dimension["height"]

    def get_icon(self):
        return self.icon

    def draw(self, screen):
        if not self.loaded_tracker:
            screen.blit(self.background_image, (0, 0))
            l_arrow = self.arrow_left.copy()
            r_arrow = self.arrow_right.copy()

            x_left_arrow = 285
            y_left_arrow = 530
            x_right_arrow = x_left_arrow + self.content.get_rect().w
            y_right_arrow = y_left_arrow
            self.left_arrow_positions = (x_left_arrow, y_left_arrow)
            self.right_arrow_positions = (x_right_arrow, y_right_arrow)

            if self.current_page == 1:
                self.core_service.convert_to_gs(l_arrow)
                l_arrow = self.core_service.set_image_transparent(image=l_arrow, opacity_disable=0.6)

            if self.current_page == self.max_pages:
                self.core_service.convert_to_gs(r_arrow)
                r_arrow = self.core_service.set_image_transparent(image=r_arrow, opacity_disable=0.6)

            index_templates = 0 + (self.max_icon_per_page * (self.current_page - 1))
            self.menu_content = []
            for i in range(0, self.max_row):
                for j in range(0, self.max_column):
                    if len(self.template_list) > index_templates:
                        content_x = (self.content.get_rect().w * (j + 1) + self.content.get_rect().w) + self.x_offset + (self.space_offset * j)
                        content_y = (self.content.get_rect().h * (i + 1) + self.content.get_rect().h) + self.y_offset + (self.space_offset * i)
                        icon_x = content_x + 10
                        icon_y = content_y + 5
                        if self.template_list[index_templates]["valid"]:
                            screen.blit(self.content, (content_x, content_y))
                        else:
                            screen.blit(self.content_error, (content_x, content_y))
                        screen.blit(self.template_list[index_templates]["icon"], (icon_x, icon_y))

                        self.menu_content.append({"positions": (content_x, content_y),
                                                  "dimensions": (self.content.get_rect().w, self.content.get_rect().h),
                                                  "template": self.template_list[index_templates]})


                        index_templates += 1

            screen.blit(l_arrow, self.left_arrow_positions)
            screen.blit(r_arrow, self.right_arrow_positions)

            temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32)
            temp_surface = temp_surface.convert_alpha()
            pages, pos_pages = self.draw_text(text="{}/{}".format(self.current_page, self.max_pages),
                                              font_name=self.font_data["path"],
                                              color=self.font_data["color_normal"],
                                              font_size=self.font_data["page_size"],
                                              surface=temp_surface,
                                              position=(0, 0),
                                              outline=1)
            space_between_arrow = x_right_arrow - x_left_arrow
            x_pages = (space_between_arrow / 2 - pages.get_rect().w / 2) + x_left_arrow + (l_arrow.get_rect().w / 2)
            y_pages = (l_arrow.get_rect().h / 2) - (pages.get_rect().h / 2) + y_left_arrow

            screen.blit(pages, (x_pages, y_pages))

            surf_title, pos_title = self.draw_text(
                text="{} v{} - Developed by LinSoraK#7235".format(self.core_service.app_name,
                                                                  self.core_service.version),
                font_name=self.font_data["path"],
                color=self.font_data["color_normal"],
                font_size=self.font_data["size"],
                surface=screen,
                position=(5, 5),
                outline=1)

            if self.new_version:
                surf_update, pos_update = self.draw_text(
                    text="The version {} is now available. Please update!".format(self.new_version),
                    font_name=self.font_data["path"],
                    color=self.font_data["color_update"],
                    font_size=self.font_data["size"],
                    surface=screen,
                    position=(5, surf_title.get_rect().h + 5),
                    outline=1)

            if self.moved_tracker:
                template_valid = self.template_list[self.selected_menu_index]["valid"]

                self.fade_engine.update()
                self.fade_value = self.fade_engine.getFadeValue()
                transparent_illustration = self.illustration.copy()
                transparent_illustration.fill((255, 255, 255, self.fade_value),
                                              special_flags=pygame.BLEND_RGBA_MULT)
                if template_valid:
                    glow = self.selected.copy()
                else:
                    glow = self.selected_error.copy()

                glow_position_x, glow_position_y = self.selected_position
                glow_position_x = glow_position_x - 38
                glow_position_y = glow_position_y - 15
                glow.fill((255, 255, 255, self.fade_value), special_flags=pygame.BLEND_RGBA_MULT)

                description_menu = self.description_menu.copy()
                description_menu.fill((255, 255, 255, self.fade_value),
                                              special_flags=pygame.BLEND_RGBA_MULT)

                x_description_menu = screen.get_rect().w - description_menu.get_rect().w
                y_description_menu = 410

                screen.blit(transparent_illustration, (0, 0))
                screen.blit(glow, (glow_position_x, glow_position_y))
                screen.blit(description_menu, (x_description_menu, y_description_menu))


                x_title = x_description_menu + 17
                y_title = y_description_menu + 13

                self.draw_text(
                    text=self.template_list[self.selected_menu_index]["information"]["Informations"]["Name"],
                    font_name=self.font_data["path"],
                    color=self.font_data["color_normal"],
                    font_size=self.font_data["title_size"],
                    surface=screen,
                    position=(x_title, y_title),
                    outline=1)

                x_creator = x_title + 15
                y_creator = y_title + 55
                self.draw_text(
                    text="Creator : {}".format(self.template_list[self.selected_menu_index]["information"]["Informations"]["Creator"]),
                    font_name=self.font_data["path"],
                    color=self.font_data["color_normal"],
                    font_size=self.font_data["description_size"],
                    surface=screen,
                    position=(x_creator, y_creator),
                    outline=1.5)

                x_version = x_creator
                y_version = y_creator + 22
                self.draw_text(
                    text="Version : {}".format(self.template_list[self.selected_menu_index]["information"]["Informations"]["Version"]),
                    font_name=self.font_data["path"],
                    color=self.font_data["color_normal"],
                    font_size=self.font_data["description_size"],
                    surface=screen,
                    position=(x_version, y_version),
                    outline=1.5)

                if "official" in self.template_list[self.selected_menu_index]:
                    x_official = x_description_menu + description_menu.get_rect().w - 90
                    y_official = y_description_menu + description_menu.get_rect().h - 35
                    self.draw_text(
                        text="OFFICIAL",
                        font_name=self.font_data["path"],
                        color=self.font_data["color_official"],
                        font_size=self.font_data["size"],
                        surface=screen,
                        position=(x_official, y_official),
                        outline=1.5)

                if not self.template_list[self.selected_menu_index]["valid"]:
                    x_not_valid = x_description_menu + 17
                    y_not_valid = y_description_menu + description_menu.get_rect().h - 35
                    self.draw_text(
                        text="NOT VALID - PLEASE UPDATE",
                        font_name=self.font_data["path"],
                        color=self.font_data["color_error"],
                        font_size=self.font_data["size"],
                        surface=screen,
                        position=(x_not_valid, y_not_valid),
                        outline=1.5)
        else:
            self.loaded_tracker.draw(screen)

    def process_templates_list(self):
        temp_list = []
        for file in glob.glob("{}{}*.template".format(self.template_directory, os.sep)):
            archive = ZipFile(file, 'r')
            tracker_json = archive.read("tracker.json")
            tracker_icon = archive.read("icon.png")
            tracker_illustration = archive.read("illustration.png")

            data = json.loads(tracker_json)

            template_checker = TemplateChecker(data)

            template_data = {
                "filename": os.path.basename(file).replace(".template", ""),
                "information": data[0],
                "icon": pygame.image.load(io.BytesIO(tracker_icon)),
                "illustration": pygame.image.load(io.BytesIO(tracker_illustration)),
                "valid": template_checker.is_valid()
            }


            print(template_data["filename"], template_checker.errors)

            if self.official_template:
                for off_template in self.official_template:
                    if off_template["template_name"] == template_data["filename"]:
                        template_data["official"] = off_template["lastest_version"]
                        self.template_list.append(template_data)
                        break

            if not "official" in template_data:
                temp_list.append(template_data)

        for none_official in temp_list:
            self.template_list.append(none_official)

        self.max_pages = int(len(self.template_list) / self.max_icon_per_page) + self.current_page

    @staticmethod
    def draw_text(text, font_name, color, font_size, surface, position, outline=2):
        return ptext.draw(str(text), position, fontname=font_name, antialias=True,
                          owidth=outline, ocolor=(0, 0, 0), color=color, fontsize=font_size, surf=surface)

    def click(self, mouse_position, button):
        if not self.loaded_tracker:
            if button == 1:
                if self.core_service.is_on_element(mouse_positions=mouse_position,
                                                   element_positons=self.left_arrow_positions, element_dimension=(
                                self.arrow_left.get_rect().w, self.arrow_left.get_rect().h)):
                    if self.current_page > 1:
                        self.current_page -= 1

                if self.core_service.is_on_element(mouse_positions=mouse_position,
                                                   element_positons=self.right_arrow_positions, element_dimension=(
                                self.arrow_right.get_rect().w, self.arrow_right.get_rect().h)):
                    if self.current_page < self.max_pages:
                        self.current_page += 1

                if self.core_service.is_on_element(mouse_positions=mouse_position,
                                                   element_positons=(self.btn_discord.left, self.btn_discord.top),
                                                   element_dimension=(self.btn_discord.w, self.btn_discord.h)):
                    Menu.open_discord()

                if self.core_service.is_on_element(mouse_positions=mouse_position,
                                                   element_positons=(self.btn_paypal.left, self.btn_paypal.top),
                                                   element_dimension=(self.btn_paypal.w, self.btn_paypal.h)):
                    Menu.open_paypal()

                for menu in self.menu_content:
                    if self.core_service.is_on_element(mouse_positions=mouse_position,
                                                       element_positons=menu["positions"],
                                                       element_dimension=menu["dimensions"]):
                        if menu["template"]["valid"]:
                            self.set_tracker(menu["template"]["filename"])
        else:
            self.loaded_tracker.click(mouse_position, button)

    def mouse_move(self, mouse_position):
        if not self.loaded_tracker:
            is_on_menu = False
            if self.menu_content:
                for i in range(0, len(self.menu_content)):
                # for menu in self.menu_content:
                    menu = self.menu_content[i]
                    if self.core_service.is_on_element(mouse_positions=mouse_position,
                                                       element_positons=menu["positions"],
                                                       element_dimension=menu["dimensions"]):

                        if self.moved_tracker != menu["template"]["filename"]:
                            self.fade_engine.reset()
                            self.illustration = menu["template"]["illustration"]
                            # self.moved_tracker = menu["template"]["filename"]
                            self.moved_tracker = menu["template"]["filename"]
                            self.selected_menu_index = i + ((self.max_row * self.max_column) * (self.current_page - 1))
                            self.selected_position = (menu["positions"][0] + 19, menu["positions"][1] - 8)
                            is_on_menu = True
                            break
                        else:
                            is_on_menu = True
                            break

                if not is_on_menu:
                    self.moved_tracker = None
                    self.illustration = None
                    self.selected_menu_index = None
                    self.fade_engine.reset()

    def set_tracker(self, tracker_name):
        self.loaded_tracker = Tracker(tracker_name, self)

    def reset_tracker(self):
        self.loaded_tracker.delete_data()
        del self.loaded_tracker
        self.loaded_tracker = None
        dimension = self.get_dimension()
        pygame.display.set_mode((dimension[0], dimension[1]))
        self.core_service.setgamewindowcenter(x=dimension[0], y=dimension[1])

    def keyup(self, button, screen):
        if self.loaded_tracker:
            self.loaded_tracker.keyup(button, screen)

    def events(self, events):
        if self.loaded_tracker:
            self.loaded_tracker.events(events)
