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
        modal_w = min(760, screen.get_width() - 80)
        modal_h = min(80 + len(self.FONT_SLOTS) * 64 + 40, screen.get_height() - 60)
        rect = pygame.Rect((screen.get_width() - modal_w) // 2, (screen.get_height() - modal_h) // 2, modal_w, modal_h)
        self._draw_card(screen, rect, (16, 19, 28), border_color=self.COLORS["gold"])
        self.fonts_buttons = {}

        self._text(screen, "FONTS", (rect.x + pad, rect.y + 18), 13, self.COLORS["muted"])
        self._text(screen, "Template fonts", (rect.x + pad, rect.y + 36), 24, self.COLORS["gold"])
        pygame.draw.line(screen, self.COLORS["line"], (rect.x + pad, rect.y + 74), (rect.right - pad, rect.y + 74), 1)
        close_rect = pygame.Rect(rect.right - pad - 32, rect.y + 22, 32, 32)
        self.fonts_buttons["close"] = close_rect
        self._draw_button(screen, close_rect, "X", self.COLORS["red"], hover=(self.hover_modal_key == "fonts_close"))

        y = rect.y + 86
        for slot in self.FONT_SLOTS:
            font = self.fonts.get(slot) or self._default_fonts()[slot]
            row = pygame.Rect(rect.x + pad, y, rect.w - pad * 2, 54)
            self._draw_card(screen, row, (12, 15, 22), border_color=(56, 62, 76))
            self._text(screen, slot, (row.x + 12, row.y + 8), 15, self.COLORS["gold"])

            # Name (ttf)
            name_rect = pygame.Rect(row.x + 12, row.y + 28, 200, 22)
            self.fonts_buttons[f"{slot}|name"] = name_rect
            pygame.draw.rect(screen, self.COLORS["panel_alt"], name_rect)
            pygame.draw.rect(screen, (56, 62, 76), name_rect, 1)
            nm = str(font.get("Name", "")); nm = nm if len(nm) <= 22 else nm[:19] + "..."
            self._text(screen, nm, (name_rect.x + 6, name_rect.y + 3), 13, self.COLORS["line_light"])

            # Size
            size_rect = pygame.Rect(name_rect.right + 10, row.y + 28, 56, 22)
            self.fonts_buttons[f"{slot}|size"] = size_rect
            pygame.draw.rect(screen, self.COLORS["panel_alt"], size_rect)
            pygame.draw.rect(screen, (56, 62, 76), size_rect, 1)
            self._text(screen, str(font.get("Size", 16)), (size_rect.x + 8, size_rect.y + 3), 13, self.COLORS["line_light"])

            # Color swatches Normal / Max
            colors = font.get("Colors", {})
            for ckey, cx in (("Normal", size_rect.right + 16), ("Max", size_rect.right + 116)):
                self._text(screen, ckey, (cx, row.y + 8), 12, self.COLORS["muted"])
                sw = pygame.Rect(cx, row.y + 28, 78, 22)
                self.fonts_buttons[f"{slot}|{ckey}"] = sw
                col = colors.get(ckey, {"r": 255, "g": 255, "b": 255})
                pygame.draw.rect(screen, (col.get("r", 255), col.get("g", 255), col.get("b", 255)), sw)
                pygame.draw.rect(screen, self.COLORS["line_light"], sw, 1)

            # Live preview using the actual font file + size + Normal color
            preview_rect = pygame.Rect(size_rect.right + 210, row.y + 6, row.right - (size_rect.right + 210) - 10, 42)
            pygame.draw.rect(screen, (8, 9, 13), preview_rect)
            pygame.draw.rect(screen, (56, 62, 76), preview_rect, 1)
            nc = colors.get("Normal", {"r": 255, "g": 255, "b": 255})
            self._draw_font_preview(screen, preview_rect, font, (nc.get("r", 255), nc.get("g", 255), nc.get("b", 255)))
            y += 62

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
            slot, _, field = key.partition("|")
            font = self.fonts.setdefault(slot, self._default_fonts()[slot])
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
            elif field in ("Normal", "Max"):
                col = font.setdefault("Colors", {}).setdefault(field, {"r": 255, "g": 255, "b": 255})
                def set_color(color, f=font, fld=field, s=slot):
                    f.setdefault("Colors", {})[fld] = color
                    self.message = f"{s} {fld} color updated."
                self._open_color_picker(f"{slot} {field}", col, set_color)
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

