import os

import pygame

from Tools import ptext
from Tools.CoreService import CoreService


class Item(pygame.sprite.Sprite):
    def __init__(self, id, name, position, image, opacity_disable, hint, enable=True, show_item=True):
        pygame.sprite.Sprite.__init__(self)
        self.id = id
        self.show_item = show_item
        self.hint = hint
        self.hint_show = False
        self.name = name
        self.base_name = self.name
        self.opacity_disable = opacity_disable
        self.enable = enable
        self.position = position
        self.base_position = position
        self.core_service = CoreService()
        self.colored_image = image.convert_alpha()
        self.grey_image = image.convert_alpha()
        self.core_service.convert_to_gs(self.grey_image)
        self.left_hint = False

        self.hint_items_data = None
        self.hint_items = None

        self.active_items_data = None
        self.active_items = None

        self.inactive_items_data = None
        self.inactive_items = None

        self.image = self.colored_image
        self.rect = pygame.Rect(self.position[0], self.position[1], self.image.get_rect().width,
                                self.image.get_rect().height)
        self.base_rect = self.rect
        self.base_save = self.get_data()

        self.can_drag = True
        self.is_dragging = False
        self.start_drag_time = 0
        self.drag_delay = 250

        self.update()

    def get_position(self):
        return self.position

    def get_rect(self):
        return self.rect

    def alpha_image(self, image):
        return self.core_service.set_image_transparent(image=image, opacity_disable=self.opacity_disable)

    def update(self):
        if self.show_item:
            if not self.enable:
                self.image = self.alpha_image(self.grey_image)
                self.set_child_visibilty("active_items", False)
                self.set_child_visibilty("inactive_items", True)
            else:
                self.image = self.colored_image
                self.set_child_visibilty("active_items", True)
                self.set_child_visibilty("inactive_items", False)

            if self.hint_show:
                self.image = self.update_hint(self.image)

            current_time = pygame.time.get_ticks()
            if self.is_dragging and (current_time - self.start_drag_time >= self.drag_delay):
                self.rect.center = pygame.mouse.get_pos()
                # self.rect.x = pygame.mouse.get_pos()[0]
                # self.rect.y = pygame.mouse.get_pos()[1]

        else:
            self.image = pygame.Surface((0, 0))
            self.set_child_visibilty("inactive_items", False)

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
                                      o_width=3 * self.core_service.zoom)
        return image

    def left_click(self):
        self.enable = not self.enable
        self.update()

    def right_click(self):
        self.left_click()
        # self.update()

    def wheel_click(self):
        if self.hint is not None:
            if self.hint_show:
                self.hint_show = False
            else:
                self.hint_show = True

            if self.hint_items:
                for sub_item in self.hint_items:
                    if sub_item.show_item:
                        self.close_all_childs_hint_items()
                    else:
                        sub_item.show_item = True
                        sub_item.update()

            self.update()

    def close_all_childs_hint_items(self):
        for sub_item in self.hint_items:
            sub_item.hint_show = False
            sub_item.show_item = False
            sub_item.update()
            if sub_item.hint_items:
                sub_item.close_all_childs_hint_items()

    def set_child_visibilty(self, child_list_name, visible):
        child_lst = getattr(self, child_list_name)
        if child_lst:
            for child in child_lst:
                child.show_item = visible
                child.update()
                sub_child_lst = getattr(child, child_list_name)
                if sub_child_lst and not visible:
                    child.set_child_visibilty(child_list_name, visible)

    def wheel_up(self):
        pass

    def wheel_down(self):
        pass

    def generate_text(self, text, font_name, color, font_size, o_width=2):
        temp_surface = pygame.Surface((400, 400)).convert_alpha()
        tsurf, tpos = ptext.draw(str(text), (0, 0), fontname=font_name, antialias=True,
                                 owidth=o_width, ocolor=(0, 0, 0), color=color, fontsize=font_size, surf=temp_surface)

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
                y = base_image.get_rect().h - tsurf.get_rect().h + (tsurf.get_rect().h / 4)
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

            temp_surface = pygame.Surface(([w, h]), pygame.SRCALPHA, 32)
            temp_surface = temp_surface.convert_alpha()
            temp_surface.blit(image_surface, (pos_x * -1, pos_y))
            temp_surface.blit(tsurf, (x, y))
            self.rect = pygame.Rect(self.position[0] + pos_x, self.position[1], self.image.get_rect().width,
                                    self.image.get_rect().height)
        else:
            temp_surface = pygame.Surface(
                [image_surface.get_rect().w, image_surface.get_rect().h],
                pygame.SRCALPHA, 32)
            temp_surface = temp_surface.convert_alpha()
            temp_surface.blit(image_surface, (0, 0))

        return temp_surface

    def get_data(self):
        data = {
            "id": self.id,
            "name": self.base_name,
            "enable": self.enable,
            "hint_show": self.hint_show,
            "show_item": self.show_item
        }
        return data

    def set_data(self, datas):
        self.enable = datas["enable"]
        self.hint_show = datas["hint_show"]
        self.show_item = datas["show_item"]
        self.update()

    def reset(self):
        self.set_data(self.base_save)

    def check_click(self, pos):
        return self.base_rect.collidepoint(pos)

    def reset_position(self):
        self.rect.x = self.base_position[0]
        self.rect.y = self.base_position[1]

    def get_colored_image(self):
        return self.colored_image
