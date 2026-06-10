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
        self._draw_popup(screen, rect, radius=10)
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
        large_preview = item.get("kind") in ("EditableBox", "TimerItem", "SubMenuItem", "MultipleChoiceItem", "GoModeItem")
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
        if item.get("kind") in ("SubMenuItem", "MultipleChoiceItem"):
            actions.insert(-1, ("edit_submenu", "Edit items"))
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
        # Disable legacy property scrollbar (categories handle the fields now)
        self.property_scroll_rect = pygame.Rect(0, 0, 1, 1)
        self.property_scroll_track_rect = pygame.Rect(0, 0, 1, 1)
        self.property_scroll_thumb_rect = pygame.Rect(0, 0, 1, 1)
        # One button per category; clicking opens a dedicated sub-window
        categories = self._field_categories(kind)
        by = prop_rect.y + 36
        for cat, specs in categories.items():
            if by + 30 > prop_rect.bottom - 4:
                break
            brow = pygame.Rect(prop_rect.x + 12, by, prop_rect.w - 24, 30)
            hovered = self.hover_modal_key == f"propcat_{cat}"
            pygame.draw.rect(screen, self.COLORS["panel_alt"] if hovered else (20, 24, 34), brow)
            pygame.draw.rect(screen, (56, 62, 76), brow, 1)
            self.modal_buttons[f"propcat_{cat}"] = brow
            self._text(screen, cat, (brow.x + 10, brow.y + 6), 15, self.COLORS["gold"])
            self._text(screen, f"{len(specs)}  >", (brow.right - 44, brow.y + 7), 13, self.COLORS["muted"])
            by += 34

        if child_area is not None:
            self._draw_card(screen, child_area, (12, 15, 22), border_color=(56, 62, 76))
            self._text(screen, "NEXTITEMS", (child_area.x + 14, child_area.y + 12), 13, self.COLORS["gold"])
            add_child_rect = pygame.Rect(child_area.right - 104, child_area.y + 8, 94, 28)
            self.modal_buttons["add_child"] = add_child_rect
            self._draw_button(screen, add_child_rect, "Add", (36, 124, 87), hover=(self.hover_modal_key == "add_child"))
            children = item.get("children", [])
            self.child_scroll_track_rect = pygame.Rect(0, 0, 0, 0)
            self.child_scroll_thumb_rect = pygame.Rect(0, 0, 0, 0)
            if not children:
                self._text(screen, "No child yet.", (child_area.x + 14, child_area.y + 44), self.font_size, self.COLORS["muted"])
            else:
                row_y = child_area.y + 44
                row_h = 40
                max_rows = max(1, (child_area.bottom - row_y - 6) // row_h)
                max_scroll = max(0, len(children) - max_rows)
                self.child_scroll = max(0, min(self.child_scroll, max_scroll))
                self.child_scroll_rect = pygame.Rect(child_area.x + 8, row_y, child_area.w - 16, child_area.bottom - row_y - 6)
                for index, child in enumerate(children[self.child_scroll:self.child_scroll + max_rows],
                                              start=self.child_scroll):
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
                if max_scroll > 0:
                    track = pygame.Rect(child_area.right - 7, self.child_scroll_rect.y, 3, self.child_scroll_rect.h)
                    self.child_scroll_track_rect = track.inflate(10, 0)
                    pygame.draw.rect(screen, (56, 62, 76), track)
                    thumb_h = max(18, int(track.h * (max_rows / len(children))))
                    thumb_y = track.y + int((track.h - thumb_h) * (self.child_scroll / max_scroll))
                    self.child_scroll_thumb_rect = pygame.Rect(track.x - 1, thumb_y, 5, thumb_h)
                    pygame.draw.rect(screen, self.COLORS["gold"], self.child_scroll_thumb_rect)
                else:
                    self.child_scroll_track_rect = pygame.Rect(0, 0, 1, 1)
                    self.child_scroll_thumb_rect = pygame.Rect(0, 0, 1, 1)

        # --- Kind picker overlay (list of item types) ---
        if self.kind_picker_open:
            current = item.get("kind", "Item")
            available_kinds = self._available_item_kinds()
            opt_h = 34
            list_h = len(available_kinds) * opt_h + 16
            pk = pygame.Rect(rect.centerx - 150, rect.y + 90, 300, min(list_h, rect.h - 120))
            self._draw_card(screen, pk, (20, 24, 34), border_color=self.COLORS["gold"])
            self._text(screen, "CHOOSE TYPE", (pk.x + 12, pk.y + 8), 13, self.COLORS["gold"])
            oy = pk.y + 30
            for kind in available_kinds:
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

        # --- Property category sub-window ---
        if self.prop_category:
            cats = self._field_categories(kind)
            specs = cats.get(self.prop_category, [])
            cw = min(440, rect.w - 80)
            ch = min(60 + len(specs) * 46 + 16, rect.h - 100)
            pc = pygame.Rect(rect.centerx - cw // 2, rect.y + 80, cw, ch)
            self._draw_card(screen, pc, (20, 24, 34), border_color=self.COLORS["gold"])
            self._text(screen, self.prop_category.upper(), (pc.x + 14, pc.y + 12), 14, self.COLORS["gold"])
            pc_close = pygame.Rect(pc.right - 38, pc.y + 10, 28, 28)
            self.modal_buttons["propcat_close"] = pc_close
            self._draw_button(screen, pc_close, "X", self.COLORS["red"], hover=(self.hover_modal_key == "propcat_close"))
            fy2 = pc.y + 46
            prev_clip = screen.get_clip()
            screen.set_clip(pc.inflate(-6, -40))
            for spec in specs:
                if fy2 + 40 > pc.bottom - 6:
                    break
                frow = pygame.Rect(pc.x + 12, fy2, pc.w - 24, 40)
                hovered = self.hover_modal_key == f"field_{spec['key']}"
                pygame.draw.rect(screen, self.COLORS["panel_alt"] if hovered else (12, 15, 22), frow)
                pygame.draw.rect(screen, (56, 62, 76), frow, 1)
                self.modal_buttons[f"field_{spec['key']}"] = frow
                self._text(screen, spec["label"], (frow.x + 10, frow.y + 4), 12, self.COLORS["muted"])
                val = self._truncate_text_to_width(self._format_field_value(item, spec), frow.w - 20, 14)
                self._text(screen, val, (frow.x + 10, frow.y + 20), 14, self.COLORS["line_light"])
                fy2 += 46
            screen.set_clip(prev_clip)

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
        if self.item_refs_editor_open and self.item_refs_editor_spec:
            self._draw_item_refs_editor(screen, rect)

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
        if spec["type"] == "image":
            return os.path.basename(str(value)) if value else "None"
        if spec["type"] == "item_refs":
            names = self._item_ref_names(value)
            if not names:
                return "None"
            text = ", ".join(names)
            return text[:26] + "..." if len(text) > 26 else text
        if spec["type"] in ("json", "jsonnull"):
            if value in (None, "", [], {}):
                return "None" if spec["type"] == "jsonnull" else "{}"
            text = json.dumps(value, ensure_ascii=False)
            return text[:26] + "..." if len(text) > 26 else text
        if value in (None, ""):
            return "None"
        return str(value)

    def _field_category(self, spec):
        key = spec["key"]
        if key in ("HintItems", "ActiveItems", "InactiveItems"):
            return "Linked items"
        # Raw whole-config JSON editors go to Advanced, not General
        if spec.get("type") in ("json", "jsonnull") and "." not in key:
            return "Advanced"
        if key == "Group" or "GroupToggle" in key:
            return "Group"
        if key in ("visible", "AlwaysEnable"):
            return "General"
        if "." in key:
            prefix = key.split(".")[0]
            return {"Timer": "Timer", "Buttons": "Buttons", "Style": "Style"}.get(prefix, prefix)
        return "General"

    def _field_categories(self, kind):
        cats = {}
        for spec in self._kind_fields(kind):
            cats.setdefault(self._field_category(spec), []).append(spec)
        # Stable, friendly order
        order = ["General", "Timer", "Buttons", "Group", "Style", "Linked items", "Advanced"]
        return {c: cats[c] for c in order if c in cats} | {c: v for c, v in cats.items() if c not in order}

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
        actions = []
        for action in spec.get("actions", []):
            visible = action.get("visible", True)
            if callable(visible):
                visible = visible()
            if visible:
                actions.append(action)
        popup_h = 98 + len(rows_to_draw) * 44 + (34 if list_mode else 0) + (42 if actions else 0)
        popup = pygame.Rect(parent_rect.centerx - 210 if list_mode else parent_rect.centerx - 180,
                            parent_rect.y + 96, 420 if list_mode else 360, popup_h)
        self._draw_popup(screen, popup, radius=10)
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
            self._text(screen, f"+ {len(parts) - len(rows_to_draw)} more entries", (popup.x + 16, y + 4),
                       13, self.COLORS["muted"])
            y += 28
        if actions:
            y += 2
            action_w = min(150, popup.w - 32)
            x = popup.x + 16
            for action in actions:
                key = f"fe_action_{action['key']}"
                rect = pygame.Rect(x, y, action_w, 30)
                self.modal_buttons[key] = rect
                self._draw_button(screen, rect, action.get("label", action["key"]), (36, 124, 87),
                                  hover=(self.hover_modal_key == key))
                x += action_w + 10

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
        self._draw_popup(screen, rect, radius=10)
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
        if self.selected_linked_path is not None:
            return self._get_linked_item_by_path(self.selected_linked_path)
        if self.selected_item_index is None:
            return None
        if self.selected_item_index < 0 or self.selected_item_index >= len(self.placed_items):
            self.selected_item_index = None
            return None
        return self.placed_items[self.selected_item_index]

    def _flatten_items_for_list(self):
        """Flat list of (item, path, depth, marker_color) including linked refs."""
        entries = []
        fields = [
            ("HintItems", (0, 220, 255)),
            ("ActiveItems", self.COLORS["green"]),
            ("InactiveItems", self.COLORS["red"]),
        ]

        def walk(item, path, depth, color):
            entries.append({"item": item, "path": path, "depth": depth, "color": color})
            for field, fcolor in fields:
                for j, ref in enumerate(item.get(field) or []):
                    walk(ref, path + (field, j), depth + 1, fcolor)
        for i, it in enumerate(self.placed_items):
            walk(it, (i,), 0, None)
        return entries

    def _get_linked_item_by_path(self, path):
        if not path or not isinstance(path[0], int) or not (0 <= path[0] < len(self.placed_items)):
            return None
        current = self.placed_items[path[0]]
        cursor = 1
        while cursor < len(path):
            field = path[cursor]
            linked_index = path[cursor + 1] if cursor + 1 < len(path) else None
            values = current.get(field) or []
            if not isinstance(linked_index, int) or linked_index < 0 or linked_index >= len(values):
                return None
            current = values[linked_index]
            cursor += 2
        return current

    def _set_linked_item_by_path(self, path, value):
        if not path or not isinstance(path[0], int) or not (0 <= path[0] < len(self.placed_items)):
            return False
        if len(path) == 1:
            self.placed_items[path[0]] = value
            return True
        parent = self._get_linked_item_by_path(path[:-2])
        if parent is None:
            return False
        field = path[-2]
        linked_index = path[-1]
        values = parent.get(field) or []
        if not isinstance(linked_index, int) or linked_index < 0 or linked_index >= len(values):
            return False
        values[linked_index] = value
        parent[field] = values
        return True

    def _delete_linked_item_by_path(self, path):
        if not path or len(path) < 3:
            return None
        parent = self._get_linked_item_by_path(path[:-2])
        if parent is None:
            return None
        field = path[-2]
        linked_index = path[-1]
        values = parent.get(field) or []
        if not isinstance(linked_index, int) or linked_index < 0 or linked_index >= len(values):
            return None
        deleted = values.pop(linked_index)
        parent[field] = values or None
        return deleted

    def _find_linked_item_path_at(self, mouse_position):
        for path, rect in reversed(getattr(self, "linked_item_targets", [])):
            if rect and rect.collidepoint(mouse_position):
                return path
        return None

    def _open_item_modal(self, index, path=None):
        self.selected_item_index = index
        self.selected_linked_path = path
        self.modal_item_index = index
        self.modal_item_path = path
        source = self._get_linked_item_by_path(path) if path is not None else self.placed_items[index]
        self.modal_item = copy.deepcopy(source)
        self.kind_picker_open = False
        self.child_scroll = 0
        self.property_scroll = 0
        self.item_modal_open = True

    def _flush_returned_items(self):
        returned = self.modal_item.pop("_returned_items", None) if self.modal_item else None
        for it in returned or []:
            self.placed_items.append(it)

    def _close_item_modal(self, save):
        if save and self.modal_item is not None and self.modal_item_path is not None:
            self._flush_returned_items()
            for transient in ("screen_rect", "_preview", "_component", "_comp_sig", "_linked_path"):
                self.modal_item.pop(transient, None)
            self._set_linked_item_by_path(self.modal_item_path, self.modal_item)
            self.message = f"Saved {self.modal_item['name']}."
        elif save and self.modal_item is not None and self.modal_item_index is not None \
                and 0 <= self.modal_item_index < len(self.placed_items):
            self._flush_returned_items()
            for transient in ("screen_rect", "_preview", "_component", "_comp_sig"):
                self.modal_item.pop(transient, None)
            self.placed_items[self.modal_item_index] = self.modal_item
            self.message = f"Saved {self.modal_item['name']}."
        else:
            self.message = "Changes discarded."
        self.item_modal_open = False
        self.kind_picker_open = False
        self.prop_category = None
        self._close_field_editor()
        self._close_item_refs_editor()
        self.position_pick_mode = False
        self.child_edit_index = None
        self.dragging_child_scroll = False
        self.dragging_property_scroll = False
        self.modal_item = None
        self.modal_item_index = None
        self.modal_item_path = None

    def _get_item_index_at(self, mouse_position):
        for index in range(len(self.placed_items) - 1, -1, -1):
            rect = self.placed_items[index].get("screen_rect")
            if rect and rect.collidepoint(mouse_position):
                return index
        return None

    def _nudge_selected(self, dx, dy):
        """Move the current selection by (dx, dy) canvas pixels. Returns True if
        something moved."""
        # Map check selected
        if self._map_view_active() and self.selected_check_index is not None:
            checks = self._current_checks()
            if 0 <= self.selected_check_index < len(checks):
                pos = checks[self.selected_check_index].setdefault("Positions", {"x": 0, "y": 0})
                pos["x"] = max(0, pos.get("x", 0) + dx)
                pos["y"] = max(0, pos.get("y", 0) + dy)
                self.message = f"Check at {pos['x']}, {pos['y']}."
                return True
            return False
        # Linked item selected
        if self.selected_linked_path is not None:
            item = self._get_linked_item_by_path(self.selected_linked_path)
            if item is not None:
                item["x"] = max(0, item.get("x", 0) + dx)
                item["y"] = max(0, item.get("y", 0) + dy)
                self.message = f"{item.get('name', 'item')} at {item['x']}, {item['y']}."
                return True
            return False
        # Top-level item selected
        if self.selected_item_index is not None and 0 <= self.selected_item_index < len(self.placed_items):
            item = self.placed_items[self.selected_item_index]
            item["x"] = max(0, item.get("x", 0) + dx)
            item["y"] = max(0, item.get("y", 0) + dy)
            self.message = f"{item.get('name', 'item')} at {item['x']}, {item['y']}."
            return True
        return False

    def _item_canvas_size(self, item):
        sr = item.get("screen_rect")
        if sr and sr.w > 0 and self.last_bg_rect.w:
            sc = self._canvas_size()[0] / self.last_bg_rect.w
            return sr.w * sc, sr.h * sc
        sheet = self._sheet_by_name(item.get("sheet")) or self.active_sheet
        if sheet:
            return float(sheet["cell_w"]), float(sheet["cell_h"])
        return 32.0, 32.0

    def _snap_xy(self, moving, x, y):
        """Snap a top-left position (canvas px) to nearby items' left/center/right
        and top/center/bottom anchors. Grid snap only when the grid is shown.
        Sets self.snap_guides."""
        self.snap_guides = []
        if not (self.snap_enabled or self.grid_shown):
            return int(x), int(y)
        scale = self._canvas_size()[0] / self.last_bg_rect.w if self.last_bg_rect.w else 1
        thr = max(3.0, 8 * scale)            # snap threshold (canvas px ~ constant on screen)
        w, h = self._item_canvas_size(moving)

        best_dx = best_dy = None
        guide_x = guide_y = None
        if self.snap_enabled:
            moving_x = (x, x + w / 2, x + w)
            moving_y = (y, y + h / 2, y + h)
            for other in self.placed_items:
                if other is moving:
                    continue
                ow, oh = self._item_canvas_size(other)
                ox, oy = other.get("x", 0), other.get("y", 0)
                for mv in moving_x:
                    for ov in (ox, ox + ow / 2, ox + ow):
                        d = ov - mv
                        if abs(d) <= thr and (best_dx is None or abs(d) < abs(best_dx)):
                            best_dx, guide_x = d, ov
                for mv in moving_y:
                    for ov in (oy, oy + oh / 2, oy + oh):
                        d = ov - mv
                        if abs(d) <= thr and (best_dy is None or abs(d) < abs(best_dy)):
                            best_dy, guide_y = d, ov
        if best_dx is not None:
            x += best_dx
            self.snap_guides.append(("v", guide_x))
        elif self.grid_shown and self.snap_size > 0:
            x = round(x / self.snap_size) * self.snap_size
        if best_dy is not None:
            y += best_dy
            self.snap_guides.append(("h", guide_y))
        elif self.grid_shown and self.snap_size > 0:
            y = round(y / self.snap_size) * self.snap_size
        return int(x), int(y)

    def _move_item_to_mouse(self, index, mouse_position):
        if index < 0 or index >= len(self.placed_items) or not self.last_bg_rect.w:
            return
        x = mouse_position[0] - self.drag_offset[0]
        y = mouse_position[1] - self.drag_offset[1]
        x = max(self.last_bg_rect.x, min(x, self.last_bg_rect.right - 1))
        y = max(self.last_bg_rect.y, min(y, self.last_bg_rect.bottom - 1))
        scale = self._canvas_size()[0] / self.last_bg_rect.w
        cx, cy = self._snap_xy(self.placed_items[index],
                               (x - self.last_bg_rect.x) * scale, (y - self.last_bg_rect.y) * scale)
        self.placed_items[index]["x"] = cx
        self.placed_items[index]["y"] = cy

    def _move_linked_item_to_mouse(self, path, mouse_position):
        item = self._get_linked_item_by_path(path)
        if item is None or not self.last_bg_rect.w:
            return
        x = mouse_position[0] - self.drag_offset[0]
        y = mouse_position[1] - self.drag_offset[1]
        x = max(self.last_bg_rect.x, min(x, self.last_bg_rect.right - 1))
        y = max(self.last_bg_rect.y, min(y, self.last_bg_rect.bottom - 1))
        scale = self._canvas_size()[0] / self.last_bg_rect.w
        cx, cy = self._snap_xy(item, (x - self.last_bg_rect.x) * scale, (y - self.last_bg_rect.y) * scale)
        item["x"] = cx
        item["y"] = cy

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

    def _available_item_kinds(self):
        kinds = list(self.ITEM_KINDS)
        if getattr(self, "canvas_context", "main") == "submenu":
            kinds = [kind for kind in kinds if kind not in ("SubMenuItem", "MultipleChoiceItem")]
        return kinds

    def _scroll_child_list(self, wheel_y):
        item = self._selected_item()
        if not item or item.get("kind") not in self.EVOLUTION_KINDS:
            return False
        children = item.get("children", [])
        if not children:
            return False
        row_h = 40
        max_rows = max(1, self.child_scroll_rect.h // row_h)
        max_scroll = max(0, len(children) - max_rows)
        if max_scroll <= 0:
            return False
        old_scroll = self.child_scroll
        self.child_scroll = max(0, min(max_scroll, self.child_scroll - wheel_y))
        return self.child_scroll != old_scroll

    def _set_child_scroll_from_mouse(self, mouse_y, drag_offset=0):
        item = self._selected_item()
        if not item or item.get("kind") not in self.EVOLUTION_KINDS:
            return False
        children = item.get("children", [])
        if not children or self.child_scroll_track_rect.h <= 1 or self.child_scroll_thumb_rect.h <= 0:
            return False
        row_h = 40
        max_rows = max(1, self.child_scroll_rect.h // row_h)
        max_scroll = max(0, len(children) - max_rows)
        if max_scroll <= 0:
            return False
        track = self.child_scroll_track_rect
        thumb = self.child_scroll_thumb_rect
        usable = max(1, track.h - thumb.h)
        y = max(track.y, min(mouse_y - drag_offset, track.y + usable))
        old_scroll = self.child_scroll
        self.child_scroll = max(0, min(max_scroll, round(((y - track.y) / usable) * max_scroll)))
        return self.child_scroll != old_scroll

    def _property_scroll_limits(self):
        item = self._selected_item()
        if not item:
            return 0
        kind = item.get("kind", "Item")
        specs = self._kind_fields(kind)
        ncols = 1 if kind in self.EVOLUTION_KINDS else 2
        row_h = 42
        visible_rows = max(1, self.property_scroll_rect.h // row_h)
        total_rows = math.ceil(len(specs) / ncols) if specs else 0
        return max(0, total_rows - visible_rows)

    def _scroll_property_list(self, wheel_y):
        max_scroll = self._property_scroll_limits()
        if max_scroll <= 0:
            return False
        old_scroll = self.property_scroll
        self.property_scroll = max(0, min(max_scroll, self.property_scroll - wheel_y))
        return self.property_scroll != old_scroll

    def _set_property_scroll_from_mouse(self, mouse_y, drag_offset=0):
        max_scroll = self._property_scroll_limits()
        if max_scroll <= 0 or self.property_scroll_track_rect.h <= 1 or self.property_scroll_thumb_rect.h <= 0:
            return False
        track = self.property_scroll_track_rect
        thumb = self.property_scroll_thumb_rect
        usable = max(1, track.h - thumb.h)
        y = max(track.y, min(mouse_y - drag_offset, track.y + usable))
        old_scroll = self.property_scroll
        self.property_scroll = max(0, min(max_scroll, round(((y - track.y) / usable) * max_scroll)))
        return self.property_scroll != old_scroll

    def _new_uid(self):
        self._uid_counter += 1
        return f"u{self._uid_counter}"

    def _linked_identities(self):
        """Identities of items embedded as Hint/Active/Inactive refs (recursive).
        Such items are owned by their parent, so they are hidden from the main canvas."""
        ids = set()

        def walk(it):
            for field in ("HintItems", "ActiveItems", "InactiveItems"):
                for ref in it.get(field) or []:
                    ids.update(self._item_ref_aliases(ref))
                    walk(ref)
        for index, it in enumerate(self.placed_items):
            if self.item_modal_open and self.modal_item is not None and index == self.modal_item_index:
                continue
            walk(it)
        if self.item_modal_open and self.modal_item is not None:
            walk(self.modal_item)
        return ids

    def _item_ref_aliases(self, item):
        if not isinstance(item, dict):
            return {str(item)}
        aliases = {self._item_ref_identity(item)}
        name = str(item.get("Name") or item.get("name") or "")
        item_id = item.get("Id", item.get("id"))
        if item_id is not None or name:
            aliases.add(f"legacy:{item_id}:{name}")
        aliases.add("struct:{}:{}:{}:{}:{}:{}:{}:{}".format(
            item_id,
            item.get("Kind") or item.get("kind") or "",
            name,
            item.get("x", item.get("Positions", {}).get("x", 0)),
            item.get("y", item.get("Positions", {}).get("y", 0)),
            item.get("row", item.get("SheetInformation", {}).get("row", 1)),
            item.get("column", item.get("SheetInformation", {}).get("column", 1)),
            item.get("sheet", item.get("SheetInformation", {}).get("SpriteSheet", "")),
        ))
        return {alias for alias in aliases if alias}

    def _item_ref_identity(self, item):
        if not isinstance(item, dict):
            return str(item)
        uid = item.get("uid")
        if uid is not None:
            return f"uid:{uid}"
        name = str(item.get("Name") or item.get("name") or "")
        item_id = item.get("Id", item.get("id"))
        return f"{item_id}:{name}" if item_id is not None else name

    def _item_ref_names(self, value):
        if not value:
            return []
        if isinstance(value, dict):
            value = [value]
        if not isinstance(value, list):
            return [str(value)]
        names = []
        for ref in value:
            if isinstance(ref, dict):
                name = str(ref.get("Name") or ref.get("name") or "")
            else:
                name = str(ref)
            if name:
                names.append(name)
        return names

    def _item_ref_identities(self, value):
        if not value:
            return set()
        if isinstance(value, dict):
            value = [value]
        if not isinstance(value, list):
            return {str(value)}
        identities = set()
        for ref in value:
            identities.update(self._item_ref_aliases(ref))
        return identities

    def _item_ref_candidates(self):
        candidates = []
        seen = set()
        spec = self.item_refs_editor_spec
        editor_item = self.item_refs_editor_item
        current_ids = set()
        if spec and editor_item is not None:
            current_ids = self._item_ref_identities(self._get_field_value(editor_item, spec))
            for linked in self._get_field_value(editor_item, spec) or []:
                identity = self._item_ref_identity(linked)
                aliases = self._item_ref_aliases(linked)
                if not identity or aliases.intersection(seen):
                    continue
                seen.update(aliases)
                name = linked.get("name") or linked.get("Name") or identity
                candidates.append((len(candidates), linked, str(name)))
        # Items already assigned to another category/parent are not selectable here
        linked_elsewhere = self._linked_identities() - current_ids
        for index, item in enumerate(self.placed_items):
            if index == self.modal_item_index:
                continue
            identity = self._item_ref_identity(item)
            aliases = self._item_ref_aliases(item)
            if identity in seen or aliases.intersection(seen) or aliases.intersection(linked_elsewhere):
                continue
            seen.update(aliases)
            name = item.get("name") or f"Item {index + 1}"
            candidates.append((len(candidates), item, str(name)))
        return candidates

    def _clean_item_transients(self, item):
        if not isinstance(item, dict):
            return item
        for transient in ("screen_rect", "_preview", "_component", "_comp_sig", "_linked_path"):
            item.pop(transient, None)
        for field in ("HintItems", "ActiveItems", "InactiveItems"):
            for child in item.get(field) or []:
                self._clean_item_transients(child)
        return item

    def _open_item_refs_editor(self, spec, item):
        current = self._get_field_value(item, spec)
        self.item_refs_editor_open = True
        self.item_refs_editor_spec = spec
        self.item_refs_editor_item = item
        self.item_refs_selected = self._item_ref_identities(current)
        self.item_refs_scroll = 0
        self.item_refs_scroll_rect = pygame.Rect(0, 0, 1, 1)

    def _close_item_refs_editor(self):
        self.item_refs_editor_open = False
        self.item_refs_editor_spec = None
        self.item_refs_editor_item = None
        self.item_refs_selected = set()
        self.item_refs_scroll = 0
        self.item_refs_scroll_rect = pygame.Rect(0, 0, 1, 1)

    def _draw_item_refs_editor(self, screen, parent_rect):
        spec = self.item_refs_editor_spec
        item = self.item_refs_editor_item
        if not spec or item is None:
            self._close_item_refs_editor()
            return
        self.modal_buttons = {}
        shade = pygame.Surface(parent_rect.size, pygame.SRCALPHA)
        shade.fill((0, 0, 0, 155))
        screen.blit(shade, parent_rect.topleft)

        popup_w = min(640, parent_rect.w - 56)
        popup_h = min(560, parent_rect.h - 86)
        popup = pygame.Rect(parent_rect.centerx - popup_w // 2, parent_rect.centery - popup_h // 2, popup_w, popup_h)
        self._draw_popup(screen, popup, radius=10)
        self._text(screen, spec["label"].upper(), (popup.x + 18, popup.y + 14), 14, self.COLORS["gold"])
        self._text(screen, "Select existing items to clone into this field.",
                   (popup.x + 18, popup.y + 38), 13, self.COLORS["muted"])

        close_rect = pygame.Rect(popup.right - 42, popup.y + 12, 30, 30)
        apply_rect = pygame.Rect(close_rect.x - 94, popup.y + 12, 82, 30)
        clear_rect = pygame.Rect(apply_rect.x - 82, popup.y + 12, 70, 30)
        self.modal_buttons["refs_apply"] = apply_rect
        self.modal_buttons["refs_clear"] = clear_rect
        self.modal_buttons["refs_close"] = close_rect
        self._draw_button(screen, clear_rect, "Clear", self.COLORS["button"], hover=(self.hover_modal_key == "refs_clear"))
        self._draw_button(screen, apply_rect, "Apply", (36, 124, 87), hover=(self.hover_modal_key == "refs_apply"))
        self._draw_button(screen, close_rect, "X", self.COLORS["red"], hover=(self.hover_modal_key == "refs_close"))

        candidates = self._item_ref_candidates()
        selected_count = sum(
            1 for _, candidate, _ in candidates
            if self._item_ref_aliases(candidate).intersection(self.item_refs_selected)
        )
        count_text = f"{selected_count} selected / {len(candidates)} items"
        self._text(screen, count_text, (popup.x + 18, popup.y + 62), 13, self.COLORS["muted"])

        row_h = 42
        list_top = popup.y + 86
        list_rect = pygame.Rect(popup.x + 18, list_top, popup.w - 36, popup.bottom - list_top - 18)
        self.item_refs_scroll_rect = list_rect
        max_rows = max(1, list_rect.h // row_h)
        max_scroll = max(0, len(candidates) - max_rows)
        self.item_refs_scroll = max(0, min(self.item_refs_scroll, max_scroll))
        if not candidates:
            self._text(screen, "No other item available.", (list_rect.x + 8, list_rect.y + 10), 15, self.COLORS["muted"])
            return

        y = list_rect.y
        for candidate_index, candidate, name in candidates[self.item_refs_scroll:self.item_refs_scroll + max_rows]:
            row = pygame.Rect(list_rect.x, y, list_rect.w, row_h - 4)
            key = f"refs_toggle_{candidate_index}"
            identity = self._item_ref_identity(candidate)
            aliases = self._item_ref_aliases(candidate)
            selected = bool(aliases.intersection(self.item_refs_selected))
            hovered = self.hover_modal_key == key
            pygame.draw.rect(screen, (34, 48, 42) if selected else (12, 15, 22), row)
            pygame.draw.rect(screen, self.COLORS["gold"] if selected else (56, 62, 76), row, 1)
            self.modal_buttons[key] = row

            icon = self._get_icon_surface(candidate.get("row", 1), candidate.get("column", 1), candidate.get("sheet"))
            if icon:
                screen.blit(pygame.transform.smoothscale(icon, (30, 30)), (row.x + 8, row.y + 4))
            mark = "[x]" if selected else "[ ]"
            self._text(screen, mark, (row.x + 50, row.y + 10), 14, self.COLORS["green"] if selected else self.COLORS["muted"])
            display = name if len(name) <= 48 else name[:45] + "..."
            self._text(screen, display, (row.x + 90, row.y + 9), 15,
                       self.COLORS["line_light"] if not hovered else self.COLORS["gold"])
            y += row_h

        if max_scroll > 0:
            page_text = f"{self.item_refs_scroll + 1}-{min(len(candidates), self.item_refs_scroll + max_rows)}"
            self._text(screen, page_text, (list_rect.right - 54, popup.y + 62), 12, self.COLORS["muted"])

    def _scroll_item_refs_editor(self, wheel_y):
        candidates = self._item_ref_candidates()
        if not candidates:
            return False
        row_h = 40
        max_rows = max(1, self.item_refs_scroll_rect.h // row_h)
        max_scroll = max(0, len(candidates) - max_rows)
        if max_scroll <= 0:
            return False
        old_scroll = self.item_refs_scroll
        self.item_refs_scroll = max(0, min(max_scroll, self.item_refs_scroll - wheel_y))
        return self.item_refs_scroll != old_scroll

    def _apply_item_refs_editor(self):
        spec = self.item_refs_editor_spec
        item = self.item_refs_editor_item
        if not spec or item is None:
            self._close_item_refs_editor()
            return
        old_refs = self._get_field_value(item, spec) or []
        selected = []
        selected_ids = set()
        for _, candidate, _ in self._item_ref_candidates():
            if self._item_ref_aliases(candidate).intersection(self.item_refs_selected):
                selected.append(self._clean_item_transients(copy.deepcopy(candidate)))
                selected_ids.update(self._item_ref_aliases(candidate))
        self._set_field_value(item, spec["key"], selected or None)

        # Items removed from this category go back to the canvas as classic items
        # (deferred to modal save so a cancel undoes everything consistently).
        existing_top = set()
        for it in self.placed_items:
            existing_top.update(self._item_ref_aliases(it))
        pending = item.setdefault("_returned_items", [])
        pending_ids = set()
        for pending_item in pending:
            pending_ids.update(self._item_ref_aliases(pending_item))
        for old in old_refs:
            old_ids = self._item_ref_aliases(old)
            if not old_ids.intersection(selected_ids) and not old_ids.intersection(existing_top) \
                    and not old_ids.intersection(pending_ids):
                returned = self._clean_item_transients(copy.deepcopy(old))
                returned["uid"] = self._new_uid()
                pending.append(returned)
        # A re-selected item is no longer "returned"
        item["_returned_items"] = [p for p in pending
                                   if not self._item_ref_aliases(p).intersection(selected_ids)]

        self.message = f"{spec['label']} updated."
        self._close_item_refs_editor()

    def _handle_item_refs_editor_click(self, mouse_position):
        for key, rect in self.modal_buttons.items():
            if not rect.collidepoint(mouse_position):
                continue
            if key == "refs_close":
                self._close_item_refs_editor()
            elif key == "refs_clear":
                self.item_refs_selected = set()
            elif key == "refs_apply":
                self._apply_item_refs_editor()
            elif key.startswith("refs_toggle_"):
                selected_index = int(key.rsplit("_", 1)[1])
                for candidate_index, candidate, _ in self._item_ref_candidates():
                    if candidate_index != selected_index:
                        continue
                    identity = self._item_ref_identity(candidate)
                    aliases = self._item_ref_aliases(candidate)
                    if aliases.intersection(self.item_refs_selected):
                        self.item_refs_selected.difference_update(aliases)
                    else:
                        self.item_refs_selected.update(aliases)
                    break
            return True
        self._close_item_refs_editor()
        return True

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
                if key.startswith("fe_action_"):
                    action_key = key[len("fe_action_"):]
                    for action in (self.field_editor_spec or {}).get("actions", []):
                        if action.get("key") == action_key and callable(action.get("callback")):
                            action["callback"]()
                            return True
                    return True
                if key.startswith("fe_"):
                    self._edit_field_editor_part(key[len("fe_"):])
                    return True
            self._close_field_editor()
            return True
        return False

    def _handle_modal_click(self, mouse_position):
        if self.item_refs_editor_open:
            self._handle_item_refs_editor_click(mouse_position)
            return
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
        # Property category sub-window takes priority while open
        if self.prop_category:
            for key, rect in self.modal_buttons.items():
                if not rect.collidepoint(mouse_position):
                    continue
                if key == "propcat_close":
                    self.prop_category = None
                elif key.startswith("field_"):
                    self._edit_field(key[len("field_"):])
                return
            self.prop_category = None
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
            elif key == "edit_submenu":
                path = self.modal_item_path
                index = self.modal_item_index
                self._close_item_modal(save=True)
                # Resolve the real (saved) item, supporting linked SubMenuItems via path
                if path is not None:
                    target = self._get_linked_item_by_path(path)
                elif index is not None and 0 <= index < len(self.placed_items):
                    target = self.placed_items[index]
                else:
                    target = None
                if target is not None:
                    self._enter_submenu_canvas(target)
            elif key == "add_child":
                self._add_child_to_selected()
            elif key.startswith("propcat_"):
                self.prop_category = key[len("propcat_"):]
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
                freed = 0
                if self.modal_item_index is not None and 0 <= self.modal_item_index < len(self.placed_items):
                    deleted = self.placed_items.pop(self.modal_item_index)
                    freed = len(self._release_linked_items(deleted))
                    self.selected_item_index = None
                elif self.modal_item_path is not None:
                    self._delete_linked_item_by_path(self.modal_item_path)
                self._close_item_modal(save=False)
                self.message = "Item deleted." + (f" ({freed} linked kept)" if freed else "")
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
        if not item or kind not in self._available_item_kinds():
            if kind in ("SubMenuItem", "MultipleChoiceItem"):
                self.message = "Item-list containers cannot contain another item-list container."
                return
        item["kind"] = kind
        self._ensure_kind_defaults(item)
        if kind not in self.SPRITE_OPTIONAL_KINDS:
            self._ensure_item_sprite(item)
        self.property_scroll = 0
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
        elif ftype == "item_refs":
            self._open_item_refs_editor(spec, item)
        elif ftype == "sprite":
            def apply(sheet, row, column, it=item, fk=field_key, lbl=label):
                self._set_field_value(it, fk, {"sheet": sheet, "row": row, "column": column})
                self.message = f"{lbl} set to {sheet} r{row} c{column}."
            self._open_sprite_picker(label, apply)
        elif ftype == "image":
            self._import_item_image_field(item, field_key, label)
        else:  # str / strnull
            def cb(text, it=item, fk=field_key, lbl=label, ft=ftype):
                self._set_field_value(it, fk, text if text not in (None, "") else (None if ft == "strnull" else ""))
                self.message = f"{lbl} updated."
            self._open_text_prompt(label, str(current or ""), cb, label=f"{label}:")

    def _import_item_image_field(self, item, field_key, label):
        path = filedialog.askopenfilename(
            title=f"Select {label}",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            surface = pygame.image.load(path).convert_alpha()
            ext = os.path.splitext(path)[1].lower() or ".png"
            base = self._slugify(os.path.splitext(os.path.basename(path))[0]) or self._slugify(item.get("name", "image"))
            file_name = f"{base}{ext}"
            self._set_field_value(item, field_key, file_name)
            assets = item.setdefault("_image_assets", {})
            assets[field_key] = {"path": path, "surface": surface, "file": file_name}
            self.message = f"{label} imported: {file_name}."
        except Exception as exc:
            self.message = f"Could not import {label}: {exc}"

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
        kinds = self._available_item_kinds()
        try:
            index = kinds.index(current)
        except ValueError:
            index = 0
        item["kind"] = kinds[(index + 1) % len(kinds)]
        self._ensure_kind_defaults(item)
        if item["kind"] not in self.SPRITE_OPTIONAL_KINDS:
            self._ensure_item_sprite(item)
        self.property_scroll = 0
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
            self.child_scroll = max(0, min(self.child_scroll, max(0, len(children) - 1)))
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

    def _release_linked_items(self, item):
        """Detach an item's Hint/Active/Inactive refs back into the canvas as classic
        items (so deleting a parent does not delete its linked items)."""
        released = []
        for field in ("HintItems", "ActiveItems", "InactiveItems"):
            for ref in item.get(field) or []:
                freed = self._clean_item_transients(copy.deepcopy(ref))
                freed["uid"] = self._new_uid()
                released.append(freed)
        self.placed_items.extend(released)
        return released

    def _delete_selected_item(self):
        if self.selected_linked_path is not None:
            deleted = self._delete_linked_item_by_path(self.selected_linked_path)
            if deleted:
                self.message = f"Deleted linked {deleted['name']}."
            self.selected_linked_path = None
            return
        if self.selected_item_index is None:
            return
        if 0 <= self.selected_item_index < len(self.placed_items):
            deleted = self.placed_items.pop(self.selected_item_index)
            freed = self._release_linked_items(deleted)
            self.selected_item_index = None
            self.dragging_item_index = None
            extra = f" ({len(freed)} linked item(s) kept)" if freed else ""
            self.message = f"Deleted {deleted['name']}.{extra}"

    def _duplicate_item(self, index):
        if index is None or not (0 <= index < len(self.placed_items)):
            return
        clone = copy.deepcopy(self.placed_items[index])
        for transient in ("screen_rect", "_preview", "_component", "_comp_sig",
                          "_linked_path", "_returned_items"):
            clone.pop(transient, None)
        clone["uid"] = self._new_uid()
        clone["id"] = max((it.get("id", 0) for it in self.placed_items), default=0) + 1
        clone["x"] = clone.get("x", 0) + 16
        clone["y"] = clone.get("y", 0) + 16
        # A duplicate must not keep links pointing it as a hidden ref twin
        self.placed_items.append(clone)
        self.selected_item_index = len(self.placed_items) - 1
        self.message = f"Duplicated {clone.get('name', 'item')}."

    def _context_edit_target(self):
        path = self.context_menu_path
        if not path:
            return
        if len(path) == 1:
            self.selected_item_index = path[0]
            self.selected_linked_path = None
            self._open_item_modal(path[0])
        else:
            self.selected_item_index = None
            self.selected_linked_path = path
            self._open_item_modal(path[0], path)

    def _context_unlink_target(self):
        path = self.context_menu_path
        if not path or len(path) == 1:
            return
        item = self._get_linked_item_by_path(path)
        if item is None:
            return
        freed = self._clean_item_transients(copy.deepcopy(item))
        freed["uid"] = self._new_uid()
        self._delete_linked_item_by_path(path)
        self.placed_items.append(freed)
        self.selected_linked_path = None
        self.message = f"Unlinked {freed.get('name', 'item')}."

    def _context_delete_target(self):
        path = self.context_menu_path
        if not path:
            return
        if len(path) == 1:
            self._delete_item_at(path[0])
        else:
            deleted = self._delete_linked_item_by_path(path)
            if deleted:
                self.message = f"Deleted linked {deleted.get('name', 'item')}."

    def _action_renumber(self):
        """Reassign unique, gap-free ids to every item (top-level + linked refs +
        submenu items). NextItems keep their local 0-based index."""
        counter = [0]

        def walk(item):
            item["id"] = counter[0]
            counter[0] += 1
            for field in ("HintItems", "ActiveItems", "InactiveItems"):
                for ref in item.get(field) or []:
                    walk(ref)
            for sub in item.get("_submenu_items") or []:
                walk(sub)
            for ci, child in enumerate(item.get("children") or []):
                child["id"] = ci
        for it in self.placed_items:
            walk(it)
        self._flash_status(f"Re-numbered {counter[0]} item id(s).")

    def _delete_item_at(self, index):
        if index is None or not (0 <= index < len(self.placed_items)):
            return
        deleted = self.placed_items.pop(index)
        freed = self._release_linked_items(deleted)
        self.selected_item_index = None
        self.dragging_item_index = None
        extra = f" ({len(freed)} linked item(s) kept)" if freed else ""
        self.message = f"Deleted {deleted.get('name', 'item')}.{extra}"
