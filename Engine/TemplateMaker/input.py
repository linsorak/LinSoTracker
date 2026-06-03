import copy
import json
import os
import re
import shutil
from tkinter import filedialog, messagebox, simpledialog
from zipfile import ZipFile

import pygame

from Tools import ptext


class InputMixin:
    def click(self, mouse_position, button):
        if self.prompt_open:
            if button == 1:
                self._handle_text_prompt_click(mouse_position)
            return True
        if self.mode == "start":
            if button == 1:
                for index, rect in self.project_delete_buttons.items():
                    if rect.collidepoint(mouse_position):
                        self._delete_project(index)
                        return True
                for index, rect in self.project_cards.items():
                    if rect.collidepoint(mouse_position):
                        self._load_template_folder(self.projects[index]["dir"])
                        return True
                for key, rect in self.start_buttons.items():
                    if rect.collidepoint(mouse_position):
                        if key == "new":
                            self._start_new_project()
                        elif key == "open":
                            self._open_template_file()
                        elif key == "back":
                            self._action_back()
                        return True
            return True

        # Position pick mode: click on canvas sets the (draft) item position
        if self.item_modal_open and self.position_pick_mode:
            if button == 1 and self.last_bg_rect.collidepoint(mouse_position):
                item = self._selected_item()
                if item:
                    scale = self.template_size[0] / self.last_bg_rect.w
                    item["x"] = int((mouse_position[0] - self.last_bg_rect.x) * scale)
                    item["y"] = int((mouse_position[1] - self.last_bg_rect.y) * scale)
                    self.message = f"Position set to {item['x']}, {item['y']}."
                self.position_pick_mode = False
            return True

        # Right / middle click on the live preview (item modal) -> component interaction
        if self.item_modal_open and not self.sprite_picker_open and not self.kind_picker_open \
                and button in (2, 3):
            prev = self.modal_buttons.get("preview")
            if prev and prev.collidepoint(mouse_position):
                self._preview_action(self._selected_item(), "wheel_click" if button == 2 else "right")
                return True

        if button == 1:
            if self.sprite_picker_open:
                self._handle_picker_click(mouse_position)
                return True
            if self.fonts_modal_open:
                self._handle_fonts_click(mouse_position)
                return True
            if self.item_modal_open:
                self._handle_modal_click(mouse_position)
                return True

            for key, rect in self.buttons.items():
                if rect.collidepoint(mouse_position):
                    getattr(self, f"_action_{key}")()
                    return True

            for key, rect in self.property_buttons.items():
                if rect.collidepoint(mouse_position):
                    self._handle_property_button(key)
                    return True

            for key, rect in self.sheet_buttons.items():
                if rect.collidepoint(mouse_position):
                    if key == "add":
                        self._action_sheet()
                    elif key == "remove":
                        self._remove_active_sheet()
                    return True

            # Dropdown: select a sheet (only when open) then close
            if self.sheet_dropdown_open:
                for index, rect in self.sheet_list_rows.items():
                    if rect.collidepoint(mouse_position):
                        self.active_sheet_index = index
                        self.sheet_scroll = 0
                        self.sheet_dropdown_open = False
                        self.message = f"Active sheet: {self.active_sheet['name']}."
                        return True
                self.sheet_dropdown_open = False

            # Dropdown header: toggle open/close
            if self.sheet_dropdown_rect.collidepoint(mouse_position):
                self.sheet_dropdown_open = not self.sheet_dropdown_open and bool(self.sheets)
                return True

            for key, rect in self.info_buttons.items():
                if rect.collidepoint(mouse_position):
                    if key == "name":
                        self._rename_project()
                    elif key == "fonts":
                        self.fonts_modal_open = True
                    elif key.startswith("info_"):
                        self._edit_info_field(key[len("info_"):])
                    elif key == "set_icon":
                        if self.selected_cell:
                            sn, r, c = self.selected_cell
                            tile = self._get_icon_surface(r, c, sn)
                            if tile:
                                self.project_icon = tile
                                self.message = "Icon set from selected tile."
                        else:
                            self.message = "Select a tile first."
                    return True

            if self.active_sheet and self.sheet_rect.collidepoint(mouse_position):
                self._select_sprite(mouse_position)
                return True

            item_index = self._get_item_index_at(mouse_position)
            if item_index is not None:
                now = pygame.time.get_ticks()
                double = self.last_click_item == item_index and now - self.last_click_time < 350
                self.last_click_time = now
                self.last_click_item = item_index
                self.selected_item_index = item_index
                item = self.placed_items[item_index]
                if double:
                    self._open_item_modal(item_index)
                    self.message = f"Editing {item['name']}."
                else:
                    self.message = f"Selected {item['name']}. Double-click to edit."
                return True

            if self.selected_cell and self.last_bg_rect.collidepoint(mouse_position):
                self._place_item(mouse_position)
                return True

        return True

    def click_down(self, mouse_position, button):
        if button != 1:
            return
        # No canvas dragging while any overlay is open
        if (self.prompt_open or self.item_modal_open or self.fonts_modal_open
                or self.sprite_picker_open):
            return
        if self.dragging_item_index is None:
            item_index = self._get_item_index_at(mouse_position)
            if item_index is None:
                return
            self.selected_item_index = item_index
            self.dragging_item_index = item_index
            item = self.placed_items[item_index]
            rect = item.get("screen_rect", pygame.Rect(mouse_position[0], mouse_position[1], 1, 1))
            self.drag_offset = (mouse_position[0] - rect.x, mouse_position[1] - rect.y)
            self.message = f"Moving {item['name']}."
        self._move_item_to_mouse(self.dragging_item_index, mouse_position)

    def mouse_up(self):
        self.dragging_item_index = None

    def mouse_move(self, mouse_position):
        if self.mode == "start":
            self.hover_start_key = None
            for key, rect in self.start_buttons.items():
                if rect.collidepoint(mouse_position):
                    self.hover_start_key = key
                    break
            if self.hover_start_key is None:
                for index, rect in self.project_delete_buttons.items():
                    if rect.collidepoint(mouse_position):
                        self.hover_start_key = f"del_{index}"
                        break
            if self.hover_start_key is None:
                for index, rect in self.project_cards.items():
                    if rect.collidepoint(mouse_position):
                        self.hover_start_key = f"project_{index}"
                        break
            self._set_cursor_safe(
                pygame.SYSTEM_CURSOR_HAND if self.hover_start_key else pygame.SYSTEM_CURSOR_ARROW
            )
            return

        self.hover_key = None
        self.hover_property_key = None
        self.hover_modal_key = None

        # When an overlay is open, only hover its own buttons; never touch canvas items
        if self.prompt_open:
            over_btn = ((self.prompt_ok_rect and self.prompt_ok_rect.collidepoint(mouse_position))
                        or (self.prompt_cancel_rect and self.prompt_cancel_rect.collidepoint(mouse_position)))
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND if over_btn else pygame.SYSTEM_CURSOR_ARROW)
            return
        if self.sprite_picker_open or self.fonts_modal_open or self.item_modal_open:
            if self.sprite_picker_open:
                btns = self.picker_buttons
            elif self.fonts_modal_open:
                btns = self.fonts_buttons
            else:
                btns = self.modal_buttons
            for key, rect in btns.items():
                if rect.collidepoint(mouse_position):
                    self.hover_modal_key = key
                    break
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND if self.hover_modal_key else pygame.SYSTEM_CURSOR_ARROW)
            return

        for key, rect in self.buttons.items():
            if rect.collidepoint(mouse_position):
                self.hover_key = key
                break
        for key, rect in self.property_buttons.items():
            if rect.collidepoint(mouse_position):
                self.hover_property_key = key
                break
        if self.hover_key is None:
            if self.sheet_buttons.get("add") and self.sheet_buttons["add"].collidepoint(mouse_position):
                self.hover_key = "sheet_add"
            elif self.sheet_buttons.get("remove") and self.sheet_buttons["remove"].collidepoint(mouse_position):
                self.hover_key = "sheet_remove"
            elif self.info_buttons.get("set_icon") and self.info_buttons["set_icon"].collidepoint(mouse_position):
                self.hover_key = "set_icon"
            elif self.info_buttons.get("fonts") and self.info_buttons["fonts"].collidepoint(mouse_position):
                self.hover_key = "fonts"
            else:
                for index, rect in self.sheet_list_rows.items():
                    if rect.collidepoint(mouse_position):
                        self.hover_key = f"sheetrow_{index}"
                        break
        if self.dragging_item_index is not None:
            self._move_item_to_mouse(self.dragging_item_index, mouse_position)
        if (self.canvas_rect.collidepoint(mouse_position) or self.left_panel_rect.collidepoint(mouse_position)
                or self.right_panel_rect.collidepoint(mouse_position)):
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND)
        else:
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_ARROW)

    def keyup(self, key, screen):
        if key == pygame.K_ESCAPE and self.fonts_modal_open:
            self.fonts_modal_open = False
        elif key == pygame.K_ESCAPE and self.position_pick_mode:
            self.position_pick_mode = False
        elif key == pygame.K_ESCAPE and self.sprite_picker_open:
            self.sprite_picker_open = False
        elif key == pygame.K_ESCAPE and self.child_edit_index is not None:
            self.child_edit_index = None
        elif key == pygame.K_ESCAPE and self.kind_picker_open:
            self.kind_picker_open = False
        elif key == pygame.K_ESCAPE and self.item_modal_open:
            self._close_item_modal(save=False)
        elif key == pygame.K_ESCAPE:
            self._action_back()
        elif key == pygame.K_DELETE and not self.item_modal_open:
            self._delete_selected_item()

    def events(self, event, time_delta):
        if self.prompt_open:
            if event.type == pygame.KEYDOWN:
                self._handle_text_prompt_event(event)
                return True
            # let mouse events reach click() for the OK/Cancel buttons
            return False
        if event.type == pygame.MOUSEWHEEL:
            pos = pygame.mouse.get_pos()
            if self.sprite_picker_open and self.picker_tileset_rect.collidepoint(pos):
                self.picker_scroll -= event.y * 40
                return True
            if self.item_modal_open:
                prev = self.modal_buttons.get("preview")
                if prev and prev.collidepoint(pos):
                    self._preview_action(self._selected_item(), "wheel_up" if event.y > 0 else "wheel_down")
                    return True
            if self.mode == "editor" and self.active_sheet and self.sheet_rect.collidepoint(pos):
                self.sheet_scroll -= event.y * 40
                return True
        return False

