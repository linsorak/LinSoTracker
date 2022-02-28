import pygame

from Entities.Item import Item


class GoModeItem(Item):
    def __init__(self, id, name, image, position, enable, opacity_disable, hint, background_glow):
        self.background_glow = background_glow
        self.angle = 0
        self.speed = 2
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable, opacity_disable=opacity_disable, hint=hint)

    def update(self):
        Item.update(self)
        if self.enable:
            x_image = (self.background_glow.get_rect().w / 2) - (self.image.get_rect().w / 2)
            y_image = (self.background_glow.get_rect().h / 2) - (self.image.get_rect().h / 2)
            pos_x = x_image * -1
            pos_y = y_image * -1
            tempSurface = pygame.Surface(([self.background_glow.get_rect().w, self.background_glow.get_rect().h]), pygame.SRCALPHA, 32)
            tempSurface = tempSurface.convert_alpha()
            if self.angle > 360:
                self.angle = 0
            self.angle += self.speed
            light = pygame.transform.rotozoom(self.background_glow, self.angle, 1)
            light_rect = light.get_rect()
            light_rect.center = (self.background_glow.get_rect().w / 2, self.background_glow.get_rect().h / 2)
            tempSurface.blit(light, light_rect)
            tempSurface.blit(self.image, (x_image, y_image))
            self.image = tempSurface
            self.rect = pygame.Rect(self.position[0] + pos_x, self.position[1] + pos_y, self.colored_image.get_rect().width,
                                    self.colored_image.get_rect().height)
        else:
            self.image =  pygame.Surface(([self.colored_image.get_rect().w, self.colored_image.get_rect().h]), pygame.SRCALPHA, 32)
            self.image = self.image.convert_alpha()
            self.rect = pygame.Rect(self.position[0], self.position[1] , self.colored_image.get_rect().width,
                                    self.colored_image.get_rect().height)

    def draw(self):
        self.update()