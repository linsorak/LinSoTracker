import copy

import pygame


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

    def _close_check_modal(self):
        self.check_modal_open = False

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
        if check.get("Kind") == "Block":
            check["Kind"] = "SimpleCheck"
            check.pop("Checks", None)
            check.setdefault("Conditions", "True")
        else:
            check["Kind"] = "Block"
            check.pop("Conditions", None)
            check.setdefault("Checks", [])
        self.message = f"Check kind: {check['Kind']}."

    def _edit_check_field(self, key):
        check = self._selected_check()
        if not check:
            return
        if key == "Conditions":
            def sink(expr, c=check):
                c["Conditions"] = expr
            self._open_cond_graph(check.get("Conditions", ""),
                                  title=f"Check: {check.get('Name', '')}", sink=sink)
            return
        labels = {"Name": "Check name", "Zone": "Zone"}

        def cb(value):
            check[key] = value if value is not None else ""
            self.message = f"{labels.get(key, key)} updated."
        self._open_text_prompt(labels.get(key, key), str(check.get(key, "") or ""),
                               cb, label=f"{labels.get(key, key)}:")

    # ---- block sub-checks ------------------------------------------------
    def _add_block_check(self):
        check = self._selected_check()
        if not check or check.get("Kind") != "Block":
            return
        subs = check.setdefault("Checks", [])
        subs.append({"Id": self._next_check_id(subs), "Name": "New check", "Conditions": "True"})
        self.message = "Sub-check added."

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
        if key == "Conditions":
            def sink(expr, s=subs[sub_index]):
                s["Conditions"] = expr
            self._open_cond_graph(subs[sub_index].get("Conditions", ""),
                                  title=f"Sub-check: {subs[sub_index].get('Name', '')}", sink=sink)
            return

        def cb(value):
            subs[sub_index][key] = value if value is not None else ""
            self.message = f"Sub-check {key} updated."
        self._open_text_prompt(f"Sub-check {key}", str(subs[sub_index].get(key, "") or ""),
                               cb, label=f"{key}:")
