import copy
import json
import os
import re
import shutil
from tkinter import filedialog, messagebox, simpledialog
from zipfile import ZipFile

import pygame

from Tools import ptext


class TemplateMakerConstants:
    ITEM_KINDS = [
        "Item", "ImageItem", "CountItem", "AlternateCountItem", "IncrementalItem",
        "LabelItem", "EvolutionItem", "DraggableEvolutionItem", "AlternateEvolutionItem",
        "CheckItem", "OpenLinkItem", "GoModeItem", "SubMenuItem", "TimerItem", "EditableBox",
    ]

    # Structural fields required by complex kinds, seeded as defaults and always serialized
    # (not all are editable in the UI, but they keep the item valid for the tracker).
    KIND_REQUIRED = {
        "SubMenuItem": {
            "Background": "background.png", "ItemsList": [],
            "ShowNumbersOfItemsActive": False, "ShowNumberOfCheckedItems": False,
        },
        "TimerItem": {"Timer": {}, "Buttons": {}, "Group": None, "GroupControls": {}},
        "EditableBox": {"Lines": 1, "Style": "default", "PlaceHolder": "",
                        "Sizes": {"w": 120, "h": 32}},
    }

    EVOLUTION_KINDS = ("EvolutionItem", "DraggableEvolutionItem", "AlternateEvolutionItem")

    # Per-kind editable fields. type: int/float/str/strnull/bool/list/sprite
    KIND_FIELDS = {
        "CountItem": [
            {"key": "valueMin", "type": "int", "label": "Value min", "default": 0},
            {"key": "valueMax", "type": "int", "label": "Value max", "default": 99},
            {"key": "valueIncrease", "type": "int", "label": "Increase", "default": 1},
            {"key": "valueStart", "type": "int", "label": "Value start", "default": 0},
        ],
        "AlternateCountItem": [
            {"key": "maxValue", "type": "int", "label": "Max value", "default": 10},
            {"key": "maxValueAlternate", "type": "int", "label": "Max alternate", "default": 10},
            {"key": "customFont", "type": "strnull", "label": "Custom font", "default": None},
        ],
        "IncrementalItem": [
            {"key": "Increment", "type": "list", "label": "Increments", "default": []},
            {"key": "StartIncrementIndex", "type": "int", "label": "Start index", "default": 0},
        ],
        "SubMenuItem": [
            {"key": "Background", "type": "str", "label": "Background img", "default": "background.png"},
            {"key": "ShowNumbersOfItemsActive", "type": "bool", "label": "Show active count", "default": False},
            {"key": "ShowNumberOfCheckedItems", "type": "bool", "label": "Show checked count", "default": False},
        ],
        "LabelItem": [
            {"key": "LabelList", "type": "list", "label": "Labels", "default": [""]},
            {"key": "OffsetLabel", "type": "int", "label": "Offset label", "default": 0},
        ],
        "EvolutionItem": [
            {"key": "Label", "type": "strnull", "label": "Label", "default": None},
            {"key": "LabelCenter", "type": "bool", "label": "Label center", "default": False},
            {"key": "AlternativeLabel", "type": "strnull", "label": "Alt label", "default": None},
        ],
        "DraggableEvolutionItem": [
            {"key": "Label", "type": "strnull", "label": "Label", "default": None},
            {"key": "LabelCenter", "type": "bool", "label": "Label center", "default": False},
            {"key": "AlternativeLabel", "type": "strnull", "label": "Alt label", "default": None},
        ],
        "AlternateEvolutionItem": [
            {"key": "Label", "type": "strnull", "label": "Label", "default": None},
            {"key": "LabelCenter", "type": "bool", "label": "Label center", "default": False},
            {"key": "AlternativeLabel", "type": "strnull", "label": "Alt label", "default": None},
            {"key": "GlobalLabel", "type": "strnull", "label": "Global label", "default": None},
        ],
        "CheckItem": [
            {"key": "check", "type": "sprite", "label": "Check sprite", "default": None},
        ],
        "GoModeItem": [
            {"key": "BackgroundGlow", "type": "str", "label": "Glow image", "default": "background.png"},
        ],
        "OpenLinkItem": [
            {"key": "Link", "type": "str", "label": "Link URL", "default": ""},
        ],
    }

    # Common optional field offered on every kind
    COMMON_FIELDS = [
        {"key": "AlwaysEnable", "type": "bool", "label": "Always enable", "default": False},
    ]

    FONT_SLOTS = [
        "incrementalItemFont", "evolutionItemFont", "countItemFont",
        "labelItemFont", "hintFont",
    ]

    COLORS = {
        "bg": (8, 9, 13),
        "bg_soft": (13, 15, 22),
        "panel": (18, 21, 30),
        "panel_alt": (25, 29, 40),
        "line": (92, 82, 58),
        "line_light": (238, 230, 210),
        "gold": (243, 200, 106),
        "green": (134, 247, 161),
        "muted": (180, 174, 160),
        "purple": (111, 77, 135),
        "brown": (95, 68, 42),
        "red": (170, 70, 70),
        "button": (44, 48, 62),
        "button_text": (248, 244, 232),
    }

    REAL_PREVIEW_KINDS = {
        "Item", "CountItem", "AlternateCountItem", "IncrementalItem",
        "LabelItem", "EvolutionItem", "AlternateEvolutionItem",
        "DraggableEvolutionItem", "CheckItem",
    }

