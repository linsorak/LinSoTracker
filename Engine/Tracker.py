import json
import os
from zipfile import ZipFile
import gc
import pygame
from Engine.Menu import Menu
from Entities.AlternateCountItem import AlternateCountItem
from Entities.CheckItem import CheckItem
from Entities.CountItem import CountItem
from Entities.EvolutionItem import EvolutionItem
from Entities.GoModeItem import GoModeItem
from Entities.IncrementalItem import IncrementalItem
from Entities.Item import Item
from Entities.LabelItem import LabelItem
from Tools.Bank import Bank
from Tools.CoreService import CoreService
from Tools.ImageSheet import ImageSheet


class Tracker:
    def __init__(self, template_name, main_menu):
        self.main_menu = main_menu
        self.kinds = None
        self.test_img = None
        self.items_sheet_data = None
        self.items_sheet = None
        self.tracker_json_data = None
        self.resources_path = None
        self.background_image = None
        self.items = pygame.sprite.Group()
        self.template_name = template_name
        self.core_service = CoreService()
        self.resources_base_path = os.path.join(self.core_service.get_temp_path(), "tracker")
        self.menu = []
        self.bank = Bank()
        self.extract_data()
        self.init_tracker()
        self.core_service.load_default_configuration()
        self.core_service.set_json_data(self.tracker_json_data)
        self.core_service.set_tracker_temp_path(self.resources_path)
        self.init_items()
        self.menu.set_zoom_index(self.core_service.zoom_index)
        self.menu.set_sound_check(self.core_service.sound_active)
        self.menu.set_esc_check(self.core_service.draw_esc_menu_label)
        self.sound_select = pygame.mixer.Sound(os.path.join(self.resources_base_path, "select.wav"))
        self.sound_cancel = pygame.mixer.Sound(os.path.join(self.resources_base_path, "cancel.wav"))
        pygame.mixer.Sound.set_volume(self.sound_select, 0.3)
        pygame.mixer.Sound.set_volume(self.sound_cancel, 0.3)
        self.check_is_default_save()

    def check_is_default_save(self):
        save_directory = os.path.join(self.core_service.get_app_path(), "default_saves")
        if os.path.exists(save_directory):
            save_name = os.path.join(save_directory, self.template_name + ".trackersave")
            if os.path.exists(save_name):
                f = open(save_name)
                self.load_data(json.load(f))

    def extract_data(self):
        filename = os.path.join(self.core_service.get_app_path(), "templates", "{}.template".format(self.template_name))
        self.resources_path = os.path.join(self.core_service.get_temp_path(), "{}".format(self.template_name))

        self.core_service.delete_directory(self.resources_path)
        self.core_service.create_directory(self.resources_path)
        if os.path.isfile(filename):
            zip = ZipFile(filename)
            # zip.extractall(self.resources_path)
            # zip.close()
            list_files = zip.namelist()
            for file in list_files:
                try:
                    zip.extract(file, self.resources_path)
                except PermissionError:
                    pass
            zip.close()

    def init_tracker(self):
        filename = os.path.join(self.resources_path, "tracker.json")
        if os.path.isfile(filename):
            with open(filename, 'r') as file:
                self.tracker_json_data = json.load(file)

        json_data_background = self.tracker_json_data[1]["Datas"]["Background"]
        w = self.tracker_json_data[1]["Datas"]["Dimensions"]["width"] * self.core_service.zoom
        h = self.tracker_json_data[1]["Datas"]["Dimensions"]["height"] * self.core_service.zoom
        pygame.display.set_mode((w, h))
        self.core_service.setgamewindowcenter(w, h)
        self.background_image = self.bank.addZoomImage(os.path.join(self.resources_path, json_data_background))

        json_data_item_sheet = self.tracker_json_data[1]["Datas"]["ItemSheet"]
        json_data_item_sheet_dimensions = self.tracker_json_data[1]["Datas"]["ItemSheetDimensions"]
        self.items_sheet = self.bank.addImage(os.path.join(self.resources_path, json_data_item_sheet))
        self.items_sheet_data = ImageSheet(self.items_sheet, json_data_item_sheet_dimensions["width"],
                                           json_data_item_sheet_dimensions["height"])

        background_color_r = self.tracker_json_data[1]["Datas"]["BackgroundColor"]["r"]
        background_color_g = self.tracker_json_data[1]["Datas"]["BackgroundColor"]["g"]
        background_color_b = self.tracker_json_data[1]["Datas"]["BackgroundColor"]["b"]

        self.core_service.set_background_color(background_color_r, background_color_g, background_color_b)

        self.menu = Menu((w, h), self)
        self.menu.set_tracker(self)
        self.esc_menu_image = self.bank.addImage(os.path.join(self.resources_base_path, "menu.png"))

    def init_items(self):
        # itemList = []
        for item in self.tracker_json_data[3]["Items"]:
            id = len(self.items)

            # if item["Name"] in itemList:
            #     print("DOUBLON", item["Name"])
            # else:
            #     itemList.append(item["Name"])

            item_image = self.core_service.zoom_image(
                self.items_sheet_data.getImageWithRowAndColumn(row=item["SheetPositions"]["row"],
                                                               column=item["SheetPositions"]["column"]))

            if item["Kind"] == "AlternateCountItem":
                item = AlternateCountItem(name=item["Name"],
                                          image=item_image,
                                          position=(item["Positions"]["x"] * self.core_service.zoom,
                                                    item["Positions"]["y"] * self.core_service.zoom),
                                          enable=item["isActive"],
                                          hint=item["Hint"],
                                          opacity_disable=item["OpacityDisable"],
                                          max_value=item["maxValue"],
                                          max_value_alternate=item["maxValueAlternate"],
                                          id=id)
                self.items.add(item)
            elif item["Kind"] == "GoModeItem":
                background_glow = self.bank.addZoomImage(os.path.join(self.resources_path, item["BackgroundGlow"]))
                item = GoModeItem(name=item["Name"],
                                  image=item_image,
                                  position=(item["Positions"]["x"] * self.core_service.zoom,
                                            item["Positions"]["y"] * self.core_service.zoom),
                                  enable=item["isActive"],
                                  hint=item["Hint"],
                                  opacity_disable=item["OpacityDisable"],
                                  background_glow=background_glow,
                                  id=id)
                self.items.add(item)
            elif item["Kind"] == "CheckItem":
                check_image = self.core_service.zoom_image(
                    self.items_sheet_data.getImageWithRowAndColumn(row=item["CheckImageSheetPositions"]["row"],
                                                                   column=item["CheckImageSheetPositions"]["column"]))
                item = CheckItem(name=item["Name"],
                                 image=item_image,
                                 position=(item["Positions"]["x"] * self.core_service.zoom,
                                           item["Positions"]["y"] * self.core_service.zoom),
                                 enable=item["isActive"],
                                 hint=item["Hint"],
                                 opacity_disable=item["OpacityDisable"],
                                 check_image=check_image,
                                 id=id)
                self.items.add(item)
            elif item["Kind"] == "LabelItem":
                item = LabelItem(name=item["Name"],
                                 image=item_image,
                                 position=(item["Positions"]["x"] * self.core_service.zoom,
                                           item["Positions"]["y"] * self.core_service.zoom),
                                 enable=item["isActive"],
                                 hint=item["Hint"],
                                 opacity_disable=item["OpacityDisable"],
                                 label_list=item["LabelList"],
                                 id=id)
                self.items.add(item)
            elif item["Kind"] == "CountItem":
                item = CountItem(name=item["Name"],
                                 image=item_image,
                                 position=(item["Positions"]["x"] * self.core_service.zoom,
                                           item["Positions"]["y"] * self.core_service.zoom),
                                 enable=item["isActive"],
                                 hint=item["Hint"],
                                 opacity_disable=item["OpacityDisable"],
                                 min_value=item["valueMin"],
                                 max_value=item["valueMax"],
                                 value_increase=item["valueIncrease"],
                                 value_start=item["valueStart"],
                                 id=id)
                self.items.add(item)
            elif item["Kind"] == "EvolutionItem":
                next_items_list = []
                for next_item in item["NextItems"]:
                    temp_item = {}
                    temp_item["Name"] = next_item["Name"]
                    temp_item["Image"] = self.core_service.zoom_image(
                        self.items_sheet_data.getImageWithRowAndColumn(row=next_item["SheetPositions"]["row"],
                                                                       column=next_item["SheetPositions"]["column"]))
                    temp_item["Label"] = next_item["Label"]
                    next_items_list.append(temp_item)

                item = EvolutionItem(name=item["Name"],
                                     image=item_image,
                                     position=(item["Positions"]["x"] * self.core_service.zoom,
                                               item["Positions"]["y"] * self.core_service.zoom),
                                     enable=item["isActive"],
                                     opacity_disable=item["OpacityDisable"],
                                     hint=item["Hint"],
                                     next_items=next_items_list,
                                     label=item["Label"],
                                     label_center=item["LabelCenter"],
                                     id=id)
                self.items.add(item)

            elif item["Kind"] == "IncrementalItem":
                item = IncrementalItem(name=item["Name"],
                                       image=item_image,
                                       position=(item["Positions"]["x"] * self.core_service.zoom,
                                                 item["Positions"]["y"] * self.core_service.zoom),
                                       enable=item["isActive"],
                                       opacity_disable=item["OpacityDisable"],
                                       hint=item["Hint"],
                                       increments=item["Increment"],
                                       id=id)
                self.items.add(item)
            elif item["Kind"] == "Item":
                item = Item(name=item["Name"],
                            image=item_image,
                            position=(item["Positions"]["x"] * self.core_service.zoom,
                                      item["Positions"]["y"] * self.core_service.zoom),
                            enable=item["isActive"],
                            hint=item["Hint"],
                            opacity_disable=item["OpacityDisable"],
                            id=id)
                self.items.add(item)

    def click(self, mouse_position, button):
        if button == 1:
            for item in self.items:
                if self.core_service.is_on_element(mouse_positions=mouse_position, element_positons=item.get_position(),
                                                   element_dimension=(item.get_rect().w, item.get_rect().h)):
                    item.left_click()
                    if self.core_service.sound_active:
                        if item.enable:
                            self.sound_select.play()
                        else:
                            self.sound_cancel.play()

        if button == 2:
            for item in self.items:
                if self.core_service.is_on_element(mouse_positions=mouse_position, element_positons=item.get_position(),
                                                   element_dimension=(item.get_rect().w, item.get_rect().h)):
                    item.wheel_click()

        if button == 3:
            for item in self.items:
                if self.core_service.is_on_element(mouse_positions=mouse_position, element_positons=item.get_position(),
                                                   element_dimension=(item.get_rect().w, item.get_rect().h)):
                    item.right_click()
                    if self.core_service.sound_active:
                        if item.enable:
                            self.sound_select.play()
                        else:
                            self.sound_cancel.play()

    def save_data(self):
        datas = []
        datas.append({
            "template_name": self.template_name
        })

        datas_items = []
        for item in self.items:
            datas_items.append(item.get_data())

        datas.append({
            "items": datas_items
        })
        return datas

    def load_data(self, datas):
        if datas[0]["template_name"] == self.template_name:
            for data in datas[1]["items"]:
                for item in self.items:
                    if data["name"] == item.name and data["id"] == item.id:
                        item.set_data(data)
                        break

    def change_zoom(self, value):
        datas = self.save_data()
        self.core_service.zoom = value
        self.items = pygame.sprite.Group()
        json_data_background = self.tracker_json_data[1]["Datas"]["Background"]
        self.background_image = self.bank.addZoomImage(os.path.join(self.resources_path, json_data_background))
        w = self.tracker_json_data[1]["Datas"]["Dimensions"]["width"] * self.core_service.zoom
        h = self.tracker_json_data[1]["Datas"]["Dimensions"]["height"] * self.core_service.zoom
        pygame.display.set_mode((w, h))
        self.init_items()
        self.menu.get_menu().resize(width=w, height=h)
        self.load_data(datas)

    def draw(self, screen):
        screen.blit(self.background_image, (0, 0))
        self.items.draw(screen)

        for item in self.items:
            if type(item) == GoModeItem:
                item.draw()
                break

        if self.menu.get_menu().is_enabled():
            self.menu.get_menu().mainloop(screen)

        if self.core_service.draw_esc_menu_label:
            screen.blit(self.esc_menu_image, (2, 2))

    def keyup(self, button, screen):
        if button == pygame.K_ESCAPE:
            if not self.menu.get_menu().is_enabled():
                self.menu.active(screen)

    def events(self, events):
        self.menu.events(events)

    def back_main_menu(self):
        self.main_menu.reset_tracker()

    def delete_data(self):
        for item in self.items:
            del item

        del self.items
        gc.collect()
