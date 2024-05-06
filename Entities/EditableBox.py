import pygame
import pygame_gui

from Entities.Item import Item


class EditableBox(Item):
    def __init__(self, id, name, position, size, manager, lines, placeholder_text=None):
        empty_image = pygame.Surface((0, 0), pygame.SRCALPHA)
        Item.__init__(self, id=id, name=name, image=empty_image, position=(0, 0), enable=True,
                      opacity_disable=0.3,
                      hint=None)

        self.edit_box = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(position, size),
            placeholder_text=placeholder_text,
            manager=manager
        )
        self.edit_box.set_position(position)
        self.lines = lines

        self.suggestion_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect((position[0], position[1] + size[1]), (size[0], size[1] * 2.5)),
            item_list=self.lines,
            manager=manager,
            allow_multi_select=False)
        self.suggestion_list.hide()

    def handle_event(self, event):
        self.edit_box.process_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.edit_box.rect.collidepoint(event.pos):
                self.edit_box.focus()
                if len(self.edit_box.get_text()) == 0:
                    self.suggestion_list.show()
            else:
                self.edit_box.unfocus()
                if not self.suggestion_list.rect.collidepoint(event.pos):
                    self.suggestion_list.hide()

        elif event.type == pygame.KEYUP:
            if self.edit_box.is_focused:
                user_input = self.edit_box.get_text().lower()
                if len(user_input) > 0:
                    matching_suggestions = self.search_items_by_case_insensitive(user_input, self.lines)
                    if len(matching_suggestions) > 0:
                        self.suggestion_list.set_item_list(matching_suggestions)
                        self.suggestion_list.show()
                else:
                    self.suggestion_list.set_item_list(self.lines)
                    self.suggestion_list.hide()

        elif event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
                selected_suggestion = event.text
                if selected_suggestion:
                    self.edit_box.set_text(selected_suggestion)
                    self.suggestion_list.hide()

    @staticmethod
    def search_items_by_case_insensitive(text, item_list):
        search_lower = text.lower()
        matching_items = [item for item in item_list if search_lower in item.lower()]
        return matching_items

    def update_box(self, dt):
        self.edit_box.update(dt)
