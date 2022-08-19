from Entities.Item import Item


class CheckListItem(Item):
    def __init__(self, id, name, image, position, enable, opacity_disable, text):
        self.text = text
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable, hint=None)