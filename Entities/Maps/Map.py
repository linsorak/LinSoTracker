import os
import pygame

from Engine.PopupWindow import PopupWindow
from Entities.Maps.BlockChecks import BlockChecks
from Entities.Maps.CheckListItem import CheckListItem
from Entities.Maps.MapPopup import MapPopup
from Entities.Maps.SimpleCheck import SimpleCheck, ConditionsType


class Map:
    def __init__(self, map_datas, index_positions, tracker, active=False):
        self.can_be_updated = False
        self.map_background = None
        self.map_image_filename = None
        self.map_datas = map_datas
        self.tracker = tracker
        self.index_positions = (index_positions["x"], index_positions["y"])
        self.active = active
        self.check_window = PopupWindow(tracker=self.tracker, index_positions=self.index_positions)
        self.checks_list = []
        self.block_checks = []
        self.simple_checks = []
        self.grouped_checks = {}
        self.current_block_checks = None
        self._process_data()
        self._process_checks()
        self._last_zoom = None

    def _process_data(self):
        datas = self.map_datas[0]["Datas"]
        self.map_image_filename = datas["Background"]
        self.checks_list_background_filename = datas["SubMenuBackground"]

    def get_name(self):
        return self.map_datas[0]["Datas"]["Name"]

    def _process_checks(self):
        checks_list_data = self.map_datas[0]["ChecksList"]
        for check in checks_list_data:
            kind = check.get("Kind")
            if kind in ("Block", "MapPopup"):
                if kind == "MapPopup":
                    block = MapPopup(
                        check["Id"], check["Name"], check["Positions"], self,
                        popup_items=check.get("Items", []),
                        popup_background=check.get("SubMenuBackground") or check.get("Background"),
                        zone=check.get("Zone"),
                        visible_condition=check.get("VisibleCondition", True)
                    )
                else:
                    block = BlockChecks(check["Id"], check["Name"], check["Positions"], self, zone=check.get("Zone"))
                if kind == "Block":
                    for check_item in check.get("Checks", []):
                        temp_check = CheckListItem(check_item["Id"], check_item["Name"], check["Positions"],
                                                   check_item["Conditions"], self.tracker,
                                                   group=check_item.get("Group", None))
                        block.add_check(temp_check)
                        self._register_grouped_check(temp_check)
                self.checks_list.append(block)
                self.block_checks.append(block)
            elif kind == "SimpleCheck":
                simple_check = SimpleCheck(check["Id"], check["Name"], check["Positions"], self,
                                           check["Conditions"], zone=check.get("Zone"), group=check.get("Group", None))
                self.checks_list.append(simple_check)
                self.simple_checks.append(simple_check)
                self._register_grouped_check(simple_check)

    def _register_grouped_check(self, check):
        if check.group:
            self.grouped_checks.setdefault(check.group, []).append(check)

    def update(self):
        if not self.can_be_updated:
            return
        resources_path = self.tracker.resources_path
        core_service = self.tracker.core_service
        zoom = core_service.zoom
        datas = self.map_datas[0]["Datas"]

        if self._last_zoom != zoom:
            self.map_background = self.tracker.bank.addZoomImage(os.path.join(resources_path, self.map_image_filename))
            self.checks_list_background = self.tracker.bank.addZoomImage(
                os.path.join(resources_path, self.checks_list_background_filename))
            self._last_zoom = zoom

        for check in self.checks_list:
            check.update()
        if self.current_block_checks:
            box_rect_data = datas["DrawBoxRectSubTitle"] if self.current_block_checks.zone else datas["DrawBoxRect"]
            bg_rect = self.checks_list_background.get_rect()
            box_checks = pygame.Rect(
                box_rect_data["x"] * zoom + bg_rect.x + self.index_positions[0] * zoom,
                box_rect_data["y"] * zoom + bg_rect.y + self.index_positions[1] * zoom,
                box_rect_data["w"] * zoom,
                box_rect_data["h"] * zoom
            )

            popup_background = getattr(self.current_block_checks, "popup_background", None)
            self.check_window.set_background_image_path(popup_background or self.checks_list_background_filename)
            self.check_window.set_arrow_left_image_path(datas["LeftArrow"]["Image"])
            self.check_window.set_arrow_right_image_path(datas["RightArrow"]["Image"])
            self.check_window.set_title(self.current_block_checks.name)
            self.check_window.set_subtitle(self.current_block_checks.zone)
            self.check_window.set_title_font(core_service.get_font("mapFontTitle"))
            self.check_window.set_subtitle_font(core_service.get_font("mapFontSubTitle"))
            self.check_window.set_title_label_position_y(datas["LabelY"])
            self.check_window.set_list_items(self.current_block_checks)
            self.check_window.set_overlay_items(getattr(self.current_block_checks, "popup_items", []))
            self.check_window.set_box_rect(box_checks)
            left_arrow = (datas["LeftArrow"]["Positions"]["x"], datas["LeftArrow"]["Positions"]["y"])
            right_arrow = (datas["RightArrow"]["Positions"]["x"], datas["RightArrow"]["Positions"]["y"])
            self.check_window.set_arrows_positions(left_arrow, right_arrow)
            self.check_window.update()

        self.tracker.update_cpt()

    def open_window(self):
        self.check_window.open = True

    def draw_background(self, screen):
        if self.active:
            zoom = self.tracker.core_service.zoom
            screen.blit(self.map_background, (self.index_positions[0] * zoom, self.index_positions[1] * zoom))

    def draw(self, screen):
        if not self.active:
            return

        for check in self.simple_checks:
            check.draw_dragged_image(screen)

        for check in self.checks_list:
            check.draw(screen)

        if self.check_window and self.check_window.is_open():
            self.check_window.draw(screen)

    def get_positions_from_index_positions(self, index_positions_index, position):
        zoom = self.tracker.core_service.zoom
        return self.index_positions[index_positions_index] * zoom + position * zoom

    def click(self, mouse_position, button):
        self.click_map(mouse_position, button)

    def find_check_at_position(self, mouse_position, include_simple=True, include_blocks=True):
        if include_blocks:
            for check in self.block_checks:
                if self.tracker.core_service.is_on_element(
                        mouse_positions=mouse_position,
                        element_positons=check.get_position(),
                        element_dimension=check.get_rect().size
                ) and not check.all_check_hidden():
                    return check
        if include_simple and not self.check_window.is_open():
            for check in self.simple_checks:
                if self.tracker.core_service.is_on_element(
                        mouse_positions=mouse_position,
                        element_positons=check.get_position(),
                        element_dimension=check.get_rect().size
                ) and not check.hide:
                    return check
        return None

    def click_map(self, mouse_position, button):
        if self.check_window.is_open():
            self.check_window.left_click(mouse_position, button)
        else:
            self.current_block_checks = None

        check = self.find_check_at_position(mouse_position, include_simple=False)
        if check:
            if button == 1:
                check.left_click(mouse_position)
                if not self.check_window.is_open():
                    self.check_window.update()
                    self.check_window.open_window()
                return
            elif button == 2:
                check.wheel_click(mouse_position)
                return
            elif button == 3:
                check.right_click(mouse_position)
                return

        check = self.find_check_at_position(mouse_position, include_blocks=False)
        if check:
            if button == 1:
                check.left_click(mouse_position)
                self.update_after_check_click(check)
                return
            elif button == 3:
                check.right_click(mouse_position)
                self.update_after_check_click(check)
                return
            elif button == 2:
                check.wheel_click(mouse_position)
                return

        if self.check_window.is_open():
            self.check_window.update()

    def update_after_check_click(self, check):
        if check.group:
            for group_check in self.grouped_checks.get(check.group, []):
                group_check.update()
        else:
            check.update()
        self.tracker.update_cpt()


    def get_count_checks(self):
        cpt_logic = 0
        cpt_left = 0

        for check in self.block_checks:
            for sub_check in check.list_checks:
                if not sub_check.hide and not sub_check.checked:
                    cpt_left += 1
                    if sub_check.state == ConditionsType.LOGIC:
                        cpt_logic += 1
        for check in self.simple_checks:
            if not check.hide and not check.checked:
                cpt_left += 1
                if check.state == ConditionsType.LOGIC:
                    cpt_logic += 1

        return cpt_logic, cpt_left

    def get_all_group_checks(self, call_check, group_name):
        return [
            check
            for check in self.grouped_checks.get(group_name, [])
            if check is not call_check and not check.hide
        ]


    def get_data(self):
        checks_datas = [check.get_data() for check in self.checks_list]
        return {
            "name": self.get_name(),
            "checks_datas": checks_datas
        }

    def load_data(self, datas):
        for data in datas.get("checks_datas", []):
            for check in self.checks_list:
                if check.id == data["id"] and check.name == data["name"]:
                    check.set_data(data)
                    break

