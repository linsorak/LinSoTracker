import pygame

from Entities.ImageItem import ImageItem
from Entities.Maps.BlockChecks import BlockChecks


class MapPopupItem:
    def __init__(self, data, tracker):
        self.data = data or {}
        self.tracker = tracker
        self.rect = pygame.Rect(0, 0, 1, 1)
        self.item = None

    def _resolve_item(self):
        item_name = self.data.get("Item") or self.data.get("Name")
        if not item_name:
            self.item = None
            return None
        self.item = self.tracker.find_item(item_name, True) or self.tracker.find_item(item_name)
        return self.item

    def update(self, popup):
        item = self._resolve_item()
        if not item:
            self.rect = pygame.Rect(0, 0, 1, 1)
            return
        item.update()
        zoom = self.tracker.core_service.zoom
        pos = self.data.get("Positions") or {}
        scale = float(self.data.get("Scale", 1.0) or 1.0)
        x = (popup.index_positions[0] + pos.get("x", 0)) * zoom
        y = (popup.index_positions[1] + pos.get("y", 0)) * zoom
        w = max(1, int(item.image.get_width() * scale))
        h = max(1, int(item.image.get_height() * scale))
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self, screen):
        if not self.item or not getattr(self.item, "show_item", True):
            return
        image = self.item.image
        if image.get_size() != self.rect.size:
            image = pygame.transform.smoothscale(image, self.rect.size)
        screen.blit(image, self.rect)

    def click(self, mouse_position, button):
        if not self.item or not getattr(self.item, "show_item", True) or not self.rect.collidepoint(mouse_position):
            return False
        if isinstance(self.item, ImageItem):
            return False

        before_states = self.tracker._snapshot_item_states()
        if button == 1:
            self.item.left_click()
        elif button == 2:
            self.item.wheel_click()
        elif button == 3:
            self.item.right_click()
        elif button == 4:
            self.item.wheel_up()
        elif button == 5:
            self.item.wheel_down()
        else:
            return False

        self.tracker.rebuild_item_indexes()
        changed_item_names = self.tracker._get_changed_item_names(before_states)
        if self.tracker.timer_window:
            self.tracker.timer_window.record_item_changes(
                before_states,
                self.tracker._iter_unique_items(),
                self.tracker._get_check_names_by_item()
            )
        self.tracker.update_checks_for_changed_items(changed_item_names)
        if self.tracker.current_map:
            self.tracker.current_map.update()
        self.item.update()
        return True


class MapPopup(BlockChecks):
    def __init__(self, ident, name, positions, linked_map, popup_items=None, popup_background=None,
                 zone=None, visible_condition=True):
        super().__init__(ident, name, positions, linked_map, zone=zone)
        self.popup_items = [MapPopupItem(item, linked_map.tracker) for item in (popup_items or [])]
        self.popup_background = popup_background
        self.visible_condition = visible_condition
        self.compiled_visible_condition = None
        if isinstance(self.visible_condition, str):
            condition = self.visible_condition.strip()
            condition = condition.replace("have(", "self.map.tracker.have(")
            condition = condition.replace("do(", "self.map.tracker.do(")
            condition = condition.replace("rules(", "self.map.tracker.rules(")
            condition = condition.replace("haveAlternateValue(", "self.map.tracker.haveAlternateValue(")
            condition = condition.replace("isChecked(", "self.map.tracker.isChecked(")
            condition = condition.replace("isVisible(", "self.map.tracker.isVisible(")
            self.compiled_visible_condition = compile(condition, "<map-popup-visible-condition>", "eval")

    def is_visible(self):
        if self.compiled_visible_condition:
            try:
                return bool(eval(self.compiled_visible_condition))
            except Exception:
                return False
        return bool(self.visible_condition)

    def all_check_hidden(self):
        if not self.is_visible():
            return True
        if self.popup_items:
            return False
        return super().all_check_hidden()
