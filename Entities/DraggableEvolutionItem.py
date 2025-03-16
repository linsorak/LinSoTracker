from Entities.EvolutionItem import EvolutionItem


class DraggableEvolutionItem(EvolutionItem):
    def __init__(self, id, name, image, position, enable, opacity_disable, hint, next_items, label, label_center,
                 alternative_label=None):
        EvolutionItem.__init__(self, id, name, image, position, enable, opacity_disable, hint, next_items, label,
                               label_center,
                               alternative_label)
        self.can_drag = False

    def set_new_current_image(self, image, name):
        self.enable = True
        self.next_item_index = -1
        self.image = image
        self.name = name
        # self.update()

    def get_data(self):
        data = EvolutionItem.get_data(self)
        return data

    def set_data(self, datas):
        EvolutionItem.set_data(self, datas)