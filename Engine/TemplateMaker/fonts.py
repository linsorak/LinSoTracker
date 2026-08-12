import copy
import json
import os
import re
import shutil
from tkinter import filedialog, messagebox, simpledialog
from zipfile import ZipFile

import pygame

from Tools import ptext


class FontsMixin:
    def _draw_fonts_modal(self, screen):
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        pad = 24
        slots = self._active_font_slots()
        row_h = 62
        modal_w = min(820, screen.get_width() - 80)
        view_h = min(len(slots) * row_h, screen.get_height() - 220)
        modal_h = view_h + 130
        rect = pygame.Rect((screen.get_width() - modal_w) // 2, (screen.get_height() - modal_h) // 2, modal_w, modal_h)
        self._draw_popup(screen, rect, radius=8)
        self.fonts_buttons = {}

        self._text(screen, "FONTS", (rect.x + pad, rect.y + 18), 13, self.COLORS["muted"])
        title = "Template fonts" + ("  (incl. map fonts)" if self.is_map_template else "")
        self._text(screen, title, (rect.x + pad, rect.y + 36), 24, self.COLORS["gold"])
        pygame.draw.line(screen, self.COLORS["line"], (rect.x + pad, rect.y + 74), (rect.right - pad, rect.y + 74), 1)
        close_rect = pygame.Rect(rect.right - pad - 32, rect.y + 22, 32, 32)
        self.fonts_buttons["close"] = close_rect
        self._draw_button(screen, close_rect, "X", self.COLORS["red"], hover=(self.hover_modal_key == "fonts_close"))

        # Scrollable font rows
        view = pygame.Rect(rect.x + pad, rect.y + 86, rect.w - pad * 2, view_h)
        content_h = len(slots) * row_h
        max_scroll = max(0, content_h - view.h)
        self.fonts_scroll = max(0, min(getattr(self, "fonts_scroll", 0), max_scroll))
        self.fonts_max_scroll = max_scroll
        prev_clip = screen.get_clip()
        screen.set_clip(view)
        y = view.y - self.fonts_scroll
        for slot in slots:
            font = self.fonts.get(slot) or self.MAP_FONT_DEFAULTS.get(slot) or self._default_fonts().get(slot)
            if y + row_h < view.y or y > view.bottom:
                y += row_h
                continue
            row = pygame.Rect(view.x, y, view.w, 54)
            self._draw_card(screen, row, (12, 15, 22), border_color=(56, 62, 76))
            self._text(screen, slot, (row.x + 12, row.y + 8), 15, self.COLORS["gold"])

            name_rect = pygame.Rect(row.x + 12, row.y + 28, 180, 22)
            self.fonts_buttons[f"{slot}|name"] = name_rect
            pygame.draw.rect(screen, self.COLORS["panel_alt"], name_rect)
            pygame.draw.rect(screen, (56, 62, 76), name_rect, 1)
            nm = str(font.get("Name", "")); nm = nm if len(nm) <= 20 else nm[:17] + "..."
            self._text(screen, nm, (name_rect.x + 6, name_rect.y + 3), 13, self.COLORS["line_light"])

            size_rect = pygame.Rect(name_rect.right + 10, row.y + 28, 50, 22)
            self.fonts_buttons[f"{slot}|size"] = size_rect
            pygame.draw.rect(screen, self.COLORS["panel_alt"], size_rect)
            pygame.draw.rect(screen, (56, 62, 76), size_rect, 1)
            self._text(screen, str(font.get("Size", 16)), (size_rect.x + 8, size_rect.y + 3), 13, self.COLORS["line_light"])

            # Color swatches for each color key the font actually defines
            colors = font.get("Colors", {}) or {"Normal": {"r": 255, "g": 255, "b": 255}}
            cx = size_rect.right + 12
            color_gap = 4
            available_w = max(24, row.right - 150 - cx)
            sw_w = max(24, min(48, (
                available_w - color_gap * max(0, len(colors) - 1)) // max(1, len(colors))))
            for ckey in colors:
                self._text(screen, ckey[:6], (cx, row.y + 8), 10, self.COLORS["muted"])
                sw = pygame.Rect(cx, row.y + 28, sw_w, 22)
                self.fonts_buttons[f"{slot}|color|{ckey}"] = sw
                col = colors.get(ckey, {"r": 255, "g": 255, "b": 255})
                pygame.draw.rect(screen, (col.get("r", 255), col.get("g", 255), col.get("b", 255)), sw)
                pygame.draw.rect(screen, self.COLORS["line_light"], sw, 1)
                cx += sw_w + color_gap

            preview_rect = pygame.Rect(row.right - 140, row.y + 6, 130, 42)
            pygame.draw.rect(screen, (8, 9, 13), preview_rect)
            pygame.draw.rect(screen, (56, 62, 76), preview_rect, 1)
            nc = colors.get("Normal") or next(iter(colors.values()), {"r": 255, "g": 255, "b": 255})
            self._draw_font_preview(screen, preview_rect, font, (nc.get("r", 255), nc.get("g", 255), nc.get("b", 255)))
            y += row_h
        screen.set_clip(prev_clip)
        track = pygame.Rect(rect.right - pad + 6, view.y, 5, view.h)
        self._register_scrollbar(screen, "fonts", track, self.fonts_scroll, max_scroll, content_h, view.h)

    def _resolve_font_path(self, name):
        if not name:
            return self.font_path
        if name in self.font_files and os.path.exists(self.font_files[name]):
            return self.font_files[name]
        if self.project_dir:
            candidate = os.path.join(self.project_dir, name)
            if os.path.exists(candidate):
                return candidate
        return self.font_path

    def _draw_font_preview(self, screen, rect, font, color):
        path = self._resolve_font_path(font.get("Name"))
        size = max(10, min(int(font.get("Size", 16)), rect.h - 8))
        prev_clip = screen.get_clip()
        screen.set_clip(rect)
        try:
            ptext.draw(
                "AaBb 0123",
                (rect.x + 8, rect.centery - size // 2),
                fontname=path,
                antialias=True,
                color=color,
                fontsize=size,
                surf=screen,
            )
        except Exception:
            self._text(screen, "AaBb 0123", (rect.x + 8, rect.y + 10), 14, color)
        screen.set_clip(prev_clip)

    def _handle_fonts_click(self, mouse_position):
        for key, rect in self.fonts_buttons.items():
            if not rect.collidepoint(mouse_position):
                continue
            if key == "close":
                self.fonts_modal_open = False
                return
            parts = key.split("|")
            slot = parts[0]
            field = parts[1] if len(parts) > 1 else ""
            default_font = self.MAP_FONT_DEFAULTS.get(slot) or self._default_fonts().get(slot) \
                or {"Name": "NotoSans-Bold.ttf", "Size": 16, "Colors": {"Normal": {"r": 255, "g": 255, "b": 255}}}
            font = self.fonts.setdefault(slot, copy.deepcopy(default_font))
            if field == "name":
                path = filedialog.askopenfilename(title="Pick a font", filetypes=[("Fonts", "*.ttf *.otf"), ("All files", "*.*")])
                if path:
                    fname = os.path.basename(path)
                    font["Name"] = fname
                    self.font_files[fname] = path
                    self.message = f"{slot} font set to {fname}."
            elif field == "size":
                def set_size(value, f=font):
                    if value is not None:
                        f["Size"] = value
                self._open_text_prompt("Font size", int(font.get("Size", 16)), set_size,
                                       kind="int", allow_empty=False, label="Size (px):", minvalue=1)
            elif field == "color" and len(parts) > 2:
                ckey = parts[2]
                col = font.setdefault("Colors", {}).setdefault(ckey, {"r": 255, "g": 255, "b": 255})
                def set_color(color, f=font, fld=ckey, s=slot):
                    f.setdefault("Colors", {})[fld] = color
                    self.message = f"{s} {fld} color updated."
                self._open_color_picker(f"{slot} {ckey}", col, set_color)
            return
        self.fonts_modal_open = False

    def _font_color(self, slot):
        col = (self.fonts.get(slot, {}) or {}).get("Colors", {}).get("Normal", {})
        return (col.get("r", 255), col.get("g", 255), col.get("b", 255))

    def _preview_font_dir(self):
        # Directory that holds the .ttf files referenced by the fonts
        if self.project_dir and os.path.isdir(self.project_dir):
            return self.project_dir
        return os.path.dirname(self.font_path) if self.font_path else ""

    def _with_preview_core(self, func):
        """Run func() with core_service temporarily wired to this template's fonts."""
        cs = self.core_service
        if cs is None:
            return func()
        old_json = getattr(cs, "json_data", None)
        old_temp = getattr(cs, "tracker_temp_path", None)
        try:
            cs.json_data = [None, None, {"Fonts": self.fonts}, None]
            cs.tracker_temp_path = self._preview_font_dir()
            return func()
        finally:
            cs.json_data = old_json
            cs.tracker_temp_path = old_temp

