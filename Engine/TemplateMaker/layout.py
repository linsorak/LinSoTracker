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
        if self.context_menu_open:
            self._draw_context_menu(screen)
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
        if self.canvas_context == "submenu":
            labels = [
                ("back", "Back to template"),
            ]
        else:
            labels = [
                ("back", "Back"),
                ("background", "Load background"),
                ("save", "Save devtemplate"),
                ("saveas", "Save as"),
                ("renumber", "Fix IDs"),
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
        if key == "back" and self.canvas_context == "submenu":
            return "Back to template"
        return {
            "back": "Back",
            "background": "Load background",
            "box": "Add box",
            "timer": "Add timer",
            "save": "Save devtemplate",
            "saveas": "Save as",
            "renumber": "Fix IDs",
        }[key]

    def _draw_canvas(self, screen):
        self._draw_card(screen, self.canvas_rect, self.COLORS["panel"], radius=14)
        title_rect = pygame.Rect(self.canvas_rect.x + 18, self.canvas_rect.y + 12, self.canvas_rect.w - 36, 28)
        canvas_size = self._canvas_size()
        title = "Submenu canvas" if self.canvas_context == "submenu" else "Canvas"
        self._text(screen, title, title_rect.topleft, 24, self.COLORS["gold"])
        self._text(screen, f"{canvas_size[0]} x {canvas_size[1]}", (title_rect.right - 120, title_rect.y + 5), 16, self.COLORS["muted"])

        # "See links" checkbox, below the title (shown in main and submenu canvas)
        box = pygame.Rect(title_rect.x, title_rect.y + 30, 18, 18)
        self.see_links_rect = pygame.Rect(box.x, box.y, 110, 20)
        pygame.draw.rect(screen, (20, 24, 34), box)
        pygame.draw.rect(screen, self.COLORS["gold"] if self.show_links else (56, 62, 76), box, 2)
        if self.show_links:
            pygame.draw.line(screen, self.COLORS["green"], (box.x + 3, box.centery), (box.centerx - 1, box.bottom - 4), 2)
            pygame.draw.line(screen, self.COLORS["green"], (box.centerx - 1, box.bottom - 4), (box.right - 3, box.y + 3), 2)
        self._text(screen, "See links", (box.right + 6, box.y + 1), 14,
                   self.COLORS["line_light"] if self.show_links else self.COLORS["muted"])

        title_h = 60
        margin = 18
        inner = pygame.Rect(
            self.canvas_rect.x + margin,
            self.canvas_rect.y + title_h,
            self.canvas_rect.w - margin * 2,
            self.canvas_rect.h - title_h - margin,
        )
        bg_rect = self._get_template_rect(inner)
        self.last_bg_rect = bg_rect
        bg_color = self._canvas_background_color()
        pygame.draw.rect(screen, (bg_color.get("r", 0), bg_color.get("g", 0), bg_color.get("b", 0)), bg_rect)
        background = self._canvas_background_surface()
        if background:
            scale = bg_rect.w / canvas_size[0]
            bg_pos = self._canvas_background_position()
            bg_w = max(1, int(background.get_width() * scale))
            bg_h = max(1, int(background.get_height() * scale))
            scaled = pygame.transform.smoothscale(background, (bg_w, bg_h))
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
        self.linked_item_targets = []
        hidden = self._linked_identities()
        for index, item in enumerate(self.placed_items):
            # Items owned as Hint/Active/Inactive refs are drawn by their parent, not standalone
            if self._item_ref_identity(item) in hidden:
                item["screen_rect"] = pygame.Rect(0, 0, 0, 0)
                continue
            rect = self._draw_item(screen, item, index, bg_rect)
            if index == self.selected_item_index:
                pygame.draw.rect(screen, self.COLORS["gold"], rect.inflate(8, 8), 3)
            self._draw_linked_items(screen, item, bg_rect, parent_path=(index,))
        screen.set_clip(prev_clip)

    def _draw_linked_items(self, screen, item, bg_rect, depth=0, parent_path=()):
        if depth > 8:
            return
        linked_fields = [
            ("HintItems", (0, 220, 255)),
            ("ActiveItems", self.COLORS["green"]),
            ("InactiveItems", self.COLORS["red"]),
        ]
        parent_rect = item.get("screen_rect")
        for field, color in linked_fields:
            for linked_index, linked in enumerate(item.get(field) or []):
                path = parent_path + (field, linked_index)
                rect = self._draw_item(screen, linked, None, bg_rect, linked=True)
                if self.show_links and parent_rect and parent_rect.w > 0:
                    self._draw_link_elbow(screen, parent_rect, rect, color)
                linked["_linked_path"] = path
                self.linked_item_targets.append((path, rect))
                pygame.draw.rect(screen, color, rect.inflate(5, 5), 2)
                if path == self.selected_linked_path:
                    pygame.draw.rect(screen, self.COLORS["gold"], rect.inflate(9, 9), 3)
                label = field.replace("Items", "")
                if rect.w >= 20 and rect.h >= 20:
                    self._text(screen, label[:1], (rect.right - 10, rect.y + 1), 12, color)
                self._draw_linked_items(screen, linked, bg_rect, depth + 1, path)

    def _draw_item(self, screen, item, index, bg_rect, linked=False):
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
        scale = bg_rect.w / self._canvas_size()[0]
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
            if not item.get("visible", True):
                icon = icon.copy()
                icon.set_alpha(95)
            screen.blit(icon, rect)
        else:
            pygame.draw.rect(screen, self.COLORS["panel_alt"], rect)
        pygame.draw.rect(screen, self.COLORS["red"] if not item.get("visible", True) else self.COLORS["green"], rect, 2)
        if not item.get("visible", True) and rect.w >= 18 and rect.h >= 18:
            self._text(screen, "V", (rect.right - 10, rect.bottom - 16), 12, self.COLORS["red"])
        if size[0] >= 24 and size[1] >= 24:
            self._text(screen, str(item["id"]), (rect.x + 3, rect.y + 1), 12,
                       self.COLORS["muted"] if linked else self.COLORS["line_light"])
        return rect

    def _draw_items_list_tab(self, screen, panel, x, y, pad):
        entries = self._flatten_items_for_list()
        self.items_list_entries = entries
        self._text(screen, f"{len(entries)} item(s)", (x, y), 13, self.COLORS["muted"])
        y += 22
        area = pygame.Rect(x, y, panel.w - pad * 2, panel.bottom - y - 14)
        self._draw_card(screen, area, (10, 12, 18), border_color=(56, 62, 76), radius=8)
        self.items_list_rect = area
        self.items_list_rows = {}
        if not entries:
            self._text_center(screen, "No item yet", area, 16, self.COLORS["muted"])
            return
        row_h = 40
        view = area.inflate(-8, -8)
        content_h = len(entries) * row_h
        max_scroll = max(0, content_h - view.h)
        self.items_list_scroll = max(0, min(self.items_list_scroll, max_scroll))
        prev_clip = screen.get_clip()
        screen.set_clip(view)
        for index, entry in enumerate(entries):
            item = entry["item"]
            depth = entry["depth"]
            ry = view.y + index * row_h - self.items_list_scroll
            if ry + row_h < view.y or ry > view.bottom:
                continue
            indent = depth * 16
            row = pygame.Rect(view.x + indent, ry, view.w - indent, row_h - 4)
            self.items_list_rows[index] = row
            if entry["path"] == (self.selected_item_index,) and self.selected_item_index is not None and depth == 0:
                selected = True
            elif depth > 0 and entry["path"] == self.selected_linked_path:
                selected = True
            else:
                selected = False
            hovered = self.hover_key == f"itemrow_{index}"
            if selected:
                pygame.draw.rect(screen, (40, 46, 62), row)
                pygame.draw.rect(screen, self.COLORS["gold"], row, 1)
            elif hovered:
                pygame.draw.rect(screen, self.COLORS["panel_alt"], row)
            if entry["color"]:
                pygame.draw.rect(screen, entry["color"], (row.x, row.y, 3, row.h))
            icon = self._get_icon_surface(item.get("row", 1), item.get("column", 1), item.get("sheet"))
            ix = row.x + 8
            if icon:
                screen.blit(pygame.transform.smoothscale(icon, (28, 28)), (ix, row.y + 4))
            else:
                pygame.draw.rect(screen, (30, 35, 48), pygame.Rect(ix, row.y + 4, 28, 28))
            name = item.get("name", "Item")
            maxn = max(5, (row.w - 48) // 8)
            if len(name) > maxn:
                name = name[:maxn - 1] + "..."
            self._text(screen, name, (ix + 34, row.y + 4), 14, self.COLORS["line_light"])
            self._text(screen, item.get("kind", "Item"), (ix + 34, row.y + 22), 11, self.COLORS["muted"])
        screen.set_clip(prev_clip)
        if max_scroll > 0:
            track = pygame.Rect(area.right - 7, view.y, 4, view.h)
            pygame.draw.rect(screen, (40, 46, 62), track)
            th = max(20, int(track.h * view.h / content_h))
            ty = track.y + int((track.h - th) * self.items_list_scroll / max_scroll)
            pygame.draw.rect(screen, self.COLORS["gold"], (track.x, ty, track.w, th))

    def _draw_left_panel(self, screen):
        panel = self.left_panel_rect
        self._draw_card(screen, panel, self.COLORS["panel"], radius=14)
        pad = 14
        x = panel.x + pad
        y = panel.y + 12

        # Tabs: Sheets | Items List
        self.left_tabs = {}
        tab_w = (panel.w - pad * 2 - 8) // 2
        for i, (key, label) in enumerate([("sheets", "Sheets"), ("items", "Items List")]):
            tr = pygame.Rect(x + i * (tab_w + 8), y, tab_w, 30)
            self.left_tabs[key] = tr
            active = self.left_tab == key
            pygame.draw.rect(screen, (40, 46, 62) if active else (20, 24, 34), tr)
            pygame.draw.rect(screen, self.COLORS["gold"] if active else (56, 62, 76), tr, 1)
            self._text_center(screen, label, tr, 15, self.COLORS["gold"] if active else self.COLORS["line_light"])
        y += 40

        if self.left_tab == "items":
            self.sheet_buttons = {}
            self.sheet_list_rows = {}
            self.sheet_rect = pygame.Rect(0, 0, 1, 1)
            self._draw_items_list_tab(screen, panel, x, y, pad)
            return

        # New (blank) / Add (import) / Remove buttons
        self.sheet_buttons = {}
        add_btn = pygame.Rect(panel.right - pad - 30, y - 2, 30, 26)
        rem_btn = pygame.Rect(add_btn.x - 36, y - 2, 30, 26)
        new_btn = pygame.Rect(rem_btn.x - 56, y - 2, 50, 26)
        self.sheet_buttons["new"] = new_btn
        self.sheet_buttons["add"] = add_btn
        self.sheet_buttons["remove"] = rem_btn
        self._draw_button(screen, new_btn, "New", (70, 74, 86), hover=(self.hover_key == "sheet_new"))
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
            # Reserve a strip at the bottom for the "set tile image" button
            set_tile_btn = pygame.Rect(x, panel.bottom - 48, panel.w - pad * 2, 34)
            area = pygame.Rect(x, ty, panel.w - pad * 2, set_tile_btn.y - ty - 10)
            self._draw_card(screen, area, (10, 12, 18), border_color=(56, 62, 76), radius=8)
            self._draw_tileset(screen, area)
            self.sheet_buttons["set_tile"] = set_tile_btn
            sel = self.selected_cell and self.active_sheet and self.selected_cell[0] == self.active_sheet["name"]
            label = "Set image in selected tile" if sel else "Select a tile first"
            self._draw_button(screen, set_tile_btn, label, (70, 74, 86) if sel else (44, 48, 62),
                              hover=(self.hover_key == "sheet_set_tile"))

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
        self._text(screen, "Submenu" if self.canvas_context == "submenu" else "Template", (x, y), 22, self.COLORS["gold"])
        y += 40
        self.info_buttons = {}

        if self.canvas_context == "submenu":
            self._draw_submenu_info_panel(screen, panel, x, y, pad)
            return

        # Scrollable content area (title above stays fixed)
        content_top = y
        view = pygame.Rect(panel.x + 2, content_top, panel.w - 4, panel.bottom - content_top - 8)
        self.info_panel_rect = view
        prev_clip = screen.get_clip()
        screen.set_clip(view)
        y = content_top - self.info_scroll

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
        btn_x = icon_rect.right + 14
        btn_w = panel.right - pad - btn_x
        set_icon = pygame.Rect(btn_x, icon_rect.y, btn_w, 30)
        self.info_buttons["set_icon"] = set_icon
        self._draw_button(screen, set_icon, "Set from tile", self.COLORS["button"], hover=(self.hover_key == "set_icon"))
        import_icon = pygame.Rect(btn_x, set_icon.bottom + 8, btn_w, 30)
        self.info_buttons["import_icon"] = import_icon
        self._draw_button(screen, import_icon, "Import image", (70, 74, 86), hover=(self.hover_key == "import_icon"))
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

        # Illustration import button
        y += 8
        illu_btn = pygame.Rect(x, y, panel.w - pad * 2, 34)
        self.info_buttons["illustration"] = illu_btn
        illu_label = "Illustration: imported" if self.illustration is not None else "Import illustration"
        self._draw_button(screen, illu_btn, illu_label, (70, 74, 86), hover=(self.hover_key == "illustration"))
        y += 42

        # Fonts editor button
        fonts_btn = pygame.Rect(x, y, panel.w - pad * 2, 38)
        self.info_buttons["fonts"] = fonts_btn
        self._draw_button(screen, fonts_btn, "Edit fonts", (70, 74, 86), hover=(self.hover_key == "fonts"))
        y += 38

        screen.set_clip(prev_clip)

        # Scroll clamping + scrollbar
        content_h = (y + self.info_scroll) - content_top
        max_scroll = max(0, content_h - view.h)
        self.info_scroll = max(0, min(self.info_scroll, max_scroll))
        self.info_max_scroll = max_scroll
        if max_scroll > 0:
            track = pygame.Rect(panel.right - 7, view.y + 2, 4, view.h - 4)
            pygame.draw.rect(screen, (40, 46, 62), track)
            th = max(24, int(track.h * view.h / content_h))
            ty = track.y + int((track.h - th) * self.info_scroll / max_scroll)
            pygame.draw.rect(screen, self.COLORS["gold"], (track.x, ty, track.w, th))

    def _draw_link_elbow(self, screen, a, b, color):
        ax, ay = a.center
        bx, by = b.center
        midx = (ax + bx) // 2
        pts = [(ax, ay), (midx, ay), (midx, by), (bx, by)]
        pygame.draw.lines(screen, color, False, pts, 2)
        pygame.draw.circle(screen, color, (bx, by), 3)

    def _draw_context_menu(self, screen):
        items = []
        has_target = self.context_menu_path is not None
        top_level = has_target and len(self.context_menu_path) == 1
        if has_target:
            items.append(("ctx_edit", "Edit"))
            if top_level:
                items.append(("ctx_duplicate", "Duplicate"))
            else:
                items.append(("ctx_unlink", "Unlink"))
            items.append(("ctx_delete", "Delete"))
        # "Add item" only from the canvas (needs a drop position)
        on_canvas = self.last_bg_rect.collidepoint(self.context_menu_pos)
        if on_canvas:
            items.append(("ctx_add", "Add item  >"))
        w, rh = 160, 30
        mx, my = self.context_menu_pos
        h = len(items) * rh + 8
        mx = min(mx, screen.get_width() - w - 4)
        my = min(my, screen.get_height() - h - 4)
        menu = pygame.Rect(mx, my, w, h)
        self._draw_card(screen, menu, (20, 24, 34), border_color=self.COLORS["gold"], radius=6)
        self.context_menu_buttons = {}
        y = menu.y + 4
        add_row = None
        for key, label in items:
            row = pygame.Rect(menu.x + 4, y, menu.w - 8, rh - 2)
            self.context_menu_buttons[key] = row
            if key == "ctx_add":
                add_row = row
            hov = row.collidepoint(pygame.mouse.get_pos())
            if hov or (key == "ctx_add" and self.context_add_open):
                pygame.draw.rect(screen, self.COLORS["panel_alt"], row)
            color = self.COLORS["red"] if key == "ctx_delete" else self.COLORS["line_light"]
            self._text(screen, label, (row.x + 12, row.y + 5), 15, color)
            y += rh

        # Kind submenu
        if self.context_add_open and add_row is not None:
            kinds = self._available_item_kinds()
            srh = 26
            sw = 170
            sh = len(kinds) * srh + 8
            sx = menu.right + 2
            if sx + sw > screen.get_width() - 4:
                sx = menu.x - sw - 2
            sy = min(add_row.y, screen.get_height() - sh - 4)
            sub = pygame.Rect(sx, sy, sw, sh)
            self._draw_card(screen, sub, (24, 28, 40), border_color=self.COLORS["gold"], radius=6)
            ky = sub.y + 4
            for kind in kinds:
                krow = pygame.Rect(sub.x + 4, ky, sub.w - 8, srh - 2)
                self.context_menu_buttons[f"ctxkind_{kind}"] = krow
                if krow.collidepoint(pygame.mouse.get_pos()):
                    pygame.draw.rect(screen, self.COLORS["panel_alt"], krow)
                self._text(screen, kind, (krow.x + 10, krow.y + 4), 14, self.COLORS["line_light"])
                ky += srh

    def _draw_position_pick(self, screen):
        item = self._selected_item()
        # Preview the dragged item at the mouse position on the canvas
        mx, my = pygame.mouse.get_pos()
        if item and self.last_bg_rect.collidepoint((mx, my)):
            icon = self._get_icon_surface(item["row"], item["column"], item.get("sheet"))
            if icon:
                sheet = self._sheet_by_name(item.get("sheet")) or self.active_sheet
                scale = self.last_bg_rect.w / self._canvas_size()[0]
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

    def _draw_submenu_info_panel(self, screen, panel, x, y, pad):
        item = self.submenu_parent or {}
        name_rect = pygame.Rect(x, y, panel.w - pad * 2, 58)
        self._draw_card(screen, name_rect, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        self._text(screen, "EDITING", (name_rect.x + 10, name_rect.y + 6), 12, self.COLORS["gold"])
        display = item.get("name", "SubMenuItem")
        if len(display) > 22:
            display = display[:19] + "..."
        self._text(screen, display, (name_rect.x + 10, name_rect.y + 25), 18, self.COLORS["line_light"])
        y = name_rect.bottom + 14

        bg_rect = pygame.Rect(x, y, panel.w - pad * 2, 44)
        self._draw_card(screen, bg_rect, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        self.info_buttons["submenu_background"] = bg_rect
        self._text(screen, "BACKGROUND", (bg_rect.x + 10, bg_rect.y + 6), 12, self.COLORS["gold"])
        bg_name = item.get("Background") or "None"
        if len(bg_name) > 24:
            bg_name = bg_name[:21] + "..."
        self._text(screen, bg_name, (bg_rect.x + 10, bg_rect.y + 24), 15, self.COLORS["line_light"])
        y = bg_rect.bottom + 10

        for key, label, color in [
            ("submenu_back", "Back to template", (70, 74, 86)),
        ]:
            btn = pygame.Rect(x, y, panel.w - pad * 2, 44)
            self.info_buttons[key] = btn
            self._draw_button(screen, btn, label, color, hover=(self.hover_key == key))
            y += 54

        size = self._canvas_size()
        infos = [
            ("Dimensions", f"{size[0]} x {size[1]}"),
            ("Items inside", str(len(self.placed_items))),
            ("Counter", "active" if item.get("ShowNumbersOfItemsActive") else "off"),
        ]
        value_x = x + 112
        for label, value in infos:
            self._text(screen, label, (x, y), 13, self.COLORS["muted"])
            self._text(screen, value, (value_x, y), 15, self.COLORS["line_light"])
            y += 26

