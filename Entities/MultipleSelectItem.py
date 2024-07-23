import os

import pygame
import pygame_gui

from Entities.Item import Item
from Tools.Bank import Bank

# An entity that represents a collection of possible items, all of which are selectable.
# Left or Right clicking will open a menu that allows selection of some sub-items, and
# selecting one of these will cause the main item to apply an overlay, so that the
# different pieces can be joined together.
# Middle click will deselect all.
#
# An example of this would be boss rewards, which could be presented with a smaller representation
# (like small medallions arranged in a hexagon for OoT) but with a larger submenu to allow
# for easier selection of individual items.
#
# Params:
#   Background: str - Path to an image to overlay on top of the current tracker, to indicate the change in selection mode.
#   BackgroundOffset: Position - Offset from the main item's top left corner to place the top left corner of the background.
#     If omitted, will position background at (0, 0)
#   ItemsList: Item[] - A list of Item entities to be displayed when the submenu is active.
#     Note that Items in the ItemsList should also have a "Representation" object that acts like SheetInformation
#     Omitting this field will use the item's default sprite, so be sure to use a blank image if you don't want that.
class MultipleSelectItem(Item):
    def __init__(self, id, name, image, position, enable, opacity_disable, hint, background_image, resources_path,
                 tracker, items_list, items_sheet_dict, background_offset=None):
        self.background_image_name = background_image
        self.background_image = None
        self.resources_path = resources_path
        self.show = False
        self.items = pygame.sprite.Group()
        self.manager = pygame_gui.UIManager((pygame.display.get_surface().get_size()))
        self.bank = Bank()
        self.tracker = tracker
        self.items_list = items_list
        self.items_sheet_dict = items_sheet_dict
        self.background_x = 0
        self.background_y = 0
        if background_offset:
            self.background_x = position[0] + background_offset[0]
            self.background_y = position[1] + background_offset[1]
        self.update_background()
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable,
                      hint=hint)
        self.init_items()

        self.can_drag = False
        for item in self.items:
            item.can_drag = False
        self.tracker.submenus.add(self)

    def update(self):
        Item.update(self)

        activeItem = next((item for item in self.items if item.enable), None)

        if activeItem == None:
            return

        temp_surface = pygame.Surface([self.position[0], self.position[1]], pygame.SRCALPHA, 32)
        temp_surface = temp_surface.convert_alpha()
        temp_surface.blit(self.colored_image, (0, 0))

        for item in self.items:
            if item.enable and hasattr(item, "representation"):
                temp_surface.blit(item.representation, (0, 0))
        self.image = temp_surface
        return

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
        for item_data, item in zip(self.items_list, self.items):
            if "Representation" in item_data:
                item_sheet = self.items_sheet_dict[item_data["Representation"]["SpriteSheet"]]
                item.representation = self.core_service.zoom_image(
                    item_sheet["ImageSheet"].getImageWithRowAndColumn(
                        row=item_data["Representation"]["row"],
                        column=item_data["Representation"]["column"]
                    )
                )
            else:
                item.representation = item.colored_image


    def left_click(self):
        self.show = not self.show
        self.update()

    def right_click(self):
        self.show = not self.show
        self.update()

    def wheel_click(self):
        # Unselect everything on middle click
        for item in self.items:
            item.enable = False
            item.update()
        self.update()

    def submenu_click(self, mouse_position, button):
        if self.show:
            self.show = self.tracker.items_click(self.items, mouse_position, button)
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
