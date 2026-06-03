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
        if self.suppress_next_click:
            self.suppress_next_click = False
            return True
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
                    scale = self._canvas_size()[0] / self.last_bg_rect.w
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

        # Canvas context menu (right-click duplicate / delete)
        no_overlay = not (self.item_modal_open or self.prompt_open or self.sprite_picker_open
                          or self.fonts_modal_open)
        if self.context_menu_open:
            if button == 1:
                for key, r in self.context_menu_buttons.items():
                    if r.collidepoint(mouse_position):
                        if key == "ctx_duplicate":
                            self._duplicate_item(self.context_menu_index)
                            self.context_menu_open = False
                        elif key == "ctx_delete":
                            self._delete_item_at(self.context_menu_index)
                            self.context_menu_open = False
                        elif key == "ctx_add":
                            self.context_add_open = not self.context_add_open
                        elif key.startswith("ctxkind_"):
                            self._add_item_kind_at(key[len("ctxkind_"):], self.context_menu_pos)
                            self.context_menu_open = False
                            self.context_add_open = False
                        return True
            self.context_menu_open = False
            self.context_add_open = False
            return True
        if button == 3 and no_overlay and self.last_bg_rect.collidepoint(mouse_position):
            idx = self._get_item_index_at(mouse_position)
            if idx is not None:
                self.selected_item_index = idx
            self.context_menu_index = idx
            self.context_menu_pos = mouse_position
            self.context_menu_open = True
            self.context_add_open = False
            return True

        if button == 1:
            if self.field_editor_open:
                self._handle_field_editor_click(mouse_position)
                return True
            if self.color_picker_open:
                self._handle_color_picker_click(mouse_position)
                return True
            if self.sprite_picker_open:
                self._handle_picker_click(mouse_position)
                return True
            if self.fonts_modal_open:
                self._handle_fonts_click(mouse_position)
                return True
            if self.item_modal_open:
                if self.item_refs_editor_open:
                    self._handle_modal_click(mouse_position)
                    return True
                if self.property_scroll_track_rect.collidepoint(mouse_position):
                    offset = self.property_scroll_thumb_rect.h // 2
                    if self.property_scroll_thumb_rect.collidepoint(mouse_position):
                        offset = mouse_position[1] - self.property_scroll_thumb_rect.y
                    self._set_property_scroll_from_mouse(mouse_position[1], offset)
                    return True
                if self.child_scroll_track_rect.collidepoint(mouse_position):
                    offset = self.child_scroll_thumb_rect.h // 2
                    if self.child_scroll_thumb_rect.collidepoint(mouse_position):
                        offset = mouse_position[1] - self.child_scroll_thumb_rect.y
                    self._set_child_scroll_from_mouse(mouse_position[1], offset)
                    return True
                self._handle_modal_click(mouse_position)
                return True

            if self.see_links_rect.collidepoint(mouse_position):
                self.show_links = not self.show_links
                return True

            for key, rect in self.buttons.items():
                if rect.collidepoint(mouse_position):
                    getattr(self, f"_action_{key}")()
                    return True

            # Left panel tabs
            for key, rect in self.left_tabs.items():
                if rect.collidepoint(mouse_position):
                    self.left_tab = key
                    return True

            # Items List tab rows (click select, double-click edit) - top-level + linked
            for index, rect in self.items_list_rows.items():
                if rect.collidepoint(mouse_position):
                    entry = self.items_list_entries[index]
                    path = entry["path"]
                    now = pygame.time.get_ticks()
                    double = self.last_click_item == index and now - self.last_click_time < 350
                    self.last_click_time = now
                    self.last_click_item = index
                    if entry["depth"] == 0:
                        self.selected_item_index = path[0]
                        self.selected_linked_path = None
                        if double:
                            self._open_item_modal(path[0])
                    else:
                        self.selected_item_index = None
                        self.selected_linked_path = path
                        if double:
                            self._open_item_modal(path[0], path)
                    return True

            for key, rect in self.property_buttons.items():
                if rect.collidepoint(mouse_position):
                    self._handle_property_button(key)
                    return True

            for key, rect in self.sheet_buttons.items():
                if rect.collidepoint(mouse_position):
                    if key == "add":
                        self._action_sheet()
                    elif key == "new":
                        self._new_blank_sheet()
                    elif key == "remove":
                        self._remove_active_sheet()
                    elif key == "set_tile":
                        self._import_tile_image()
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
                    elif key == "illustration":
                        self._import_illustration()
                    elif key == "import_icon":
                        self._import_icon()
                    elif key == "background_color":
                        self._edit_template_background_color()
                    elif key == "dimensions":
                        self._edit_template_dimensions()
                    elif key == "background_position":
                        self._edit_background_position()
                    elif key == "submenu_back":
                        self._exit_submenu_canvas()
                    elif key == "submenu_background":
                        self._import_submenu_background()
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

            linked_path = self._find_linked_item_path_at(mouse_position)
            if linked_path is not None:
                now = pygame.time.get_ticks()
                double = self.last_click_item == linked_path and now - self.last_click_time < 350
                self.last_click_time = now
                self.last_click_item = linked_path
                self.selected_item_index = linked_path[0] if linked_path else None
                self.selected_linked_path = linked_path
                item = self._get_linked_item_by_path(linked_path)
                if not item:
                    return True
                if double:
                    self._open_item_modal(linked_path[0], linked_path)
                    self.message = f"Editing linked {item['name']}."
                else:
                    self.message = f"Selected linked {item['name']}. Double-click to edit."
                return True

            item_index = self._get_item_index_at(mouse_position)
            if item_index is not None:
                now = pygame.time.get_ticks()
                double = self.last_click_item == item_index and now - self.last_click_time < 350
                self.last_click_time = now
                self.last_click_item = item_index
                self.selected_item_index = item_index
                self.selected_linked_path = None
                item = self.placed_items[item_index]
                if double:
                    self._open_item_modal(item_index)
                    self.message = f"Editing {item['name']}."
                else:
                    self.message = f"Selected {item['name']}. Double-click to edit."
                return True

            if (self.selected_cell or self.placement_kind) and self.last_bg_rect.collidepoint(mouse_position):
                self.selected_linked_path = None
                self._place_item(mouse_position)
                return True

        return True

    def click_down(self, mouse_position, button):
        if button != 1:
            return
        if self.item_modal_open and not (
                self.prompt_open or self.sprite_picker_open or self.fonts_modal_open
                or self.field_editor_open or self.color_picker_open or self.kind_picker_open
                or self.item_refs_editor_open or self.child_edit_index is not None):
            if self.property_scroll_thumb_rect.collidepoint(mouse_position):
                self.dragging_property_scroll = True
                self.property_scroll_drag_offset = mouse_position[1] - self.property_scroll_thumb_rect.y
                return
            if self.property_scroll_track_rect.collidepoint(mouse_position):
                self.dragging_property_scroll = True
                self.property_scroll_drag_offset = self.property_scroll_thumb_rect.h // 2
                self._set_property_scroll_from_mouse(mouse_position[1], self.property_scroll_drag_offset)
                return
            if self.child_scroll_thumb_rect.collidepoint(mouse_position):
                self.dragging_child_scroll = True
                self.child_scroll_drag_offset = mouse_position[1] - self.child_scroll_thumb_rect.y
                return
            if self.child_scroll_track_rect.collidepoint(mouse_position):
                self.dragging_child_scroll = True
                self.child_scroll_drag_offset = self.child_scroll_thumb_rect.h // 2
                self._set_child_scroll_from_mouse(mouse_position[1], self.child_scroll_drag_offset)
                return
        # No canvas dragging while any overlay is open
        if (self.prompt_open or self.item_modal_open or self.fonts_modal_open
                or self.sprite_picker_open):
            return
        linked_path = self._find_linked_item_path_at(mouse_position)
        if linked_path is not None:
            item = self._get_linked_item_by_path(linked_path)
            if item is None:
                return
            self.selected_item_index = linked_path[0]
            self.selected_linked_path = linked_path
            self.dragging_linked_path = linked_path
            self.suppress_next_click = True
            rect = item.get("screen_rect", pygame.Rect(mouse_position[0], mouse_position[1], 1, 1))
            self.drag_offset = (mouse_position[0] - rect.x, mouse_position[1] - rect.y)
            self.message = f"Moving linked {item['name']}."
            self._move_linked_item_to_mouse(linked_path, mouse_position)
            return
        if self.dragging_item_index is None:
            item_index = self._get_item_index_at(mouse_position)
            if item_index is None:
                return
            self.selected_item_index = item_index
            self.selected_linked_path = None
            self.dragging_item_index = item_index
            self.suppress_next_click = True
            item = self.placed_items[item_index]
            rect = item.get("screen_rect", pygame.Rect(mouse_position[0], mouse_position[1], 1, 1))
            self.drag_offset = (mouse_position[0] - rect.x, mouse_position[1] - rect.y)
            self.message = f"Moving {item['name']}."
        self._move_item_to_mouse(self.dragging_item_index, mouse_position)

    def mouse_up(self):
        self.dragging_item_index = None
        self.dragging_linked_path = None
        self.dragging_child_scroll = False
        self.dragging_property_scroll = False

    def mouse_move(self, mouse_position):
        if self.dragging_linked_path is not None:
            self._move_linked_item_to_mouse(self.dragging_linked_path, mouse_position)
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND)
            return
        if self.dragging_property_scroll:
            self._set_property_scroll_from_mouse(mouse_position[1], self.property_scroll_drag_offset)
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND)
            return
        if self.dragging_child_scroll:
            self._set_child_scroll_from_mouse(mouse_position[1], self.child_scroll_drag_offset)
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND)
            return
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
        if self.sprite_picker_open or self.fonts_modal_open or self.item_modal_open or self.field_editor_open:
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
            if self.item_modal_open and (self.property_scroll_thumb_rect.collidepoint(mouse_position)
                                         or self.property_scroll_track_rect.collidepoint(mouse_position)):
                self.hover_modal_key = "property_scroll"
            if self.item_modal_open and (self.child_scroll_thumb_rect.collidepoint(mouse_position)
                                         or self.child_scroll_track_rect.collidepoint(mouse_position)):
                self.hover_modal_key = "child_scroll"
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
            for index, rect in self.items_list_rows.items():
                if rect.collidepoint(mouse_position):
                    self.hover_key = f"itemrow_{index}"
                    break
        if self.hover_key is None:
            if self.sheet_buttons.get("add") and self.sheet_buttons["add"].collidepoint(mouse_position):
                self.hover_key = "sheet_add"
            elif self.sheet_buttons.get("new") and self.sheet_buttons["new"].collidepoint(mouse_position):
                self.hover_key = "sheet_new"
            elif self.sheet_buttons.get("remove") and self.sheet_buttons["remove"].collidepoint(mouse_position):
                self.hover_key = "sheet_remove"
            elif self.sheet_buttons.get("set_tile") and self.sheet_buttons["set_tile"].collidepoint(mouse_position):
                self.hover_key = "sheet_set_tile"
            elif self.info_buttons.get("set_icon") and self.info_buttons["set_icon"].collidepoint(mouse_position):
                self.hover_key = "set_icon"
            elif self.info_buttons.get("import_icon") and self.info_buttons["import_icon"].collidepoint(mouse_position):
                self.hover_key = "import_icon"
            elif self.info_buttons.get("fonts") and self.info_buttons["fonts"].collidepoint(mouse_position):
                self.hover_key = "fonts"
            elif self.info_buttons.get("illustration") and self.info_buttons["illustration"].collidepoint(mouse_position):
                self.hover_key = "illustration"
            elif self.info_buttons.get("background_color") and self.info_buttons["background_color"].collidepoint(mouse_position):
                self.hover_key = "background_color"
            elif self.info_buttons.get("dimensions") and self.info_buttons["dimensions"].collidepoint(mouse_position):
                self.hover_key = "dimensions"
            elif self.info_buttons.get("background_position") and self.info_buttons["background_position"].collidepoint(mouse_position):
                self.hover_key = "background_position"
            elif self.info_buttons.get("submenu_back") and self.info_buttons["submenu_back"].collidepoint(mouse_position):
                self.hover_key = "submenu_back"
            elif self.info_buttons.get("submenu_background") and self.info_buttons["submenu_background"].collidepoint(mouse_position):
                self.hover_key = "submenu_background"
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
        elif key == pygame.K_ESCAPE and self.item_refs_editor_open:
            self._close_item_refs_editor()
        elif key == pygame.K_ESCAPE and self.field_editor_open:
            self._close_field_editor()
        elif key == pygame.K_ESCAPE and self.color_picker_open:
            self._close_color_picker()
        elif key == pygame.K_ESCAPE and self.context_menu_open:
            self.context_menu_open = False
            self.context_add_open = False
        elif key == pygame.K_ESCAPE and self.prop_category:
            self.prop_category = None
        elif key == pygame.K_ESCAPE and self.kind_picker_open:
            self.kind_picker_open = False
        elif key == pygame.K_ESCAPE and self.item_modal_open:
            self._close_item_modal(save=False)
        elif key == pygame.K_ESCAPE and self.canvas_context == "submenu":
            self._exit_submenu_canvas()
        elif key == pygame.K_ESCAPE:
            self._action_back()
        elif key == pygame.K_DELETE and not self.item_modal_open:
            self._delete_selected_item()

    def events(self, event, time_delta):
        if self.prompt_open:
            if event.type == pygame.KEYDOWN:
                self._handle_text_prompt_event(event)
                return True
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
                if self._handle_text_prompt_mouse_event(event):
                    return True
            # let mouse events reach click() for the OK/Cancel buttons
            return False
        if event.type == pygame.MOUSEWHEEL:
            pos = pygame.mouse.get_pos()
            if self.mode == "start":
                if self.project_list_rect.collidepoint(pos):
                    self.project_scroll -= event.y * 48
                return True
            if self.sprite_picker_open and self.picker_tileset_rect.collidepoint(pos):
                self.picker_scroll -= event.y * 40
                return True
            if self.item_modal_open:
                if self.item_refs_editor_open and self.item_refs_scroll_rect.collidepoint(pos) \
                        and self._scroll_item_refs_editor(event.y):
                    return True
                prev = self.modal_buttons.get("preview")
                if prev and prev.collidepoint(pos):
                    self._preview_action(self._selected_item(), "wheel_up" if event.y > 0 else "wheel_down")
                    return True
                if self.property_scroll_rect.collidepoint(pos) and self._scroll_property_list(event.y):
                    return True
                if self.child_scroll_rect.collidepoint(pos) and self._scroll_child_list(event.y):
                    return True
            if self.mode == "editor" and self.left_tab == "items" and self.items_list_rect.collidepoint(pos):
                self.items_list_scroll -= event.y * 40
                return True
            if self.mode == "editor" and not self.item_modal_open and not self.fonts_modal_open \
                    and self.info_panel_rect.collidepoint(pos):
                self.info_scroll = max(0, min(getattr(self, "info_max_scroll", 0),
                                              self.info_scroll - event.y * 48))
                return True
            if self.mode == "editor" and self.active_sheet and self.sheet_rect.collidepoint(pos):
                self.sheet_scroll -= event.y * 40
                return True
        return False

