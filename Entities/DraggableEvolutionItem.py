from Entities.EvolutionItem import EvolutionItem


class DraggableEvolutionItem(EvolutionItem):
    def __init__(self, id, name, image, position, enable, opacity_disable, hint, next_items, label, label_center,
                 alternative_label=None, always_enable=False):
        self.can_drag = False
        self.dragged_item_name = None
        self.dragged_item_basename = None
        self.dragged_item_index = None
        EvolutionItem.__init__(self, id, name, image, position, enable, opacity_disable, hint, next_items, label,
                               label_center, alternative_label, always_enable=always_enable)

    def update_image(self):
        if self.dragged_item_name:
            tracker = self.core_service.get_current_tracker()
            item = tracker.find_item(self.dragged_item_name, self.dragged_item_name == self.dragged_item_basename)
            if item:
                if self.dragged_item_index and hasattr(item, "next_item_index"):
                    if self.dragged_item_index > -1:
                        self.image = item.next_items[self.dragged_item_index]["Image"]
                    else:
                        self.image = item.colored_image
                else:
                    self.image = item.image

    def update(self):
        EvolutionItem.update(self)
        self.update_image()

    def sub_click(self):
        if self.dragged_item_name:
            self.next_item_index = -1
            self.dragged_item_name = None
            self.dragged_item_basename = None
            self.name = self.base_name
            self.image = self.colored_image

    def left_click(self):
        EvolutionItem.left_click(self)
        self.sub_click()

    def right_click(self):
        EvolutionItem.right_click(self)
        self.sub_click()

    def set_new_current_image(self, name, base_name, index=None):
        self.enable = True
        self.next_item_index = -1
        self.dragged_item_name = name
        self.dragged_item_basename = base_name
        self.dragged_item_index = index
        self.update()

    def get_data(self):
        data = EvolutionItem.get_data(self)
        data["dragged_item_name"] = self.dragged_item_name
        data["dragged_item_basename"] = self.dragged_item_basename
        data["dragged_item_index"] = self.dragged_item_index
        return data

    def set_data(self, datas):
        self.dragged_item_name = datas["dragged_item_name"]
        self.dragged_item_basename = datas["dragged_item_basename"]
        self.dragged_item_index = datas["dragged_item_index"]
        EvolutionItem.set_data(self, datas)
        self.update_image()