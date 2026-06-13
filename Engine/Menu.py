import json
import os
import webbrowser
from tkinter import messagebox
from typing import Tuple, Any

import pygame

from Tools.CoreService import CoreService
from Tools.SaveLoadTool import SaveLoadTool


class EscMenuView:
    def __init__(self, owner, width, height):
        self.owner = owner
        self.width = width
        self.height = height
        self.enabled = False

    def resize(self, width=None, height=None, w=None, h=None):
        self.width = width if width is not None else w if w is not None else self.width
        self.height = height if height is not None else h if h is not None else self.height

    def enable(self):
        self.enabled = True
        self.owner.selected_index = None
        self.owner.menu_scroll = 0

    def disable(self):
        self.enabled = False

    def is_enabled(self):
        return self.enabled

    def mainloop(self, screen):
        self.owner.draw_menu(screen)


class Menu:
    def __init__(self, dimensions, tracker):
        self.tracker = tracker
        self.core_service = CoreService()
        self.saveTool = SaveLoadTool()
        self.font_path = self.core_service.get_ui_font()
        font = pygame.font.Font(self.font_path, 20)
        self.title_font = pygame.font.Font(self.font_path, 30)
        self.section_font = pygame.font.Font(self.font_path, 16)
        self.widget_font = pygame.font.Font(self.font_path, 19)
        self.small_font = pygame.font.Font(self.font_path, 14)
        self.seed_overlay_open = False
        self.seed_text = ""
        self.seed_error = None
        self.seed_input_rect = None
        self.seed_import_rect = None
        self.seed_cancel_rect = None
        self.seed_overlay_consumed_click = False
        self.seed_font = font
        self.seed_title_font = pygame.font.Font(self.font_path, 26)
        self.font_sizes = {
            id(font): 20,
            id(self.title_font): 30,
            id(self.section_font): 16,
            id(self.widget_font): 19,
            id(self.small_font): 14,
            id(self.seed_title_font): 26,
        }
        self.font_cache = {}
        self.syncing_timer_check = False
        self.menu = EscMenuView(self, dimensions[0], dimensions[1])
        self.selected_index = None
        self.hover_index = None
        self.item_rects = []
        self.selector_hitboxes = {}
        self.menu_scroll = 0
        self.menu_max_scroll = 0
        self.menu_scrollbar_track = None
        self.menu_scrollbar_thumb = None
        self.dragging_menu_scrollbar = False
        self.menu_scrollbar_drag_offset = 0
        self.consume_escape_keyup = False
        self.close_rect = None
        self.zoom_options = [
            ("x0.75", 0.75, 7),
            ("x0.85", 0.85, 6),
            ("x0.9", 0.9, 5),
            ("x1", 1, 0),
            ("x1.25", 1.25, 1),
            ("x1.5", 1.5, 2),
            ("x1.75", 1.75, 3),
            ("x2", 2, 4),
        ]
        self.zoom_index = 0
        self.sound_value = False
        self.esc_label_value = True
        self.show_hint_value = True
        self.show_timer_value = True
        self.gomode_glow_clockwise_value = True
        self.items = [
            {"type": "section", "label": "Tracker"},
            {"type": "selector", "label": "Zoom", "change": self.change_zoom_by_step},
            {"type": "button", "label": "Save tracker state", "action": self.save},
            {"type": "button", "label": "Save as default", "action": self.save_default},
            {"type": "button", "label": "Load tracker state", "action": self.load},
            {"type": "button", "label": "Load default save", "action": self.load_default},
            {"type": "button", "label": "Import settings", "action": self.add_seed},
            {"type": "section", "label": "Preferences"},
            {"type": "toggle", "label": "Sound effects", "getter": lambda: self.sound_value, "setter": self.onchange_sound},
            {"type": "toggle", "label": "ESC label", "getter": lambda: self.esc_label_value, "setter": self.onchange_esc},
            {"type": "toggle", "label": "Show hints", "getter": lambda: self.show_hint_value, "setter": self.onchange_show_hint},
            {"type": "toggle", "label": "Show timer", "getter": lambda: self.show_timer_value, "setter": self.onchange_show_timer},
            {
                "type": "toggle",
                "label": "Go Mode glow clockwise",
                "getter": lambda: self.gomode_glow_clockwise_value,
                "setter": self.onchange_gomode_glow_clockwise
            },
            {"type": "section", "label": "Navigation"},
            {"type": "button", "label": "Back to main menu", "action": self.back_menu, "danger": True},
            {"type": "button", "label": "Discord", "action": self.open_discord},
            {"type": "button", "label": "Pay me a coffee", "action": self.open_paypal},
            {"type": "button", "label": "Official website", "action": self.open_website},
            {"type": "button", "label": "Close menu", "action": self.menu.disable},
        ]

    def onchange_sound(self, current_state_value, **kwargs):
        self.sound_value = current_state_value
        self.core_service.save_configuration("soundWhenItemActive", current_state_value)
        self.core_service.sound_active = current_state_value

    def onchange_esc(self, current_state_value, **kwargs):
        self.esc_label_value = current_state_value
        self.core_service.save_configuration("showESCLabel", current_state_value)
        self.core_service.draw_esc_menu_label = current_state_value

    def onchange_show_hint(self, current_state_value, **kwargs):
        self.show_hint_value = current_state_value
        self.core_service.save_configuration("showHint", current_state_value)
        self.core_service.show_hint_on_item = current_state_value

    def onchange_show_timer(self, current_state_value, **kwargs):
        if self.syncing_timer_check:
            return
        self.show_timer_value = current_state_value
        self.core_service.show_timer = current_state_value
        self.core_service.save_configuration("showTimer", current_state_value)
        self.tracker.set_timer_visible(current_state_value)

    def onchange_gomode_glow_clockwise(self, current_state_value, **kwargs):
        self.gomode_glow_clockwise_value = current_state_value
        self.core_service.go_mode_glow_clockwise = current_state_value
        self.core_service.save_configuration("goModeGlowClockwise", current_state_value)

    def set_zoom_index(self, zoom_index):
        config_index = int(zoom_index)
        self.zoom_index = next(
            (index for index, option in enumerate(self.zoom_options) if option[2] == config_index),
            3
        )
        self.change_zoom(
            (self.zoom_options[self.zoom_index], self.zoom_options[self.zoom_index][2]),
            self.zoom_options[self.zoom_index][1]
        )

    def set_sound_check(self, value):
        self.sound_value = value

    def set_esc_check(self, value):
        self.esc_label_value = value

    def set_show_hint_check(self, value):
        self.show_hint_value = value

    def set_show_timer_check(self, value):
        self.syncing_timer_check = True
        try:
            self.show_timer_value = value
        finally:
            self.syncing_timer_check = False

    def set_gomode_glow_clockwise_check(self, value):
        self.gomode_glow_clockwise_value = value

    def active(self, screen):
        self.menu.resize(width=screen.get_rect().w, height=screen.get_rect().h)
        self.menu_scroll = 0
        self.menu.enable()

    def change_zoom(self, value: Tuple[Any, int], zoom_level: float) -> None:
        selected, config_index = value
        self.zoom_index = next(
            (index for index, option in enumerate(self.zoom_options) if option[2] == config_index),
            self.zoom_index
        )
        main_menu = self.tracker.main_menu
        tracker_ready = hasattr(self.tracker, "is_moving")
        progress_callback = main_menu.draw_loading_screen if tracker_ready else getattr(self.tracker,
                                                                                        "progress_callback", None)
        if progress_callback:
            main_menu.draw_loading_screen(0, "Changing zoom")
        self.tracker.change_zoom(value=zoom_level, progress_callback=progress_callback)
        self.core_service.save_configuration("defaultZoom", config_index)
        main_menu.loading_active = False
        screen = pygame.display.get_surface()
        if tracker_ready and screen:
            self.tracker.draw(screen, 0)
            pygame.display.update()

    def change_zoom_by_step(self, step):
        next_index = max(0, min(self.zoom_index + step, len(self.zoom_options) - 1))
        if next_index == self.zoom_index:
            return
        self.zoom_index = next_index
        option = self.zoom_options[self.zoom_index]
        self.change_zoom((option, option[2]), option[1])

    def resize(self, w, h):
        self.menu.resize(w, h)

    def enable(self):
        self.menu.enable()
        self.menu_scroll = 0

    def disable(self):
        self.menu.disable()

    def get_menu(self):
        return self.menu

    def save(self):
        data = self.tracker.save_data()
        self.saveTool.saveFileDialog(data)
        self.menu.disable()

    def save_default(self):
        save_directory = os.path.join(self.core_service.get_app_path(), "default_saves")
        self.core_service.create_directory(save_directory)
        if os.path.exists(save_directory):
            save_name = os.path.join(save_directory, self.tracker.template_name + ".trackersave")

            if os.path.exists(save_name):
                os.remove(save_name)

            data = self.tracker.save_data()
            json_data_dump = json.dumps(data, indent=4).encode('utf-8')
            encrypted = self.saveTool.fernet.encrypt(json_data_dump)
            with open(save_name, 'wb') as f:
                f.write(encrypted)
                f.close()

        self.menu.disable()

    def load_default(self):
        self.tracker.check_is_default_save()
        self.menu.disable()

    def add_seed(self):
        self.menu.disable()
        self.seed_overlay_open = True
        self.seed_text = ""
        self.seed_error = None

    def is_seed_overlay_open(self):
        return self.seed_overlay_open

    def consume_seed_overlay_click(self):
        if self.seed_overlay_consumed_click:
            self.seed_overlay_consumed_click = False
            return True
        return False

    def close_seed_overlay(self):
        self.seed_overlay_open = False
        self.seed_error = None

    def apply_seed_text(self):
        seed = self.seed_text.strip()
        if not seed:
            self.seed_error = "Paste a settings string first."
            return

        self.tracker.seed = seed
        if not hasattr(self.tracker, 'apply_seed'):
            self.seed_error = "This tracker cannot import settings."
            return

        try:
            if self.tracker.apply_seed(seed):
                self.close_seed_overlay()
            else:
                self.seed_error = "Import failed."
        except Exception as e:
            self.seed_error = "Failed to apply seed: {}".format(e)

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

    def handle_seed_overlay_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close_seed_overlay()
            elif event.key == pygame.K_RETURN:
                self.apply_seed_text()
            elif event.key == pygame.K_BACKSPACE:
                self.seed_text = self.seed_text[:-1]
                self.seed_error = None
            elif event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
                self.seed_text += self.get_clipboard_text().strip()
                self.seed_error = None
            elif event.unicode and event.unicode.isprintable():
                self.seed_text += event.unicode
                self.seed_error = None

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.seed_overlay_consumed_click = True
            if self.seed_import_rect and self.seed_import_rect.collidepoint(event.pos):
                self.apply_seed_text()
            elif self.seed_cancel_rect and self.seed_cancel_rect.collidepoint(event.pos):
                self.close_seed_overlay()

    def draw_seed_overlay_button(self, screen, rect, label, color):
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (235, 235, 235), rect, 2)
        text = self.seed_font.render(label, True, (255, 255, 255))
        screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))

    def draw_seed_overlay(self, screen):
        if not self.seed_overlay_open:
            return

        width, height = screen.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        screen.blit(overlay, (0, 0))

        popup_w = min(720, max(460, int(width * 0.70)))
        popup_h = 230
        popup_x = (width - popup_w) // 2
        popup_y = (height - popup_h) // 2
        popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)

        pygame.draw.rect(screen, (22, 22, 28), popup_rect)
        pygame.draw.rect(screen, (235, 235, 235), popup_rect, 2)

        title = self.seed_title_font.render("Import settings", True, (255, 255, 255))
        screen.blit(title, (popup_x + 24, popup_y + 22))

        label = self.seed_font.render("Paste a settings string:", True, (230, 230, 230))
        screen.blit(label, (popup_x + 24, popup_y + 70))

        self.seed_input_rect = pygame.Rect(popup_x + 24, popup_y + 102, popup_w - 48, 38)
        pygame.draw.rect(screen, (245, 245, 245), self.seed_input_rect)
        pygame.draw.rect(screen, (70, 130, 210), self.seed_input_rect, 2)

        visible_text = self.seed_text
        max_text_width = self.seed_input_rect.width - 20
        while visible_text and self.seed_font.size(visible_text)[0] > max_text_width:
            visible_text = visible_text[1:]
        text_surface = self.seed_font.render(visible_text, True, (20, 20, 20))
        screen.blit(text_surface, (self.seed_input_rect.x + 10, self.seed_input_rect.y + 9))

        cursor_x = self.seed_input_rect.x + 10 + text_surface.get_width() + 1
        pygame.draw.line(screen, (20, 20, 20), (cursor_x, self.seed_input_rect.y + 8),
                         (cursor_x, self.seed_input_rect.y + self.seed_input_rect.height - 8), 1)

        if self.seed_error:
            error = self.seed_font.render(self.seed_error, True, (255, 120, 120))
            screen.blit(error, (popup_x + 24, popup_y + 150))

        button_w = 120
        button_h = 38
        buttons_y = popup_y + popup_h - button_h - 22
        self.seed_cancel_rect = pygame.Rect(popup_x + popup_w - 24 - button_w, buttons_y, button_w, button_h)
        self.seed_import_rect = pygame.Rect(self.seed_cancel_rect.x - button_w - 12, buttons_y, button_w, button_h)
        self.draw_seed_overlay_button(screen, self.seed_import_rect, "Import", (4, 100, 180))
        self.draw_seed_overlay_button(screen, self.seed_cancel_rect, "Cancel", (80, 80, 90))

    def selectable_indexes(self):
        return [index for index, item in enumerate(self.items) if item["type"] != "section"]

    def move_selection(self, step):
        selectable = self.selectable_indexes()
        if not selectable:
            return
        if self.selected_index not in selectable:
            self.selected_index = selectable[0] if step >= 0 else selectable[-1]
            return
        current = selectable.index(self.selected_index)
        self.selected_index = selectable[(current + step) % len(selectable)]

    def activate_selected(self):
        if not self.items or self.selected_index is None:
            return
        self.activate_item(self.items[self.selected_index], 1)

    def activate_item(self, item, direction=1):
        item_type = item["type"]
        if item_type == "button":
            item["action"]()
        elif item_type == "toggle":
            item["setter"](not item["getter"]())
        elif item_type == "selector":
            item["change"](direction)

    def handle_menu_event(self, event):
        if self.consume_escape_keyup and event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:
            self.consume_escape_keyup = False
            return True
        if not self.menu.is_enabled():
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.consume_escape_keyup = True
                self.menu.disable()
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.move_selection(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.move_selection(1)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                if self.selected_index is not None:
                    self.activate_item(self.items[self.selected_index], -1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                if self.selected_index is not None:
                    self.activate_item(self.items[self.selected_index], 1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.activate_selected()
            return True

        if event.type == pygame.MOUSEMOTION:
            if self.dragging_menu_scrollbar:
                self.update_menu_scrollbar_drag(event.pos)
                return True
            self.hover_index = None
            for index, rect in self.item_rects:
                if rect.collidepoint(event.pos):
                    self.hover_index = index
                    break
            return True

        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL):
            if event.type == pygame.MOUSEWHEEL:
                if self.menu_max_scroll > 0:
                    self.scroll_menu(-event.y * 36)
                    return True
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.menu_scrollbar_thumb and self.menu_scrollbar_thumb.collidepoint(event.pos):
                    self.dragging_menu_scrollbar = True
                    self.menu_scrollbar_drag_offset = event.pos[1] - self.menu_scrollbar_thumb.y
                    return True
                if self.menu_scrollbar_track and self.menu_scrollbar_track.collidepoint(event.pos):
                    self.dragging_menu_scrollbar = True
                    self.menu_scrollbar_drag_offset = self.menu_scrollbar_thumb.h // 2 if self.menu_scrollbar_thumb else 0
                    self.update_menu_scrollbar_drag(event.pos)
                    return True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.dragging_menu_scrollbar:
                    self.dragging_menu_scrollbar = False
                    return True
                if self.close_rect and self.close_rect.collidepoint(event.pos):
                    self.menu.disable()
                    return True
                for index, rect in self.item_rects:
                    if rect.collidepoint(event.pos) and self.items[index]["type"] != "section":
                        self.selected_index = index
                        item = self.items[index]
                        direction = 1
                        if item["type"] == "selector":
                            hitboxes = self.selector_hitboxes.get(index, {})
                            if hitboxes.get("minus") and hitboxes["minus"].collidepoint(event.pos):
                                direction = -1
                            elif hitboxes.get("value") and hitboxes["value"].collidepoint(event.pos):
                                direction = -1 if event.pos[0] < hitboxes["value"].centerx else 1
                            elif event.pos[0] < rect.centerx:
                                direction = -1
                        self.activate_item(item, direction)
                        return True
            elif event.type == pygame.MOUSEBUTTONUP and event.button in (4, 5):
                if self.menu_max_scroll > 0:
                    self.scroll_menu(-36 if event.button == 4 else 36)
                else:
                    self.move_selection(-1 if event.button == 4 else 1)
            return True

        return True

    def scroll_menu(self, amount):
        self.menu_scroll = max(0, min(self.menu_scroll + amount, self.menu_max_scroll))

    def update_menu_scrollbar_drag(self, mouse_position):
        if not self.menu_scrollbar_track or not self.menu_scrollbar_thumb:
            return
        track = self.menu_scrollbar_track
        denom = max(1, track.h - self.menu_scrollbar_thumb.h)
        thumb_y = mouse_position[1] - track.y - self.menu_scrollbar_drag_offset
        fraction = max(0.0, min(1.0, thumb_y / denom))
        self.menu_scroll = int(fraction * self.menu_max_scroll)

    def draw_menu(self, screen):
        width, height = screen.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        screen.blit(overlay, (0, 0))

        fullscreen = width < 640 or height < 520
        if fullscreen:
            panel_w = width
            panel_h = height
            panel_x = 0
            panel_y = 0
            panel_radius = 0
            panel_padding = 15
            close_top = 12
        else:
            panel_w = min(820, max(360, width - 40))
            panel_h = min(height - 30, 560)
            panel_x = (width - panel_w) // 2
            panel_y = max(15, (height - panel_h) // 2)
            panel_radius = 8
            panel_padding = 28
            close_top = 18
        panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        self._draw_rect(screen, (16, 20, 28), panel, border_radius=panel_radius)
        self._draw_rect(screen, (50, 91, 132), panel, 1, border_radius=panel_radius)

        self.close_rect = pygame.Rect(panel.right - panel_padding - 32, panel.y + close_top, 32, 32)
        self._draw_rect(screen, (42, 47, 58), self.close_rect, border_radius=4)
        self._draw_centered_text(screen, "X", self.close_rect, self.widget_font, (235, 238, 242))

        header_x = panel.x + panel_padding
        screen.blit(self._render_text("PAUSE MENU", self.section_font, (164, 188, 212)), (header_x, panel.y + 20))
        title = self._render_text("Options", self.title_font, (245, 247, 250))
        screen.blit(title, (header_x, panel.y + 40))
        hint_text = "Esc closes - arrows navigate - Enter selects"
        hint = self._render_text(hint_text, self.small_font, (165, 170, 180))
        max_hint_w = self.close_rect.x - header_x - 10 if fullscreen else panel.right - panel_padding - header_x
        while hint_text and hint.get_width() > max_hint_w:
            hint_text = hint_text[:-1]
            suffix = "..."
            shown = hint_text[:-len(suffix)] + suffix if len(hint_text) > len(suffix) else hint_text
            hint = self._render_text(shown, self.small_font, (165, 170, 180))
        screen.blit(hint, (header_x, panel.y + 74))
        pygame.draw.line(screen, (58, 65, 78), (header_x, panel.y + 98), (panel.right - panel_padding, panel.y + 98), 1)

        self.item_rects = []
        self.selector_hitboxes = {}
        self.menu_scrollbar_track = None
        self.menu_scrollbar_thumb = None
        row_h = 31
        gap = 4
        content_x = panel.x + panel_padding
        content_w = panel.w - panel_padding * 2
        if fullscreen:
            content_w -= 14
        if content_w >= 560 and not fullscreen:
            columns = [
                list(range(0, 7)),
                list(range(7, len(self.items))),
            ]
        else:
            columns = [list(range(len(self.items)))]
        col_gap = 18
        col_w = (content_w - (col_gap * (len(columns) - 1))) // len(columns)
        start_y = panel.y + 110
        content_rect = pygame.Rect(content_x, start_y, content_w, panel.bottom - 20 - start_y)
        column_heights = [self.measure_menu_column_height(indexes, row_h, gap) for indexes in columns]
        content_height = max(column_heights) if column_heights else 0
        self.menu_max_scroll = max(0, content_height - content_rect.h)
        self.menu_scroll = max(0, min(self.menu_scroll, self.menu_max_scroll))

        previous_clip = screen.get_clip()
        screen.set_clip(content_rect)
        for col_index, indexes in enumerate(columns):
            x = content_x + col_index * (col_w + col_gap)
            y = start_y - self.menu_scroll
            for index in indexes:
                item = self.items[index]
                if item["type"] == "section":
                    if y > start_y:
                        y += 3
                    if y + 24 >= content_rect.y and y <= content_rect.bottom:
                        label = self._render_text(item["label"].upper(), self.section_font, (164, 188, 212))
                        screen.blit(label, (x, y + 5))
                    y += 24
                    continue

                rect = pygame.Rect(x, y, col_w, row_h)
                if rect.bottom < content_rect.y or rect.y > content_rect.bottom:
                    y += row_h + gap
                    continue
                self.item_rects.append((index, rect))
                selected = index == self.selected_index
                hovered = index == self.hover_index
                bg = (36, 45, 58) if selected else (27, 33, 44) if hovered else (20, 25, 34)
                border = (238, 190, 86) if selected else (79, 101, 124) if hovered else (50, 61, 76)
                border_width = 2 if selected else 1
                self._draw_rect(screen, bg, rect, border_radius=5)
                self._draw_rect(screen, border, rect, border_width, border_radius=5)

                text_color = (250, 248, 240) if selected else (220, 225, 232)
                right_space = 160 if item["type"] in ("selector", "toggle") else 120 if item.get("danger") else 18
                self._draw_fitted_text(screen, item["label"], self.widget_font, text_color,
                                       rect.x + 14, rect, rect.w - right_space)

                if item["type"] == "selector":
                    value = self.zoom_options[self.zoom_index][0]
                    control_rect = pygame.Rect(rect.right - 132, rect.y + 4, 112, rect.h - 8)
                    minus_rect = pygame.Rect(control_rect.x, control_rect.y, 28, control_rect.h)
                    value_rect = pygame.Rect(minus_rect.right + 4, control_rect.y, 48, control_rect.h)
                    plus_rect = pygame.Rect(value_rect.right + 4, control_rect.y, 28, control_rect.h)
                    self.selector_hitboxes[index] = {
                        "minus": minus_rect,
                        "value": value_rect,
                        "plus": plus_rect,
                    }
                    self._draw_step_button(screen, minus_rect, "-", self.zoom_index > 0, selected)
                    self._draw_pill(screen, value_rect, value, (31, 78, 120), text_color)
                    self._draw_step_button(screen, plus_rect, "+", self.zoom_index < len(self.zoom_options) - 1, selected)
                elif item["type"] == "toggle":
                    self._draw_toggle(screen, rect, item["getter"]())
                elif item.get("danger") and rect.w > 300:
                    note = self._render_text("Leaves tracker", self.small_font, (236, 142, 142))
                    screen.blit(note, note.get_rect(midright=(rect.right - 14, rect.centery)))

                y += row_h + gap
        screen.set_clip(previous_clip)

        if self.menu_max_scroll > 0:
            self.draw_menu_scrollbar(screen, content_rect, content_height)

    def measure_menu_column_height(self, indexes, row_h, gap):
        height = 0
        first = True
        for index in indexes:
            item = self.items[index]
            if item["type"] == "section":
                if not first:
                    height += 3
                height += 24
            else:
                height += row_h + gap
            first = False
        return max(0, height - gap)

    def draw_menu_scrollbar(self, screen, content_rect, content_height):
        track_x = min(content_rect.right + 8, screen.get_width() - 12)
        track = pygame.Rect(track_x, content_rect.y, 8, content_rect.h)
        self.menu_scrollbar_track = track
        self._draw_rect(screen, (26, 31, 42), track, border_radius=4)
        thumb_h = max(28, int(track.h * content_rect.h / max(content_height, 1)))
        thumb_y = track.y + int((track.h - thumb_h) * self.menu_scroll / max(self.menu_max_scroll, 1))
        thumb = pygame.Rect(track.x, thumb_y, track.w, thumb_h)
        self.menu_scrollbar_thumb = thumb
        self._draw_rect(screen, (238, 190, 86), thumb, border_radius=4)

    def _draw_toggle(self, screen, row_rect, enabled):
        toggle_rect = pygame.Rect(row_rect.right - 80, row_rect.y + 6, 52, row_rect.h - 12)
        track_color = (46, 136, 92) if enabled else (74, 79, 91)
        knob_color = (245, 247, 250)
        self._draw_rect(screen, track_color, toggle_rect, border_radius=toggle_rect.h // 2)
        knob_size = toggle_rect.h - 6
        knob_x = toggle_rect.right - knob_size - 3 if enabled else toggle_rect.x + 3
        knob_rect = pygame.Rect(knob_x, toggle_rect.y + 3, knob_size, knob_size)
        self._draw_rect(screen, knob_color, knob_rect, border_radius=knob_size // 2)
        label = "ON" if enabled else "OFF"
        label_color = (126, 235, 177) if enabled else (190, 194, 202)
        text = self._render_text(label, self.small_font, label_color)
        screen.blit(text, text.get_rect(midright=(toggle_rect.x - 12, row_rect.centery)))

    def _draw_pill(self, screen, rect, label, color, text_color):
        self._draw_rect(screen, color, rect, border_radius=rect.h // 2)
        self._draw_centered_text(screen, label, rect, self.small_font, text_color)

    def _draw_step_button(self, screen, rect, label, enabled, selected):
        bg = (42, 64, 86) if enabled else (35, 40, 49)
        border = (238, 190, 86) if selected and enabled else None
        color = (245, 247, 250) if enabled else (120, 126, 136)
        self._draw_rect(screen, bg, rect, border_radius=4)
        if border:
            self._draw_rect(screen, border, rect, 1, border_radius=4)
        self._draw_centered_text(screen, label, rect, self.widget_font, color)

    def _render_text(self, label, font, color):
        size = self.font_sizes.get(id(font))
        if not size:
            return font.render(str(label), True, color)
        key = size * 2
        if key not in self.font_cache:
            self.font_cache[key] = pygame.font.Font(self.font_path, key)
        hi = self.font_cache[key].render(str(label), True, color)
        return pygame.transform.smoothscale(
            hi,
            (max(1, hi.get_width() // 2), max(1, hi.get_height() // 2))
        )

    @staticmethod
    def _draw_rect(screen, color, rect, width=0, border_radius=0):
        if border_radius <= 0:
            pygame.draw.rect(screen, color, rect, width)
            return
        scale = 2
        surf = pygame.Surface((rect.w * scale, rect.h * scale), pygame.SRCALPHA)
        scaled_rect = surf.get_rect()
        pygame.draw.rect(surf, color, scaled_rect, width * scale, border_radius=border_radius * scale)
        screen.blit(pygame.transform.smoothscale(surf, rect.size), rect.topleft)

    def _draw_centered_text(self, screen, label, rect, font, color):
        text = self._render_text(label, font, color)
        screen.blit(text, text.get_rect(center=rect.center))

    def _draw_fitted_text(self, screen, label, font, color, x, rect, max_width):
        text = label
        while text and font.size(text)[0] > max_width:
            text = text[:-1]
        if text != label and len(text) > 3:
            text = text[:-3] + "..."
        surface = self._render_text(text, font, color)
        screen.blit(surface, surface.get_rect(midleft=(x, rect.centery)))

    def load(self):
        data = self.saveTool.openFileNameDialog()
        if not data:
            return
        try:
            if not isinstance(data, list) or not data or not isinstance(data[0], dict):
                messagebox.showerror('Error', 'Something wrong with this save')
                return
            template_name = data[0].get("template_name")
            if template_name == self.tracker.template_name:
                self.tracker.load_data(data)
                self.tracker.update_cpt()
                self.menu.disable()
            else:
                messagebox.showerror('Error', 'This save is for the template {}'.format(template_name))
        except Exception:
            messagebox.showerror('Error', 'Something wrong with this save')

    def events(self, events):
        if self.seed_overlay_open:
            self.handle_seed_overlay_event(events)
            return True

        if self.handle_menu_event(events):
            return True
        return False

    def back_menu(self):
        tracker = self.tracker
        main_menu = tracker.main_menu

        self.menu.disable()
        main_menu.draw_loading_screen(0, "Back to main menu")
        tracker.change_zoom(value=1, progress_callback=main_menu.draw_loading_screen)
        main_menu.draw_loading_screen(0.70, "Closing tracker")
        tracker.back_main_menu()
        main_menu.draw_loading_screen(0.90, "Loading main menu")
        tracker.bank.unloadImages()
        screen = pygame.display.get_surface()
        if screen:
            main_menu.loading_active = False
            main_menu.draw_home(screen)
            pygame.display.update()

    def set_tracker(self, tracker):
        self.tracker = tracker

    @staticmethod
    def open_discord():
        webbrowser.open("https://discord.gg/5MQvh7MAGN")

    @staticmethod
    def open_paypal():
        webbrowser.open("https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=3RNQCK64GWBMS&source=url")

    @staticmethod
    def open_website():
        webbrowser.open("https://www.linsotracker.com/")
