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
            }
            item["_preview"] = st
        return st

    def _preview_overlay_text(self, screen, rect, slot, text):
        path = self._resolve_font_path((self.fonts.get(slot, {}) or {}).get("Name"))
        try:
            ptext.draw(str(text), midbottom=(rect.centerx, rect.bottom - 4), fontname=path,
                       antialias=True, owidth=1.2, ocolor=(0, 0, 0),
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
                    "AlternativeLabel": ch.get("AlternativeLabel"),
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
                    # Anchor the icon cell (top-left of the composed image) at the box centre,
                    # so it stays put regardless of label overflow.
                    icon_w = cw * scale
                    icon_h = ch * scale
                    bx = int(rect.centerx - icon_w / 2)
                    by = int(rect.centery - icon_h / 2)
                    prev_clip = screen.get_clip()
                    screen.set_clip(rect)
                    screen.blit(sized, (bx, by))
                    screen.set_clip(prev_clip)
                return
            except Exception:
                pass
        self._draw_item_preview_sim(screen, rect, item)

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
        else:
            st["active"] = not st["active"]

