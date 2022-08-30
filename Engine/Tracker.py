import gc
import json
import os
from tkinter import messagebox
from zipfile import ZipFile

import pygame

from Engine import MainMenu
from Engine.Menu import Menu
from Engine.PopupWindow import PopupWindow
from Entities.AlternateCountItem import AlternateCountItem
from Entities.AlternateEvolutionItem import AlternateEvolutionItem
from Entities.CheckItem import CheckItem
from Entities.CountItem import CountItem
from Entities.EvolutionItem import EvolutionItem
from Entities.GoModeItem import GoModeItem
from Entities.IncrementalItem import IncrementalItem
from Entities.Item import Item
from Entities.LabelItem import LabelItem
from Entities.Maps.Map import Map
from Entities.Maps.MapNameListItem import MapNameListItem
from Entities.SubMenuItem import SubMenuItem
from Tools.Bank import Bank
from Tools.CoreService import CoreService
from Tools.ImageSheet import ImageSheet
from Tools.SaveLoadTool import SaveLoadTool


class Tracker:
    def __init__(self, template_name, main_menu):
        self.surface_label_map_name = None
        self.position_draw_label_map_name = None
        self.map_name_items_list = None
        self.maps_names = []
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
        self.current_map = None
        self.drop_down_maps_list = None
        self.next_map_name = None
        self.box_label_map_name_rect = None
        self.maps_list_window = PopupWindow(tracker=self, index_positions=(0, 0))
        self.maps_list = []
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

        # if self.map_image:
        #     self.map_image = self.bank.addZoomImage(os.path.join(self.resources_path, self.map_image_filename))

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
        self.map_name_items_list = []
        if len(self.tracker_json_data) > 4:
            if "Maps" in self.tracker_json_data[4].keys():
                self.maps_names = []
                maps = self.tracker_json_data[4]["Maps"]
                for map in maps:
                    filename = os.path.join(self.resources_path, map["Datas"])
                    if os.path.isfile(filename):
                        with open(filename, 'r') as file:
                            json_datas = json.load(file)

                            positions = {
                                "x": self.background_image.get_rect().w + self.background_image.get_rect().x,
                                "y": self.background_image.get_rect().y
                            }
                            temp_map = Map(json_datas, positions, self, False)
                            self.maps_list.append(temp_map)
                            self.maps_names.append(temp_map.get_name())

                            temp_map_name = MapNameListItem(tracker=self,
                                                            ident=map["Id"],
                                                            name=json_datas[0]["Datas"]["Name"],
                                                            position=positions)
                            self.map_name_items_list.append(temp_map_name)

        self.change_map(self.map_name_items_list[0])
        self.update()

    def update(self):
        self.box_label_map_name_rect = self.tracker_json_data[4]["MapsList"]["MapListButtonLabelRect"]
        self.box_label_map_name_rect = pygame.Rect(
            self.box_label_map_name_rect["x"] * self.core_service.zoom,
            self.box_label_map_name_rect["y"] * self.core_service.zoom,
            self.box_label_map_name_rect["w"] * self.core_service.zoom,
            self.box_label_map_name_rect["h"] * self.core_service.zoom
        )

        font = self.core_service.get_font("mapFontListMaps")
        font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])

        temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32)
        temp_surface = temp_surface.convert_alpha()
        self.surface_label_map_name, self.position_draw_label_map_name = MainMenu.MainMenu.draw_text(
            text=self.current_map.get_name(),
            font_name=font_path,
            color=(255, 255, 255),
            font_size=font["Size"] * self.core_service.zoom,
            surface=temp_surface,
            position=(self.box_label_map_name_rect.x, self.box_label_map_name_rect.y),
            outline=1 * self.core_service.zoom)

        x = (self.box_label_map_name_rect.w / 2) - (
                self.surface_label_map_name.get_rect().w / 2) + self.box_label_map_name_rect.x
        y = (self.box_label_map_name_rect.h / 2) - (
                self.surface_label_map_name.get_rect().h / 2) + self.box_label_map_name_rect.y
        self.position_draw_label_map_name = (x, y)

        maps_list_box_datas = self.tracker_json_data[4]["MapsList"]["MapsListBox"]
        self.maps_list_background = self.bank.addZoomImage(
            os.path.join(self.resources_path, maps_list_box_datas["SubMenuBackground"]))

        maps_list_box_rect = pygame.Rect(
            (maps_list_box_datas["DrawBoxRect"][
                 "x"] * self.core_service.zoom) + self.maps_list_background.get_rect().x,
            (maps_list_box_datas["DrawBoxRect"][
                 "y"] * self.core_service.zoom) + self.maps_list_background.get_rect().y,
            maps_list_box_datas["DrawBoxRect"]["w"] * self.core_service.zoom,
            maps_list_box_datas["DrawBoxRect"]["h"] * self.core_service.zoom)

        self.maps_list_window.set_background_image_path(maps_list_box_datas["SubMenuBackground"])
        self.maps_list_window.set_arrow_left_image_path(maps_list_box_datas["LeftArrow"]["Image"])
        self.maps_list_window.set_arrow_right_image_path(maps_list_box_datas["RightArrow"]["Image"])
        self.maps_list_window.set_title("Maps")
        self.maps_list_window.set_title_font(self.core_service.get_font("mapFontTitle"))
        self.maps_list_window.set_title_label_position_y(maps_list_box_datas["LabelY"])
        self.maps_list_window.set_list_items(self.map_name_items_list)
        self.maps_list_window.set_box_rect(maps_list_box_rect)
        left_arrow = (maps_list_box_datas["LeftArrow"]["Positions"]["x"],
                      maps_list_box_datas["LeftArrow"]["Positions"]["y"])
        right_arrow = (maps_list_box_datas["RightArrow"]["Positions"]["x"],
                       maps_list_box_datas["RightArrow"]["Positions"]["y"])

        self.maps_list_window.set_arrows_positions(left_arrow, right_arrow)
        self.maps_list_window.update()

    def change_map_by_map_name(self, map_name):
        for map_item in self.map_name_items_list:
            if map_item.name == map_name:
                self.change_map(map_item)

    def change_map(self, map_list_item):
        self.current_map = self.maps_list[map_list_item.id]
        self.current_map.active = True
        self.current_map.update()
        self.update()

        # print("map", map_infos)

    def init_item(self, item, item_list, items_sheet_image):
        item_image = self.core_service.zoom_image(
            items_sheet_image.getImageWithRowAndColumn(row=item["SheetPositions"]["row"],
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
                items_sheet_image.getImageWithRowAndColumn(row=item["CheckImageSheetPositions"]["row"],
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
                    items_sheet_image.getImageWithRowAndColumn(row=next_item["SheetPositions"]["row"],
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
            start_increment_index = None
            if "StartIncrementIndex" in item:
                start_increment_index = item["StartIncrementIndex"]

            _item = IncrementalItem(name=item["Name"],
                                    image=item_image,
                                    position=(item["Positions"]["x"] * self.core_service.zoom,
                                              item["Positions"]["y"] * self.core_service.zoom),
                                    enable=item["isActive"],
                                    opacity_disable=item["OpacityDisable"],
                                    hint=item["Hint"],
                                    increments=item["Increment"],
                                    id=item["Id"],
                                    start_increment_index=start_increment_index)
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
                                show_numbers_items_active=item["ShowNumbersOfItemsActive"],
                                show_numbers_checked_items=item["ShowNumberOfCheckedItems"])

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
            self.init_item(item, self.items, self.items_sheet_data)

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
                return True
        return False

    def click(self, mouse_position, button):
        can_click = True

        for submenu in self.submenus:
            if submenu.show:
                can_click = False
                break

        if can_click:
            if self.current_map:
                self.current_map.click(mouse_position, button)
                self.current_map.update()

                if not self.current_map.checks_list_open:
                    self.items_click(self.items, mouse_position, button)
                    self.current_map.update()

                if self.maps_list_window.is_open():
                    self.maps_list_window.left_click(mouse_position)

                if self.core_service.is_on_element(mouse_positions=mouse_position,
                                                   element_positons=(
                                                           self.box_label_map_name_rect.x,
                                                           self.box_label_map_name_rect.y),
                                                   element_dimension=(
                                                           self.box_label_map_name_rect.w,
                                                           self.box_label_map_name_rect.h)):
                    self.maps_list_window.open = True
                    self.maps_list_window.update()

            else:
                self.items_click(self.items, mouse_position, button)
                if self.current_map:
                    self.current_map.update()

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

        if self.maps_list:
            maps_datas = []
            for map_data in self.maps_list:
                maps_datas.append(map_data.get_data())

        datas.append({
            "maps": maps_datas
        })
        return datas

    def load_data(self, datas):
        if datas[0]["template_name"] == self.template_name:
            for data in datas[1]["items"]:
                for item in self.items:
                    if data["name"] == item.name and data["id"] == item.id:
                        item.set_data(data)
                        break

            if "maps" in datas[2]:
                for maps_datas in datas[2]["maps"]:
                    for map_data in self.maps_list:
                        if maps_datas["name"] == map_data.get_name():
                            map_data.load_data(maps_datas)
                            map_data.update()
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
        if "MapsList" in self.tracker_json_data:
            maps_rect = self.tracker_json_data[4]["MapsList"]["MapsListBox"]["MapsListRect"]

        if self.current_map:
            self.current_map.update()

        pygame.display.set_mode((w, h))
        self.init_items()
        self.menu.get_menu().resize(width=w, height=h)
        self.load_data(datas)
        self.update()

    def draw(self, screen):
        screen.blit(self.background_image, (0, 0))
        self.items.draw(screen)

        for item in self.items:
            if type(item) == GoModeItem:
                if item.enable:
                    item.draw()
                    break

            # pygame.draw.rect(screen, (255, 255, 255),item.rect)

        if self.menu.get_menu().is_enabled():
            self.menu.get_menu().mainloop(screen)

        if self.core_service.draw_esc_menu_label:
            screen.blit(self.esc_menu_image, (2, 2))

        for submenu in self.submenus:
            submenu.draw_submenu(screen)

        if self.current_map:
            self.current_map.draw(screen)

        screen.blit(self.surface_label_map_name, self.position_draw_label_map_name)

        if self.maps_list_window.is_open():
            infoObject = pygame.display.Info()
            s = pygame.Surface((infoObject.current_w, infoObject.current_h), pygame.SRCALPHA)  # per-pixel alpha
            s.fill((0, 0, 0, 209))  # notice the alpha value in the color
            screen.blit(s, (0, 0))
            self.maps_list_window.draw(screen)

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

    def have(self, item_name):
        for item in self.items:
            if item.name == item_name:
                if item.enable:
                    return True
                else:
                    return False

        return False

    def do(self, action):
        actions_list = self.tracker_json_data[4]["ActionsConditions"]
        if action in actions_list:
            if type(actions_list[action]) == str:
                action_do = actions_list[action].replace("have(", "self.have(").replace("do(", "self.do(")
            else:
                action_do = action
            return eval(action_do)
