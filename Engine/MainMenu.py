import glob
import io
import json
import math
import os
import shutil
from tkinter import messagebox
from zipfile import ZipFile

import pygame
from pygame.rect import Rect

from Engine.FadeAnimation import FadeAnimation, FadeMode
from Engine.Menu import Menu
from Engine.TemplateMaker import TemplateMaker
from Engine.Tracker import Tracker
from Tools import ptext
from Tools.Bank import Bank
from Tools.CoreService import CoreService
from Tools.TemplateChecker import TemplateChecker


class MainMenu:
    def __init__(self):
        self.selected_indev = None
        self.selected_official = None
        self.content_indev = None
        self.icon_indev = None
        self.x_offset = -60
        self.y_offset = 60
        self.space_offset = 10
        self.max_row = 3
        self.max_column = 5
        # Vertical scrolling of the templates grid (replaces pagination).
        self.scroll_offset = 0
        self.scroll_max = 0
        self.scroll_step = 94
        self.official_template = None
        self.new_version = None
        self.menu_content = []
        self.menu_a = None
        self.draw_templates = 0
        self.font_data = None
        self.selected_error = None
        self.selected = None
        self.selected_update = None
        self.selected_position = None
        self.content_error = None
        self.content = None
        self.content_update = None
        self.content_official = None
        self.icon = None
        self.icon_update = None
        self.icon_official = None
        self.background_image = None
        self.description_menu = None
        self.menu_json_data = None
        self.resources_path = None
        self.selected_menu_index = None
        self.fade_engine = FadeAnimation(fadeStart=0, fadeEnd=255, fadeStep=45, mode=FadeMode.FADE)
        self.illustration = None
        self.moved_tracker = None
        self.fade_value = self.fade_engine.getFadeValue()
        self.core_service = CoreService()
        self.show_donation_popup = self.core_service.register_app_launch()
        self.donation_paypal_rect = None
        self.donation_close_rect = None
        self.loading_active = False
        self.loading_progress = 0
        self.loading_label = ""
        self.template_maker = None
        self.template_maker_button = None
        # --- template filtering (search bar + game combo) ---
        self.search_text = ""
        self.search_active = False
        self.search_rect = None
        self.combo_rect = None
        self.combo_open = False
        self.combo_selected = None  # None => all games, else a game id
        self.games = []            # games.json content
        self.combo_games = []      # games that actually have matching templates
        self.game_icons = {}       # game id -> scaled icon surface
        self.combo_option_rects = []
        self.display_list = []
        self.bank = Bank()
        app_path = self.core_service.get_app_path()
        if self.core_service.dev_version:
            # Dev: read/write next to the sources
            self.template_directory = os.path.join(app_path, "templates")
            self.dev_template_directory = os.path.join(app_path, "devtemplates")
        else:
            # Packaged: the app folder can be read-only (macOS App Translocation,
            # mounted .dmg, /Applications without write rights). Use a writable
            # location and seed it from the bundled templates on first launch.
            base = self.core_service.temp_path_fixe
            self.template_directory = os.path.join(base, "templates")
            self.dev_template_directory = os.path.join(base, "devtemplates")
            self._seed_bundled_templates(os.path.join(app_path, "templates"), self.template_directory)
            self._seed_bundled_templates(os.path.join(app_path, "devtemplates"), self.dev_template_directory)
        self.template_list = []
        self.core_service.sync_tracker_data()
        self.extract_data()
        self.init_menu()
        self.load_games()
        self.set_check()
        self.process_templates_list()
        self.download_missing_officials_templates()
        self.loaded_tracker = None
        self.btn_paypal = None
        self.btn_discord = None
        self.init_btns()

    @staticmethod
    def _seed_bundled_templates(bundled_dir, writable_dir):
        """Copy templates shipped inside the (possibly read-only) app bundle into a
        writable directory. Per-template so new official templates are added on
        update without clobbering the user's own saved/edited templates."""
        try:
            os.makedirs(writable_dir, exist_ok=True)
            if not os.path.isdir(bundled_dir):
                return
            for name in os.listdir(bundled_dir):
                src = os.path.join(bundled_dir, name)
                dst = os.path.join(writable_dir, name)
                if os.path.isdir(src) and not os.path.exists(dst):
                    shutil.copytree(src, dst)
                elif os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copyfile(src, dst)
        except Exception:
            pass

    def init_btns(self):
        dimensions = self.get_dimension()
        btn_paypal_w = 200
        btn_paypal_h = 100
        self.btn_paypal = Rect(0, dimensions[1] - btn_paypal_h, btn_paypal_w, btn_paypal_h)
        btn_discord_w = 120
        btn_discord_h = 100
        self.btn_discord = Rect(dimensions[0] - btn_discord_w, dimensions[1] - btn_discord_h, btn_discord_w,
                                btn_discord_h)

    def extract_data(self):
        filename = os.path.join(self.core_service.get_app_path(), "tracker.data")
        self.resources_path = os.path.join(self.core_service.get_temp_path(), "tracker")
        self.core_service.create_directory(self.resources_path)

        if os.path.isfile(filename):
            with ZipFile(filename, 'r') as zip:
                zip.extractall(self.resources_path)

    def init_menu(self):
        filename = os.path.join(self.resources_path, "home.json")
        if os.path.isfile(filename):
            with open(filename, 'r') as file:
                self.menu_json_data = json.load(file)

    def load_games(self):
        """Load the games list (games.json bundled in tracker.data)."""
        self.games = []
        filename = os.path.join(self.resources_path, "games.json")
        if os.path.isfile(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                self.games = data.get("games", []) if isinstance(data, dict) else data
            except Exception:
                self.games = []

    def _match_game(self, template, game):
        """Template belongs to a game by explicit filename or by name match."""
        if template["filename"] in game.get("templates", []):
            return True
        name = template["information"]["Informations"].get("Name", "").lower()
        game_name = game.get("name", "").lower()
        return bool(game_name) and game_name in name

    def template_in_game(self, template, game):
        if game.get("id") == "divers":
            if template["filename"] in game.get("templates", []):
                return True
            # catch-all: matched by no other game
            return not any(g.get("id") != "divers" and self._match_game(template, g)
                           for g in self.games)
        return self._match_game(template, game)

    def set_check(self):
        self.new_version = self.core_service.get_new_version()
        self.official_template = self.core_service.get_official_template()

    def initialization(self):
        self.background_image = self.menu_json_data[0]["BackgroundImage"]
        self.background_image = self.bank.addImage(os.path.join(self.resources_path, self.background_image))
        self.icon = self.menu_json_data[0]["Icon"]
        self.icon = self.bank.addImage(os.path.join(self.resources_path, self.icon))
        self.icon_update = self.menu_json_data[0]["UpdateIcon"]
        self.icon_update = self.bank.addImage(os.path.join(self.resources_path, self.icon_update))
        self.icon_official = self.menu_json_data[0]["OfficialIcon"]
        self.icon_official = self.bank.addImage(os.path.join(self.resources_path, self.icon_official))
        self.icon_indev = self.menu_json_data[0]["InDevIcon"]
        self.icon_indev = self.bank.addImage(os.path.join(self.resources_path, self.icon_indev))
        self.content = self.menu_json_data[0]["BoxTrackerContentImage"]
        self.content = self.bank.addImage(os.path.join(self.resources_path, self.content))
        self.content_error = self.menu_json_data[0]["BoxTrackerContentImageNotCompatible"]
        self.content_error = self.bank.addImage(os.path.join(self.resources_path, self.content_error))
        self.content_update = self.menu_json_data[0]["BoxTrackerContentImageUpdate"]
        self.content_update = self.bank.addImage(os.path.join(self.resources_path, self.content_update))
        self.content_official = self.menu_json_data[0]["BoxTrackerContentImageOfficial"]
        self.content_official = self.bank.addImage(os.path.join(self.resources_path, self.content_official))
        self.content_indev = self.menu_json_data[0]["BoxTrackerContentImageInDev"]
        self.content_indev = self.bank.addImage(os.path.join(self.resources_path, self.content_indev))
        self.selected = self.bank.addImage(os.path.join(self.resources_path, "glow.png"))
        self.selected_error = self.bank.addImage(os.path.join(self.resources_path, "glow-error.png"))
        self.selected_update = self.bank.addImage(os.path.join(self.resources_path, "glow-update.png"))
        self.selected_official = self.bank.addImage(os.path.join(self.resources_path, "glow-official.png"))
        self.selected_indev = self.bank.addImage(os.path.join(self.resources_path, "glow-indev.png"))
        self.description_menu = self.bank.addImage(
            os.path.join(self.resources_path, self.menu_json_data[0]["DescriptionBox"]))

        self.game_icons = {}
        for game in self.games:
            icon_rel = game.get("icon")
            if not icon_rel:
                continue
            icon_path = os.path.join(self.resources_path, icon_rel)
            if os.path.isfile(icon_path):
                try:
                    self.game_icons[game["id"]] = pygame.transform.smoothscale(
                        self.bank.addImage(icon_path), (24, 24))
                except Exception:
                    pass

        session_font = self.menu_json_data[0]["HomeMenuFont"]
        self.core_service.set_menu_font(os.path.join(self.resources_path, session_font["Name"]))
        session_font_color = session_font["Colors"]
        self.font_data = {
            "path": self.core_service.get_menu_font(),
            "size": session_font["Size"],
            "description_size": session_font["DescriptionSize"],
            "page_size": session_font["PageSize"],
            "title_size": session_font["TitleSize"],
            "color_normal": (
                session_font_color["Normal"]["r"], session_font_color["Normal"]["g"],
                session_font_color["Normal"]["b"]),
            "color_error": (
                session_font_color["Error"]["r"], session_font_color["Error"]["g"], session_font_color["Error"]["b"]),
            "color_update": (
                session_font_color["Update"]["r"], session_font_color["Update"]["g"],
                session_font_color["Update"]["b"]),
            "color_official": (
                session_font_color["Official"]["r"], session_font_color["Official"]["g"],
                session_font_color["Official"]["b"])
        }

    def get_dimension(self):
        dimension = self.menu_json_data[0]["Dimensions"]
        return dimension["width"], dimension["height"]

    def open_template_maker(self):
        surface = pygame.display.get_surface()
        self.previous_window_size = surface.get_size() if surface else self.get_dimension()
        try:
            desktop_w, desktop_h = pygame.display.get_desktop_sizes()[0]
        except (AttributeError, IndexError):
            info = pygame.display.Info()
            desktop_w, desktop_h = info.current_w, info.current_h
        width = min(1600, max(1280, desktop_w - 80))
        height = min(900, max(720, desktop_h - 120))
        pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.core_service.setgamewindowcenter(width, height)
        self.template_maker = TemplateMaker(self)
        self.moved_tracker = None
        self.illustration = None

    def close_template_maker(self):
        self.template_maker = None
        width, height = getattr(self, "previous_window_size", self.get_dimension())
        pygame.display.set_mode((width, height))
        self.core_service.setgamewindowcenter(width, height)

    def get_icon(self):
        return self.icon

    def draw(self, screen, time_delta):
        if self.template_maker:
            self.template_maker.draw(screen, time_delta)
        elif not self.loaded_tracker:
            self.draw_home(screen)
        else:
            self.loaded_tracker.draw(screen, time_delta)
        if self.loading_active:
            self.draw_loading_overlay(screen, self.loading_progress, self.loading_label)
        if self.show_donation_popup:
            self.draw_donation_popup(screen)

    def draw_donation_popup(self, screen):
        width, height = screen.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        screen.blit(overlay, (0, 0))

        popup_w = min(520, max(360, int(width * 0.58)))
        popup_h = 210
        popup_x = (width - popup_w) // 2
        popup_y = (height - popup_h) // 2
        popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)

        pygame.draw.rect(screen, (22, 22, 28), popup_rect)
        pygame.draw.rect(screen, (235, 235, 235), popup_rect, 2)

        temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32).convert_alpha()
        title, _ = self.draw_text(
            text="Support LinSoTracker",
            font_name=self.font_data["path"],
            color=self.font_data["color_normal"],
            font_size=self.font_data["title_size"] * 0.75,
            surface=temp_surface,
            position=(0, 0),
            outline=1)
        body_lines = [
            "If LinSoTracker helps you,",
            "you can support the project with a small donation."
        ]
        screen.blit(title, (popup_x + (popup_w - title.get_width()) // 2, popup_y + 22))

        y = popup_y + 75
        for line in body_lines:
            text_surface, _ = self.draw_text(
                text=line,
                font_name=self.font_data["path"],
                color=self.font_data["color_normal"],
                font_size=self.font_data["size"],
                surface=temp_surface,
                position=(0, 0),
                outline=1)
            screen.blit(text_surface, (popup_x + (popup_w - text_surface.get_width()) // 2, y))
            y += text_surface.get_height() + 4

        button_w = 150
        button_h = 38
        gap = 16
        buttons_y = popup_y + popup_h - button_h - 22
        self.donation_paypal_rect = pygame.Rect(
            popup_x + (popup_w // 2) - button_w - (gap // 2), buttons_y, button_w, button_h)
        self.donation_close_rect = pygame.Rect(
            popup_x + (popup_w // 2) + (gap // 2), buttons_y, button_w, button_h)

        self.draw_donation_button(screen, self.donation_paypal_rect, "PayPal", (56, 150, 110))
        self.draw_donation_button(screen, self.donation_close_rect, "Close", (70, 70, 80))

    def draw_donation_button(self, screen, rect, label, color):
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (235, 235, 235), rect, 2)
        temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32).convert_alpha()
        text_surface, _ = self.draw_text(
            text=label,
            font_name=self.font_data["path"],
            color=self.font_data["color_normal"],
            font_size=self.font_data["size"],
            surface=temp_surface,
            position=(0, 0),
            outline=1)
        screen.blit(text_surface, (
            rect.x + (rect.w - text_surface.get_width()) // 2,
            rect.y + (rect.h - text_surface.get_height()) // 2
        ))

    def donation_popup_click(self, mouse_position, button):
        if not self.show_donation_popup:
            return False
        if button != 1:
            return True
        if self.donation_paypal_rect and self.donation_paypal_rect.collidepoint(mouse_position):
            Menu.open_paypal()
            self.show_donation_popup = False
            return True
        if self.donation_close_rect and self.donation_close_rect.collidepoint(mouse_position):
            self.show_donation_popup = False
            return True
        return True

    def get_grid_layout(self):
        """Geometry of the scrollable templates grid."""
        content_rect = self.content.get_rect()
        col_step = content_rect.w + self.space_offset
        row_step = content_rect.h + self.space_offset
        grid_left = content_rect.w * 2 + self.x_offset
        grid_top = content_rect.h * 2 + self.y_offset
        grid_width = content_rect.w * self.max_column + self.space_offset * (self.max_column - 1)
        viewport_bottom = self.get_dimension()[1] - 120
        viewport_h = max(row_step, viewport_bottom - grid_top)
        return content_rect, col_step, row_step, grid_left, grid_top, grid_width, viewport_h

    def draw_home(self, screen):
        screen.blit(self.background_image, (0, 0))

        content_rect, col_step, row_step, grid_left, grid_top, grid_width, viewport_h = self.get_grid_layout()
        total_rows = math.ceil(len(self.display_list) / self.max_column) if self.display_list else 0
        total_height = total_rows * row_step
        self.scroll_max = max(0, total_height - viewport_h)
        self.scroll_offset = max(0, min(self.scroll_offset, self.scroll_max))

        self.menu_content = []
        previous_clip = screen.get_clip()
        screen.set_clip(Rect(grid_left, grid_top, grid_width, viewport_h))

        for index, current_template in enumerate(self.display_list):
            col = index % self.max_column
            row = index // self.max_column
            content_x = grid_left + col * col_step
            content_y = grid_top + row * row_step - self.scroll_offset
            if content_y + content_rect.h < grid_top or content_y > grid_top + viewport_h:
                continue
            icon_x, icon_y = content_x + 10, content_y + 5
            outdated, valid = "outdated" in current_template and current_template["outdated"], \
                current_template["valid"]

            if valid:
                if outdated:
                    content_image = self.content_update
                else:
                    if "official" in current_template:
                        content_image = self.content_official
                    elif "is_dev_template" in current_template:
                        content_image = self.content_indev
                    else:
                        content_image = self.content
            else:
                content_image = self.content_error

            screen.blit(content_image, (content_x, content_y))
            screen.blit(current_template["icon"], (icon_x, icon_y))

            if outdated:
                screen.blit(self.icon_update, (content_x, content_y))

            if "official" in current_template and not outdated:
                screen.blit(self.icon_official, (content_x, content_y))

            elif "is_dev_template" in current_template and not outdated:
                screen.blit(self.icon_indev, (content_x, content_y))

            self.menu_content.append({"positions": (content_x, content_y),
                                      "dimensions": (content_rect.w, content_rect.h),
                                      "template": current_template,
                                      "index": index})

        screen.set_clip(previous_clip)
        self.draw_scrollbar(screen, grid_left, grid_top, grid_width, viewport_h, total_height)

        # Re-resolve hover against the current scroll position each frame.
        self.update_hover(pygame.mouse.get_pos())

        pos_dev_y = self.draw_info_text(screen)

        if self.moved_tracker:
            self.draw_fade_effect(screen, pos_dev_y)

        self.draw_template_maker_button(screen)
        self.draw_filters(screen)
        self.draw_combo_dropdown(screen)

    def draw_scrollbar(self, screen, grid_left, grid_top, grid_width, viewport_h, total_height):
        if self.scroll_max <= 0:
            return
        track_x = grid_left + grid_width + 4
        track = pygame.Surface((6, viewport_h), pygame.SRCALPHA)
        pygame.draw.rect(track, (255, 255, 255, 35), track.get_rect(), border_radius=3)
        screen.blit(track, (track_x, grid_top))
        thumb_h = max(30, int(viewport_h * viewport_h / total_height))
        thumb_y = grid_top + int((self.scroll_offset / self.scroll_max) * (viewport_h - thumb_h))
        thumb = pygame.Surface((6, thumb_h), pygame.SRCALPHA)
        pygame.draw.rect(thumb, (230, 230, 230, 180), thumb.get_rect(), border_radius=3)
        screen.blit(thumb, (track_x, thumb_y))

    def draw_template_maker_button(self, screen):
        button_w = 180
        button_h = 36
        x = screen.get_width() - button_w - 16
        y = 16
        self.template_maker_button = Rect(x, y, button_w, button_h)
        button_surface = pygame.Surface((button_w, button_h), pygame.SRCALPHA)
        pygame.draw.rect(button_surface, (140, 140, 140, 90), button_surface.get_rect(), border_radius=5)
        pygame.draw.rect(button_surface, (210, 210, 210, 120), button_surface.get_rect(), 1, border_radius=5)
        screen.blit(button_surface, (x, y))
        temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32).convert_alpha()
        label, _ = self.draw_text(
            text="Template Maker",
            font_name=self.font_data["path"],
            color=self.font_data["color_normal"],
            font_size=self.font_data["size"],
            surface=temp_surface,
            position=(0, 0),
            outline=1)
        screen.blit(label, (
            x + (button_w - label.get_width()) // 2,
            y + (button_h - label.get_height()) // 2
        ))

    def get_filter_rects(self):
        """Search bar + combo rects, stacked just above the templates grid."""
        content_rect = self.content.get_rect()
        grid_left = (content_rect.w * 2) + self.x_offset
        grid_top = (content_rect.h * 2) + self.y_offset
        width = content_rect.w * self.max_column + self.space_offset * (self.max_column - 1)
        bar_h = 34
        combo_y = grid_top - bar_h - 14
        search_y = combo_y - bar_h - 8
        search_rect = Rect(grid_left, search_y, width, bar_h)
        combo_rect = Rect(grid_left, combo_y, width, bar_h)
        return search_rect, combo_rect

    def _draw_bar(self, screen, rect, active):
        surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        bg = (150, 150, 150, 130) if active else (130, 130, 130, 90)
        pygame.draw.rect(surf, bg, surf.get_rect(), border_radius=6)
        border = (255, 255, 255, 170) if active else (210, 210, 210, 120)
        pygame.draw.rect(surf, border, surf.get_rect(), 1, border_radius=6)
        screen.blit(surf, (rect.x, rect.y))

    def _draw_label(self, screen, text, x, y_center, color, size):
        temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32).convert_alpha()
        surf, _ = self.draw_text(
            text=text,
            font_name=self.font_data["path"],
            color=color,
            font_size=size,
            surface=temp_surface,
            position=(0, 0),
            outline=1)
        screen.blit(surf, (x, y_center - surf.get_height() // 2))
        return surf

    def draw_filters(self, screen):
        search_rect, combo_rect = self.get_filter_rects()
        self.search_rect = search_rect
        self.combo_rect = combo_rect

        # Search bar
        self._draw_bar(screen, search_rect, self.search_active)
        if self.search_text:
            search_label = self.search_text + ("|" if self.search_active else "")
            search_color = self.font_data["color_normal"]
        else:
            search_label = "Search a template..." + ("|" if self.search_active else "")
            search_color = (170, 170, 170)
        self._draw_label(screen, search_label, search_rect.x + 12, search_rect.centery,
                         search_color, self.font_data["size"])

        # Combo bar
        self._draw_bar(screen, combo_rect, self.combo_open)
        selected_game = self._game_by_id(self.combo_selected)
        text_x = combo_rect.x + 12
        if selected_game:
            icon = self.game_icons.get(selected_game.get("id"))
            if icon:
                screen.blit(icon, (combo_rect.x + 10, combo_rect.centery - 12))
                text_x = combo_rect.x + 10 + 24 + 8
            combo_label = selected_game.get("name", "")
        else:
            combo_label = "All games"
        self._draw_label(screen, combo_label, text_x, combo_rect.centery,
                         self.font_data["color_normal"], self.font_data["size"])
        ax = combo_rect.right - 22
        ay = combo_rect.centery
        if self.combo_open:
            points = [(ax - 6, ay + 3), (ax + 6, ay + 3), (ax, ay - 4)]
        else:
            points = [(ax - 6, ay - 3), (ax + 6, ay - 3), (ax, ay + 4)]
        pygame.draw.polygon(screen, (230, 230, 230), points)

    def _game_by_id(self, game_id):
        return next((g for g in self.combo_games if g.get("id") == game_id), None)

    def is_over_filters(self, mouse_position):
        """True when the cursor is over the search bar, combo, or open dropdown."""
        search_rect, combo_rect = self.get_filter_rects()
        if search_rect.collidepoint(mouse_position) or combo_rect.collidepoint(mouse_position):
            return True
        if self.combo_open:
            row_h = 30
            option_count = len(self.combo_games) + 1
            panel = Rect(combo_rect.x, combo_rect.bottom + 3, combo_rect.w, row_h * option_count)
            if panel.collidepoint(mouse_position):
                return True
        return False

    def draw_combo_dropdown(self, screen):
        self.combo_option_rects = []
        if not self.combo_open:
            return
        _, combo_rect = self.get_filter_rects()
        row_h = 30
        options = [("All games", None, None)] + [
            (game.get("name", ""), game.get("id"), self.game_icons.get(game.get("id")))
            for game in self.combo_games]
        y = combo_rect.bottom + 3
        panel = pygame.Surface((combo_rect.w, row_h * len(options)), pygame.SRCALPHA)
        pygame.draw.rect(panel, (28, 28, 34, 240), panel.get_rect(), border_radius=6)
        pygame.draw.rect(panel, (210, 210, 210, 140), panel.get_rect(), 1, border_radius=6)
        screen.blit(panel, (combo_rect.x, y))
        mouse_position = pygame.mouse.get_pos()
        for label, value, icon in options:
            row_rect = Rect(combo_rect.x, y, combo_rect.w, row_h)
            hovered = row_rect.collidepoint(mouse_position)
            if value == self.combo_selected:
                color = (90, 140, 110, 190) if hovered else (90, 140, 110, 160)
            elif hovered:
                color = (255, 255, 255, 55)
            else:
                color = None
            if color:
                highlight = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
                pygame.draw.rect(highlight, color, highlight.get_rect())
                screen.blit(highlight, (row_rect.x, row_rect.y))
            text_x = row_rect.x + 12
            if icon:
                screen.blit(icon, (row_rect.x + 8, row_rect.centery - 12))
                text_x = row_rect.x + 8 + 24 + 8
            self._draw_label(screen, label, text_x, row_rect.centery,
                             self.font_data["color_normal"], self.font_data["size"] * 0.9)
            self.combo_option_rects.append((row_rect, value))
            y += row_h

    def draw_loading_screen(self, progress, label):
        screen = pygame.display.get_surface()
        if not screen:
            return

        self.loading_active = True
        self.loading_progress = progress
        self.loading_label = label

        width, height = screen.get_size()
        screen.fill((10, 10, 14))
        self.draw_loading_overlay(screen, progress, label)

        pygame.display.update()
        pygame.event.pump()

    def draw_loading_overlay(self, screen, progress, label):
        width, height = screen.get_size()

        bar_w = max(240, min(520, int(width * 0.58)))
        bar_h = 24
        bar_x = (width - bar_w) // 2
        bar_y = (height - bar_h) // 2
        progress = max(0, min(1, progress))
        fill_w = int(bar_w * progress)

        temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32).convert_alpha()
        title, _ = self.draw_text(
            text=label,
            font_name=self.font_data["path"],
            color=self.font_data["color_normal"],
            font_size=self.font_data["size"] + 4,
            surface=temp_surface,
            position=(0, 0),
            outline=1)
        percent, _ = self.draw_text(
            text=f"{int(progress * 100)}%",
            font_name=self.font_data["path"],
            color=self.font_data["color_normal"],
            font_size=self.font_data["size"],
            surface=temp_surface,
            position=(0, 0),
            outline=1)

        title_x = (width - title.get_rect().w) // 2
        title_y = max(16, bar_y - title.get_rect().h - 18)
        percent_x = (width - percent.get_rect().w) // 2
        percent_y = bar_y + bar_h + 10

        pygame.draw.rect(screen, (22, 22, 28), (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(screen, (230, 230, 230), (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), 2)
        if fill_w:
            pygame.draw.rect(screen, (72, 180, 132), (bar_x, bar_y, fill_w, bar_h))
        screen.blit(title, (title_x, title_y))
        screen.blit(percent, (percent_x, percent_y))

    def draw_info_text(self, screen):
        surf_title, pos_title = self.draw_text(
            text="{} v{} - Developed by LinSoraK#7235".format(self.core_service.app_name,
                                                              self.core_service.version),
            font_name=self.font_data["path"],
            color=self.font_data["color_normal"],
            font_size=self.font_data["size"],
            surface=screen,
            position=(5, 5),
            outline=1)

        pos_dev_y = surf_title.get_rect().h + 5
        if self.new_version:
            surf_update, pos_update = self.draw_text(
                text="The version {} is now available. Please update!".format(self.new_version),
                font_name=self.font_data["path"],
                color=self.font_data["color_update"],
                font_size=self.font_data["size"],
                surface=screen,
                position=(5, pos_dev_y),
                outline=1)

            pos_dev_y = pos_dev_y + surf_update.get_rect().h + 5

        if self.core_service.dev_version:
            if self.new_version:
                surf_dev, pos_dev = self.draw_text(
                    text="DEVELOPER VERSION - DO NOT USE WITHOUT AUTHORIZATION",
                    font_name=self.font_data["path"],
                    color=self.font_data["color_official"],
                    font_size=self.font_data["size"] - 2,
                    surface=screen,
                    position=(5, pos_dev_y),
                    outline=1)

        return pos_dev_y

    def draw_fade_effect(self, screen, pos_dev_y):
        if self.selected_menu_index is None or self.selected_menu_index >= len(self.display_list):
            return
        template_valid = self.display_list[self.selected_menu_index]["valid"]
        self.fade_engine.update()
        self.fade_value = self.fade_engine.getFadeValue()
        transparent_illustration = self.illustration.copy()
        transparent_illustration.fill((255, 255, 255, self.fade_value),
                                      special_flags=pygame.BLEND_RGBA_MULT)
        if template_valid:
            glow = self.selected.copy()
            if "official" in self.display_list[self.selected_menu_index]:
                glow = self.selected_official.copy()

            if "is_dev_template" in self.display_list[self.selected_menu_index]:
                glow = self.selected_indev.copy()
        else:
            glow = self.selected_error.copy()

        if "outdated" in self.display_list[self.selected_menu_index] and self.display_list[self.selected_menu_index][
            "outdated"]:
            glow = self.selected_update.copy()

        glow_position_x, glow_position_y = self.selected_position
        glow_position_x = glow_position_x - 38
        glow_position_y = glow_position_y - 15
        glow.fill((255, 255, 255, self.fade_value), special_flags=pygame.BLEND_RGBA_MULT)

        description_menu = self.description_menu.copy()
        description_menu.fill((255, 255, 255, self.fade_value),
                              special_flags=pygame.BLEND_RGBA_MULT)

        x_description_menu = screen.get_rect().w - description_menu.get_rect().w
        y_description_menu = 410

        screen.blit(transparent_illustration, (0, 0))
        screen.blit(glow, (glow_position_x, glow_position_y))
        screen.blit(description_menu, (x_description_menu, y_description_menu))

        x_title = x_description_menu + 17
        y_title = y_description_menu + 13

        self.draw_text(
            text=self.display_list[self.selected_menu_index]["information"]["Informations"]["Name"],
            font_name=self.font_data["path"],
            color=self.font_data["color_normal"],
            font_size=self.font_data["title_size"],
            surface=screen,
            position=(x_title, y_title),
            outline=1)

        x_creator = x_title + 15
        y_creator = y_title + 55
        self.draw_text(
            text="Creator : {}".format(
                self.display_list[self.selected_menu_index]["information"]["Informations"]["Creator"]),
            font_name=self.font_data["path"],
            color=self.font_data["color_normal"],
            font_size=self.font_data["description_size"],
            surface=screen,
            position=(x_creator, y_creator),
            outline=1.5)

        x_version = x_creator
        y_version = y_creator + 22
        self.draw_text(
            text="Version : {}".format(
                self.display_list[self.selected_menu_index]["information"]["Informations"]["Version"]),
            font_name=self.font_data["path"],
            color=self.font_data["color_normal"],
            font_size=self.font_data["description_size"],
            surface=screen,
            position=(x_version, y_version),
            outline=1.5)

        if "official" in self.display_list[self.selected_menu_index]:
            x_official = x_description_menu + description_menu.get_rect().w - 90
            y_official = y_description_menu + description_menu.get_rect().h - 35
            self.draw_text(
                text="OFFICIAL",
                font_name=self.font_data["path"],
                color=self.font_data["color_official"],
                font_size=self.font_data["size"],
                surface=screen,
                position=(x_official, y_official),
                outline=1.5)

        if not self.display_list[self.selected_menu_index]["valid"]:
            x_not_valid = x_description_menu + 17
            y_not_valid = y_description_menu + description_menu.get_rect().h - 35
            self.draw_text(
                text="NOT VALID - PLEASE UPDATE",
                font_name=self.font_data["path"],
                color=self.font_data["color_error"],
                font_size=self.font_data["size"],
                surface=screen,
                position=(x_not_valid, y_not_valid),
                outline=1.5)

        if "Comments" in self.display_list[self.selected_menu_index]:
            x_comments = x_creator
            y_comments = y_version + 22
            self.draw_text(
                text="Comments : {}".format(
                    self.display_list[self.selected_menu_index]["information"]["Informations"]["Comments"]),
                font_name=self.font_data["path"],
                color=self.font_data["color_normal"],
                font_size=self.font_data["description_size"] * 0.85,
                surface=screen,
                position=(x_comments, y_comments),
                outline=1.5)

        if "Credits" in self.display_list[self.selected_menu_index]:
            x_credits = x_creator

            if "Comments" in self.display_list[self.selected_menu_index]:
                y_credits = y_comments + 22
            else:
                y_credits = y_version + 22

            self.draw_text(
                text="Credits : {}".format(
                    self.display_list[self.selected_menu_index]["information"]["Informations"]["Credits"]),
                font_name=self.font_data["path"],
                color=self.font_data["color_normal"],
                font_size=self.font_data["description_size"] * 0.85,
                surface=screen,
                position=(x_credits, y_credits),
                outline=1.5)

    def download_missing_officials_templates(self):
        if self.official_template:
            for template in self.official_template:
                template_path = os.path.join(self.template_directory, f"{template.get('template_name')}.template")
                if not os.path.exists(template_path):
                    MsgBox = messagebox.askquestion('New template detected',
                                                    f'A new template is available [{template.get("name")}], would you '
                                                    f'like to download it ?',
                                                    icon='question')
                    if MsgBox == 'yes':
                        url = f"http://linsotracker.com/tracker/templates/{template['template_name']}-{template['lastest_version']}.template"
                        self.core_service.download_and_replace(url, self.template_directory,
                                                               f"{template['template_name']}.template")
                        self.set_check()
                        self.process_templates_list()

    def process_templates_list(self):
        temp_list = []
        official_temp_list = []
        dev_temp_list = []
        self.template_list = []
        templates = glob.glob(f"{self.template_directory}{os.sep}*.template")

        if os.path.exists(self.dev_template_directory):
            dev_templates = [d for d in glob.glob(f"{self.dev_template_directory}{os.sep}*") if os.path.isdir(d)]
            templates = dev_templates + templates

        for file in templates:
            if os.path.isdir(file):
                tracker_file_path = os.path.join(file, "tracker.json")
                icon_file_path = os.path.join(file, "icon.png")
                illustration_file_path = os.path.join(file, "illustration.png")
                if os.path.exists(tracker_file_path) and os.path.exists(icon_file_path) and os.path.exists(illustration_file_path):
                    with open(tracker_file_path, "rb") as tracker_file:
                        tracker_json = tracker_file.read()

                    with open(icon_file_path, "rb") as icon_file:
                        tracker_icon = icon_file.read()

                    with open(illustration_file_path, "rb") as illustration_file:
                        tracker_illustration = illustration_file.read()
                else:
                    continue
            else:
                archive = ZipFile(file, 'r')
                tracker_json = archive.read("tracker.json")
                tracker_icon = archive.read("icon.png")
                tracker_illustration = archive.read("illustration.png")

            data = json.loads(tracker_json)

            template_checker = TemplateChecker(data)

            template_data = {
                "filename": os.path.basename(file).replace(".template", ""),
                "information": data[0],
                "icon": pygame.image.load(io.BytesIO(tracker_icon)),
                "illustration": pygame.image.load(io.BytesIO(tracker_illustration)),
                "valid": template_checker.is_valid()
            }

            if os.path.isdir(file):
                template_data["is_dev_template"] = True

            if "Comments" in data[0]["Informations"]:
                template_data["Comments"] = data[0]["Informations"]["Comments"]

            if "Credits" in data[0]["Informations"]:
                template_data["Credits"] = data[0]["Informations"]["Credits"]

            if self.official_template:
                for off_template in self.official_template:
                    if off_template["template_name"] == template_data["filename"] and not "is_dev_template" in template_data:
                        template_data["official"] = off_template["lastest_version"]

                        if data[0]["Informations"]["Version"] != template_data["official"]:
                            template_data["outdated"] = True

                        official_temp_list.append(template_data)
                        break

            if "is_dev_template" in template_data:
                dev_temp_list.append(template_data)

            if not ("official" in template_data or "is_dev_template" in template_data):
                temp_list.append(template_data)

        for indev in dev_temp_list:
            self.template_list.append(indev)

        for official in official_temp_list:
            self.template_list.append(official)

        for none_official in temp_list:
            self.template_list.append(none_official)

        self.update_combo_options()
        self.apply_filters()

    def update_combo_options(self):
        """Keep only games that actually have at least one matching template."""
        self.combo_games = [
            game for game in self.games
            if any(self.template_in_game(template, game) for template in self.template_list)
        ]
        valid_ids = {game.get("id") for game in self.combo_games}
        if self.combo_selected not in valid_ids:
            self.combo_selected = None

    def apply_filters(self):
        """Build display_list from template_list using the combo + search filters."""
        search = self.search_text.strip().lower()
        selected_game = next((g for g in self.combo_games if g.get("id") == self.combo_selected), None)
        result = []
        for template in self.template_list:
            name = template["information"]["Informations"]["Name"]
            if selected_game and not self.template_in_game(template, selected_game):
                continue
            if search and search not in name.lower():
                continue
            result.append(template)
        self.display_list = result
        self.scroll_offset = 0
        self.selected_menu_index = None
        self.moved_tracker = None
        self.illustration = None
        self.fade_engine.reset()

    @staticmethod
    def draw_text(text, font_name, color, font_size, surface, position, outline=2, color_outline=(0, 0, 0)):
        try:
            outline_temp = outline
            core_service = CoreService()
            if core_service.zoom == 1 and outline == 1:
                outline_temp = 2

            tsurf, tpos = ptext.draw(str(text), position, fontname=font_name, antialias=True,
                                     owidth=outline_temp, ocolor=color_outline, color=color, fontsize=font_size,
                                     surf=surface)
            return tsurf, tpos
        except Exception as e:
            print(e)

    def click_down(self, mouse_position, button):
        if self.template_maker:
            self.template_maker.click_down(mouse_position, button)
            return
        if self.loaded_tracker:
            self.loaded_tracker.click_down(mouse_position, button)

    def click(self, mouse_position, button):
        if self.donation_popup_click(mouse_position, button):
            return

        if self.template_maker:
            template_maker = self.template_maker
            template_maker.click(mouse_position, button)
            template_maker.mouse_up()
            return

        if not self.loaded_tracker:
            if button == 1:
                search_rect, combo_rect = self.get_filter_rects()

                # Open dropdown overlays everything: handle it first.
                if self.combo_open:
                    for row_rect, value in self.combo_option_rects:
                        if row_rect.collidepoint(mouse_position):
                            self.combo_selected = value
                            self.apply_filters()
                            break
                    self.combo_open = False
                    return

                if combo_rect.collidepoint(mouse_position):
                    self.combo_open = True
                    self.search_active = False
                    return

                if search_rect.collidepoint(mouse_position):
                    self.search_active = True
                    return

                self.search_active = False

                if self.template_maker_button and self.template_maker_button.collidepoint(mouse_position):
                    self.open_template_maker()
                    return

                if self.core_service.is_on_element(mouse_positions=mouse_position,
                                                   element_positons=(self.btn_discord.left, self.btn_discord.top),
                                                   element_dimension=(self.btn_discord.w, self.btn_discord.h)):
                    Menu.open_discord()

                if self.core_service.is_on_element(mouse_positions=mouse_position,
                                                   element_positons=(self.btn_paypal.left, self.btn_paypal.top),
                                                   element_dimension=(self.btn_paypal.w, self.btn_paypal.h)):
                    Menu.open_paypal()

                for menu in self.menu_content:
                    if self.core_service.is_on_element(mouse_positions=mouse_position,
                                                       element_positons=menu["positions"],
                                                       element_dimension=menu["dimensions"]):
                        if menu["template"]["valid"]:
                            selected = menu["template"]
                            if "outdated" in selected and selected["outdated"]:
                                MsgBox = messagebox.askquestion('New version detected',
                                                                f'Do you want to update : {selected["information"]["Informations"]["Name"]} ?',
                                                                icon='question')
                                if MsgBox == 'yes':
                                    url = f"http://linsotracker.com/tracker/templates/{selected['filename']}-{selected['official']}.template"
                                    self.core_service.download_and_replace(url, self.template_directory,
                                                                           selected['filename'] + ".template")
                                    self.set_check()
                                    self.process_templates_list()
                                else:
                                    self.set_tracker(menu["template"]["filename"], "is_dev_template" in menu["template"])

                            else:
                                self.set_tracker(menu["template"]["filename"], "is_dev_template" in menu["template"])
        else:
            self.loaded_tracker.click(mouse_position, button)

    def mouse_move(self, mouse_position):
        if self.template_maker:
            self.template_maker.mouse_move(mouse_position)
        elif not self.loaded_tracker:
            self.update_hover(mouse_position)
        else:
            self.loaded_tracker.mouse_move(mouse_position)

    def update_hover(self, mouse_position):
        """Resolve which template box is under the cursor. Runs every frame so the
        glow keeps following the boxes while scrolling."""
        # Mouse over the filter widgets steals focus from the templates grid.
        if self.is_over_filters(mouse_position):
            self.moved_tracker = None
            self.illustration = None
            self.selected_menu_index = None
            self.fade_engine.reset()
            return
        for menu in self.menu_content:
            if self.core_service.is_on_element(mouse_positions=mouse_position,
                                               element_positons=menu["positions"],
                                               element_dimension=menu["dimensions"]):
                if self.moved_tracker != menu["template"]["filename"]:
                    self.fade_engine.reset()
                    self.illustration = menu["template"]["illustration"]
                    self.moved_tracker = menu["template"]["filename"]
                    self.selected_menu_index = menu["index"]
                # Refresh position every frame so the glow tracks the scroll.
                self.selected_position = (menu["positions"][0] + 19, menu["positions"][1] - 8)
                return
        self.moved_tracker = None
        self.illustration = None
        self.selected_menu_index = None
        self.fade_engine.reset()

    def set_tracker(self, tracker_name, is_dev_template=False):
        self.draw_loading_screen(0, "Starting template")
        self.loaded_tracker = Tracker(tracker_name, self, is_dev_template, progress_callback=self.draw_loading_screen)
        screen = pygame.display.get_surface()
        if screen:
            self.loading_active = False
            self.loaded_tracker.draw(screen, 0)
            pygame.display.update()

    def reset_tracker(self):
        del self.loaded_tracker
        self.loaded_tracker = None
        dimension = self.get_dimension()
        pygame.display.set_mode((dimension[0], dimension[1]))
        self.core_service.setgamewindowcenter(x=dimension[0], y=dimension[1])

    def keyup(self, button, screen):
        if self.template_maker:
            self.template_maker.keyup(button, screen)
            return
        if self.loaded_tracker:
            self.loaded_tracker.keyup(button, screen)

    def events(self, events, time_delta):
        if self.template_maker:
            return self.template_maker.events(events, time_delta)
        if self.loaded_tracker:
            return self.loaded_tracker.events(events, time_delta)
        # Home screen: mouse wheel scrolls the templates grid.
        if getattr(events, "type", None) == pygame.MOUSEWHEEL and not self.combo_open:
            self.scroll_offset = max(0, min(self.scroll_max,
                                            self.scroll_offset - events.y * self.scroll_step))
            return True
        # Home screen: capture typing while the search bar is focused.
        if self.search_active and getattr(events, "type", None) == pygame.KEYDOWN:
            if events.key == pygame.K_BACKSPACE:
                self.search_text = self.search_text[:-1]
            elif events.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.search_active = False
            elif events.unicode and events.unicode.isprintable():
                self.search_text += events.unicode
            self.apply_filters()
            return True
        return False
