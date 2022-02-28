import os

import pygame

from Entities.Item import Item


class EvolutionItem(Item):
    def __init__(self, id, name, image, position, enable, opacity_disable, hint, next_items, label, label_center):
        self.label_center = label_center
        self.label = label
        self.next_item_index = -1
        self.next_items = next_items
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable, opacity_disable=opacity_disable, hint=hint)

    def left_click(self):
        if self.enable:
            if self.next_item_index < len(self.next_items) - 1:
                self.next_item_index = self.next_item_index + 1
            else:
                self.next_item_index = -1
                self.enable = False
        else:
            self.enable = True
        self.update()

    def right_click(self):
        if not self.enable:
            self.enable = True
            self.next_item_index = len(self.next_items) - 1
        else:
            if self.next_item_index >= 0:
                self.next_item_index = self.next_item_index - 1
            else:
                self.enable = False
        self.update()

    def update(self):
        Item.update(self)
        font = self.core_service.get_font("incrementalItemFont")
        font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])
        position = "right"
        if self.label_center:
            position = "center"

        print(len(self.next_items))

        if self.next_item_index >= 0:
            next_item = self.next_items[self.next_item_index]          
            
            if self.next_item_index == len(self.next_items) - 1:
                color_category = "Max"
            else:
                color_category = "Normal"

            self.image = self.get_drawing_text(font=font,
                                               color_category=color_category,
                                               text=next_item["Label"],
                                               font_path=font_path,
                                               base_image=self.image,
                                               image_surface=next_item["Image"],
                                               text_position=position)
            if self.hint_show:
                self.image = self.update_hint(self.image)

        elif self.enable:
            color_category = "Normal"
            if len(self.next_items) == 0:
                color_category = "Max"

            self.image = self.get_drawing_text(font=font,
                                               color_category=color_category,
                                               text=self.label,
                                               font_path=font_path,
                                               base_image=self.image,
                                               image_surface=self.image,
                                               text_position=position)

    def get_data(self):
        data = Item.get_data(self)
        data["next_item_index"] = self.next_item_index
        return data

    def set_data(self, datas):
        self.next_item_index = datas["next_item_index"]
        Item.set_data(self, datas)