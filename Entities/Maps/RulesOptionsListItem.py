import os

import pygame

from Engine import MainMenu
from Entities.Maps.BlockChecks import BlockChecks
from Entities.Maps.CheckListItem import CheckListItem
from Entities.Maps.SimpleCheck import SimpleCheck


class RulesOptionsListItem(CheckListItem):
    def __init__(self, ident, name, position, tracker, checked, hide_checks, actions, active_on_start=False, can_be_clickable=True):
        super().__init__(ident, name, position, None, tracker)
        self.checked = checked
        self.hide_checks = hide_checks
        self.actions = actions
        self.active_on_start = active_on_start
        self.can_be_clickable = can_be_clickable
        self.update()
        self.set_hidden_checks()

    def update(self):
        self.color = None
        font = self.tracker.core_service.get_font("mapFont")
        font_path = os.path.join(self.tracker.core_service.get_tracker_temp_path(), font["Name"])

        if self.checked:
            self.color = self.tracker.core_service.get_color_from_font(font, "Done")
        else:
            self.color = self.tracker.core_service.get_color_from_font(font, "Normal")

        temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32)
        temp_surface = temp_surface.convert_alpha()
        self.surface, self.position_draw = MainMenu.MainMenu.draw_text(
            text=self.name,
            font_name=font_path,
            color=self.color,
            font_size=font["Size"] * self.tracker.core_service.zoom,
            surface=temp_surface,
            position=(self.position["x"], self.position["y"]),
            outline=1 * self.tracker.core_service.zoom)
        # print(f"Rules : {self.name} - {self.checked}")

    def is_active(self):
        return not self.checked

    def set_hidden_checks(self):
        if self.hide_checks:
            for hidden_check in self.hide_checks:
                for map in self.tracker.maps_list:
                    for check in map.checks_list:
                        if type(check) == SimpleCheck and hidden_check["Kind"] == "SimpleCheck":
                            for hidden_check_name in hidden_check["Checks"]:
                                if hidden_check_name == check.name:
                                    if self.checked:
                                        check.hide = True
                                    else:
                                        check.hide = False
                                    break
                        elif type(check) == BlockChecks and hidden_check["Kind"] == "Block":
                            if hidden_check["Name"] == check.name:
                                for check_item in check.list_checks:
                                    for block_hidden_check in hidden_check["Checks"]:
                                        if check_item.name == block_hidden_check:
                                            if self.checked:
                                                check_item.hide = True
                                            else:
                                                check_item.hide = False
                                            break

    def do_actions(self):
        if self.actions:
            for action_dict in self.actions:
                if "SetRule" in action_dict:
                    rule_action = action_dict["SetRule"]
                    rule_name = rule_action["RuleName"]

                    rule_active = rule_action.get("Active", False) if not self.checked else False

                    matching_rules = filter(lambda rule_item: rule_item.name == rule_name,
                                            self.tracker.rules_options_items_list)
                    matching_rule = next(matching_rules, None)
                    if matching_rule:
                        matching_rule.checked = not rule_active
                        matching_rule.update()
                        matching_rule.do_actions()
                        matching_rule.set_hidden_checks()

                elif "SetLeftClick" or "SetWheelClick" or "SetRightClick" in action_dict:
                    action_name = list(action_dict.keys())[0]
                    rule_action = action_dict[action_name]
                    item = self.tracker.find_item(rule_action["Item"], True)

                    if item:
                        if not self.checked:
                            for i in range(rule_action.get("Counter", 0)):
                                if action_name == "SetLeftClick":
                                    item.left_click()
                                elif action_name == "SetWheelClick":
                                    item.wheel_click()
                                elif action_name == "SetRightClick":
                                    item.right_click()
                        else:
                            item.reset()

    def left_click(self, force_click=False):
        if self.can_be_clickable or force_click:
            super().left_click()
            self.set_hidden_checks()
            self.do_actions()
