from enum import Enum

import pygame
from pygame import gfxdraw

from Entities.Maps.AttachedItems import (
    add_attached_item, load_attached_items, refresh_attached_images,
    remove_last_attached_item, serialize_attached_items, sync_legacy_attachment,
)


class ConditionsType(Enum):
    DONE = 0
    LOGIC = 1
    OUT_OF_LOGIC = 2
    SCOUTABLE = 3
    UNCERTAIN = 4
    NOT_LOGIC = 5
    PARTIAL_LOGIC = 6


STATE_COLOR_KEYS = {
    ConditionsType.DONE: "Done",
    ConditionsType.LOGIC: "Logic",
    ConditionsType.OUT_OF_LOGIC: "OutOfLogic",
    ConditionsType.SCOUTABLE: "Scoutable",
    ConditionsType.UNCERTAIN: "Uncertain",
    ConditionsType.NOT_LOGIC: "NotLogic",
    ConditionsType.PARTIAL_LOGIC: "HaveLogic",
}

CONDITION_STATE_FIELDS = (
    (ConditionsType.LOGIC, "Conditions"),
    (ConditionsType.OUT_OF_LOGIC, "OutOfLogicConditions"),
    (ConditionsType.SCOUTABLE, "ScoutableConditions"),
    (ConditionsType.UNCERTAIN, "UncertainConditions"),
)

_TRACKER_CALLS = (
    ("labelIs(", "tracker.labelIs("),
    ("haveAlternateValue(", "tracker.haveAlternateValue("),
    ("haveCheck(", "tracker.have_check("),
    ("isChecked(", "tracker.isChecked("),
    ("isVisible(", "tracker.isVisible("),
    ("rules(", "tracker.rules("),
    ("have(", "tracker.have("),
    ("do(", "tracker.do("),
)


def normalize_item_count(value):
    """Return a safe positive weight for a map check."""
    if isinstance(value, bool):
        return 1
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


def compile_map_condition(value, filename):
    if not isinstance(value, str) or not value.strip():
        return None
    expression = value.strip()
    for source, replacement in _TRACKER_CALLS:
        expression = expression.replace(source, replacement)
    return compile(expression, filename, "eval")


def evaluate_map_condition(value, compiled, tracker):
    if compiled is not None:
        return bool(eval(compiled, {"__builtins__": {}}, {"tracker": tracker}))
    return bool(value)


def resolve_condition_state(condition_values, compiled_conditions, tracker):
    """Return the first matching state in green/yellow/blue/purple order."""
    for state, _field in CONDITION_STATE_FIELDS:
        value = condition_values.get(state)
        if value in (None, ""):
            continue
        try:
            if evaluate_map_condition(value, compiled_conditions.get(state), tracker):
                return state
        except Exception:
            continue
    return ConditionsType.NOT_LOGIC


def aggregate_block_state(checks):
    """Summarize visible, unfinished child checks for a Block pin."""
    pending = [check for check in checks if not check.hide and not check.checked]
    if not pending:
        return ConditionsType.DONE, 0

    logic_count = sum(
        check.item_count for check in pending if check.state == ConditionsType.LOGIC)
    if all(check.state == ConditionsType.LOGIC for check in pending):
        return ConditionsType.LOGIC, logic_count
    if logic_count:
        return ConditionsType.PARTIAL_LOGIC, logic_count
    for state in (
            ConditionsType.OUT_OF_LOGIC,
            ConditionsType.SCOUTABLE,
            ConditionsType.UNCERTAIN):
        if any(check.state == state for check in pending):
            return state, 0
    return ConditionsType.NOT_LOGIC, 0

