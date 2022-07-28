import json
import webbrowser
from tkinter import filedialog
from typing import Tuple, Any

import pygame_menu
from pygame_menu import Theme

from Tools.PyQtSaveLoadTool import PyQtSaveLoadTool


class Menu():
    def __init__(self, dimensions, tracker):
        self.tracker = tracker
        theme = Theme(background_color=(0, 0, 0, 50),  # transparent background
                      title_font=pygame_menu.font.FONT_NEVIS,
                      title_background_color=(4, 47, 126),
                      title_bar_style=pygame_menu.widgets.MENUBAR_STYLE_UNDERLINE,
                      title_font_size=25,
                      widget_font=pygame_menu.font.FONT_NEVIS,
                      widget_font_size=20)

        self.menu = pygame_menu.Menu('Options', dimensions[0], dimensions[1], theme=theme)
        self.menu.add.selector('Zoom :', [('x1', 1),
                                          ('x1.25', 1.25),
                                          ('x1.5', 1.5),
                                          ('x1.75', 1.75),
                                          ('x2', 2),
                                          ('x0.9', 0.9),
                                          ('x0.85', 0.85),
                                          ('x0.75', 0.75)], onchange=self.change_zoom)
        self.menu.add.button('Save tracker state', self.save)
        self.menu.add.button('Load tracker state', self.load)
        self.menu.add.button('Back to main menu', self.back_menu)
        self.menu.add.button('Discord', self.open_discord)
        self.menu.add.button('Pay me a coffee ? :)', self.open_paypal)
        self.menu.add.button('Official website', self.open_website)
        self.menu.add.button('Close menu', self.menu.disable)
        self.saveTool = PyQtSaveLoadTool()
        self.menu.disable()

    def active(self, screen):
        self.menu.resize(width=screen.get_rect().w, height=screen.get_rect().h)
        self.menu.enable()

    def change_zoom(self, value: Tuple[Any, int], zoom_level: float) -> None:
        selected, index = value
        self.tracker.change_zoom(value=zoom_level)

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

    def load(self):
        # data = self.load_file()
        data = self.saveTool.openFileNameDialog()
        if data:
            self.tracker.load_data(data)
            self.menu.disable()

    def save_file(self, data):
        file = filedialog.asksaveasfile(mode='w',
                                        title="LinSoTracker loading save",
                                        defaultextension=".trackersave",
                                        filetypes=[("LinSoTracker Save", ".trackersave")])
        if file:
            json.dump(data, file, ensure_ascii=False, indent=4)
            file.close()

    def load_file(self):
        file = filedialog.askopenfilename(title="LinSoTracker loading save",
                                          defaultextension=".trackersave",
                                          filetypes=[("LinSoTracker Save", ".trackersave")])

        if file:
            f = open(file)
            return json.load(f)
        else:
            return None

    def events(self, events):
        if self.menu.is_enabled():
            # print(self.menu.update(events))
            # self.menu.update(events)
            pass

    def back_menu(self):
        self.tracker.back_main_menu()
        self.menu.disable()

    def set_tracker(self, tracker):
        self.tracker = tracker

    @staticmethod
    def open_discord():
        webbrowser.open("https://discord.gg/5MQvh7MAGN")

    @staticmethod
    def open_paypal():
        webbrowser.open("https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=3RNQCK64GWBMS&source=url")    \

    @staticmethod
    def open_website():
        webbrowser.open("http://www.linsotracker.com/")
