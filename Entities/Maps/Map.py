import concurrent.futures
import os
import pygame

from Engine.PopupWindow import PopupWindow
from Entities.Maps.BlockChecks import BlockChecks
from Entities.Maps.CheckListItem import CheckListItem
from Entities.Maps.SimpleCheck import SimpleCheck, ConditionsType

import threading


class Map:
    def __init__(self, map_datas, index_positions, tracker, active=False):
        self.can_be_updated = False
        self.map_background = None
        self.map_image_filename = None
        self.map_datas = map_datas
        self.tracker = tracker
        self.index_positions = (index_positions["x"], index_positions["y"])
        self.active = active
        self.checks_list_open = False
        self.checks_list = []
        self.current_block_checks = None
        self.check_window = PopupWindow(tracker=self.tracker, index_positions=self.index_positions)
        self.processing()
        self.processing_checks()

    def processing(self):
        self.map_image_filename = self.map_datas[0]["Datas"]["Background"]
        self.checks_list_background_filename = self.map_datas[0]["Datas"]["SubMenuBackground"]

    def get_name(self):
        return self.map_datas[0]["Datas"]["Name"]

    def processing_checks(self):
        for check in self.map_datas[0]["ChecksList"]:
            if check["Kind"] == "Block":
                block = BlockChecks(check["Id"], check["Name"], check["Positions"], self, zone=check.get("Zone", None))

                for check_item in check["Checks"]:
                    temp_check = CheckListItem(check_item["Id"], check_item["Name"], check["Positions"],
                                               check_item["Conditions"], self.tracker)
                    block.add_check(temp_check)

                self.checks_list.append(block)

            if check["Kind"] == "SimpleCheck":
                simple_check = SimpleCheck(check["Id"], check["Name"],
                                           check["Positions"], self, check["Conditions"], zone=check.get("Zone", None))
                self.checks_list.append(simple_check)

    def update(self):
        if self.can_be_updated:
            self.map_background = self.tracker.bank.addZoomImage(
                os.path.join(self.tracker.resources_path, self.map_image_filename))

            self.checks_list_background = self.tracker.bank.addZoomImage(
                os.path.join(self.tracker.resources_path, self.checks_list_background_filename))

            if self.current_block_checks:
                box_rect = self.map_datas[0]["Datas"]["DrawBoxRect"] if not self.current_block_checks.zone else self.map_datas[0]["Datas"]["DrawBoxRectSubTitle"]
                box_checks = pygame.Rect(
                    (box_rect["x"] * self.tracker.core_service.zoom) + self.checks_list_background.get_rect().x + (
                            self.index_positions[0] * self.tracker.core_service.zoom),
                    (box_rect["y"] * self.tracker.core_service.zoom) + self.checks_list_background.get_rect().y + (
                            self.index_positions[1] * self.tracker.core_service.zoom),
                    box_rect["w"] * self.tracker.core_service.zoom,
                    box_rect["h"] * self.tracker.core_service.zoom)

                self.check_window.set_background_image_path(self.checks_list_background_filename)
                self.check_window.set_arrow_left_image_path(self.map_datas[0]["Datas"]["LeftArrow"]["Image"])
                self.check_window.set_arrow_right_image_path(self.map_datas[0]["Datas"]["RightArrow"]["Image"])
                self.check_window.set_title(self.current_block_checks.name)
                self.check_window.set_subtitle(self.current_block_checks.zone)
                self.check_window.set_title_font(self.tracker.core_service.get_font("mapFontTitle"))
                self.check_window.set_subtitle_font(self.tracker.core_service.get_font("mapFontSubTitle"))
                self.check_window.set_title_label_position_y(self.map_datas[0]["Datas"]["LabelY"])

                # test_list = []
                #
                # for check in self.current_block_checks:
                #     if not check.hide:
                #         test_list.append(check)
                #
                # self.check_window.set_list_items(test_list)
                self.check_window.set_list_items(self.current_block_checks)
                self.check_window.set_box_rect(box_checks)
                left_arrow = (self.map_datas[0]["Datas"]["LeftArrow"]["Positions"]["x"],
                              self.map_datas[0]["Datas"]["LeftArrow"]["Positions"]["y"])
                right_arrow = (self.map_datas[0]["Datas"]["RightArrow"]["Positions"]["x"],
                               self.map_datas[0]["Datas"]["RightArrow"]["Positions"]["y"])
                self.check_window.set_arrows_positions(left_arrow, right_arrow)
                self.check_window.update()
            else:
                # pool = Pool(processes=len(self.checks_list))
                # pool.map(self.update_check, self.checks_list)
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    executor.map(self.update_check, self.checks_list)

            self.tracker.update_cpt()

    def update_check(self, check):
        check.update()

    def open_window(self):
        self.check_window.open = True

    def draw_background(self, screen):
        if self.active:
            screen.blit(self.map_background, (self.index_positions[0] * self.tracker.core_service.zoom,
                                              self.index_positions[1] * self.tracker.core_service.zoom))

    def draw(self, screen):
        if self.active:
            for check in self.checks_list:
                check.draw(screen)

            if self.check_window and self.check_window.is_open():
                self.check_window.draw(screen)

    def get_positions_from_index_positions(self, index_positions_index, position):
        return (self.index_positions[index_positions_index] * self.tracker.core_service.zoom) + (
                position * self.tracker.core_service.zoom)

    def click(self, mouse_position, button):
        click_map = threading.Thread(target=self.click_map, args=(mouse_position, button))
        click_map.start()
        click_map.join()

    def click_map(self, mouse_position, button):
        if self.check_window.is_open():
            self.check_window.left_click(mouse_position, button)
            self.current_block_checks.update()
        else:
            self.current_block_checks = None

        for check in self.checks_list:
            if isinstance(check, BlockChecks):
                if not self.current_block_checks:
                    pos = check.get_position()
                    dim = check.get_rect().size
                    if self.tracker.core_service.is_on_element(mouse_positions=mouse_position, element_positons=pos,
                                                               element_dimension=dim) and not check.all_check_hidden():
                        if button == 1:
                            check.left_click(mouse_position)
                            if not self.check_window.is_open():
                                self.check_window.update()
                                self.check_window.open = True
                            break

                        elif button == 2:
                            check.wheel_click(mouse_position)
                            break

                        elif button == 3:
                            check.right_click(mouse_position)
                            break

            elif isinstance(check, SimpleCheck):
                pos = check.get_position()
                dim = check.get_rect().size
                if self.tracker.core_service.is_on_element(mouse_positions=mouse_position, element_positons=pos,
                                                           element_dimension=dim) and not check.hide:
                    if button == 1 or button == 3:
                        check.left_click(mouse_position)
                        self.update()
                        break

                    elif button == 2:
                        check.wheel_click(mouse_position)
                        break

        if self.check_window.is_open():
            self.check_window.update()

    def get_count_checks(self):
        cpt_logic = 0
        cpt_left = 0

        for check in self.checks_list:
            if not check.hide and not check.checked:

                if isinstance(check, BlockChecks):
                    for check_in_block in check.list_checks:
                        if not check_in_block.hide and not check_in_block.checked:
                            cpt_left += 1

                            if check_in_block.state == ConditionsType.LOGIC:
                                cpt_logic += 1

                elif isinstance(check, SimpleCheck):
                    cpt_left += 1

                    if check.state == ConditionsType.LOGIC:
                        cpt_logic += 1

        return cpt_logic, cpt_left

    def get_name(self):
        return self.map_datas[0]["Datas"]["Name"]

    def get_data(self):
        checks_datas = []
        for check in self.checks_list:
            checks_datas.append(check.get_data())

        data = {
            "name": self.get_name(),
            "checks_datas": checks_datas
        }
        return data

    def load_data(self, datas):
        i = 0
        checks_datas = datas["checks_datas"]
        for data in checks_datas:
            for check in self.checks_list:
                if (check.id == data["id"]) and (check.name == data["name"]):
                    i = i + 1
                    check.set_data(data)
                    break
