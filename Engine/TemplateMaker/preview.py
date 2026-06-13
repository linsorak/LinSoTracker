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


class PreviewMixin:
    def _preview_state(self, item):
        st = item.get("_preview")
        if st is None:
            st = {
                "active": bool(item.get("isActive", False)),
                "value": int(item.get("valueStart", 0) or 0),
                "label_index": int(item.get("OffsetLabel", 0) or 0),
                "inc_index": 0,
                "evo_index": 0,
                "checked": False,
                "submenu_open": False,
            }
            item["_preview"] = st
        return st

    def _preview_overlay_text(self, screen, rect, slot, text):
        path = self._resolve_font_path((self.fonts.get(slot, {}) or {}).get("Name"))
        try:
            ptext.draw(str(text), midbottom=(rect.centerx, rect.bottom - 4), fontname=path,
                       antialias=True, owidth=0.45, ocolor=(0, 0, 0),
                       color=self._font_color(slot), fontsize=22, surf=screen)
        except Exception:
            self._text(screen, str(text), (rect.x + 4, rect.bottom - 22), 18, self._font_color(slot))

    def _preview_signature(self, item):
        return (
            item.get("kind"), item.get("sheet"), item.get("row"), item.get("column"),
            item.get("opacity"), item.get("hint"),
            tuple((c.get("sheet"), c.get("row"), c.get("column"), c.get("name"), c.get("label"))
                  for c in item.get("children", [])),
            str(item.get("check")), tuple(item.get("LabelList") or ()),
            tuple(item.get("Increment") or ()),
            item.get("valueMin"), item.get("valueMax"), item.get("valueIncrease"),
            item.get("valueStart"), item.get("maxValue"), item.get("maxValueAlternate"),
            item.get("Background"), item.get("ShowNumbersOfItemsActive"),
            item.get("ShowNumberOfCheckedItems"),
            item.get("BackgroundGlow"), item.get("Image"),
            json.dumps(item.get("_submenu_items") or item.get("ItemsList") or [], sort_keys=True, default=str),
        )

    def _zoom_cell(self, sheet, row, column):
        cell = self._get_icon_surface(row, column, sheet)
        if cell is None:
            return None
        return self.core_service.zoom_image(cell) if self.core_service else cell

    def _instantiate_item(self, item):
        kind = item.get("kind", "Item")
        if kind not in self.REAL_PREVIEW_KINDS or self.core_service is None:
            return None
        image = self._zoom_cell(item.get("sheet"), item["row"], item["column"])
        if image is None:
            return None
        base = dict(
            id=item.get("id", 0), name=item.get("name", ""), image=image,
            position=(0, 0), enable=item.get("isActive", False),
            hint=item.get("hint"), opacity_disable=item.get("opacity", 0.5),
            always_enable=False,
        )
        if kind == "CountItem":
            return CountItem(min_value=item.get("valueMin", 0), max_value=item.get("valueMax", 99),
                             value_increase=item.get("valueIncrease", 1), value_start=item.get("valueStart", 0), **base)
        if kind == "AlternateCountItem":
            return AlternateCountItem(max_value=item.get("maxValue", 10),
                                      max_value_alternate=item.get("maxValueAlternate", 10), **base)
        if kind == "IncrementalItem":
            return IncrementalItem(increments=item.get("Increment", []),
                                   start_increment_index=item.get("StartIncrementIndex"), **base)
        if kind == "LabelItem":
            return LabelItem(label_list=item.get("LabelList", [""]), label_offset=item.get("OffsetLabel", 0), **base)
        if kind in self.EVOLUTION_KINDS:
            next_items = []
            for ch in item.get("children", []):
                next_items.append({
                    "Name": ch.get("name"),
                    "Label": ch.get("label"),
                    "AlternativeLabel": ch.get("alt_label"),
                    "Image": self._zoom_cell(ch.get("sheet"), ch["row"], ch["column"]),
                })
            evo_args = dict(next_items=next_items, label=item.get("Label"),
                            label_center=item.get("LabelCenter", False),
                            alternative_label=item.get("AlternativeLabel"))
            if kind == "AlternateEvolutionItem":
                return AlternateEvolutionItem(global_label=item.get("GlobalLabel"), **evo_args, **base)
            if kind == "DraggableEvolutionItem":
                return DraggableEvolutionItem(**evo_args, **base)
            return EvolutionItem(**evo_args, **base)
        if kind == "CheckItem":
            chk = item.get("check")
            check_image = self._zoom_cell(chk.get("sheet"), chk["row"], chk["column"]) if chk \
                else self._zoom_cell(item.get("sheet"), item["row"], item["column"])
            return CheckItem(check_image=check_image, **base)
        return Item(**base)

    def _preview_component(self, item):
        sig = self._preview_signature(item)
        if item.get("_comp_sig") != sig or item.get("_component") is None:
            try:
                comp = self._with_preview_core(lambda: self._instantiate_item(item))
            except Exception:
                comp = None
            item["_component"] = comp
            item["_comp_sig"] = sig
        return item.get("_component")

    def _draw_item_preview(self, screen, rect, item):
        if item.get("kind") == "EditableBox":
            self._draw_editable_box_preview(screen, rect, item)
            return
        if item.get("kind") == "TimerItem":
            self._draw_timer_item_preview(screen, rect, item)
            return
        if item.get("kind") in ("SubMenuItem", "MultipleChoiceItem"):
            self._draw_submenu_item_preview(screen, rect, item)
            return
        if item.get("kind") == "GoModeItem":
            self._draw_gomode_item_preview(screen, rect, item)
            return
        if item.get("kind") == "ImageItem":
            self._draw_image_item_preview(screen, rect, item)
            return
        comp = self._preview_component(item)
        if comp is not None:
            try:
                self._with_preview_core(comp.update)
                img = comp.image
                if img and img.get_width() > 0 and img.get_height() > 0:
                    # Scale from the item's cell size (not the composed image) so the icon
                    # keeps the same size whether or not a label grows the surface.
                    sheet = self._sheet_by_name(item.get("sheet")) or self.active_sheet
                    cw = sheet["cell_w"] if sheet else img.get_width()
                    ch = sheet["cell_h"] if sheet else img.get_height()
                    scale = min(72 / max(1, cw), 72 / max(1, ch), 4.0)
                    sized = pygame.transform.smoothscale(
                        img, (max(1, int(img.get_width() * scale)), max(1, int(img.get_height() * scale))))
                    if item.get("kind") in ("CountItem", "AlternateCountItem", "LabelItem"):
                        visible = sized.get_bounding_rect()
                        bx = rect.centerx - visible.w // 2 - visible.x
                        by = rect.centery - visible.h // 2 - visible.y
                    else:
                        # Anchor the icon cell (top-left of the composed image) at the box centre,
                        # so it stays put regardless of label overflow.
                        icon_w = cw * scale
                        icon_h = ch * scale
                        surface_offset_x = getattr(comp, "rect", pygame.Rect(0, 0, 0, 0)).x
                        bx = int(rect.centerx - icon_w / 2 + surface_offset_x * scale)
                        by = int(rect.centery - icon_h / 2)
                    prev_clip = screen.get_clip()
                    screen.set_clip(rect)
                    screen.blit(sized, (bx, by))
                    screen.set_clip(prev_clip)
                return
            except Exception:
                pass
        self._draw_item_preview_sim(screen, rect, item)

    @staticmethod
    def _preview_color(data, fallback):
        if not isinstance(data, dict):
            return fallback
        return data.get("r", fallback[0]), data.get("g", fallback[1]), data.get("b", fallback[2])

    def _draw_editable_box_preview(self, screen, rect, item):
        sizes = item.get("Sizes") or {}
        style = item.get("Style") or {}
        src_w = max(1, int(sizes.get("w", 120)))
        src_h = max(1, int(sizes.get("h", 32)))
        box = pygame.Rect(rect.centerx - src_w // 2, rect.centery - src_h // 2 - 10, src_w, src_h)

        bg = self._preview_color(style.get("BackgroundColor"), (255, 255, 255))
        text_color = self._preview_color(style.get("NormalTextColor"), (0, 0, 0))
        selected_bg = self._preview_color(style.get("HoveredBackgroundColor"), (70, 70, 70))
        selected_text = self._preview_color(style.get("HoveredTextColor"), (255, 255, 255))
        prev_clip = screen.get_clip()
        screen.set_clip(rect.inflate(-2, -2))
        pygame.draw.rect(screen, bg, box)
        pygame.draw.rect(screen, (70, 130, 210), box, 2)

        placeholder = item.get("PlaceHolder") or item.get("name") or "EditableBox"
        font = pygame.font.Font(None, max(13, min(22, int(src_h * 0.65))))
        visible = placeholder
        max_width = box.w - 12
        while visible and font.size(visible)[0] > max_width:
            visible = visible[:-1]
        text = font.render(visible, True, text_color if item.get("PlaceHolder") else (120, 120, 120))
        screen.blit(text, (box.x + 6, box.centery - text.get_height() // 2))
        cursor_x = box.x + 8 + text.get_width()
        pygame.draw.line(screen, text_color, (cursor_x, box.y + 5), (cursor_x, box.bottom - 5), 1)

        suggestions = item.get("Lines") or []
        if suggestions:
            row_h = max(16, min(22, src_h))
            list_h = min(len(suggestions), 2) * row_h
            list_rect = pygame.Rect(box.x, box.bottom + 4, box.w, list_h)
            pygame.draw.rect(screen, bg, list_rect)
            pygame.draw.rect(screen, (30, 30, 30), list_rect, 1)
            for index, suggestion in enumerate(suggestions[:2]):
                row = pygame.Rect(list_rect.x, list_rect.y + index * row_h, list_rect.w, row_h)
                if index == 0:
                    pygame.draw.rect(screen, selected_bg, row)
                line = font.render(str(suggestion), True, selected_text if index == 0 else text_color)
                screen.blit(line, (row.x + 6, row.centery - line.get_height() // 2))
        screen.set_clip(prev_clip)
        if box.w > rect.w or box.h > rect.h:
            self._text(screen, "clipped actual size", (rect.x + 8, rect.bottom - 18), 11, self.COLORS["muted"])

    def _draw_timer_item_preview(self, screen, rect, item):
        timer = item.get("Timer") or {}
        buttons = item.get("Buttons") or {}
        timer_rect_data = timer.get("Rect", {"x": 0, "y": 0, "w": 180, "h": 42})
        rects = [pygame.Rect(timer_rect_data.get("x", 0), timer_rect_data.get("y", 0),
                             timer_rect_data.get("w", 180), timer_rect_data.get("h", 42))]
        for cfg in buttons.values():
            if isinstance(cfg, dict) and cfg.get("Enable") is not False and "Rect" in cfg:
                rd = cfg["Rect"]
                rects.append(pygame.Rect(rd.get("x", 0), rd.get("y", 0), rd.get("w", 1), rd.get("h", 1)))
        bounds = rects[0].copy()
        for r in rects[1:]:
            bounds.union_ip(r)
        origin = (rect.centerx - bounds.w // 2 - bounds.x, rect.centery - bounds.h // 2 - bounds.y)

        prev_clip = screen.get_clip()
        screen.set_clip(rect.inflate(-2, -2))
        timer_rect = pygame.Rect(origin[0] + rects[0].x, origin[1] + rects[0].y, rects[0].w, rects[0].h)
        bg_cfg = timer.get("Background", {})
        fill = self._preview_color(bg_cfg.get("Color"), (12, 15, 22))
        border = self._preview_color(bg_cfg.get("BorderColor"), self.COLORS["green"])
        pygame.draw.rect(screen, fill, timer_rect, border_radius=int(bg_cfg.get("Radius", 0)))
        pygame.draw.rect(screen, border, timer_rect, max(1, int(bg_cfg.get("BorderSize", 1))))

        font_cfg = timer.get("Font", {})
        font = pygame.font.Font(None, int(font_cfg.get("Size", 32)))
        color = self._preview_color(font_cfg.get("Color"), self.COLORS["green"])
        text = "00:00.00" if timer.get("ShowCentiseconds", True) else "00:00"
        surface = font.render(text, True, color)
        screen.blit(surface, (timer_rect.centerx - surface.get_width() // 2,
                              timer_rect.centery - surface.get_height() // 2))

        for key, cfg in buttons.items():
            if not isinstance(cfg, dict) or cfg.get("Enable") is False or "Rect" not in cfg:
                continue
            rd = cfg["Rect"]
            br = pygame.Rect(origin[0] + rd.get("x", 0), origin[1] + rd.get("y", 0),
                             rd.get("w", 80), rd.get("h", 28))
            if key == "StartPause":
                fill = self._preview_color((cfg.get("Colors") or {}).get("Start"), (35, 130, 85))
                label = (cfg.get("Labels") or {}).get("Start", "Start")
            else:
                fill = self._preview_color(cfg.get("Color"), (110, 65, 135))
                label = cfg.get("Label", "Reset")
            pygame.draw.rect(screen, fill, br, border_radius=int(cfg.get("Radius", 6)))
            pygame.draw.rect(screen, self._preview_color(cfg.get("BorderColor"), (235, 235, 235)), br, 1,
                             border_radius=int(cfg.get("Radius", 6)))
            bfont = pygame.font.Font(None, int((cfg.get("Font") or {}).get("Size", 16)))
            btext = bfont.render(label, True, self._preview_color((cfg.get("Font") or {}).get("Color"), (255, 255, 255)))
            screen.blit(btext, (br.centerx - btext.get_width() // 2, br.centery - btext.get_height() // 2))
        screen.set_clip(prev_clip)
        if bounds.w > rect.w or bounds.h > rect.h:
            self._text(screen, "clipped actual size", (rect.x + 8, rect.bottom - 18), 11, self.COLORS["muted"])

    def _draw_submenu_item_preview(self, screen, rect, item):
        st = self._preview_state(item)
        if st.get("submenu_open"):
            self._draw_submenu_open_preview(screen, rect, item)
            return

        icon = self._get_icon_surface(item["row"], item["column"], item.get("sheet"))
        if icon:
            scaled = pygame.transform.smoothscale(icon, (72, 72))
            if not item.get("isActive", False):
                scaled = scaled.copy()
                scaled.set_alpha(int(max(0.0, min(1.0, item.get("opacity", 0.5))) * 255))
        else:
            scaled = None

        counter_text = None
        if item.get("ShowNumbersOfItemsActive"):
            items = item.get("_submenu_items") or item.get("ItemsList") or []
            active = sum(1 for subitem in items if subitem.get("isActive", False))
            if item.get("ShowNumberOfCheckedItems"):
                checked = sum(1 for subitem in items
                              if subitem.get("Kind") == "CheckItem" and subitem.get("isActive", False))
                counter_text = f"{checked}/{active}"
            else:
                counter_text = f"{active}/{len(items)}"

        if scaled:
            composed = self._compose_submenu_icon_counter(scaled, counter_text)
            visible = composed.get_bounding_rect()
            if visible.w > 0 and visible.h > 0:
                cropped = composed.subsurface(visible).copy()
                prev_clip = screen.get_clip()
                screen.set_clip(rect)
                screen.blit(cropped, (rect.centerx - cropped.get_width() // 2,
                                      rect.centery - cropped.get_height() // 2))
                screen.set_clip(prev_clip)

        self._text(screen, "click to open", (rect.x + 8, rect.bottom - 18), 11, self.COLORS["muted"])

    def _compose_submenu_icon_counter(self, icon, text):
        if not text:
            return icon
        path = self._resolve_font_path((self.fonts.get("subMenuItemFont", {}) or {}).get("Name"))
        text_surface = None
        try:
            temp = pygame.Surface((240, 120), pygame.SRCALPHA)
            text_surface, _ = ptext.draw(str(text), (0, 0), fontname=path,
                                         antialias=True, owidth=0.45, ocolor=(0, 0, 0),
                                         color=self._font_color("subMenuItemFont"), fontsize=22, surf=temp)
        except Exception:
            font = pygame.font.Font(None, 22)
            text_surface = font.render(str(text), True, self._font_color("subMenuItemFont"))

        base_w, base_h = icon.get_size()
        text_w, text_h = text_surface.get_size()
        x = base_w - text_w
        y = base_h - text_h + (text_h / 4)
        width = max(1, int(base_w + text_w / 1.5))
        height = max(1, int(base_h + text_h / 1.5))
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        surface.blit(icon, (0, 0))
        surface.blit(text_surface, (int(x), int(y)))
        return surface

    def _draw_submenu_open_preview(self, screen, rect, item):
        bg = self._load_submenu_background(item.get("Background"))
        items = item.get("_submenu_items") or item.get("ItemsList") or []

        prev_clip = screen.get_clip()
        screen.set_clip(rect.inflate(-2, -2))
        pygame.draw.rect(screen, (5, 6, 9), rect)

        if bg:
            bg_w, bg_h = bg.get_size()
            scale = min(rect.w / max(1, bg_w), rect.h / max(1, bg_h))
            target = pygame.Rect(0, 0, max(1, int(bg_w * scale)), max(1, int(bg_h * scale)))
            target.center = rect.center
            screen.blit(pygame.transform.smoothscale(bg, target.size), target)
        else:
            bg_w, bg_h = self.template_size
            scale = min(rect.w / max(1, bg_w), rect.h / max(1, bg_h))
            target = pygame.Rect(rect.x + 8, rect.y + 8, rect.w - 16, rect.h - 28)
            pygame.draw.rect(screen, (15, 18, 26), target)
            pygame.draw.rect(screen, (56, 62, 76), target, 1)

        for subitem in items[:80]:
            pos = subitem.get("Positions") or {}
            sheet = (subitem.get("SheetInformation") or {}).get("SpriteSheet")
            row = (subitem.get("SheetInformation") or {}).get("row", 1)
            column = (subitem.get("SheetInformation") or {}).get("column", 1)
            icon = self._get_icon_surface(row, column, sheet)
            if not icon:
                continue
            size = max(4, int(24 * scale))
            x = target.x + int(pos.get("x", 0) * scale)
            y = target.y + int(pos.get("y", 0) * scale)
            scaled = pygame.transform.smoothscale(icon, (size, size))
            if not subitem.get("isActive", False):
                scaled = scaled.copy()
                scaled.set_alpha(120)
            screen.blit(scaled, (x, y))

        if len(items) > 80:
            self._text(screen, f"+{len(items) - 80}", (rect.right - 34, rect.bottom - 18), 11, self.COLORS["muted"])
        self._text(screen, "submenu preview", (rect.x + 8, rect.bottom - 18), 11, self.COLORS["muted"])
        screen.set_clip(prev_clip)

    def _load_submenu_background(self, name):
        if not name:
            return None
        candidates = []
        if self.project_dir:
            candidates.append(os.path.join(self.project_dir, name))
        if self.background_path:
            candidates.append(os.path.join(os.path.dirname(self.background_path), name))
        for path in candidates:
            if os.path.exists(path):
                try:
                    return pygame.image.load(path).convert_alpha()
                except Exception:
                    return None
        return None

    def _load_item_image_asset(self, item, key):
        assets = item.get("_image_assets") or {}
        asset = assets.get(key) or {}
        if asset.get("surface"):
            return asset["surface"]
        name = item.get(key)
        if not name:
            return None
        candidates = []
        if asset.get("path"):
            candidates.append(asset["path"])
        if self.project_dir:
            candidates.append(os.path.join(self.project_dir, name))
        if self.background_path:
            candidates.append(os.path.join(os.path.dirname(self.background_path), name))
        for path in candidates:
            if os.path.exists(path):
                try:
                    surface = pygame.image.load(path).convert_alpha()
                    item.setdefault("_image_assets", {})[key] = {
                        "path": path,
                        "surface": surface,
                        "file": name,
                    }
                    return surface
                except Exception:
                    return None
        return None

    def _draw_gomode_item_preview(self, screen, rect, item):
        icon = self._get_icon_surface(item["row"], item["column"], item.get("sheet"))
        glow = self._load_item_image_asset(item, "BackgroundGlow")
        if not icon:
            return

        source = pygame.Surface((max(icon.get_width(), 72), max(icon.get_height(), 72)), pygame.SRCALPHA)
        source_rect = source.get_rect()
        if glow:
            side_w = max(glow.get_width(), icon.get_width())
            side_h = max(glow.get_height(), icon.get_height())
            source = pygame.Surface((side_w, side_h), pygame.SRCALPHA)
            source_rect = source.get_rect()
            angle = (pygame.time.get_ticks() / 12) % 360
            rotated = pygame.transform.rotozoom(glow, angle, 1)
            rotated_rect = rotated.get_rect(center=source_rect.center)
            source.blit(rotated, rotated_rect)
        else:
            pygame.draw.rect(source, self.COLORS["green"], source_rect.inflate(-8, -8), 3)

        icon_rect = icon.get_rect(center=source_rect.center)
        source.blit(icon, icon_rect)
        visible = source.get_bounding_rect()
        if visible.w <= 0 or visible.h <= 0:
            return
        cropped = source.subsurface(visible).copy()
        scale = min((rect.w - 16) / cropped.get_width(), (rect.h - 16) / cropped.get_height(), 4.0)
        scaled = pygame.transform.smoothscale(
            cropped,
            (max(1, int(cropped.get_width() * scale)), max(1, int(cropped.get_height() * scale)))
        )
        prev_clip = screen.get_clip()
        screen.set_clip(rect)
        screen.blit(scaled, (rect.centerx - scaled.get_width() // 2, rect.centery - scaled.get_height() // 2))
        screen.set_clip(prev_clip)
        if not glow:
            self._text(screen, "missing glow", (rect.x + 8, rect.bottom - 18), 11, self.COLORS["muted"])

    def _draw_image_item_preview(self, screen, rect, item):
        image = self._load_item_image_asset(item, "Image")
        source_label = None
        if not image:
            image = self._get_icon_surface(item.get("row", 1), item.get("column", 1), item.get("sheet")) \
                if item.get("sheet") else None
            source_label = "spritesheet" if image else None
        if not image:
            self._text_center(screen, "No image / sprite", rect, 15, self.COLORS["muted"])
            return
        scale = min(rect.w / max(1, image.get_width()), rect.h / max(1, image.get_height()), 1.0)
        size = (max(1, int(image.get_width() * scale)), max(1, int(image.get_height() * scale)))
        scaled = pygame.transform.smoothscale(image, size) if size != image.get_size() else image
        screen.blit(scaled, (rect.centerx - size[0] // 2, rect.centery - size[1] // 2))
        if source_label:
            self._text(screen, source_label, (rect.x + 8, rect.bottom - 18), 11, self.COLORS["muted"])

    def _advance_preview(self, item):
        self._preview_action(item, "left")

    def _preview_action(self, item, action):
        """action: left / right / wheel_up / wheel_down / wheel_click"""
        if not item:
            return
        comp = self._preview_component(item)
        method = {
            "left": "left_click",
            "right": "right_click",
            "wheel_up": "wheel_up",
            "wheel_down": "wheel_down",
            "wheel_click": "wheel_click",
        }.get(action)
        if comp is not None and method and hasattr(comp, method):
            try:
                self._with_preview_core(getattr(comp, method))
                return
            except Exception:
                pass
        # Simulation fallback only handles left/right as a state advance
        if action in ("left", "right"):
            self._advance_preview_sim(item)

    def _draw_item_preview_sim(self, screen, rect, item):
        kind = item.get("kind", "Item")
        st = self._preview_state(item)
        children = item.get("children", [])

        # Determine which sprite + whether the item reads as "on"
        spr = (item.get("sheet"), item["row"], item["column"])
        if kind in self.EVOLUTION_KINDS and st["evo_index"] > 0 and st["evo_index"] <= len(children):
            ch = children[st["evo_index"] - 1]
            spr = (ch.get("sheet"), ch["row"], ch["column"])
        if kind in ("CountItem", "AlternateCountItem"):
            is_on = st["value"] > 0
        elif kind == "LabelItem":
            is_on = st["label_index"] > 0
        elif kind in self.EVOLUTION_KINDS:
            is_on = st["evo_index"] > 0
        elif kind == "CheckItem":
            is_on = st["checked"]
        else:
            is_on = st["active"]

        icon = self._get_icon_surface(spr[1], spr[2], spr[0])
        if icon:
            scaled = pygame.transform.smoothscale(icon, (72, 72))
            if not is_on:
                scaled = scaled.copy()
                scaled.set_alpha(int(max(0.0, min(1.0, item.get("opacity", 0.5))) * 255))
            screen.blit(scaled, (rect.centerx - 36, rect.centery - 36))

        # GoMode glow ring
        if kind == "GoModeItem" and is_on:
            pygame.draw.rect(screen, self.COLORS["green"], rect.inflate(-6, -6), 3)

        # Overlays per kind
        if kind in ("CountItem", "AlternateCountItem"):
            self._preview_overlay_text(screen, rect, "countItemFont", st["value"])
        elif kind == "LabelItem":
            labels = item.get("LabelList") or [""]
            idx = st["label_index"] % len(labels)
            if labels[idx]:
                self._preview_overlay_text(screen, rect, "labelItemFont", labels[idx])
        elif kind == "IncrementalItem":
            incs = item.get("Increment") or []
            if incs and is_on:
                self._preview_overlay_text(screen, rect, "incrementalItemFont", incs[st["inc_index"] % len(incs)])
        elif kind == "CheckItem" and st["checked"]:
            chk = item.get("check")
            chimg = self._get_icon_surface(chk["row"], chk["column"], chk.get("sheet")) if chk else None
            if chimg:
                screen.blit(pygame.transform.smoothscale(chimg, (36, 36)), (rect.right - 40, rect.bottom - 40))
            else:
                pygame.draw.line(screen, self.COLORS["green"], (rect.x + 10, rect.centery), (rect.centerx - 4, rect.bottom - 12), 4)
                pygame.draw.line(screen, self.COLORS["green"], (rect.centerx - 4, rect.bottom - 12), (rect.right - 10, rect.y + 12), 4)

    def _advance_preview_sim(self, item):
        if not item:
            return
        kind = item.get("kind", "Item")
        st = self._preview_state(item)
        if kind in ("CountItem", "AlternateCountItem"):
            inc = int(item.get("valueIncrease", 1) or 1)
            vmax = int(item.get("valueMax", item.get("maxValue", 99)) or 99)
            vmin = int(item.get("valueMin", 0) or 0)
            st["value"] = vmin if st["value"] + inc > vmax else st["value"] + inc
        elif kind == "LabelItem":
            labels = item.get("LabelList") or [""]
            st["label_index"] = (st["label_index"] + 1) % len(labels)
        elif kind == "IncrementalItem":
            incs = item.get("Increment") or []
            st["inc_index"] = (st["inc_index"] + 1) % (len(incs) or 1)
            st["active"] = True
        elif kind in self.EVOLUTION_KINDS:
            st["evo_index"] = (st["evo_index"] + 1) % (len(item.get("children", [])) + 1)
        elif kind == "CheckItem":
            st["checked"] = not st["checked"]
        elif kind == "SubMenuItem":
            st["submenu_open"] = not st.get("submenu_open", False)
        else:
            st["active"] = not st["active"]

