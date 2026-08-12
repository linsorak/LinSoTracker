import os

import pygame
from pygame.sprite import Sprite

from Engine import MainMenu
from Entities.Maps.AttachedItems import (
    add_attached_item, load_attached_items, refresh_attached_images,
    remove_last_attached_item, serialize_attached_items, sync_legacy_attachment,
)
from Entities.Maps.SimpleCheck import (
    ConditionsType, STATE_COLOR_KEYS, compile_map_condition,
    evaluate_map_condition, normalize_item_count, resolve_condition_state,
)

def wrap_popup_text(text, font_path, font_size, max_width):
    """Wrap a popup label on at most two balanced lines."""
    text = str(text)
    if not max_width or "\n" in text:
        return text
    try:
        font = pygame.font.Font(font_path, max(1, int(font_size)))
        if font.size(text)[0] <= max_width:
            return text
        words = text.split()
        if len(words) < 2:
            return text
        candidates = []
        for split in range(1, len(words)):
            first = " ".join(words[:split])
            second = " ".join(words[split:])
            first_width = font.size(first)[0]
            second_width = font.size(second)[0]
            candidates.append((
                max(first_width, second_width),
                abs(first_width - second_width),
                first,
                second,
            ))
        _width, _balance, first, second = min(candidates)
        return f"{first}\n{second}"
    except (OSError, TypeError, ValueError, pygame.error):
        return text


class CheckListItem(Sprite):
    def __init__(self, ident, name, position, conditions, tracker, hide=False,
                 group=None, item_count=1, out_of_logic_conditions=None,
                 scoutable_conditions=None, uncertain_conditions=None):
        Sprite.__init__(self)
        self.dragged_items = []
        self.dragged_icon_item_images = []
        self.dragged_icon_item_image = None
        self.dragged_item_index = None
        self.dragged_item_basename = None
        self.dragged_item_name = None
        self.popup_wrap_width = None
        self.display_line_count = 1
        self.strike_lines = []
        self.y_line_end = None
        self.x_line_end = None
        self.y_line_start = None
        self.x_line_start = None
        self.state = None
        self.surface_shadow = None
        self.surface = None
        self.position_draw = None
        self.id = ident
        self.name = name
        self.position = position
        self.conditions = conditions
        self.out_of_logic_conditions = out_of_logic_conditions
        self.scoutable_conditions = scoutable_conditions
        self.uncertain_conditions = uncertain_conditions
        self.condition_values = {
            ConditionsType.LOGIC: conditions,
            ConditionsType.OUT_OF_LOGIC: out_of_logic_conditions,
            ConditionsType.SCOUTABLE: scoutable_conditions,
            ConditionsType.UNCERTAIN: uncertain_conditions,
        }
        self.compiled_conditions_by_state = {
            state: compile_map_condition(value, "<check-list-condition>")
            for state, value in self.condition_values.items()
        }
        self.compiled_conditions = self.compiled_conditions_by_state[ConditionsType.LOGIC]
        self.tracker = tracker
        self.checked = False
        self.color = None
        self.show = False
        self.hide = hide
        self.group = group
        self.item_count = normalize_item_count(item_count)
        self.focused = False
        self._dragged_scaled_cache_key = None

        self.update(render=False)

    def evaluate_conditions(self):
        return evaluate_map_condition(
            self.conditions, self.compiled_conditions, self.tracker)

    def evaluate_state(self):
        return resolve_condition_state(
            self.condition_values, self.compiled_conditions_by_state, self.tracker)

    def update(self, render=True):
        self.color = None
        font = self.tracker.core_service.get_font("mapFont")
        self.state = ConditionsType.DONE if self.checked else self.evaluate_state()
        self.color = self.tracker.core_service.get_color_from_font(
            font, STATE_COLOR_KEYS[self.state])
        if self.checked:
            self.focused = False

        if not render:
            return

        font_path = os.path.join(self.tracker.core_service.get_tracker_temp_path(), font["Name"])
        outline_color = (0, 0, 0)
        if self.focused:
            outline_color = self.tracker.core_service.get_color_from_font(font, "Focused")

        temp_surface = pygame.Surface(([0, 0]), pygame.SRCALPHA, 32)
        temp_surface = temp_surface.convert_alpha()

        try:
            display_name = self.name if self.item_count == 1 else f"{self.name} (x{self.item_count})"
            display_name = wrap_popup_text(
                display_name, font_path,
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
                outline=1 * self.tracker.core_service.zoom,
                color_outline=outline_color)
        except Exception as e:
            pass

    def left_click(self):
        self.checked = not self.checked
        self.update()

        if self.group:
            grouped_checks = self.tracker.current_map.get_all_group_checks(self, self.group)
            for group_check in grouped_checks:
                group_check.checked = self.checked
                group_check.update()

    def right_click(self):
        if remove_last_attached_item(self):
            self.update_dragged_image()
    def wheel_click(self):
        self.focused = not self.focused
        self.update()

    def get_surface_label(self):
        return self.surface

    def set_position_draw(self, x, y):
        self.position_draw = (x, y)
        self.x_line_start = x
        self.x_line_end = x + self.surface.get_rect().w
        line_count = max(1, self.display_line_count)
        line_height = self.surface.get_rect().h / line_count
        self.strike_lines = [
            (
                (self.x_line_start, y + line_height * (index + 0.5)),
                (self.x_line_end, y + line_height * (index + 0.5)),
            )
            for index in range(line_count)
        ]
        self.y_line_start = self.strike_lines[0][0][1]
        self.y_line_end = self.y_line_start

    def get_position_draw(self):
        return self.position_draw

    def get_dimensions(self):
        return self.surface.get_rect().w, self.surface.get_rect().h
    
    def set_new_current_image(self, name, base_name, index=None):
        if not add_attached_item(self, name, base_name, index):
            return False
        self.update_dragged_image()
        return True

    def update_dragged_image(self):
        zoom = self.tracker.core_service.zoom
        size = max(1, int(26 * zoom))
        refresh_attached_images(self, self.tracker, (size, size))

    def draw(self, screen):
        images = self.dragged_icon_item_images
        if images:
            spacing = max(9, int(16 * self.tracker.core_service.zoom))
            total_width = images[0].get_width() + spacing * (len(images) - 1)
            pos_x = self.position_draw[0] - total_width
            for offset, image in enumerate(images):
                pos_y = ((self.surface.get_rect().h - image.get_rect().h) / 2) + self.position_draw[1]
                screen.blit(image, (pos_x + offset * spacing, pos_y))
        screen.blit(self.surface, self.position_draw)
        if self.checked:
            for line_start, line_end in self.strike_lines:
                pygame.draw.line(
                    screen, self.color, line_start, line_end,
                    int(2 * self.tracker.core_service.zoom))
    def get_data(self):
        sync_legacy_attachment(self)
        return {
            "id": self.id,
            "name": self.name,
            "checked": self.checked,
            "hide": self.hide,
            "focused": self.focused,
            "dragged_items": serialize_attached_items(self),
            "dragged_item_name": self.dragged_item_name,
            "dragged_item_basename": self.dragged_item_basename,
            "dragged_item_index": self.dragged_item_index,
        }

    def set_data(self, datas):
        self.checked = datas.get("checked", False)
        self.hide = datas.get("hide", False)
        self.focused = datas.get("focused", False)
        load_attached_items(self, datas)
        self.update()
        self.update_dragged_image()