class SimpleCheck:
    def __init__(self, ident, name, positions, linked_map, conditions, hide=False,
                 zone=None, group=None, item_count=1,
                 out_of_logic_conditions=None, scoutable_conditions=None,
                 uncertain_conditions=None):
        self.state = None
        self.id = ident
        self.name = name
        self.positions = positions
        self.map = linked_map
        self.pin = None
        self.pin_color = None
        self.pin_rect = None
        self.checked = False
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
            state: compile_map_condition(value, "<simple-check-condition>")
            for state, value in self.condition_values.items()
        }
        self.compiled_conditions = self.compiled_conditions_by_state[ConditionsType.LOGIC]
        self.hide = hide
        self.focused = False
        self.zone = zone
        self.group = group
        self.item_count = normalize_item_count(item_count)
        self.zoom = self.map.tracker.core_service.zoom
        self.pin_rect = pygame.Rect(0, 0, 1, 1)
        self.dragged_item_name = None
        self.dragged_item_basename = None
        self.dragged_item_index = None
        self.dragged_icon_item_image = None
        self._dragged_scaled_cache_key = None

        self.state = self.evaluate_state()

    def update(self):
        font = self.map.tracker.core_service.get_font("mapFont")
        core_service = self.map.tracker.core_service
        index_positions = self.map.index_positions

        self.state = ConditionsType.DONE if self.checked else self.evaluate_state()
        self.pin_color = self.map.tracker.core_service.get_color_from_font(
            font, STATE_COLOR_KEYS[self.state])
        if self.checked:
            self.focused = False

        simple_check_datas = self.map.tracker.tracker_json_data[4]["SizeSimpleCheck"]
        x = (index_positions[0] * core_service.zoom + self.positions["x"] * core_service.zoom) + (simple_check_datas["w"] * self.zoom) / 2
        y = (index_positions[1] * core_service.zoom + self.positions["y"] * core_service.zoom) + (simple_check_datas["h"] * self.zoom) / 2
        self.pin_rect = pygame.Rect(x, y, (simple_check_datas["w"] * 2) * self.zoom, (simple_check_datas["h"] * 2) * self.zoom)
        self.update_dragged_image()

    def evaluate_conditions(self):
        return evaluate_map_condition(
            self.conditions, self.compiled_conditions, self.map.tracker)

    def evaluate_state(self):
        return resolve_condition_state(
            self.condition_values, self.compiled_conditions_by_state, self.map.tracker)

    def draw_dragged_image(self, screen):
        images = self.dragged_icon_item_images
        if not images:
            return
        spacing = max(10, int(18 * self.map.tracker.core_service.zoom))
        total_width = images[0].get_width() + spacing * (len(images) - 1)
        start_x = self.pin_rect.centerx - total_width // 2
        y = self.pin_rect.y - images[0].get_height() + 4
        for offset, image in enumerate(images):
            screen.blit(image, (start_x + offset * spacing, y))
    def draw(self, screen):
        if not self.hide:
            # zoom = self.map.tracker.core_service.zoom
            zoom = 1.0

            if self.map.tracker.core_service.zoom < 1.0:
                zoom = 1.0

            pin_center = (
                (self.pin_rect.x + (self.pin_rect.w // 2) * zoom),
                (self.pin_rect.y + (self.pin_rect.h // 2) * zoom)
            )

            pin_radius = self.pin_rect.w // 2

            if self.focused:
                font = self.map.tracker.core_service.get_font("mapFont")
                pygame.gfxdraw.filled_circle(screen, int(pin_center[0]), int(pin_center[1]), int((pin_radius + 3) * zoom),
                                             self.map.tracker.core_service.get_color_from_font(font, "Focused"))
                pygame.gfxdraw.aacircle(screen, int(pin_center[0]), int(pin_center[1]), int((pin_radius + 3) * zoom),
                                        pygame.Color("black"))

            pygame.gfxdraw.filled_circle(screen, int(pin_center[0]), int(pin_center[1]), int(pin_radius * zoom), self.pin_color)
            pygame.gfxdraw.aacircle(screen, int(pin_center[0]), int(pin_center[1]), int(pin_radius * zoom),
                                         pygame.Color("black"))


    def draw_circle_with_thickness(self, surface, color, center, radius, thickness):
        for i in range(thickness):
            pygame.gfxdraw.aacircle(surface, int(center[0]), int(center[1]), int(radius + i), color)
        pygame.gfxdraw.aacircle(surface, int(center[0]), int(center[1]), int(radius + thickness), pygame.Color("black"))

    def left_click(self, mouse_position):
        self.checked = not self.checked
        self.map.tracker.reset_hint()
        self.update()

        if self.group:
            grouped_checks = self.map.get_all_group_checks(self, self.group)
            for group_check in grouped_checks:
                group_check.checked = self.checked
                group_check.update()

    def right_click(self, mouse_position):
        if remove_last_attached_item(self):
            self.update_dragged_image()
            self.update()
    def wheel_click(self, mouse_position):
        if not self.checked:
            self.focused = not self.focused

    def update_dragged_image(self):
        zoom = self.map.tracker.core_service.zoom
        size = max(1, int(30 * zoom))
        refresh_attached_images(
            self, self.map.tracker, (size, size))

    def set_new_current_image(self, name, base_name, index=None):
        if not add_attached_item(self, name, base_name, index):
            return False
        self.update_dragged_image()
        self.update()
        return True

    def get_rect(self):
        return self.pin_rect

    def get_position(self):
        return self.pin_rect.x, self.pin_rect.y

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

    def all_check_hidden(self):
        return False
