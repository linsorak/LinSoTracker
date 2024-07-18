import os

import pygame
import pygame_gui

from Entities.Item import Item
from Tools.Bank import Bank

# An entity that represents one of a collection of possible items.
# On right click, will open a submenu with a multiple-choice list of options to pick from
# and selecting one will set that as the choice for the main item.
# The main item can then be selected normally, or optionally can automatically select to the chosen item.
# Middle click will undo all selections.
#
# An example of this would be a bottled item in Majora's Mask, where the contents of the bottle
# could be easily selected and modified, making it less of a hassle to mark, for example, the seahorse.
#
# Params:
#   Background: str - Path to an image to overlay on top of the current tracker, to indicate the change in selection mode.
#   BackgroundOffset: Position - Offset from the main item's top left corner to place the top left corner of the background.
#     If omitted, will position background at (0, 0)
#   ItemsList: Item[] - A list of Item entities to be displayed when the submenu is active.
#   ActiveOnSelection: bool {Optional} - If the main item should be selected upon selecting a subitem
#     (as opposed to picking a subitem and manually enabling). Defaults to False.
#   CloseOnSelection: bool {Optional} - If the submenu should close upon making a selection.
#     Defaults to False.
class MultipleChoiceItem(Item):
    def __init__(self, id, name, image, position, enable, opacity_disable, hint, background_image, resources_path,
                 tracker, items_list, active_on_selection=False, background_offset=None, close_on_selection=False):
        self.background_image_name = background_image
        self.background_image = None
        self.resources_path = resources_path
        self.active_on_selection = active_on_selection
        self.show = False
        self.items = pygame.sprite.Group()
        self.manager = pygame_gui.UIManager((pygame.display.get_surface().get_size()))
        self.bank = Bank()
        self.tracker = tracker
        self.items_list = items_list
        self.close_on_selection = close_on_selection
        self.background_x = 0
        self.background_y = 0
        if background_offset:
            self.background_x = position[0] + background_offset[0]
            self.background_y = position[1] + background_offset[1]
        self.init_items()
        self.update_background()
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable,
                      hint=hint)

        self.can_drag = False
        for item in self.items:
            item.can_drag = False
        self.tracker.submenus.add(self)

    def update(self):
        Item.update(self)

        activeItem = next((item for item in self.items if item.enable), None)

        if activeItem == None:
            return

        if self.enable or self.active_on_selection:
            self.image = activeItem.colored_image
        else:
            self.image = self.alpha_image(activeItem.grey_image)

        if hasattr(activeItem, "label_list"):
            font = self.core_service.get_font("labelItemFont")
            font_path = os.path.join(self.core_service.get_tracker_temp_path(), font["Name"])
            color_category = "Normal"
            self.image = self.get_drawing_text(font=font,
                                           color_category=color_category,
                                           text=activeItem.label_list[activeItem.label_count],
                                           font_path=font_path,
                                           base_image=self.image,
                                           image_surface=self.image,
                                           text_position="label",
                                           offset=activeItem.label_offset)

    def update_background(self):
        self.background_image = self.bank.addZoomImage(os.path.join(self.resources_path, self.background_image_name))

    def draw_submenu(self, screen, time_delta):
        if self.show:
            info_object = pygame.display.Info()
            s = pygame.Surface((info_object.current_w, info_object.current_h), pygame.SRCALPHA)  # per-pixel alpha
            s.fill((0, 0, 0, 70))  # notice the alpha value in the color
            screen.blit(s, (0, 0))

            screen.blit(self.background_image, (self.background_x, self.background_y))
            self.items.draw(screen)

            self.manager.update(time_delta)
            self.manager.draw_ui(screen)

    def init_items(self):
        for item in self.items_list:
            self.tracker.init_item(item, self.items, self.manager)

    def left_click(self):
        if self.active_on_selection:
            # Unselect everything on left click
            """self.enable = False
            for item in self.items:
                item.enable = False
                item.update()"""
            # On second thought, it's probably better to just open the menu
            self.show = not self.show
        else:
            self.enable = not self.enable
        self.update()

    def right_click(self):
        self.show = not self.show

    def wheel_click(self):
        # Unselect everything on middle click
        for item in self.items:
            item.enable = False
            item.update()
        self.update()

    def submenu_click(self, mouse_position, button):
        if self.show:
            self.show = self.tracker.items_click(self.items, mouse_position, button)
            if button == 1 or button == 3:
                # Only check changes on left/right click
                theItem = next((item for item in self.items if item.check_click(mouse_position)), None)
                if theItem != None and theItem.enable:
                    for item in self.items:
                        if item != theItem:
                            item.enable = False
                            item.update()
                if self.close_on_selection:
                    self.show = False
                self.update()

    def get_data(self):
        data = Item.get_data(self)
        items_datas = []

        for item in self.items:
            items_datas.append(item.get_data())

        data["submenu_items"] = items_datas
        return data

    def set_data(self, datas):
        # self.increments_position = datas["increments_position"]
        for item_datas in datas["submenu_items"]:
            for item in self.items:
                if item_datas["name"] == item.name and item_datas["id"] == item.id:
                    item.set_data(item_datas)
                    break

        Item.set_data(self, datas)
