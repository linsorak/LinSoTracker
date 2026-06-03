import copy
import json
import os
import re
import shutil
from tkinter import filedialog, messagebox, simpledialog
from zipfile import ZipFile

import pygame

from Tools import ptext


class DrawingMixin:
    def _text(self, surface, text, position, size=None, color=None):
        return ptext.draw(
            str(text),
            position,
            fontname=self.font_path,
            antialias=True,
            owidth=1,
            ocolor=(0, 0, 0),
            color=color or self.font_color,
            fontsize=size or self.font_size,
            surf=surface
        )

    def _text_center(self, surface, text, rect, size=None, color=None):
        temp = pygame.Surface((1, 1), pygame.SRCALPHA)
        text_surface, _ = self._text(temp, text, (0, 0), size, color)
        surface.blit(text_surface, (
            rect.x + (rect.w - text_surface.get_width()) // 2,
            rect.y + (rect.h - text_surface.get_height()) // 2
        ))

    def _truncate_text_to_width(self, text, max_width, size=None):
        text = str(text)
        if max_width <= 0 or not text:
            return ""
        temp = pygame.Surface((1, 1), pygame.SRCALPHA)
        rendered, _ = self._text(temp, text, (0, 0), size, self.font_color)
        if rendered.get_width() <= max_width:
            return text
        ellipsis = "..."
        low = 0
        high = len(text)
        while low < high:
            mid = (low + high + 1) // 2
            candidate = text[:mid] + ellipsis
            rendered, _ = self._text(temp, candidate, (0, 0), size, self.font_color)
            if rendered.get_width() <= max_width:
                low = mid
            else:
                high = mid - 1
        return text[:low] + ellipsis

    def _draw_card(self, screen, rect, color, border_color=None, radius=0):
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, border_color or self.COLORS["line"], rect, 1)

    def _draw_button(self, screen, rect, label, color, hover=False):
        # Flat solid fill, brighten slightly on hover
        fill = self._lighten(color, 18) if hover else color
        pygame.draw.rect(screen, fill, rect)

        # Thin flat border, accent on hover
        border = self._lighten(fill, 30) if hover else self._darken(color, 18)
        pygame.draw.rect(screen, border, rect, 1)

        font_size = self.font_size
        if rect.h <= 30:
            font_size = max(12, self.font_size - 3)
        elif rect.w < 80:
            font_size = max(12, self.font_size - 2)
        self._text_center(screen, label, rect, font_size, self.COLORS["button_text"])

    @staticmethod
    def _lighten(color, amount):
        return tuple(min(255, channel + amount) for channel in color)

    @staticmethod
    def _darken(color, amount):
        return tuple(max(0, channel - amount) for channel in color)

    @staticmethod
    def _set_cursor_safe(cursor):
        try:
            pygame.mouse.set_cursor(cursor)
        except pygame.error:
            pass

    @staticmethod
    def _slugify(value):
        value = value.strip().lower()
        value = re.sub(r"[^a-z0-9_-]+", "-", value)
        return value.strip("-")

    def _draw_empty_canvas(self, screen, rect):
        pygame.draw.rect(screen, (20, 23, 32), rect)
        for x in range(rect.x, rect.right, 32):
            pygame.draw.line(screen, (35, 39, 50), (x, rect.y), (x, rect.bottom), 1)
        for y in range(rect.y, rect.bottom, 32):
            pygame.draw.line(screen, (35, 39, 50), (rect.x, y), (rect.right, y), 1)
        self._text_center(screen, "Load a background to start", rect, 30, self.COLORS["muted"])
        hint_rect = pygame.Rect(rect.centerx - 210, rect.centery + 34, 420, 34)
        pygame.draw.rect(screen, (36, 124, 87), hint_rect)
        self._text_center(screen, "then select a sprite and click here", hint_rect, self.font_size, self.COLORS["line_light"])

    def _draw_background(self, screen, width, height):
        screen.fill(self.COLORS["bg"])
        for y in range(0, height, 42):
            pygame.draw.line(screen, (15, 17, 24), (0, y), (width, y), 1)
        for x in range(0, width, 42):
            pygame.draw.line(screen, (15, 17, 24), (x, 0), (x, height), 1)
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.circle(overlay, (134, 247, 161, 26), (int(width * 0.18), 120), 340)
        pygame.draw.circle(overlay, (243, 200, 106, 30), (int(width * 0.82), 90), 300)
        overlay.fill((0, 0, 0, 90), special_flags=pygame.BLEND_RGBA_SUB)
        screen.blit(overlay, (0, 0))

    def _get_template_rect(self, container):
        tw, th = self._canvas_size()
        scale = min(container.w / tw, container.h / th)
        w = int(tw * scale)
        h = int(th * scale)
        return pygame.Rect(container.x + (container.w - w) // 2, container.y + (container.h - h) // 2, w, h)

    def _canvas_size(self):
        if getattr(self, "canvas_context", "main") == "submenu":
            background = self._submenu_background_surface()
            if background:
                return background.get_size()
        return self.template_size

    def _canvas_background_surface(self):
        if getattr(self, "canvas_context", "main") == "submenu":
            return self._submenu_background_surface()
        return self.background

    def _canvas_background_color(self):
        if getattr(self, "canvas_context", "main") == "submenu":
            return {"r": 0, "g": 0, "b": 0}
        return self.background_color or {"r": 0, "g": 0, "b": 0}

    def _canvas_background_position(self):
        if getattr(self, "canvas_context", "main") == "submenu":
            return {"x": 0, "y": 0}
        return self.background_position or {"x": 0, "y": 0}

    def _submenu_background_surface(self, item=None):
        item = item or getattr(self, "submenu_parent", None)
        if not item:
            return None
        if item.get("_submenu_background_surface"):
            return item["_submenu_background_surface"]
        name = item.get("Background")
        if not name:
            return None
        candidates = []
        if getattr(self, "project_dir", None):
            candidates.append(os.path.join(self.project_dir, name))
        if getattr(self, "background_path", None):
            candidates.append(os.path.join(os.path.dirname(self.background_path), name))
        for path in candidates:
            if os.path.exists(path):
                try:
                    surface = pygame.image.load(path).convert_alpha()
                    item["_submenu_background_surface"] = surface
                    item["_submenu_background_path"] = path
                    return surface
                except Exception:
                    return None
        return None

    def _draw_status(self, screen):
        rect = pygame.Rect(20, screen.get_height() - 42, screen.get_width() - 40, 28)
        flashing = pygame.time.get_ticks() < getattr(self, "status_flash_until", 0)
        if flashing:
            pygame.draw.rect(screen, (36, 124, 87), rect)
            pygame.draw.rect(screen, self.COLORS["green"], rect, 1)
        else:
            pygame.draw.rect(screen, (10, 12, 18), rect)
            pygame.draw.rect(screen, (56, 62, 76), rect, 1)
        self._text(screen, self.message, (rect.x + 12, rect.y + 5), self.font_size, self.COLORS["muted"])

    def _flash_status(self, message, duration_ms=2500):
        self.message = message
        self.status_flash_until = pygame.time.get_ticks() + duration_ms

