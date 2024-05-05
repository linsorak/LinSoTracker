import os

from Entities.Item import Item


class AlternateCountItem(Item):
    def __init__(self, id, name, position, image, opacity_disable, hint, max_value, max_value_alternate, enable=True, custom_font=None):
        self.max_value = max_value
        self.max_value_alternate = max_value_alternate
        self.used_max_value = self.max_value
        self.value = 0
        self.custom_font = custom_font
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable,
                      hint=hint)
        self.left_hint = True

    def update(self):
        Item.update(self)
        font = self.core_service.get_font("incrementalItemFont")

        if self.custom_font:
            font = self.core_service.get_custom_font(self.custom_font)

        font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])
        position = "right"

        if self.value > 0:
            if self.value == self.used_max_value:
                color_category = "Max"
            else:
                color_category = "Normal"

            self.image = self.get_drawing_text(font=font,
                                               color_category=color_category,
                                               text=self.value,
                                               font_path=font_path,
                                               base_image=self.image,
                                               image_surface=self.image,
                                               text_position=position)

    def right_click(self):
        if self.value > 0:
            self.value = self.value - 1
        else:
            self.value = self.used_max_value

        if self.value == 0:
            self.enable = False
        else:
            self.enable = True

        self.update()

    def left_click(self):
        if self.value < self.used_max_value:
            self.value = self.value + 1
            self.enable = True
        else:
            self.value = 0
            self.enable = False

        self.update()

    def wheel_click(self):
        Item.wheel_click(self)
        if self.hint_show:
            self.used_max_value = self.max_value_alternate
            self.image = self.update_hint(self.image)
        else:
            self.used_max_value = self.max_value

        if self.value >= self.used_max_value:
            self.value = self.used_max_value

        self.update()

    def wheel_up(self):
        self.left_click()

    def wheel_down(self):
        self.right_click()

    def get_data(self):
        data = Item.get_data(self)
        data["value"] = self.value
        data["maxUsedValue"] = self.used_max_value
        return data

    def set_data(self, datas):
        self.value = datas["value"]
        self.used_max_value = datas["maxUsedValue"]
        Item.set_data(self, datas)
