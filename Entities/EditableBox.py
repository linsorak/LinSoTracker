import json
import os.path

import pygame
import pygame_gui
from pygame import Rect
from pygame_gui.core import ObjectID

from Entities.Item import Item


class EditableBox(Item):
    def __init__(self, id, name, position, size, manager, lines, style, placeholder_text=None, always_enable=False):
        empty_image = pygame.Surface((0, 0), pygame.SRCALPHA)
        Item.__init__(self, id=id, name=name, image=empty_image, position=(0, 0), enable=True,
                      opacity_disable=0.3, hint=None, always_enable=always_enable)
        self.manager = manager
        self.clicked = False

        custom_json = {
            f"@{name}": {
                "colours": {
                    "dark_bg": f"rgb({style['BackgroundColor']['r']}, {style['BackgroundColor']['g']}, {style['BackgroundColor']['b']})",
                    "normal_text": f"rgb({style['NormalTextColor']['r']}, {style['NormalTextColor']['g']}, {style['NormalTextColor']['b']})",
                    "selected_bg": f"rgb({style['SelectedBackgroundColor']['r']}, {style['SelectedBackgroundColor']['g']}, {style['SelectedBackgroundColor']['b']})",
                    "selected_text": f"rgb({style['SelectedTextColor']['r']}, {style['SelectedTextColor']['g']}, {style['SelectedTextColor']['b']})",
                }
            },
            f"@{name}.@selection_list_item": {
                "colours": {
                    "dark_bg": f"rgb({style['BackgroundColor']['r']}, {style['BackgroundColor']['g']}, {style['BackgroundColor']['b']})",
                    "normal_text": f"rgb({style['NormalTextColor']['r']}, {style['NormalTextColor']['g']}, {style['NormalTextColor']['b']})",
                }
            },
            f"@{name}.#item_list_item": {
                "colours": {
                    "normal_bg": f"rgb({style['BackgroundColor']['r']}, {style['BackgroundColor']['g']}, {style['BackgroundColor']['b']})",
                    "hovered_bg": f"rgb({style['HoveredBackgroundColor']['r']}, {style['HoveredBackgroundColor']['g']}, {style['HoveredBackgroundColor']['b']})",
                    "hovered_text": f"rgb({style['HoveredTextColor']['r']}, {style['HoveredTextColor']['g']}, {style['HoveredTextColor']['b']})",
                }
            }
        }

        filename = os.path.join(self.core_service.get_temp_path(), f"{name}.json")
        with open(filename, "w") as json_file:
            json.dump(custom_json, json_file, indent=4)

        manager.get_theme().load_theme(filename)

        self.edit_box = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(position, size),
            placeholder_text=placeholder_text,
            manager=manager,
            object_id=ObjectID(class_id=f'@{name}', object_id=f'#{name}')
        )
        self.edit_box.set_position(position)
        self.lines = lines

        self.suggestion_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect((position[0], position[1] + size[1]), (size[0], size[1] * 2.5)),
            item_list=self.lines,
            manager=manager,
            allow_multi_select=False,
            object_id=ObjectID(class_id=f'@{name}', object_id=f'#{name}_list')
        )
        self.suggestion_list.hide()

        self.edit_box.cursor_blink_interval = 0
        self.edit_box._cursor_alpha = 0

    def handle_event(self, event):
        if not self.enable:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.edit_box.rect.collidepoint(event.pos):
                self.edit_box.focus()
                if len(self.edit_box.get_text()) == 0:
                    self.suggestion_list.set_item_list(self.lines)
                    self.suggestion_list.show()
            else:
                if not self.suggestion_list.rect.collidepoint(event.pos):
                    self.suggestion_list.hide()
                self.edit_box.unfocus()

        # Mise à jour de l'autocomplétion dès que le texte change
        elif event.type == pygame_gui.UI_TEXT_ENTRY_CHANGED and event.ui_element == self.edit_box:
            current_text = event.text
            if current_text:
                matching_suggestions = self.search_items_by_case_insensitive(current_text, self.lines)
                if matching_suggestions:
                    self.suggestion_list.set_item_list(matching_suggestions)
                    self.suggestion_list.show()
                else:
                    self.suggestion_list.hide()
            else:
                self.suggestion_list.set_item_list(self.lines)
                self.suggestion_list.hide()

        elif event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION and event.ui_element == self.suggestion_list:
                selected_suggestion = event.text
                if selected_suggestion:
                    self.edit_box.set_text(selected_suggestion)
                    self.suggestion_list.hide()

    @staticmethod
    def search_items_by_case_insensitive(text, item_list):
        search_lower = text.lower()
        return [item for item in item_list if item.lower().startswith(search_lower)]

    def update_box(self, dt):
        self.edit_box.update(dt)
        self.suggestion_list.update(dt)

    def check_click(self, mouse_position):
        if self.suggestion_list.visible:
            test = Rect(self.edit_box.rect[0], self.edit_box.rect[1],
                        self.suggestion_list.relative_rect[2], self.suggestion_list.relative_rect[3])
            return test.collidepoint(mouse_position)
        else:
            return self.edit_box.rect.collidepoint(mouse_position)

    def left_click(self):
        self.clicked = True

    def disable_click(self):
        self.enable = False
        self.edit_box.disable()

    def enable_click(self):
        self.enable = True
        self.edit_box.enable()

    def get_data(self):
        data = Item.get_data(self)
        data["text"] = self.edit_box.get_text() if hasattr(self, 'edit_box') else ""
        return data

    def set_data(self, datas):
        self.edit_box.set_text(datas["text"])
        Item.set_data(self, datas)
