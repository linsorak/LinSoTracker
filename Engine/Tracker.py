import gc
import inspect
import json
import multiprocessing
import os
import re
import operator
import time
from multiprocessing.pool import ThreadPool
from tkinter import messagebox
from zipfile import ZipFile

import pygame
import pygame_gui

from Engine import MainMenu
from Engine.Menu import Menu
from Engine.PopupWindow import PopupWindow
from Entities.ImageItem import ImageItem
from Entities.AlternateCountItem import AlternateCountItem
from Entities.AlternateEvolutionItem import AlternateEvolutionItem
from Entities.CheckItem import CheckItem
from Entities.CountItem import CountItem
from Entities.DraggableEvolutionItem import DraggableEvolutionItem
from Entities.EditableBox import EditableBox
from Entities.EvolutionItem import EvolutionItem
from Entities.GoModeItem import GoModeItem
from Entities.IncrementalItem import IncrementalItem
from Entities.Item import Item
from Entities.LabelItem import LabelItem
from Entities.Maps.Map import Map
from Entities.Maps.MapNameListItem import MapNameListItem
from Entities.Maps.RulesOptionsListItem import RulesOptionsListItem
from Entities.Maps.SimpleCheck import SimpleCheck
from Entities.SubMenuItem import SubMenuItem
from Tools.Bank import Bank
from Tools.CoreService import CoreService
from Tools.ImageSheet import ImageSheet
from Tools.SaveLoadTool import SaveLoadTool
from Entities.Maps.BlockChecks import BlockChecks


