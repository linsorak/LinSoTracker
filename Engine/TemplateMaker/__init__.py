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
        self.sheets = []
        self.active_sheet_index = 0
        self.sheet_scroll = 0
        self.selected_cell = None
        self.placed_items = []
        self.mode = "start"
        self.project_name = None
        self.project_dir = None
        self.project_info = {}
        self.fonts = self._default_fonts()
        self.font_files = {}
        self.fonts_modal_open = False
        self.fonts_buttons = {}
        self.message = "Create a new template project or open an existing one."
        self.buttons = {}
        self.start_buttons = {}
        self.project_cards = {}
        self.project_delete_buttons = {}
        self.hover_start_key = None
        self.projects = []
        self.property_buttons = {}
        self.modal_buttons = {}
        self.modal_item = None
        self.modal_item_index = None
        self.item_modal_rect = pygame.Rect(0, 0, 1, 1)
        self.position_pick_mode = False
        self.child_edit_index = None
        self.kind_picker_open = False
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
        self.drag_offset = (0, 0)
        self.last_bg_rect = pygame.Rect(0, 0, 1, 1)
        self.item_modal_open = False
        self.last_click_time = 0
        self.last_click_item = None
        self._init_text_prompt()
        self._scan_projects()

