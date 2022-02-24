import os

import pygame

from Entities.Item import Item


class EvolutionItem(Item):
    def __init__(self, name, image, position, enable, opacity_disable, hint, next_items, label, label_center):
        self.label_center = label_center
        self.label = label
        self.next_item_index = -1
        self.next_items = next_items
        Item.__init__(self, name=name, image=image, position=position, enable=enable, opacity_disable=opacity_disable, hint=hint)

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
        elif self.enable:
            self.image = self.get_drawing_text(font=font,
                                               color_category="Normal",
                                               text=self.label,
                                               font_path=font_path,
                                               base_image=self.image,
                                               image_surface=self.colored_image,
                                               text_position=position)