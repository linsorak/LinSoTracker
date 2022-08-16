import json
import os
from tkinter import messagebox
from zipfile import ZipFile
import gc
import pygame
from Engine.Menu import Menu
from Entities.AlternateCountItem import AlternateCountItem
from Entities.AlternateEvolutionItem import AlternateEvolutionItem
from Entities.CheckItem import CheckItem
from Entities.CountItem import CountItem
from Entities.EvolutionItem import EvolutionItem
from Entities.GoModeItem import GoModeItem
from Entities.IncrementalItem import IncrementalItem
from Entities.Item import Item
from Entities.LabelItem import LabelItem
from Entities.SubMenuItem import SubMenuItem
from Tools.Bank import Bank
from Tools.CoreService import CoreService
from Tools.DropDown import DropDown
from Tools.ImageSheet import ImageSheet
from Tools.SaveLoadTool import SaveLoadTool


class Tracker:
    def __init__(self, template_name, main_menu):
        self.map_image_filename = None
        self.map_position = None
        self.main_menu = main_menu
        self.kinds = None
        self.test_img = None
        self.items_sheet_data = None
        self.items_sheet = None
        self.tracker_json_data = None
        self.resources_path = None
        self.background_image = None
        self.maps_datas = None
        self.list_map = None
        self.map_image = None
        self.submenus = pygame.sprite.Group()
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
        self.core_service.set_current_tracker_name(self.template_name)
        self.init_items()
        self.init_maps_datas()
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

            save_tool = SaveLoadTool()
            if os.path.exists(save_name):
                f = save_tool.loadEcryptedFile(save_name)
                if f:
                    if f[0]["template_name"] == self.template_name:
                        self.load_data(f)
                    else:
                        messagebox.showerror('Error', 'This save is for the template {}'.format(f[0]["template_name"]))

    def extract_data(self):
        filename = os.path.join(self.core_service.get_app_path(), "templates", "{}.template".format(self.template_name))
        self.resources_path = os.path.join(self.core_service.get_temp_path(), "{}".format(self.template_name))

        self.core_service.delete_directory(self.resources_path)
        self.core_service.create_directory(self.resources_path)
        if os.path.isfile(filename):
            zip = ZipFile(filename)
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

        if self.map_image:
            self.map_image = self.bank.addZoomImage(os.path.join(self.resources_path, self.map_image_filename))

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

    def init_maps_datas(self):
        if len(self.tracker_json_data) > 4:
            if "Maps" in self.tracker_json_data[4].keys():
                self.maps_datas = []
                maps_list = []
                name_list = []
                maps = self.tracker_json_data[4]["Maps"]
                maps_data = maps["Datas"]
                for map in maps_data:
                    filename = os.path.join(self.resources_path, map["Datas"])
                    if os.path.isfile(filename):
                        with open(filename, 'r') as file:
                            json_datas = json.load(file)
                            self.maps_datas.append(json_datas)
                            name_list.append(json_datas[0]["Datas"]["Name"])

                font = self.core_service.get_font("mapListFont")
                font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])
                transparent_color = (255, 255, 255, 0)
                background_color = (
                    font["Colors"]["BackgroundMenuList"]["r"], font["Colors"]["BackgroundMenuList"]["r"],
                    font["Colors"]["BackgroundMenuList"]["b"])
                text_color = (font["Colors"]["Font"]["r"], font["Colors"]["Font"]["r"], font["Colors"]["Font"]["b"])
                self.list_map = DropDown(
                    background_color,
                    background_color,
                    text_color,
                    maps["MapsListDimensions"]["x"],
                    maps["MapsListDimensions"]["y"],
                    maps["MapsListDimensions"]["width"],
                    maps["MapsListDimensions"]["height"],
                    pygame.font.SysFont(None, 30),
                    name_list[0],
                    name_list)

                self.map_image_filename = self.maps_datas[0][0]["Datas"]["Background"]
                self.map_image = self.bank.addZoomImage(os.path.join(self.resources_path, self.map_image_filename))
                self.map_position = self.maps_datas[0][0]["Datas"]["Positions"]

    def change_map(self, map_name):
        pass

    def init_item(self, item, item_list):
        item_image = self.core_service.zoom_image(
            self.items_sheet_data.getImageWithRowAndColumn(row=item["SheetPositions"]["row"],
                                                           column=item["SheetPositions"]["column"]))

        if item["Kind"] == "AlternateCountItem":
            _item = AlternateCountItem(name=item["Name"],
                                       image=item_image,
                                       position=(item["Positions"]["x"] * self.core_service.zoom,
                                                 item["Positions"]["y"] * self.core_service.zoom),
                                       enable=item["isActive"],
                                       hint=item["Hint"],
                                       opacity_disable=item["OpacityDisable"],
                                       max_value=item["maxValue"],
                                       max_value_alternate=item["maxValueAlternate"],
                                       id=item["Id"])
            item_list.add(_item)
        elif item["Kind"] == "GoModeItem":
            background_glow = self.bank.addZoomImage(os.path.join(self.resources_path, item["BackgroundGlow"]))
            _item = GoModeItem(name=item["Name"],
                               image=item_image,
                               position=(item["Positions"]["x"] * self.core_service.zoom,
                                         item["Positions"]["y"] * self.core_service.zoom),
                               enable=item["isActive"],
                               hint=item["Hint"],
                               opacity_disable=item["OpacityDisable"],
                               background_glow=background_glow,
                               id=item["Id"])
            item_list.add(_item)
        elif item["Kind"] == "CheckItem":
            check_image = self.core_service.zoom_image(
                self.items_sheet_data.getImageWithRowAndColumn(row=item["CheckImageSheetPositions"]["row"],
                                                               column=item["CheckImageSheetPositions"]["column"]))
            _item = CheckItem(name=item["Name"],
                              image=item_image,
                              position=(item["Positions"]["x"] * self.core_service.zoom,
                                        item["Positions"]["y"] * self.core_service.zoom),
                              enable=item["isActive"],
                              hint=item["Hint"],
                              opacity_disable=item["OpacityDisable"],
                              check_image=check_image,
                              id=item["Id"])
            item_list.add(_item)
        elif item["Kind"] == "LabelItem":
            offset = 0
            if "OffsetLabel" in item:
                offset = item["OffsetLabel"]
            _item = LabelItem(name=item["Name"],
                              image=item_image,
                              position=(item["Positions"]["x"] * self.core_service.zoom,
                                        item["Positions"]["y"] * self.core_service.zoom),
                              enable=item["isActive"],
                              hint=item["Hint"],
                              opacity_disable=item["OpacityDisable"],
                              label_list=item["LabelList"],
                              label_offset=offset,
                              id=item["Id"])
            item_list.add(_item)
        elif item["Kind"] == "CountItem":
            _item = CountItem(name=item["Name"],
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
                              id=item["Id"])
            item_list.add(_item)
        elif item["Kind"] == "EvolutionItem" or item["Kind"] == "AlternateEvolutionItem":
            alternative_label = None
            next_items_list = []
            for next_item in item["NextItems"]:
                temp_item = {}
                temp_item["Name"] = next_item["Name"]
                temp_item["Image"] = self.core_service.zoom_image(
                    self.items_sheet_data.getImageWithRowAndColumn(row=next_item["SheetPositions"]["row"],
                                                                   column=next_item["SheetPositions"]["column"]))
                temp_item["Label"] = next_item["Label"]
                if "AlternativeLabel" in next_item:
                    temp_item["AlternativeLabel"] = next_item["AlternativeLabel"]

                next_items_list.append(temp_item)

            if "AlternativeLabel" in item:
                alternative_label = item["AlternativeLabel"]

            if item["Kind"] == "EvolutionItem":
                _item = EvolutionItem(name=item["Name"],
                                      image=item_image,
                                      position=(item["Positions"]["x"] * self.core_service.zoom,
                                                item["Positions"]["y"] * self.core_service.zoom),
                                      enable=item["isActive"],
                                      opacity_disable=item["OpacityDisable"],
                                      hint=item["Hint"],
                                      next_items=next_items_list,
                                      label=item["Label"],
                                      label_center=item["LabelCenter"],
                                      id=item["Id"],
                                      alternative_label=alternative_label)
            else:
                global_label = None

                if "GlobalLabel" in item:
                    global_label = item["GlobalLabel"]

                _item = AlternateEvolutionItem(name=item["Name"],
                                               image=item_image,
                                               position=(item["Positions"]["x"] * self.core_service.zoom,
                                                         item["Positions"]["y"] * self.core_service.zoom),
                                               enable=item["isActive"],
                                               opacity_disable=item["OpacityDisable"],
                                               hint=item["Hint"],
                                               next_items=next_items_list,
                                               label=item["Label"],
                                               label_center=item["LabelCenter"],
                                               id=item["Id"],
                                               alternative_label=alternative_label,
                                               global_label=global_label)
            item_list.add(_item)

        elif item["Kind"] == "IncrementalItem":
            _item = IncrementalItem(name=item["Name"],
                                    image=item_image,
                                    position=(item["Positions"]["x"] * self.core_service.zoom,
                                              item["Positions"]["y"] * self.core_service.zoom),
                                    enable=item["isActive"],
                                    opacity_disable=item["OpacityDisable"],
                                    hint=item["Hint"],
                                    increments=item["Increment"],
                                    id=item["Id"])
            item_list.add(_item)
        elif item["Kind"] == "SubMenuItem":
            _item = SubMenuItem(name=item["Name"],
                                image=item_image,
                                position=(item["Positions"]["x"] * self.core_service.zoom,
                                          item["Positions"]["y"] * self.core_service.zoom),
                                enable=item["isActive"],
                                hint=item["Hint"],
                                opacity_disable=item["OpacityDisable"],
                                id=item["Id"],
                                background_image=item["Background"],
                                resources_path=self.resources_path,
                                tracker=self,
                                items_list=item["ItemsList"],
                                show_numbers_items_active=item["ShowNumbersOfItemsActive"])

            item_list.add(_item)
        elif item["Kind"] == "Item":
            _item = Item(name=item["Name"],
                         image=item_image,
                         position=(item["Positions"]["x"] * self.core_service.zoom,
                                   item["Positions"]["y"] * self.core_service.zoom),
                         enable=item["isActive"],
                         hint=item["Hint"],
                         opacity_disable=item["OpacityDisable"],
                         id=item["Id"])
            item_list.add(_item)

    def init_items(self):
        for item in self.tracker_json_data[3]["Items"]:
            self.init_item(item, self.items)

    def items_left_click(self, item_list, mouse_position):
        for item in item_list:
            if self.core_service.is_on_element(mouse_positions=mouse_position, element_positons=item.get_position(),
                                               element_dimension=(item.get_rect().w, item.get_rect().h)):
                item.left_click()
                if self.core_service.sound_active:
                    if item.enable:
                        self.sound_select.play()
                    else:
                        self.sound_cancel.play()

    def items_click(self, item_list, mouse_position, button):
        click_found = False
        for item in item_list:
            if self.core_service.is_on_element(mouse_positions=mouse_position, element_positons=item.get_position(),
                                               element_dimension=(item.get_rect().w, item.get_rect().h)):
                if button == 1:
                    item.left_click()
                if button == 2:
                    item.wheel_click()
                if button == 3:
                    item.right_click()

                if self.core_service.sound_active and (button == 1 or button == 3):
                    if item.enable:
                        self.sound_select.play()
                    else:
                        self.sound_cancel.play()
                click_found = True

        return click_found

    def click(self, mouse_position, button):
        can_click = True

        for submenu in self.submenus:
            if submenu.show:
                can_click = False
                break

        if can_click:
            self.items_click(self.items, mouse_position, button)

        else:
            for submenu in self.submenus:
                if submenu.show:
                    submenu.submenu_click(mouse_position, button)

                    for item in self.items:
                        if type(item) == SubMenuItem:
                            item.update()


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
        self.submenus = pygame.sprite.Group()
        json_data_background = self.tracker_json_data[1]["Datas"]["Background"]
        self.background_image = self.bank.addZoomImage(os.path.join(self.resources_path, json_data_background))
        w = self.tracker_json_data[1]["Datas"]["Dimensions"]["width"] * self.core_service.zoom
        h = self.tracker_json_data[1]["Datas"]["Dimensions"]["height"] * self.core_service.zoom

        if self.map_image:
            self.map_image = self.bank.addZoomImage(os.path.join(self.resources_path, self.map_image_filename))

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

            # pygame.draw.rect(screen, (255, 255, 255),item.rect)

        if self.menu.get_menu().is_enabled():
            self.menu.get_menu().mainloop(screen)

        if self.core_service.draw_esc_menu_label:
            screen.blit(self.esc_menu_image, (2, 2))

        if self.list_map:
            screen.blit(self.map_image, (
                self.map_position["x"] * self.core_service.zoom, self.map_position["y"] * self.core_service.zoom))
            self.list_map.draw(screen)

        for submenu in self.submenus:
            submenu.draw_submenu(screen)

    def keyup(self, button, screen):
        if button == pygame.K_ESCAPE:
            if not self.menu.get_menu().is_enabled():
                self.menu.active(screen)

    def events(self, events):
        if self.list_map:
            selected_option = self.list_map.update(events)
            if selected_option >= 0:
                self.list_map.main = self.list_map.options[selected_option]
                self.change_map(self.list_map.main)

        self.menu.events(events)

    def back_main_menu(self):
        self.main_menu.reset_tracker()

    def delete_data(self):
        for item in self.items:
            del item

        del self.items
        gc.collect()
