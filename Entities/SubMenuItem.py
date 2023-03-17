import os

import pygame

from Entities.CheckItem import CheckItem
from Entities.Item import Item
from Tools.Bank import Bank


class SubMenuItem(Item):
    def __init__(self, id, name, image, position, enable, opacity_disable, hint, background_image, resources_path,
                 tracker, items_list, show_numbers_items_active, show_numbers_checked_items):
        self.background_image_name = background_image
        self.background_image = None
        self.base_image = None
        self.resources_path = resources_path
        self.show_numbers_items_active = show_numbers_items_active
        self.show_numbers_checked_items = show_numbers_checked_items
        self.show = False
        self.items = pygame.sprite.Group()
        self.bank = Bank()
        self.tracker = tracker
        self.items_list = items_list
        self.counter_enable = 0
        self.init_items()
        self.update_background()
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable,
                      hint=hint)

        self.tracker.submenus.add(self)

    def update(self):
        Item.update(self)

        if not self.show_numbers_items_active:
            return

        self.counter_enable = sum(1 for item in self.items if item.enable)
        self.counter_check = sum(1 for item in self.items if isinstance(item, CheckItem) and item.check)

        font = self.core_service.get_font("subMenuItemFont")
        font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])

        color_category = "Normal" if self.counter_enable != len(self.items) else "Max"

        text_draw = "{}/{}".format(self.counter_check,
                                   self.counter_enable) if self.show_numbers_checked_items else "{}/{}".format(
            self.counter_enable, len(self.items))

        self.image = self.get_drawing_text(font=font,
                                           color_category=color_category,
                                           text=text_draw,
                                           font_path=font_path,
                                           base_image=self.image,
                                           image_surface=self.image,
                                           text_position="right",
                                           offset=10)

    def update_background(self):
        self.background_image = self.bank.addZoomImage(os.path.join(self.resources_path, self.background_image_name))

    def draw_submenu(self, screen):
        if self.show:
            info_object = pygame.display.Info()
            s = pygame.Surface((info_object.current_w, info_object.current_h), pygame.SRCALPHA)  # per-pixel alpha
            s.fill((0, 0, 0, 209))  # notice the alpha value in the color
            screen.blit(s, (0, 0))

            screen.blit(self.background_image, (0, 0))
            self.items.draw(screen)

    def init_items(self):
        for item in self.items_list:
            self.tracker.init_item(item, self.items, self.tracker.items_sheet_data)

    def left_click(self):
        if self.show:
            self.show = False
        else:
            self.show = True

    def right_click(self):
        pass

    def wheel_click(self):
        pass

    def submenu_click(self, mouse_position, button):
        if self.show:
            self.show = self.tracker.items_click(self.items, mouse_position, button)

    def get_data(self):
        data = Item.get_data(self)
        items_datas = []

        for item in self.items:
            items_datas.append(item.get_data())

        data["submenu_items"] = items_datas
        return data

    def set_data(self, datas):
        # self.increments_position = datas["increments_position"]
        for item_datas in datas["submenu_items"]:
            for item in self.items:
                if item_datas["name"] == item.name and item_datas["id"] == item.id:
                    item.set_data(item_datas)
                    break

        Item.set_data(self, datas)
