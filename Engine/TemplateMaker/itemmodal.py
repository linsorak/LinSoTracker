import colorsys
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


class ItemModalMixin:
    def _draw_item_modal(self, screen):
        item = self._selected_item()
        if not item:
            self.item_modal_open = False
            return

        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        pad = 24
        modal_w = min(760, screen.get_width() - 80)
        modal_h = min(720, screen.get_height() - 40)
        rect = pygame.Rect((screen.get_width() - modal_w) // 2, (screen.get_height() - modal_h) // 2, modal_w, modal_h)
        self.item_modal_rect = rect
        self._draw_card(screen, rect, (16, 19, 28), border_color=self.COLORS["gold"])
        self.modal_buttons = {}

        # --- Header (no strip, clean) ---
        self._text(screen, "ITEM DETAILS  (close to cancel)", (rect.x + pad, rect.y + 18), 13, self.COLORS["muted"])
        name = item["name"] if len(item["name"]) <= 28 else item["name"][:25] + "..."
        self._text(screen, name, (rect.x + pad, rect.y + 36), 26, self.COLORS["gold"])
        header_bottom = rect.y + 76
        pygame.draw.line(screen, self.COLORS["line"], (rect.x + pad, header_bottom), (rect.right - pad, header_bottom), 1)

        close_rect = pygame.Rect(rect.right - pad - 32, rect.y + 22, 32, 32)
        self.modal_buttons["close"] = close_rect
        self._draw_button(screen, close_rect, "X", self.COLORS["red"], hover=(self.hover_modal_key == "close"))
        save_rect = pygame.Rect(close_rect.x - 110, rect.y + 22, 100, 32)
        self.modal_buttons["save"] = save_rect
        self._draw_button(screen, save_rect, "Save", (36, 124, 87), hover=(self.hover_modal_key == "save"))

        # --- Details card (preview + properties) ---
        det_rect = pygame.Rect(rect.x + pad, header_bottom + pad, rect.w - pad * 2, 234)
        self._draw_card(screen, det_rect, (12, 15, 22), border_color=(56, 62, 76))

        # Interactive live preview (click to simulate in-tracker behaviour)
        large_preview = item.get("kind") in ("EditableBox", "TimerItem", "SubMenuItem")
        wide_preview = item.get("kind") in ("CountItem", "AlternateCountItem", "LabelItem")
        preview_w = 238 if large_preview else (192 if wide_preview else 96)
        preview_h = 178 if large_preview else 96
        icon_rect = pygame.Rect(det_rect.x + 16, det_rect.y + 16, preview_w, preview_h)
        self._draw_card(screen, icon_rect, (8, 9, 13), border_color=(56, 62, 76))
        self.modal_buttons["preview"] = icon_rect
        self._draw_item_preview(screen, icon_rect, item)
        preview_hint = "Actual size preview" if large_preview else "L/R/wheel to test"
        self._text(screen, preview_hint, (icon_rect.x - 2, icon_rect.bottom + 4), 11, self.COLORS["muted"])

        details = [
            ("Id", item["id"]),
            ("Name", item["name"]),
            ("Type", item.get("kind", "Item")),
            ("Position", f"x {item['x']} / y {item['y']}"),
            ("Sprite", "optional" if item.get("kind") in self.SPRITE_OPTIONAL_KINDS and not item.get("sheet")
             else f"row {item['row']} / column {item['column']}"),
            ("Active", item.get("isActive", False)),
            ("Opacity", item.get("opacity", 0.5)),
            ("Hint", item.get("hint") or "None"),
        ]
        info_x = icon_rect.right + 28
        value_x = info_x + 110
        info_y = det_rect.y + 18
        row_h = 24 if large_preview else 26
        for label, value in details:
            self._text(screen, label, (info_x, info_y), 16, self.COLORS["muted"])
            display = str(value)
            if len(display) > 40:
                display = display[:37] + "..."
            self._text(screen, display, (value_x, info_y), 16, self.COLORS["line_light"])
            info_y += row_h

        # --- Common action buttons ---
        actions = [
            ("rename", "Name"),
            ("kind", "Type"),
            ("position", "X / Y"),
            ("place", "Place"),
            ("sprite", "Sprite"),
            ("hint", "Hint"),
            ("active", "Active"),
            ("opacity", "Opacity"),
            ("delete", "Delete"),
        ]
        btn_w = 104
        btn_h = 34
        gap = 10
        x = rect.x + pad
        y = det_rect.bottom + pad
        for key, label in actions:
            if x + btn_w > rect.right - pad:
                x = rect.x + pad
                y += btn_h + gap
            button = pygame.Rect(x, y, btn_w, btn_h)
            self.modal_buttons[key] = button
            color = self.COLORS["red"] if key == "delete" else self.COLORS["button"]
            self._draw_button(screen, button, label, color, hover=(self.hover_modal_key == key))
            x += btn_w + gap
        y += btn_h + pad

        kind = item.get("kind", "Item")
        is_evo = kind in self.EVOLUTION_KINDS
        lower = pygame.Rect(rect.x + pad, y, rect.w - pad * 2, rect.bottom - y - pad)

        # Kind-specific properties (left column) + children for evolution (right column)
        if is_evo:
            prop_w = (lower.w - pad) // 2
            prop_rect = pygame.Rect(lower.x, lower.y, prop_w, lower.h)
            child_area = pygame.Rect(prop_rect.right + pad, lower.y, lower.w - prop_w - pad, lower.h)
        else:
            prop_rect = lower
            child_area = None

        self._draw_card(screen, prop_rect, (12, 15, 22), border_color=(56, 62, 76))
        self._text(screen, f"{kind} PROPERTIES", (prop_rect.x + 14, prop_rect.y + 12), 13, self.COLORS["gold"])
        specs = self._kind_fields(kind)
        ncols = 1 if is_evo else 2
        col_w = (prop_rect.w - 20 - (ncols - 1) * 10) // ncols
        col_top = prop_rect.y + 38
        col_bottom = prop_rect.bottom - 6
        for index, spec in enumerate(specs):
            col = index % ncols
            slot = index // ncols
            fy = col_top + slot * 42
            if fy + 38 > col_bottom:
                continue
            fx = prop_rect.x + 10 + col * (col_w + 10)
            frow = pygame.Rect(fx, fy, col_w, 36)
            hovered = self.hover_modal_key == f"field_{spec['key']}"
            pygame.draw.rect(screen, self.COLORS["panel_alt"] if hovered else (20, 24, 34), frow)
            pygame.draw.rect(screen, (56, 62, 76), frow, 1)
            self.modal_buttons[f"field_{spec['key']}"] = frow
            self._text(screen, spec["label"], (frow.x + 8, frow.y + 3), 12, self.COLORS["muted"])
            self._text(screen, self._format_field_value(item, spec), (frow.x + 8, frow.y + 18), 14, self.COLORS["line_light"])

        if child_area is not None:
            self._draw_card(screen, child_area, (12, 15, 22), border_color=(56, 62, 76))
            self._text(screen, "NEXTITEMS", (child_area.x + 14, child_area.y + 12), 13, self.COLORS["gold"])
            add_child_rect = pygame.Rect(child_area.right - 104, child_area.y + 8, 94, 28)
            self.modal_buttons["add_child"] = add_child_rect
            self._draw_button(screen, add_child_rect, "Add", (36, 124, 87), hover=(self.hover_modal_key == "add_child"))
            children = item.get("children", [])
            if not children:
                self._text(screen, "No child yet.", (child_area.x + 14, child_area.y + 44), self.font_size, self.COLORS["muted"])
            else:
                row_y = child_area.y + 44
                row_h = 40
                max_rows = max(1, (child_area.bottom - row_y - 6) // row_h)
                for index, child in enumerate(children[:max_rows]):
                    crow = pygame.Rect(child_area.x + 10, row_y, child_area.w - 20, row_h - 4)
                    pygame.draw.rect(screen, (20, 24, 34), crow)
                    pygame.draw.rect(screen, (56, 62, 76), crow, 1)
                    thumb = self._get_icon_surface(child["row"], child["column"], child.get("sheet"))
                    if thumb:
                        screen.blit(pygame.transform.smoothscale(thumb, (26, 26)), (crow.x + 5, crow.y + 5))
                    cname = child["name"]
                    if len(cname) > 11:
                        cname = cname[:10] + "..."
                    self._text(screen, f"{index + 1}. {cname}", (crow.x + 38, crow.y + 9), 14, self.COLORS["line_light"])
                    edit_rect = pygame.Rect(crow.right - 6 - 50, crow.y + 5, 50, crow.h - 10)
                    del_rect = pygame.Rect(edit_rect.x - 40, crow.y + 5, 36, crow.h - 10)
                    self.modal_buttons[f"child_edit_{index}"] = edit_rect
                    self.modal_buttons[f"remove_child_{index}"] = del_rect
                    self._draw_button(screen, edit_rect, "Edit", self.COLORS["button"], hover=(self.hover_modal_key == f"child_edit_{index}"))
                    self._draw_button(screen, del_rect, "Del", self.COLORS["red"], hover=(self.hover_modal_key == f"remove_child_{index}"))
                    row_y += row_h

        # --- Kind picker overlay (list of item types) ---
        if self.kind_picker_open:
            current = item.get("kind", "Item")
            opt_h = 34
            list_h = len(self.ITEM_KINDS) * opt_h + 16
            pk = pygame.Rect(rect.centerx - 150, rect.y + 90, 300, min(list_h, rect.h - 120))
            self._draw_card(screen, pk, (20, 24, 34), border_color=self.COLORS["gold"])
            self._text(screen, "CHOOSE TYPE", (pk.x + 12, pk.y + 8), 13, self.COLORS["gold"])
            oy = pk.y + 30
            for kind in self.ITEM_KINDS:
                if oy + opt_h > pk.bottom - 6:
                    break
                orow = pygame.Rect(pk.x + 8, oy, pk.w - 16, opt_h - 4)
                self.modal_buttons[f"kindopt_{kind}"] = orow
                sel = kind == current
                hovered = self.hover_modal_key == f"kindopt_{kind}"
                if sel:
                    pygame.draw.rect(screen, (40, 46, 62), orow)
                    pygame.draw.rect(screen, self.COLORS["gold"], orow, 1)
                elif hovered:
                    pygame.draw.rect(screen, self.COLORS["panel_alt"], orow)
                self._text(screen, kind, (orow.x + 10, orow.y + 5), 15,
                           self.COLORS["gold"] if sel else self.COLORS["line_light"])
                oy += opt_h

        # --- Child (NextItem) editor overlay ---
        children = item.get("children", [])
        if self.child_edit_index is not None and 0 <= self.child_edit_index < len(children):
            child = children[self.child_edit_index]
            ce = pygame.Rect(rect.centerx - 170, rect.y + 110, 340, 290)
            self._draw_card(screen, ce, (20, 24, 34), border_color=self.COLORS["gold"])
            self._text(screen, f"NEXTITEM {self.child_edit_index + 1}", (ce.x + 14, ce.y + 12), 13, self.COLORS["gold"])
            ce_close = pygame.Rect(ce.right - 38, ce.y + 10, 28, 28)
            self.modal_buttons["ce_close"] = ce_close
            self._draw_button(screen, ce_close, "X", self.COLORS["red"], hover=(self.hover_modal_key == "ce_close"))

            # Sprite preview
            thumb = self._get_icon_surface(child["row"], child["column"], child.get("sheet"))
            tr = pygame.Rect(ce.x + 16, ce.y + 44, 60, 60)
            self._draw_card(screen, tr, self.COLORS["panel_alt"], border_color=(56, 62, 76))
            if thumb:
                screen.blit(pygame.transform.smoothscale(thumb, (48, 48)), (tr.centerx - 24, tr.centery - 24))
            spr_btn = pygame.Rect(tr.right + 14, tr.y + 16, ce.right - 14 - (tr.right + 14), 30)
            self.modal_buttons["ce_sprite"] = spr_btn
            self._draw_button(screen, spr_btn, "Change sprite", (36, 124, 87), hover=(self.hover_modal_key == "ce_sprite"))

            rows = [
                ("ce_name", "Name", child.get("name") or "-"),
                ("ce_label", "Label", child.get("label") or "-"),
                ("ce_alt", "Alt label", child.get("alt_label") or "-"),
            ]
            ry = tr.bottom + 14
            for bkey, label, value in rows:
                row = pygame.Rect(ce.x + 16, ry, ce.w - 32, 38)
                self.modal_buttons[bkey] = row
                hovered = self.hover_modal_key == bkey
                pygame.draw.rect(screen, self.COLORS["panel_alt"] if hovered else (12, 15, 22), row)
                pygame.draw.rect(screen, (56, 62, 76), row, 1)
                self._text(screen, label, (row.x + 10, row.y + 4), 12, self.COLORS["muted"])
                disp = str(value)
                if len(disp) > 30:
                    disp = disp[:27] + "..."
                self._text(screen, disp, (row.x + 10, row.y + 19), 14, self.COLORS["line_light"])
                ry += 44

        if self.field_editor_open and self.field_editor_spec:
            self._draw_field_editor(screen, rect)

    def _format_field_value(self, item, spec):
        value = self._get_field_value(item, spec)
        if spec["type"] == "sprite":
            if value:
                return f"{value.get('sheet')} r{value.get('row')} c{value.get('column')}"
            return "same as item"
        if spec["type"] == "bool":
            return "Yes" if value else "No"
        if spec["type"] in ("list", "list_editor"):
            value = value or []
            text = ", ".join(str(v) for v in value)
            return text[:24] + "..." if len(text) > 24 else (text or "(empty)")
        if spec["type"] == "rect":
            value = value or {}
            if "h" in value:
                return f"x{value.get('x', 0)} y{value.get('y', 0)} w{value.get('w', 0)} h{value.get('h', 0)}"
            return f"w{value.get('w', 0)} h{value.get('h', 0)}"
        if spec["type"] == "color":
            if not value:
                return "None"
            return f"{value.get('r', 0)}, {value.get('g', 0)}, {value.get('b', 0)}"
        if spec["type"] in ("json", "jsonnull"):
            if value in (None, "", [], {}):
                return "None" if spec["type"] == "jsonnull" else "{}"
            text = json.dumps(value, ensure_ascii=False)
            return text[:26] + "..." if len(text) > 26 else text
        if value in (None, ""):
            return "None"
        return str(value)

    def _get_field_value(self, item, spec):
        current = item
        for part in spec["key"].split("."):
            if not isinstance(current, dict) or part not in current:
                return copy.deepcopy(spec["default"])
            current = current[part]
        return current

    def _set_field_value(self, item, key, value):
        parts = key.split(".")
        current = item
        for part in parts[:-1]:
            child = current.get(part)
            if not isinstance(child, dict):
                child = {}
                current[part] = child
            current = child
        current[parts[-1]] = value

    def _field_editor_parts(self):
        spec = self.field_editor_spec
        if not spec:
            return []
        value = self._get_field_value(self.field_editor_item, spec)
        if spec["type"] == "rect":
            value = value or {}
            keys = spec.get("keys") or (["x", "y", "w", "h"] if ("x" in value or "y" in value) else ["w", "h"])
            return [(key, str(value.get(key, 0 if key in ("x", "y") else 1))) for key in keys]
        if spec["type"] == "color":
            value = value or {}
            return [(key, str(value.get(key, 0))) for key in ("r", "g", "b")]
        if spec["type"] == "list_editor":
            return [(str(index), str(value)) for index, value in enumerate(value or [])]
        return []

    def _draw_field_editor(self, screen, parent_rect):
        spec = self.field_editor_spec
        item = self.field_editor_item
        if not spec or item is None:
            self._close_field_editor()
            return
        self.modal_buttons = {}
        parts = self._field_editor_parts()
        list_mode = spec["type"] == "list_editor"
        rows_to_draw = parts[:6] if list_mode else parts
        popup_h = 98 + len(rows_to_draw) * 44 + (34 if list_mode else 0)
        popup = pygame.Rect(parent_rect.centerx - 210 if list_mode else parent_rect.centerx - 180,
                            parent_rect.y + 96, 420 if list_mode else 360, popup_h)
        self._draw_card(screen, popup, (20, 24, 34), border_color=self.COLORS["gold"])
        self._text(screen, spec["label"].upper(), (popup.x + 14, popup.y + 12), 13, self.COLORS["gold"])
        close_rect = pygame.Rect(popup.right - 38, popup.y + 10, 28, 28)
        self.modal_buttons["fe_close"] = close_rect
        self._draw_button(screen, close_rect, "X", self.COLORS["red"], hover=(self.hover_modal_key == "fe_close"))

        y = popup.y + 48
        if list_mode:
            add_rect = pygame.Rect(popup.x + 16, y, 96, 30)
            self.modal_buttons["fe_add"] = add_rect
            self._draw_button(screen, add_rect, "Add", (36, 124, 87), hover=(self.hover_modal_key == "fe_add"))
            count_text = f"{len(parts)} entry" if len(parts) == 1 else f"{len(parts)} entries"
            self._text(screen, count_text, (add_rect.right + 12, y + 7), 14, self.COLORS["muted"])
            y += 42
            if not parts:
                self._text(screen, "No entry yet.", (popup.x + 16, y + 8), 15, self.COLORS["muted"])
                return

        for key, value in rows_to_draw:
            row = pygame.Rect(popup.x + 16, y, popup.w - 32, 36)
            bkey = f"fe_{key}"
            hovered = self.hover_modal_key == bkey
            pygame.draw.rect(screen, self.COLORS["panel_alt"] if hovered else (12, 15, 22), row)
            pygame.draw.rect(screen, (56, 62, 76), row, 1)
            if list_mode:
                edit_rect = pygame.Rect(row.right - 102, row.y + 5, 56, 26)
                del_rect = pygame.Rect(row.right - 42, row.y + 5, 36, 26)
                self.modal_buttons[f"fe_edit_{key}"] = edit_rect
                self.modal_buttons[f"fe_del_{key}"] = del_rect
                display = value if len(value) <= 28 else value[:25] + "..."
                self._text(screen, f"{int(key) + 1}. {display}", (row.x + 10, row.y + 8), 15, self.COLORS["line_light"])
                self._draw_button(screen, edit_rect, "Edit", self.COLORS["button"],
                                  hover=(self.hover_modal_key == f"fe_edit_{key}"))
                self._draw_button(screen, del_rect, "Del", self.COLORS["red"],
                                  hover=(self.hover_modal_key == f"fe_del_{key}"))
            else:
                self.modal_buttons[bkey] = row
                self._text(screen, key.upper(), (row.x + 10, row.y + 7), 15, self.COLORS["muted"])
                self._text(screen, value, (row.right - 92, row.y + 7), 15, self.COLORS["line_light"])
            y += 44
        if list_mode and len(parts) > len(rows_to_draw):
            self._text(screen, f"+ {len(parts) - len(rows_to_draw)} more in JSON", (popup.x + 16, y + 4),
                       13, self.COLORS["muted"])

    def _open_color_picker(self, title, initial, callback):
        initial = initial or {}
        self.color_picker_open = True
        self.color_picker_title = title
        self.color_picker_value = {
            "r": max(0, min(255, int(initial.get("r", 255)))),
            "g": max(0, min(255, int(initial.get("g", 255)))),
            "b": max(0, min(255, int(initial.get("b", 255)))),
        }
        self.color_picker_callback = callback
        self.color_picker_buttons = {}

    def _apply_color_picker(self):
        if callable(self.color_picker_callback):
            self.color_picker_callback(dict(self.color_picker_value))

    def _close_color_picker(self):
        self.color_picker_open = False
        self.color_picker_callback = None
        self.color_picker_buttons = {}

    @staticmethod
    def _color_picker_tuple(color):
        return color.get("r", 0), color.get("g", 0), color.get("b", 0)

    def _draw_color_picker(self, screen):
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        screen.blit(overlay, (0, 0))

        rect = pygame.Rect(screen.get_width() // 2 - 260, screen.get_height() // 2 - 190, 520, 380)
        self._draw_card(screen, rect, (20, 24, 34), border_color=self.COLORS["gold"])
        self.color_picker_buttons = {}
        self._text(screen, self.color_picker_title.upper(), (rect.x + 18, rect.y + 14), 13, self.COLORS["gold"])

        close_rect = pygame.Rect(rect.right - 42, rect.y + 12, 30, 30)
        self.color_picker_buttons["close"] = close_rect
        self._draw_button(screen, close_rect, "X", self.COLORS["red"], hover=False)

        wheel_size = 172
        wheel_rect = pygame.Rect(rect.x + 28, rect.y + 58, wheel_size, wheel_size)
        self.color_picker_wheel_rect = wheel_rect
        self._draw_color_wheel(screen, wheel_rect)

        current = self._color_picker_tuple(self.color_picker_value)
        preview = pygame.Rect(wheel_rect.x, wheel_rect.bottom + 18, wheel_rect.w, 44)
        pygame.draw.rect(screen, current, preview)
        pygame.draw.rect(screen, self.COLORS["line_light"], preview, 1)
        self._text_center(screen, f"RGB {current[0]}, {current[1]}, {current[2]}", preview, 14,
                          (0, 0, 0) if sum(current) > 382 else self.COLORS["line_light"])

        x = wheel_rect.right + 32
        y = wheel_rect.y + 4
        for key in ("r", "g", "b"):
            row = pygame.Rect(x, y, rect.right - x - 28, 44)
            self.color_picker_buttons[f"rgb_{key}"] = row
            pygame.draw.rect(screen, self.COLORS["panel_alt"], row)
            pygame.draw.rect(screen, (56, 62, 76), row, 1)
            self._text(screen, key.upper(), (row.x + 14, row.y + 12), 16, self.COLORS["muted"])
            self._text(screen, str(self.color_picker_value.get(key, 0)), (row.right - 70, row.y + 12),
                       16, self.COLORS["line_light"])
            y += 56

        hint_y = y + 10
        self._text(screen, "Wheel: hue + saturation", (x, hint_y), 14, self.COLORS["muted"])
        self._text(screen, "Rows: exact RGB values", (x, hint_y + 24), 14, self.COLORS["muted"])
        self._text(screen, "Esc or X to close", (x, hint_y + 48), 13, self.COLORS["muted"])

    def _draw_color_wheel(self, screen, rect):
        center = rect.center
        radius = rect.w // 2
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        for y in range(rect.h):
            for x in range(rect.w):
                dx = x - radius
                dy = y - radius
                dist = math.hypot(dx, dy)
                if dist <= radius:
                    hue = (math.atan2(dy, dx) / (2 * math.pi)) % 1.0
                    sat = dist / radius
                    r, g, b = colorsys.hsv_to_rgb(hue, sat, 1.0)
                    surface.set_at((x, y), (int(r * 255), int(g * 255), int(b * 255), 255))
        screen.blit(surface, rect)
        pygame.draw.circle(screen, self.COLORS["line_light"], center, radius, 1)

        r, g, b = self._color_picker_tuple(self.color_picker_value)
        h, s, _ = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        angle = h * 2 * math.pi
        marker = (
            int(center[0] + math.cos(angle) * s * radius),
            int(center[1] + math.sin(angle) * s * radius),
        )
        pygame.draw.circle(screen, (0, 0, 0), marker, 6, 2)
        pygame.draw.circle(screen, (255, 255, 255), marker, 4, 1)

    def _handle_color_picker_click(self, mouse_position):
        for key, rect in self.color_picker_buttons.items():
            if not rect.collidepoint(mouse_position):
                continue
            if key == "close":
                self._close_color_picker()
                return True
            if key.startswith("rgb_"):
                channel = key[-1]
                def cb(value, ch=channel):
                    if value is None:
                        return
                    self.color_picker_value[ch] = max(0, min(255, int(value)))
                    self._apply_color_picker()
                    self.message = f"{self.color_picker_title} updated."
                self._open_text_prompt(f"{self.color_picker_title} {channel.upper()}",
                                       self.color_picker_value.get(channel, 0), cb, kind="int",
                                       allow_empty=False, label=f"{channel.upper()} (0-255):", minvalue=0)
                return True

        if self.color_picker_wheel_rect.collidepoint(mouse_position):
            center = self.color_picker_wheel_rect.center
            radius = self.color_picker_wheel_rect.w // 2
            dx = mouse_position[0] - center[0]
            dy = mouse_position[1] - center[1]
            dist = math.hypot(dx, dy)
            if dist <= radius:
                hue = (math.atan2(dy, dx) / (2 * math.pi)) % 1.0
                sat = dist / radius
                r, g, b = colorsys.hsv_to_rgb(hue, sat, 1.0)
                self.color_picker_value = {"r": int(r * 255), "g": int(g * 255), "b": int(b * 255)}
                self._apply_color_picker()
                self.message = f"{self.color_picker_title} updated."
                return True

        self._close_color_picker()
        return True

    # --- Live item preview (simulates in-tracker behaviour) ---
    def _selected_item(self):
        # While the modal is open, edits target the draft copy (cancellable)
        if self.item_modal_open and self.modal_item is not None:
            return self.modal_item
        if self.selected_item_index is None:
            return None
        if self.selected_item_index < 0 or self.selected_item_index >= len(self.placed_items):
            self.selected_item_index = None
            return None
        return self.placed_items[self.selected_item_index]

    def _open_item_modal(self, index):
        self.selected_item_index = index
        self.modal_item_index = index
        self.modal_item = copy.deepcopy(self.placed_items[index])
        self.kind_picker_open = False
        self.item_modal_open = True

    def _close_item_modal(self, save):
        if save and self.modal_item is not None and self.modal_item_index is not None \
                and 0 <= self.modal_item_index < len(self.placed_items):
            for transient in ("screen_rect", "_preview", "_component", "_comp_sig"):
                self.modal_item.pop(transient, None)
            self.placed_items[self.modal_item_index] = self.modal_item
            self.message = f"Saved {self.modal_item['name']}."
        else:
            self.message = "Changes discarded."
        self.item_modal_open = False
        self.kind_picker_open = False
        self._close_field_editor()
        self.position_pick_mode = False
        self.child_edit_index = None
        self.modal_item = None
        self.modal_item_index = None

    def _get_item_index_at(self, mouse_position):
        for index in range(len(self.placed_items) - 1, -1, -1):
            rect = self.placed_items[index].get("screen_rect")
            if rect and rect.collidepoint(mouse_position):
                return index
        return None

    def _move_item_to_mouse(self, index, mouse_position):
        if index < 0 or index >= len(self.placed_items) or not self.last_bg_rect.w:
            return
        x = mouse_position[0] - self.drag_offset[0]
        y = mouse_position[1] - self.drag_offset[1]
        x = max(self.last_bg_rect.x, min(x, self.last_bg_rect.right - 1))
        y = max(self.last_bg_rect.y, min(y, self.last_bg_rect.bottom - 1))
        scale = self.template_size[0] / self.last_bg_rect.w
        self.placed_items[index]["x"] = int((x - self.last_bg_rect.x) * scale)
        self.placed_items[index]["y"] = int((y - self.last_bg_rect.y) * scale)

    def _handle_property_button(self, key):
        if key == "rename":
            self._rename_selected_item()
        elif key == "kind":
            self._cycle_selected_kind()
        elif key == "position":
            self._edit_selected_position()
        elif key == "sprite":
            self._edit_selected_sprite()
        elif key == "delete":
            self._delete_selected_item()

    def _close_field_editor(self):
        self.field_editor_open = False
        self.field_editor_spec = None
        self.field_editor_item = None
        self.field_editor_callback = None

    def _notify_field_editor_changed(self):
        if callable(self.field_editor_callback):
            self.field_editor_callback()

    def _handle_field_editor_click(self, mouse_position):
        if self.field_editor_open:
            for key, rect in self.modal_buttons.items():
                if not rect.collidepoint(mouse_position):
                    continue
                if key == "fe_close":
                    self._close_field_editor()
                    return True
                if key == "fe_add":
                    self._add_list_editor_value()
                    return True
                if key.startswith("fe_edit_"):
                    self._edit_list_editor_value(int(key.rsplit("_", 1)[1]))
                    return True
                if key.startswith("fe_del_"):
                    self._delete_list_editor_value(int(key.rsplit("_", 1)[1]))
                    return True
                if key.startswith("fe_"):
                    self._edit_field_editor_part(key[len("fe_"):])
                    return True
            self._close_field_editor()
            return True
        return False

    def _handle_modal_click(self, mouse_position):
        if self.field_editor_open:
            self._handle_field_editor_click(mouse_position)
            return
        # Kind picker overlay takes priority while open
        if self.kind_picker_open:
            for key, rect in self.modal_buttons.items():
                if key.startswith("kindopt_") and rect.collidepoint(mouse_position):
                    self._set_selected_kind(key[len("kindopt_"):])
                    self.kind_picker_open = False
                    return
            self.kind_picker_open = False
            return
        # Child editor overlay takes priority while open
        if self.child_edit_index is not None:
            idx = self.child_edit_index
            for key, rect in self.modal_buttons.items():
                if not rect.collidepoint(mouse_position):
                    continue
                if key == "ce_close":
                    self.child_edit_index = None
                elif key == "ce_sprite":
                    self._pick_child_sprite(idx)
                elif key == "ce_name":
                    self._rename_child(idx)
                elif key == "ce_label":
                    self._edit_child_text(idx, "label", "Label")
                elif key == "ce_alt":
                    self._edit_child_text(idx, "alt_label", "Alternative label")
                return
            self.child_edit_index = None
            return
        for key, rect in self.modal_buttons.items():
            if not rect.collidepoint(mouse_position):
                continue
            if key == "close":
                self._close_item_modal(save=False)
            elif key == "save":
                self._close_item_modal(save=True)
            elif key == "preview":
                self._advance_preview(self._selected_item())
            elif key == "rename":
                self._rename_selected_item()
            elif key == "kind":
                self.kind_picker_open = True
            elif key == "position":
                self._edit_selected_position()
            elif key == "place":
                self.position_pick_mode = True
                self.message = "Click on the canvas to set the item position (Esc to cancel)."
            elif key == "sprite":
                self._pick_item_sprite()
            elif key == "hint":
                self._edit_selected_hint()
            elif key == "active":
                self._toggle_selected_active()
            elif key == "opacity":
                self._edit_selected_opacity()
            elif key == "add_child":
                self._add_child_to_selected()
            elif key.startswith("field_"):
                self._edit_field(key[len("field_"):])
            elif key.startswith("child_edit_"):
                try:
                    self.child_edit_index = int(key.rsplit("_", 1)[1])
                except ValueError:
                    pass
            elif key.startswith("remove_child_"):
                try:
                    self._remove_child_from_selected(int(key.rsplit("_", 1)[1]))
                except ValueError:
                    pass
            elif key.startswith("sprite_child_"):
                try:
                    self._pick_child_sprite(int(key.rsplit("_", 1)[1]))
                except ValueError:
                    pass
            elif key.startswith("rename_child_"):
                try:
                    self._rename_child(int(key.rsplit("_", 1)[1]))
                except ValueError:
                    pass
            elif key.startswith("label_child_"):
                try:
                    self._edit_child_text(int(key.rsplit("_", 1)[1]), "label", "Label")
                except ValueError:
                    pass
            elif key.startswith("altlabel_child_"):
                try:
                    self._edit_child_text(int(key.rsplit("_", 1)[1]), "alt_label", "Alternative label")
                except ValueError:
                    pass
            elif key == "delete":
                if self.modal_item_index is not None and 0 <= self.modal_item_index < len(self.placed_items):
                    self.placed_items.pop(self.modal_item_index)
                    for i, it in enumerate(self.placed_items, start=1):
                        it["id"] = i
                    self.selected_item_index = None
                self._close_item_modal(save=False)
                self.message = "Item deleted."
            return
        # Click on empty modal area: keep open. Only close when clicking outside.
        if not self.item_modal_rect.collidepoint(mouse_position):
            self._close_item_modal(save=False)

    def _pick_item_sprite(self):
        item = self._selected_item()
        if not item:
            return

        def apply(sheet, row, column, it=item):
            it["sheet"] = sheet
            it["row"] = row
            it["column"] = column
            self.message = f"Sprite set to {sheet} r{row} c{column}."
        self._open_sprite_picker("Choose item sprite", apply)

    def _pick_child_sprite(self, index):
        item = self._selected_item()
        if not item:
            return
        children = item.get("children", [])
        if not (0 <= index < len(children)):
            return
        child = children[index]

        def apply(sheet, row, column, ch=child):
            ch["sheet"] = sheet
            ch["row"] = row
            ch["column"] = column
            self.message = f"{ch['name']} sprite set to {sheet} r{row} c{column}."
        self._open_sprite_picker(f"Choose NextItem {index + 1} sprite", apply)

    def _set_selected_kind(self, kind):
        item = self._selected_item()
        if not item or kind not in self.ITEM_KINDS:
            return
        item["kind"] = kind
        self._ensure_kind_defaults(item)
        if kind not in self.SPRITE_OPTIONAL_KINDS:
            self._ensure_item_sprite(item)
        self.message = f"Type set to {kind}."

    def _edit_field(self, field_key):
        item = self._selected_item()
        if not item:
            return
        spec = next((s for s in self._kind_fields(item.get("kind", "Item")) if s["key"] == field_key), None)
        if not spec:
            return
        ftype = spec["type"]
        current = self._get_field_value(item, spec)
        label = spec["label"]
        if ftype == "bool":
            self._set_field_value(item, field_key, not bool(current))
            self.message = f"{label} updated."
        elif ftype in ("int", "float"):
            def cb(value, it=item, fk=field_key, lbl=label):
                if value is None:
                    return
                self._set_field_value(it, fk, value)
                self.message = f"{lbl} updated."
            self._open_text_prompt(label, current if current is not None else 0, cb, kind=ftype, label=f"{label}:")
        elif ftype == "list":
            def cb(text, it=item, fk=field_key, lbl=label):
                self._set_field_value(it, fk, [v.strip() for v in (text or "").split(",") if v.strip() != ""])
                self.message = f"{lbl} updated."
            self._open_text_prompt(label, ", ".join(str(v) for v in (current or [])), cb, label="Comma separated values:")
        elif ftype == "list_editor":
            self.field_editor_open = True
            self.field_editor_spec = spec
            self.field_editor_item = item
            self.field_editor_callback = None
        elif ftype == "rect":
            self.field_editor_open = True
            self.field_editor_spec = spec
            self.field_editor_item = item
            self.field_editor_callback = None
        elif ftype == "color":
            def apply_color(color, it=item, fk=field_key, lbl=label):
                self._set_field_value(it, fk, color)
                self.message = f"{lbl} updated."
            self._open_color_picker(label, current or spec["default"], apply_color)
        elif ftype in ("json", "jsonnull"):
            def cb(text, it=item, fk=field_key, lbl=label, ft=ftype):
                raw = (text or "").strip()
                if raw == "" and ft == "jsonnull":
                    self._set_field_value(it, fk, None)
                    self.message = f"{lbl} cleared."
                    return
                try:
                    self._set_field_value(it, fk, json.loads(raw) if raw else {})
                    self.message = f"{lbl} updated."
                except json.JSONDecodeError as exc:
                    self._open_text_prompt(lbl, raw, cb, label=f"{lbl}:")
                    self.prompt_error = f"Invalid JSON: {exc.msg}"
            initial = "" if current is None else json.dumps(current, ensure_ascii=False)
            self._open_text_prompt(label, initial, cb, label=f"{label}:")
        elif ftype == "sprite":
            def apply(sheet, row, column, it=item, fk=field_key, lbl=label):
                self._set_field_value(it, fk, {"sheet": sheet, "row": row, "column": column})
                self.message = f"{lbl} set to {sheet} r{row} c{column}."
            self._open_sprite_picker(label, apply)
        else:  # str / strnull
            def cb(text, it=item, fk=field_key, lbl=label, ft=ftype):
                self._set_field_value(it, fk, text if text not in (None, "") else (None if ft == "strnull" else ""))
                self.message = f"{lbl} updated."
            self._open_text_prompt(label, str(current or ""), cb, label=f"{label}:")

    def _edit_field_editor_part(self, part):
        spec = self.field_editor_spec
        item = self.field_editor_item
        if not spec or item is None:
            return
        current = self._get_field_value(item, spec) or {}
        if spec["type"] == "color":
            label = f"{spec['label']} {part}"
            def cb(value, it=item, sp=spec, key=part):
                if value is None:
                    return
                data = dict(self._get_field_value(it, sp) or {})
                data[key] = max(0, min(255, int(value)))
                self._set_field_value(it, sp["key"], data)
                self._notify_field_editor_changed()
                self.message = f"{sp['label']} updated."
            self._open_text_prompt(label, current.get(part, 0), cb, kind="int",
                                   allow_empty=False, label=f"{part} (0-255):", minvalue=0)
            return

        label = f"{spec['label']} {part}"
        minvalues = spec.get("min", {})
        minvalue = minvalues.get(part) if part in minvalues else (0 if part in ("x", "y") else 1)
        def cb(value, it=item, sp=spec, key=part):
            if value is None:
                return
            data = dict(self._get_field_value(it, sp) or {})
            data[key] = int(value)
            self._set_field_value(it, sp["key"], data)
            self._notify_field_editor_changed()
            self.message = f"{sp['label']} updated."
        self._open_text_prompt(label, current.get(part, 0 if part in ("x", "y") else 1), cb,
                               kind="int", allow_empty=False, label=f"{part}:", minvalue=minvalue)

    def _add_list_editor_value(self):
        spec = self.field_editor_spec
        item = self.field_editor_item
        if not spec or item is None:
            return
        def cb(value, it=item, sp=spec):
            if value in (None, ""):
                return
            values = list(self._get_field_value(it, sp) or [])
            values.append(value)
            self._set_field_value(it, sp["key"], values)
            self._notify_field_editor_changed()
            self.message = f"{sp['label']} added."
        self._open_text_prompt(f"Add {spec['label']}", "", cb, allow_empty=False, label="Value:")

    def _edit_list_editor_value(self, index):
        spec = self.field_editor_spec
        item = self.field_editor_item
        if not spec or item is None:
            return
        values = list(self._get_field_value(item, spec) or [])
        if not (0 <= index < len(values)):
            return
        def cb(value, it=item, sp=spec, idx=index):
            if value in (None, ""):
                return
            vals = list(self._get_field_value(it, sp) or [])
            if 0 <= idx < len(vals):
                vals[idx] = value
                self._set_field_value(it, sp["key"], vals)
                self._notify_field_editor_changed()
                self.message = f"{sp['label']} updated."
        self._open_text_prompt(f"Edit {spec['label']}", values[index], cb, allow_empty=False, label="Value:")

    def _delete_list_editor_value(self, index):
        spec = self.field_editor_spec
        item = self.field_editor_item
        if not spec or item is None:
            return
        values = list(self._get_field_value(item, spec) or [])
        if 0 <= index < len(values):
            removed = values.pop(index)
            self._set_field_value(item, spec["key"], values)
            self._notify_field_editor_changed()
            self.message = f"Removed {removed}."

    def _edit_rect_field(self, item, field_key, current, label):
        current = dict(current or {})
        has_position = "x" in current or "y" in current

        def finish(values):
            self._set_field_value(item, field_key, values)
            self.message = f"{label} updated."

        if has_position:
            def ask_y(x):
                if x is None:
                    return
                def ask_w(y):
                    if y is None:
                        return
                    def ask_h(w):
                        if w is None:
                            return
                        self._open_text_prompt(f"{label} height", current.get("h", 32),
                                               lambda h: finish({"x": x, "y": y, "w": w, "h": h}) if h is not None else None,
                                               kind="int", allow_empty=False, label="h:", minvalue=1)
                    self._open_text_prompt(f"{label} width", current.get("w", 120), ask_h,
                                           kind="int", allow_empty=False, label="w:", minvalue=1)
                self._open_text_prompt(f"{label} y", current.get("y", 0), ask_w,
                                       kind="int", allow_empty=False, label="y:", minvalue=0)
            self._open_text_prompt(f"{label} x", current.get("x", 0), ask_y,
                                   kind="int", allow_empty=False, label="x:", minvalue=0)
        else:
            def ask_h(w):
                if w is None:
                    return
                self._open_text_prompt(f"{label} height", current.get("h", 32),
                                       lambda h: finish({"w": w, "h": h}) if h is not None else None,
                                       kind="int", allow_empty=False, label="h:", minvalue=1)
            self._open_text_prompt(f"{label} width", current.get("w", 120), ask_h,
                                   kind="int", allow_empty=False, label="w:", minvalue=1)

    def _rename_selected_item(self):
        item = self._selected_item()
        if not item:
            return

        def cb(name):
            if name:
                item["name"] = name
                self.message = f"Renamed item to {name}."
        self._open_text_prompt("Item name", item["name"], cb, allow_empty=False, label="Name:")

    def _cycle_selected_kind(self):
        item = self._selected_item()
        if not item:
            return
        current = item.get("kind", "Item")
        try:
            index = self.ITEM_KINDS.index(current)
        except ValueError:
            index = 0
        item["kind"] = self.ITEM_KINDS[(index + 1) % len(self.ITEM_KINDS)]
        self._ensure_kind_defaults(item)
        if item["kind"] not in self.SPRITE_OPTIONAL_KINDS:
            self._ensure_item_sprite(item)
        self.message = f"{item['name']} kind set to {item['kind']}."

    def _edit_selected_position(self):
        item = self._selected_item()
        if not item:
            return

        def ask_y(x):
            if x is None:
                return
            def set_xy(y, x=x):
                if y is None:
                    return
                item["x"] = x
                item["y"] = y
                self.message = f"Moved {item['name']} to {x}, {y}."
            self._open_text_prompt("Item Y", item["y"], set_xy, kind="int", allow_empty=False, label="Y:", minvalue=0)
        self._open_text_prompt("Item X", item["x"], ask_y, kind="int", allow_empty=False, label="X:", minvalue=0)

    def _edit_selected_sprite(self):
        self._pick_item_sprite()

    def _edit_selected_hint(self):
        item = self._selected_item()
        if not item:
            return

        def cb(hint):
            item["hint"] = hint or None
            self.message = f"{item['name']} hint updated."
        self._open_text_prompt("Item hint", item.get("hint") or "", cb, label="Hint:")

    def _toggle_selected_active(self):
        item = self._selected_item()
        if not item:
            return
        item["isActive"] = not item.get("isActive", False)
        self.message = f"{item['name']} active set to {item['isActive']}."

    def _edit_selected_opacity(self):
        item = self._selected_item()
        if not item:
            return

        def cb(value):
            if value is None:
                return
            item["opacity"] = max(0.0, min(1.0, float(value)))
            self.message = f"{item['name']} opacity set to {item['opacity']}."
        self._open_text_prompt("Disabled opacity", item.get("opacity", 0.5), cb, kind="float",
                               allow_empty=False, label="Opacity (0.0 - 1.0):")

    def _add_child_to_selected(self):
        item = self._selected_item()
        if not item:
            return
        if item.get("kind") not in self.EVOLUTION_KINDS:
            item["kind"] = "EvolutionItem"
            self._ensure_kind_defaults(item)

        def apply(sheet_name, row, column, it=item):
            children = it.setdefault("children", [])
            name = f"{it['name']} Stage {len(children) + 1}"
            children.append({
                "id": len(children),
                "name": name,
                "row": row,
                "column": column,
                "sheet": sheet_name,
                "label": None,
            })
            self.message = f"Added {name}. Use Nm to rename."
        self._open_sprite_picker("Choose NextItem sprite", apply)

    def _remove_child_from_selected(self, index):
        item = self._selected_item()
        if not item:
            return
        children = item.get("children", [])
        if 0 <= index < len(children):
            child = children.pop(index)
            for child_index, child_item in enumerate(children):
                child_item["id"] = child_index
            self.message = f"Removed child {child['name']}."

    def _set_child_sprite(self, index):
        item = self._selected_item()
        if not item:
            return
        children = item.get("children", [])
        if not (0 <= index < len(children)):
            return
        if not self.selected_cell:
            self.message = "Pick a tile in the palette first, then click Spr."
            return
        sheet_name, row, column = self.selected_cell
        children[index]["sheet"] = sheet_name
        children[index]["row"] = row
        children[index]["column"] = column
        self.message = f"Child {children[index]['name']} sprite set to {sheet_name} r{row} c{column}."

    def _rename_child(self, index):
        item = self._selected_item()
        if not item:
            return
        children = item.get("children", [])
        if not (0 <= index < len(children)):
            return
        def cb(name, ch=children[index]):
            if name:
                ch["name"] = name
                self.message = f"Child renamed to {name}."
        self._open_text_prompt("Child name", children[index]["name"], cb, allow_empty=False, label="Name:")

    def _edit_child_text(self, index, key, title):
        item = self._selected_item()
        if not item:
            return
        children = item.get("children", [])
        if not (0 <= index < len(children)):
            return

        def cb(value, ch=children[index], k=key, t=title):
            ch[k] = value if value not in (None, "") else None
            self.message = f"{t} updated."
        self._open_text_prompt(title, str(children[index].get(key) or ""), cb, label=f"{title}:")

    def _delete_selected_item(self):
        if self.selected_item_index is None:
            return
        if 0 <= self.selected_item_index < len(self.placed_items):
            deleted = self.placed_items.pop(self.selected_item_index)
            for index, item in enumerate(self.placed_items, start=1):
                item["id"] = index
            self.selected_item_index = None
            self.dragging_item_index = None
            self.message = f"Deleted {deleted['name']}."
