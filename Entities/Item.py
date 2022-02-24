import pygame

from Tools import ptext
from Tools.CoreService import CoreService


class Item(pygame.sprite.Sprite):
    def __init__(self, name, position, image, opacity_disable, hint, enable=True):
        pygame.sprite.Sprite.__init__(self)
        self.hint = hint
        self.name = name
        self.opacity_disable = opacity_disable
        self.enable = enable
        self.position = position
        self.core_service = CoreService()
        self.colored_image = image.convert_alpha()
        self.grey_image = image.convert_alpha()
        self.core_service.convert_to_gs(self.grey_image)

        self.image = self.colored_image
        self.rect = pygame.Rect(self.position[0], self.position[1], self.image.get_rect().width, self.image.get_rect().height)
        self.update()


    def get_position(self):
        return self.position

    def get_rect(self):
        return self.rect

    def update(self):
        if not self.enable:
            transparent_image = self.grey_image.copy()
            transparent_image.fill((255, 255, 255, 255 * self.opacity_disable), special_flags=pygame.BLEND_RGBA_MULT)
            self.image = transparent_image
        else:
            self.image = self.colored_image

    def left_click(self):
        if self.enable:
            self.enable = False
        else:
            self.enable = True
        self.update()

    def right_click(self):
        self.left_click()
        self.update()

    def wheel_click(self):
        pass

    def generate_text(self, text, font_name, color, font_size):
        tempSurface = pygame.Surface((400, 400)).convert_alpha()
        tsurf, tpos = ptext.draw(str(text), (0, 0), fontname=font_name, antialias=True,
                                 owidth=3, ocolor=(0, 0, 0), color=color, fontsize=font_size, surf=tempSurface)
        return tsurf, tpos

    def get_name(self):
        return self.name

    def get_drawing_text(self, font, color_category, text, font_path, base_image, image_surface, text_position):
        if text is not None:
            color = (font["Colors"][color_category]["r"], font["Colors"][color_category]["g"], font["Colors"][color_category]["b"])
            tsurf, tpos = self.generate_text(text=text, font_name=font_path, font_size=font["Size"],
                                             color=color)
            x = 0
            y = base_image.get_rect().h - tsurf.get_rect().h / 1.5
            w = image_surface.get_rect().w

            if text_position == "center":
                x = (image_surface.get_rect().w / 2) - (tsurf.get_rect().w / 2)
            elif text_position == "right":
                x = (image_surface.get_rect().w - tsurf.get_rect().w )
                y = base_image.get_rect().h - tsurf.get_rect().h
                w = w + tsurf.get_rect().w / 1.5

            tempSurface = pygame.Surface(
                [w, image_surface.get_rect().h + tsurf.get_rect().h / 1.5],
                pygame.SRCALPHA, 32)
            tempSurface = tempSurface.convert_alpha()
            tempSurface.blit(image_surface, (0, 0))
            tempSurface.blit(tsurf, (x, y))
        else:
            tempSurface = pygame.Surface(
                [image_surface.get_rect().w, image_surface.get_rect().h],
                pygame.SRCALPHA, 32)
            tempSurface = tempSurface.convert_alpha()
            tempSurface.blit(image_surface, (0, 0))

        return tempSurface