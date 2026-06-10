import pygame

from Entities.Item import Item


class GoModeItem(Item):
    def __init__(self, id, name, image, position, enable, opacity_disable, hint, background_glow, always_enable=False):
        self.background_glow = background_glow
        self.glow_image = None
        self.glow_rect = pygame.Rect(0, 0, 0, 0)
        self.angle = 0
        self.speed = 2
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable, hint=hint, always_enable=always_enable)
        self.can_drag = False

    def update(self):
        Item.update(self)
        if self.enable:
            if self.angle > 360 or self.angle < -360:
                self.angle = 0
            if self.core_service.go_mode_glow_clockwise:
                self.angle -= self.speed
            else:
                self.angle += self.speed
            self.image = self.colored_image
            self.rect = pygame.Rect(self.position[0], self.position[1], self.colored_image.get_rect().width,
                                    self.colored_image.get_rect().height)
            self.glow_image = pygame.transform.rotozoom(self.background_glow, self.angle, 1)
            self.glow_rect = self.glow_image.get_rect(center=self.rect.center)
        else:
            self.image = pygame.Surface(([self.colored_image.get_rect().w, self.colored_image.get_rect().h]),
                                        pygame.SRCALPHA, 32)
            self.image = self.image.convert_alpha()
            self.rect = pygame.Rect(self.position[0], self.position[1], self.colored_image.get_rect().width,
                                    self.colored_image.get_rect().height)
            self.glow_image = None
            self.glow_rect = pygame.Rect(0, 0, 0, 0)

    def draw(self):
        self.update()

    def draw_glow(self, screen):
        if self.enable and self.glow_image:
            screen.blit(self.glow_image, self.glow_rect)


