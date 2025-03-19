from Entities.Item import Item


class ImageItem(Item):
    def __init__(self, id, name, position, image, opacity_disable, hint, enable=True, always_enable=False):
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable,hint=hint, always_enable=always_enable)
        self.can_drag = False

    def right_click(self):
        pass

    def left_click(self):
        pass

    def wheel_click(self):
        pass

