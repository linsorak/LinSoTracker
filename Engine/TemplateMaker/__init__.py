import copy
import json
import os
import re
import shutil
from tkinter import filedialog, messagebox, simpledialog
from zipfile import ZipFile

import pygame

from Tools import ptext
from Entities.Item import Item
from Entities.CountItem import CountItem
from Entities.AlternateCountItem import AlternateCountItem
from Entities.IncrementalItem import IncrementalItem
from Entities.LabelItem import LabelItem
from Entities.EvolutionItem import EvolutionItem
from Entities.AlternateEvolutionItem import AlternateEvolutionItem
from Entities.DraggableEvolutionItem import DraggableEvolutionItem
from Entities.CheckItem import CheckItem

from Engine.TemplateMaker.constants import TemplateMakerConstants
from Engine.TemplateMaker.drawing import DrawingMixin
from Engine.TemplateMaker.layout import LayoutMixin
from Engine.TemplateMaker.start import StartMixin
from Engine.TemplateMaker.sheets import SheetsMixin
from Engine.TemplateMaker.projectio import ProjectIOMixin
from Engine.TemplateMaker.fonts import FontsMixin
from Engine.TemplateMaker.preview import PreviewMixin
from Engine.TemplateMaker.itemmodal import ItemModalMixin
from Engine.TemplateMaker.input import InputMixin
from Engine.TemplateMaker.textprompt import TextPromptMixin


class TemplateMaker(TemplateMakerConstants, DrawingMixin, LayoutMixin, StartMixin,
                    SheetsMixin, ProjectIOMixin, FontsMixin, PreviewMixin,
                    ItemModalMixin, InputMixin, TextPromptMixin):
    def __init__(self, main_menu):
        self.main_menu = main_menu
        self.core_service = main_menu.core_service
        self.font_path = main_menu.font_data["path"]
        self.font_color = main_menu.font_data["color_normal"]
        self.font_size = main_menu.font_data["size"]
        self.background_path = None
        self.background = None
        self.project_icon = None
        self.illustration = None
        self.illustration_path = None
        self.sheets = []
        self.active_sheet_index = 0
        self.sheet_scroll = 0
        self.selected_cell = None
        self.placement_kind = None
        self.placed_items = []
        self.canvas_context = "main"
        self.main_items = self.placed_items
        self.submenu_parent = None
        self.submenu_parent_index = None
        self.mode = "start"
        self.project_name = None
        self.project_dir = None
        self.project_info = {}
        self.background_color = {"r": 0, "g": 0, "b": 0}
        self.background_position = {"x": 0, "y": 0}
        self.fonts = self._default_fonts()
        self.font_files = {}
        self.fonts_modal_open = False
        self.fonts_buttons = {}
        self.message = "Create a new template project or open an existing one."
        self.buttons = {}
        self.start_buttons = {}
        self.project_cards = {}
        self.project_delete_buttons = {}
        self.project_scroll = 0
        self.project_list_rect = pygame.Rect(0, 0, 1, 1)
        self.hover_start_key = None
        self.projects = []
        self.property_buttons = {}
        self.modal_buttons = {}
        self.modal_item = None
        self.modal_item_index = None
        self.modal_item_path = None
        self.selected_linked_path = None
        self.item_modal_rect = pygame.Rect(0, 0, 1, 1)
        self.position_pick_mode = False
        self.child_edit_index = None
        self.child_scroll = 0
        self.child_scroll_rect = pygame.Rect(0, 0, 1, 1)
        self.child_scroll_track_rect = pygame.Rect(0, 0, 1, 1)
        self.child_scroll_thumb_rect = pygame.Rect(0, 0, 1, 1)
        self.dragging_child_scroll = False
        self.child_scroll_drag_offset = 0
        self.property_scroll = 0
        self.property_scroll_rect = pygame.Rect(0, 0, 1, 1)
        self.property_scroll_track_rect = pygame.Rect(0, 0, 1, 1)
        self.property_scroll_thumb_rect = pygame.Rect(0, 0, 1, 1)
        self.dragging_property_scroll = False
        self.property_scroll_drag_offset = 0
        self.field_editor_open = False
        self.field_editor_spec = None
        self.field_editor_item = None
        self.field_editor_callback = None
        self.item_refs_editor_open = False
        self.item_refs_editor_spec = None
        self.item_refs_editor_item = None
        self.item_refs_selected = set()
        self.item_refs_scroll = 0
        self.item_refs_scroll_rect = pygame.Rect(0, 0, 1, 1)
        self.color_picker_open = False
        self.color_picker_title = ""
        self.color_picker_value = {"r": 255, "g": 255, "b": 255}
        self.color_picker_callback = None
        self.color_picker_buttons = {}
        self.color_picker_wheel_rect = pygame.Rect(0, 0, 1, 1)
        self.kind_picker_open = False
        self.prop_category = None
        self.prop_category_scroll = 0
        self.show_links = False
        self.see_links_rect = pygame.Rect(0, 0, 1, 1)
        self.left_tab = "sheets"
        self.left_tabs = {}
        self.items_list_rows = {}
        self.items_list_entries = []
        self.items_list_scroll = 0
        self.items_list_rect = pygame.Rect(0, 0, 1, 1)
        self.context_menu_open = False
        self.context_add_open = False
        self.context_menu_index = None
        self.context_menu_pos = (0, 0)
        self.context_menu_buttons = {}
        self.sprite_picker_open = False
        self.sprite_picker_target = None
        self.sprite_picker_title = ""
        self.picker_sheet_index = 0
        self.picker_scroll = 0
        self.picker_buttons = {}
        self.picker_geom = None
        self.picker_tileset_rect = pygame.Rect(0, 0, 1, 1)
        self.canvas_rect = pygame.Rect(0, 0, 1, 1)
        self.left_panel_rect = pygame.Rect(0, 0, 1, 1)
        self.right_panel_rect = pygame.Rect(0, 0, 1, 1)
        self.sheet_list_rows = {}
        self.sheet_buttons = {}
        self.info_buttons = {}
        self.info_scroll = 0
        self.info_max_scroll = 0
        self.info_panel_rect = pygame.Rect(0, 0, 1, 1)
        self.sheet_dropdown_open = False
        self.sheet_dropdown_rect = pygame.Rect(0, 0, 1, 1)
        self.sheet_rect = pygame.Rect(0, 0, 1, 1)
        self._tileset_geom = None
        self.template_size = (800, 600)
        self.hover_key = None
        self.hover_property_key = None
        self.hover_modal_key = None
        self.selected_item_index = None
        self.dragging_item_index = None
        self.dragging_linked_path = None
        self.suppress_next_click = False
        self.drag_offset = (0, 0)
        self.last_bg_rect = pygame.Rect(0, 0, 1, 1)
        self.item_modal_open = False
        self.last_click_time = 0
        self.last_click_item = None
        self._uid_counter = 0
        self.status_flash_until = 0
        self._init_text_prompt()
        self._scan_projects()

