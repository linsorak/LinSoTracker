import copy
import json
import math
import os
import re
import shutil
from tkinter import filedialog, messagebox, simpledialog
from zipfile import ZipFile

import pygame

from Tools import ptext


class DrawingMixin:
    def _render_ui_text(self, text, size=None, color=None):
        font_size = int(size or self.font_size)
        font_path = getattr(self, "ui_font_path", None)
        resolved_color = tuple(color or self.font_color)
        text = str(text)
        font_key = (font_path, font_size * 2)
        font_cache = getattr(self, "_ui_font_cache", None)
        if font_cache is None:
            font_cache = self._ui_font_cache = {}
        font = font_cache.get(font_key)
        if font is None:
            font = pygame.font.Font(font_path, font_size * 2)
            font_cache[font_key] = font

        cache = getattr(self, "_ui_text_cache", None)
        if cache is None:
            cache = self._ui_text_cache = {}
        cache_key = (font_key, text, resolved_color)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # pygame can return a zero-width surface for an empty string. Passing
        # that surface to smoothscale crashes pygame-ce natively on Windows.
        if not text:
            rendered = pygame.Surface(
                (1, max(1, font.get_linesize() // 2)), pygame.SRCALPHA
            )
            cache[cache_key] = rendered
            return rendered

        text_surface = font.render(text, True, resolved_color)
        rendered = pygame.transform.smoothscale(
            text_surface,
            (max(1, text_surface.get_width() // 2), max(1, text_surface.get_height() // 2))
        )
        if len(cache) >= 1024:
            for old_key in list(cache)[:256]:
                cache.pop(old_key, None)
        cache[cache_key] = rendered
        return rendered
    def _text(self, surface, text, position, size=None, color=None):
        text_surface = self._render_ui_text(text, size, color)
        rect = text_surface.get_rect(topleft=position)
        surface.blit(text_surface, rect)
        return text_surface, rect

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
        self._draw_aa_rect(screen, color, rect, border_radius=radius)
        self._draw_aa_rect(screen, border_color or self.COLORS["line"], rect, 1, border_radius=radius)

    def _draw_popup(self, screen, rect, radius=12, border_color=None):
        """Modal frame with a drop shadow + thick bright border, so the popup
        clearly stands out from whatever is behind it."""
        shadow = rect.inflate(22, 22)
        shadow_surf = pygame.Surface(shadow.size, pygame.SRCALPHA)
        self._draw_aa_rect(shadow_surf, (0, 0, 0, 140), shadow_surf.get_rect(), border_radius=radius + 6)
        screen.blit(shadow_surf, shadow.topleft)
        self._draw_aa_rect(screen, self.COLORS["panel"], rect, border_radius=radius)
        self._draw_aa_rect(screen, (6, 7, 11), rect, 1, border_radius=radius)
        self._draw_aa_rect(screen, border_color or self.COLORS["gold"], rect, 3, border_radius=radius)

    def _draw_button(self, screen, rect, label, color, hover=False):
        # Flat solid fill, brighten slightly on hover
        fill = self._lighten(color, 18) if hover else color
        self._draw_aa_rect(screen, fill, rect)

        # Thin flat border, accent on hover
        border = self._lighten(fill, 30) if hover else self._darken(color, 18)
        self._draw_aa_rect(screen, border, rect, 1)

        font_size = self.font_size
        if rect.h <= 30:
            font_size = max(12, self.font_size - 3)
        elif rect.w < 80:
            font_size = max(12, self.font_size - 2)
        self._text_center(screen, label, rect, font_size, self.COLORS["button_text"])

    def _draw_aa_rect(self, screen, color, rect, width=0, border_radius=0):
        if border_radius <= 0:
            pygame.draw.rect(screen, color, rect, width)
            return
        cache = getattr(self, "_aa_rect_cache", None)
        if cache is None:
            cache = self._aa_rect_cache = {}
        cache_key = (rect.size, tuple(color), width, border_radius)
        cached = cache.get(cache_key)
        if cached is not None:
            screen.blit(cached, rect.topleft)
            return
        scale = 2
        surf = pygame.Surface((rect.w * scale, rect.h * scale), pygame.SRCALPHA)
        pygame.draw.rect(
            surf,
            color,
            surf.get_rect(),
            width * scale,
            border_radius=border_radius * scale
        )
        rendered = pygame.transform.smoothscale(surf, rect.size)
        if len(cache) >= 128:
            for old_key in list(cache)[:32]:
                cache.pop(old_key, None)
        cache[cache_key] = rendered
        screen.blit(rendered, rect.topleft)

    def _draw_cached_map_background(self, screen, background, bg_rect, view_rect):
        visible_rect = bg_rect.clip(view_rect)
        if visible_rect.w <= 0 or visible_rect.h <= 0:
            return

        local_visible = visible_rect.move(-bg_rect.x, -bg_rect.y)
        cache_key = (id(background), background.get_size(), bg_rect.size)
        cache_data = getattr(self, "_map_background_cache", None)
        if cache_data and cache_data["key"] == cache_key \
                and cache_data["rect"].contains(local_visible):
            cache_rect = cache_data["rect"]
            scaled = cache_data["surface"]
        else:
            desired = local_visible.inflate(
                max(128, local_visible.w),
                max(128, local_visible.h),
            )
            desired = desired.clip(pygame.Rect((0, 0), bg_rect.size))

            source_w, source_h = background.get_size()
            source_rect = pygame.Rect(
                max(0, math.floor(desired.x * source_w / bg_rect.w)),
                max(0, math.floor(desired.y * source_h / bg_rect.h)),
                0,
                0,
            )
            source_right = min(
                source_w, math.ceil(desired.right * source_w / bg_rect.w))
            source_bottom = min(
                source_h, math.ceil(desired.bottom * source_h / bg_rect.h))
            source_rect.w = max(1, source_right - source_rect.x)
            source_rect.h = max(1, source_bottom - source_rect.y)

            cache_left = round(source_rect.x * bg_rect.w / source_w)
            cache_top = round(source_rect.y * bg_rect.h / source_h)
            cache_right = round(source_rect.right * bg_rect.w / source_w)
            cache_bottom = round(source_rect.bottom * bg_rect.h / source_h)
            cache_rect = pygame.Rect(
                cache_left,
                cache_top,
                max(1, cache_right - cache_left),
                max(1, cache_bottom - cache_top),
            )
            source = background.subsurface(source_rect)
            scaled = pygame.transform.smoothscale(source, cache_rect.size)
            self._map_background_cache = {
                "key": cache_key,
                "rect": cache_rect,
                "surface": scaled,
            }

        screen.blit(
            scaled,
            (bg_rect.x + cache_rect.x, bg_rect.y + cache_rect.y),
        )
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

    def _map_view_active(self):
        return (getattr(self, "left_tab", None) == "maps"
                and getattr(self, "is_map_template", False)
                and self._current_map() is not None)

    def _zoom_canvas(self, direction, pos):
        if getattr(self, "canvas_context", "main") != "main":
            return
        old = max(0.2, float(getattr(self, "canvas_zoom", 1.0)))
        factor = 1.2 if direction > 0 else (1 / 1.2)
        new = max(0.25, min(8.0, old * factor))
        if abs(new - old) < 1e-6:
            return
        inner = getattr(self, "canvas_view_rect", pygame.Rect(0, 0, 1, 1))
        ratio = new / old
        ox = pos[0] - inner.centerx
        oy = pos[1] - inner.centery
        self.canvas_pan[0] = int((self.canvas_pan[0] - ox) * ratio + ox)
        self.canvas_pan[1] = int((self.canvas_pan[1] - oy) * ratio + oy)
        self.canvas_zoom = new
        if abs(new - 1.0) < 1e-6:
            self.canvas_pan = [0, 0]

    def _current_map(self):
        maps = getattr(self, "maps", None)
        idx = getattr(self, "selected_map_index", 0)
        if maps and 0 <= idx < len(maps):
            return maps[idx]
        return None

    def _canvas_size(self):
        if self._map_view_active():
            bg = self._current_map()["assets"].get("Background")
            if bg:
                return bg.get_size()
            dims = self._current_map()["data"]["Datas"].get("Dimensions", {})
            return (dims.get("width") or self.template_size[0], dims.get("height") or self.template_size[1])
        if getattr(self, "canvas_context", "main") == "submenu":
            parent = getattr(self, "submenu_parent", None) or {}
            if parent.get("kind") == "MultipleChoiceItem":
                dims = parent.get("Dimensions") or {}
                if dims.get("w") and dims.get("h"):
                    return (max(1, int(dims.get("w"))), max(1, int(dims.get("h"))))
            background = self._submenu_background_surface()
            if background:
                return background.get_size()
        return self.template_size

    def _canvas_background_surface(self):
        if self._map_view_active():
            return self._current_map()["assets"].get("Background")
        if getattr(self, "canvas_context", "main") == "submenu":
            return self._submenu_background_surface()
        return self.background

    def _canvas_background_color(self):
        if self._map_view_active():
            return {"r": 0, "g": 0, "b": 0}
        if getattr(self, "canvas_context", "main") == "submenu":
            return {"r": 0, "g": 0, "b": 0}
        return self.background_color or {"r": 0, "g": 0, "b": 0}

    def _canvas_background_position(self):
        if self._map_view_active() or getattr(self, "canvas_context", "main") == "submenu":
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

    # ---- generic draggable scrollbars ----------------------------------
    SCROLL_ATTRS = {
        "info": "info_scroll", "items_list": "items_list_scroll",
        "sheet": "sheet_scroll", "picker": "picker_scroll",
        "fonts": "fonts_scroll", "project": "project_scroll",
        "maps_checks": "maps_checks_scroll", "map_data": "map_data_scroll",
        "cond_builder": "cond_builder_scroll", "hide_editor": "hide_editor_scroll",
        "name_picker": "name_picker_scroll", "error_popup": "error_popup_scroll",
        "field_editor": "field_editor_scroll",
    }

    def _register_scrollbar(self, screen, name, track, scroll, max_scroll, content_h, view_h):
        pygame.draw.rect(screen, (40, 46, 62), track)
        if max_scroll <= 0 or content_h <= 0:
            return
        th = max(20, int(track.h * view_h / content_h))
        ty = track.y + int((track.h - th) * scroll / max_scroll)
        thumb = pygame.Rect(track.x, ty, track.w, th)
        pygame.draw.rect(screen, self.COLORS["gold"], thumb)
        self._scrollbars[name] = {"track": track, "thumb": thumb, "max": max_scroll}

    def _start_scrollbar_drag(self, mouse_position, only=None):
        for name, sb in (self._scrollbars or {}).items():
            if only is not None and name != only:
                continue
            if sb["thumb"].collidepoint(mouse_position):
                self.dragging_scrollbar = name
                self.scrollbar_drag_offset = mouse_position[1] - sb["thumb"].y
                self.suppress_next_click = True
                return True
            if sb["track"].collidepoint(mouse_position):
                self.dragging_scrollbar = name
                self.scrollbar_drag_offset = sb["thumb"].h // 2
                self.suppress_next_click = True
                self._update_scrollbar_drag(mouse_position)
                return True
        return False

    def _update_scrollbar_drag(self, mouse_position):
        name = self.dragging_scrollbar
        sb = (self._scrollbars or {}).get(name)
        attr = self.SCROLL_ATTRS.get(name)
        if not sb or not attr:
            return
        track = sb["track"]
        denom = max(1, track.h - sb["thumb"].h)
        frac = (mouse_position[1] - track.y - self.scrollbar_drag_offset) / denom
        frac = max(0.0, min(1.0, frac))
        setattr(self, attr, int(frac * sb["max"]))

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

    def _open_error_popup(self, title, errors):
        self.error_popup_title = str(title or "Error")
        self.error_popup_errors = [str(error) for error in errors]
        self.error_popup_scroll = 0
        self.error_popup_max_scroll = 0
        self.error_popup_copied_until = 0
        self.error_popup_open = True
        self.message = "Save blocked. Review the error details."

    def _close_error_popup(self):
        self.error_popup_open = False
        self.error_popup_buttons = {}
        self.error_popup_scroll = 0
        self.error_popup_max_scroll = 0

    def _error_popup_text(self):
        lines = [self.error_popup_title, ""]
        lines.extend(
            f"{index}. {error}"
            for index, error in enumerate(self.error_popup_errors, start=1)
        )
        return "\n".join(lines)

    def _copy_error_popup(self):
        self._set_prompt_clipboard(self._error_popup_text())
        self.error_popup_copied_until = pygame.time.get_ticks() + 1800
        self.message = "Error details copied to the clipboard."

    def _scroll_error_popup(self, wheel_y):
        self.error_popup_scroll = max(
            0,
            min(
                self.error_popup_max_scroll,
                self.error_popup_scroll - int(wheel_y) * 48,
            ),
        )

    def _wrap_error_popup_text(self, text, max_width, size=15):
        paragraphs = str(text).replace("\r", "").split("\n")
        wrapped = []
        for paragraph in paragraphs:
            if not paragraph:
                wrapped.append("")
                continue
            words = paragraph.split(" ")
            line = ""
            for word in words:
                candidate = word if not line else f"{line} {word}"
                if self._render_ui_text(candidate, size, self.COLORS["line_light"]).get_width() <= max_width:
                    line = candidate
                    continue
                if line:
                    wrapped.append(line)
                    line = ""
                remainder = word
                while remainder and self._render_ui_text(
                        remainder, size, self.COLORS["line_light"]).get_width() > max_width:
                    low, high = 1, len(remainder)
                    while low < high:
                        middle = (low + high + 1) // 2
                        width = self._render_ui_text(
                            remainder[:middle], size, self.COLORS["line_light"]
                        ).get_width()
                        if width <= max_width:
                            low = middle
                        else:
                            high = middle - 1
                    wrapped.append(remainder[:low])
                    remainder = remainder[low:]
                line = remainder
            if line:
                wrapped.append(line)
        return wrapped or [""]

    def _draw_error_popup(self, screen):
        sw, sh = screen.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 195))
        screen.blit(overlay, (0, 0))

        modal_w = min(1000, max(520, sw - 80))
        modal_h = min(700, max(420, sh - 80))
        modal = pygame.Rect(
            (sw - modal_w) // 2,
            (sh - modal_h) // 2,
            modal_w,
            modal_h,
        )
        self._draw_popup(screen, modal, radius=12)
        self.error_popup_buttons = {}

        self._text(
            screen,
            self.error_popup_title,
            (modal.x + 24, modal.y + 18),
            24,
            self.COLORS["gold"],
        )
        count = len(self.error_popup_errors)
        summary = (
            "1 error prevents saving."
            if count == 1 else f"{count} errors prevent saving."
        )
        self._text(
            screen,
            summary,
            (modal.x + 24, modal.y + 52),
            14,
            (255, 150, 150),
        )
        self._text(
            screen,
            "Use the button below or Ctrl+C to copy all details.",
            (modal.x + 24, modal.y + 72),
            12,
            self.COLORS["muted"],
        )

        area = pygame.Rect(
            modal.x + 24,
            modal.y + 102,
            modal.w - 48,
            modal.h - 176,
        )
        self._draw_card(
            screen,
            area,
            (10, 12, 18),
            border_color=(80, 55, 60),
            radius=8,
        )
        text_width = area.w - 38
        groups = []
        for index, error in enumerate(self.error_popup_errors, start=1):
            groups.append(
                self._wrap_error_popup_text(
                    f"{index}. {error}", text_width, size=15
                )
            )
        line_height = 23
        content_h = 18 + sum(len(lines) * line_height + 10 for lines in groups)
        self.error_popup_max_scroll = max(0, content_h - area.h)
        self.error_popup_scroll = max(
            0, min(self.error_popup_scroll, self.error_popup_max_scroll)
        )

        previous_clip = screen.get_clip()
        screen.set_clip(area.inflate(-8, -8))
        y = area.y + 10 - self.error_popup_scroll
        for lines in groups:
            for line in lines:
                self._text(
                    screen,
                    line,
                    (area.x + 12, y),
                    15,
                    self.COLORS["line_light"],
                )
                y += line_height
            y += 10
        screen.set_clip(previous_clip)
        track = pygame.Rect(area.right - 8, area.y + 8, 4, area.h - 16)
        self._register_scrollbar(
            screen,
            "error_popup",
            track,
            self.error_popup_scroll,
            self.error_popup_max_scroll,
            content_h,
            area.h,
        )

        copy_button = pygame.Rect(modal.x + 24, modal.bottom - 52, 170, 32)
        close_button = pygame.Rect(modal.right - 124, modal.bottom - 52, 100, 32)
        self.error_popup_buttons["copy"] = copy_button
        self.error_popup_buttons["close"] = close_button
        copied = pygame.time.get_ticks() < self.error_popup_copied_until
        self._draw_button(
            screen,
            copy_button,
            "Copied!" if copied else "Copy all errors",
            (36, 124, 87),
            hover=self.hover_modal_key == "error_copy",
        )
        self._draw_button(
            screen,
            close_button,
            "Close",
            self.COLORS["red"],
            hover=self.hover_modal_key == "error_close",
        )