class Tracker:
    def __init__(self, template_name, main_menu):
        self.loaded = False
        self.position_check_zone_hint = None
        self.surface_check_zone_hint = None
        self.initialized = False
        self.rules_options_show = None
        self.list_items_sheets = None
        self.position_draw_label_checks_cpt = None
        self.surface_label_checks_cpt = None
        self.cpt_all_checks = None
        self.cpt_checks_logics = None
        self.current_item_on_mouse = None
        self.rules_options_button_rect = None
        self.rules_options_items_list = None
        self.maps_list_background = None
        self.rules_options_list_background = None
        self.position_check_hint = None
        self.surface_check_hint = None
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
        self.mouse_check_found = None
        self.maps_list_window = PopupWindow(tracker=self, index_positions=(0, 0))
        self.rules_options_list_window = PopupWindow(tracker=self, index_positions=(0, 0))
        self.maps_list = []
        self.submenus = pygame.sprite.Group()
        self.items = pygame.sprite.Group()
        self.template_name = template_name
        self.core_service = CoreService()
        self.resources_base_path = os.path.join(self.core_service.get_temp_path(), "tracker")
        self.menu = []
        self.bank = Bank()

        self._font_cache = {}
        self._compiled_actions = {}

        self._pool = ThreadPool(processes=multiprocessing.cpu_count())

        self.extract_data()
        self.init_tracker()

        self.manager = pygame_gui.UIManager(pygame.display.get_surface().get_size())

        self.core_service.set_json_data(self.tracker_json_data)
        self.core_service.set_tracker_temp_path(self.resources_path)
        self.core_service.set_current_tracker_name(self.template_name)
        self.init_items()
        self.init_maps_datas()
        self.menu.set_zoom_index(self.core_service.zoom_index)
        self.menu.set_sound_check(self.core_service.sound_active)
        self.menu.set_esc_check(self.core_service.draw_esc_menu_label)
        self.menu.set_show_hint_check(self.core_service.show_hint_on_item)
        self.sound_select = pygame.mixer.Sound(os.path.join(self.resources_base_path, "select.wav"))
        self.sound_cancel = pygame.mixer.Sound(os.path.join(self.resources_base_path, "cancel.wav"))
        pygame.mixer.Sound.set_volume(self.sound_select, 0.3)
        pygame.mixer.Sound.set_volume(self.sound_cancel, 0.3)
        self.check_is_default_save()
        self.core_service.load_default_configuration()
        self.is_moving = None
        self.end_delay = None
        self.selected_items_list = None
        self.current_editablebox = None
        self.loaded = True

    def get_font_data(self, font_session):
        if font_session not in self._font_cache:
            font = self.core_service.get_font(font_session)
            font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])
            self._font_cache[font_session] = (font, font_path)
        return self._font_cache[font_session]

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
        zoom = self.core_service.zoom
        w = self.tracker_json_data[1]["Datas"]["Dimensions"]["width"] * zoom
        h = self.tracker_json_data[1]["Datas"]["Dimensions"]["height"] * zoom
        pygame.display.set_mode((w, h))
        self.core_service.setgamewindowcenter(w, h)
        self.background_image = self.bank.addZoomImage(os.path.join(self.resources_path, json_data_background))
        items_sheets = self.tracker_json_data[1]["Datas"]["Items"]
        self.list_items_sheets = []
        for sheet_name, sheet_info in items_sheets.items():
            image_sheet = self.bank.addImage(os.path.join(self.resources_path, sheet_info["ItemsSheet"]))
            items_sheet_data = ImageSheet(image_sheet, sheet_info["ItemsSheetDimensions"]["width"],
                                          sheet_info["ItemsSheetDimensions"]["height"])
            self.list_items_sheets.append({
                "Name": sheet_name,
                "ImageSheet": items_sheet_data,
                "ImageSheetDimensions": sheet_info["ItemsSheetDimensions"]
            })
        bg_color = self.tracker_json_data[1]["Datas"]["BackgroundColor"]
        self.core_service.set_background_color(bg_color["r"], bg_color["g"], bg_color["b"])
        self.menu = Menu((w, h), self)
        self.menu.set_tracker(self)
        self.esc_menu_image = self.bank.addImage(os.path.join(self.resources_base_path, "menu.png"))

    def init_maps_datas(self):
        self.map_name_items_list = []
        self.rules_options_items_list = []
        if len(self.tracker_json_data) > 4:
            if "Maps" in self.tracker_json_data[4]:
                self.maps_names = []
                maps = self.tracker_json_data[4]["Maps"]
                for map_data in maps:
                    filename = os.path.join(self.resources_path, map_data["Datas"])
                    if os.path.isfile(filename):
                        with open(filename, 'r') as file:
                            json_datas = json.load(file)
                            positions = {
                                "x": self.background_image.get_rect().right,
                                "y": self.background_image.get_rect().y
                            }
                            temp_map = Map(json_datas, positions, self, False)
                            self.maps_list.append(temp_map)
                            self.maps_names.append(temp_map.get_name())
                            temp_map_name = MapNameListItem(tracker=self,
                                                            ident=map_data["Id"],
                                                            name=json_datas[0]["Datas"]["Name"],
                                                            position=positions)
                            self.map_name_items_list.append(temp_map_name)
            if "RulesOptionsList" in self.tracker_json_data[4]:
                rules = self.tracker_json_data[4]["RulesOptions"]
                positions = {
                    "x": self.background_image.get_rect().right,
                    "y": self.background_image.get_rect().y
                }
                for i, rule in enumerate(rules):
                    temp_rule = RulesOptionsListItem(
                        tracker=self,
                        ident=i,
                        name=rule["Name"],
                        position=positions,
                        checked=True,
                        hide_checks=rule.get("HideChecks"),
                        actions=rule.get("Actions"),
                        active_on_start=rule.get("Active", False),
                        can_be_clickable=rule.get("CanBeClickable", True)
                    )
                    self.rules_options_items_list.append(temp_rule)
            self.change_map(self.map_name_items_list[0])
        for rule in [r for r in self.rules_options_items_list if r.active_on_start]:
            rule.left_click(force_click=True)
        self.update()

    def update_popup(self, popup, popup_datas, title, title_font, background_image, items_list):
        box_rect = pygame.Rect(
            (popup_datas["DrawBoxRect"]["x"] * self.core_service.zoom) + background_image.get_rect().x,
            (popup_datas["DrawBoxRect"]["y"] * self.core_service.zoom) + background_image.get_rect().y,
            popup_datas["DrawBoxRect"]["w"] * self.core_service.zoom,
            popup_datas["DrawBoxRect"]["h"] * self.core_service.zoom
        )
        popup.set_background_image_path(popup_datas["SubMenuBackground"])
        popup.set_arrow_left_image_path(popup_datas["LeftArrow"]["Image"])
        popup.set_arrow_right_image_path(popup_datas["RightArrow"]["Image"])
        popup.set_title(title)
        _, font_path = self.get_font_data(title_font)
        popup.set_title_font(self.core_service.get_font(title_font))
        popup.set_title_label_position_y(popup_datas["LabelY"])
        popup.set_list_items(items_list)
        popup.set_box_rect(box_rect)
        left_arrow = (popup_datas["LeftArrow"]["Positions"]["x"], popup_datas["LeftArrow"]["Positions"]["y"])
        right_arrow = (popup_datas["RightArrow"]["Positions"]["x"], popup_datas["RightArrow"]["Positions"]["y"])
        popup.set_arrows_positions(left_arrow, right_arrow)
        for item in items_list:
            item.update()
        popup.update()

    def update(self):
        caller = inspect.stack()[1]
        zoom = self.core_service.zoom
        if self.current_map:
            if "MapsList" in self.tracker_json_data[4]:
                box_label = self.tracker_json_data[4]["MapsList"]["MapListButtonLabelRect"]
                self.box_label_map_name_rect = pygame.Rect(
                    box_label["x"] * zoom,
                    box_label["y"] * zoom,
                    box_label["w"] * zoom,
                    box_label["h"] * zoom
                )
                _, font_path = self.get_font_data("mapFontListMaps")
                temp_surface = pygame.Surface((0, 0), pygame.SRCALPHA, 32).convert_alpha()
                self.surface_label_map_name, self.position_draw_label_map_name = MainMenu.MainMenu.draw_text(
                    text=self.current_map.get_name(),
                    font_name=font_path,
                    color=(255, 255, 255),
                    font_size=self.core_service.get_font("mapFontListMaps")["Size"] * zoom,
                    surface=temp_surface,
                    position=(self.box_label_map_name_rect.x, self.box_label_map_name_rect.y),
                    outline=1 * zoom)
                x = (self.box_label_map_name_rect.w / 2) - (self.surface_label_map_name.get_rect().w / 2) + self.box_label_map_name_rect.x
                y = (self.box_label_map_name_rect.h / 2) - (self.surface_label_map_name.get_rect().h / 2) + self.box_label_map_name_rect.y
                self.position_draw_label_map_name = (x, y)
                maps_list_box_datas = self.tracker_json_data[4]["MapsList"]["MapsListBox"]
                self.maps_list_background = self.bank.addZoomImage(
                    os.path.join(self.resources_path, maps_list_box_datas["SubMenuBackground"]))
                self.update_popup(popup=self.maps_list_window,
                                  popup_datas=maps_list_box_datas,
                                  title="Maps",
                                  title_font="mapFontTitle",
                                  background_image=self.maps_list_background,
                                  items_list=self.map_name_items_list)
            if "RulesOptionsList" in self.tracker_json_data[4]:
                rules_rect = self.tracker_json_data[4]["RulesOptionsList"]["RulesOptionsListButtonRect"]
                self.rules_options_button_rect = pygame.Rect(
                    rules_rect["x"] * zoom,
                    rules_rect["y"] * zoom,
                    rules_rect["w"] * zoom,
                    rules_rect["h"] * zoom
                )
                rules_options_box_datas = self.tracker_json_data[4]["RulesOptionsList"]["RulesOptionListBox"]
                self.rules_options_list_background = self.bank.addZoomImage(
                    os.path.join(self.resources_path, rules_options_box_datas["SubMenuBackground"]))
                self.update_popup(popup=self.rules_options_list_window,
                                  popup_datas=rules_options_box_datas,
                                  title="Rules Options",
                                  title_font="rulesOptionsFontTitle",
                                  background_image=self.rules_options_list_background,
                                  items_list=self.rules_options_items_list)

    def update_cpt(self):
        if self.current_map:
            self.cpt_checks_logics = 0
            self.cpt_all_checks = 0
            for map_item in self.maps_list:
                logic_checks_cpt, all_checks_cpt = map_item.get_count_checks()
                self.cpt_checks_logics += logic_checks_cpt
                self.cpt_all_checks += all_checks_cpt
            font_data, font_path = self.get_font_data("mapFontChecksNumber")
            cpt_checks_position = self.tracker_json_data[4]["CptChecksPosition"]
            temp_surface = pygame.Surface((300, 50), pygame.SRCALPHA, 32).convert_alpha()
            text = "Checks : {} logics / {} lefts".format(self.cpt_checks_logics, self.cpt_all_checks)
            self.surface_label_checks_cpt, self.position_draw_label_checks_cpt = MainMenu.MainMenu.draw_text(
                text=text,
                font_name=font_path,
                color=(255, 255, 255),
                font_size=font_data["Size"] * self.core_service.zoom,
                surface=temp_surface,
                position=(
                cpt_checks_position["x"] * self.core_service.zoom, cpt_checks_position["y"] * self.core_service.zoom),
                outline=1 * self.core_service.zoom)

    def change_map_by_map_name(self, map_name):
        for map_item in self.map_name_items_list:
            if map_item.name == map_name:
                self.change_map(map_item)

    def change_map(self, map_list_item):
        self.current_map = self.maps_list[map_list_item.id]
        self.current_map.can_be_updated = True
        self.current_map.active = True
        self.current_map.update()
        self.update()

    def init_item(self, item, item_list, manager):
        _item = None
        item_image = None
        items_sheet_dict = None
        item_sheet_name = None
        bypass = item["Kind"] == "EditableBox"
        if not bypass:
            items_sheet_dict = {sheet["Name"]: sheet for sheet in self.list_items_sheets}
            item_sheet_name = item["SheetInformation"]["SpriteSheet"]
        if bypass or item_sheet_name in items_sheet_dict:
            if not bypass:
                sheet = items_sheet_dict[item_sheet_name]
                item_image = self.core_service.zoom_image(
                    sheet["ImageSheet"].getImageWithRowAndColumn(
                        row=item["SheetInformation"]["row"],
                        column=item["SheetInformation"]["column"]
                    )
                )
            def get_position(item):
                return (item["Positions"]["x"] * self.core_service.zoom, item["Positions"]["y"] * self.core_service.zoom)
            def get_size(item):
                return (item["Sizes"]["w"] * self.core_service.zoom, item["Sizes"]["h"] * self.core_service.zoom)
            def create_base_item(item, item_class, **additional_args):
                return item_class(name=item["Name"],
                                  image=item_image,
                                  position=get_position(item),
                                  enable=item["isActive"],
                                  hint=item["Hint"],
                                  opacity_disable=item["OpacityDisable"],
                                  id=item["Id"],
                                  **additional_args)
            def create_evo_item(item, item_class):
                next_items_list = []
                for next_item in item["NextItems"]:
                    temp_item = {
                        "Name": next_item["Name"],
                        "Label": next_item["Label"],
                        "AlternativeLabel": next_item.get("AlternativeLabel")
                    }
                    for items_sheet in self.list_items_sheets:
                        if items_sheet["Name"] == next_item["SheetInformation"]["SpriteSheet"]:
                            temp_item["Image"] = self.core_service.zoom_image(
                                items_sheet["ImageSheet"].getImageWithRowAndColumn(
                                    row=next_item["SheetInformation"]["row"],
                                    column=next_item["SheetInformation"]["column"]
                                )
                            )
                    next_items_list.append(temp_item)
                item_args = {
                    "next_items": next_items_list,
                    "label": item["Label"],
                    "label_center": item["LabelCenter"],
                    "alternative_label": item.get("AlternativeLabel"),
                }
                if item["Kind"] == "AlternateEvolutionItem":
                    item_args["global_label"] = item.get("GlobalLabel")
                return create_base_item(item, item_class, **item_args)
            item_classes = {
                "AlternateCountItem": AlternateCountItem,
                "GoModeItem": GoModeItem,
                "CheckItem": CheckItem,
                "LabelItem": LabelItem,
                "CountItem": CountItem,
                "EvolutionItem": EvolutionItem,
                "AlternateEvolutionItem": AlternateEvolutionItem,
                "IncrementalItem": IncrementalItem,
                "SubMenuItem": SubMenuItem,
                "EditableBox": EditableBox,
                "DraggableEvolutionItem": DraggableEvolutionItem,
                "ImageItem": ImageItem,
                "Item": Item
            }
            if item["Kind"] in item_classes:
                item_class = item_classes[item["Kind"]]
                if item["Kind"] == "EditableBox":
                    _item = EditableBox(
                        id=item["Id"],
                        name=item["Name"],
                        position=get_position(item),
                        size=get_size(item),
                        manager=manager,
                        lines=item["Lines"],
                        style=item["Style"],
                        placeholder_text=item["PlaceHolder"]
                    )
                elif item["Kind"] == "AlternateCountItem":
                    _item = create_base_item(item, item_class,
                                             max_value=item["maxValue"],
                                             max_value_alternate=item["maxValueAlternate"],
                                             custom_font=item.get("customFont", None))
                elif item["Kind"] == "GoModeItem":
                    background_glow = self.bank.addZoomImage(os.path.join(self.resources_path, item["BackgroundGlow"]))
                    _item = create_base_item(item, item_class, background_glow=background_glow)
                elif item["Kind"] == "CheckItem":
                    check_image = None
                    for items_sheet in self.list_items_sheets:
                        if items_sheet["Name"] == item["CheckImageSheetInformation"]["SpriteSheet"]:
                            check_image = self.core_service.zoom_image(
                                items_sheet["ImageSheet"].getImageWithRowAndColumn(
                                    row=item["CheckImageSheetInformation"]["row"],
                                    column=item["CheckImageSheetInformation"]["column"]
                                )
                            )
                    _item = create_base_item(item, item_class, check_image=check_image)
                elif item["Kind"] == "LabelItem":
                    offset = item.get("OffsetLabel", 0)
                    _item = create_base_item(item, item_class,
                                             label_list=item["LabelList"],
                                             label_offset=offset)
                elif item["Kind"] == "CountItem":
                    _item = create_base_item(item, item_class,
                                             min_value=item["valueMin"],
                                             max_value=item["valueMax"],
                                             value_increase=item["valueIncrease"],
                                             value_start=item["valueStart"])
                elif item["Kind"] == "ImageItem":
                    _item = create_base_item(item, item_class)
                elif item["Kind"] in ("EvolutionItem", "DraggableEvolutionItem", "AlternateEvolutionItem"):
                    _item = create_evo_item(item, item_class)
                elif item["Kind"] == "IncrementalItem":
                    _item = create_base_item(item, item_class,
                                             increments=item["Increment"],
                                             start_increment_index=item.get("StartIncrementIndex"))
                elif item["Kind"] == "SubMenuItem":
                    _item = create_base_item(item, item_class,
                                             background_image=item["Background"],
                                             resources_path=self.resources_path,
                                             tracker=self,
                                             items_list=item["ItemsList"],
                                             show_numbers_items_active=item["ShowNumbersOfItemsActive"],
                                             show_numbers_checked_items=item["ShowNumberOfCheckedItems"])
                else:
                    _item = create_base_item(item, item_class)
            if item.get("HintItems", False):
                _item.hint_items_data = item.get("HintItems")
            if item.get("ActiveItems", False):
                _item.active_items_data = item.get("ActiveItems")
            if item.get("InactiveItems", False):
                _item.inactive_items_data = item.get("InactiveItems")
            if _item:
                item_list.add(_item)

    def init_items(self):
        for item in self.tracker_json_data[3]["Items"]:
            self.init_item(item, self.items, self.manager)
        for item in self.items:
            self.add_sub_special_item(item, "hint_items_data", "hint_items")
            self.add_sub_special_item(item, "active_items_data", "active_items")
            self.add_sub_special_item(item, "inactive_items_data", "inactive_items", visibility=item.show_item)

    def add_sub_special_item(self, item, data_items_name, items_list_name, visibility=False):
        item_data = getattr(item, data_items_name)
        if item_data:
            items_list = pygame.sprite.Group()
            for sub_item in item_data:
                self.init_item(sub_item, items_list, self.manager)
                setattr(item, items_list_name, items_list)
                for sub_special_item in items_list:
                    sub_special_item.show_item = visibility
                    self.items.add(sub_special_item)
                    self.add_sub_special_item(sub_special_item, "hint_items_data", "hint_items")
                    self.add_sub_special_item(sub_special_item, "active_items_data", "active_items")
                    self.add_sub_special_item(sub_special_item, "inactive_items_data", "inactive_items", visibility)

    def add_active_item(self, item):
        if item.hint_items_data:
            item.hint_items = pygame.sprite.Group()
            for sub_item in item.hint_items_data:
                self.init_item(sub_item, item.hint_items, self.manager)
                for sub_hint_item in item.hint_items:
                    sub_hint_item.show_item = False
                    self.items.add(sub_hint_item)
                    self.add_sub_special_item(sub_hint_item, "hint_items_data", "hint_items")

    def items_left_click(self, item_list, mouse_position):
        for item in item_list:
            if self.core_service.is_on_element(mouse_positions=mouse_position,
                                               element_positons=item.get_position(),
                                               element_dimension=(item.get_rect().w, item.get_rect().h)) and item.show_item:
                item.left_click()
                if self.core_service.sound_active:
                    if item.enable:
                        self.sound_select.play()
                    else:
                        self.sound_cancel.play()

    def items_click(self, item_list, mouse_position, button):
        for item in item_list:
            if item.check_click(mouse_position) and self.is_moving is None and item.show_item:
                if button == 1:
                    item.left_click()
                elif button == 2:
                    item.wheel_click()
                elif button == 3:
                    item.right_click()
                elif button == 4:
                    item.wheel_up()
                elif button == 5:
                    item.wheel_down()
                self.current_item_on_mouse = None
                if self.current_map:
                    self.current_map.update()
                if self.core_service.sound_active and button in (1, 3):
                    if item.enable:
                        self.sound_select.play()
                    else:
                        self.sound_cancel.play()
                return True
        return False

    def items_mouse_down(self, mouse_position, button, item_list):
        for item in item_list:
            if item.check_click(mouse_position) and not item.is_dragging and item.can_drag and item.show_item:
                item.is_dragging = True
                self.is_moving = item
                self.selected_items_list = item_list
                item.start_drag_time = pygame.time.get_ticks()

    def click_down(self, mouse_position, button):
        can_click = not any(submenu.show for submenu in self.submenus)
        if can_click:
            self.items_mouse_down(mouse_position, button, self.items)
        else:
            for submenu in self.submenus:
                if submenu.show:
                    self.items_mouse_down(mouse_position, button, submenu.items)

    def click(self, mouse_position, button):
        if self.is_moving:
            for item in self.selected_items_list:
                if item.check_click(mouse_position) and isinstance(item, DraggableEvolutionItem):
                    item.set_new_current_image(self.is_moving.get_colored_image(), self.is_moving.name)
                    break
            self.is_moving.is_dragging = False
            self.is_moving.reset_position()
            self.is_moving.update()
            self.is_moving = None
            return
        if not any(submenu.show for submenu in self.submenus):
            if self.current_map:
                self.current_map.click(mouse_position, button)
                if (not self.maps_list_window.is_open() and
                    not self.rules_options_list_window.is_open()) :#and
                    # not self.current_map.check_window.is_open()):
                    self.items_click(self.items, mouse_position, button)
                if self.maps_list_window.is_open():
                    self.maps_list_window.left_click(mouse_position)
                if self.rules_options_list_window.is_open():
                    self.rules_options_list_window.left_click(mouse_position)
                if (self.box_label_map_name_rect and
                    self.core_service.is_on_element(mouse_positions=mouse_position,
                                                    element_positons=(self.box_label_map_name_rect.x,
                                                                        self.box_label_map_name_rect.y),
                                                    element_dimension=(self.box_label_map_name_rect.w,
                                                                       self.box_label_map_name_rect.h))):
                    self.maps_list_window.open_window()
                    self.surface_check_zone_hint, self.position_check_zone_hint = (None, None)
                    self.mouse_check_found = None
                if (self.rules_options_button_rect and
                    self.core_service.is_on_element(mouse_positions=mouse_position,
                                                    element_positons=(self.rules_options_button_rect.x,
                                                                        self.rules_options_button_rect.y),
                                                    element_dimension=(self.rules_options_button_rect.w,
                                                                       self.rules_options_button_rect.h))):
                    self.rules_options_list_window.open_window()
            else:
                if not self.rules_options_list_window.is_open() or not self.maps_list_window.is_open():
                    self.items_click(self.items, mouse_position, button)
        else:
            for submenu in self.submenus:
                if submenu.show:
                    submenu.submenu_click(mouse_position, button)
                    for item in self.items:
                        if isinstance(item, SubMenuItem):
                            item.update()

    def mouse_move(self, mouse_position):
        submenu_found = any(submenu.show for submenu in self.submenus)
        if self.current_map and self.current_map.check_window.is_open():
            submenu_found = True
        if self.current_map and self.current_map.checks_list and not submenu_found:
            self.mouse_check_found = next(
                (check for check in self.current_map.checks_list
                 if not check.hide and not check.all_check_hidden() and not isinstance(check, ImageItem) and
                 self.core_service.is_on_element(mouse_positions=mouse_position,
                                                 element_positons=check.get_position(),
                                                 element_dimension=(check.get_rect().w, check.get_rect().h))),
                None
            )
            if self.mouse_check_found:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                self.surface_check_hint, self.position_check_hint = self.update_hint(self.mouse_check_found, "mapFontCheckHint", True)
                if self.mouse_check_found.zone:
                    self.surface_check_zone_hint, self.position_check_zone_hint = self.update_hint(self.mouse_check_found, "mapFontCheckZoneHint", True, zone=True)
                else:
                    self.surface_check_zone_hint, self.position_check_zone_hint = (None, None)
            else:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                self.mouse_check_found = None
                self.position_check_zone_hint = None
                self.surface_check_zone_hint = None
        if not self.maps_list_window.is_open() and not self.rules_options_list_window.is_open():
            found = False
            if not submenu_found:
                for item in self.items:
                    if (self.core_service.is_on_element(mouse_positions=mouse_position,
                                                         element_positons=item.get_position(),
                                                         element_dimension=(item.get_rect().w, item.get_rect().h))
                        and not isinstance(item, ImageItem)):
                        self.current_item_on_mouse = item
                        self.surface_check_hint, self.position_check_hint = self.update_hint(self.current_item_on_mouse, "labelItemFont", False)
                        found = True
            else:
                for submenu in self.submenus:
                    if submenu.show:
                        for item in submenu.items:
                            if (self.core_service.is_on_element(mouse_positions=mouse_position,
                                                                 element_positons=item.get_position(),
                                                                 element_dimension=(item.get_rect().w, item.get_rect().h))
                                and not isinstance(item, ImageItem)):
                                self.current_item_on_mouse = item
                                self.surface_check_hint, self.position_check_hint = self.update_hint(self.current_item_on_mouse, "labelItemFont", False)
                                found = True
            if not found:
                self.current_item_on_mouse = None

    def update_hint(self, item, font_session, top, zone=False):
        if item:
            font_data, font_path = self.get_font_data(font_session)
            color = self.core_service.get_color_from_font(font_data, "Normal")
            temp_surface = pygame.Surface((0, 0), pygame.SRCALPHA, 32).convert_alpha()
            text = (item.name + " - [" + type(item).__name__ + "]") if (self.core_service.dev_version and not zone) else (f'- {item.zone} -' if zone else item.name)
            surf, pos = MainMenu.MainMenu.draw_text(
                text=text,
                font_name=font_path,
                color=color,
                font_size=font_data["Size"] * self.core_service.zoom,
                surface=temp_surface,
                position=(0, 0),
                outline=1 * self.core_service.zoom
            )
            x = item.get_position()[0] - ((surf.get_rect().w / 2) - (item.get_rect().w / 2))
            y = item.get_position()[1] - surf.get_rect().h if top else item.get_position()[1] + item.get_rect().h - surf.get_rect().h
            return surf, (x, y)

    def save_data(self):
        datas = [{"template_name": self.template_name}]
        datas_items = [item.get_data() for item in self.items]
        datas.append({"items": datas_items})
        if self.maps_list:
            maps_datas = [map_data.get_data() for map_data in self.maps_list]
            datas.append({"maps": maps_datas})
            if self.rules_options_list_window.list_items:
                rules_datas = [rule.get_data() for rule in self.rules_options_list_window.list_items]
                datas.append({"rules": rules_datas})
        return datas

    def load_data(self, datas):
        if datas[0].get("template_name") != self.template_name:
            return
        item_lookup = {(item.base_name, item.id): item for item in self.items}
        if "items" in datas[1]:
            for data in datas[1]["items"]:
                item = item_lookup.get((data["name"], data["id"]))
                if item:
                    item.set_data(data)
        if len(datas) > 2 and "maps" in datas[2]:
            maps = datas[2].get("maps")
            if maps:
                for map_data in self.maps_list:
                    map_name = map_data.get_name()
                    map_data.load_data(next((m for m in maps if m["name"] == map_name), None))
                    map_data.update()
            if len(datas) > 3 and "rules" in datas[3]:
                rules = datas[3].get("rules")
                if rules:
                    for rule_data in rules:
                        rule = next((r for r in self.rules_options_list_window.list_items if r.name == rule_data["name"]), None)
                        if rule:
                            rule.set_data(rule_data)
                            rule.update()
            if self.current_map:
                self.update()
                self.update_cpt()
                self.current_map.update()

    def change_zoom(self, value):
        datas = self.save_data()
        self.core_service.zoom = value
        self.items = pygame.sprite.Group()
        self.submenus = pygame.sprite.Group()
        json_data_background = self.tracker_json_data[1]["Datas"]["Background"]
        self.background_image = self.bank.addZoomImage(os.path.join(self.resources_path, json_data_background))
        w = self.tracker_json_data[1]["Datas"]["Dimensions"]["width"] * self.core_service.zoom
        h = self.tracker_json_data[1]["Datas"]["Dimensions"]["height"] * self.core_service.zoom
        pygame.display.set_mode((w, h))
        self.init_items()
        self.menu.get_menu().resize(width=w, height=h)
        self.load_data(datas)
        self.update()
        if self.current_map:
            self.current_map.update()

    def reset_hint(self):
        self.mouse_check_found = False
        self.position_check_zone_hint = None
        self.surface_check_zone_hint = None

    def draw(self, screen, time_delta):
        screen.blit(self.background_image, (0, 0))
        if self.menu.get_menu().is_enabled():
            self.menu.get_menu().mainloop(screen)
        if self.core_service.draw_esc_menu_label:
            screen.blit(self.esc_menu_image, (2, 2))
        if self.current_map:
            self.current_map.draw_background(screen)
            self.items.draw(screen)
            for item in self.items:
                if isinstance(item, GoModeItem) and item.enable:
                    item.draw()
                    break
            self.current_map.draw(screen)
            if self.surface_label_map_name:
                screen.blit(self.surface_label_map_name, self.position_draw_label_map_name)
            screen.blit(self.surface_label_checks_cpt, self.position_draw_label_checks_cpt)
            if self.maps_list_window.is_open() or self.rules_options_list_window.is_open():
                info_object = pygame.display.Info()
                s = pygame.Surface((info_object.current_w, info_object.current_h), pygame.SRCALPHA)
                s.fill((0, 0, 0, 209))
                screen.blit(s, (0, 0))
                if self.maps_list_window.is_open():
                    self.maps_list_window.draw(screen)
                if self.rules_options_list_window.is_open():
                    self.rules_options_list_window.draw(screen)
            elif (self.mouse_check_found and not self.current_map.check_window.is_open()) or (self.core_service.show_hint_on_item and self.current_item_on_mouse):
                temp_rect = pygame.Rect(self.position_check_hint[0],
                                        self.position_check_hint[1],
                                        self.surface_check_hint.get_rect().w,
                                        self.surface_check_hint.get_rect().h)
                if self.surface_check_zone_hint and self.position_check_hint:
                    temp_rect = pygame.Rect(
                        temp_rect.x if self.position_check_hint[0] < self.position_check_zone_hint[0] else self.position_check_zone_hint[0],
                        temp_rect.y - self.surface_check_zone_hint.get_rect().h,
                        max(self.surface_check_hint.get_rect().w, self.surface_check_zone_hint.get_rect().w),
                        temp_rect.height + self.surface_check_zone_hint.get_rect().h)
                pygame.draw.rect(screen, (0, 0, 0), temp_rect)
                if self.surface_check_zone_hint and self.position_check_zone_hint:
                    screen.blit(self.surface_check_zone_hint, (self.position_check_zone_hint[0], self.position_check_zone_hint[1]))
                    screen.blit(self.surface_check_hint, (self.position_check_hint[0], self.position_check_hint[1] - self.surface_check_zone_hint.get_rect().h))
                else:
                    screen.blit(self.surface_check_hint, self.position_check_hint)
        else:
            self.items.draw(screen)
            for item in self.items:
                if isinstance(item, GoModeItem) and item.enable:
                    item.draw()
                    break
            self.manager.update(time_delta)
            self.manager.draw_ui(screen)
        for submenu in self.submenus:
            submenu.draw_submenu(screen, time_delta)
        if self.current_item_on_mouse and self.core_service.show_hint_on_item and self.current_item_on_mouse.show_item:
            temp_rect = pygame.Rect(self.position_check_hint[0],
                                    self.position_check_hint[1],
                                    self.surface_check_hint.get_rect().w,
                                    self.surface_check_hint.get_rect().h)
            pygame.draw.rect(screen, (0, 0, 0), temp_rect)
            screen.blit(self.surface_check_hint, self.position_check_hint)
        boxes = [item for item in self.items if isinstance(item, EditableBox)]
        for box in boxes:
            box.update_box(time_delta)

    def keyup(self, button, screen):
        if button == pygame.K_ESCAPE:
            if not self.menu.get_menu().is_enabled():
                self.menu.active(screen)

    def handle_event_boxes(self, item_list, events):
        boxes = [item for item in item_list if isinstance(item, EditableBox)]
        for box in boxes:
            box.handle_event(events)

    def events(self, events, time_delta):
        self.menu.events(events)
        self.manager.process_events(events)
        self.handle_event_boxes(self.items, events)
        if self.is_moving:
            self.is_moving.update()
        for submenu in self.submenus:
            if submenu.show:
                self.handle_event_boxes(submenu.items, events)
                submenu.manager.process_events(events)

    def back_main_menu(self):
        self.main_menu.reset_tracker()


    def find_item(self, item_name, is_base_name=False):
        """
        Search for an item (or its sub-item) whose name or base_name matches item_name.
        Iterates directly over items and, if needed, their sub-items.
        """
        for item in self.items:
            if isinstance(item, SubMenuItem):
                for sub_item in item.items:
                    name = sub_item.base_name if is_base_name else sub_item.name
                    if name == item_name:
                        return sub_item
            else:
                name = item.base_name if is_base_name else item.name
                if name == item_name:
                    return item
        return None

    @staticmethod
    def _item_has_index(item, condition):
        """
        Check if the item's 'value' attribute satisfies the condition.
        The condition must be in the form ">= 10", "< 5", etc.
        """
        if condition is None:
            return True
        try:
            value = getattr(item, 'value', None)
            m = Tracker.CONDITION_REGEX.match(condition)
            if m:
                op_str = m.group(1)
                threshold = float(m.group(2))
                ops = {
                    '>': operator.gt,
                    '<': operator.lt,
                    '>=': operator.ge,
                    '<=': operator.le,
                    '==': operator.eq,
                    '!=': operator.ne
                }
                return ops[op_str](value, threshold)
            else:
                return False
        except Exception:
            return False

    @staticmethod
    def _check_item(item, item_name, condition):
        """
        Verify that the item has the correct name, is enabled, and satisfies the index condition.
        """
        return item.name == item_name and item.enable and Tracker._item_has_index(item, condition)

    def have(self, item_name, condition=None):
        """
        Returns True if the item with the name item_name exists and satisfies the condition (if provided).
        """
        item = self.find_item(item_name)
        if item and Tracker._check_item(item, item_name, condition):
            return True
        return False

    def haveAlternateValue(self, item_name):
        item = self.find_item(item_name)
        return item and item.hint_show

    def isChecked(self, item_name):
        item = self.find_item(item_name)
        return isinstance(item, CheckItem) and item.check

    def isVisible(self, item_name):
        item = self.find_item(item_name)
        return item.show_item

    def do(self, action):
        """
        Execute the action if it exists in the JSON configuration.
        Preprocess the code (replace function calls), then compile and execute it.
        """
        actions_list = self.tracker_json_data[4]["ActionsConditions"]
        if action in actions_list:
            code_str = actions_list[action]
            if isinstance(code_str, str):
                code_str = code_str.strip()
                code_str = code_str.replace("have(", "self.have(") \
                    .replace("do(", "self.do(") \
                    .replace("rules(", "self.rules(") \
                    .replace("haveAlternateValue(", "self.haveAlternateValue(") \
                    .replace("isChecked(", "self.isChecked(") \
                    .replace("isVisible(", "self.isVisible(")
            else:
                code_str = action
            if action not in self._compiled_actions:
                self._compiled_actions[action] = compile(code_str, '<string>', 'eval')
            try:
                return eval(self._compiled_actions[action])
            except (TypeError, RecursionError):
                return False
        return False

    def rules(self, rule):
        """
        Check if a rule is active in the list of rule options.
        """
        if self.rules_options_list_window.list_items:
            for rule_option in self.rules_options_list_window.list_items:
                if rule_option.name == rule:
                    return rule_option.is_active()
            return False
        return False

    def check_sub_check(self, check, check_name):
        """
        Return the 'checked' value of the first sub-check whose name matches check_name.
        Uses 'next' to return immediately upon the first match.
        """
        sub = next((sub for sub in check.list_checks if sub.name == check_name), None)
        if sub is not None:
            return sub.checked
        return None

    def have_check(self, check_name, block_name=None):
        """
        Search through maps for checks that match check_name or block_name,
        then return the result of the first found check (using parallel processing if available).
        """
        tasks = [
            (check, check_name)
            for map_obj in self.maps_list
            for check in map_obj.checks_list
            if (isinstance(check, BlockChecks) and block_name is not None and check.name == block_name)
               or (isinstance(check, SimpleCheck) and check.name == check_name)
        ]
        if tasks and self._pool is not None:
            results = self._pool.starmap(self.check_sub_check, tasks)
            for result in results:
                if result is not None:
                    return result
        return None
