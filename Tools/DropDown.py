import pygame

from Tools.CoreService import CoreService


class DropDown:
    def __init__(self, color_menu, color_option, text_color, x, y, w, h, font, main, options):
        self.color_menu = color_menu
        self.color_option = color_option
        self.text_color = text_color
        self.rect = pygame.Rect(x, y, w, h)
        self.base_rect = self.rect
        self.font = font
        self.main = main
        self.options = options
        self.draw_menu = False
        self.menu_active = False
        self.active_option = -1
        self.core_service = CoreService()

    def draw(self, surf):
        # pygame.draw.rect(surf, self.color_menu[self.menu_active], self.rect, 0)
        zoom_rect = self.base_rect.copy()
        zoom_rect.x = zoom_rect.x * self.core_service.zoom
        zoom_rect.y = zoom_rect.y * self.core_service.zoom
        zoom_rect.w = zoom_rect.w * self.core_service.zoom
        zoom_rect.h = zoom_rect.h * self.core_service.zoom
        self.rect = zoom_rect

        msg = self.font.render(self.main, 1, self.text_color)
        surf.blit(msg, msg.get_rect(center=self.rect.center))



        if self.draw_menu:
            for i, text in enumerate(self.options):
                rect = self.rect.copy()
                rect.y += (i + 1) * self.rect.height
                pygame.draw.rect(surf, self.color_option, rect, 0)
                msg = self.font.render(text, 1, self.text_color)
                surf.blit(msg, msg.get_rect(center=rect.center))

    def update(self, event_list):
        mpos = pygame.mouse.get_pos()
        self.menu_active = self.rect.collidepoint(mpos)

        self.active_option = -1
        for i in range(len(self.options)):
            rect = self.rect.copy()
            rect.y += (i + 1) * self.rect.height
            if rect.collidepoint(mpos):
                self.active_option = i
                break

        if not self.menu_active and self.active_option == -1:
            self.draw_menu = False

        for event in event_list:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.menu_active:
                    self.draw_menu = not self.draw_menu
                elif self.draw_menu and self.active_option >= 0:
                    self.draw_menu = False
                    return self.active_option
        return -1
