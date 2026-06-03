import copy
import json
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

        # --- Details card (icon + properties) ---
        det_rect = pygame.Rect(rect.x + pad, header_bottom + pad, rect.w - pad * 2, 234)
        self._draw_card(screen, det_rect, (12, 15, 22), border_color=(56, 62, 76))

        # Interactive live preview (click to simulate in-tracker behaviour)
        icon_rect = pygame.Rect(det_rect.x + 16, det_rect.y + 16, 96, 96)
        self._draw_card(screen, icon_rect, (8, 9, 13), border_color=(56, 62, 76))
        self.modal_buttons["preview"] = icon_rect
        self._draw_item_preview(screen, icon_rect, item)
        self._text(screen, "L/R/wheel to test", (icon_rect.x - 2, icon_rect.bottom + 4), 11, self.COLORS["muted"])

        details = [
            ("Id", item["id"]),
            ("Name", item["name"]),
            ("Type", item.get("kind", "Item")),
            ("Position", f"x {item['x']} / y {item['y']}"),
            ("Sprite", f"row {item['row']} / column {item['column']}"),
            ("Active", item.get("isActive", False)),
            ("Opacity", item.get("opacity", 0.5)),
            ("Hint", item.get("hint") or "None"),
        ]
        info_x = icon_rect.right + 28
        value_x = info_x + 110
        info_y = det_rect.y + 18
        row_h = 26
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

    def _format_field_value(self, item, spec):
        value = item.get(spec["key"], spec["default"])
        if spec["type"] == "sprite":
            if value:
                return f"{value.get('sheet')} r{value.get('row')} c{value.get('column')}"
            return "same as item"
        if spec["type"] == "bool":
            return "Yes" if value else "No"
        if spec["type"] == "list":
            value = value or []
            text = ", ".join(str(v) for v in value)
            return text[:24] + "..." if len(text) > 24 else (text or "(empty)")
        if value in (None, ""):
            return "None"
        return str(value)

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

    def _handle_modal_click(self, mouse_position):
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
        self.message = f"Type set to {kind}."

    def _edit_field(self, field_key):
        item = self._selected_item()
        if not item:
            return
        spec = next((s for s in self._kind_fields(item.get("kind", "Item")) if s["key"] == field_key), None)
        if not spec:
            return
        ftype = spec["type"]
        current = item.get(field_key, spec["default"])
        label = spec["label"]
        if ftype == "bool":
            item[field_key] = not bool(current)
            self.message = f"{label} updated."
        elif ftype in ("int", "float"):
            def cb(value, it=item, fk=field_key, lbl=label):
                if value is None:
                    return
                it[fk] = value
                self.message = f"{lbl} updated."
            self._open_text_prompt(label, current if current is not None else 0, cb, kind=ftype, label=f"{label}:")
        elif ftype == "list":
            def cb(text, it=item, fk=field_key, lbl=label):
                it[fk] = [v.strip() for v in (text or "").split(",") if v.strip() != ""] or [""]
                self.message = f"{lbl} updated."
            self._open_text_prompt(label, ", ".join(str(v) for v in (current or [])), cb, label="Comma separated values:")
        elif ftype == "sprite":
            def apply(sheet, row, column, it=item, fk=field_key, lbl=label):
                it[fk] = {"sheet": sheet, "row": row, "column": column}
                self.message = f"{lbl} set to {sheet} r{row} c{column}."
            self._open_sprite_picker(label, apply)
        else:  # str / strnull
            def cb(text, it=item, fk=field_key, lbl=label, ft=ftype):
                it[fk] = text if text not in (None, "") else (None if ft == "strnull" else "")
                self.message = f"{lbl} updated."
            self._open_text_prompt(label, str(current or ""), cb, label=f"{label}:")

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
