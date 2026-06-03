import copy
import json
import os
import re
import shutil
from tkinter import filedialog, messagebox, simpledialog
from zipfile import ZipFile

import pygame

from Tools import ptext


class LayoutMixin:
    def draw(self, screen, time_delta=0):
        width, height = screen.get_size()
        self._layout(width, height)
        self._draw_background(screen, width, height)
        if self.mode == "start":
            self._draw_start_screen(screen)
        else:
            self._draw_toolbar(screen)
            self._draw_left_panel(screen)
            self._draw_canvas(screen)
            self._draw_right_panel(screen)
        self._draw_status(screen)
        if self.item_modal_open and self.position_pick_mode:
            self._draw_position_pick(screen)
        elif self.item_modal_open:
            self._draw_item_modal(screen)
        if self.field_editor_open and not self.item_modal_open:
            self._draw_field_editor(screen, screen.get_rect())
        if self.fonts_modal_open:
            self._draw_fonts_modal(screen)
        if self.sprite_picker_open:
            self._draw_sprite_picker(screen)
        if self.color_picker_open:
            self._draw_color_picker(screen)
        if self.prompt_open:
            self._draw_text_prompt(screen)

    def _layout(self, width, height):
        toolbar_h = 86
        margin = 20
        left_w = min(330, max(260, int(width * 0.24)))
        right_w = min(300, max(240, int(width * 0.22)))
        top = toolbar_h + margin
        body_h = height - toolbar_h - margin * 2 - 34
        self.left_panel_rect = pygame.Rect(margin, top, left_w, body_h)
        self.right_panel_rect = pygame.Rect(width - right_w - margin, top, right_w, body_h)
        canvas_x = self.left_panel_rect.right + margin
        self.canvas_rect = pygame.Rect(canvas_x, top, self.right_panel_rect.x - margin - canvas_x, body_h)

        x = margin
        y = 18
        button_h = 46
        labels = [
            ("back", "Back"),
            ("background", "Load background"),
            ("box", "Add box"),
            ("timer", "Add timer"),
            ("save", "Save devtemplate"),
        ]
        self.buttons = {}
        for key, label in labels:
            button_w = max(118, 26 + len(label) * 9)
            self.buttons[key] = pygame.Rect(x, y, button_w, button_h)
            x += button_w + 12

    def _draw_toolbar(self, screen):
        toolbar = pygame.Rect(0, 0, screen.get_width(), 86)
        self._draw_card(screen, toolbar, (12, 14, 20), border_color=(80, 72, 52), radius=0)
        for key, rect in self.buttons.items():
            color = (70, 74, 86)
            self._draw_button(screen, rect, self._button_label(key), color, hover=(key == self.hover_key))

        title_x = screen.get_width() - 330
        self._text(screen, "Template Maker", (title_x, 16), 30, self.COLORS["gold"])
        subtitle = self.project_name or "visual template layout test"
        self._text(screen, subtitle, (title_x + 3, 49), 15, self.COLORS["muted"])

    def _button_label(self, key):
        return {
            "back": "Back",
            "background": "Load background",
            "box": "Add box",
            "timer": "Add timer",
            "save": "Save devtemplate",
        }[key]

    def _draw_canvas(self, screen):
        self._draw_card(screen, self.canvas_rect, self.COLORS["panel"], radius=14)
        title_rect = pygame.Rect(self.canvas_rect.x + 18, self.canvas_rect.y + 12, self.canvas_rect.w - 36, 28)
        self._text(screen, "Canvas", title_rect.topleft, 24, self.COLORS["gold"])
        self._text(screen, f"{self.template_size[0]} x {self.template_size[1]}", (title_rect.right - 120, title_rect.y + 5), 16, self.COLORS["muted"])

        title_h = 50
        margin = 18
        inner = pygame.Rect(
            self.canvas_rect.x + margin,
            self.canvas_rect.y + title_h,
            self.canvas_rect.w - margin * 2,
            self.canvas_rect.h - title_h - margin,
        )
        bg_rect = self._get_template_rect(inner)
        self.last_bg_rect = bg_rect
        bg_color = self.background_color or {"r": 0, "g": 0, "b": 0}
        pygame.draw.rect(screen, (bg_color.get("r", 0), bg_color.get("g", 0), bg_color.get("b", 0)), bg_rect)
        if self.background:
            scale = bg_rect.w / self.template_size[0]
            bg_pos = self.background_position or {"x": 0, "y": 0}
            bg_w = max(1, int(self.background.get_width() * scale))
            bg_h = max(1, int(self.background.get_height() * scale))
            scaled = pygame.transform.smoothscale(self.background, (bg_w, bg_h))
            prev_clip = screen.get_clip()
            screen.set_clip(bg_rect)
            screen.blit(scaled, (
                bg_rect.x + int(bg_pos.get("x", 0) * scale),
                bg_rect.y + int(bg_pos.get("y", 0) * scale),
            ))
            screen.set_clip(prev_clip)
        else:
            self._draw_empty_canvas(screen, bg_rect)

        pygame.draw.rect(screen, self.COLORS["line_light"], bg_rect, 2)

        # Clip items to the template so off-canvas items (e.g. invisible helpers) don't spill out
        prev_clip = screen.get_clip()
        screen.set_clip(bg_rect)
        for index, item in enumerate(self.placed_items):
            rect = self._draw_item(screen, item, index, bg_rect)
            if index == self.selected_item_index:
                pygame.draw.rect(screen, self.COLORS["gold"], rect.inflate(8, 8), 3)
        screen.set_clip(prev_clip)

    def _draw_item(self, screen, item, index, bg_rect):
        icon = self._get_icon_surface(item["row"], item["column"], item.get("sheet"))
        item_sheet = self._sheet_by_name(item.get("sheet")) or self.active_sheet
        cw = item_sheet["cell_w"] if item_sheet else self.cell_width
        ch = item_sheet["cell_h"] if item_sheet else self.cell_height
        if item.get("kind") == "EditableBox":
            sizes = item.get("Sizes") or {}
            cw = int(sizes.get("w", 120))
            ch = int(sizes.get("h", 32))
        elif item.get("kind") == "TimerItem":
            timer_rect = (item.get("Timer") or {}).get("Rect", {})
            buttons = item.get("Buttons") or {}
            cw = int(timer_rect.get("w", 180))
            ch = int(timer_rect.get("h", 42))
            for cfg in buttons.values():
                rect_data = (cfg or {}).get("Rect", {})
                cw = max(cw, int(rect_data.get("x", 0)) + int(rect_data.get("w", 0)))
                ch = max(ch, int(rect_data.get("y", 0)) + int(rect_data.get("h", 0)))
        scale = bg_rect.w / self.template_size[0]
        size = (max(1, int(cw * scale)), max(1, int(ch * scale)))
        x = bg_rect.x + int(item["x"] * scale)
        y = bg_rect.y + int(item["y"] * scale)
        rect = pygame.Rect(x, y, size[0], size[1])
        item["screen_rect"] = rect
        if item.get("kind") == "EditableBox":
            pygame.draw.rect(screen, (245, 245, 245), rect)
            pygame.draw.rect(screen, self.COLORS["green"], rect, 2)
            placeholder = item.get("PlaceHolder") or item.get("name") or "EditableBox"
            self._text(screen, placeholder, (rect.x + 5, rect.y + 3), max(10, int(13 * scale)),
                       (20, 20, 20))
        elif item.get("kind") == "TimerItem":
            pygame.draw.rect(screen, (12, 15, 22), rect)
            pygame.draw.rect(screen, self.COLORS["green"], rect, 2)
            self._text_center(screen, "00:00.00", rect, max(10, int(24 * scale)), self.COLORS["green"])
        elif icon:
            icon = pygame.transform.smoothscale(icon, size)
            screen.blit(icon, rect)
        else:
            pygame.draw.rect(screen, self.COLORS["panel_alt"], rect)
        pygame.draw.rect(screen, self.COLORS["green"], rect, 2)
        if size[0] >= 24 and size[1] >= 24:
            self._text(screen, str(item["id"]), (rect.x + 3, rect.y + 1), 12, self.COLORS["line_light"])
        return rect

    def _draw_left_panel(self, screen):
        panel = self.left_panel_rect
        self._draw_card(screen, panel, self.COLORS["panel"], radius=14)
        pad = 14
        x = panel.x + pad
        y = panel.y + 14
        self._text(screen, "Spritesheets", (x, y), 22, self.COLORS["gold"])

        # Add / Remove buttons
        self.sheet_buttons = {}
        add_btn = pygame.Rect(panel.right - pad - 30, y - 2, 30, 26)
        rem_btn = pygame.Rect(add_btn.x - 36, y - 2, 30, 26)
        self.sheet_buttons["add"] = add_btn
        self.sheet_buttons["remove"] = rem_btn
        self._draw_button(screen, add_btn, "+", (36, 124, 87), hover=(self.hover_key == "sheet_add"))
        self._draw_button(screen, rem_btn, "-", self.COLORS["red"], hover=(self.hover_key == "sheet_remove"))
        y += 36

        # Dropdown header (shows active sheet, click to expand)
        header_h = 34
        self.sheet_dropdown_rect = pygame.Rect(x, y, panel.w - pad * 2, header_h)
        self._draw_card(screen, self.sheet_dropdown_rect, (40, 46, 62), border_color=self.COLORS["gold"], radius=8)
        max_name = max(6, (self.sheet_dropdown_rect.w - 44) // 9)
        if self.active_sheet:
            name = self.active_sheet["name"]
            if len(name) > max_name:
                name = name[:max_name - 1] + "..."
            self._text(screen, name, (x + 10, y + 7), 16, self.COLORS["gold"])
        else:
            self._text(screen, "No spritesheet - press +", (x + 10, y + 7), 15, self.COLORS["muted"])
        chevron = "v" if not self.sheet_dropdown_open else "^"
        self._text(screen, chevron, (self.sheet_dropdown_rect.right - 20, y + 6), 16, self.COLORS["gold"])
        y += header_h + 12

        # Active tileset preview below the dropdown
        self.sheet_list_rows = {}
        if not self.active_sheet:
            self.sheet_rect = pygame.Rect(0, 0, 1, 1)
        else:
            self._text(screen, f"Tiles - cell {self.cell_width}x{self.cell_height}", (x, y), 14, self.COLORS["muted"])
            ty = y + 22
            area = pygame.Rect(x, ty, panel.w - pad * 2, panel.bottom - ty - 14)
            self._draw_card(screen, area, (10, 12, 18), border_color=(56, 62, 76), radius=8)
            self._draw_tileset(screen, area)

        # Expanded dropdown list (overlay, drawn last so it sits on top)
        if self.sheet_dropdown_open and self.sheets:
            row_h = 30
            list_rect = pygame.Rect(self.sheet_dropdown_rect.x, self.sheet_dropdown_rect.bottom + 2,
                                    self.sheet_dropdown_rect.w, len(self.sheets) * row_h + 6)
            self._draw_card(screen, list_rect, (18, 21, 30), border_color=self.COLORS["gold"], radius=8)
            ry = list_rect.y + 3
            for index, sheet in enumerate(self.sheets):
                row = pygame.Rect(list_rect.x + 3, ry, list_rect.w - 6, row_h - 2)
                self.sheet_list_rows[index] = row
                active = index == self.active_sheet_index
                if active:
                    pygame.draw.rect(screen, (40, 46, 62), row)
                elif self.hover_key == f"sheetrow_{index}":
                    pygame.draw.rect(screen, self.COLORS["panel_alt"], row)
                name_color = self.COLORS["gold"] if active else self.COLORS["line_light"]
                dims = f"{sheet['cell_w']}x{sheet['cell_h']}"
                dims_w = len(dims) * 8
                dims_x = row.right - dims_w - 10
                name = sheet["name"]
                max_name = max(4, (dims_x - (row.x + 8)) // 9)
                if len(name) > max_name:
                    name = name[:max_name - 1] + "..."
                self._text(screen, name, (row.x + 8, row.y + 5), 16, name_color)
                self._text(screen, dims, (dims_x, row.y + 6), 14, self.COLORS["muted"])
                ry += row_h

    def _draw_right_panel(self, screen):
        panel = self.right_panel_rect
        self._draw_card(screen, panel, self.COLORS["panel"], radius=14)
        pad = 14
        x = panel.x + pad
        y = panel.y + 14
        self._text(screen, "Template", (x, y), 22, self.COLORS["gold"])
        y += 40
        self.info_buttons = {}

        # Name (clickable to rename)
        name_rect = pygame.Rect(x, y, panel.w - pad * 2, 50)
        self._draw_card(screen, name_rect, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        self.info_buttons["name"] = name_rect
        self._text(screen, "NAME", (name_rect.x + 10, name_rect.y + 6), 12, self.COLORS["gold"])
        display = self.project_name or "Untitled"
        if len(display) > 22:
            display = display[:19] + "..."
        self._text(screen, display, (name_rect.x + 10, name_rect.y + 24), 18, self.COLORS["line_light"])
        y = name_rect.bottom + 14

        # Icon
        self._text(screen, "ICON", (x, y), 12, self.COLORS["gold"])
        y += 18
        icon_rect = pygame.Rect(x, y, 72, 72)
        self._draw_card(screen, icon_rect, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        icon = self.project_icon
        if icon is None and self.sheets:
            icon = self._get_icon_surface(1, 1, self.sheets[0]["name"])
        if icon:
            scaled = pygame.transform.smoothscale(icon, (56, 56))
            screen.blit(scaled, (icon_rect.centerx - 28, icon_rect.centery - 28))
        set_icon = pygame.Rect(icon_rect.right + 14, icon_rect.y + 8, panel.right - pad - (icon_rect.right + 14), 30)
        self.info_buttons["set_icon"] = set_icon
        self._draw_button(screen, set_icon, "Set from tile", self.COLORS["button"], hover=(self.hover_key == "set_icon"))
        self._text(screen, "uses selected tile", (icon_rect.right + 16, set_icon.bottom + 6), 13, self.COLORS["muted"])
        y = icon_rect.bottom + 16

        # Background color
        bg_row = pygame.Rect(x, y, panel.w - pad * 2, 44)
        self._draw_card(screen, bg_row, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        self.info_buttons["background_color"] = bg_row
        self._text(screen, "BACKGROUND COLOR", (bg_row.x + 10, bg_row.y + 6), 12, self.COLORS["gold"])
        bg = self.background_color or {"r": 0, "g": 0, "b": 0}
        swatch = pygame.Rect(bg_row.right - 56, bg_row.y + 10, 38, 24)
        pygame.draw.rect(screen, (bg.get("r", 0), bg.get("g", 0), bg.get("b", 0)), swatch)
        pygame.draw.rect(screen, self.COLORS["line_light"], swatch, 1)
        self._text(screen, f"{bg.get('r',0)}, {bg.get('g',0)}, {bg.get('b',0)}",
                   (bg_row.x + 10, bg_row.y + 24), 14, self.COLORS["line_light"])
        y = bg_row.bottom + 14

        dim_row = pygame.Rect(x, y, panel.w - pad * 2, 44)
        self._draw_card(screen, dim_row, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        self.info_buttons["dimensions"] = dim_row
        self._text(screen, "DIMENSIONS", (dim_row.x + 10, dim_row.y + 6), 12, self.COLORS["gold"])
        self._text(screen, f"{self.template_size[0]} x {self.template_size[1]}",
                   (dim_row.x + 10, dim_row.y + 24), 15, self.COLORS["line_light"])
        y = dim_row.bottom + 8

        bg_pos = self.background_position or {"x": 0, "y": 0}
        pos_row = pygame.Rect(x, y, panel.w - pad * 2, 44)
        self._draw_card(screen, pos_row, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        self.info_buttons["background_position"] = pos_row
        self._text(screen, "BACKGROUND POSITION", (pos_row.x + 10, pos_row.y + 6), 12, self.COLORS["gold"])
        self._text(screen, f"x {bg_pos.get('x', 0)} / y {bg_pos.get('y', 0)}",
                   (pos_row.x + 10, pos_row.y + 24), 15, self.COLORS["line_light"])
        y = pos_row.bottom + 14

        max_chars = max(8, (panel.w - pad * 2) // 9 - 2)

        # Editable Informations fields (click to edit). Always offer the standard keys.
        edit_keys = ["Creator", "Version", "Credits"]
        for key in (self.project_info or {}):
            if key != "Name" and key not in edit_keys:
                edit_keys.append(key)
        for key in edit_keys:
            row = pygame.Rect(x, y, panel.w - pad * 2, 44)
            self._draw_card(screen, row, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
            self.info_buttons[f"info_{key}"] = row
            self._text(screen, key.upper(), (row.x + 10, row.y + 6), 12, self.COLORS["gold"])
            value = str((self.project_info or {}).get(key) or "")
            display = value if value else "click to edit"
            color = self.COLORS["line_light"] if value else self.COLORS["muted"]
            if len(display) > max_chars:
                display = display[:max_chars - 3] + "..."
            self._text(screen, display, (row.x + 10, row.y + 24), 15, color)
            y += 50

        # Computed (read-only) info
        value_x = x + 120
        value_chars = max(4, (panel.right - pad - value_x) // 9)
        for label, value in [
            ("Background", os.path.basename(self.background_path) if self.background_path else "None"),
            ("Tilesets", str(len(self.sheets))),
            ("Items placed", str(len(self.placed_items))),
        ]:
            self._text(screen, label, (x, y), 13, self.COLORS["muted"])
            display = value if len(value) <= value_chars else value[:value_chars - 3] + "..."
            self._text(screen, display, (value_x, y), 15, self.COLORS["line_light"])
            y += 26

        # Fonts editor button
        y += 8
        fonts_btn = pygame.Rect(x, y, panel.w - pad * 2, 38)
        self.info_buttons["fonts"] = fonts_btn
        self._draw_button(screen, fonts_btn, "Edit fonts", (70, 74, 86), hover=(self.hover_key == "fonts"))

    def _draw_position_pick(self, screen):
        item = self._selected_item()
        # Preview the dragged item at the mouse position on the canvas
        mx, my = pygame.mouse.get_pos()
        if item and self.last_bg_rect.collidepoint((mx, my)):
            icon = self._get_icon_surface(item["row"], item["column"], item.get("sheet"))
            if icon:
                sheet = self._sheet_by_name(item.get("sheet")) or self.active_sheet
                scale = self.last_bg_rect.w / self.template_size[0]
                cw = (sheet["cell_w"] if sheet else 32) * scale
                ch = (sheet["cell_h"] if sheet else 32) * scale
                sized = pygame.transform.smoothscale(icon, (max(1, int(cw)), max(1, int(ch))))
                screen.blit(sized, (mx - sized.get_width() // 2, my - sized.get_height() // 2))
                pygame.draw.rect(screen, self.COLORS["gold"],
                                 (mx - sized.get_width() // 2, my - sized.get_height() // 2,
                                  sized.get_width(), sized.get_height()), 2)
        banner = pygame.Rect(self.canvas_rect.x, self.canvas_rect.y, self.canvas_rect.w, 30)
        pygame.draw.rect(screen, (40, 46, 62), banner)
        pygame.draw.rect(screen, self.COLORS["gold"], banner, 1)
        self._text_center(screen, "Click on the canvas to place the item  -  Esc to cancel", banner, 15, self.COLORS["gold"])

