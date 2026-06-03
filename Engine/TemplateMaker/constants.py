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

    SPRITE_OPTIONAL_KINDS = {"TimerItem", "EditableBox"}

    # Structural fields required by complex kinds, seeded as defaults and always serialized
    # (not all are editable in the UI, but they keep the item valid for the tracker).
    KIND_REQUIRED = {
        "SubMenuItem": {
            "Background": "background.png", "ItemsList": [],
            "ShowNumbersOfItemsActive": False, "ShowNumberOfCheckedItems": False,
        },
        "TimerItem": {
            "Timer": {
                "Rect": {"x": 0, "y": 0, "w": 180, "h": 42},
                "ShowCentiseconds": True,
                "FixedWidthDigits": True,
            },
            "Buttons": {
                "StartPause": {"Enable": True, "Rect": {"x": 0, "y": 48, "w": 86, "h": 30}},
                "Reset": {"Enable": True, "Rect": {"x": 94, "y": 48, "w": 86, "h": 30}},
            },
            "Group": None,
            "GroupControls": {},
        },
        "EditableBox": {"Lines": [], "Style": {}, "PlaceHolder": "",
                        "Sizes": {"w": 120, "h": 32}},
    }

    EVOLUTION_KINDS = ("EvolutionItem", "DraggableEvolutionItem", "AlternateEvolutionItem")

    # Per-kind editable fields. type: int/float/str/strnull/bool/list/sprite/json/jsonnull/rect/color
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
            {"key": "Increment", "type": "list_editor", "label": "Increments", "default": []},
            {"key": "StartIncrementIndex", "type": "int", "label": "Start index", "default": 0},
        ],
        "SubMenuItem": [
            {"key": "Background", "type": "str", "label": "Background img", "default": "background.png"},
            {"key": "ItemsList", "type": "json", "label": "ItemsList JSON", "default": []},
            {"key": "ShowNumbersOfItemsActive", "type": "bool", "label": "Show active count", "default": False},
            {"key": "ShowNumberOfCheckedItems", "type": "bool", "label": "Show checked count", "default": False},
        ],
        "TimerItem": [
            {"key": "Timer.Rect", "type": "rect", "label": "Timer rect",
             "default": KIND_REQUIRED["TimerItem"]["Timer"]["Rect"]},
            {"key": "Timer.Background.Color", "type": "color", "label": "Timer bg", "default": None},
            {"key": "Timer.Background.BorderColor", "type": "color", "label": "Timer border", "default": None},
            {"key": "Timer.Font.Color", "type": "color", "label": "Timer text", "default": {"r": 150, "g": 255, "b": 160}},
            {"key": "Timer.Font.Size", "type": "int", "label": "Timer font size", "default": 32},
            {"key": "Timer.ShowCentiseconds", "type": "bool", "label": "Show centiseconds", "default": True},
            {"key": "Timer.FixedWidthDigits", "type": "bool", "label": "Fixed digits", "default": True},
            {"key": "Buttons.StartPause.Rect", "type": "rect", "label": "Start rect",
             "default": KIND_REQUIRED["TimerItem"]["Buttons"]["StartPause"]["Rect"]},
            {"key": "Buttons.Reset.Rect", "type": "rect", "label": "Reset rect",
             "default": KIND_REQUIRED["TimerItem"]["Buttons"]["Reset"]["Rect"]},
            {"key": "Buttons.StartPause.Colors.Start", "type": "color", "label": "Start color", "default": {"r": 35, "g": 130, "b": 85}},
            {"key": "Buttons.StartPause.Colors.Pause", "type": "color", "label": "Pause color", "default": {"r": 165, "g": 100, "b": 35}},
            {"key": "Buttons.Reset.Color", "type": "color", "label": "Reset color", "default": {"r": 110, "g": 65, "b": 135}},
            {"key": "Timer", "type": "json", "label": "Timer JSON", "default": KIND_REQUIRED["TimerItem"]["Timer"]},
            {"key": "Buttons", "type": "json", "label": "Buttons JSON", "default": KIND_REQUIRED["TimerItem"]["Buttons"]},
            {"key": "Group", "type": "strnull", "label": "Group", "default": None},
            {"key": "GroupControls", "type": "json", "label": "Group controls JSON", "default": {}},
        ],
        "EditableBox": [
            {"key": "Sizes", "type": "rect", "label": "Size", "default": {"w": 120, "h": 32}},
            {"key": "Lines", "type": "list_editor", "label": "Suggestions", "default": []},
            {"key": "PlaceHolder", "type": "str", "label": "Placeholder", "default": ""},
            {"key": "Style.BackgroundColor", "type": "color", "label": "Background", "default": {"r": 255, "g": 255, "b": 255}},
            {"key": "Style.NormalTextColor", "type": "color", "label": "Text color", "default": {"r": 0, "g": 0, "b": 0}},
            {"key": "Style.SelectedBackgroundColor", "type": "color", "label": "Selected bg", "default": {"r": 40, "g": 110, "b": 190}},
            {"key": "Style.SelectedTextColor", "type": "color", "label": "Selected text", "default": {"r": 255, "g": 255, "b": 255}},
            {"key": "Style.HoveredBackgroundColor", "type": "color", "label": "Hovered bg", "default": {"r": 70, "g": 70, "b": 70}},
            {"key": "Style.HoveredTextColor", "type": "color", "label": "Hovered text", "default": {"r": 255, "g": 255, "b": 255}},
            {"key": "Style", "type": "json", "label": "Style JSON", "default": {}},
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
        {"key": "HintItems", "type": "jsonnull", "label": "Hint items JSON", "default": None},
        {"key": "ActiveItems", "type": "jsonnull", "label": "Active items JSON", "default": None},
        {"key": "InactiveItems", "type": "jsonnull", "label": "Inactive items JSON", "default": None},
    ]

    FONT_SLOTS = [
        "incrementalItemFont", "evolutionItemFont", "countItemFont",
        "labelItemFont", "hintFont", "subMenuItemFont", "editableBoxFont",
        "timerItemFont",
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

