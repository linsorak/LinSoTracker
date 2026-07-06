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
            slot: {"Name": "NotoSans-Bold.ttf", "Size": 16, "Colors": {"Normal": dict(normal), "Max": dict(max_color)}}
            for slot in self.FONT_SLOTS
        }
        if "timerItemFont" in fonts:
            fonts["timerItemFont"]["Size"] = 32
            fonts["timerItemFont"]["Colors"]["Normal"] = {"r": 150, "g": 255, "b": 160}
        return fonts

    def _active_font_slots(self):
        slots = list(self.FONT_SLOTS)
        if self.is_map_template:
            slots += list(self.MAP_FONT_SLOTS)
        return slots

    def _ensure_map_fonts(self):
        """Seed missing map font slots (with their proper color keys)."""
        for slot in self.MAP_FONT_SLOTS:
            if slot not in self.fonts:
                self.fonts[slot] = copy.deepcopy(self.MAP_FONT_DEFAULTS[slot])

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
            background_name = datas.get("Background")
            self.background_path = os.path.join(folder, background_name) if background_name else None
            self.background = pygame.image.load(self.background_path).convert_alpha() if self.background_path and os.path.exists(self.background_path) else None
            icon_file = os.path.join(folder, "icon.png")
            self.project_icon = pygame.image.load(icon_file).convert_alpha() if os.path.exists(icon_file) else None
            illu_file = os.path.join(folder, "illustration.png")
            self.illustration = pygame.image.load(illu_file).convert_alpha() if os.path.exists(illu_file) else None
            self.illustration_path = illu_file if os.path.exists(illu_file) else None
            self.selected_cell = None
            self.selected_item_index = None
            self.selected_item_indices = set()
            self.item_modal_open = False
            self.placed_items = self._items_from_tracker_json(data[3].get("Items", []))
            self.main_items = self.placed_items
            # Map template: load the Maps list (section 5) + preserve the rest
            if len(data) >= 5 and isinstance(data[4], dict):
                self.is_map_template = True
                self.maps_extra = {k: copy.deepcopy(v) for k, v in data[4].items() if k != "Maps"}
                self.map_source_dir = folder
                self.maps = self._load_maps(data[4].get("Maps", []), folder)
                self._ensure_map_extras()
                self._ensure_map_fonts()
            else:
                self.is_map_template = False
                self.maps_extra = {}
                self.map_source_dir = None
                self.maps = []
            self.canvas_context = "main"
            self.canvas_pan = [0, 0]
            self.canvas_zoom = 1.0
            self.panning_canvas = False
            self.submenu_parent = None
            self.submenu_parent_index = None
            self.mode = "editor"
            self.saved_once = True
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
            if kind == "ImageItem" and not sheet_info:
                entry["sheet"] = None
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
            if kind in ("SubMenuItem", "MultipleChoiceItem"):
                entry["_submenu_items"] = self._items_from_tracker_json(item.get("ItemsList") or [])
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
        if not isinstance(item, dict) or item.get("kind") not in ("SubMenuItem", "MultipleChoiceItem"):
            return
        self.main_items = self.placed_items
        self.submenu_parent = item
        self.submenu_parent_index = None
        if "_submenu_items" not in item:
            item["_submenu_items"] = self._items_from_tracker_json(item.get("ItemsList") or [])
        if item.get("kind") == "MultipleChoiceItem" and not item.get("_multiple_choice_relative"):
            ox, oy = self._multiple_choice_origin(item)
            for choice in item.get("_submenu_items") or []:
                choice["x"] = int(choice.get("x", 0)) - ox
                choice["y"] = int(choice.get("y", 0)) - oy
            item["_multiple_choice_relative"] = True
        self.placed_items = item["_submenu_items"]
        self.canvas_context = "submenu"
        self.selected_item_index = None
        self.selected_item_indices = set()
        self.dragging_item_index = None
        self.last_click_item = None
        label = "choices" if item.get("kind") == "MultipleChoiceItem" else "submenu"
        self.message = f"Editing {label}: {item.get('name', item.get('kind', 'item'))}."

    def _sync_submenu_canvas(self):
        if self.canvas_context != "submenu" or not self.submenu_parent:
            return
        self.placed_items = [
            item for item in self.placed_items
            if item.get("kind") not in ("SubMenuItem", "MultipleChoiceItem")
        ]
        for index, item in enumerate(self.placed_items, start=1):
            item["id"] = index
        self.submenu_parent["_submenu_items"] = self.placed_items
        self.submenu_parent["ItemsList"] = self._build_items_list_json(self.submenu_parent, self.placed_items)

    def _exit_submenu_canvas(self):
        if self.canvas_context != "submenu":
            return
        name = self.submenu_parent.get("name", "Item") if self.submenu_parent else "Item"
        self._sync_submenu_canvas()
        self.placed_items = self.main_items
        self.canvas_context = "main"
        self.submenu_parent = None
        self.submenu_parent_index = None
        self.selected_item_index = None
        self.selected_item_indices = set()
        self.dragging_item_index = None
        self.last_click_item = None
        self.message = f"Saved items for {name}."

    def _multiple_choice_origin(self, item):
        offset = item.get("BackgroundOffset")
        if not offset:
            return (0, 0)
        return (
            int(item.get("x", 0)) + int(offset.get("x", 0)),
            int(item.get("y", 0)) + int(offset.get("y", 0)),
        )

    def _build_items_list_json(self, parent, items):
        if parent.get("kind") != "MultipleChoiceItem":
            return [self._build_item_json(item) for item in items]
        ox, oy = self._multiple_choice_origin(parent)
        exported = []
        for item in items:
            copy_item = copy.deepcopy(item)
            copy_item["x"] = int(copy_item.get("x", 0)) + ox
            copy_item["y"] = int(copy_item.get("y", 0)) + oy
            exported.append(self._build_item_json(copy_item))
        return exported

    def _import_submenu_background(self, item=None):
        item = item or self.submenu_parent
        if not item or item.get("kind") not in ("SubMenuItem", "MultipleChoiceItem"):
            self.message = "Select a SubMenuItem or MultipleChoiceItem first."
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
            label = "Choice" if item.get("kind") == "MultipleChoiceItem" else "Submenu"
            self.message = f"{label} background imported: {file_name}."
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
        if self.saved_once and self.project_dir and self.project_name:
            self._do_save(self.project_name)
            return
        # First save: propose the template folder name
        self._open_text_prompt("Save devtemplate", self.project_name or "My Template",
                               self._do_save, allow_empty=False, label="Template folder name:")

    def _action_saveas(self):
        if self.canvas_context == "submenu":
            self._sync_submenu_canvas()
        self._open_text_prompt("Save as new devtemplate", self.project_name or "My Template",
                               self._do_save, allow_empty=False, label="New template name:")

    def _action_saveto(self):
        if self.canvas_context == "submenu":
            self._sync_submenu_canvas()
        folder = filedialog.askdirectory(title="Choose where to save the template")
        if not folder:
            return

        def cb(name):
            if name:
                self._do_save(name, base_dir=folder)
        self._open_text_prompt("Save in chosen folder", self.project_name or "My Template",
                               cb, allow_empty=False, label="Template name:")

    def _action_export(self):
        if self.canvas_context == "submenu":
            self._sync_submenu_canvas()
        if not (self.project_dir and os.path.isdir(self.project_dir)):
            self.message = "Save the template first, then export."
            return
        default = f"{self._slugify(self.project_name or 'template') or 'template'}.template"
        path = filedialog.asksaveasfilename(
            title="Export template", defaultextension=".template",
            initialfile=default, filetypes=[("LinSoTracker template", "*.template")])
        if not path:
            return
        try:
            with ZipFile(path, "w") as archive:
                for fname in os.listdir(self.project_dir):
                    fp = os.path.join(self.project_dir, fname)
                    if os.path.isfile(fp):
                        archive.write(fp, fname)
            self._flash_status(f"Exported to {path}")
        except Exception as exc:
            self.message = f"Export failed: {exc}"

    def _do_save(self, name, base_dir=None):
        if self.canvas_context == "submenu":
            self._sync_submenu_canvas()
        if not name:
            return
        # Map templates: ensure the window reserves room for the maps (drawn to the
        # right of the items), otherwise they would render off-screen in the tracker.
        if self.is_map_template and self.maps:
            ok, rw, rh = self._map_window_ok()
            if not ok:
                self.template_size = (max(self.template_size[0], rw), max(self.template_size[1], rh))
                self.message = f"Window widened to {self.template_size[0]}x{self.template_size[1]} for maps."
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
        preview_json = self._build_tracker_json(name, "background.png" if self.background else None, sheet_files_preview)
        checker = TemplateChecker(preview_json)
        if not checker.is_valid():
            errs = checker.errors
            extra = f" (+{len(errs) - 2} more)" if len(errs) > 2 else ""
            self.message = "Save blocked - " + " | ".join(str(e) for e in errs[:2]) + extra
            return

        template_dir = os.path.join(base_dir or self.main_menu.dev_template_directory, slug)
        source_dir = self.project_dir
        self.project_name = name
        self.project_dir = template_dir
        os.makedirs(template_dir, exist_ok=True)

        background_name = "background.png" if self.background else None
        icon_name = "icon.png"
        illustration_name = "illustration.png"

        if self.background:
            pygame.image.save(self.background, os.path.join(template_dir, background_name))

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
            surface = pygame.Surface((base_size[0], base_size[1]), pygame.SRCALPHA, 32).convert_alpha()
            surface.fill((0, 0, 0, 0))
            pygame.image.save(surface, illustration_path)

        icon = self.project_icon
        if icon is None and self.selected_cell:
            sheet_name, row, column = self.selected_cell
            icon = self._get_icon_surface(row, column, sheet_name)
        elif icon is None and self.sheets:
            icon = self._get_icon_surface(1, 1, self.sheets[0]["name"])
        if icon:
            pygame.image.save(self._normalized_template_icon(icon), os.path.join(template_dir, icon_name))
        elif os.path.exists(os.path.join(self.main_menu.resources_path, "icon.png")):
            try:
                fallback_icon = pygame.image.load(os.path.join(self.main_menu.resources_path, "icon.png")).convert_alpha()
            except Exception:
                fallback_icon = None
            pygame.image.save(self._normalized_template_icon(fallback_icon), os.path.join(template_dir, icon_name))
        else:
            pygame.image.save(self._normalized_template_icon(None), os.path.join(template_dir, icon_name))

        self._save_fonts(template_dir, source_dir)
        self._save_submenu_backgrounds(template_dir, source_dir)
        self._save_item_image_assets(template_dir, source_dir)
        if self.is_map_template:
            self._save_map_assets(template_dir)

        tracker_json = self._build_tracker_json(name, background_name, sheet_files)
        with open(os.path.join(template_dir, "tracker.json"), "w", encoding="utf-8") as file:
            json.dump(tracker_json, file, indent=2)

        self.saved_once = True
        self.main_menu.process_templates_list()
        self._scan_projects()
        self._flash_status(f"Saved '{name}'  -  {template_dir}")

    @staticmethod
    def _normalized_template_icon(icon):
        target_size = 64
        surface = pygame.Surface((target_size, target_size), pygame.SRCALPHA).convert_alpha()
        surface.fill((0, 0, 0, 0))
        if not icon or icon.get_width() <= 0 or icon.get_height() <= 0:
            return surface
        scale = min(target_size / icon.get_width(), target_size / icon.get_height())
        size = (
            max(1, int(icon.get_width() * scale)),
            max(1, int(icon.get_height() * scale)),
        )
        image = pygame.transform.smoothscale(icon, size) if size != icon.get_size() else icon
        surface.blit(image, (
            (target_size - size[0]) // 2,
            (target_size - size[1]) // 2,
        ))
        return surface

    # ---- Maps model ------------------------------------------------------
    def _toggle_map_template(self):
        if self.is_map_template:
            self.is_map_template = False
            if self.left_tab == "maps":
                self.left_tab = "sheets"
            self.message = "Map template OFF - Maps section will not be saved."
            return
        if not self.maps:
            self.maps = [self._new_map_dict("Main Map")]
            self.selected_map_index = 0
        self._ensure_map_extras()
        self.is_map_template = True
        self._ensure_map_fonts()
        self.left_tab = "maps"
        self.message = "Map template ON - manage maps in the Maps tab."

    def _new_map_dict(self, name, json_file=None):
        """Build an in-memory map (Datas scaffold + empty checks + placeholder
        assets), mirroring devtemplates/twilightprincessmap."""
        w, h = self.template_size
        datas = {
            "Name": name,
            "Background": None,
            "Dimensions": {"width": w, "height": h},
            "SubMenuBackground": None,
            "DrawBoxRect": {"x": int(w * 0.30), "y": int(h * 0.25), "w": int(w * 0.40), "h": int(h * 0.50)},
            "DrawBoxRectSubTitle": {"x": int(w * 0.30), "y": int(h * 0.28), "w": int(w * 0.40), "h": int(h * 0.47)},
            "LabelY": int(h * 0.18),
            "LeftArrow": {"Image": None, "Positions": {"x": int(w * 0.45), "y": int(h * 0.86)}},
            "RightArrow": {"Image": None, "Positions": {"x": int(w * 0.52), "y": int(h * 0.86)}},
        }
        return {
            "name": name,
            "json_file": json_file or self._unique_map_file(name),
            "data": {"Datas": datas, "ChecksList": []},
            "assets": {},          # key -> pygame.Surface (loaded/imported)
        }

    def _unique_map_file(self, name):
        base = self._slugify(name) or "map"
        existing = {m["json_file"] for m in self.maps}
        candidate = f"{base}.json"
        i = 1
        while candidate in existing:
            candidate = f"{base}-{i}.json"
            i += 1
        return candidate

    def _load_maps(self, maps_list, folder):
        maps = []
        for entry in maps_list:
            jf = entry.get("Datas", "main_map.json")
            path = os.path.join(folder, jf)
            inner = {"Datas": {}, "ChecksList": []}
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8-sig") as f:
                        content = json.load(f)
                    inner = content[0] if isinstance(content, list) and content else content
                except Exception:
                    pass
            d = inner.get("Datas", {})
            for check in inner.get("ChecksList", []):
                if check.get("Kind") == "MapPopup":
                    check.pop("Checks", None)
            m = {"name": d.get("Name", jf), "json_file": jf, "data": inner, "assets": {}}
            for key in ("Background", "SubMenuBackground"):
                self._load_map_asset(m, key, d.get(key), folder)
            for key in ("LeftArrow", "RightArrow"):
                self._load_map_asset(m, key, (d.get(key) or {}).get("Image"), folder)
            maps.append(m)
        return maps

    def _load_map_asset(self, m, key, filename, folder):
        if not filename:
            return
        path = os.path.join(folder, filename)
        if os.path.isfile(path):
            try:
                m["assets"][key] = pygame.image.load(path).convert_alpha()
            except Exception:
                pass

    def _add_map(self):
        name = f"Map {len(self.maps) + 1}"
        self.maps.append(self._new_map_dict(name))
        self.selected_map_index = len(self.maps) - 1
        self.message = f"Added {name}."

    def _remove_map(self, index):
        if not (0 <= index < len(self.maps)):
            return
        if len(self.maps) <= 1:
            self.message = "A map template needs at least one map."
            return
        removed = self.maps.pop(index)
        self.selected_map_index = max(0, min(self.selected_map_index, len(self.maps) - 1))
        self.message = f"Removed {removed['name']}."

    def _import_map_image(self, index, asset_key):
        """Import an image for a map asset (Background / SubMenuBackground /
        LeftArrow / RightArrow)."""
        if not (0 <= index < len(self.maps)):
            return
        path = filedialog.askopenfilename(
            title=f"Select {asset_key} image",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")])
        if not path:
            return
        try:
            surface = pygame.image.load(path).convert_alpha()
        except Exception as exc:
            self.message = f"Could not load image: {exc}"
            return
        m = self.maps[index]
        m["assets"][asset_key] = surface
        filename = f"{self._slugify(m['name']) or 'map'}_{asset_key.lower()}.png"
        data = m["data"]["Datas"]
        if asset_key in ("LeftArrow", "RightArrow"):
            data.setdefault(asset_key, {"Image": None, "Positions": {"x": 0, "y": 0}})
            data[asset_key]["Image"] = filename
        else:
            data[asset_key] = filename
        self.message = f"{asset_key} set for {m['name']}."

    def _ensure_map_extras(self):
        """Seed the section-5 keys the tracker reads unconditionally for a map
        (sizes, checks counter, action helpers), so a fresh map template runs."""
        e = self.maps_extra
        e.setdefault("SizeSimpleCheck", {"w": 5, "h": 5})
        e.setdefault("SizeGroupChecks", {"w": 16, "h": 16})
        e.setdefault("CptChecksPosition", {"x": 10, "y": 10})
        e.setdefault("ActionsConditions", {})
        e.setdefault("RulesOptionsLists", [])
        e.setdefault("RulesOptions", [])

    def _required_map_dimensions(self):
        """Window must be wide enough to host items + the widest map to its right
        (the tracker places maps at background.right)."""
        items_w = self.background.get_width() if self.background else self.template_size[0]
        items_h = self.background.get_height() if self.background else self.template_size[1]
        map_w = map_h = 0
        for m in self.maps:
            bg = m["assets"].get("Background")
            if bg:
                mw, mh = bg.get_size()
            else:
                dims = m["data"]["Datas"].get("Dimensions", {})
                mw, mh = dims.get("width", 0), dims.get("height", 0)
            map_w = max(map_w, mw)
            map_h = max(map_h, mh)
        return items_w + map_w, max(items_h, map_h)

    def _map_window_ok(self):
        if not (self.is_map_template and self.maps):
            return True, 0, 0
        rw, rh = self._required_map_dimensions()
        ok = self.template_size[0] >= rw and self.template_size[1] >= rh
        return ok, rw, rh

    def _fit_window_to_maps(self):
        rw, rh = self._required_map_dimensions()
        self.template_size = (max(self.template_size[0], rw), max(self.template_size[1], rh))
        self._flash_status(f"Window fit to {self.template_size[0]} x {self.template_size[1]} (room for maps).")

    def _open_map_options(self):
        if self._current_map():
            self.map_options_open = True

    def _edit_map_option(self, key):
        m = self._current_map()
        if not m:
            return
        data = m["data"]["Datas"]
        if key in ("DrawBoxRect", "DrawBoxRectSubTitle"):
            cur = data.get(key, {"x": 0, "y": 0, "w": 0, "h": 0})
            initial = f"{cur.get('x',0)},{cur.get('y',0)},{cur.get('w',0)},{cur.get('h',0)}"

            def cb(value, k=key):
                parts = [p.strip() for p in str(value).split(",")]
                if len(parts) == 4 and all(p.lstrip("-").isdigit() for p in parts):
                    data[k] = {"x": int(parts[0]), "y": int(parts[1]), "w": int(parts[2]), "h": int(parts[3])}
                    self.message = f"{k} updated."
                else:
                    self.message = "Enter x,y,w,h."
            self._open_text_prompt(key, initial, cb, label="x,y,w,h:")
        elif key == "LabelY":
            def cb(value):
                if value is not None:
                    data["LabelY"] = value
                    self.message = "Label Y updated."
            self._open_text_prompt("Label Y", int(data.get("LabelY", 0)), cb, kind="int", label="Y:")
        elif key in ("LeftArrowPos", "RightArrowPos"):
            arrow = "LeftArrow" if key == "LeftArrowPos" else "RightArrow"
            cfg = data.setdefault(arrow, {"Image": None, "Positions": {"x": 0, "y": 0}})
            pos = cfg.setdefault("Positions", {"x": 0, "y": 0})
            initial = f"{pos.get('x',0)},{pos.get('y',0)}"

            def cb(value, p=pos):
                parts = [q.strip() for q in str(value).split(",")]
                if len(parts) == 2 and all(q.lstrip("-").isdigit() for q in parts):
                    p["x"], p["y"] = int(parts[0]), int(parts[1])
                    self.message = f"{arrow} position updated."
                else:
                    self.message = "Enter x,y."
            self._open_text_prompt(f"{arrow} position", initial, cb, label="x,y:")

    def _rename_map(self, index):
        if not (0 <= index < len(self.maps)):
            return
        m = self.maps[index]

        def cb(value):
            if value:
                m["name"] = value
                m["data"]["Datas"]["Name"] = value
                self.message = f"Map renamed to {value}."
        self._open_text_prompt("Rename map", m["name"], cb, allow_empty=False, label="Map name:")

    def _save_map_assets(self, template_dir):
        # First copy every still-needed file from the source folder (map json files,
        # RulesOptions backgrounds, map_list.png, etc) that we do not regenerate.
        self._copy_remaining_map_files(template_dir)
        for m in self.maps:
            self._save_map_popup_assets(m, template_dir)
            map_data = copy.deepcopy(m["data"])
            for check in map_data.get("ChecksList", []):
                if check.get("Kind") == "MapPopup":
                    check.pop("Checks", None)
            self._strip_private_editor_fields(map_data)
            # write the map json
            with open(os.path.join(template_dir, m["json_file"]), "w", encoding="utf-8") as f:
                json.dump([map_data], f, indent=2)
            data = m["data"]["Datas"]
            self._save_one_map_asset(m, "Background", data, template_dir, fallback="bg")
            self._save_one_map_asset(m, "SubMenuBackground", data, template_dir, fallback="submenu")
            self._save_one_map_asset(m, "LeftArrow", data, template_dir, fallback="left")
            self._save_one_map_asset(m, "RightArrow", data, template_dir, fallback="right")
        self._save_extra_section_assets(template_dir)

    def _strip_private_editor_fields(self, node):
        if isinstance(node, dict):
            for key in list(node.keys()):
                if key.startswith("_"):
                    node.pop(key, None)
                else:
                    self._strip_private_editor_fields(node[key])
        elif isinstance(node, list):
            for item in node:
                self._strip_private_editor_fields(item)

    def _save_map_popup_assets(self, m, template_dir):
        for check in m["data"].get("ChecksList", []):
            assets = check.get("_popup_assets") or {}
            for asset in assets.values():
                filename = asset.get("file") or check.get("SubMenuBackground")
                if not filename:
                    continue
                dest = os.path.join(template_dir, filename)
                surface = asset.get("surface")
                if surface is not None:
                    try:
                        pygame.image.save(surface, dest)
                        continue
                    except Exception:
                        pass
                path = asset.get("path")
                if path and os.path.isfile(path):
                    try:
                        shutil.copyfile(path, dest)
                    except Exception:
                        pass

    def _save_extra_section_assets(self, template_dir):
        """Write/placeholder every image referenced by section-5 extras (maps-list
        + rules-list submenu backgrounds, arrows) so the tracker can load them."""
        refs = set()
        ml = self.maps_extra.get("MapsList")
        if ml:
            box = ml.get("MapsListBox", {})
            for key in ("LeftArrow", "RightArrow"):
                img = (box.get(key) or {}).get("Image")
                if img:
                    refs.add(("arrow", img, key))
            if box.get("SubMenuBackground"):
                refs.add(("panel", box["SubMenuBackground"], None))
        for rl in self.maps_extra.get("RulesOptionsLists", []):
            box = rl.get("ListBox", {})
            if box.get("SubMenuBackground"):
                refs.add(("panel", box["SubMenuBackground"], None))
            for key in ("LeftArrow", "RightArrow"):
                img = (box.get(key) or {}).get("Image")
                if img:
                    refs.add(("arrow", img, key))
        for kind, fname, akey in refs:
            dest = os.path.join(template_dir, fname)
            if fname in self.maps_extra_assets:
                try:
                    pygame.image.save(self.maps_extra_assets[fname], dest)
                except Exception:
                    pass
                continue
            if os.path.exists(dest):
                continue
            if kind == "arrow":
                surf = self._placeholder_map_asset("left" if "Left" in (akey or "") else "right", {})
            else:
                surf = pygame.Surface((363, 455), pygame.SRCALPHA)
                surf.fill((16, 19, 28, 235))
                pygame.draw.rect(surf, (243, 200, 106), surf.get_rect(), 2)
            try:
                pygame.image.save(surf, dest)
            except Exception:
                pass

    def _copy_remaining_map_files(self, template_dir):
        """Copy assets referenced by the preserved section 5 (RulesOptions submenu
        backgrounds, maps list background, etc) that live in the source folder."""
        src = self.map_source_dir
        if not src or not os.path.isdir(src) or os.path.abspath(src) == os.path.abspath(template_dir):
            return
        skip = {"tracker.json", "background.png", "icon.png", "illustration.png"}
        skip |= {f"{self._slugify(s['name']) or 'sheet'}.png" for s in self.sheets}
        skip |= {f.get("Name") for f in (self.fonts or {}).values() if f.get("Name")}
        for fname in os.listdir(src):
            if fname in skip:
                continue
            sp = os.path.join(src, fname)
            dp = os.path.join(template_dir, fname)
            if os.path.isfile(sp) and not os.path.exists(dp):
                try:
                    shutil.copyfile(sp, dp)
                except Exception:
                    pass

    def _save_one_map_asset(self, m, key, data, template_dir, fallback):
        if key in ("LeftArrow", "RightArrow"):
            filename = (data.get(key) or {}).get("Image")
        else:
            filename = data.get(key)
        if not filename:
            filename = f"{self._slugify(m['name']) or 'map'}_{key.lower()}.png"
            if key in ("LeftArrow", "RightArrow"):
                data.setdefault(key, {"Image": None, "Positions": {"x": 0, "y": 0}})
                data[key]["Image"] = filename
            else:
                data[key] = filename
        dest = os.path.join(template_dir, filename)
        surface = m["assets"].get(key)
        if surface is None:
            surface = self._placeholder_map_asset(fallback, data)
        try:
            pygame.image.save(surface, dest)
        except Exception:
            pass

    def _placeholder_map_asset(self, kind, data):
        w, h = self.template_size
        if kind == "bg":
            if self.background:
                return self.background
            s = pygame.Surface((w, h)); s.fill((0, 0, 0)); return s
        if kind == "submenu":
            box = data.get("DrawBoxRect", {"w": 360, "h": 450})
            s = pygame.Surface((max(1, box["w"]), max(1, box["h"])), pygame.SRCALPHA)
            s.fill((16, 19, 28, 235))
            pygame.draw.rect(s, (243, 200, 106), s.get_rect(), 2)
            return s
        a = pygame.Surface((28, 28), pygame.SRCALPHA)
        pts = [(20, 4), (20, 24), (6, 14)] if kind == "left" else [(8, 4), (8, 24), (22, 14)]
        pygame.draw.polygon(a, (238, 230, 210), pts)
        return a

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
            elif os.path.exists(os.path.join(self.core_service.get_temp_path(), "tracker", fname)):
                source = os.path.join(self.core_service.get_temp_path(), "tracker", fname)
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
                nested = self._items_from_tracker_json(item.get("ItemsList") or []) \
                    if item.get("kind") in ("SubMenuItem", "MultipleChoiceItem") else []
            for child in self._iter_all_items(nested):
                yield child
            for key in ("ActiveItems", "InactiveItems", "HintItems"):
                for child in self._iter_all_items(item.get(key) or []):
                    yield child

    def _save_submenu_backgrounds(self, template_dir, source_dir=None):
        for item in self._iter_all_items(self.main_items):
            if item.get("kind") not in ("SubMenuItem", "MultipleChoiceItem"):
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
        sections = [
            {
                "Informations": informations
            },
            {
                "Datas": {
                    "Dimensions": {"width": self.template_size[0], "height": self.template_size[1]},
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
                    for item in self._export_items_without_linked_refs(self.main_items)
                ]
            }
        ]
        if background_name:
            sections[1]["Datas"]["Background"] = background_name

        # Map template: build section 5 (Maps list + preserved extras)
        if self.is_map_template and self.maps:
            section = {"Maps": [{"Id": i, "Datas": m["json_file"]} for i, m in enumerate(self.maps)]}
            for key, value in (self.maps_extra or {}).items():
                section[key] = copy.deepcopy(value)
            sections.append(section)
        return sections

    def _export_items_without_linked_refs(self, items):
        referenced = self._referenced_item_identities(items)
        return [
            item for item in items
            if not self._item_ref_aliases(item).intersection(referenced)
        ]

    def _referenced_item_identities(self, items):
        """Identities of items embedded as Hint/Active/Inactive refs of another item.
        Those must not also appear as top-level items (the tracker spawns them from
        the parent), otherwise they are rendered twice."""
        referenced = set()

        def walk(item):
            for field in ("HintItems", "ActiveItems", "InactiveItems"):
                for ref in item.get(field) or []:
                    referenced.update(self._item_ref_aliases(ref))
                    walk(ref)
            for child in item.get("children") or []:
                walk(child)
            for sub in item.get("_submenu_items") or []:
                walk(sub)
        for it in items:
            walk(it)
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

        if kind == "ImageItem":
            data = {
                "Id": assigned_id,
                "Kind": "ImageItem",
                "Name": item["name"],
                "Positions": {"x": item["x"], "y": item["y"]},
                "Sizes": item.get("Sizes", {"w": 64, "h": 64}),
                "isActive": item.get("isActive", True),
                "Hint": item.get("hint"),
                "OpacityDisable": item.get("opacity", 0.5),
            }
            if item.get("Image"):
                data["Image"] = item.get("Image")
            else:
                data.pop("Image", None)
            if item.get("sheet"):
                data["SheetInformation"] = {
                    "row": item.get("row", 1),
                    "column": item.get("column", 1),
                    "SpriteSheet": item.get("sheet")
                }
            else:
                data.pop("SheetInformation", None)
            if item.get("visible", True) is not True:
                data["Visible"] = bool(item.get("visible"))
            else:
                data.pop("Visible", None)
            if item.get("AlwaysEnable", False):
                data["AlwaysEnable"] = True
            else:
                data.pop("AlwaysEnable", None)
            return data

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

        if kind in ("SubMenuItem", "MultipleChoiceItem"):
            submenu_items = item.get("_submenu_items")
            if submenu_items is not None:
                data["ItemsList"] = self._build_items_list_json(
                    item,
                    self._export_items_without_linked_refs(submenu_items)
                )

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

