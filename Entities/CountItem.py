import os

import pygame

from Entities.Item import Item


class CountItem(Item):
    def __init__(self, id, name, position, image, opacity_disable, hint, min_value, max_value, value_increase,
                 value_start, enable=True):
        self.value = value_start
        self.value_increase = value_increase
        self.max_value = max_value
        self.min_value = min_value
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable,
                      hint=hint)

    def update(self):
        Item.update(self)

        font = self.core_service.get_font("countItemFont")
        font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])

        if self.value == self.max_value:
            color_category = "Max"
        else:
            color_category = "Normal"

        self.image = self.get_drawing_text(font=font,
                                           color_category=color_category,
                                           text=self.value,
                                           font_path=font_path,
                                           base_image=self.image,
                                           image_surface=self.colored_image,
                                           text_position="count_item")
        self.rect = pygame.Rect(self.position[0], self.position[1], self.image.get_rect().width,
                                self.image.get_rect().height)

    def right_click(self):
        if self.value > self.min_value:
            self.value = self.value - self.value_increase
        else:
            self.value = self.max_value

        self.update()

    def left_click(self):
        if self.value < self.max_value:
            self.value = self.value + self.value_increase
        else:
            self.value = self.min_value

        self.update()

    def get_data(self):
        data = Item.get_data(self)
        data["value"] = self.value
        return data

    def set_data(self, datas):
        self.value = datas["value"]
        Item.set_data(self, datas)
