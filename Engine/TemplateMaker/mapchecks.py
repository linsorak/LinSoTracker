import copy
from tkinter import filedialog

import pygame


CHECK_CONDITION_FIELDS = (
    "Conditions", "OutOfLogicConditions",
    "ScoutableConditions", "UncertainConditions",
)

CHECK_CONDITION_LABELS = {
    "Conditions": "Logic condition (green)",
    "OutOfLogicConditions": "Out-of-logic condition (yellow)",
    "ScoutableConditions": "Scoutable condition (blue)",
    "UncertainConditions": "Uncertain condition (purple)",
}


class MapChecksMixin:
    """Editing the ChecksList of the selected map: add / move / delete / edit
    SimpleCheck and Block checks directly on the map canvas."""


    # ---- geometry --------------------------------------------------------
    def _map_pixel_from_screen(self, pos):
        if not self._map_view_active():
            return None
        if not self.map_view_rect.collidepoint(pos):
            return None
        bg_rect = self.last_bg_rect
        scale = bg_rect.w / self._canvas_size()[0]
        if scale <= 0:
            return None
        mx = int((pos[0] - bg_rect.x) / scale)
        my = int((pos[1] - bg_rect.y) / scale)
        return mx, my

    def _zoom_map(self, direction, pos):
        old = self.map_zoom
        factor = 1.2 if direction > 0 else (1 / 1.2)
        new = max(1.0, min(8.0, old * factor))
        if abs(new - old) < 1e-6:
            return
        # Keep the point under the cursor fixed: adjust pan around the canvas centre.
        inner = self.map_view_rect
        ratio = new / old
        ox = pos[0] - inner.centerx
        oy = pos[1] - inner.centery
        self.map_pan[0] = int((self.map_pan[0] - ox) * ratio + ox)
        self.map_pan[1] = int((self.map_pan[1] - oy) * ratio + oy)
        self.map_zoom = new
        if new <= 1.0:
            self.map_pan = [0, 0]

    def _reset_map_view(self):
        self.map_zoom = 1.0
        self.map_pan = [0, 0]

    def _check_index_at(self, pos):
        for index, rect in (self.check_screen_rects or {}).items():
            if rect.collidepoint(pos):
                return index
        return None

    def _current_checks(self):
        m = self._current_map()
        return m["data"].setdefault("ChecksList", []) if m else []

    def _next_check_id(self, checks):
        return max((c.get("Id", -1) for c in checks), default=-1) + 1

    # ---- add / move / delete --------------------------------------------
    def _add_check_at(self, pos):
        pixel = self._map_pixel_from_screen(pos)
        if pixel is None:
            return
        checks = self._current_checks()
        check = {
            "Id": self._next_check_id(checks),
            "Kind": "SimpleCheck",
            "Name": "New check",
            "Zone": "",
            "Positions": {"x": pixel[0], "y": pixel[1]},
            "Conditions": "True",
            "ItemCount": 1,
        }
        checks.append(check)
        self.selected_check_index = len(checks) - 1
        self.message = "Check added. Double-click to edit, Delete to remove."

    def _move_check(self, index, pos):
        pixel = self._map_pixel_from_screen(pos)
        if pixel is None:
            return
        checks = self._current_checks()
        if 0 <= index < len(checks):
            checks[index]["Positions"] = {"x": pixel[0], "y": pixel[1]}

    def _delete_check(self, index):
        checks = self._current_checks()
        if 0 <= index < len(checks):
            removed = checks.pop(index)
            self.selected_check_index = None
            self.dragging_check_index = None
            self.expanded_blocks = set()
            self.message = f"Deleted check '{removed.get('Name', '')}'."

    def _delete_selected_check(self):
        if self.selected_check_index is not None:
            self._delete_check(self.selected_check_index)

    # ---- check modal -----------------------------------------------------
    def _open_check_modal(self, index):
        checks = self._current_checks()
        if not (0 <= index < len(checks)):
            return
        self.selected_check_index = index
        self.check_modal_open = True
        self.check_sub_scroll = 0
        self.popup_item_scroll = 0

    def _close_check_modal(self):
        self.check_modal_open = False

    def _scroll_check_modal(self, direction):
        check = self._selected_check()
        if not check:
            return
        delta = -1 if direction > 0 else 1
        if check.get("Kind") == "Block":
            maximum = max(0, len(check.get("Checks", [])) - 1)
            self.check_sub_scroll = max(0, min(maximum, self.check_sub_scroll + delta))
        elif check.get("Kind") == "MapPopup":
            maximum = max(0, len(check.get("Items", [])) - 1)
            self.popup_item_scroll = max(0, min(maximum, self.popup_item_scroll + delta))

    def _selected_check(self):
        checks = self._current_checks()
        idx = self.selected_check_index
        if idx is not None and 0 <= idx < len(checks):
            return checks[idx]
        return None

    def _toggle_check_kind(self):
        check = self._selected_check()
        if not check:
            return
        kind = check.get("Kind")
        if kind == "SimpleCheck":
            check["Kind"] = "Block"
            for field in CHECK_CONDITION_FIELDS:
                check.pop(field, None)
            check.pop("ItemCount", None)
            check.setdefault("Checks", [])
        elif kind == "Block":
            check["Kind"] = "MapPopup"
            check.pop("Checks", None)
            check.setdefault("Items", [])
            check.setdefault("VisibleCondition", "True")
            check.setdefault("SubMenuBackground", "")
        else:
            check["Kind"] = "SimpleCheck"
            check.pop("Checks", None)
            check.pop("Items", None)
            check.pop("VisibleCondition", None)
            check.pop("SubMenuBackground", None)
            check.setdefault("Conditions", "True")
            check.setdefault("ItemCount", 1)
        self.message = f"Check kind: {check['Kind']}."

    def _edit_check_field(self, key):
        check = self._selected_check()
        if not check:
            return
        if key == "ItemCount":
            self._open_item_count_prompt(check, "Check item count")
            return
        if key in CHECK_CONDITION_FIELDS:
            def sink(expr, c=check, field=key):
                if expr:
                    c[field] = expr
                else:
                    c.pop(field, None)
            self._open_cond_graph(
                check.get(key, ""),
                title=f"{CHECK_CONDITION_LABELS[key]}: {check.get('Name', '')}",
                sink=sink)
            return
        if key == "VisibleCondition":
            def sink(expr, c=check):
                c["VisibleCondition"] = expr or "True"
            self._open_cond_graph(check.get("VisibleCondition", "True"),
                                  title=f"Visible: {check.get('Name', '')}", sink=sink)
            return
        if key == "SubMenuBackground":
            path = filedialog.askopenfilename(
                title="Select popup image",
                filetypes=[("PNG image", "*.png"), ("All files", "*.*")]
            )
            if not path:
                return
            try:
                surface = pygame.image.load(path).convert_alpha()
            except Exception as exc:
                self.message = f"Could not load image: {exc}"
                return
            filename = f"{self._slugify(check.get('Name', 'popup')) or 'popup'}_popup.png"
            check["SubMenuBackground"] = filename
            check.setdefault("_popup_assets", {})["SubMenuBackground"] = {
                "path": path,
                "surface": surface,
                "file": filename,
            }
            self.message = "Popup image set."
            return
        labels = {
            "Name": "Check name",
            "Zone": "Zone",
            "Group": "Linked check group",
            "ItemCount": "Item count",
            **CHECK_CONDITION_LABELS,
            "SubMenuBackground": "Popup image filename",
            "VisibleCondition": "Visible condition",
        }

        def cb(value):
            check[key] = value if value is not None else ""
            self.message = f"{labels.get(key, key)} updated."
        self._open_text_prompt(labels.get(key, key), str(check.get(key, "") or ""),
                               cb, label=f"{labels.get(key, key)}:")

    def _open_item_count_prompt(self, target, title):
        def cb(value):
            target["ItemCount"] = max(1, int(value))
            self.message = "Item count updated."

        self._open_text_prompt(title, target.get("ItemCount", 1), cb, kind="int",
                               allow_empty=False, minvalue=1, label="Number of items:")

    # ---- block sub-checks ------------------------------------------------
    def _add_block_check(self):
        check = self._selected_check()
        if not check or check.get("Kind") != "Block":
            return
        subs = check.setdefault("Checks", [])
        subs.append({
            "Id": self._next_check_id(subs),
            "Name": "New check",
            "Conditions": "True",
            "ItemCount": 1,
        })
        self.message = "Sub-check added."

    def _move_block_check(self, sub_index, direction):
        check = self._selected_check()
        if not check or check.get("Kind") != "Block":
            return
        subs = check.get("Checks", [])
        target_index = sub_index + direction
        if not (0 <= sub_index < len(subs) and 0 <= target_index < len(subs)):
            return
        subs[sub_index], subs[target_index] = subs[target_index], subs[sub_index]
        visible_rows = max(1, getattr(self, "check_sub_visible_rows", 1))
        if target_index < self.check_sub_scroll:
            self.check_sub_scroll = target_index
        elif target_index >= self.check_sub_scroll + visible_rows:
            self.check_sub_scroll = target_index - visible_rows + 1
        self.message = f"Sub-check moved to position {target_index + 1}."

    def _delete_block_check(self, sub_index):
        check = self._selected_check()
        if not check or check.get("Kind") != "Block":
            return
        subs = check.get("Checks", [])
        if 0 <= sub_index < len(subs):
            subs.pop(sub_index)
            self.message = "Sub-check removed."

    def _edit_block_check_field(self, sub_index, key):
        check = self._selected_check()
        if not check or check.get("Kind") != "Block":
            return
        subs = check.get("Checks", [])
        if not (0 <= sub_index < len(subs)):
            return
        if key == "ItemCount":
            self._open_item_count_prompt(subs[sub_index], "Sub-check item count")
            return
        if key in CHECK_CONDITION_FIELDS:
            def sink(expr, s=subs[sub_index], field=key):
                if expr:
                    s[field] = expr
                else:
                    s.pop(field, None)
            self._open_cond_graph(
                subs[sub_index].get(key, ""),
                title=f"{CHECK_CONDITION_LABELS[key]}: {subs[sub_index].get('Name', '')}",
                sink=sink)
            return

        def cb(value):
            subs[sub_index][key] = value if value is not None else ""
            self.message = f"Sub-check {key} updated."
        self._open_text_prompt(f"Sub-check {key}", str(subs[sub_index].get(key, "") or ""),
                               cb, label=f"{key}:")

    # ---- popup items -----------------------------------------------------
    def _add_popup_item(self):
        check = self._selected_check()
        if not check or check.get("Kind") != "MapPopup":
            return
        items = check.setdefault("Items", [])
        items.append({"Item": "", "Positions": {"x": 32, "y": 32}, "Scale": 1.0})
        self.message = "Popup item added."

    def _delete_popup_item(self, item_index):
        check = self._selected_check()
        if not check or check.get("Kind") != "MapPopup":
            return
        items = check.get("Items", [])
        if 0 <= item_index < len(items):
            items.pop(item_index)
            self.message = "Popup item removed."

    def _edit_popup_item_field(self, item_index, key):
        check = self._selected_check()
        if not check or check.get("Kind") != "MapPopup":
            return
        items = check.get("Items", [])
        if not (0 <= item_index < len(items)):
            return
        item = items[item_index]
        if key == "Item":
            def set_item(name):
                item["Item"] = name
                item.pop("Name", None)
                self.message = f"Popup item set to {name}."

            self._open_name_picker(
                "Pick a popup item", self._all_template_item_names(), set_item)
            return
        elif key == "Positions":
            pos = item.setdefault("Positions", {"x": 0, "y": 0})
            initial = f"{pos.get('x', 0)},{pos.get('y', 0)}"
            label = "Item position x,y"
            kind = "str"
        else:
            initial = item.get("Scale", 1.0)
            label = "Item scale"
            kind = "float"

        def cb(value):
            if key == "Positions":
                parts = [p.strip() for p in str(value).split(",")]
                if len(parts) == 2 and all(p.lstrip("-").isdigit() for p in parts):
                    item["Positions"] = {"x": int(parts[0]), "y": int(parts[1])}
                else:
                    self.message = "Enter x,y."
                    return
            elif key == "Scale":
                try:
                    item["Scale"] = max(0.1, float(value))
                except (TypeError, ValueError):
                    self.message = "Enter a valid scale."
                    return
            else:
                item["Item"] = value or ""
            self.message = f"Popup item {key} updated."
        self._open_text_prompt(label, initial, cb, kind=kind, label=f"{label}:")
