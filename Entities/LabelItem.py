import os

from Entities.Item import Item


class LabelItem(Item):
    def __init__(self, id, name, position, image, opacity_disable, hint, enable, label_list, label_offset=0):
        self.label_count = 0
        self.label_list = label_list
        self.label_offset = label_offset
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable,
                      hint=hint)

    def update(self):
        Item.update(self)
        font = self.core_service.get_font("labelItemFont")
        font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])
        color_category = "Normal"
        self.image = self.get_drawing_text(font=font,
                                           color_category=color_category,
                                           text=self.label_list[self.label_count],
                                           font_path=font_path,
                                           base_image=self.image,
                                           image_surface=self.image,
                                           text_position="label",
                                           offset=self.label_offset)

    def right_click(self):
        if self.label_count < len(self.label_list) - 1:
            self.label_count += 1
        else:
            self.label_count = 0

        self.update()

    def get_data(self):
        data = Item.get_data(self)
        data["label_count"] = self.label_count
        return data

    def set_data(self, datas):
        self.label_count = datas["label_count"]
        Item.set_data(self, datas)
