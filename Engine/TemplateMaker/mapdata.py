import os
from tkinter import filedialog

import pygame


class MapDataMixin:
    """Edit the global map section-5 extras: check marker sizes, the checks
    counter position, action helpers (do('X') logic), and the rule toggles
    (RulesOptions) + their list windows (RulesOptionsLists)."""

    def _open_map_data(self):
        self._ensure_map_extras()
        self.map_data_open = True
        self.map_data_scroll = 0

    # ---- editing helpers -------------------------------------------------
    def _edit_extra_int(self, container_key, sub, label):
        cont = self.maps_extra.setdefault(container_key, {})

        def cb(value):
            if value is not None:
                cont[sub] = value
                self.message = f"{label} updated."
        self._open_text_prompt(label, int(cont.get(sub, 0)), cb, kind="int", label=f"{label}:")

    def _add_action_condition(self):
        def name_cb(name):
            if not name:
                return

            def expr_cb(expr):
                self.maps_extra.setdefault("ActionsConditions", {})[name] = expr or ""
                self.message = f"Action '{name}' added."
            self._open_text_prompt("Condition expression", "", expr_cb, label="e.g. have('Bow') and do('CanX'):")
        self._open_text_prompt("Action name", "", name_cb, allow_empty=False, label="do('NAME'):")

    def _edit_action_condition(self, name):
        ac = self.maps_extra.get("ActionsConditions", {})

        def cb(value):
            ac[name] = value or ""
            self.message = f"Action '{name}' updated."
        self._open_text_prompt(f"Edit {name}", str(ac.get(name, "")), cb, label="Expression:")

    def _delete_action_condition(self, name):
        self.maps_extra.get("ActionsConditions", {}).pop(name, None)
        self.message = f"Action '{name}' removed."

    # ---- maps-list button (switch between maps on the tracker) -----------
    def _enable_maps_list(self):
        self.maps_extra["MapsList"] = {
            "MapListButtonLabelRect": {"x": 10, "y": 10, "w": 160, "h": 32},
            "MapsListBox": {
                "SubMenuBackground": "map_list.png",
                "DrawBoxRect": {"x": 195, "y": 150, "w": 363, "h": 455},
                "LabelY": 100,
                "LeftArrow": {"Image": "left-arrow.png", "Positions": {"x": 311, "y": 612}},
                "RightArrow": {"Image": "right-arrow.png", "Positions": {"x": 415, "y": 612}},
            },
        }
        self.message = "Maps-list button enabled."

    def _disable_maps_list(self):
        self.maps_extra.pop("MapsList", None)
        self.message = "Maps-list button removed."

    def _edit_mapslist_rect(self, path, fields):
        """path: dotted keys into MapsList; fields: 'x,y,w,h' or 'x,y'."""
        ml = self.maps_extra.get("MapsList")
        if not ml:
            return
        node = ml
        keys = path.split(".")
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        last = keys[-1]
        cur = node.get(last, {})
        keyset = fields.split(",")
        initial = ",".join(str(cur.get(k, 0)) for k in keyset)

        def cb(value):
            parts = [p.strip() for p in str(value).split(",")]
            if len(parts) == len(keyset) and all(p.lstrip("-").isdigit() for p in parts):
                node[last] = {k: int(p) for k, p in zip(keyset, parts)}
                self.message = f"{last} updated."
            else:
                self.message = f"Enter {fields}."
        self._open_text_prompt(last, initial, cb, label=f"{fields}:")

    # ---- rule Actions editor --------------------------------------------
    ACTION_TYPES = ("SetLeftClick", "SetRightClick", "SetWheelClick", "ResetItem", "SetRule")

    def _open_actions_editor(self, rule_index):
        rules = self.maps_extra.get("RulesOptions", [])
        if 0 <= rule_index < len(rules):
            self.actions_editor_rule = rule_index
            self.actions_editor_open = True

    def _current_actions(self):
        rules = self.maps_extra.get("RulesOptions", [])
        if self.actions_editor_rule is not None and 0 <= self.actions_editor_rule < len(rules):
            rule = rules[self.actions_editor_rule]
            if rule.get("Actions") is None:
                rule["Actions"] = []
            return rule.setdefault("Actions", [])
        return []

    def _discard_empty_set_rule_actions(self):
        """Remove obsolete no-op SetRule entries created by older Maker builds."""
        removed = 0
        for rule in self.maps_extra.get("RulesOptions", []):
            actions = rule.get("Actions")
            if not isinstance(actions, list):
                continue
            kept = []
            for action in actions:
                target = action.get("SetRule") if isinstance(action, dict) else None
                if isinstance(target, dict) and not str(target.get("RuleName") or "").strip():
                    removed += 1
                    continue
                kept.append(action)
            if len(kept) != len(actions):
                rule["Actions"] = kept or None
        return removed

    def _add_action(self, atype):
        if atype == "SetRule":
            def cb(name):
                if name:
                    self._current_actions().append(
                        {"SetRule": {"Active": True, "RuleName": name}})
                    self.message = f"{atype} added."
            self._open_name_picker("Pick a rule", self._all_rule_names(), cb)
            return

        def cb(name):
            if not name:
                return
            data = {"Item": name}
            if atype != "ResetItem":
                data["Counter"] = 1
            self._current_actions().append({atype: data})
            self.message = f"{atype} added."
        self._open_name_picker("Pick an item", self._all_item_names(), cb)

    def _all_item_names(self):
        return self._all_template_item_names()

    def _all_rule_names(self):
        return sorted({r.get("Name", "") for r in self.maps_extra.get("RulesOptions", []) if r.get("Name")})

    def _action_set_item(self, index):
        acts = self._current_actions()
        if not (0 <= index < len(acts)):
            return
        data = acts[index][next(iter(acts[index]))]

        def cb(name):
            data["Item"] = name
            self.message = f"Item set to {name}."
        self._open_name_picker("Pick an item", self._all_item_names(), cb)

    def _action_set_counter(self, index):
        acts = self._current_actions()
        if not (0 <= index < len(acts)):
            return
        data = acts[index][next(iter(acts[index]))]

        def cb(value):
            if value is not None:
                data["Counter"] = value
        self._open_text_prompt("Counter", int(data.get("Counter", 1)), cb, kind="int", label="Times:")

    def _action_set_rulename(self, index):
        acts = self._current_actions()
        if not (0 <= index < len(acts)):
            return
        data = acts[index].get("SetRule")
        if data is None:
            return

        def cb(name):
            data["RuleName"] = name
            self.message = f"Target rule: {name}."
        self._open_name_picker("Pick a rule", self._all_rule_names(), cb)

    def _action_toggle_active(self, index):
        acts = self._current_actions()
        if 0 <= index < len(acts) and "SetRule" in acts[index]:
            d = acts[index]["SetRule"]
            d["Active"] = not d.get("Active", False)

    def _delete_action(self, index):
        acts = self._current_actions()
        if 0 <= index < len(acts):
            acts.pop(index)

    def _draw_actions_editor(self, screen):
        rules = self.maps_extra.get("RulesOptions", [])
        if self.actions_editor_rule is None or self.actions_editor_rule >= len(rules):
            self.actions_editor_open = False
            return
        rule = rules[self.actions_editor_rule]
        sw, sh = screen.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        screen.blit(overlay, (0, 0))
        modal = pygame.Rect(sw // 2 - 340, sh // 2 - 250, 680, 500)
        self._draw_popup(screen, modal, radius=12)
        self.actions_editor_buttons = {}
        pad = 18
        x = modal.x + pad
        self._text(screen, f"Actions - {rule.get('Name', '')[:30]}", (x, modal.y + 14), 22, self.COLORS["gold"])
        self._text(screen, "Triggered when the rule is applied", (x, modal.y + 42), 12, self.COLORS["muted"])
        # add buttons
        bx = x
        for atype in self.ACTION_TYPES:
            b = pygame.Rect(bx, modal.y + 62, 128, 26)
            self.actions_editor_buttons[f"add_{atype}"] = b
            self._draw_button(screen, b, atype, (40, 90, 150), hover=(self.hover_modal_key == f"add_{atype}"))
            bx += 132
        # list
        y = modal.y + 100
        for i, action in enumerate(self._current_actions()):
            atype = next(iter(action))
            data = action[atype]
            row = pygame.Rect(x, y, modal.w - pad * 2, 38)
            self._draw_card(screen, row, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=6)
            self._text(screen, atype, (row.x + 8, row.y + 4), 13, self.COLORS["gold"])
            del_btn = pygame.Rect(row.right - 28, row.y + 6, 24, 26)
            self.actions_editor_buttons[f"del_{i}"] = del_btn
            pygame.draw.rect(screen, self.COLORS["red"], del_btn)
            self._text(screen, "x", (del_btn.x + 8, del_btn.y + 4), 14, self.COLORS["line_light"])
            if atype == "SetRule":
                rb = pygame.Rect(row.x + 8, row.y + 18, 320, 16)
                ab = pygame.Rect(rb.right + 10, row.y + 12, 90, 22)
                self.actions_editor_buttons[f"rule_{i}"] = rb
                self.actions_editor_buttons[f"active_{i}"] = ab
                self._text(screen, f"rule: {data.get('RuleName', '') or '(click)'}", (rb.x, rb.y), 13, self.COLORS["line_light"])
                act = data.get("Active", False)
                self._draw_button(screen, ab, f"Active:{'Y' if act else 'N'}",
                                  (36, 124, 87) if act else (70, 74, 86), hover=(self.hover_modal_key == f"active_{i}"))
            else:
                ib = pygame.Rect(row.x + 8, row.y + 18, 300, 16)
                self.actions_editor_buttons[f"item_{i}"] = ib
                self._text(screen, f"item: {data.get('Item', '') or '(click)'}", (ib.x, ib.y), 13, self.COLORS["line_light"])
                if atype != "ResetItem":
                    cb_ = pygame.Rect(ib.right + 10, row.y + 12, 90, 22)
                    self.actions_editor_buttons[f"counter_{i}"] = cb_
                    self._draw_button(screen, cb_, f"x{data.get('Counter', 1)}", (70, 74, 86),
                                      hover=(self.hover_modal_key == f"counter_{i}"))
            y += 44
        close_btn = pygame.Rect(modal.right - pad - 100, modal.bottom - 44, 100, 30)
        self.actions_editor_buttons["close"] = close_btn
        self._draw_button(screen, close_btn, "Close", (36, 124, 87), hover=(self.hover_modal_key == "close"))

    def _handle_actions_editor_click(self, mouse_position):
        for key, rect in self.actions_editor_buttons.items():
            if not rect.collidepoint(mouse_position):
                continue
            if key == "close":
                self.actions_editor_open = False
            elif key.startswith("add_"):
                self._add_action(key[len("add_"):])
            elif key.startswith("del_"):
                self._delete_action(int(key.rsplit("_", 1)[1]))
            elif key.startswith("item_"):
                self._action_set_item(int(key.rsplit("_", 1)[1]))
            elif key.startswith("counter_"):
                self._action_set_counter(int(key.rsplit("_", 1)[1]))
            elif key.startswith("rule_"):
                self._action_set_rulename(int(key.rsplit("_", 1)[1]))
            elif key.startswith("active_"):
                self._action_toggle_active(int(key.rsplit("_", 1)[1]))
            return True
        return True

    # ---- HideChecks editor ----------------------------------------------
    def _open_hide_editor(self, rule_index):
        rules = self.maps_extra.get("RulesOptions", [])
        if 0 <= rule_index < len(rules):
            self.hide_editor_rule = rule_index
            self.hide_editor_entry = None
            self.hide_editor_scroll = 0
            self.hide_editor_open = True

    def _current_hide(self):
        rules = self.maps_extra.get("RulesOptions", [])
        if self.hide_editor_rule is not None and 0 <= self.hide_editor_rule < len(rules):
            r = rules[self.hide_editor_rule]
            if r.get("HideChecks") is None:
                r["HideChecks"] = []
            return r["HideChecks"]
        return []

    def _all_check_names(self, entry=None):
        """Checks addressable by a HideChecks entry, across every map."""
        names = set()
        entry = entry or {}
        kind = entry.get("Kind", "SimpleCheck")
        block_name = entry.get("Name")
        for map_model in self.maps:
            for check in map_model["data"].get("ChecksList", []):
                if kind == "Block":
                    if check.get("Kind") == "Block" and (not block_name or check.get("Name") == block_name):
                        names.update(sub.get("Name") for sub in check.get("Checks", []) if sub.get("Name"))
                elif check.get("Kind") == "SimpleCheck" and check.get("Name"):
                    names.add(check["Name"])
        return sorted(names)

    def _all_block_names(self):
        return sorted({
            check.get("Name")
            for map_model in self.maps
            for check in map_model["data"].get("ChecksList", [])
            if check.get("Kind") == "Block" and check.get("Name")
        })

    def _add_hide_entry(self, kind):
        entry = {"Kind": kind, "Checks": []}
        if kind == "Block":
            entry["Name"] = ""
        self._current_hide().append(entry)

    def _delete_hide_entry(self, index):
        hide = self._current_hide()
        if 0 <= index < len(hide):
            hide.pop(index)

    def _toggle_hide_kind(self, index):
        hide = self._current_hide()
        if not (0 <= index < len(hide)):
            return
        e = hide[index]
        if e.get("Kind") == "Block":
            e["Kind"] = "SimpleCheck"
            e.pop("Name", None)
        else:
            e["Kind"] = "Block"
            e.setdefault("Name", "")
        e["Checks"] = []

    def _edit_hide_blockname(self, index):
        hide = self._current_hide()
        if not (0 <= index < len(hide)):
            return

        def cb(value):
            entry = hide[index]
            if entry.get("Name") != value:
                entry["Checks"] = []
            entry["Name"] = value or ""

        self._open_name_picker("Pick a block", self._all_block_names(), cb)

    def _draw_hide_editor(self, screen):
        rules = self.maps_extra.get("RulesOptions", [])
        if self.hide_editor_rule is None or self.hide_editor_rule >= len(rules):
            self.hide_editor_open = False
            return
        rule = rules[self.hide_editor_rule]
        sw, sh = screen.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        screen.blit(overlay, (0, 0))
        modal = pygame.Rect(sw // 2 - 360, sh // 2 - 270, 720, 540)
        self._draw_popup(screen, modal, radius=12)
        self.hide_editor_buttons = {}
        self._scrollbars.pop("hide_editor", None)
        pad = 18
        x = modal.x + pad
        self._text(screen, f"Hidden checks - {rule.get('Name', '')[:30]}", (x, modal.y + 14), 22, self.COLORS["gold"])
        self._text(screen, "Checks hidden while this rule is active", (x, modal.y + 42), 12, self.COLORS["muted"])
        close_btn = pygame.Rect(modal.right - pad - 90, modal.y + 12, 90, 28)
        self.hide_editor_buttons["close"] = close_btn
        self._draw_button(screen, close_btn, "Close", (36, 124, 87), hover=(self.hover_modal_key == "close"))

        if self.hide_editor_entry is not None:
            self._draw_hide_picker(screen, modal, x, pad)
            return

        # entry add buttons
        ab = pygame.Rect(x, modal.y + 64, 150, 26)
        self.hide_editor_buttons["add_SimpleCheck"] = ab
        self._draw_button(screen, ab, "+ Simple check", (40, 90, 150), hover=(self.hover_modal_key == "add_SimpleCheck"))
        bb = pygame.Rect(ab.right + 8, modal.y + 64, 150, 26)
        self.hide_editor_buttons["add_Block"] = bb
        self._draw_button(screen, bb, "+ Block", (95, 70, 135), hover=(self.hover_modal_key == "add_Block"))

        entries = self._current_hide()
        view = pygame.Rect(
            x, modal.y + 100, modal.w - pad * 2,
            modal.bottom - (modal.y + 100) - 14,
        )
        row_h = 56
        content_h = len(entries) * row_h
        self.hide_editor_max_scroll = max(0, content_h - view.h)
        self.hide_editor_scroll = max(
            0, min(self.hide_editor_scroll, self.hide_editor_max_scroll))
        previous_clip = screen.get_clip()
        screen.set_clip(view)
        for i, e in enumerate(entries):
            y = view.y + i * row_h - self.hide_editor_scroll
            if y + 50 <= view.y or y >= view.bottom:
                continue
            is_block = e.get("Kind") == "Block"
            card = pygame.Rect(x, y, view.w - 10, 50)
            self._draw_card(screen, card, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=6)
            kb = pygame.Rect(card.x + 8, card.y + 8, 96, 22)
            self.hide_editor_buttons[f"kind_{i}"] = kb
            self._draw_button(screen, kb, e.get("Kind", ""), (95, 70, 135) if is_block else (40, 90, 150),
                              hover=(self.hover_modal_key == f"kind_{i}"))
            if is_block:
                nb = pygame.Rect(kb.right + 8, card.y + 8, 200, 22)
                self.hide_editor_buttons[f"name_{i}"] = nb
                pygame.draw.rect(screen, (20, 24, 34), nb)
                self._text(screen, e.get("Name", "") or "(block name)", (nb.x + 6, nb.y + 4), 13, self.COLORS["line_light"])
            cb_ = pygame.Rect(card.right - 150, card.y + 8, 110, 22)
            self.hide_editor_buttons[f"checks_{i}"] = cb_
            self._draw_button(screen, cb_, f"Checks ({len(e.get('Checks') or [])})", (70, 74, 86),
                              hover=(self.hover_modal_key == f"checks_{i}"))
            db = pygame.Rect(card.right - 30, card.y + 8, 24, 22)
            self.hide_editor_buttons[f"del_{i}"] = db
            pygame.draw.rect(screen, self.COLORS["red"], db)
            self._text(screen, "x", (db.x + 8, db.y + 4), 14, self.COLORS["line_light"])
            self._text(screen, ", ".join(e.get("Checks") or [])[:80], (card.x + 8, card.y + 32), 11, self.COLORS["muted"])
        screen.set_clip(previous_clip)
        track = pygame.Rect(view.right - 5, view.y, 5, view.h)
        self._register_scrollbar(
            screen, "hide_editor", track, self.hide_editor_scroll,
            self.hide_editor_max_scroll, content_h, view.h)

    def _draw_hide_picker(self, screen, modal, x, pad):
        entry = self._current_hide()[self.hide_editor_entry]
        chosen = set(entry.get("Checks") or [])
        self._text(screen, "Toggle checks in this entry", (x, modal.y + 64), 13, self.COLORS["gold"])
        back = pygame.Rect(modal.right - pad - 90, modal.y + 60, 90, 24)
        self.hide_editor_buttons["pick_back"] = back
        self._draw_button(screen, back, "Done", (36, 124, 87), hover=(self.hover_modal_key == "pick_back"))
        area = pygame.Rect(x, modal.y + 92, modal.w - pad * 2, modal.bottom - (modal.y + 92) - 14)
        self._draw_card(screen, area, (10, 12, 18), border_color=(56, 62, 76), radius=8)
        names = self._all_check_names(entry)
        view = area.inflate(-8, -8)
        row_h = 26
        content_h = len(names) * row_h
        max_scroll = max(0, content_h - view.h)
        self.hide_editor_scroll = max(0, min(self.hide_editor_scroll, max_scroll))
        self.hide_editor_max_scroll = max_scroll
        prev = screen.get_clip()
        screen.set_clip(view)
        for i, nm in enumerate(names):
            ry = view.y + i * row_h - self.hide_editor_scroll
            if ry + row_h <= view.y or ry >= view.bottom:
                continue
            row = pygame.Rect(view.x, ry, view.w, row_h - 2)
            self.hide_editor_buttons[f"pickname_{i}"] = row
            on = nm in chosen
            if on:
                pygame.draw.rect(screen, (28, 70, 45), row)
            elif self.hover_modal_key == f"pickname_{i}":
                pygame.draw.rect(screen, self.COLORS["panel_alt"], row)
            mk = pygame.Rect(row.x + 6, row.y + 5, 14, 14)
            pygame.draw.rect(screen, self.COLORS["green"] if on else (56, 62, 76), mk, 2)
            self._text(screen, nm, (row.x + 28, row.y + 4), 13, self.COLORS["line_light"])
        screen.set_clip(prev)
        track = pygame.Rect(area.right - 7, view.y, 4, view.h)
        self._register_scrollbar(screen, "hide_editor", track, self.hide_editor_scroll, max_scroll, content_h, view.h)

    def _handle_hide_editor_click(self, mouse_position):
        if self.hide_editor_entry is not None:
            entry = self._current_hide()[self.hide_editor_entry]
            names = self._all_check_names(entry)
            for key, rect in self.hide_editor_buttons.items():
                if not rect.collidepoint(mouse_position):
                    continue
                if key == "pick_back":
                    self.hide_editor_entry = None
                    self.hide_editor_scroll = 0
                elif key == "close":
                    self.hide_editor_open = False
                elif key.startswith("pickname_"):
                    nm = names[int(key.rsplit("_", 1)[1])]
                    entry = self._current_hide()[self.hide_editor_entry]
                    checks = entry.setdefault("Checks", [])
                    if nm in checks:
                        checks.remove(nm)
                    else:
                        checks.append(nm)
                return True
            return True
        for key, rect in self.hide_editor_buttons.items():
            if not rect.collidepoint(mouse_position):
                continue
            if key == "close":
                self.hide_editor_open = False
            elif key.startswith("add_"):
                self._add_hide_entry(key[len("add_"):])
            elif key.startswith("kind_"):
                self._toggle_hide_kind(int(key.rsplit("_", 1)[1]))
            elif key.startswith("name_"):
                self._edit_hide_blockname(int(key.rsplit("_", 1)[1]))
            elif key.startswith("checks_"):
                self.hide_editor_entry = int(key.rsplit("_", 1)[1])
                self.hide_editor_scroll = 0
            elif key.startswith("del_"):
                self._delete_hide_entry(int(key.rsplit("_", 1)[1]))
            return True
        return True

    def _import_mapslist_bg(self):
        ml = self.maps_extra.get("MapsList")
        if not ml:
            return
        path = filedialog.askopenfilename(title="Maps-list background",
                                          filetypes=[("PNG image", "*.png"), ("All files", "*.*")])
        if not path:
            return
        try:
            surface = pygame.image.load(path).convert_alpha()
        except Exception as exc:
            self.message = f"Could not load image: {exc}"
            return
        fname = "maps_list_bg.png"
        ml.setdefault("MapsListBox", {})["SubMenuBackground"] = fname
        self.maps_extra_assets[fname] = surface
        self.message = "Maps-list background set."

    def _edit_mapslist_labely(self):
        ml = self.maps_extra.get("MapsList")
        if not ml:
            return
        box = ml.setdefault("MapsListBox", {})

        def cb(value):
            if value is not None:
                box["LabelY"] = value
                self.message = "Maps-list LabelY updated."
        self._open_text_prompt("Maps-list LabelY", int(box.get("LabelY", 0)), cb, kind="int", label="Y:")

    def _add_rules_list(self):
        def cb(name):
            if not name:
                return
            self.maps_extra.setdefault("RulesOptionsLists", []).append({
                "Name": name,
                "ButtonRect": {"x": 10, "y": 10, "w": 129, "h": 32},
                "ListBox": {
                    "SubMenuBackground": "map_list.png",
                    "DrawBoxRect": {"x": 195, "y": 150, "w": 363, "h": 455},
                    "LabelY": 100,
                    "LeftArrow": {"Image": "left-arrow.png", "Positions": {"x": 311, "y": 612}},
                    "RightArrow": {"Image": "right-arrow.png", "Positions": {"x": 415, "y": 612}},
                },
            })
            self.message = f"Rules list '{name}' added."
        self._open_text_prompt("Rules list name", "", cb, allow_empty=False, label="Name:")

    def _edit_rules_list_name(self, index):
        lists = self.maps_extra.get("RulesOptionsLists", [])
        if not (0 <= index < len(lists)):
            return

        old = lists[index].get("Name", "")

        def cb(value):
            if value:
                lists[index]["Name"] = value
                for r in self.maps_extra.get("RulesOptions", []):
                    if r.get("ParentListName") == old:
                        r["ParentListName"] = value
                if self.selected_rules_list == old:
                    self.selected_rules_list = value
                self.message = "Rules list renamed."
        self._open_text_prompt("Rename rules list", old, cb, label="Name:")

    def _delete_rules_list(self, index):
        lists = self.maps_extra.get("RulesOptionsLists", [])
        if 0 <= index < len(lists):
            removed = lists.pop(index)
            # drop its rules too
            name = removed.get("Name", "")
            self.maps_extra["RulesOptions"] = [r for r in self.maps_extra.get("RulesOptions", [])
                                               if r.get("ParentListName") != name]
            if self.selected_rules_list == name:
                self.selected_rules_list = None
            self.message = "Rules list + its rules removed."

    def _add_rule_option(self):
        lists = self.maps_extra.get("RulesOptionsLists", [])
        parent = self.selected_rules_list or (lists[0]["Name"] if lists else "")
        if not parent:
            self.message = "Create a rules list first."
            return

        def cb(name):
            if not name:
                return
            self.maps_extra.setdefault("RulesOptions", []).append({
                "Name": name, "HideChecks": None, "Active": True, "ParentListName": parent,
            })
            self.message = f"Rule '{name}' added to {parent}."
        self._open_text_prompt(f"Rule name (in {parent})", "", cb, allow_empty=False, label="Name:")

    def _toggle_rule_active(self, index):
        rules = self.maps_extra.get("RulesOptions", [])
        if 0 <= index < len(rules):
            rules[index]["Active"] = not rules[index].get("Active", False)

    def _edit_rule_field(self, index, key):
        rules = self.maps_extra.get("RulesOptions", [])
        if not (0 <= index < len(rules)):
            return

        def cb(value):
            rules[index][key] = value if value is not None else ""
            self.message = f"Rule {key} updated."
        self._open_text_prompt(f"Rule {key}", str(rules[index].get(key, "") or ""), cb, label=f"{key}:")

    def _delete_rule_option(self, index):
        rules = self.maps_extra.get("RulesOptions", [])
        if 0 <= index < len(rules):
            rules.pop(index)
            self.message = "Rule removed."

    def _toggle_rule_clickable(self, index):
        rules = self.maps_extra.get("RulesOptions", [])
        if 0 <= index < len(rules):
            rules[index]["CanBeClickable"] = not rules[index].get("CanBeClickable", False)

    def _edit_rule_exclusive(self, index):
        rules = self.maps_extra.get("RulesOptions", [])
        if not (0 <= index < len(rules)):
            return

        def cb(value):
            rules[index]["ExclusiveGroup"] = value or None
            self.message = "Exclusive group updated."
        self._open_text_prompt("Exclusive group", str(rules[index].get("ExclusiveGroup") or ""),
                               cb, label="Group name (blank = none):")

    def _edit_rule_json(self, index, key):
        rules = self.maps_extra.get("RulesOptions", [])
        if not (0 <= index < len(rules)):
            return
        import json as _json

        def cb(value):
            txt = (value or "").strip()
            if not txt:
                rules[index][key] = None
                self.message = f"{key} cleared."
                return
            try:
                rules[index][key] = _json.loads(txt)
                self.message = f"{key} updated."
            except Exception:
                self.message = f"Invalid JSON for {key}."
        current = rules[index].get(key)
        initial = _json.dumps(current) if current else ""
        self._open_text_prompt(f"{key} (JSON)", initial, cb, label=f"{key} as JSON list:")

    # ---- drawing ---------------------------------------------------------
    def _draw_map_data_modal(self, screen):
        e = self.maps_extra
        sw, sh = screen.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        screen.blit(overlay, (0, 0))
        w = min(960, sw - 80); h = min(760, sh - 80)
        modal = pygame.Rect((sw - w) // 2, (sh - h) // 2, w, h)
        self._draw_popup(screen, modal, radius=12)
        self.map_data_buttons = {}
        pad = 18
        self._text(screen, "Map data  (checks, logic, rules)", (modal.x + pad, modal.y + 14), 22, self.COLORS["gold"])
        close_btn = pygame.Rect(modal.right - pad - 90, modal.y + 14, 90, 28)
        self.map_data_buttons["close"] = close_btn
        self._draw_button(screen, close_btn, "Close", (36, 124, 87), hover=(self.hover_modal_key == "close"))

        view = pygame.Rect(modal.x + pad, modal.y + 54, modal.w - pad * 2, modal.h - 70)
        prev_clip = screen.get_clip()
        screen.set_clip(view)
        x = view.x
        y = view.y - self.map_data_scroll

        def label(text, yy):
            self._text(screen, text, (x, yy), 13, self.COLORS["gold"])

        def int_box(lbl, key, value, bx, by, w=70):
            box = pygame.Rect(bx, by, w, 26)
            self.map_data_buttons[key] = box
            pygame.draw.rect(screen, self.COLORS["panel_alt"], box)
            pygame.draw.rect(screen, (56, 62, 76), box, 1)
            self._text(screen, lbl, (box.x + 4, box.y - 15), 11, self.COLORS["muted"])
            self._text(screen, str(value), (box.x + 6, box.y + 4), 14, self.COLORS["line_light"])

        ssc = e.get("SizeSimpleCheck", {"w": 5, "h": 5})
        sgc = e.get("SizeGroupChecks", {"w": 16, "h": 16})
        cpt = e.get("CptChecksPosition", {"x": 10, "y": 10})
        label("CHECK MARKER SIZES", y); y += 28
        int_box("Simple w", "size_ssc_w", ssc.get("w", 5), x, y)
        int_box("Simple h", "size_ssc_h", ssc.get("h", 5), x + 90, y)
        int_box("Block w", "size_sgc_w", sgc.get("w", 16), x + 200, y)
        int_box("Block h", "size_sgc_h", sgc.get("h", 16), x + 290, y)
        y += 42
        label("CHECKS COUNTER POSITION", y); y += 28
        int_box("x", "cpt_x", cpt.get("x", 10), x, y)
        int_box("y", "cpt_y", cpt.get("y", 10), x + 90, y)
        y += 46

        # Maps-list button (switch maps on the tracker)
        ml = e.get("MapsList")
        label("MAPS-LIST BUTTON", y)
        toggle = pygame.Rect(view.right - 90, y - 4, 86, 22)
        self.map_data_buttons["ml_toggle"] = toggle
        self._draw_button(screen, toggle, "Remove" if ml else "Enable",
                          self.COLORS["red"] if ml else (36, 124, 87),
                          hover=(self.hover_modal_key == "ml_toggle"))
        y += 26
        if ml:
            blr = ml.get("MapListButtonLabelRect", {})
            box = ml.get("MapsListBox", {})
            dbr = box.get("DrawBoxRect", {})

            def ml_row(lbl, key, value):
                row = pygame.Rect(x, y, view.w, 26)
                self.map_data_buttons[key] = row
                pygame.draw.rect(screen, self.COLORS["panel_alt"], row)
                self._text(screen, lbl, (row.x + 6, row.y + 5), 12, self.COLORS["gold"])
                self._text(screen, str(value), (row.x + 200, row.y + 5), 12, self.COLORS["line_light"])
                return row
            ml_row("Button rect (x,y,w,h)", "ml_btnrect", f"{blr.get('x',0)},{blr.get('y',0)},{blr.get('w',0)},{blr.get('h',0)}"); y += 30
            ml_row("List box (x,y,w,h)", "ml_boxrect", f"{dbr.get('x',0)},{dbr.get('y',0)},{dbr.get('w',0)},{dbr.get('h',0)}"); y += 30
            ml_row("List label Y", "ml_labely", box.get("LabelY", 0)); y += 30
            ml_row("List background img", "ml_bg", box.get("SubMenuBackground", "")); y += 30
        y += 16

        # Rules lists -> click one to reveal its rules below it
        rlists = e.get("RulesOptionsLists", [])
        label(f"RULES LISTS ({len(rlists)})", y)
        addl = pygame.Rect(view.right - 30, y - 4, 26, 22)
        self.map_data_buttons["rol_add"] = addl
        self._draw_button(screen, addl, "+", (36, 124, 87), hover=(self.hover_modal_key == "rol_add"))
        y += 24
        all_rules = e.get("RulesOptions", [])
        for i, rl in enumerate(rlists):
            name = rl.get("Name", "")
            selected = (self.selected_rules_list == name)
            header = pygame.Rect(x, y, view.w, 34)
            nbtn = pygame.Rect(x, y, view.w - 70, 34)
            ebtn = pygame.Rect(view.right - 66, y + 3, 30, 28)
            dbtn = pygame.Rect(view.right - 32, y + 3, 28, 28)
            self.map_data_buttons[f"rol_sel_{i}"] = nbtn
            self.map_data_buttons[f"rol_edit_{i}"] = ebtn
            self.map_data_buttons[f"rol_del_{i}"] = dbtn
            pygame.draw.rect(screen, (44, 50, 68) if selected else self.COLORS["panel_alt"], header)
            pygame.draw.rect(screen, self.COLORS["gold"] if selected else (56, 62, 76), header, 1)
            count = sum(1 for r in all_rules if r.get("ParentListName") == name)
            self._text(screen, ("v  " if selected else ">  ") + name, (nbtn.x + 10, nbtn.y + 8), 16, self.COLORS["gold"] if selected else self.COLORS["line_light"])
            self._text(screen, f"{count} rule(s)", (nbtn.right - 90, nbtn.y + 10), 13, self.COLORS["muted"])
            pygame.draw.rect(screen, (70, 74, 86), ebtn)
            self._text(screen, "ren", (ebtn.x + 5, ebtn.y + 6), 12, self.COLORS["line_light"])
            pygame.draw.rect(screen, self.COLORS["red"], dbtn)
            self._text(screen, "x", (dbtn.x + 10, dbtn.y + 6), 14, self.COLORS["line_light"])
            y += 38

            # Expanded rules for the selected list, as readable cards
            if selected:
                bar = pygame.Rect(x + 14, y, view.w - 14, 24)
                addr = pygame.Rect(view.right - 30, y, 26, 22)
                self.map_data_buttons["ro_add"] = addr
                self._text(screen, "RULES IN THIS LIST", (bar.x, y + 4), 12, self.COLORS["gold"])
                self._draw_button(screen, addr, "+", (36, 124, 87), hover=(self.hover_modal_key == "ro_add"))
                y += 28
                for ri, ro in enumerate(all_rules):
                    if ro.get("ParentListName") != name:
                        continue
                    card = pygame.Rect(x + 14, y, view.w - 14, 58)
                    self._draw_card(screen, card, (20, 24, 34), border_color=(56, 62, 76), radius=8)
                    active = ro.get("Active", False)
                    chk = pygame.Rect(card.x + 10, card.y + 9, 20, 20)
                    self.map_data_buttons[f"ro_active_{ri}"] = chk
                    pygame.draw.rect(screen, (12, 14, 20), chk)
                    pygame.draw.rect(screen, self.COLORS["green"] if active else (90, 96, 110), chk, 2)
                    if active:
                        pygame.draw.line(screen, self.COLORS["green"], (chk.x + 4, chk.centery), (chk.centerx - 1, chk.bottom - 5), 3)
                        pygame.draw.line(screen, self.COLORS["green"], (chk.centerx - 1, chk.bottom - 5), (chk.right - 4, chk.y + 4), 3)
                    nrow = pygame.Rect(chk.right + 10, card.y + 6, card.w - 200, 24)
                    self.map_data_buttons[f"ro_name_{ri}"] = nrow
                    rule_name = ro.get("Name") or "(unnamed rule)"
                    self._text(screen, rule_name[:46], (nrow.x, nrow.y + 4), 16, self.COLORS["line_light"])
                    self._text(screen, "Active" if active else "Inactive at start",
                               (chk.right + 10, card.y + 32), 11, self.COLORS["muted"])
                    drow = pygame.Rect(card.right - 30, card.y + 6, 24, 24)
                    self.map_data_buttons[f"ro_del_{ri}"] = drow
                    pygame.draw.rect(screen, self.COLORS["red"], drow)
                    self._text(screen, "x", (drow.x + 8, drow.y + 4), 14, self.COLORS["line_light"])
                    # option buttons (right-aligned, labelled)
                    clk = ro.get("CanBeClickable", False)
                    opts = [("ro_clk_", "Clickable" if clk else "Not clickable", (36, 124, 87) if clk else (70, 74, 86)),
                            ("ro_excl_", f"Group: {(ro.get('ExclusiveGroup') or 'none')[:10]}", (70, 74, 86)),
                            ("ro_act_", f"Actions ({len(ro.get('Actions') or [])})", (40, 90, 150)),
                            ("ro_hide_", f"Hide ({len(ro.get('HideChecks') or [])})", (110, 80, 50))]
                    bw = 132
                    bx = card.right - 6 - bw * 4 - 6 * 3
                    for pk, lbl, col in opts:
                        b = pygame.Rect(bx, card.y + 30, bw, 22)
                        self.map_data_buttons[f"{pk}{ri}"] = b
                        self._draw_button(screen, b, lbl, col, hover=(self.hover_modal_key == f"{pk}{ri}"))
                        bx += bw + 6
                    y += 64
                y += 10
        y += 16

        # Action conditions (logic helpers)
        ac = e.get("ActionsConditions", {})
        label(f"ACTION CONDITIONS / do('X')  ({len(ac)})", y)
        adda = pygame.Rect(view.right - 30, y - 4, 26, 22)
        self.map_data_buttons["ac_add"] = adda
        self._draw_button(screen, adda, "+", (36, 124, 87), hover=(self.hover_modal_key == "ac_add"))
        y += 24
        for i, (name, expr) in enumerate(ac.items()):
            nbtn = pygame.Rect(x, y, 200, 26)
            ebtn = pygame.Rect(nbtn.right + 6, y, view.right - 34 - (nbtn.right + 6), 26)
            dbtn = pygame.Rect(view.right - 28, y, 24, 26)
            self.map_data_buttons[f"ac_edit_{name}"] = ebtn
            self.map_data_buttons[f"ac_del_{name}"] = dbtn
            pygame.draw.rect(screen, self.COLORS["panel_alt"], nbtn)
            self._text(screen, name[:24], (nbtn.x + 6, nbtn.y + 5), 13, self.COLORS["gold"])
            pygame.draw.rect(screen, self.COLORS["panel_alt"], ebtn)
            self._text(screen, str(expr)[:46], (ebtn.x + 6, ebtn.y + 5), 12, self.COLORS["muted"])
            pygame.draw.rect(screen, self.COLORS["red"], dbtn)
            self._text(screen, "x", (dbtn.x + 8, dbtn.y + 4), 14, self.COLORS["line_light"])
            y += 30

        content_bottom = y + self.map_data_scroll
        screen.set_clip(prev_clip)
        max_scroll = max(0, (content_bottom - view.y) - view.h)
        self.map_data_max_scroll = max_scroll
        self.map_data_scroll = max(0, min(self.map_data_scroll, max_scroll))
        track = pygame.Rect(modal.right - 12, view.y, 5, view.h)
        self._register_scrollbar(screen, "map_data", track, self.map_data_scroll, max_scroll,
                                 content_bottom - view.y, view.h)

    def _handle_map_data_click(self, mouse_position):
        for key, rect in self.map_data_buttons.items():
            if not rect.collidepoint(mouse_position):
                continue
            if key == "close":
                self.map_data_open = False
            elif key == "size_ssc_w":
                self._edit_extra_int("SizeSimpleCheck", "w", "Simple check w")
            elif key == "size_ssc_h":
                self._edit_extra_int("SizeSimpleCheck", "h", "Simple check h")
            elif key == "size_sgc_w":
                self._edit_extra_int("SizeGroupChecks", "w", "Block w")
            elif key == "size_sgc_h":
                self._edit_extra_int("SizeGroupChecks", "h", "Block h")
            elif key == "cpt_x":
                self._edit_extra_int("CptChecksPosition", "x", "Counter x")
            elif key == "cpt_y":
                self._edit_extra_int("CptChecksPosition", "y", "Counter y")
            elif key == "ml_toggle":
                if self.maps_extra.get("MapsList"):
                    self._disable_maps_list()
                else:
                    self._enable_maps_list()
            elif key == "ml_btnrect":
                self._edit_mapslist_rect("MapListButtonLabelRect", "x,y,w,h")
            elif key == "ml_boxrect":
                self._edit_mapslist_rect("MapsListBox.DrawBoxRect", "x,y,w,h")
            elif key == "ml_labely":
                self._edit_mapslist_labely()
            elif key == "ml_bg":
                self._import_mapslist_bg()
            elif key == "rol_add":
                self._add_rules_list()
            elif key.startswith("rol_sel_"):
                lists = self.maps_extra.get("RulesOptionsLists", [])
                idx = int(key.rsplit("_", 1)[1])
                if 0 <= idx < len(lists):
                    name = lists[idx].get("Name", "")
                    self.selected_rules_list = None if self.selected_rules_list == name else name
            elif key.startswith("rol_edit_"):
                self._edit_rules_list_name(int(key.rsplit("_", 1)[1]))
            elif key.startswith("rol_del_"):
                self._delete_rules_list(int(key.rsplit("_", 1)[1]))
            elif key == "ro_add":
                self._add_rule_option()
            elif key.startswith("ro_active_"):
                self._toggle_rule_active(int(key.rsplit("_", 1)[1]))
            elif key.startswith("ro_name_"):
                self._edit_rule_field(int(key.rsplit("_", 1)[1]), "Name")
            elif key.startswith("ro_del_"):
                self._delete_rule_option(int(key.rsplit("_", 1)[1]))
            elif key.startswith("ro_clk_"):
                self._toggle_rule_clickable(int(key.rsplit("_", 1)[1]))
            elif key.startswith("ro_excl_"):
                self._edit_rule_exclusive(int(key.rsplit("_", 1)[1]))
            elif key.startswith("ro_act_"):
                self._open_actions_editor(int(key.rsplit("_", 1)[1]))
            elif key.startswith("ro_hide_"):
                self._open_hide_editor(int(key.rsplit("_", 1)[1]))
            elif key == "ac_add":
                self._open_cond_builder()
            elif key.startswith("ac_edit_"):
                self._open_cond_builder(key[len("ac_edit_"):])
            elif key.startswith("ac_del_"):
                self._delete_action_condition(key[len("ac_del_"):])
            return True
        return True  # clicks inside the modal are swallowed
