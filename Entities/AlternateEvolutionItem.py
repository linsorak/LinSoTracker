import os

from Entities.EvolutionItem import EvolutionItem


class AlternateEvolutionItem(EvolutionItem):
    def __init__(self, id, name, image, position, enable, opacity_disable, hint, next_items, label, label_center,
                 alternative_label=None, global_label=None):
        self.global_label = global_label
        EvolutionItem.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                               opacity_disable=opacity_disable, hint=hint, next_items=next_items, label=label,
                               label_center=label_center, alternative_label=alternative_label)

    def left_click(self):
        if self.enable:
            self.enable = False
        else:
            self.enable = True

        self.update()

    def right_click(self):
        # if self.next_item_index >= 0:
        #     self.next_item_index = self.next_item_index - 1
        # else:
        #     self.next_item_index = self.next_item_index + 1
        if -1 <= self.next_item_index < len(self.next_items) - 1:
            self.next_item_index += 1
        else:
            self.next_item_index = -1

        self.update()

    def update(self):
        EvolutionItem.update(self)
        if self.global_label:
            font = self.core_service.get_font("labelItemFont")
            font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])
            color_category = "Normal"
            self.image = self.get_drawing_text(font=font,
                                               color_category=color_category,
                                               text=self.global_label,
                                               font_path=font_path,
                                               base_image=self.image,
                                               image_surface=self.image,
                                               text_position="label",
                                               offset=10)