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
        self._ensure_error_popup_state()
        if self.suppress_next_click:
            self.suppress_next_click = False
            return True
        if self.error_popup_open:
            if button in (4, 5):
                self._scroll_error_popup(1 if button == 4 else -1)
                return True
            if button == 1:
                copy_button = self.error_popup_buttons.get("copy")
                close_button = self.error_popup_buttons.get("close")
                if copy_button and copy_button.collidepoint(mouse_position):
                    self._copy_error_popup()
                elif close_button and close_button.collidepoint(mouse_position):
                    self._close_error_popup()
            return True
        if self.prompt_open:
            if button == 1:
                self._handle_text_prompt_click(mouse_position)
            return True
        if self.name_picker_open:
            if button == 1:
                self._handle_name_picker_click(mouse_position)
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

        # Actions editor (overlays map data)
        if self.actions_editor_open:
            if button == 1:
                return self._handle_actions_editor_click(mouse_position)
            return True

        # HideChecks editor (overlays map data)
        if self.hide_editor_open:
            if button == 1:
                return self._handle_hide_editor_click(mouse_position)
            return True

        # Condition builder (overlays map data)
        if self.cond_builder_open:
            if button == 1:
                return self._handle_cond_builder_click(mouse_position)
            return True

        # Map data modal (sizes / counter / rules / conditions)
        if self.map_data_open:
            if button == 1:
                return self._handle_map_data_click(mouse_position)
            return True

        # Map options modal
        if self.map_options_open:
            if button == 1:
                for key, r in self.map_options_buttons.items():
                    if r.collidepoint(mouse_position):
                        if key == "close":
                            self.map_options_open = False
                        elif key == "fit_window":
                            self._fit_window_to_maps()
                        elif key.startswith("mapimg_"):
                            self._import_map_image(self.selected_map_index, key[len("mapimg_"):])
                        elif key.startswith("opt_"):
                            self._edit_map_option(key[len("opt_"):])
                        return True
            return True

        # Check modal (map view)
        if self.check_modal_open:
            if button in (4, 5):
                self._scroll_check_modal(1 if button == 4 else -1)
                return True
            if button == 1:
                for key, r in self.check_modal_buttons.items():
                    if r.collidepoint(mouse_position):
                        if key.startswith("field_"):
                            self._edit_check_field(key[len("field_"):])
                        elif key == "toggle_kind":
                            self._toggle_check_kind()
                        elif key == "add_sub":
                            self._add_block_check()
                        elif key == "add_popup_item":
                            self._add_popup_item()
                        elif key == "close":
                            self._close_check_modal()
                        elif key == "delete":
                            idx = self.selected_check_index
                            self._close_check_modal()
                            self._delete_check(idx)
                        return True
                for (si, part), r in self.check_subrows.items():
                    if r.collidepoint(mouse_position):
                        if part == "del":
                            self._delete_block_check(si)
                        elif part == "up":
                            self._move_block_check(si, -1)
                        elif part == "down":
                            self._move_block_check(si, 1)
                        else:
                            self._edit_block_check_field(si, part)
                        return True
                for (item_index, part), r in getattr(self, "popup_item_rows", {}).items():
                    if r.collidepoint(mouse_position):
                        if part == "del":
                            self._delete_popup_item(item_index)
                        else:
                            self._edit_popup_item_field(item_index, part)
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

        # Map view: click the map to add / select / edit checks
        no_overlay = not (self.item_modal_open or self.prompt_open or self.sprite_picker_open
                          or self.fonts_modal_open or self.check_modal_open
                          or self.map_options_open or self.map_data_open
                          or self.cond_builder_open)
        if no_overlay and self._map_view_active() and button == 1:
            for filter_name, filter_rect in self.map_visibility_buttons.items():
                if not filter_rect.collidepoint(mouse_position):
                    continue
                if filter_name == "blocks":
                    self.show_map_blocks = not self.show_map_blocks
                    state = self.show_map_blocks
                else:
                    self.show_map_checks = not self.show_map_checks
                    state = self.show_map_checks
                self.message = (
                    f"{filter_name.title()} {'shown' if state else 'hidden'}."
                )
                return True
        if no_overlay and self._map_view_active() and self.map_view_rect.collidepoint(mouse_position):
            if self.suppress_next_click:
                self.suppress_next_click = False
                return True
            if button == 1:
                idx = self._check_index_at(mouse_position)
                now = pygame.time.get_ticks()
                if idx is not None:
                    double = self.last_click_item == ("chk", idx) and now - self.last_click_time < 350
                    self.last_click_time = now
                    self.last_click_item = ("chk", idx)
                    self.selected_check_index = idx
                    if double:
                        self._open_check_modal(idx)
                else:
                    self._add_check_at(mouse_position)
                return True
            return True

        # Canvas context menu (right-click duplicate / delete)
        if self.context_menu_open:
            if button == 1:
                for key, r in self.context_menu_buttons.items():
                    if r.collidepoint(mouse_position):
                        if key == "ctx_edit":
                            self._context_edit_target()
                            self.context_menu_open = False
                        elif key == "ctx_duplicate":
                            self._duplicate_item(self.context_menu_index)
                            self.context_menu_open = False
                        elif key == "ctx_unlink":
                            self._context_unlink_target()
                            self.context_menu_open = False
                        elif key == "ctx_delete":
                            self._context_delete_target()
                            self.context_menu_open = False
                        elif key == "ctx_add":
                            self.context_add_mode = "canvas"
                            self.context_add_open = not self.context_add_open
                        elif key == "ctx_add_below":
                            self.context_add_mode = "below"
                            self.context_add_open = not self.context_add_open
                        elif key == "ctx_reset_view":
                            self.canvas_zoom = 1.0
                            self.canvas_pan = [0, 0]
                            self.context_menu_open = False
                            self.context_add_open = False
                            self.message = "Canvas view reset."
                        elif key.startswith("ctxkind_"):
                            kind = key[len("ctxkind_"):]
                            if self.context_add_mode == "below":
                                self._insert_item_kind_below(kind, self.context_menu_index)
                            else:
                                self._add_item_kind_at(kind, self.context_menu_pos)
                            self.context_menu_open = False
                            self.context_add_open = False
                            self.context_add_mode = None
                        return True
            self.context_menu_open = False
            self.context_add_open = False
            self.context_add_mode = None
            return True
        canvas_menu_hit = self.last_bg_rect.collidepoint(mouse_position)
        if self.canvas_context == "main" and self.canvas_view_rect.collidepoint(mouse_position):
            canvas_menu_hit = True
        if button == 3 and no_overlay and canvas_menu_hit:
            linked_path = self._find_linked_item_path_at(mouse_position)
            if linked_path is not None:
                self.selected_linked_path = linked_path
                self.selected_item_index = None
                self._clear_multi_selection()
                self.context_menu_index = None
                self.context_menu_path = linked_path
            else:
                idx = self._get_item_index_at(mouse_position)
                if idx is not None:
                    self._set_single_item_selection(idx)
                self.context_menu_index = idx
                self.context_menu_path = (idx,) if idx is not None else None
            self.context_menu_pos = mouse_position
            self.context_menu_from_list = False
            self.context_menu_open = True
            self.context_add_open = False
            return True
        # Right-click on an Items List row -> context menu (Edit / Duplicate / Delete)
        if button == 3 and no_overlay and self.left_tab == "items":
            for index, rect in self.items_list_rows.items():
                if rect.collidepoint(mouse_position):
                    entry = self.items_list_entries[index]
                    self.context_menu_path = entry["path"]
                    self.context_menu_index = entry["path"][0] if entry["depth"] == 0 else None
                    if entry["depth"] == 0:
                        self._set_single_item_selection(entry["path"][0])
                    self.context_menu_pos = mouse_position
                    self.context_menu_from_list = True
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
            if self.snap_rect.collidepoint(mouse_position):
                self.snap_enabled = not self.snap_enabled
                self.message = f"Snap to items {'ON' if self.snap_enabled else 'OFF'}."
                return True
            if self.grid_rect.collidepoint(mouse_position):
                self.grid_shown = not self.grid_shown
                self.message = f"Grid {'shown (snaps to grid)' if self.grid_shown else 'hidden'}."
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

            # Maps tab: list rows + buttons + checks list
            if self.left_tab == "maps":
                for index, rect in self.maps_rows.items():
                    if rect.collidepoint(mouse_position):
                        self.selected_map_index = index
                        self.selected_check_index = None
                        self.expanded_blocks = set()
                        self.maps_checks_scroll = 0
                        self._reset_map_view()
                        return True
                for key, rect in self.maps_buttons.items():
                    if rect.collidepoint(mouse_position):
                        if key == "map_add":
                            self._add_map()
                        elif key == "map_remove":
                            self._remove_map(self.selected_map_index)
                        elif key == "map_rename":
                            self._rename_map(self.selected_map_index)
                        elif key == "map_options":
                            self._open_map_options()
                        elif key == "map_data":
                            self._open_map_data()
                        elif key == "fit_window":
                            self._fit_window_to_maps()
                        elif key.startswith("mapimg_"):
                            self._import_map_image(self.selected_map_index, key[len("mapimg_"):])
                        return True
                for rect, meta in self.map_check_rows:
                    if not rect.collidepoint(mouse_position):
                        continue
                    t = meta["t"]
                    if t == "toggle":
                        if meta["i"] in self.expanded_blocks:
                            self.expanded_blocks.discard(meta["i"])
                        else:
                            self.expanded_blocks.add(meta["i"])
                        return True
                    target = meta["i"]
                    now = pygame.time.get_ticks()
                    double = self.last_click_item == ("mapchk", target) and now - self.last_click_time < 350
                    self.last_click_time = now
                    self.last_click_item = ("mapchk", target)
                    self.selected_check_index = target
                    if double or t == "sub":
                        self._open_check_modal(target)
                    return True

            # Items List tab rows (click select, double-click edit) - top-level + linked
            if self.left_tab == "items":
              for key, rect in getattr(self, "items_list_buttons", {}).items():
                if rect.collidepoint(mouse_position):
                    if key == "item_order_up":
                        self._move_selected_items_in_list(-1)
                    elif key == "item_order_down":
                        self._move_selected_items_in_list(1)
                    return True
              for index, rect in self.items_list_rows.items():
                if rect.collidepoint(mouse_position) and index < len(self.items_list_entries):
                    entry = self.items_list_entries[index]
                    path = entry["path"]
                    if not path or path[0] >= len(self.placed_items):
                        return True
                    now = pygame.time.get_ticks()
                    double = self.last_click_item == index and now - self.last_click_time < 350
                    self.last_click_time = now
                    self.last_click_item = index
                    if entry["depth"] == 0:
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                            selected = self._toggle_item_selection(path[0])
                            self.message = f"{len(selected)} item(s) selected."
                            return True
                        self._set_single_item_selection(path[0])
                        if double:
                            self._open_item_modal(path[0])
                    else:
                        self.selected_item_index = None
                        self.selected_linked_path = path
                        self._clear_multi_selection()
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
                    elif key == "map_template":
                        self._toggle_map_template()
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
                    elif key == "submenu_counter":
                        if self.submenu_parent:
                            value = not bool(self.submenu_parent.get("ShowNumbersOfItemsActive"))
                            self.submenu_parent["ShowNumbersOfItemsActive"] = value
                            self.message = f"Submenu counter {'enabled' if value else 'disabled'}."
                    elif key == "submenu_checked_counter":
                        if self.submenu_parent:
                            value = not bool(self.submenu_parent.get("ShowNumberOfCheckedItems"))
                            self.submenu_parent["ShowNumberOfCheckedItems"] = value
                            self.message = f"Submenu checked counter {'enabled' if value else 'disabled'}."
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
                self._clear_multi_selection()
                item = self._get_linked_item_by_path(linked_path)
                if not item:
                    return True
                if double:
                    self._open_item_modal(linked_path[0], linked_path)
                    self.message = f"Editing linked {item['name']}."
                else:
                    self.message = (
                        f"Selected linked {item['name']} at "
                        f"{item.get('x', 0)}, {item.get('y', 0)}. Double-click to edit."
                    )
                return True

            item_index = self._get_item_index_at(mouse_position)
            if item_index is not None:
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    selected = self._toggle_item_selection(item_index)
                    self.last_click_time = pygame.time.get_ticks()
                    self.last_click_item = item_index
                    self.message = f"{len(selected)} item(s) selected."
                    return True
                now = pygame.time.get_ticks()
                double = self.last_click_item == item_index and now - self.last_click_time < 350
                self.last_click_time = now
                self.last_click_item = item_index
                self._set_single_item_selection(item_index)
                item = self.placed_items[item_index]
                if double:
                    self._open_item_modal(item_index)
                    self.message = f"Editing {item['name']}."
                else:
                    self.message = (
                        f"Selected {item['name']} at "
                        f"{item.get('x', 0)}, {item.get('y', 0)}. Double-click to edit."
                    )
                return True

            if (self.selected_cell or self.placement_kind) and self.last_bg_rect.collidepoint(mouse_position):
                self.selected_linked_path = None
                self._place_item(mouse_position)
                return True

        return True

    def click_down(self, mouse_position, button):
        self._ensure_error_popup_state()
        if button != 1:
            return
        # The topmost error popup may only start its own scrollbar.
        if self.error_popup_open:
            self._start_scrollbar_drag(mouse_position, only="error_popup")
            return
        # Generic draggable scrollbars (panels, pickers, fonts, checks list)
        if self._start_scrollbar_drag(mouse_position):
            return
        if self.name_picker_open:
            return
        # Condition node-graph: start dragging a node or a wire
        if self.cond_builder_open and self._cg_start_drag(mouse_position):
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
                or self.sprite_picker_open or self.check_modal_open
                or self.map_options_open or self.map_data_open):
            return
        if self._map_view_active() and any(
                rect.collidepoint(mouse_position)
                for rect in self.map_visibility_buttons.values()):
            return
        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            return
        # Map view: drag a check marker, or pan the map (empty area)
        if self._map_view_active() and self.map_view_rect.collidepoint(mouse_position):
            idx = self._check_index_at(mouse_position)
            if idx is not None:
                self.selected_check_index = idx
                self.dragging_check_index = idx
                self.check_drag_moved = False
                self.check_drag_start = mouse_position
                marker_rect = self.check_screen_rects.get(idx)
                marker_anchor = self.check_screen_anchors.get(
                    idx, marker_rect.center if marker_rect else mouse_position)
                self.check_drag_offset = (
                    mouse_position[0] - marker_anchor[0],
                    mouse_position[1] - marker_anchor[1],
                )
            else:
                self.panning_map = True
                self.map_pan_moved = False
                self.pan_start = mouse_position
                self.pan_origin = list(self.map_pan)
            return
        linked_path = self._find_linked_item_path_at(mouse_position)
        if linked_path is not None:
            item = self._get_linked_item_by_path(linked_path)
            if item is None:
                return
            self.selected_item_index = linked_path[0]
            self.selected_linked_path = linked_path
            self._clear_multi_selection()
            self.dragging_linked_path = linked_path
            self.item_drag_start = mouse_position
            self.item_drag_moved = False
            rect = item.get("screen_rect", pygame.Rect(mouse_position[0], mouse_position[1], 1, 1))
            self.drag_offset = (mouse_position[0] - rect.x, mouse_position[1] - rect.y)
            return
        if self.dragging_item_index is None:
            item_index = self._get_item_index_at(mouse_position)
            if item_index is None:
                if (self.canvas_context == "main" and self.canvas_view_rect.collidepoint(mouse_position)
                        and not self.selected_cell and not self.placement_kind):
                    self.panning_canvas = True
                    self.pan_start = mouse_position
                    self.pan_origin = list(self.canvas_pan)
                    self.suppress_next_click = True
                return
            if item_index not in self._selected_indices():
                self._set_single_item_selection(item_index)
            else:
                self.selected_item_index = item_index
                self.selected_linked_path = None
            self.dragging_item_index = item_index
            self.item_drag_start = mouse_position
            self.item_drag_moved = False
            item = self.placed_items[item_index]
            rect = item.get("screen_rect", pygame.Rect(mouse_position[0], mouse_position[1], 1, 1))
            self.drag_offset = (mouse_position[0] - rect.x, mouse_position[1] - rect.y)
            self.group_drag_offsets = {
                index: (self.placed_items[index].get("x", 0), self.placed_items[index].get("y", 0))
                for index in self._selected_indices()
            }

    def mouse_up(self):
        if self.cond_builder_open and (self.cg_drag_node is not None or self.cg_drag_wire_src is not None
                                       or self.cg_panning):
            mp = pygame.mouse.get_pos()
            self._cg_drag_end(mp)
        self.dragging_item_index = None
        self.dragging_linked_path = None
        self.item_drag_start = (0, 0)
        self.item_drag_moved = False
        self.group_drag_offsets = {}
        self.dragging_check_index = None
        self.check_drag_moved = False
        self.check_drag_start = (0, 0)
        self.check_drag_offset = (0, 0)
        self.dragging_scrollbar = None
        self.panning_map = False
        self.map_pan_moved = False
        self.panning_canvas = False
        self.snap_guides = []
        self.dragging_child_scroll = False
        self.dragging_property_scroll = False

    def mouse_move(self, mouse_position):
        self._ensure_error_popup_state()
        if self.error_popup_open:
            if self.dragging_scrollbar is not None:
                self._update_scrollbar_drag(mouse_position)
                self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND)
                return
            self.hover_key = None
            self.hover_property_key = None
            self.hover_modal_key = None
            copy_button = self.error_popup_buttons.get("copy")
            close_button = self.error_popup_buttons.get("close")
            if copy_button and copy_button.collidepoint(mouse_position):
                self.hover_modal_key = "error_copy"
            elif close_button and close_button.collidepoint(mouse_position):
                self.hover_modal_key = "error_close"
            self._set_cursor_safe(
                pygame.SYSTEM_CURSOR_HAND
                if self.hover_modal_key else pygame.SYSTEM_CURSOR_ARROW
            )
            return
        if self.cond_builder_open and self._cg_drag_move(mouse_position):
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND)
            return
        if self.panning_map:
            dx = mouse_position[0] - self.pan_start[0]
            dy = mouse_position[1] - self.pan_start[1]
            if not self.map_pan_moved:
                if dx * dx + dy * dy < 25:
                    return
                self.map_pan_moved = True
                self.suppress_next_click = True
            self.map_pan[0] = self.pan_origin[0] + dx
            self.map_pan[1] = self.pan_origin[1] + dy
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND)
            return
        if self.panning_canvas:
            self.canvas_pan[0] = self.pan_origin[0] + (mouse_position[0] - self.pan_start[0])
            self.canvas_pan[1] = self.pan_origin[1] + (mouse_position[1] - self.pan_start[1])
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND)
            return
        if self.dragging_scrollbar is not None:
            self._update_scrollbar_drag(mouse_position)
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND)
            return
        if self.dragging_check_index is not None:
            if not self.check_drag_moved:
                dx = mouse_position[0] - self.check_drag_start[0]
                dy = mouse_position[1] - self.check_drag_start[1]
                if dx * dx + dy * dy < 25:
                    return
                self.check_drag_moved = True
                self.suppress_next_click = True
            target_position = (
                mouse_position[0] - self.check_drag_offset[0],
                mouse_position[1] - self.check_drag_offset[1],
            )
            self._move_check(self.dragging_check_index, target_position)
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND)
            return
        if self.dragging_linked_path is not None:
            if not self.item_drag_moved:
                dx = mouse_position[0] - self.item_drag_start[0]
                dy = mouse_position[1] - self.item_drag_start[1]
                if dx * dx + dy * dy < 25:
                    return
                self.item_drag_moved = True
                self.suppress_next_click = True
                item = self._get_linked_item_by_path(self.dragging_linked_path)
                if item:
                    self.message = f"Moving linked {item['name']}."
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
        if self.name_picker_open:
            if self.name_picker_buttons.get("close") and self.name_picker_buttons["close"].collidepoint(mouse_position):
                self.hover_modal_key = "np_close"
            else:
                for i, (row, _nm) in self.name_picker_rows.items():
                    if row.collidepoint(mouse_position):
                        self.hover_modal_key = f"np_row_{i}"
                        break
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND if self.hover_modal_key else pygame.SYSTEM_CURSOR_ARROW)
            return
        if self.actions_editor_open:
            for key, rect in self.actions_editor_buttons.items():
                if rect.collidepoint(mouse_position):
                    self.hover_modal_key = key
                    break
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND if self.hover_modal_key else pygame.SYSTEM_CURSOR_ARROW)
            return
        if self.hide_editor_open:
            for key, rect in self.hide_editor_buttons.items():
                if rect.collidepoint(mouse_position):
                    self.hover_modal_key = key
                    break
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND if self.hover_modal_key else pygame.SYSTEM_CURSOR_ARROW)
            return
        if self.cond_builder_open:
            for key, rect in self.cond_builder_buttons.items():
                if rect.collidepoint(mouse_position):
                    self.hover_modal_key = key
                    break
            else:
                for key, (rect, _payload) in self.cond_builder_rows.items():
                    if rect.collidepoint(mouse_position):
                        self.hover_modal_key = key
                        break
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND if self.hover_modal_key else pygame.SYSTEM_CURSOR_ARROW)
            return
        if self.map_data_open:
            for key, rect in self.map_data_buttons.items():
                if rect.collidepoint(mouse_position):
                    self.hover_modal_key = key
                    break
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND if self.hover_modal_key else pygame.SYSTEM_CURSOR_ARROW)
            return
        if self.map_options_open:
            for key, rect in self.map_options_buttons.items():
                if rect.collidepoint(mouse_position):
                    self.hover_modal_key = key
                    break
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND if self.hover_modal_key else pygame.SYSTEM_CURSOR_ARROW)
            return
        if self.check_modal_open:
            for key, rect in self.check_modal_buttons.items():
                if rect.collidepoint(mouse_position):
                    self.hover_modal_key = key
                    break
            over = self.hover_modal_key is not None
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND if over else pygame.SYSTEM_CURSOR_ARROW)
            return
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
                if self.item_modal_open:
                    if self.prop_category and key != "propcat_close" and not key.startswith("field_"):
                        continue
                    if self.child_edit_index is not None and key != "ce_close" and key != "ce_sprite" and not key.startswith("ce_"):
                        continue
                    if self.kind_picker_open and not key.startswith("kindopt_"):
                        continue
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
        if self.hover_key is None and self.left_tab == "maps":
            for key, rect in self.maps_buttons.items():
                if rect.collidepoint(mouse_position):
                    self.hover_key = key
                    break
            else:
                for index, rect in self.maps_rows.items():
                    if rect.collidepoint(mouse_position):
                        self.hover_key = f"maprow_{index}"
                        break
                else:
                    for rect, meta in self.map_check_rows:
                        if rect.collidepoint(mouse_position) and meta["t"] in ("block", "popup", "simple"):
                            self.hover_key = f"mapcheck_{meta['i']}"
                            break
        if self.hover_key is None:
            if self.left_tab == "items":
                for key, rect in getattr(self, "items_list_buttons", {}).items():
                    if rect.collidepoint(mouse_position):
                        self.hover_key = key
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
            elif self.info_buttons.get("map_template") and self.info_buttons["map_template"].collidepoint(mouse_position):
                self.hover_key = "map_template"
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
            elif self.info_buttons.get("submenu_counter") and self.info_buttons["submenu_counter"].collidepoint(mouse_position):
                self.hover_key = "submenu_counter"
            elif self.info_buttons.get("submenu_checked_counter") and self.info_buttons["submenu_checked_counter"].collidepoint(mouse_position):
                self.hover_key = "submenu_checked_counter"
            else:
                for index, rect in self.sheet_list_rows.items():
                    if rect.collidepoint(mouse_position):
                        self.hover_key = f"sheetrow_{index}"
                        break
        if self.dragging_item_index is not None:
            if not self.item_drag_moved:
                dx = mouse_position[0] - self.item_drag_start[0]
                dy = mouse_position[1] - self.item_drag_start[1]
                if dx * dx + dy * dy < 25:
                    return
                self.item_drag_moved = True
                self.suppress_next_click = True
                selected_count = len(self._selected_indices())
                item = self.placed_items[self.dragging_item_index]
                self.message = (f"Moving {selected_count} item(s)." if selected_count > 1
                                else f"Moving {item['name']}.")
            self._move_item_to_mouse(self.dragging_item_index, mouse_position)
        if (self.canvas_rect.collidepoint(mouse_position) or self.left_panel_rect.collidepoint(mouse_position)
                or self.right_panel_rect.collidepoint(mouse_position)):
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_HAND)
        else:
            self._set_cursor_safe(pygame.SYSTEM_CURSOR_ARROW)

    def keyup(self, key, screen):
        self._ensure_error_popup_state()
        if self.error_popup_open:
            if key == pygame.K_ESCAPE:
                self._close_error_popup()
            return
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
        elif key == pygame.K_ESCAPE and self.actions_editor_open:
            self.actions_editor_open = False
        elif key == pygame.K_ESCAPE and self.cond_builder_open:
            if self.cond_builder_mode is not None:
                self.cond_builder_mode = None
            else:
                self.cond_builder_open = False
        elif key == pygame.K_ESCAPE and self.hide_editor_open:
            if self.hide_editor_entry is not None:
                self.hide_editor_entry = None
                self.hide_editor_scroll = 0
            else:
                self.hide_editor_open = False
        elif key == pygame.K_ESCAPE and self.map_data_open:
            self.map_data_open = False
        elif key == pygame.K_ESCAPE and self.map_options_open:
            self.map_options_open = False
        elif key == pygame.K_ESCAPE and self.check_modal_open:
            self._close_check_modal()
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
        elif key == pygame.K_DELETE and self.check_modal_open:
            idx = self.selected_check_index
            self._close_check_modal()
            self._delete_check(idx)
        elif key == pygame.K_DELETE and self._map_view_active():
            self._delete_selected_check()
        elif key == pygame.K_DELETE and not self.item_modal_open:
            self._delete_selected_item()

    def events(self, event, time_delta):
        self._ensure_error_popup_state()
        if self.error_popup_open:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                if event.key == pygame.K_c and event.mod & pygame.KMOD_CTRL:
                    self._copy_error_popup()
                return True
            if event.type == pygame.MOUSEWHEEL:
                self._scroll_error_popup(event.y)
                return True
            if event.type in (
                    pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                    pygame.MOUSEMOTION):
                return False
            return True
        if self.name_picker_open:
            if event.type == pygame.KEYDOWN:
                self._name_picker_key(event)
                return True
            if event.type == pygame.MOUSEWHEEL:
                self.name_picker_scroll = max(0, min(getattr(self, "name_picker_max_scroll", 0),
                                                     self.name_picker_scroll - event.y * 40))
                return True
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                return False  # let click()/mouse_move handle it
            return True
        if self.prompt_open:
            if event.type == pygame.KEYDOWN:
                self._handle_text_prompt_event(event)
                return True
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
                if self._handle_text_prompt_mouse_event(event):
                    return True
            # let mouse events reach click() for the OK/Cancel buttons
            return False
        # Arrow keys nudge the selected item / linked item / map check by 1px (10 with Shift)
        if event.type == pygame.KEYDOWN and self.mode == "editor" and not (
                self.prompt_open or self.item_modal_open or self.fonts_modal_open or self.sprite_picker_open
                or self.color_picker_open or self.map_options_open or self.check_modal_open):
            arrows = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0),
                      pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}
            if event.key in arrows:
                step = 10 if (event.mod & pygame.KMOD_SHIFT) else 1
                ddx, ddy = arrows[event.key]
                if self._nudge_selected(ddx * step, ddy * step):
                    return True
        if event.type == pygame.MOUSEWHEEL:
            pos = pygame.mouse.get_pos()
            if self.mode == "start":
                if self.project_list_rect.collidepoint(pos):
                    self.project_scroll -= event.y * 48
                return True
            if self.check_modal_open:
                self._scroll_check_modal(event.y)
                return True
            if self.cond_builder_open:
                if self.cond_builder_mode in ("have", "do", "rules"):
                    self.cond_builder_scroll = max(0, min(getattr(self, "cond_builder_max_scroll", 0),
                                                          self.cond_builder_scroll - event.y * 48))
                else:
                    self._cg_zoom_at(event.y, pygame.mouse.get_pos())
                return True
            if self.hide_editor_open:
                self.hide_editor_scroll = max(0, min(getattr(self, "hide_editor_max_scroll", 0),
                                                     self.hide_editor_scroll - event.y * 48))
                return True
            if self.map_data_open:
                self.map_data_scroll = max(0, min(getattr(self, "map_data_max_scroll", 0),
                                                  self.map_data_scroll - event.y * 48))
                return True
            if self.fonts_modal_open:
                self.fonts_scroll = max(0, min(getattr(self, "fonts_max_scroll", 0),
                                               self.fonts_scroll - event.y * 48))
                return True
            if self.sprite_picker_open and self.picker_tileset_rect.collidepoint(pos):
                self.picker_scroll -= event.y * 40
                return True
            if self.item_modal_open:
                if self.field_editor_open:
                    self.field_editor_scroll = max(
                        0, min(self.field_editor_max_scroll,
                               self.field_editor_scroll - event.y * 44))
                    return True
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
            if self.mode == "editor" and self.left_tab == "maps" and self.maps_checks_rect.collidepoint(pos):
                self.maps_checks_scroll = max(0, min(getattr(self, "maps_checks_max_scroll", 0),
                                                     self.maps_checks_scroll - event.y * 40))
                return True
            if (self.mode == "editor" and self._map_view_active() and self.map_view_rect.collidepoint(pos)
                    and not (self.map_options_open or self.map_data_open or self.check_modal_open)):
                self._zoom_map(event.y, pos)
                return True
            if (self.mode == "editor" and self.canvas_context == "main"
                    and self.canvas_view_rect.collidepoint(pos)
                    and not (self.item_modal_open or self.fonts_modal_open or self.sprite_picker_open)):
                self._zoom_canvas(event.y, pos)
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
