import pygame

from Entities.Item import Item


class CheckItem(Item):
    def __init__(self, id, name, position, image, opacity_disable, hint, check_image, enable=True):
        self.check_image = check_image
        self.check = False
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable,
                      hint=hint)

    def right_click(self):
        if self.check:
            self.check = False
        else:
            self.check = True
        self.update()

    def update(self):
        Item.update(self)
        if self.check:
            x = self.check_image.get_rect().w / 4
            y = (self.check_image.get_rect().h / 4) * -1
            tempSurface = pygame.Surface(([self.image.get_rect().w, self.image.get_rect().h]), pygame.SRCALPHA, 32)
            tempSurface = tempSurface.convert_alpha()
            tempSurface.blit(self.image, (0, 0))
            tempSurface.blit(self.check_image, (x, y))
            self.image = tempSurface

    def get_data(self):
        data = Item.get_data(self)
        data["check"] = self.check
        return data

    def set_data(self, datas):
        self.check = datas["check"]
        Item.set_data(self, datas)

    def reinitialize(self):
        self.check = False
        Item.reinitialize(self)