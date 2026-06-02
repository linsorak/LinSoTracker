import pygame
from pygame import Rect

from Entities.Item import Item


class EditableBox(Item):
    def __init__(self, id, name, position, size, manager, lines, style, placeholder_text=None, always_enable=False):
        empty_image = pygame.Surface((0, 0), pygame.SRCALPHA)
        Item.__init__(self, id=id, name=name, image=empty_image, position=(0, 0), enable=True,
                      opacity_disable=0.3, hint=None, always_enable=always_enable)
        self.manager = manager
        self.can_drag = False
        self.clicked = False
        self.box_position = position
        self.box_size = size
        self.rect = pygame.Rect(position, size)
        self.base_rect = self.rect
        self.placeholder_text = placeholder_text or ""
        self.lines = lines
        self.text = ""
        self.focused = False
        self.suggestions_visible = False
        self.suggestions = []
        self.selected_suggestion_index = 0
        self.max_visible_suggestions = 5
        self.suggestion_height = max(22, int(size[1]))
        self.suggestion_rect = pygame.Rect(position[0], position[1] + size[1],
                                           size[0], self.suggestion_height * self.max_visible_suggestions)

        self.background_color = self._read_color(style, "BackgroundColor", (255, 255, 255))
        self.normal_text_color = self._read_color(style, "NormalTextColor", (0, 0, 0))
        self.selected_background_color = self._read_color(style, "SelectedBackgroundColor", (40, 110, 190))
        self.selected_text_color = self._read_color(style, "SelectedTextColor", (255, 255, 255))
        self.hovered_background_color = self._read_color(style, "HoveredBackgroundColor", (70, 70, 70))
        self.hovered_text_color = self._read_color(style, "HoveredTextColor", (255, 255, 255))
        self.border_color = (70, 130, 210)
        self.disabled_color = (120, 120, 120)

        try:
            font_data = self.core_service.get_font("editableBoxFont")
            font_path = self.core_service.get_tracker_temp_path()
            import os
            font_name = os.path.join(font_path, font_data["Name"])
            self.font = pygame.font.Font(font_name, int(font_data["Size"] * self.core_service.zoom))
        except Exception:
            self.font = pygame.font.Font(None, max(16, int(size[1] * 0.65)))

        self._cursor_visible = True
        self._cursor_elapsed = 0
        self._last_search_text = None

    @staticmethod
    def _read_color(style, key, default):
        data = style.get(key)
        if not data:
            return default
        return data.get("r", default[0]), data.get("g", default[1]), data.get("b", default[2])

    @staticmethod
    def search_items_by_case_insensitive(text, item_list):
        search_lower = text.lower()
        return [item for item in item_list if item.lower().startswith(search_lower)]

    @staticmethod
    def get_clipboard_text():
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            data = pygame.scrap.get(pygame.SCRAP_TEXT)
            if not data:
                return ""
            if isinstance(data, bytes):
                return data.decode("utf-8", errors="ignore").replace("\x00", "")
            return str(data)
        except Exception:
            return ""

    def _refresh_suggestions(self):
        if self._last_search_text == self.text:
            return
        self._last_search_text = self.text
        if self.text:
            self.suggestions = self.search_items_by_case_insensitive(self.text, self.lines)
        else:
            self.suggestions = list(self.lines)
        self.suggestions_visible = self.focused and bool(self.suggestions)
        if self.suggestions:
            self.selected_suggestion_index = min(self.selected_suggestion_index, len(self.suggestions) - 1)
        else:
            self.selected_suggestion_index = 0

    def _set_text(self, text):
        self.text = text
        self._last_search_text = None
        self.selected_suggestion_index = 0
        self._refresh_suggestions()

    def _suggestion_at_position(self, pos):
        if not self.suggestions_visible or not self.suggestion_rect.collidepoint(pos):
            return None
        index = int((pos[1] - self.suggestion_rect.y) // self.suggestion_height)
        visible = self.suggestions[:self.max_visible_suggestions]
        if 0 <= index < len(visible):
            return visible[index]
        return None

    def handle_event(self, event):
        if not self.enable:
            return

        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and event.button == 1:
            selected_suggestion = self._suggestion_at_position(event.pos)
            if selected_suggestion:
                self._set_text(selected_suggestion)
                self.suggestions_visible = False
                self.focused = False
                self.selected_suggestion_index = 0
            elif self.rect.collidepoint(event.pos):
                self.focused = True
                self._refresh_suggestions()
            else:
                self.focused = False
                self.suggestions_visible = False

        elif event.type == pygame.KEYDOWN and self.focused:
            if event.key == pygame.K_ESCAPE:
                self.focused = False
                self.suggestions_visible = False
            elif event.key == pygame.K_RETURN:
                if self.suggestions_visible and self.suggestions:
                    self._set_text(self.suggestions[self.selected_suggestion_index])
                self.suggestions_visible = False
                self.focused = False
            elif event.key == pygame.K_DOWN:
                self._refresh_suggestions()
                if self.suggestions:
                    self.suggestions_visible = True
                    self.selected_suggestion_index = (self.selected_suggestion_index + 1) % len(self.suggestions)
            elif event.key == pygame.K_UP:
                self._refresh_suggestions()
                if self.suggestions:
                    self.suggestions_visible = True
                    self.selected_suggestion_index = (self.selected_suggestion_index - 1) % len(self.suggestions)
            elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                self._set_text(self.text[:-1])
            elif event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
                self._set_text(self.text + self.get_clipboard_text().strip())
            elif event.unicode and event.unicode.isprintable():
                self._set_text(self.text + event.unicode)

    def update_box(self, dt):
        if not self.focused:
            return
        self._cursor_elapsed += dt
        if self._cursor_elapsed >= 0.5:
            self._cursor_elapsed = 0
            self._cursor_visible = not self._cursor_visible

    def draw_box(self, screen):
        if not self.show_item:
            return

        bg = self.background_color if self.enable else self.disabled_color
        pygame.draw.rect(screen, bg, self.rect)
        pygame.draw.rect(screen, self.border_color if self.focused else (30, 30, 30), self.rect, 2)

        draw_text = self.text if self.text else self.placeholder_text
        text_color = self.normal_text_color if self.text else (120, 120, 120)
        visible_text = draw_text
        max_width = self.rect.width - 16
        while visible_text and self.font.size(visible_text)[0] > max_width:
            visible_text = visible_text[1:]
        text_surface = self.font.render(visible_text, True, text_color)
        screen.blit(text_surface, (self.rect.x + 8, self.rect.centery - text_surface.get_height() // 2))

        if self.focused and self._cursor_visible:
            cursor_x = self.rect.x + 8 + text_surface.get_width() + 1
            pygame.draw.line(screen, self.normal_text_color, (cursor_x, self.rect.y + 7),
                             (cursor_x, self.rect.bottom - 7), 1)

        if self.suggestions_visible:
            visible_suggestions = self.suggestions[:self.max_visible_suggestions]
            self.suggestion_rect.height = self.suggestion_height * len(visible_suggestions)
            pygame.draw.rect(screen, self.background_color, self.suggestion_rect)
            pygame.draw.rect(screen, (30, 30, 30), self.suggestion_rect, 2)

            mouse_pos = pygame.mouse.get_pos()
            for index, suggestion in enumerate(visible_suggestions):
                line_rect = pygame.Rect(self.suggestion_rect.x,
                                        self.suggestion_rect.y + index * self.suggestion_height,
                                        self.suggestion_rect.width,
                                        self.suggestion_height)
                selected = index == self.selected_suggestion_index
                hovered = line_rect.collidepoint(mouse_pos)
                if selected or hovered:
                    pygame.draw.rect(screen, self.hovered_background_color, line_rect)
                color = self.hovered_text_color if selected or hovered else self.normal_text_color
                suggestion_surface = self.font.render(suggestion, True, color)
                screen.blit(suggestion_surface, (line_rect.x + 8,
                                                 line_rect.centery - suggestion_surface.get_height() // 2))

    def check_click(self, mouse_position):
        if self.suggestions_visible:
            test = Rect(self.rect[0], self.rect[1],
                        max(self.rect.width, self.suggestion_rect.width),
                        self.rect.height + self.suggestion_rect.height)
            return test.collidepoint(mouse_position)
        return self.rect.collidepoint(mouse_position)

    def left_click(self):
        self.clicked = True
        self.focused = True
        self._refresh_suggestions()

    def disable_click(self):
        self.enable = False
        self.focused = False
        self.suggestions_visible = False

    def enable_click(self):
        self.enable = True

    def get_data(self):
        data = Item.get_data(self)
        data["text"] = getattr(self, "text", "")
        return data

    def set_data(self, datas):
        self._set_text(datas.get("text", ""))
        Item.set_data(self, datas)
