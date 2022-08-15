import json
import os

import pygame

from Entities.Item import Item
from Tools.Bank import Bank


class SubMenuItem(Item):
    def __init__(self, id, name, image, position, enable, opacity_disable, hint, background_image, resources_path, tracker, items_list):
        self.background_image_name = background_image
        self.background_image = None
        self.resources_path = resources_path
        self.show = False
        self.items = pygame.sprite.Group()
        self.bank = Bank()
        self.tracker = tracker
        self.items_list = items_list
        self.init_items()
        self.update_background()
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable,
                      hint=hint)

        self.tracker.submenus.add(self)

    def update_background(self):
        self.background_image = self.bank.addZoomImage(os.path.join(self.resources_path, self.background_image_name))

    def draw_submenu(self, screen):
        if self.show:
            screen.blit(self.background_image, (0, 0))
            self.items.draw(screen)

    def init_items(self):
        for item in self.items_list:
            self.tracker.init_item(item, self.items)

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
        print(self.id)
        return data

    def set_data(self, datas):
        # self.increments_position = datas["increments_position"]
        for item_datas in datas["submenu_items"]:
            for item in self.items:
                if item_datas["name"] == item.name and item_datas["id"] == item.id:
                    item.set_data(item_datas)
                    break

        Item.set_data(self, datas)



