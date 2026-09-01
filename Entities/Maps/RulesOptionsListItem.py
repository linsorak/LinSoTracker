import os

import pygame

from Engine import MainMenu
from Entities.Maps.CheckListItem import CheckListItem, wrap_popup_text


class RulesOptionsListItem(CheckListItem):
    def __init__(self, ident, name, position, tracker, checked, hide_checks, actions, active_on_start=False,
                 can_be_clickable=True, exclusive_group=None):
        super().__init__(ident, name, position, None, tracker)
        self.checked = checked
        # Default state comes from the template "Active" flag: presets reset the
        # rules they share to that default, not to the pre-activation state.
        self.base_checked = not active_on_start
        self.hide_checks = hide_checks
        self.actions = actions
        self.active_on_start = active_on_start
        self.can_be_clickable = can_be_clickable
        self.exclusive_group = exclusive_group
        self.update()
        self.set_hidden_checks()

    def update(self, render=True):
        if not render:
            return
        self.color = None
        font = self.tracker.core_service.get_font("mapFont")
        font_path = os.path.join(self.tracker.core_service.get_tracker_temp_path(), font["Name"])

        if self.checked:
            self.color = self.tracker.core_service.get_color_from_font(font, "Done")
        else:
            self.color = self.tracker.core_service.get_color_from_font(font, "Normal")

        temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32)
        temp_surface = temp_surface.convert_alpha()
        display_name = wrap_popup_text(
            self.name, font_path,
            font["Size"] * self.tracker.core_service.zoom,
            self.popup_wrap_width,
        )
        self.display_line_count = display_name.count("\n") + 1
        self.surface, self.position_draw = MainMenu.MainMenu.draw_text(
            text=display_name,
            font_name=font_path,
            color=self.color,
            font_size=font["Size"] * self.tracker.core_service.zoom,
            surface=temp_surface,
            align="center",
            position=(self.position["x"], self.position["y"]),
            outline=1 * self.tracker.core_service.zoom)

    def is_active(self):
        return not self.checked

    def is_exclusive_preset(self):
        return bool(self.exclusive_group)

    def iter_exclusive_group_rules(self):
        for rule_item in self.tracker._rules_by_name.values():
            if rule_item is not self and rule_item.exclusive_group == self.exclusive_group:
                yield rule_item

    @staticmethod
    def get_action_targets(actions):
        targets = {"rules": set(), "items": set()}
        for action_dict in actions or []:
            if "SetRule" in action_dict:
                targets["rules"].add(action_dict["SetRule"]["RuleName"])
            elif any(action in action_dict for action in ("SetLeftClick", "SetWheelClick", "SetRightClick", "ResetItem")):
                action_data = action_dict[list(action_dict.keys())[0]]
                targets["items"].add(action_data["Item"])
        return targets

    def deactivate_exclusive_group_rules(self):
        for rule_item in self.iter_exclusive_group_rules():
            if rule_item.is_active():
                rule_item.checked = True
                rule_item.update()

    def reset_exclusive_group_targets(self):
        reset_rules = set()
        reset_items = set()
        presets_to_reset = [self, *self.iter_exclusive_group_rules()]

        for ruleset in presets_to_reset:
            targets = self.get_action_targets(ruleset.actions)
            reset_rules.update(targets["rules"])
            reset_items.update(targets["items"])

        for rule_name in reset_rules:
            rule = self.tracker.find_rule(rule_name)
            if rule:
                rule.checked = rule.base_checked
                rule.update()
                rule.set_hidden_checks()

        for item_name in reset_items:
            item = self.tracker.find_item(item_name, True)
            if item:
                item.reset()
                item.update()
                self.tracker.mark_item_action_batch_dirty()

        self.deactivate_exclusive_group_rules()

    def set_hidden_checks(self):
        if self.hide_checks:
            for hidden_check in self.hide_checks:
                if hidden_check["Kind"] == "SimpleCheck":
                    hidden_names = {name.lower() for name in hidden_check["Checks"]}
                    for check_name, checks in self.tracker._simple_checks_by_name.items():
                        if check_name.lower() in hidden_names:
                            for check in checks:
                                if check.hide != self.checked:
                                    check.hide = self.checked
                                    self.tracker.mark_check_visibility_changed(check)
                elif hidden_check["Kind"] == "Block":
                    block_name = hidden_check["Name"].lower()
                    hidden_names = {name.lower() for name in hidden_check["Checks"]}
                    for check_name, blocks in self.tracker._block_checks_by_name.items():
                        if check_name.lower() == block_name:
                            for block in blocks:
                                for check_item in block.list_checks:
                                    if check_item.name.lower() in hidden_names:
                                        if check_item.hide != self.checked:
                                            check_item.hide = self.checked
                                            self.tracker.mark_check_visibility_changed(check_item)

    def do_actions(self):
        if self.actions:
            for action_dict in self.actions:
                if "SetRule" in action_dict:
                    rule_action = action_dict["SetRule"]
                    rule_name = rule_action["RuleName"]
                    rule_active = False
                    matching_rule = None

                    if not self.checked:
                        rule_active = rule_action.get("Active", False)

                    matching_rule = self.tracker.find_rule(rule_name)

                    if matching_rule:
                        matching_rule.checked = not rule_active
                        matching_rule.update()
                        matching_rule.do_actions()
                        matching_rule.set_hidden_checks()

                elif any(action in action_dict for action in ("SetLeftClick", "SetWheelClick", "SetRightClick", "ResetItem")):
                    action_name = list(action_dict.keys())[0]
                    rule_action = action_dict[action_name]
                    item = self.tracker.find_item(rule_action["Item"], True)

                    if item:
                        is_batched = self.tracker._item_action_batch_depth > 0
                        before_states = None if is_batched else self.tracker._snapshot_item_states()
                        if not self.checked:
                            item.reset()
                            if action_name != "ResetItem" :
                                for i in range(rule_action.get("Counter", 0)):
                                    if action_name == "SetLeftClick":
                                        item.left_click()
                                    elif action_name == "SetWheelClick":
                                        item.wheel_click()
                                    elif action_name == "SetRightClick":
                                        item.right_click()
                        else:
                            item.reset()
                        item.update()
                        if is_batched:
                            self.tracker.mark_item_action_batch_dirty()
                        else:
                            self.tracker.rebuild_item_indexes()
                            self.tracker.update_checks_for_changed_items(
                                self.tracker._get_changed_item_names(before_states)
                            )


    def left_click(self, force_click=False):
        if self.can_be_clickable or force_click:
            self.tracker.begin_item_action_batch()
            try:
                super().left_click()
                if self.is_active() and self.is_exclusive_preset():
                    self.reset_exclusive_group_targets()
                    self.deactivate_exclusive_group_rules()
                self.set_hidden_checks()
                self.do_actions()
            finally:
                self.tracker.end_item_action_batch()
            current_map = getattr(self.tracker, "current_map", None)
            if current_map:
                current_map.update()
