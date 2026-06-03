import copy
import json
import os
import re
import shutil
from tkinter import filedialog, messagebox, simpledialog
from zipfile import ZipFile

import pygame

from Tools import ptext


class SheetsMixin:
    @property
    def active_sheet(self):
        if 0 <= self.active_sheet_index < len(self.sheets):
            return self.sheets[self.active_sheet_index]
        return None

    @property
    def sheet(self):
        active = self.active_sheet
        return active["surface"] if active else None

    @property
    def sheet_path(self):
        active = self.active_sheet
        return active["path"] if active else None

    @property
    def cell_width(self):
        active = self.active_sheet
        return active["cell_w"] if active else 32

    @property
    def cell_height(self):
        active = self.active_sheet
        return active["cell_h"] if active else 32

    def _sheet_by_name(self, name):
        for sheet in self.sheets:
            if sheet["name"] == name:
                return sheet
        return None

    def _unique_sheet_name(self, base):
        existing = {sheet["name"] for sheet in self.sheets}
        if base not in existing:
            return base
        index = 2
        while f"{base}{index}" in existing:
            index += 1
        return f"{base}{index}"

    def _add_sheet(self, path):
        try:
            surface = pygame.image.load(path).convert_alpha()
        except Exception as exc:
            self.message = f"Could not load spritesheet: {exc}"
            return

        def ask_width(_=None):
            self._open_text_prompt("Sprite cell width", 32, ask_height, kind="int",
                                   allow_empty=False, label="Cell width (px):", minvalue=1)

        def ask_height(width):
            if not width:
                return
            self._open_text_prompt("Sprite cell height", 32, lambda h: ask_name(width, h), kind="int",
                                   allow_empty=False, label="Cell height (px):", minvalue=1)

        def ask_name(width, height):
            if not height:
                return
            suggested = "Normal" if not self.sheets else "SubItems"
            self._open_text_prompt("Sheet name", suggested,
                                   lambda nm: finalize(width, height, nm),
                                   allow_empty=False, label="Sheet name (Normal, SubItems...):")

        def finalize(width, height, name):
            if not name:
                return
            name = self._unique_sheet_name(name.strip())
            self.sheets.append({
                "name": name, "surface": surface, "path": path,
                "cell_w": width, "cell_h": height,
            })
            self.active_sheet_index = len(self.sheets) - 1
            self.sheet_scroll = 0
            self.message = f"Added sheet '{name}' ({width}x{height})."

        ask_width()

    def _remove_active_sheet(self):
        if not self.active_sheet:
            self.message = "No sheet to remove."
            return
        name = self.active_sheet["name"]
        used = sum(1 for item in self.placed_items if item.get("sheet") == name)
        if used:
            self.message = f"Can't remove '{name}': {used} item(s) use it."
            return
        del self.sheets[self.active_sheet_index]
        self.active_sheet_index = max(0, min(self.active_sheet_index, len(self.sheets) - 1))
        if self.selected_cell and self.selected_cell[0] == name:
            self.selected_cell = None
        self.sheet_scroll = 0
        self.message = f"Removed sheet '{name}'."

    def _get_icon_surface(self, row, column, sheet_name=None):
        sheet = self._sheet_by_name(sheet_name) if sheet_name else self.active_sheet
        if not sheet:
            return None
        surface = sheet["surface"]
        cw, ch = sheet["cell_w"], sheet["cell_h"]
        x = (column - 1) * cw
        y = (row - 1) * ch
        if x < 0 or y < 0 or x + cw > surface.get_width() or y + ch > surface.get_height():
            return None
        return surface.subsurface((x, y, cw, ch)).copy()

    def _select_sprite(self, mouse_position):
        if not self.active_sheet or not self._tileset_geom:
            return
        origin_x, origin_y, cell_px, cell_py, cols, rows = self._tileset_geom
        column = int((mouse_position[0] - origin_x) // cell_px) + 1
        row = int((mouse_position[1] - origin_y) // cell_py) + 1
        if 1 <= column <= cols and 1 <= row <= rows and self._get_icon_surface(row, column):
            self.selected_cell = (self.active_sheet["name"], row, column)
            self.message = f"Selected {self.active_sheet['name']} tile row {row}, col {column}."

    def _place_item(self, mouse_position):
        bg_rect = self.last_bg_rect
        if not bg_rect.collidepoint(mouse_position):
            return
        scale = self.template_size[0] / bg_rect.w
        x = int((mouse_position[0] - bg_rect.x) * scale)
        y = int((mouse_position[1] - bg_rect.y) * scale)
        sheet_name, row, column = self.selected_cell
        item = {
            "id": len(self.placed_items) + 1,
            "name": f"Item {len(self.placed_items) + 1}",
            "kind": "Item",
            "x": x,
            "y": y,
            "row": row,
            "column": column,
            "sheet": sheet_name,
            "isActive": False,
            "opacity": 0.5,
            "hint": None,
            "children": [],
        }
        self._ensure_kind_defaults(item)
        self.placed_items.append(item)
        self.selected_item_index = len(self.placed_items) - 1
        self.message = "Item placed. Double-click it to edit. Delete key removes it."

    def _remove_last_item(self):
        if self.placed_items:
            self.placed_items.pop()
            self.selected_item_index = None
            self.message = "Removed last placed item."

    def _draw_tileset(self, screen, area):
        geom, scroll, srect = self._draw_tileset_grid(
            screen, area, self.active_sheet, self.sheet_scroll, self.selected_cell)
        self.sheet_scroll = scroll
        self.sheet_rect = srect
        self._tileset_geom = geom
        if self.selected_cell and self.active_sheet and self.selected_cell[0] == self.active_sheet["name"]:
            _, row, column = self.selected_cell
            self._text(screen, f"row {row}, col {column}", (area.x + 4, area.bottom + 2), 13, self.COLORS["green"])

    def _draw_tileset_grid(self, screen, area, sheet, scroll, selected):
        """Render a spritesheet as a clickable grid. Returns (geom, clamped_scroll, inner_rect)."""
        surface = sheet["surface"]
        cw, ch = sheet["cell_w"], sheet["cell_h"]
        sheet_w, sheet_h = surface.get_size()
        cols = max(1, sheet_w // cw)
        rows = max(1, sheet_h // ch)

        inner = area.inflate(-12, -12)
        scale = inner.w / sheet_w
        cell_px = cw * scale
        cell_h_px = ch * scale
        full_h = sheet_h * scale

        max_scroll = max(0, int(full_h - inner.h))
        scroll = max(0, min(scroll, max_scroll))

        prev_clip = screen.get_clip()
        screen.set_clip(inner)
        origin_x = inner.x
        origin_y = inner.y - scroll
        scaled = pygame.transform.smoothscale(surface, (max(1, int(sheet_w * scale)), max(1, int(full_h))))
        screen.blit(scaled, (origin_x, origin_y))

        for c in range(cols + 1):
            gx = origin_x + int(c * cell_px)
            pygame.draw.line(screen, (60, 66, 82), (gx, inner.y), (gx, inner.bottom), 1)
        for r in range(rows + 1):
            gy = origin_y + int(r * cell_h_px)
            if inner.y - 1 <= gy <= inner.bottom + 1:
                pygame.draw.line(screen, (60, 66, 82), (inner.x, gy), (inner.right, gy), 1)

        mouse_pos = pygame.mouse.get_pos()
        if inner.collidepoint(mouse_pos):
            hc = int((mouse_pos[0] - origin_x) // cell_px) + 1
            hr = int((mouse_pos[1] - origin_y) // cell_h_px) + 1
            if 1 <= hc <= cols and 1 <= hr <= rows:
                hx = origin_x + int((hc - 1) * cell_px)
                hy = origin_y + int((hr - 1) * cell_h_px)
                pygame.draw.rect(screen, self.COLORS["line_light"], (hx, hy, int(cell_px), int(cell_h_px)), 2)

        if selected and selected[0] == sheet["name"]:
            _, row, column = selected
            sx = origin_x + int((column - 1) * cell_px)
            sy = origin_y + int((row - 1) * cell_h_px)
            pygame.draw.rect(screen, self.COLORS["green"], (sx, sy, int(cell_px), int(cell_h_px)), 3)

        screen.set_clip(prev_clip)
        pygame.draw.rect(screen, (56, 62, 76), inner, 1)
        geom = (origin_x, origin_y, cell_px, cell_h_px, cols, rows)
        return geom, scroll, inner

    # --- Sprite picker (reusable window) ---
    def _action_sheet(self):
        path = filedialog.askopenfilename(
            title="Add a tileset / spritesheet",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")]
        )
        if not path:
            return
        self._add_sheet(path)

    def _open_sprite_picker(self, title, target):
        if not self.sheets:
            self.message = "Add a spritesheet first."
            return
        self.sprite_picker_title = title
        self.sprite_picker_target = target
        self.picker_sheet_index = self.active_sheet_index if 0 <= self.active_sheet_index < len(self.sheets) else 0
        self.picker_scroll = 0
        self.sprite_picker_open = True

    def _picker_sheet(self):
        if 0 <= self.picker_sheet_index < len(self.sheets):
            return self.sheets[self.picker_sheet_index]
        return None

    def _draw_sprite_picker(self, screen):
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))

        pad = 20
        modal_w = min(640, screen.get_width() - 80)
        modal_h = min(680, screen.get_height() - 60)
        rect = pygame.Rect((screen.get_width() - modal_w) // 2, (screen.get_height() - modal_h) // 2, modal_w, modal_h)
        self._draw_card(screen, rect, (16, 19, 28), border_color=self.COLORS["gold"])
        self.picker_buttons = {}

        self._text(screen, self.sprite_picker_title or "Choose a sprite", (rect.x + pad, rect.y + 16), 22, self.COLORS["gold"])
        close_rect = pygame.Rect(rect.right - pad - 30, rect.y + 16, 30, 30)
        self.picker_buttons["close"] = close_rect
        self._draw_button(screen, close_rect, "X", self.COLORS["red"], hover=(self.hover_modal_key == "picker_close"))

        # Sheet selector tabs
        tx = rect.x + pad
        ty = rect.y + 56
        for index, sheet in enumerate(self.sheets):
            label = sheet["name"]
            tab_w = max(60, 16 + len(label) * 9)
            if tx + tab_w > rect.right - pad:
                tx = rect.x + pad
                ty += 34
            tab = pygame.Rect(tx, ty, tab_w, 28)
            self.picker_buttons[f"psheet_{index}"] = tab
            active = index == self.picker_sheet_index
            pygame.draw.rect(screen, (40, 46, 62) if active else self.COLORS["panel_alt"], tab)
            pygame.draw.rect(screen, self.COLORS["gold"] if active else (56, 62, 76), tab, 1)
            self._text_center(screen, label, tab, 14, self.COLORS["gold"] if active else self.COLORS["line_light"])
            tx += tab_w + 6
        ty += 36

        sheet = self._picker_sheet()
        if not sheet:
            self._text(screen, "No spritesheet.", (rect.x + pad, ty), 16, self.COLORS["muted"])
            return
        area = pygame.Rect(rect.x + pad, ty, rect.w - pad * 2, rect.bottom - ty - pad)
        self._draw_card(screen, area, (10, 12, 18), border_color=(56, 62, 76))
        geom, scroll, srect = self._draw_tileset_grid(screen, area, sheet, self.picker_scroll, None)
        self.picker_scroll = scroll
        self.picker_geom = geom
        self.picker_tileset_rect = srect

    def _handle_picker_click(self, mouse_position):
        if self.picker_buttons.get("close") and self.picker_buttons["close"].collidepoint(mouse_position):
            self.sprite_picker_open = False
            return
        for index in range(len(self.sheets)):
            rect = self.picker_buttons.get(f"psheet_{index}")
            if rect and rect.collidepoint(mouse_position):
                self.picker_sheet_index = index
                self.picker_scroll = 0
                return
        sheet = self._picker_sheet()
        if sheet and self.picker_geom and self.picker_tileset_rect.collidepoint(mouse_position):
            ox, oy, cell_px, cell_py, cols, rows = self.picker_geom
            col = int((mouse_position[0] - ox) // cell_px) + 1
            row = int((mouse_position[1] - oy) // cell_py) + 1
            if 1 <= col <= cols and 1 <= row <= rows and self._get_icon_surface(row, col, sheet["name"]):
                if callable(self.sprite_picker_target):
                    self.sprite_picker_target(sheet["name"], row, col)
                self.sprite_picker_open = False
            return
        # click outside content closes
        modal_hit = any(r.collidepoint(mouse_position) for r in self.picker_buttons.values())
        if not modal_hit and not self.picker_tileset_rect.collidepoint(mouse_position):
            self.sprite_picker_open = False

