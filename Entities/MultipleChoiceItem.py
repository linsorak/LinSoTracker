import os

import pygame

from Entities.CheckItem import CheckItem
from Entities.Item import Item
from Tools.Bank import Bank


class MultipleChoiceItem(Item):
    def __init__(self, id, name, image, position, enable, opacity_disable, hint, background_image, resources_path,
                 tracker, items_list, active_on_selection=False, background_offset=None, close_on_selection=False,
                 dimensions=None, show_numbers_items_active=False, show_numbers_checked_items=False,
                 always_enable=False):
        self.background_image_name = background_image
        self.background_image = None
        self.resources_path = resources_path
        self.active_on_selection = active_on_selection
        self.show = False
        self.items = pygame.sprite.Group()
        self.bank = Bank()
        self.tracker = tracker
        self.items_list = items_list
        self.close_on_selection = close_on_selection
        self.dimensions = dimensions
        self.show_numbers_items_active = show_numbers_items_active
        self.show_numbers_checked_items = show_numbers_checked_items
        self.counter_enable = 0
        self.counter_check = 0
        self.background_x = 0
        self.background_y = 0
        if background_offset:
            self.background_x = position[0] + background_offset[0]
            self.background_y = position[1] + background_offset[1]
        self.init_items()
        self._choice_base_positions = {}
        self.update_background()
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable, hint=hint, always_enable=always_enable)

        self.can_drag = False
        for item in self.items:
            item.can_drag = False
            item.ignore_timer_log = True
            self._choice_base_positions[item] = item.position
        self.tracker.submenus.add(self)

    def update(self):
        Item.update(self)

        active_item = self.get_active_choice()
        if active_item is not None:
            if self.enable or self.active_on_selection:
                self.image = active_item.colored_image
            else:
                self.image = self.alpha_image(active_item.grey_image)

            if hasattr(active_item, "label_list"):
                font = self.core_service.get_font("labelItemFont")
                font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])
                self.image = self.get_drawing_text(
                    font=font,
                    color_category="Normal",
                    text=active_item.label_list[active_item.label_count],
                    font_path=font_path,
                    base_image=self.image,
                    image_surface=self.image,
                    text_position="label",
                    offset=active_item.label_offset,
                )

        if self.show_numbers_items_active:
            self.counter_enable = sum(1 for item in self.items if item.enable)
            self.counter_check = sum(1 for item in self.items if isinstance(item, CheckItem) and item.check)

            font = self.core_service.get_font("subMenuItemFont")
            font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])
            color_category = "Normal" if self.counter_enable != len(self.items) else "Max"
            if self.show_numbers_checked_items:
                text_draw = "{}/{}".format(self.counter_check, self.counter_enable)
            else:
                text_draw = "{}/{}".format(self.counter_enable, len(self.items))

            self.image = self.get_drawing_text(font=font,
                                               color_category=color_category,
                                               text=text_draw,
                                               font_path=font_path,
                                               base_image=self.image,
                                               image_surface=self.image,
                                               text_position="right",
                                               offset=10)

    def get_active_choice(self):
        return next((item for item in self.items if item.enable), None)

    def get_timer_icon_image(self):
        active_item = self.get_active_choice()
        if active_item:
            return active_item.colored_image
        return self.colored_image

    def update_background(self):
        self.background_image = None
        if not self.background_image_name:
            return
        background_path = os.path.join(self.resources_path, self.background_image_name)
        if not os.path.exists(background_path):
            return
        self.background_image = self.bank.addZoomImage(background_path)

    def draw_submenu(self, screen, time_delta):
        if self.show:
            menu_x, menu_y = self.layout_menu(screen)
            info_object = pygame.display.Info()
            s = pygame.Surface((info_object.current_w, info_object.current_h), pygame.SRCALPHA)
            s.fill((0, 0, 0, 70))
            screen.blit(s, (0, 0))

            if self.background_image:
                screen.blit(self.background_image, (menu_x, menu_y))
            self.items.draw(screen)
            for item in self.items:
                if hasattr(item, "draw_box"):
                    item.update_box(time_delta)
                    item.draw_box(screen)

    def init_items(self):
        for item in self.items_list:
            self.tracker.init_item(item, self.items, None)

    def layout_menu(self, screen=None):
        surface = screen or pygame.display.get_surface()
        screen_rect = surface.get_rect() if surface else pygame.Rect(0, 0, 0, 0)
        bounds = None
        for item in self.items:
            base_pos = self._choice_base_positions.get(item, item.position)
            rect = item.base_rect.copy()
            rect.topleft = base_pos
            bounds = rect if bounds is None else bounds.union(rect)
        if self.background_image:
            menu_rect = self.background_image.get_rect()
            if self.dimensions and self.dimensions[0] and self.dimensions[1]:
                menu_rect.size = (int(self.dimensions[0]), int(self.dimensions[1]))
            menu_rect.center = screen_rect.center
            delta_x = menu_rect.x - self.background_x
            delta_y = menu_rect.y - self.background_y
            if bounds is not None and not menu_rect.contains(bounds.move(delta_x, delta_y)):
                # Authored origin puts the choices outside the frame: re-center them in it.
                delta_x = menu_rect.centerx - bounds.centerx
                delta_y = menu_rect.centery - bounds.centery
            menu_pos = menu_rect.topleft
        else:
            if bounds is None:
                return 0, 0
            centered = bounds.copy()
            centered.center = screen_rect.center
            delta_x = centered.x - bounds.x
            delta_y = centered.y - bounds.y
            menu_pos = centered.topleft

        for item in self.items:
            base_pos = self._choice_base_positions.get(item, item.position)
            new_pos = (base_pos[0] + delta_x, base_pos[1] + delta_y)
            item.position = new_pos
            item.base_position = new_pos
            item.rect.topleft = new_pos
            item.base_rect.topleft = new_pos
        return menu_pos

    def left_click(self):
        if self.active_on_selection:
            self.show = not self.show
        elif not self.always_enable:
            self.enable = not self.enable
        self.update()

    def right_click(self):
        self.show = not self.show
        self.update()

    def wheel_click(self):
        for item in self.items:
            item.enable = False
            item.update()
        self.update()

    def submenu_click(self, mouse_position, button):
        if self.show:
            self.layout_menu()
            self.show = self.tracker.items_click(self.items, mouse_position, button)
            if button in (1, 3):
                selected_item = next((item for item in self.items if item.check_click(mouse_position)), None)
                if selected_item is not None and selected_item.enable:
                    for item in self.items:
                        if item != selected_item:
                            item.enable = False
                            item.update()
                if self.close_on_selection:
                    self.show = False
                self.update()

    def get_data(self):
        data = Item.get_data(self)
        data["submenu_items"] = [item.get_data() for item in self.items]
        return data

    def set_data(self, datas):
        for item_datas in datas["submenu_items"]:
            for item in self.items:
                if item_datas["name"] == item.name and item_datas["id"] == item.id:
                    item.set_data(item_datas)
                    break

        Item.set_data(self, datas)
