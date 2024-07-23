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
    def __init__(self, dimensions, tracker, is_dev=False):
        self.tracker = tracker
        self.screen = None
        self.core_service = CoreService()
        self.saveTool = SaveLoadTool()
        font = pygame.font.Font(self.core_service.get_menu_font(), 20)
        theme = Theme(background_color=(20, 20, 20, 50),  # transparent background
                      title_font=font,#pygame_menu.font.FONT_NEVIS,
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
        self.sound_check = self.menu.add.toggle_switch('Sound effect', False, onchange=self.onchange_sound)
        self.esc_menu_check = self.menu.add.toggle_switch('ESC Label', True, onchange=self.onchange_esc)
        self.show_hint_menu_check = self.menu.add.toggle_switch('Show Hint', True, onchange=self.onchange_show_hint)
        self.menu.add.button('Back to main menu', self.back_menu)
        self.menu.add.button('Discord', self.open_discord)
        self.menu.add.button('Pay me a coffee ? :)', self.open_paypal)
        self.menu.add.button('Official website', self.open_website)
        if is_dev:
            self.menu.add.button('Take screenshot', self.take_screenshot)
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

    def active(self, screen):
        self.menu.resize(width=screen.get_rect().w, height=screen.get_rect().h)
        self.menu.enable()

    def change_zoom(self, value: Tuple[Any, int], zoom_level: float) -> None:
        selected, index = value
        self.tracker.change_zoom(value=zoom_level)
        self.core_service.save_configuration("defaultZoom", index)

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
        # self.save_file(data)
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

    def load(self):
        # data = self.load_file()
        data = self.saveTool.openFileNameDialog()
        try:
            if data and data[0]["template_name"] == self.tracker.template_name:
                self.tracker.load_data(data)
                self.tracker.update_cpt()
                self.menu.disable()
            else:
                messagebox.showerror('Error', 'This save is for the template {}'.format(data[0]["template_name"]))
        except:
            messagebox.showerror('Error', 'Something wrong with this save')

    def events(self, events):
        if self.menu.is_enabled():
            try:
                self.menu.update(events)
            except AssertionError:
                pass

    def back_menu(self):
        self.tracker.change_zoom(value=1)
        self.tracker.back_main_menu()
        self.menu.disable()

    def take_screenshot(self):
        filename =  os.path.join(self.core_service.get_app_path(), "template_dev", "screenshot.jpg")
        pygame.image.save(self.screen, filename)
        self.menu.disable()

    def set_tracker(self, tracker):
        self.tracker = tracker

    def set_screen(self, screen):
        self.screen = screen

    @staticmethod
    def open_discord():
        webbrowser.open("https://discord.gg/5MQvh7MAGN")

    @staticmethod
    def open_paypal():
        webbrowser.open("https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=3RNQCK64GWBMS&source=url")

    @staticmethod
    def open_website():
        webbrowser.open("https://www.linsotracker.com/")
