import os.path

from Entities.Item import Item


class IncrementalItem(Item):
    def __init__(self, id, name, image, position, enable, opacity_disable, increments, hint):
        self.increments_position = -1
        self.increments = increments
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable, hint=hint)

    def left_click(self):
        if self.enable:
            if self.increments_position < len(self.increments) - 1:
                self.increments_position = self.increments_position + 1
            else:
                self.increments_position = -1
                self.enable = False
        else:
            self.enable = True
        self.update()

    def right_click(self):
        if not self.enable:
            self.enable = True
            self.increments_position = len(self.increments) - 1
        else:
            if self.increments_position >= 0:
                self.increments_position = self.increments_position - 1
            else:
                self.enable = False
        self.update()

    def update(self):
        Item.update(self)

        if self.increments_position >= 0:
            font = self.core_service.get_font("incrementalItemFont")
            font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])

            if self.increments_position == len(self.increments) - 1:
                color_category = "Max"
            else:
                color_category = "Normal"

            self.image = self.get_drawing_text(font=font,
                                               color_category=color_category,
                                               text=self.increments[self.increments_position],
                                               font_path=font_path,
                                               base_image=self.image,
                                               image_surface=self.image,
                                               text_position="left")

    def get_data(self):
        data = Item.get_data(self)
        data["increments_position"] = self.increments_position
        return data

    def set_data(self, datas):
        self.increments_position = datas["increments_position"]
        Item.set_data(self, datas)
