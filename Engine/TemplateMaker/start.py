import copy
import json
import os
import re
import shutil
from tkinter import filedialog, messagebox, simpledialog
from zipfile import ZipFile

import pygame

from Tools import ptext


class StartMixin:
    def _draw_start_screen(self, screen):
        width, height = screen.get_size()
        pad = 32
        panel_w = min(820, width - 80)
        panel_h = min(620, height - 60)
        panel = pygame.Rect((width - panel_w) // 2, (height - panel_h) // 2, panel_w, panel_h)
        self._draw_card(screen, panel, (16, 19, 28), border_color=self.COLORS["gold"])

        # Header
        self._text(screen, "Template Maker", (panel.x + pad, panel.y + 28), 40, self.COLORS["gold"])
        self._text(screen, "Build a tracker template visually, then save it to devtemplates.", (panel.x + pad + 2, panel.y + 78), 16, self.COLORS["muted"])
        pygame.draw.line(screen, self.COLORS["line"], (panel.x + pad, panel.y + 108), (panel.right - pad, panel.y + 108), 1)

        self.start_buttons = {}
        # Top action buttons
        actions_y = panel.y + 124
        new_rect = pygame.Rect(panel.x + pad, actions_y, 220, 48)
        open_rect = pygame.Rect(new_rect.right + 14, actions_y, 220, 48)
        self.start_buttons["new"] = new_rect
        self.start_buttons["open"] = open_rect
        gray = (70, 74, 86)
        self._draw_button(screen, new_rect, "+  New project", gray, hover=(self.hover_start_key == "new"))
        self._draw_button(screen, open_rect, "Open .template file", gray, hover=(self.hover_start_key == "open"))

        # Existing projects list
        list_top = actions_y + 78
        self._text(screen, "YOUR PROJECTS", (panel.x + pad, list_top - 26), 14, self.COLORS["muted"])
        list_rect = pygame.Rect(panel.x + pad, list_top, panel.w - pad * 2, panel.bottom - list_top - 78)
        self._draw_card(screen, list_rect, (12, 15, 22), border_color=(56, 62, 76))

        self.project_cards = {}
        self.project_delete_buttons = {}
        self.project_list_rect = list_rect
        if not self.projects:
            self._text_center(screen, "No projects yet — create a new one to get started.", list_rect, 17, self.COLORS["muted"])
        else:
            card_h = 64
            gap = 8
            step = card_h + gap
            inner_x = list_rect.x + 12
            inner_w = list_rect.w - 24
            view_top = list_rect.y + 12
            view_h = list_rect.h - 24
            content_h = len(self.projects) * step - gap
            max_scroll = max(0, content_h - view_h)
            self.project_scroll = max(0, min(self.project_scroll, max_scroll))

            prev_clip = screen.get_clip()
            screen.set_clip(list_rect)
            for index, project in enumerate(self.projects):
                cy = view_top + index * step - self.project_scroll
                if cy + card_h < list_rect.y or cy > list_rect.bottom:
                    continue  # off-screen, skip draw + clickable registration
                card = pygame.Rect(inner_x, cy, inner_w, card_h)
                self.project_cards[index] = card
                hovered = self.hover_start_key == f"project_{index}"
                bg = self.COLORS["panel_alt"] if hovered else (20, 24, 34)
                pygame.draw.rect(screen, bg, card)
                pygame.draw.rect(screen, self.COLORS["gold"] if hovered else (56, 62, 76), card, 1)

                icon = project.get("icon")
                if icon:
                    scaled = pygame.transform.smoothscale(icon, (44, 44))
                    screen.blit(scaled, (card.x + 12, card.centery - 22))
                else:
                    pygame.draw.rect(screen, (30, 35, 48), pygame.Rect(card.x + 12, card.centery - 22, 44, 44))
                self._text(screen, project["name"], (card.x + 70, card.y + 12), 20, self.COLORS["line_light"])
                self._text(screen, os.path.basename(project["dir"]), (card.x + 70, card.y + 38), 14, self.COLORS["muted"])

                del_rect = pygame.Rect(card.right - 44, card.centery - 15, 30, 30)
                self.project_delete_buttons[index] = del_rect
                self._draw_button(screen, del_rect, "X", self.COLORS["red"], hover=(self.hover_start_key == f"del_{index}"))
                self._text(screen, "Open", (card.right - 108, card.centery - 9), 16, self.COLORS["green"])
            screen.set_clip(prev_clip)

            if max_scroll > 0:
                track = pygame.Rect(list_rect.right - 8, list_rect.y + 4, 4, list_rect.h - 8)
                pygame.draw.rect(screen, (40, 46, 62), track)
                th = max(24, int(track.h * view_h / content_h))
                ty = track.y + int((track.h - th) * self.project_scroll / max_scroll)
                pygame.draw.rect(screen, self.COLORS["gold"], (track.x, ty, track.w, th))

        # Back button
        back_rect = pygame.Rect(panel.x + pad, panel.bottom - 60, 150, 42)
        self.start_buttons["back"] = back_rect
        self._draw_button(screen, back_rect, "Back", (70, 74, 86), hover=(self.hover_start_key == "back"))

    def _scan_projects(self):
        self.projects = []
        directory = self.main_menu.dev_template_directory
        if not os.path.isdir(directory):
            return
        for entry in sorted(os.listdir(directory)):
            folder = os.path.join(directory, entry)
            tracker_path = os.path.join(folder, "tracker.json")
            if not os.path.isdir(folder) or not os.path.exists(tracker_path):
                continue
            name = entry
            try:
                with open(tracker_path, "r", encoding="utf-8-sig") as file:
                    data = json.load(file)
                name = data[0].get("Informations", {}).get("Name") or entry
            except Exception:
                pass
            icon = None
            icon_path = os.path.join(folder, "icon.png")
            if os.path.exists(icon_path):
                try:
                    icon = pygame.image.load(icon_path).convert_alpha()
                except Exception:
                    icon = None
            self.projects.append({"name": name, "dir": folder, "icon": icon})

    def _start_new_project(self):
        self._open_text_prompt("New template project", "My Template", self._create_new_project,
                               allow_empty=False, label="Project name:")

    def _create_new_project(self, name):
        if not name:
            return
        self.project_name = name
        self.project_dir = os.path.join(self.main_menu.dev_template_directory, self._slugify(name))
        self.project_info = {
            "Creator": "Template Maker",
            "Name": name,
            "Version": "0.1",
            "Comments": "Generated by LinSoTracker Template Maker",
        }
        self.fonts = self._default_fonts()
        self.font_files = {}
        self.background_path = None
        self.background = None
        self.illustration = None
        self.illustration_path = None
        self.background_color = {"r": 0, "g": 0, "b": 0}
        self.background_position = {"x": 0, "y": 0}
        self.sheets = []
        self.active_sheet_index = 0
        self.sheet_scroll = 0
        self.selected_cell = None
        self.project_icon = None
        self.placed_items = []
        self.main_items = self.placed_items
        self.canvas_context = "main"
        self.submenu_parent = None
        self.submenu_parent_index = None
        self.selected_item_index = None
        self.item_modal_open = False
        self.template_size = (800, 600)
        self.mode = "editor"
        self.message = "New project created. Add a background and a tileset (+) to start."

    def _open_template_file(self):
        path = filedialog.askopenfilename(
            title="Open template archive",
            filetypes=[("LinSoTracker template", "*.template"), ("All files", "*.*")]
        )
        if path:
            self._load_template_archive(path)

    def _delete_project(self, index):
        if index < 0 or index >= len(self.projects):
            return
        project = self.projects[index]
        confirm = messagebox.askyesno(
            "Delete project",
            f"Delete '{project['name']}' permanently?\n\n{project['dir']}"
        )
        if not confirm:
            return
        try:
            shutil.rmtree(project["dir"])
            self.message = f"Deleted {project['name']}."
        except Exception as exc:
            self.message = f"Could not delete project: {exc}"
        self._scan_projects()
        if hasattr(self.main_menu, "process_templates_list"):
            self.main_menu.process_templates_list()

    def _action_back(self):
        if getattr(self, "canvas_context", "main") == "submenu":
            self._exit_submenu_canvas()
            return
        self._set_cursor_safe(pygame.SYSTEM_CURSOR_ARROW)
        if hasattr(self.main_menu, "close_template_maker"):
            self.main_menu.close_template_maker()
        else:
            self.main_menu.template_maker = None

    def _rename_project(self):
        def cb(name):
            if name:
                self.project_name = name
                if self.project_info is None:
                    self.project_info = {}
                self.project_info["Name"] = name
                self.message = f"Template renamed to {name}."
        self._open_text_prompt("Template name", self.project_name or "My Template", cb, label="Name:")

    def _edit_info_field(self, key):
        current = str((self.project_info or {}).get(key) or "")
        self._open_text_prompt(f"Edit {key}", current, lambda v: self._apply_info_field(key, v), label=f"{key}:")

    def _edit_template_background_color(self):
        def apply(color):
            self.background_color = color
            self.message = "Template background color updated."
        self._open_color_picker("Template background", self.background_color, apply)

    def _edit_template_dimensions(self):
        width, height = self.template_size
        data = {"Dimensions": {"w": width, "h": height}}

        def apply():
            dims = data["Dimensions"]
            self.template_size = (
                max(1, int(dims.get("w", width))),
                max(1, int(dims.get("h", height))),
            )
            self.message = f"Template dimensions set to {self.template_size[0]} x {self.template_size[1]}."

        self.field_editor_open = True
        self.field_editor_spec = {
            "key": "Dimensions",
            "type": "rect",
            "label": "Template dimensions",
            "default": {"w": width, "h": height},
            "keys": ["w", "h"],
        }
        self.field_editor_item = data
        self.field_editor_callback = apply

    def _edit_background_position(self):
        pos = self.background_position or {"x": 0, "y": 0}
        data = {"BackgroundPosition": {"x": pos.get("x", 0), "y": pos.get("y", 0)}}

        def apply():
            value = data["BackgroundPosition"]
            self.background_position = {
                "x": int(value.get("x", 0)),
                "y": int(value.get("y", 0)),
            }
            self.message = f"Background position set to {self.background_position['x']}, {self.background_position['y']}."

        self.field_editor_open = True
        self.field_editor_spec = {
            "key": "BackgroundPosition",
            "type": "rect",
            "label": "Background position",
            "default": {"x": pos.get("x", 0), "y": pos.get("y", 0)},
            "keys": ["x", "y"],
            "min": {"x": None, "y": None},
        }
        self.field_editor_item = data
        self.field_editor_callback = apply

    def _apply_info_field(self, key, value):
        if value is None:
            return
        if self.project_info is None:
            self.project_info = {}
        self.project_info[key] = value
        self.message = f"{key} updated."

