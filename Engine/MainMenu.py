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


class MainMenu:
    def __init__(self):
        self.official_template = None
        self.new_version = None
        self.menu_content = []
        self.menu_a = None
        self.right_arrow_positions = None
        self.left_arrow_positions = None
        self.current_page = 1
        self.max_pages = 2
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
        self.menu_json_data = None
        self.resources_path = None
        self.fade_engine = FadeAnimation(fadeStart=0, fadeEnd=255, fadeStep=8, mode=FadeMode.FADE)
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
        btn_paypal_w = 125
        btn_paypal_h = 50
        self.btn_paypal = Rect(0, dimensions[1] - btn_paypal_h, btn_paypal_w, btn_paypal_h)
        btn_discord_w = 105
        btn_discord_h = 70
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
        self.arrow_left = self.bank.addImage(os.path.join(self.resources_path, "arrowLeft.png"))
        self.arrow_right = self.bank.addImage(os.path.join(self.resources_path, "arrowRight.png"))
        self.content = self.menu_json_data[0]["BoxTrackerContentImage"]
        self.content = self.bank.addImage(os.path.join(self.resources_path, self.content))
        self.content_error = self.menu_json_data[0]["BoxTrackerContentImageNotCompatible"]
        self.content_error = self.bank.addImage(os.path.join(self.resources_path, self.content_error))
        self.selected = self.bank.addImage(os.path.join(self.resources_path, "selected.png"))
        self.selected_error = self.bank.addImage(os.path.join(self.resources_path, "selected-error.png"))
        session_font = self.menu_json_data[0]["HomeMenuFont"]
        session_font_color = session_font["Colors"]
        self.font_data = {
            "path": os.path.join(self.resources_path, session_font["Name"]),
            "size": session_font["Size"],
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
            if self.current_page == 1:
                self.core_service.convert_to_gs(l_arrow)
                l_arrow = self.core_service.set_image_transparent(image=l_arrow, opacity_disable=0.6)

            if self.current_page == self.max_pages:
                self.core_service.convert_to_gs(r_arrow)
                r_arrow = self.core_service.set_image_transparent(image=r_arrow, opacity_disable=0.6)

            x_left_arrow = screen.get_rect().w - (l_arrow.get_rect().w * 5)
            y_left_arrow = screen.get_rect().h - (l_arrow.get_rect().h * 3.5)
            x_right_arrow = screen.get_rect().w - (l_arrow.get_rect().w * 1.5)
            y_right_arrow = screen.get_rect().h - (l_arrow.get_rect().h * 3.5)
            self.left_arrow_positions = (x_left_arrow, y_left_arrow)
            self.right_arrow_positions = (x_right_arrow, y_right_arrow)

            screen.blit(l_arrow, self.left_arrow_positions)
            screen.blit(r_arrow, self.right_arrow_positions)

            temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32)
            temp_surface = temp_surface.convert_alpha()
            pages, pos_pages = self.draw_text(text="{}/{}".format(self.current_page, self.max_pages),
                                              font_name=self.font_data["path"],
                                              color=self.font_data["color_normal"],
                                              font_size=self.font_data["size"],
                                              surface=temp_surface,
                                              position=(0, 0),
                                              outline=1)
            space_between_arrow = x_right_arrow - x_left_arrow
            x_pages = (space_between_arrow / 2 - pages.get_rect().w / 2) + x_left_arrow + (l_arrow.get_rect().w / 2)
            y_pages = (l_arrow.get_rect().h / 2) - (pages.get_rect().h / 2) + y_left_arrow

            screen.blit(pages, (x_pages, y_pages))

            min_value = (self.current_page - 1) * 3
            max_value = self.current_page * 3

            if max_value > len(self.template_list):
                max_value = len(self.template_list)

            self.draw_templates = max_value - min_value

            self.menu_content = []
            for i in range(min_value, max_value):
                offset = 3 * (self.current_page - 1)
                content_x = screen.get_rect().w - self.content.get_rect().w
                content_y = 180 + ((self.content.get_rect().h + 10) * (i - offset))
                icon_x = content_x + 29
                icon_y = content_y + 2
                title_x = icon_x + self.template_list[i]["icon"].get_rect().w + 15
                title_y = content_y + 6
                screen.blit(self.content, (content_x, content_y))
                screen.blit(self.template_list[i]["icon"], (icon_x, icon_y))
                surf_title, pos_title = self.draw_text(
                    text=self.template_list[i]["information"]["Informations"]["Name"],
                    font_name=self.font_data["path"],
                    color=self.font_data["color_normal"],
                    font_size=self.font_data["size"],
                    surface=screen,
                    position=(title_x, title_y),
                    outline=1)
                author_x = title_x
                author_y = title_y + surf_title.get_rect().h + 2
                surf_author, pos_author = self.draw_text(
                    text="Author : {}".format(self.template_list[i]["information"]["Informations"]["Creator"]),
                    font_name=self.font_data["path"],
                    color=self.font_data["color_normal"],
                    font_size=self.font_data["size"] - 4,
                    surface=screen,
                    position=(author_x, author_y),
                    outline=1)
                version_x = title_x
                version_y = author_y + surf_author.get_rect().h + 2
                surf_version, pos_version = self.draw_text(
                    text="Version : {}".format(self.template_list[i]["information"]["Informations"]["Version"]),
                    font_name=self.font_data["path"],
                    color=self.font_data["color_normal"],
                    font_size=self.font_data["size"] - 4,
                    surface=screen,
                    position=(version_x, version_y),
                    outline=1)

                if "official" in self.template_list[i]:
                    official_x = screen.get_rect().w - 75
                    official_y = version_y
                    surf_official, pos_official = self.draw_text(
                        text="OFFICIAL",
                        font_name=self.font_data["path"],
                        color=self.font_data["color_official"],
                        font_size=self.font_data["size"] - 4,
                        surface=screen,
                        position=(official_x, official_y),
                        outline=1)

                    version_official_x = version_x + surf_version.get_rect().w
                    version_official_y = version_y
                    surf_version_official, surf_version_official = self.draw_text(
                        text=" | Lastest version : {}".format(self.template_list[i]["official"]),
                        font_name=self.font_data["path"],
                        color=self.font_data["color_normal"],
                        font_size=self.font_data["size"] - 4,
                        surface=screen,
                        position=(version_official_x, version_official_y),
                        outline=1)


                self.menu_content.append({"positions": (content_x, content_y),
                                          "dimensions": (self.content.get_rect().w, self.content.get_rect().h),
                                          "template": self.template_list[i]})

                if self.moved_tracker:
                    self.fade_engine.update()
                    self.fade_value = self.fade_engine.getFadeValue()
                    transparent_illustration = self.illustration.copy()
                    transparent_illustration.fill((255, 255, 255, self.fade_value),
                                                  special_flags=pygame.BLEND_RGBA_MULT)
                    glow = self.selected.copy()
                    glow.fill((255, 255, 255, self.fade_value), special_flags=pygame.BLEND_RGBA_MULT)
                    screen.blit(transparent_illustration, (0, 0))
                    screen.blit(glow, self.selected_position)

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
            template_data = {
                "filename": os.path.basename(file).replace(".template", ""),
                "information": data[0],
                "icon": pygame.image.load(io.BytesIO(tracker_icon)),
                "illustration": pygame.image.load(io.BytesIO(tracker_illustration))
            }
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

        self.max_pages = int(len(self.template_list) / 3) + self.current_page

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
                        self.set_tracker(menu["template"]["filename"])
        else:
            self.loaded_tracker.click(mouse_position, button)

    def mouse_move(self, mouse_position):
        if not self.loaded_tracker:
            is_on_menu = False
            if self.menu_content:
                for menu in self.menu_content:
                    if self.core_service.is_on_element(mouse_positions=mouse_position,
                                                       element_positons=menu["positions"],
                                                       element_dimension=menu["dimensions"]):
                        if self.moved_tracker != menu["template"]["filename"]:
                            self.fade_engine.reset()
                            self.illustration = menu["template"]["illustration"]
                            self.moved_tracker = menu["template"]["filename"]
                            self.selected_position = (menu["positions"][0] + 19, menu["positions"][1] - 8)
                            is_on_menu = True
                            break
                        else:
                            is_on_menu = True
                            break

                if not is_on_menu:
                    self.moved_tracker = None
                    self.illustration = None
                    self.moved_tracker = None
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
