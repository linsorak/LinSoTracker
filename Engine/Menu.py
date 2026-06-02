import json
import os
import webbrowser
from tkinter import messagebox
from typing import Tuple, Any

import pygame
import pygame_menu
from pygame_menu import Theme

from Tools.CoreService import CoreService
from Tools.SaveLoadTool import SaveLoadTool


class Menu:
    def __init__(self, dimensions, tracker):
        self.tracker = tracker
        self.core_service = CoreService()
        self.saveTool = SaveLoadTool()
        font = pygame.font.Font(self.core_service.get_menu_font(), 20)
        self.seed_overlay_open = False
        self.seed_text = ""
        self.seed_error = None
        self.seed_input_rect = None
        self.seed_import_rect = None
        self.seed_cancel_rect = None
        self.seed_overlay_consumed_click = False
        self.seed_font = font
        self.seed_title_font = pygame.font.Font(self.core_service.get_menu_font(), 26)
        self.syncing_timer_check = False
        theme = Theme(background_color=(20, 20, 20, 50),  # transparent background
                      title_font=font,  # pygame_menu.font.FONT_NEVIS,
                      title_font_color=(255, 255, 255),
                      title_background_color=(4, 47, 126),
                      title_bar_style=pygame_menu.widgets.MENUBAR_STYLE_UNDERLINE,
                      title_font_size=25,
                      widget_font=font,
                      widget_font_size=20)

        self.menu = pygame_menu.Menu('Options', dimensions[0], dimensions[1], theme=theme)
        self.zoom_selector = self.menu.add.selector('Zoom :', [('x1', 1),
                                                               ('x1.25', 1.25),
                                                               ('x1.5', 1.5),
                                                               ('x1.75', 1.75),
                                                               ('x2', 2),
                                                               ('x0.9', 0.9),
                                                               ('x0.85', 0.85),
                                                               ('x0.75', 0.75),
                                                               ], onchange=self.change_zoom)

        self.menu.add.button('Save tracker state', self.save)
        self.menu.add.button('Save as default', self.save_default)
        self.menu.add.button('Load tracker state', self.load)
        self.menu.add.button('Load default save', self.load_default)
        self.menu.add.button('Import settings from...', self.add_seed)
        self.sound_check = self.menu.add.toggle_switch('Sound effect', False, onchange=self.onchange_sound)
        self.esc_menu_check = self.menu.add.toggle_switch('ESC Label', True, onchange=self.onchange_esc)
        self.show_hint_menu_check = self.menu.add.toggle_switch('Show Hint', True, onchange=self.onchange_show_hint)
        self.show_timer_menu_check = self.menu.add.toggle_switch('Show Timer', True, onchange=self.onchange_show_timer)
        self.menu.add.button('Back to main menu', self.back_menu)
        self.menu.add.button('Discord', self.open_discord)
        self.menu.add.button('Pay me a coffee ? :)', self.open_paypal)
        self.menu.add.button('Official website', self.open_website)
        self.menu.add.button('Close menu', self.menu.disable)
        self.menu.disable()

    def onchange_sound(self, current_state_value, **kwargs):
        self.core_service.save_configuration("soundWhenItemActive", current_state_value)
        self.core_service.sound_active = current_state_value

    def onchange_esc(self, current_state_value, **kwargs):
        self.core_service.save_configuration("showESCLabel", current_state_value)
        self.core_service.draw_esc_menu_label = current_state_value

    def onchange_show_hint(self, current_state_value, **kwargs):
        self.core_service.save_configuration("showHint", current_state_value)
        self.core_service.show_hint_on_item = current_state_value

    def onchange_show_timer(self, current_state_value, **kwargs):
        if self.syncing_timer_check:
            return
        self.tracker.set_timer_visible(current_state_value)

    def set_zoom_index(self, zoom_index):
        self.zoom_selector.set_value(zoom_index)
        value, index = self.zoom_selector.get_value()
        self.change_zoom(self.zoom_selector.get_value(), value[1])

    def set_sound_check(self, value):
        self.sound_check.set_value(value)

    def set_esc_check(self, value):
        self.esc_menu_check.set_value(value)

    def set_show_hint_check(self, value):
        self.show_hint_menu_check.set_value(value)

    def set_show_timer_check(self, value):
        self.syncing_timer_check = True
        try:
            self.show_timer_menu_check.set_value(value)
        finally:
            self.syncing_timer_check = False

    def active(self, screen):
        self.menu.resize(width=screen.get_rect().w, height=screen.get_rect().h)
        self.menu.enable()

    def change_zoom(self, value: Tuple[Any, int], zoom_level: float) -> None:
        selected, index = value
        main_menu = self.tracker.main_menu
        tracker_ready = hasattr(self.tracker, "is_moving")
        progress_callback = main_menu.draw_loading_screen if tracker_ready else getattr(self.tracker,
                                                                                        "progress_callback", None)
        if progress_callback:
            main_menu.draw_loading_screen(0, "Changing zoom")
        self.tracker.change_zoom(value=zoom_level, progress_callback=progress_callback)
        self.core_service.save_configuration("defaultZoom", index)
        main_menu.loading_active = False
        screen = pygame.display.get_surface()
        if tracker_ready and screen:
            self.tracker.draw(screen, 0)
            pygame.display.update()

    def resize(self, w, h):
        self.menu.resize(w, h)

    def enable(self):
        self.menu.enable()

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
            return

        if self.menu.is_enabled():
            try:
                self.menu.update(events)
            except AssertionError:
                pass

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
