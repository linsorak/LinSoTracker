import copy
import io
import json
import os
import re
import shutil
from tkinter import filedialog, messagebox, simpledialog
from zipfile import ZipFile

import pygame

from Tools import ptext
from Tools.TemplateChecker import TemplateChecker


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
            # Dotted keys (Timer.Rect, Style.X) are nested; their default is handled by
            # _get_field_value, so don't create a flat literal key for them.
            if "." in spec["key"]:
                continue
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
            illu_file = os.path.join(folder, "illustration.png")
            self.illustration = pygame.image.load(illu_file).convert_alpha() if os.path.exists(illu_file) else None
            self.illustration_path = illu_file if os.path.exists(illu_file) else None
            self.selected_cell = None
            self.selected_item_index = None
            self.item_modal_open = False
            self.placed_items = self._items_from_tracker_json(data[3].get("Items", []))
            self.main_items = self.placed_items
            self.canvas_context = "main"
            self.submenu_parent = None
            self.submenu_parent_index = None
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
                "visible": item.get("Visible", True),
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
                        if spec["type"] == "item_refs":
                            entry[key] = self._items_from_tracker_json(item.get(json_key) or [])
                        else:
                            entry[key] = item[json_key]
            # Capture structural fields (ItemsList, Timer configs...) before seeding defaults
            for key in self.KIND_REQUIRED.get(kind, {}):
                if key in item:
                    entry[key] = item[key]
            self._ensure_kind_defaults(entry)
            entry["uid"] = self._new_uid()
            # Preserve the raw json so complex/unsupported kinds (SubMenuItem, TimerItem,
            # EditableBox...) keep their extra fields on save.
            entry["_raw"] = dict(item)
            result.append(entry)
        return result

    def _action_background(self):
        if getattr(self, "canvas_context", "main") == "submenu":
            self._import_submenu_background()
            return
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

    def _enter_submenu_canvas(self, item):
        if self.canvas_context != "main":
            return
        if not isinstance(item, dict) or item.get("kind") != "SubMenuItem":
            return
        self.main_items = self.placed_items
        self.submenu_parent = item
        self.submenu_parent_index = None
        if "_submenu_items" not in item:
            item["_submenu_items"] = self._items_from_tracker_json(item.get("ItemsList") or [])
        self.placed_items = item["_submenu_items"]
        self.canvas_context = "submenu"
        self.selected_item_index = None
        self.dragging_item_index = None
        self.last_click_item = None
        self.message = f"Editing submenu: {item.get('name', 'SubMenuItem')}."

    def _sync_submenu_canvas(self):
        if self.canvas_context != "submenu" or not self.submenu_parent:
            return
        self.placed_items = [item for item in self.placed_items if item.get("kind") != "SubMenuItem"]
        for index, item in enumerate(self.placed_items, start=1):
            item["id"] = index
        self.submenu_parent["_submenu_items"] = self.placed_items
        self.submenu_parent["ItemsList"] = [self._build_item_json(item) for item in self.placed_items]

    def _exit_submenu_canvas(self):
        if self.canvas_context != "submenu":
            return
        name = self.submenu_parent.get("name", "SubMenuItem") if self.submenu_parent else "SubMenuItem"
        self._sync_submenu_canvas()
        self.placed_items = self.main_items
        self.canvas_context = "main"
        self.submenu_parent = None
        self.submenu_parent_index = None
        self.selected_item_index = None
        self.dragging_item_index = None
        self.last_click_item = None
        self.message = f"Saved submenu items for {name}."

    def _import_submenu_background(self, item=None):
        item = item or self.submenu_parent
        if not item or item.get("kind") != "SubMenuItem":
            self.message = "Select a SubMenuItem first."
            return
        path = filedialog.askopenfilename(
            title="Select submenu background",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            surface = pygame.image.load(path).convert_alpha()
            ext = os.path.splitext(path)[1].lower() or ".png"
            name = self._slugify(os.path.splitext(os.path.basename(path))[0]) or self._slugify(item.get("name", "submenu"))
            file_name = f"{name}{ext}"
            item["Background"] = file_name
            item["_submenu_background_path"] = path
            item["_submenu_background_surface"] = surface
            self.message = f"Submenu background imported: {file_name}."
        except Exception as exc:
            self.message = f"Could not import submenu background: {exc}"

    def _illustration_base_surface(self):
        """The reference illustration (illustration_base.png) from tracker.data."""
        rp = getattr(self.main_menu, "resources_path", None)
        if rp:
            p = os.path.join(rp, "illustration_base.png")
            if os.path.exists(p):
                try:
                    return pygame.image.load(p).convert_alpha()
                except Exception:
                    pass
        try:
            data = os.path.join(self.core_service.get_app_path(), "tracker.data")
            with ZipFile(data) as z:
                return pygame.image.load(io.BytesIO(z.read("illustration_base.png"))).convert_alpha()
        except Exception:
            return None

    def _import_illustration(self):
        path = filedialog.askopenfilename(
            title="Select template illustration",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            surface = pygame.image.load(path).convert_alpha()
            base = self._illustration_base_surface()
            base_size = base.get_size() if base else (1280, 720)
            if surface.get_size() != base_size:
                surface = pygame.transform.smoothscale(surface, base_size)
                self.message = f"Illustration imported (scaled to {base_size[0]}x{base_size[1]})."
            else:
                self.message = "Illustration imported."
            self.illustration = surface
            self.illustration_path = path
        except Exception as exc:
            self.message = f"Could not import illustration: {exc}"

    def _import_icon(self):
        path = filedialog.askopenfilename(
            title="Select template icon",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            self.project_icon = pygame.image.load(path).convert_alpha()
            self.message = f"Icon imported: {os.path.basename(path)}."
        except Exception as exc:
            self.message = f"Could not import icon: {exc}"

    def _action_save(self):
        if self.canvas_context == "submenu":
            self._sync_submenu_canvas()
        # Already-saved / opened project: save directly without re-asking the name
        if self.project_dir and self.project_name:
            self._do_save(self.project_name)
            return
        self._open_text_prompt("Save devtemplate", self.project_name or "My Template",
                               self._do_save, allow_empty=False, label="Template name:")

    def _action_saveas(self):
        if self.canvas_context == "submenu":
            self._sync_submenu_canvas()
        self._open_text_prompt("Save as new devtemplate", self.project_name or "My Template",
                               self._do_save, allow_empty=False, label="New template name:")

    def _do_save(self, name):
        if self.canvas_context == "submenu":
            self._sync_submenu_canvas()
        if not name:
            return
        slug = self._slugify(name)
        if not slug:
            self.message = "Invalid template name."
            return

        # Validate the whole template before writing anything
        sheet_files_preview = {}
        if self.sheets:
            for sheet in self.sheets:
                sheet_files_preview[sheet["name"]] = f"{self._slugify(sheet['name']) or 'sheet'}.png"
        else:
            sheet_files_preview["Normal"] = "items.png"
        preview_json = self._build_tracker_json(name, "background.png", sheet_files_preview)
        checker = TemplateChecker(preview_json)
        if not checker.is_valid():
            errs = checker.errors
            extra = f" (+{len(errs) - 2} more)" if len(errs) > 2 else ""
            self.message = "Save blocked - " + " | ".join(str(e) for e in errs[:2]) + extra
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

        illustration_path = os.path.join(template_dir, illustration_name)
        base = self._illustration_base_surface()
        base_size = base.get_size() if base else (1280, 720)
        if self.illustration is not None:
            illu = self.illustration
            if illu.get_size() != base_size:
                illu = pygame.transform.smoothscale(illu, base_size)
            pygame.image.save(illu, illustration_path)
        elif base is not None:
            pygame.image.save(base, illustration_path)
        else:
            shutil.copyfile(os.path.join(template_dir, background_name), illustration_path)

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
        self._save_submenu_backgrounds(template_dir, source_dir)
        self._save_item_image_assets(template_dir, source_dir)

        tracker_json = self._build_tracker_json(name, background_name, sheet_files)
        with open(os.path.join(template_dir, "tracker.json"), "w", encoding="utf-8") as file:
            json.dump(tracker_json, file, indent=2)

        self.main_menu.process_templates_list()
        self._scan_projects()
        self._flash_status(f"Saved '{name}'  -  {template_dir}")

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

    def _iter_all_items(self, items):
        for item in items:
            yield item
            nested = item.get("_submenu_items")
            if nested is None:
                nested = self._items_from_tracker_json(item.get("ItemsList") or []) if item.get("kind") == "SubMenuItem" else []
            for child in self._iter_all_items(nested):
                yield child

    def _save_submenu_backgrounds(self, template_dir, source_dir=None):
        for item in self._iter_all_items(self.main_items):
            if item.get("kind") != "SubMenuItem":
                continue
            name = item.get("Background")
            if not name:
                continue
            dest = os.path.join(template_dir, name)
            surface = item.get("_submenu_background_surface")
            if surface:
                try:
                    pygame.image.save(surface, dest)
                    continue
                except Exception:
                    pass
            sources = []
            if item.get("_submenu_background_path"):
                sources.append(item["_submenu_background_path"])
            if source_dir:
                sources.append(os.path.join(source_dir, name))
            if self.project_dir:
                sources.append(os.path.join(self.project_dir, name))
            for source in sources:
                if source and os.path.exists(source) and os.path.abspath(source) != os.path.abspath(dest):
                    try:
                        shutil.copyfile(source, dest)
                        break
                    except Exception:
                        pass

    def _save_item_image_assets(self, template_dir, source_dir=None):
        for item in self._iter_all_items(self.main_items):
            for spec in self._kind_fields(item.get("kind", "Item")):
                if spec.get("type") != "image":
                    continue
                name = item.get(spec["key"])
                if not name:
                    continue
                dest = os.path.join(template_dir, name)
                asset = (item.get("_image_assets") or {}).get(spec["key"], {})
                surface = asset.get("surface")
                if surface:
                    try:
                        pygame.image.save(surface, dest)
                        continue
                    except Exception:
                        pass
                sources = []
                if asset.get("path"):
                    sources.append(asset["path"])
                if source_dir:
                    sources.append(os.path.join(source_dir, name))
                if self.project_dir:
                    sources.append(os.path.join(self.project_dir, name))
                for source in sources:
                    if source and os.path.exists(source) and os.path.abspath(source) != os.path.abspath(dest):
                        try:
                            shutil.copyfile(source, dest)
                            break
                        except Exception:
                            pass

    def _build_tracker_json(self, name, background_name, sheet_files):
        fonts = self.fonts or self._default_fonts()
        self._ref_identity_cache = None
        self._save_id_counter = 0
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
                    for item in self.main_items
                    if self._item_ref_identity(item) not in self._referenced_item_identities(self.main_items)
                ]
            }
        ]

    def _referenced_item_identities(self, items):
        """Identities of items embedded as Hint/Active/Inactive refs of another item.
        Those must not also appear as top-level items (the tracker spawns them from
        the parent), otherwise they are rendered twice."""
        if getattr(self, "_ref_identity_cache", None) is not None:
            return self._ref_identity_cache
        referenced = set()

        def walk(item):
            for field in ("HintItems", "ActiveItems", "InactiveItems"):
                for ref in item.get(field) or []:
                    referenced.add(self._item_ref_identity(ref))
                    walk(ref)
            for child in item.get("children") or []:
                walk(child)
            for sub in item.get("_submenu_items") or []:
                walk(sub)
        for it in items:
            walk(it)
        self._ref_identity_cache = referenced
        return referenced

    def _build_item_json(self, item):
        kind = item.get("kind", "Item")
        sheet_name = item.get("sheet", "Normal")
        # Assign a fresh unique Id across the whole template (top-level + linked refs)
        if getattr(self, "_save_id_counter", None) is None:
            self._save_id_counter = 0
        assigned_id = self._save_id_counter
        self._save_id_counter += 1

        # EditableBox is sprite-less and has no enable/hint/opacity/sheet fields
        if kind == "EditableBox":
            return {
                "Id": assigned_id,
                "Kind": "EditableBox",
                "Name": item["name"],
                "Positions": {"x": item["x"], "y": item["y"]},
                "Sizes": item.get("Sizes", {"w": 120, "h": 32}),
                "PlaceHolder": item.get("PlaceHolder", ""),
                "Style": item.get("Style", {}),
                "Lines": item.get("Lines", []),
            }

        # Start from the raw json (if any) to keep fields of unsupported kinds intact
        data = dict(item.get("_raw", {}))
        data.update({
            "Id": assigned_id,
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
            output_key = spec.get("json", key)
            value = item.get(key, spec["default"])
            if spec.get("omit_default") and value == spec["default"]:
                data.pop(output_key, None)
                continue
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
                # Common optional bools (Visible, AlwaysEnable) are omitted when at default
                # to respect strict key counts (CountItem==12, CheckItem==9, GoMode==9).
                # Kind-specific bools (e.g. LabelCenter) are always emitted (mandatory).
                common_bool_keys = {f["key"] for f in self.COMMON_FIELDS if f["type"] == "bool"}
                if spec["key"] in common_bool_keys:
                    if bool(value) == bool(spec["default"]):
                        data.pop(output_key, None)
                    else:
                        data[output_key] = bool(value)
                else:
                    data[output_key] = bool(value)
            elif spec["type"] == "item_refs":
                if value in (None, "", [], {}):
                    data.pop(output_key, None)
                else:
                    data[output_key] = [self._build_item_json(ref_item) for ref_item in value]
            elif spec["type"] == "jsonnull":
                if value in (None, "", [], {}):
                    data.pop(output_key, None)
                else:
                    data[output_key] = value
            elif spec["type"] == "strnull":
                # Optional labels are omitted when empty; "Label" stays (checker needs it)
                if value in (None, "") and output_key != "Label":
                    data.pop(output_key, None)
                else:
                    data[output_key] = value
            else:
                data[output_key] = value

        # Structural fields for complex kinds (SubMenu/Timer/EditableBox)
        for key, default in self.KIND_REQUIRED.get(kind, {}).items():
            data[key] = item.get(key, copy.deepcopy(default))

        if kind == "SubMenuItem":
            submenu_items = item.get("_submenu_items")
            if submenu_items is not None:
                data["ItemsList"] = [self._build_item_json(subitem) for subitem in submenu_items]

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

