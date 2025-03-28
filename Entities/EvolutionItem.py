import os

from Entities.Item import Item


class EvolutionItem(Item):
    def __init__(self, id, name, image, position, enable, opacity_disable, hint, next_items, label, label_center,
                 alternative_label=None, always_enable=False):
        self.label_center = label_center
        self.label = label
        self.base_label = label
        self.next_item_index = -1
        self.next_items = next_items
        self.alternative_label = alternative_label
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable, hint=hint, always_enable=always_enable)

    def left_click(self):
        if self.enable:
            if self.next_item_index < len(self.next_items) - 1:
                self.next_item_index = self.next_item_index + 1
                next_item = self.next_items[self.next_item_index]
                self.name = next_item["Name"]
                self.label = next_item["Label"]
            else:
                self.next_item_index = -1
                if not self.always_enable:
                    self.enable = False
                    self.name = self.base_name
                    self.label = self.base_label
                else:
                    self.name = self.base_name
                    self.label = self.base_label

        else:
            self.enable = True
        self.update()

    def right_click(self):
        if not self.enable:
            self.enable = True
            self.next_item_index = len(self.next_items) - 1
            next_item = self.next_items[self.next_item_index]
            self.name = next_item["Name"]
            self.label = next_item["Label"]
        else:
            if self.next_item_index > 0:
                self.next_item_index = self.next_item_index - 1
                next_item = self.next_items[self.next_item_index]
                self.name = next_item["Name"]
                self.label = next_item["Label"]
            elif self.next_item_index == 0:
                self.next_item_index = self.next_item_index - 1
                self.name = self.base_name
                self.label = self.base_label
            else:
                if not self.always_enable:
                    self.enable = False
                    self.name = self.base_name
                    self.label = self.base_label
                else:
                    self.next_item_index = len(self.next_items) - 1
                    next_item = self.next_items[self.next_item_index]
                    self.name = next_item["Name"]
                    self.label =  next_item["Label"]
        self.update()

    def update(self):
        Item.update(self)
        font = self.core_service.get_font("evolutionItemFont")
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

            if self.hint_show:
                self.image = self.update_hint(next_item["Image"])
            else:
                self.image = next_item["Image"]

            if self.hint_show and ("AlternativeLabel" in next_item):
                draw_label = next_item["AlternativeLabel"]
            else:
                draw_label = next_item["Label"]

            image_draw = self.image.copy()
            if not self.enable:
                image_draw = self.image.convert_alpha()
                self.core_service.convert_to_gs(image_draw)
                image_draw = self.alpha_image(image_draw)

            self.image = self.get_drawing_text(font=font,
                                               color_category=color_category,
                                               text=draw_label,
                                               font_path=font_path,
                                               base_image=image_draw,
                                               image_surface=image_draw,
                                               text_position=position)

        elif self.enable:
            color_category = "Normal"
            if len(self.next_items) == 0:
                color_category = "Max"

            if self.hint_show and self.alternative_label is not None:
                draw_label = self.alternative_label
            else:
                draw_label = self.label

            self.image = self.get_drawing_text(font=font,
                                               color_category=color_category,
                                               text=draw_label,
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
        if datas["next_item_index"] != -1:
            next_item = self.next_items[self.next_item_index]
            self.name = next_item["Name"]
            self.label = next_item["Label"]
        else:
            self.name = self.base_name
            self.label = self.base_label

    def get_colored_image(self):
        if not self.enable:
            return self.colored_image
        else:
            return self.image

    def reinitialize(self):
        self.next_item_index = -1
        self.name = self.base_name
        self.label = self.base_label
        Item.reinitialize(self)