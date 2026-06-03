import copy
import json
import os
import re
import shutil
from tkinter import filedialog, messagebox, simpledialog
from zipfile import ZipFile

import pygame

from Tools import ptext


class ProjectIOMixin:
    def _default_fonts(self):
        normal = {"r": 255, "g": 255, "b": 255}
        max_color = {"r": 0, "g": 255, "b": 0}
        fonts = {
            slot: {"Name": "visitor1.ttf", "Size": 16, "Colors": {"Normal": dict(normal), "Max": dict(max_color)}}
            for slot in self.FONT_SLOTS
        }
        if "timerItemFont" in fonts:
            fonts["timerItemFont"]["Size"] = 32
            fonts["timerItemFont"]["Colors"]["Normal"] = {"r": 150, "g": 255, "b": 160}
        return fonts

    def _kind_fields(self, kind):
        return self.KIND_FIELDS.get(kind, []) + self.COMMON_FIELDS

    def _ensure_kind_defaults(self, item):
        kind = item.get("kind", "Item")
        for spec in self._kind_fields(kind):
            if spec["key"] not in item:
                default = spec["default"]
                item[spec["key"]] = copy.deepcopy(default)
        for key, default in self.KIND_REQUIRED.get(kind, {}).items():
            if key not in item:
                item[key] = copy.deepcopy(default)
        if kind in self.EVOLUTION_KINDS:
            item.setdefault("children", [])

    # --- Active sheet proxies (keep legacy reads working) ---
    def _load_template_archive(self, path):
        try:
            slug = self._slugify(os.path.splitext(os.path.basename(path))[0])
            target_dir = os.path.join(self.main_menu.dev_template_directory, slug)
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            os.makedirs(target_dir, exist_ok=True)
            with ZipFile(path, "r") as archive:
                archive.extractall(target_dir)
            self._load_template_folder(target_dir)
        except Exception as exc:
            self.message = f"Could not open template archive: {exc}"

    def _load_template_folder(self, folder):
        try:
            tracker_path = os.path.join(folder, "tracker.json")
            if not os.path.exists(tracker_path):
                self.message = "Selected folder has no tracker.json."
                return
            with open(tracker_path, "r", encoding="utf-8-sig") as file:
                data = json.load(file)

            info = data[0].get("Informations", {})
            datas = data[1].get("Datas", {})
            sheets = datas.get("Items", {})
            if not sheets:
                self.message = "Template has no item sheet."
                return

            self.sheets = []
            for sheet_name, sheet_data in sheets.items():
                sheet_file = os.path.join(folder, sheet_data["ItemsSheet"])
                dims = sheet_data["ItemsSheetDimensions"]
                self.sheets.append({
                    "name": sheet_name,
                    "surface": pygame.image.load(sheet_file).convert_alpha(),
                    "path": sheet_file,
                    "cell_w": dims["width"],
                    "cell_h": dims["height"],
                })
            self.active_sheet_index = 0
            self.sheet_scroll = 0

            self.project_info = dict(info)
            fonts_section = next((s["Fonts"] for s in data if "Fonts" in s), None)
            self.fonts = dict(fonts_section) if fonts_section else self._default_fonts()
            self.font_files = {}
            self.project_name = info.get("Name") or os.path.basename(folder)
            self.project_dir = folder
            self.template_size = (datas["Dimensions"]["width"], datas["Dimensions"]["height"])
            self.background_color = dict(datas.get("BackgroundColor", {"r": 0, "g": 0, "b": 0}))
            self.background_position = dict(datas.get("BackgroundPosition", {"x": 0, "y": 0}))
            self.background_path = os.path.join(folder, datas["Background"])
            self.background = pygame.image.load(self.background_path).convert_alpha()
            icon_file = os.path.join(folder, "icon.png")
            self.project_icon = pygame.image.load(icon_file).convert_alpha() if os.path.exists(icon_file) else None
            self.selected_cell = None
            self.selected_item_index = None
            self.item_modal_open = False
            self.placed_items = self._items_from_tracker_json(data[3].get("Items", []))
            self.mode = "editor"
            self.message = f"Opened {self.project_name}."
        except Exception as exc:
            self.message = f"Could not open project: {exc}"

    def _items_from_tracker_json(self, items):
        default_sheet = self.sheets[0]["name"] if self.sheets else "Normal"
        result = []
        for index, item in enumerate(items, start=1):
            sheet_info = item.get("SheetInformation", {})
            kind = item.get("Kind", "Item")
            entry = {
                "id": item.get("Id", index),
                "name": item.get("Name", f"Item {index}"),
                "kind": kind,
                "x": item.get("Positions", {}).get("x", 0),
                "y": item.get("Positions", {}).get("y", 0),
                "row": sheet_info.get("row", 1),
                "column": sheet_info.get("column", 1),
                "sheet": sheet_info.get("SpriteSheet", default_sheet),
                "isActive": item.get("isActive", False),
                "opacity": item.get("OpacityDisable", 0.5),
                "hint": item.get("Hint"),
                "children": [
                    {
                        "id": child.get("Id", child_index),
                        "name": child.get("Name", f"Child {child_index + 1}"),
                        "row": child.get("SheetInformation", {}).get("row", 1),
                        "column": child.get("SheetInformation", {}).get("column", 1),
                        "sheet": child.get("SheetInformation", {}).get("SpriteSheet", default_sheet),
                        "label": child.get("Label"),
                        "alt_label": child.get("AlternativeLabel"),
                    }
                    for child_index, child in enumerate(item.get("NextItems", []))
                ],
            }
            # Kind-specific fields, read from json into the item dict
            for spec in self._kind_fields(kind):
                key = spec["key"]
                if spec["type"] == "sprite":
                    src = item.get("CheckImageSheetInformation")
                    if src:
                        entry[key] = {
                            "sheet": src.get("SpriteSheet", default_sheet),
                            "row": src.get("row", 1),
                            "column": src.get("column", 1),
                        }
                    else:
                        entry[key] = None
                else:
                    json_key = spec.get("json", key)
                    if json_key in item:
                        entry[key] = item[json_key]
            # Capture structural fields (ItemsList, Timer configs...) before seeding defaults
            for key in self.KIND_REQUIRED.get(kind, {}):
                if key in item:
                    entry[key] = item[key]
            self._ensure_kind_defaults(entry)
            # Preserve the raw json so complex/unsupported kinds (SubMenuItem, TimerItem,
            # EditableBox...) keep their extra fields on save.
            entry["_raw"] = dict(item)
            result.append(entry)
        return result

    def _action_background(self):
        path = filedialog.askopenfilename(
            title="Select template background",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            self.background_path = path
            self.background = pygame.image.load(path).convert_alpha()
            self.message = f"Background loaded: {os.path.basename(path)}"
        except Exception as exc:
            self.message = f"Could not load background: {exc}"

    def _action_save(self):
        self._open_text_prompt("Save devtemplate", self.project_name or "My Template",
                               self._do_save, allow_empty=False, label="Template name:")

    def _do_save(self, name):
        if not name:
            return
        slug = self._slugify(name)
        if not slug:
            self.message = "Invalid template name."
            return

        template_dir = os.path.join(self.main_menu.dev_template_directory, slug)
        source_dir = self.project_dir
        self.project_name = name
        self.project_dir = template_dir
        os.makedirs(template_dir, exist_ok=True)

        background_name = "background.png"
        icon_name = "icon.png"
        illustration_name = "illustration.png"

        if self.background:
            pygame.image.save(self.background, os.path.join(template_dir, background_name))
        else:
            surface = pygame.Surface(self.template_size)
            surface.fill((0, 0, 0))
            pygame.image.save(surface, os.path.join(template_dir, background_name))

        # Save every tileset; build name -> file mapping
        sheet_files = {}
        if self.sheets:
            for sheet in self.sheets:
                file_name = f"{self._slugify(sheet['name']) or 'sheet'}.png"
                pygame.image.save(sheet["surface"], os.path.join(template_dir, file_name))
                sheet_files[sheet["name"]] = file_name
        else:
            file_name = "items.png"
            surface = pygame.Surface((32, 32), pygame.SRCALPHA)
            surface.fill((255, 255, 255, 255))
            pygame.image.save(surface, os.path.join(template_dir, file_name))
            sheet_files["Normal"] = file_name

        if self.background:
            pygame.image.save(self.background, os.path.join(template_dir, illustration_name))
        else:
            shutil.copyfile(os.path.join(template_dir, background_name), os.path.join(template_dir, illustration_name))

        icon = self.project_icon
        if icon is None and self.selected_cell:
            sheet_name, row, column = self.selected_cell
            icon = self._get_icon_surface(row, column, sheet_name)
        elif icon is None and self.sheets:
            icon = self._get_icon_surface(1, 1, self.sheets[0]["name"])
        if icon:
            pygame.image.save(icon, os.path.join(template_dir, icon_name))
        elif os.path.exists(os.path.join(self.main_menu.resources_path, "icon.png")):
            shutil.copyfile(os.path.join(self.main_menu.resources_path, "icon.png"), os.path.join(template_dir, icon_name))
        else:
            pygame.image.save(pygame.Surface((32, 32)), os.path.join(template_dir, icon_name))

        self._save_fonts(template_dir, source_dir)

        tracker_json = self._build_tracker_json(name, background_name, sheet_files)
        with open(os.path.join(template_dir, "tracker.json"), "w", encoding="utf-8") as file:
            json.dump(tracker_json, file, indent=2)

        self.main_menu.process_templates_list()
        self._scan_projects()
        self.message = f"Saved devtemplate: {template_dir}"

    def _save_fonts(self, template_dir, source_dir=None):
        names = {font.get("Name") for font in (self.fonts or {}).values() if font.get("Name")}
        for fname in names:
            dest = os.path.join(template_dir, fname)
            if os.path.exists(dest):
                continue
            source = None
            if source_dir and os.path.exists(os.path.join(source_dir, fname)):
                source = os.path.join(source_dir, fname)
            elif fname in self.font_files and os.path.exists(self.font_files[fname]):
                source = self.font_files[fname]
            elif self.font_path and os.path.exists(self.font_path):
                source = self.font_path
            if source:
                try:
                    shutil.copyfile(source, dest)
                except Exception:
                    pass

    def _build_tracker_json(self, name, background_name, sheet_files):
        fonts = self.fonts or self._default_fonts()
        items_sheets = {}
        for sheet in self.sheets:
            items_sheets[sheet["name"]] = {
                "ItemsSheet": sheet_files.get(sheet["name"], f"{self._slugify(sheet['name'])}.png"),
                "ItemsSheetDimensions": {"width": sheet["cell_w"], "height": sheet["cell_h"]}
            }
        if not items_sheets:
            items_sheets["Normal"] = {
                "ItemsSheet": next(iter(sheet_files.values()), "items.png"),
                "ItemsSheetDimensions": {"width": 32, "height": 32}
            }
        informations = dict(self.project_info or {})
        informations["Name"] = name
        informations.setdefault("Creator", "Template Maker")
        informations.setdefault("Version", "0.1")
        if "Comments" not in informations and "Credits" not in informations:
            informations["Comments"] = "Generated by LinSoTracker Template Maker"
        return [
            {
                "Informations": informations
            },
            {
                "Datas": {
                    "Dimensions": {"width": self.template_size[0], "height": self.template_size[1]},
                    "Background": background_name,
                    "BackgroundColor": dict(self.background_color or {"r": 0, "g": 0, "b": 0}),
                    "BackgroundPosition": dict(self.background_position or {"x": 0, "y": 0}),
                    "Items": items_sheets
                }
            },
            {
                "Fonts": fonts
            },
            {
                "Items": [
                    self._build_item_json(item)
                    for item in self.placed_items
                ]
            }
        ]

    def _build_item_json(self, item):
        kind = item.get("kind", "Item")
        sheet_name = item.get("sheet", "Normal")
        # Start from the raw json (if any) to keep fields of unsupported kinds intact
        data = dict(item.get("_raw", {}))
        data.update({
            "Id": item["id"],
            "Kind": kind,
            "Name": item["name"],
            "Positions": {"x": item["x"], "y": item["y"]},
            "SheetInformation": {
                "row": item["row"],
                "column": item["column"],
                "SpriteSheet": sheet_name
            },
            "isActive": item.get("isActive", False),
            "Hint": item.get("hint"),
            "OpacityDisable": item.get("opacity", 0.5)
        })

        # Kind-specific fields (data-driven from schema)
        for spec in self._kind_fields(kind):
            key = spec["key"]
            if "." in key:
                continue
            value = item.get(key, spec["default"])
            if spec["type"] == "sprite":
                if value:
                    data["CheckImageSheetInformation"] = {
                        "row": value.get("row", item["row"]),
                        "column": value.get("column", item["column"]),
                        "SpriteSheet": value.get("sheet", sheet_name),
                    }
                else:
                    data["CheckImageSheetInformation"] = {
                        "row": item["row"], "column": item["column"], "SpriteSheet": sheet_name
                    }
            elif spec["type"] == "bool":
                if value:  # only emit when enabled
                    data[key] = True
                else:
                    data.pop(key, None)
            elif spec["type"] == "jsonnull":
                if value in (None, "", [], {}):
                    data.pop(key, None)
                else:
                    data[key] = value
            else:
                data[key] = value

        # Structural fields for complex kinds (SubMenu/Timer/EditableBox)
        for key, default in self.KIND_REQUIRED.get(kind, {}).items():
            data[key] = item.get(key, copy.deepcopy(default))

        # Evolution children -> NextItems
        if kind in self.EVOLUTION_KINDS:
            next_items = []
            for child in item.get("children", []):
                nxt = {
                    "Id": child["id"],
                    "Name": child["name"],
                    "SheetInformation": {
                        "row": child["row"],
                        "column": child["column"],
                        "SpriteSheet": child.get("sheet", sheet_name)
                    },
                    "Label": child.get("label"),
                }
                if child.get("alt_label") not in (None, ""):
                    nxt["AlternativeLabel"] = child.get("alt_label")
                next_items.append(nxt)
            data["NextItems"] = next_items

        return data

