import glob
import io
import json
import os
from zipfile import ZipFile

import pygame

from Tools import ptext
from Tools.Bank import Bank
from Tools.CoreService import CoreService


class MainMenu:
    def __init__(self):
        self.font_data = None
        self.selected_error = None
        self.selected = None
        self.content_error = None
        self.content = None
        self.arrow_right = None
        self.arrow_left = None
        self.icon = None
        self.background_image = None
        self.menu_json_data = None
        self.resources_path = None
        self.core_service = CoreService()
        self.bank = Bank()
        self.template_directory = os.path.join(self.core_service.get_app_path(), "templates")
        self.template_list = []
        self.extract_data()
        self.init_menu()
        self.process_templates_list()

    def extract_data(self):
        filename = os.path.join(self.core_service.get_app_path(), "tracker.data")
        self.resources_path = os.path.join(self.core_service.get_temp_path(), "tracker")
        self.core_service.create_directory(self.resources_path)
        print(self.resources_path)
        if os.path.isfile(filename):
            zip = ZipFile(filename)
            zip.extractall(self.resources_path)
            zip.close()

    def init_menu(self):
        filename = os.path.join(self.resources_path, "home.json")
        if os.path.isfile(filename):
            with open(filename, 'r') as file:
                self.menu_json_data = json.load(file)
                print(self.menu_json_data)

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
            "color_normal": (session_font_color["Normal"]["r"], session_font_color["Normal"]["g"], session_font_color["Normal"]["b"]),
            "color_error": (session_font_color["Error"]["r"], session_font_color["Error"]["g"], session_font_color["Error"]["b"])
        }
        print(self.font_data["size"])

    def get_dimension(self):
        dimension = self.menu_json_data[0]["Dimensions"]
        return dimension["width"], dimension["height"]

    def get_icon(self):
        return self.icon

    def draw(self, screen):
        screen.blit(self.background_image, (0, 0))
        self.draw_text(text="LinSoTracker BETA Version",
                       font_name=self.font_data["path"],
                       color=self.font_data["color_normal"],
                       font_size=self.font_data["size"],
                       surface=screen,
                       position=(5, 5),
                       outline=1)
        for i in range(0, len(self.template_list)):
            content_x = screen.get_rect().w - self.content.get_rect().w
            content_y = 180 + ((self.content.get_rect().h + 10) * i)
            icon_x = content_x + 29
            icon_y = content_y + 2
            title_x = icon_x + self.template_list[i]["icon"].get_rect().w + 15
            title_y = content_y + 6
            screen.blit(self.content, (content_x, content_y))
            screen.blit(self.template_list[i]["icon"], (icon_x, icon_y))
            surf_title, pos_title = self.draw_text(text=self.template_list[i]["information"]["Informations"]["Name"],
                                                   font_name=self.font_data["path"],
                                                   color=self.font_data["color_normal"],
                                                   font_size=self.font_data["size"],
                                                   surface=screen,
                                                   position=(title_x, title_y),
                                                   outline=1)
            author_x = title_x
            author_y = title_y + surf_title.get_rect().h + 2
            surf_author, pos_author = self.draw_text(text="Author : {}".format(self.template_list[i]["information"]["Informations"]["Creator"]),
                                                     font_name=self.font_data["path"],
                                                     color=self.font_data["color_normal"],
                                                     font_size=self.font_data["size"] - 4,
                                                     surface=screen,
                                                     position=(author_x, author_y),
                                                     outline=1)
            version_x = title_x
            version_y = author_y + surf_author.get_rect().h + 2
            surf_author, pos_author = self.draw_text(text="Version : {}".format(self.template_list[i]["information"]["Informations"]["Version"]),
                                                     font_name=self.font_data["path"],
                                                     color=self.font_data["color_normal"],
                                                     font_size=self.font_data["size"] - 4,
                                                     surface=screen,
                                                     position=(version_x, version_y),
                                                     outline=1)



    def process_templates_list(self):
        for file in glob.glob("{}{}*.template".format(self.template_directory, os.sep)):
            archive = ZipFile(file, 'r')
            tracker_json = archive.read("tracker.json")
            tracker_icon = archive.read("icon.png")

            data = json.loads(tracker_json)
            template_data = {
                "information": data[0],
                "icon": pygame.image.load(io.BytesIO(tracker_icon))
            }
            self.template_list.append(template_data)

        print(self.template_list)
            # print(data[0])
            # bytes_io = io.BytesIO(file_data)
            #
            # surface = pygame.image.load(bytes_io)
            # print(surface)

    def draw_text(self, text, font_name, color, font_size, surface, position, outline=2):
        return ptext.draw(str(text), position, fontname=font_name, antialias=True,
                                 owidth=outline, ocolor=(0, 0, 0), color=color, fontsize=font_size, surf=surface)
