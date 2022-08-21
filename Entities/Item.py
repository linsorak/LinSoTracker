import os

import pygame

from Tools import ptext
from Tools.CoreService import CoreService


class Item(pygame.sprite.Sprite):
    def __init__(self, id, name, position, image, opacity_disable, hint, enable=True):
        pygame.sprite.Sprite.__init__(self)
        self.id = id
        self.hint = hint
        self.hint_show = False
        self.name = name
        self.base_name = self.name
        self.opacity_disable = opacity_disable
        self.enable = enable
        self.position = position
        self.core_service = CoreService()
        self.colored_image = image.convert_alpha()
        self.grey_image = image.convert_alpha()
        self.core_service.convert_to_gs(self.grey_image)
        self.left_hint = False

        self.image = self.colored_image
        self.rect = pygame.Rect(self.position[0], self.position[1], self.image.get_rect().width,
                                self.image.get_rect().height)
        self.update()

    def get_position(self):
        return self.position

    def get_rect(self):
        return self.rect

    def alpha_image(self, image):
        return self.core_service.set_image_transparent(image=image, opacity_disable=self.opacity_disable)

    def update(self):
        if not self.enable:
            # transparent_image = self.grey_image.copy()
            # transparent_image.fill((255, 255, 255, 255 * self.opacity_disable), special_flags=pygame.BLEND_RGBA_MULT)
            self.image = self.alpha_image(self.grey_image)
        else:
            self.image = self.colored_image

        if self.hint_show:
            self.image = self.update_hint(self.image)

    def update_hint(self, image):
        # self.update()
        font = self.core_service.get_font("hintFont")
        font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])
        image = self.get_drawing_text(font=font,
                                      color_category="Normal",
                                      text=self.hint,
                                      font_path=font_path,
                                      base_image=image,
                                      image_surface=image,
                                      text_position="hint",
                                      o_width=2)
        return image

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
        if self.hint is not None:
            if self.hint_show:
                self.hint_show = False
            else:
                self.hint_show = True

            self.update()

    def generate_text(self, text, font_name, color, font_size, o_width=2):
        tempSurface = pygame.Surface((400, 400)).convert_alpha()
        tsurf, tpos = ptext.draw(str(text), (0, 0), fontname=font_name, antialias=True,
                                 owidth=o_width, ocolor=(0, 0, 0), color=color, fontsize=font_size, surf=tempSurface)

        ptext.MEMORY_REDUCTION_FACTOR = 0
        ptext.AUTO_CLEAN = True
        return tsurf, tpos

    def get_name(self):
        return self.name

    def get_drawing_text(self, font, color_category, text, font_path, base_image, image_surface, text_position,
                         o_width=2, offset=0):
        if text is not None:
            color = (font["Colors"][color_category]["r"], font["Colors"][color_category]["g"],
                     font["Colors"][color_category]["b"])
            tsurf, tpos = self.generate_text(text=text, font_name=font_path,
                                             font_size=font["Size"] * self.core_service.zoom,
                                             color=color,
                                             o_width=o_width)
            x = 0
            y = base_image.get_rect().h - tsurf.get_rect().h / 1.5
            w = image_surface.get_rect().w
            h = image_surface.get_rect().h + tsurf.get_rect().h / 1.5
            pos_x = 0
            pos_y = 0

            if text_position == "center":
                x = (image_surface.get_rect().w / 2) - (tsurf.get_rect().w / 2)
            elif text_position == "right":
                x = (image_surface.get_rect().w - tsurf.get_rect().w)
                y = base_image.get_rect().h - tsurf.get_rect().h
                w = w + tsurf.get_rect().w / 1.5
            elif text_position == "count_item":
                w = base_image.get_rect().w * 2
                x = base_image.get_rect().w + (base_image.get_rect().w / 2 - tsurf.get_rect().w / 2)
                y = base_image.get_rect().h / 2 - tsurf.get_rect().h / 2
            elif text_position == "hint":
                if self.left_hint:
                    x = 0
                else:
                    x = base_image.get_rect().w - tsurf.get_rect().w
                y = 0
                h = image_surface.get_rect().h

            elif text_position == "label":
                x = (image_surface.get_rect().w / 2) - (tsurf.get_rect().w / 2)
                y = (image_surface.get_rect().h - (tsurf.get_rect().h / 5)) - (offset * self.core_service.zoom)
                h = image_surface.get_rect().h + tsurf.get_rect().h
                if tsurf.get_rect().w > image_surface.get_rect().w:
                    pos_x = image_surface.get_rect().w - tsurf.get_rect().w
                    w = tsurf.get_rect().w - pos_x
                    x = x - pos_x

            tempSurface = pygame.Surface(([w, h]), pygame.SRCALPHA, 32)
            tempSurface = tempSurface.convert_alpha()
            tempSurface.blit(image_surface, (pos_x * -1, pos_y))
            tempSurface.blit(tsurf, (x, y))
            self.rect = pygame.Rect(self.position[0] + pos_x, self.position[1], self.image.get_rect().width,
                                    self.image.get_rect().height)
        else:
            tempSurface = pygame.Surface(
                [image_surface.get_rect().w, image_surface.get_rect().h],
                pygame.SRCALPHA, 32)
            tempSurface = tempSurface.convert_alpha()
            tempSurface.blit(image_surface, (0, 0))

        return tempSurface

    def get_data(self):
        data = {
            "id": self.id,
            "name": self.name,
            "enable": self.enable,
            "hint_show": self.hint_show
        }
        return data

    def set_data(self, datas):
        self.enable = datas["enable"]
        self.hint_show = datas["hint_show"]
        self.update()
