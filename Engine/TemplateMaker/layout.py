import copy
import json
import os
import re
import shutil
from tkinter import filedialog, messagebox, simpledialog
from zipfile import ZipFile

import pygame
import pygame.gfxdraw

from Tools import ptext


class LayoutMixin:
    def draw(self, screen, time_delta=0):
        self._ensure_error_popup_state()
        width, height = screen.get_size()
        self._scrollbars = {}
        self._layout(width, height)
        self._draw_background(screen, width, height)
        if self.mode == "start":
            self._draw_start_screen(screen)
        else:
            self._draw_toolbar(screen)
            self._draw_left_panel(screen)
            self._draw_canvas(screen)
            self._draw_right_panel(screen)
        self._draw_status(screen)
        if self.item_modal_open and self.position_pick_mode:
            self._draw_position_pick(screen)
        elif self.item_modal_open:
            self._draw_item_modal(screen)
        if self.field_editor_open and not self.item_modal_open:
            self._draw_field_editor(screen, screen.get_rect())
        if self.fonts_modal_open:
            self._draw_fonts_modal(screen)
        if self.sprite_picker_open:
            self._draw_sprite_picker(screen)
        if self.color_picker_open:
            self._draw_color_picker(screen)
        if self.map_options_open:
            self._draw_map_options_modal(screen)
        if self.check_modal_open:
            self._draw_check_modal(screen)
        if self.map_data_open:
            self._draw_map_data_modal(screen)
        if self.actions_editor_open:
            self._draw_actions_editor(screen)
        if self.hide_editor_open:
            self._draw_hide_editor(screen)
        if self.cond_builder_open:
            self._draw_cond_builder(screen)
        if self.name_picker_open:
            self._draw_name_picker(screen)
        if self.context_menu_open:
            self._draw_context_menu(screen)
        if self.prompt_open:
            self._draw_text_prompt(screen)
        if self.error_popup_open:
            self._draw_error_popup(screen)

    def _layout(self, width, height):
        toolbar_h = 86
        margin = 20
        left_w = min(330, max(260, int(width * 0.24)))
        right_w = min(300, max(240, int(width * 0.22)))
        top = toolbar_h + margin
        body_h = height - toolbar_h - margin * 2 - 34
        self.left_panel_rect = pygame.Rect(margin, top, left_w, body_h)
        self.right_panel_rect = pygame.Rect(width - right_w - margin, top, right_w, body_h)
        canvas_x = self.left_panel_rect.right + margin
        self.canvas_rect = pygame.Rect(canvas_x, top, self.right_panel_rect.x - margin - canvas_x, body_h)

        x = margin
        y = 18
        button_h = 46
        if self.canvas_context == "submenu":
            labels = [
                ("back", "Back to template"),
            ]
        else:
            labels = [
                ("back", "Back"),
                ("background", "Load background"),
                ("save", "Save devtemplate"),
                ("saveas", "Save as"),
                ("saveto", "Save to..."),
                ("export", "Export .template"),
                ("renumber", "Fix IDs"),
            ]
        self.buttons = {}
        for key, label in labels:
            button_w = max(118, 26 + len(label) * 9)
            self.buttons[key] = pygame.Rect(x, y, button_w, button_h)
            x += button_w + 12

    def _draw_toolbar(self, screen):
        toolbar = pygame.Rect(0, 0, screen.get_width(), 86)
        self._draw_card(screen, toolbar, (12, 14, 20), border_color=(80, 72, 52), radius=0)
        for key, rect in self.buttons.items():
            color = (70, 74, 86)
            self._draw_button(screen, rect, self._button_label(key), color, hover=(key == self.hover_key))

        title_x = screen.get_width() - 330
        self._text(screen, "Template Maker", (title_x, 16), 30, self.COLORS["gold"])
        subtitle = self.project_name or "visual template layout test"
        self._text(screen, subtitle, (title_x + 3, 49), 15, self.COLORS["muted"])

    def _button_label(self, key):
        if key == "back" and self.canvas_context == "submenu":
            return "Back to template"
        return {
            "back": "Back",
            "background": "Load background",
            "box": "Add box",
            "timer": "Add timer",
            "save": "Save devtemplate",
            "saveas": "Save as",
            "saveto": "Save to...",
            "export": "Export .template",
            "renumber": "Fix IDs",
        }[key]

    def _draw_canvas(self, screen):
        self._draw_card(screen, self.canvas_rect, self.COLORS["panel"], radius=14)
        title_rect = pygame.Rect(self.canvas_rect.x + 18, self.canvas_rect.y + 12, self.canvas_rect.w - 36, 28)
        canvas_size = self._canvas_size()
        map_view = self._map_view_active()
        self.map_visibility_buttons = {}
        if map_view:
            title = f"Map: {self._current_map()['name']}"
        elif self.canvas_context == "submenu":
            title = "Choices canvas" if (self.submenu_parent or {}).get("kind") == "MultipleChoiceItem" else "Submenu canvas"
        else:
            title = "Canvas"
        self._text(screen, title, title_rect.topleft, 24, self.COLORS["gold"])
        self._text(screen, f"{canvas_size[0]} x {canvas_size[1]}", (title_rect.right - 120, title_rect.y + 5), 16, self.COLORS["muted"])

        # "See links" + "Snap" checkboxes, below the title (item canvases only, not map view)
        if map_view:
            self.see_links_rect = pygame.Rect(0, 0, 1, 1)
            self.snap_rect = pygame.Rect(0, 0, 1, 1)
            self.grid_rect = pygame.Rect(0, 0, 1, 1)
            check_count = len(self._current_map()["data"].get("ChecksList", []))
            filter_width = 88
            filter_y = title_rect.y + 28
            checks_filter = pygame.Rect(
                title_rect.right - filter_width, filter_y, filter_width, 20)
            blocks_filter = pygame.Rect(
                checks_filter.x - filter_width - 6,
                filter_y,
                filter_width,
                20,
            )
            self.map_visibility_buttons = {
                "blocks": blocks_filter,
                "checks": checks_filter,
            }
            self._draw_button(
                screen,
                blocks_filter,
                f"Blocks {'ON' if self.show_map_blocks else 'OFF'}",
                (36, 124, 87) if self.show_map_blocks else (70, 74, 86),
            )
            self._draw_button(
                screen,
                checks_filter,
                f"Checks {'ON' if self.show_map_checks else 'OFF'}",
                (36, 124, 87) if self.show_map_checks else (70, 74, 86),
            )
            status = f"{check_count} check(s) - click map to add"
            status = self._truncate_text_to_width(
                status, max(80, blocks_filter.x - title_rect.x - 10), 13)
            self._text(
                screen,
                status,
                (title_rect.x, title_rect.y + 32),
                13,
                self.COLORS["muted"],
            )
        else:
            box = pygame.Rect(title_rect.x, title_rect.y + 30, 18, 18)
            self.see_links_rect = pygame.Rect(box.x, box.y, 110, 20)
            pygame.draw.rect(screen, (20, 24, 34), box)
            pygame.draw.rect(screen, self.COLORS["gold"] if self.show_links else (56, 62, 76), box, 2)
            if self.show_links:
                pygame.draw.line(screen, self.COLORS["green"], (box.x + 3, box.centery), (box.centerx - 1, box.bottom - 4), 2)
                pygame.draw.line(screen, self.COLORS["green"], (box.centerx - 1, box.bottom - 4), (box.right - 3, box.y + 3), 2)
            self._text(screen, "See links", (box.right + 6, box.y + 1), 14,
                       self.COLORS["line_light"] if self.show_links else self.COLORS["muted"])
            sbox = pygame.Rect(box.right + 96, box.y, 18, 18)
            self.snap_rect = pygame.Rect(sbox.x, sbox.y, 90, 20)
            pygame.draw.rect(screen, (20, 24, 34), sbox)
            pygame.draw.rect(screen, self.COLORS["gold"] if self.snap_enabled else (56, 62, 76), sbox, 2)
            if self.snap_enabled:
                pygame.draw.line(screen, self.COLORS["green"], (sbox.x + 3, sbox.centery), (sbox.centerx - 1, sbox.bottom - 4), 2)
                pygame.draw.line(screen, self.COLORS["green"], (sbox.centerx - 1, sbox.bottom - 4), (sbox.right - 3, sbox.y + 3), 2)
            self._text(screen, "Snap items", (sbox.right + 6, sbox.y + 1), 14,
                       self.COLORS["line_light"] if self.snap_enabled else self.COLORS["muted"])
            gbox = pygame.Rect(sbox.right + 96, box.y, 18, 18)
            self.grid_rect = pygame.Rect(gbox.x, gbox.y, 60, 20)
            pygame.draw.rect(screen, (20, 24, 34), gbox)
            pygame.draw.rect(screen, self.COLORS["gold"] if self.grid_shown else (56, 62, 76), gbox, 2)
            if self.grid_shown:
                pygame.draw.line(screen, self.COLORS["green"], (gbox.x + 3, gbox.centery), (gbox.centerx - 1, gbox.bottom - 4), 2)
                pygame.draw.line(screen, self.COLORS["green"], (gbox.centerx - 1, gbox.bottom - 4), (gbox.right - 3, gbox.y + 3), 2)
            self._text(screen, "Grid", (gbox.right + 6, gbox.y + 1), 14,
                       self.COLORS["line_light"] if self.grid_shown else self.COLORS["muted"])

        title_h = 60
        margin = 18
        inner = pygame.Rect(
            self.canvas_rect.x + margin,
            self.canvas_rect.y + title_h,
            self.canvas_rect.w - margin * 2,
            self.canvas_rect.h - title_h - margin,
        )
        # Map view supports zoom + pan for precise check placement
        if map_view:
            fit = self._get_template_rect(inner)
            zw = max(1, int(fit.w * self.map_zoom))
            zh = max(1, int(fit.h * self.map_zoom))
            bg_rect = pygame.Rect(inner.centerx + self.map_pan[0] - zw // 2,
                                  inner.centery + self.map_pan[1] - zh // 2, zw, zh)
            self.map_view_rect = inner
            clip_rect = inner
        elif self.canvas_context == "main":
            fit = self._get_template_rect(inner)
            zoom = max(0.2, float(getattr(self, "canvas_zoom", 1.0)))
            zw = max(1, int(fit.w * zoom))
            zh = max(1, int(fit.h * zoom))
            bg_rect = pygame.Rect(inner.centerx + self.canvas_pan[0] - zw // 2,
                                  inner.centery + self.canvas_pan[1] - zh // 2, zw, zh)
            self.canvas_view_rect = inner
            clip_rect = inner
        else:
            bg_rect = self._get_template_rect(inner)
            self.canvas_view_rect = pygame.Rect(0, 0, 1, 1)
            clip_rect = bg_rect
        self.last_bg_rect = bg_rect
        bg_color = self._canvas_background_color()
        prev_clip = screen.get_clip()
        screen.set_clip(clip_rect)
        pygame.draw.rect(screen, (bg_color.get("r", 0), bg_color.get("g", 0), bg_color.get("b", 0)), bg_rect)
        background = self._canvas_background_surface()
        if background:
            if map_view:
                self._draw_cached_map_background(
                    screen, background, bg_rect, clip_rect)
            else:
                scale = bg_rect.w / canvas_size[0]
                bg_pos = self._canvas_background_position()
                bg_w = max(1, int(background.get_width() * scale))
                bg_h = max(1, int(background.get_height() * scale))
                scaled = pygame.transform.smoothscale(background, (bg_w, bg_h))
                screen.blit(scaled, (
                    bg_rect.x + int(bg_pos.get("x", 0) * scale),
                    bg_rect.y + int(bg_pos.get("y", 0) * scale),
                ))
        screen.set_clip(prev_clip)

        # Grid overlay (item canvas) - enables grid snapping
        if not map_view and self.grid_shown and self.snap_size > 0:
            scale = bg_rect.w / canvas_size[0]
            step = max(4, int(self.snap_size * scale))
            prev = screen.get_clip()
            screen.set_clip(clip_rect)
            for gx in range(bg_rect.x, bg_rect.right, step):
                pygame.draw.line(screen, (60, 66, 82), (gx, bg_rect.y), (gx, bg_rect.bottom), 1)
            for gy in range(bg_rect.y, bg_rect.bottom, step):
                pygame.draw.line(screen, (60, 66, 82), (bg_rect.x, gy), (bg_rect.right, gy), 1)
            screen.set_clip(prev)

        pygame.draw.rect(screen, self.COLORS["line_light"], clip_rect, 2)

        # Map view: draw the checks markers (click map to add, drag to move) + zoom hint
        if map_view:
            self._draw_map_checks(screen, bg_rect, canvas_size)
            self._text(screen, f"Zoom {self.map_zoom:.1f}x  (wheel=zoom, drag empty=pan)",
                       (inner.right - 290, inner.y + 4), 13, self.COLORS["muted"])
            return
        if self.canvas_context == "main":
            self._text(screen, f"Zoom {self.canvas_zoom:.1f}x  (wheel=zoom, drag empty=pan)",
                       (inner.right - 310, inner.y + 4), 13, self.COLORS["muted"])

        # Clip items to the template so off-canvas items (e.g. invisible helpers) don't spill out
        item_clip = bg_rect.clip(clip_rect)
        prev_clip = screen.get_clip()
        screen.set_clip(item_clip)
        self.linked_item_targets = []
        hidden = self._linked_identities()
        for index, item in enumerate(self.placed_items):
            # Items owned as Hint/Active/Inactive refs are drawn by their parent, not standalone
            if self._item_ref_aliases(item).intersection(hidden):
                item["screen_rect"] = pygame.Rect(0, 0, 0, 0)
                continue
            rect = self._draw_item(screen, item, index, bg_rect)
            if not rect.colliderect(item_clip):
                item["screen_rect"] = pygame.Rect(0, 0, 0, 0)
                self._draw_linked_items(screen, item, bg_rect, parent_path=(index,), parent_rect=rect)
                continue
            item["screen_rect"] = rect.clip(item_clip)
            selected_indices = getattr(self, "selected_item_indices", set()) or set()
            if index in selected_indices:
                pygame.draw.rect(screen, self.COLORS["gold"], rect.inflate(8, 8), 2)
            if index == self.selected_item_index:
                pygame.draw.rect(screen, self.COLORS["gold"], rect.inflate(12, 12), 3)
            self._draw_linked_items(screen, item, bg_rect, parent_path=(index,), parent_rect=rect)
        # Alignment guides while dragging with snap on
        dragging = self.dragging_item_index is not None or self.dragging_linked_path is not None
        if dragging and self.snap_guides:
            scale = bg_rect.w / canvas_size[0]
            for orient, coord in self.snap_guides:
                if orient == "v":
                    sx = bg_rect.x + int(coord * scale)
                    pygame.draw.line(screen, self.COLORS["gold"], (sx, bg_rect.y), (sx, bg_rect.bottom), 1)
                else:
                    sy = bg_rect.y + int(coord * scale)
                    pygame.draw.line(screen, self.COLORS["gold"], (bg_rect.x, sy), (bg_rect.right, sy), 1)
        screen.set_clip(prev_clip)

    def _draw_map_options_modal(self, screen):
        m = self._current_map()
        if not m:
            self.map_options_open = False
            return
        data = m["data"]["Datas"]
        sw, sh = screen.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        screen.blit(overlay, (0, 0))
        modal = pygame.Rect(sw // 2 - 440, sh // 2 - 280, 880, 560)
        self._draw_popup(screen, modal, radius=12)
        self.map_options_buttons = {}
        x = modal.x + 20
        y = modal.y + 16
        self._text(screen, f"Map options - {m['name']}", (x, y), 22, self.COLORS["gold"])
        y += 36

        # Left column: image imports + numeric options
        colw = 380
        for key, label in (("Background", "Map image"), ("SubMenuBackground", "Submenu image"),
                           ("LeftArrow", "Left arrow"), ("RightArrow", "Right arrow")):
            thumb_box = pygame.Rect(x, y, 40, 34)
            btn = pygame.Rect(thumb_box.right + 8, y, colw - 48, 34)
            self.map_options_buttons[f"mapimg_{key}"] = btn
            surf = m["assets"].get(key)
            pygame.draw.rect(screen, (10, 12, 18), thumb_box)
            pygame.draw.rect(screen, (56, 62, 76), thumb_box, 1)
            if surf:
                iw, ih = surf.get_size()
                s = min(36 / iw, 30 / ih)
                tw, th = max(1, int(iw * s)), max(1, int(ih * s))
                screen.blit(pygame.transform.smoothscale(surf, (tw, th)),
                            (thumb_box.centerx - tw // 2, thumb_box.centery - th // 2))
            self._draw_button(screen, btn, f"{label}: {'set' if surf else 'import'}",
                              (36, 124, 87) if surf else (70, 74, 86), hover=(self.hover_modal_key == f"mapimg_{key}"))
            y += 40

        def opt_row(label, key, value):
            row = pygame.Rect(x, y, colw, 32)
            self._draw_card(screen, row, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=6)
            self.map_options_buttons[f"opt_{key}"] = row
            self._text(screen, label, (row.x + 8, row.y + 8), 13, self.COLORS["gold"])
            self._text(screen, str(value), (row.x + 170, row.y + 8), 13, self.COLORS["line_light"])
            return row

        box = data.get("DrawBoxRect", {})
        sub = data.get("DrawBoxRectSubTitle", {})
        la = (data.get("LeftArrow") or {}).get("Positions", {})
        ra = (data.get("RightArrow") or {}).get("Positions", {})
        opt_row("Checks box (x,y,w,h)", "DrawBoxRect", f"{box.get('x',0)},{box.get('y',0)},{box.get('w',0)},{box.get('h',0)}"); y += 36
        opt_row("Subtitle box", "DrawBoxRectSubTitle", f"{sub.get('x',0)},{sub.get('y',0)},{sub.get('w',0)},{sub.get('h',0)}"); y += 36
        opt_row("Label Y", "LabelY", data.get("LabelY", 0)); y += 36
        opt_row("Left arrow pos", "LeftArrowPos", f"{la.get('x',0)},{la.get('y',0)}"); y += 36
        opt_row("Right arrow pos", "RightArrowPos", f"{ra.get('x',0)},{ra.get('y',0)}"); y += 36

        # Right column: live preview of the map with the boxes overlaid
        pv = pygame.Rect(modal.x + colw + 40, modal.y + 56, modal.right - (modal.x + colw + 40) - 20, 420)
        pygame.draw.rect(screen, (8, 9, 13), pv)
        pygame.draw.rect(screen, (56, 62, 76), pv, 1)
        self._text(screen, "PREVIEW", (pv.x + 6, pv.y - 18), 12, self.COLORS["muted"])
        bg = m["assets"].get("Background")
        if bg:
            iw, ih = bg.get_size()
            s = min((pv.w - 8) / iw, (pv.h - 8) / ih)
            dw, dh = max(1, int(iw * s)), max(1, int(ih * s))
            ox = pv.x + (pv.w - dw) // 2
            oy = pv.y + (pv.h - dh) // 2
            screen.blit(pygame.transform.smoothscale(bg, (dw, dh)), (ox, oy))

            def to_pv(px, py):
                return ox + int(px * s), oy + int(py * s)
            if box:
                r = pygame.Rect(*to_pv(box.get("x", 0), box.get("y", 0)),
                                int(box.get("w", 0) * s), int(box.get("h", 0) * s))
                pygame.draw.rect(screen, self.COLORS["gold"], r, 2)
            sb = m["assets"].get("SubMenuBackground")
            if sb and box:
                sbw, sbh = max(1, int(box.get("w", 1) * s)), max(1, int(box.get("h", 1) * s))
                screen.blit(pygame.transform.smoothscale(sb, (sbw, sbh)), to_pv(box.get("x", 0), box.get("y", 0)))
                r = pygame.Rect(*to_pv(box.get("x", 0), box.get("y", 0)), sbw, sbh)
                pygame.draw.rect(screen, self.COLORS["gold"], r, 2)
            for arrow, pos in (("LeftArrow", la), ("RightArrow", ra)):
                if pos:
                    ax, ay = to_pv(pos.get("x", 0), pos.get("y", 0))
                    asurf = m["assets"].get(arrow)
                    if asurf:
                        aw = max(6, int(asurf.get_width() * s)); ah = max(6, int(asurf.get_height() * s))
                        screen.blit(pygame.transform.smoothscale(asurf, (aw, ah)), (ax, ay))
                    else:
                        pygame.draw.circle(screen, self.COLORS["green"], (ax, ay), 5)
        else:
            self._text_center(screen, "Import a map image", pv, 16, self.COLORS["muted"])

        # Window-size warning + Fit button (maps render right of the items)
        wok, rw, rh = self._map_window_ok()
        if not wok:
            warn = pygame.Rect(modal.x + 20, modal.bottom - 86, colw, 34)
            pygame.draw.rect(screen, (60, 40, 20), warn)
            pygame.draw.rect(screen, (200, 140, 60), warn, 1)
            self._text(screen, f"Window too small - need {rw}x{rh}", (warn.x + 8, warn.y + 4), 12, (255, 200, 120))
            self._text(screen, f"have {self.template_size[0]}x{self.template_size[1]}", (warn.x + 8, warn.y + 18), 11, self.COLORS["muted"])
            fit_btn = pygame.Rect(warn.right - 64, warn.y + 6, 56, 22)
            self.map_options_buttons["fit_window"] = fit_btn
            self._draw_button(screen, fit_btn, "Fit", (36, 124, 87), hover=(self.hover_modal_key == "fit_window"))

        close_btn = pygame.Rect(modal.right - 120, modal.bottom - 44, 100, 30)
        self.map_options_buttons["close"] = close_btn
        self._draw_button(screen, close_btn, "Close", (36, 124, 87), hover=(self.hover_modal_key == "close"))

    def _draw_check_modal(self, screen):
        check = self._selected_check()
        if not check:
            self.check_modal_open = False
            return
        sw, sh = screen.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))
        modal_h = min(760, sh - 80)
        modal = pygame.Rect(sw // 2 - 260, (sh - modal_h) // 2, 520, modal_h)
        self._draw_popup(screen, modal, radius=12)
        self.check_modal_buttons = {}
        self.check_subrows = {}
        self.popup_item_rows = {}
        x = modal.x + 20
        y = modal.y + 16
        is_block = check.get("Kind") == "Block"
        is_popup = check.get("Kind") == "MapPopup"
        self._text(screen, f"Edit {check.get('Kind')}  (#{check.get('Id')})", (x, y), 22, self.COLORS["gold"])
        y += 36

        def field_row(label, key, value):
            row = pygame.Rect(x, y, modal.w - 40, 38)
            self._draw_card(screen, row, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
            self.check_modal_buttons[f"field_{key}"] = row
            self._text(screen, label.upper(), (row.x + 10, row.y + 4), 11, self.COLORS["gold"])
            disp = str(value) if value not in (None, "") else "click to edit"
            self._text(screen, disp[:54], (row.x + 10, row.y + 18), 14, self.COLORS["line_light"])

        field_row("Name", "Name", check.get("Name"))
        y += 44
        field_row("Zone", "Zone", check.get("Zone"))
        y += 44

        # Kind toggle
        kind_btn = pygame.Rect(x, y, modal.w - 40, 32)
        self.check_modal_buttons["toggle_kind"] = kind_btn
        self._draw_button(screen, kind_btn, f"Kind: {check.get('Kind')}  (click to switch)",
                          (70, 74, 86), hover=(self.hover_modal_key == "toggle_kind"))
        y += 40

        if is_popup:
            field_row("Popup image", "SubMenuBackground", check.get("SubMenuBackground", ""))
            y += 44
            field_row("Visible condition", "VisibleCondition", check.get("VisibleCondition", "True"))
            y += 44

        if not (is_block or is_popup):
            field_row("Group", "Group", check.get("Group"))
            y += 44
            field_row("Item count", "ItemCount", check.get("ItemCount", 1))
            y += 44
            field_row("Logic condition (green)", "Conditions", check.get("Conditions"))
            y += 44
            field_row("Out-of-logic condition (yellow)", "OutOfLogicConditions",
                      check.get("OutOfLogicConditions"))
            y += 44
            field_row("Scoutable condition (blue)", "ScoutableConditions",
                      check.get("ScoutableConditions"))
            y += 44
            field_row("Uncertain condition (purple)", "UncertainConditions",
                      check.get("UncertainConditions"))
            y += 44
        elif is_block:
            self._text(screen, "SUB-CHECKS", (x, y), 12, self.COLORS["gold"])
            add_btn = pygame.Rect(modal.right - 50, y - 4, 30, 24)
            self.check_modal_buttons["add_sub"] = add_btn
            self._draw_button(screen, add_btn, "+", (36, 124, 87), hover=(self.hover_modal_key == "add_sub"))
            y += 22
            list_area = pygame.Rect(x, y, modal.w - 40, max(70, modal.bottom - y - 60))
            self._draw_card(screen, list_area, (10, 12, 18), border_color=(56, 62, 76), radius=8)
            ry = list_area.y + 4
            prev_clip = screen.get_clip()
            screen.set_clip(list_area)
            subchecks = check.get("Checks", [])
            max_rows = max(1, (list_area.h - 8) // 30)
            self.check_sub_visible_rows = max_rows
            self.check_sub_scroll = max(
                0, min(self.check_sub_scroll, max(0, len(subchecks) - max_rows)))
            for si in range(self.check_sub_scroll, min(len(subchecks), self.check_sub_scroll + max_rows)):
                sub = subchecks[si]
                nrow = pygame.Rect(list_area.x + 4, ry, 90, 26)
                count_row = pygame.Rect(nrow.right + 4, ry, 40, 26)
                group_row = pygame.Rect(count_row.right + 4, ry, 68, 26)
                del_btn = pygame.Rect(list_area.right - 26, ry, 22, 26)
                down_btn = pygame.Rect(del_btn.x - 24, ry, 20, 26)
                up_btn = pygame.Rect(down_btn.x - 22, ry, 20, 26)
                condition_specs = (
                    ("Conditions", "L", (38, 116, 58)),
                    ("OutOfLogicConditions", "O", (154, 126, 32)),
                    ("ScoutableConditions", "S", (42, 91, 166)),
                    ("UncertainConditions", "U", (118, 63, 151)),
                )
                condition_x = group_row.right + 4
                condition_space = up_btn.x - 4 - condition_x
                condition_w = max(24, (condition_space - 9) // 4)
                condition_rows = {}
                for condition_index, (field, short_label, active_color) in enumerate(condition_specs):
                    condition_row = pygame.Rect(
                        condition_x + condition_index * (condition_w + 3), ry,
                        condition_w, 26)
                    condition_rows[field] = (condition_row, short_label, active_color)

                self.check_subrows[(si, "Name")] = nrow
                self.check_subrows[(si, "ItemCount")] = count_row
                self.check_subrows[(si, "Group")] = group_row
                for field, (condition_row, _short_label, _active_color) in condition_rows.items():
                    self.check_subrows[(si, field)] = condition_row
                self.check_subrows[(si, "up")] = up_btn
                self.check_subrows[(si, "down")] = down_btn
                self.check_subrows[(si, "del")] = del_btn
                pygame.draw.rect(screen, self.COLORS["panel_alt"], nrow)
                pygame.draw.rect(screen, self.COLORS["panel_alt"], count_row)
                pygame.draw.rect(screen, self.COLORS["panel_alt"], group_row)
                self._text(screen, str(sub.get("Name", ""))[:12], (nrow.x + 4, nrow.y + 5), 12, self.COLORS["line_light"])
                self._text(screen, f"x{sub.get('ItemCount', 1)}", (count_row.x + 4, count_row.y + 5), 11, self.COLORS["gold"])
                self._text(screen, str(sub.get("Group", ""))[:8] or "group", (group_row.x + 4, group_row.y + 5), 10, self.COLORS["muted"])
                for field, (condition_row, short_label, active_color) in condition_rows.items():
                    active = bool(sub.get(field))
                    pygame.draw.rect(
                        screen, active_color if active else self.COLORS["panel_alt"],
                        condition_row)
                    self._text(
                        screen, short_label, (condition_row.x + 5, condition_row.y + 5),
                        11, self.COLORS["line_light"] if active else self.COLORS["muted"])
                up_enabled = si > 0
                down_enabled = si < len(subchecks) - 1
                pygame.draw.rect(screen, (70, 74, 86) if up_enabled else (35, 38, 46), up_btn)
                pygame.draw.rect(screen, (70, 74, 86) if down_enabled else (35, 38, 46), down_btn)
                self._text_center(
                    screen, "^", up_btn, 13,
                    self.COLORS["line_light"] if up_enabled else self.COLORS["muted"])
                self._text_center(
                    screen, "v", down_btn, 13,
                    self.COLORS["line_light"] if down_enabled else self.COLORS["muted"])
                pygame.draw.rect(screen, self.COLORS["red"], del_btn)
                self._text(screen, "x", (del_btn.x + 7, del_btn.y + 4), 14, self.COLORS["line_light"])
                ry += 30
            screen.set_clip(prev_clip)
            y = list_area.bottom + 10

        if is_popup:
            self._text(screen, "POPUP ITEMS", (x, y), 12, self.COLORS["gold"])
            add_item_btn = pygame.Rect(modal.right - 50, y - 4, 30, 24)
            self.check_modal_buttons["add_popup_item"] = add_item_btn
            self._draw_button(screen, add_item_btn, "+", (36, 124, 87),
                              hover=(self.hover_modal_key == "add_popup_item"))
            y += 22
            item_area = pygame.Rect(x, y, modal.w - 40, max(56, modal.bottom - y - 60))
            self._draw_card(screen, item_area, (10, 12, 18), border_color=(56, 62, 76), radius=8)
            ry = item_area.y + 4
            prev_clip = screen.get_clip()
            screen.set_clip(item_area)
            popup_items = check.get("Items", [])
            max_rows = max(1, (item_area.h - 8) // 30)
            self.popup_item_scroll = max(
                0, min(self.popup_item_scroll, max(0, len(popup_items) - max_rows)))
            for ii in range(self.popup_item_scroll, min(len(popup_items), self.popup_item_scroll + max_rows)):
                popup_item = popup_items[ii]
                item_row = pygame.Rect(item_area.x + 4, ry, item_area.w - 218, 26)
                pos_row = pygame.Rect(item_row.right + 4, ry, 82, 26)
                scale_row = pygame.Rect(pos_row.right + 4, ry, 54, 26)
                del_btn = pygame.Rect(item_area.right - 26, ry, 22, 26)
                self.popup_item_rows[(ii, "Item")] = item_row
                self.popup_item_rows[(ii, "Positions")] = pos_row
                self.popup_item_rows[(ii, "Scale")] = scale_row
                self.popup_item_rows[(ii, "del")] = del_btn
                pygame.draw.rect(screen, self.COLORS["panel_alt"], item_row)
                pygame.draw.rect(screen, self.COLORS["panel_alt"], pos_row)
                pygame.draw.rect(screen, self.COLORS["panel_alt"], scale_row)
                item_name = popup_item.get("Item") or popup_item.get("Name", "")
                pos = popup_item.get("Positions", {})
                self._text(screen, item_name[:22] or "item name", (item_row.x + 4, item_row.y + 5), 12,
                           self.COLORS["line_light"] if item_name else self.COLORS["muted"])
                self._text(screen, f"{pos.get('x',0)},{pos.get('y',0)}", (pos_row.x + 4, pos_row.y + 5), 11,
                           self.COLORS["muted"])
                self._text(screen, str(popup_item.get("Scale", 1.0))[:5], (scale_row.x + 4, scale_row.y + 5), 11,
                           self.COLORS["muted"])
                up_enabled = si > 0
                down_enabled = si < len(subchecks) - 1
                pygame.draw.rect(screen, (70, 74, 86) if up_enabled else (35, 38, 46), up_btn)
                pygame.draw.rect(screen, (70, 74, 86) if down_enabled else (35, 38, 46), down_btn)
                self._text_center(
                    screen, "^", up_btn, 13,
                    self.COLORS["line_light"] if up_enabled else self.COLORS["muted"])
                self._text_center(
                    screen, "v", down_btn, 13,
                    self.COLORS["line_light"] if down_enabled else self.COLORS["muted"])
                pygame.draw.rect(screen, self.COLORS["red"], del_btn)
                self._text(screen, "x", (del_btn.x + 7, del_btn.y + 4), 14, self.COLORS["line_light"])
                ry += 30
            screen.set_clip(prev_clip)

        # Close / Delete buttons
        close_btn = pygame.Rect(modal.right - 120, modal.bottom - 44, 100, 30)
        del_check_btn = pygame.Rect(modal.x + 20, modal.bottom - 44, 120, 30)
        self.check_modal_buttons["close"] = close_btn
        self.check_modal_buttons["delete"] = del_check_btn
        self._draw_button(screen, close_btn, "Close", (36, 124, 87), hover=(self.hover_modal_key == "close"))
        self._draw_button(screen, del_check_btn, "Delete check", self.COLORS["red"], hover=(self.hover_modal_key == "delete"))

    def _draw_map_checks(self, screen, bg_rect, canvas_size):
        self.check_screen_rects = {}
        self.check_screen_anchors = {}
        checks = self._current_map()["data"].get("ChecksList", [])
        scale = bg_rect.w / canvas_size[0]
        extra = self.maps_extra or {}
        ssc = extra.get("SizeSimpleCheck", {"w": 5, "h": 5})
        sgc = extra.get("SizeGroupChecks", {"w": 16, "h": 16})
        red = (200, 40, 40)
        black = (0, 0, 0)
        prev_clip = screen.get_clip()
        screen.set_clip(getattr(self, "map_view_rect", bg_rect))
        for index, check in enumerate(checks):
            pos = check.get("Positions") or {}
            px = float(pos.get("x", 0) or 0)
            py = float(pos.get("y", 0) or 0)
            anchor_x = bg_rect.x + int(px * scale)
            anchor_y = bg_rect.y + int(py * scale)
            is_block = check.get("Kind") in ("Block", "MapPopup")
            if is_block and not self.show_map_blocks:
                continue
            if not is_block and not self.show_map_checks:
                continue
            if is_block:
                marker_w = max(1, int(float(sgc.get("w", 16) or 16) * scale))
                marker_h = max(1, int(float(sgc.get("h", 16) or 16) * scale))
                rect = pygame.Rect(anchor_x, anchor_y, marker_w, marker_h)
            else:
                simple_w = float(ssc.get("w", 5) or 5)
                simple_h = float(ssc.get("h", 5) or 5)
                pin_x = bg_rect.x + int((px + simple_w / 2) * scale)
                pin_y = bg_rect.y + int((py + simple_h / 2) * scale)
                pin_w = max(1, int(simple_w * 2 * scale))
                pin_h = max(1, int(simple_h * 2 * scale))
                rect = pygame.Rect(pin_x, pin_y, pin_w, pin_h)
                circle_center = (
                    rect.x + rect.w // 2,
                    rect.y + rect.h // 2,
                )
                circle_radius = max(1, rect.w // 2)

            if not rect.colliderect(self.map_view_rect):
                continue

            if is_block:
                pygame.draw.rect(screen, (80, 120, 210) if check.get("Kind") == "MapPopup" else red, rect)
                pygame.draw.rect(screen, black, rect, max(1, int(2 * scale)))
                n = (len(check.get("Items") or []) if check.get("Kind") == "MapPopup"
                     else len(check.get("Checks") or []))
                self._text_center(
                    screen, str(n), rect,
                    max(1, int(min(rect.w, rect.h) * 0.55)),
                    (255, 255, 255),
                )
            else:
                pygame.gfxdraw.filled_circle(
                    screen, circle_center[0], circle_center[1], circle_radius, red)
                pygame.gfxdraw.aacircle(
                    screen, circle_center[0], circle_center[1], circle_radius, black)
            self.check_screen_anchors[index] = (anchor_x, anchor_y)
            self.check_screen_rects[index] = rect.inflate(6, 6)
            if index == self.selected_check_index:
                pygame.draw.rect(screen, self.COLORS["line_light"], rect.inflate(8, 8), 2)
                name = check.get("Name", "")
                if name:
                    self._text(screen, name, (rect.right + 6, rect.y - 2), 14, self.COLORS["line_light"])
        screen.set_clip(prev_clip)
    def _draw_linked_items(self, screen, item, bg_rect, depth=0, parent_path=(), parent_rect=None):
        if depth > 8:
            return
        linked_fields = [
            ("HintItems", (0, 220, 255)),
            ("ActiveItems", self.COLORS["green"]),
            ("InactiveItems", self.COLORS["red"]),
        ]
        parent_rect = parent_rect or item.get("screen_rect")
        for field, color in linked_fields:
            for linked_index, linked in enumerate(item.get(field) or []):
                path = parent_path + (field, linked_index)
                rect = self._draw_item(screen, linked, None, bg_rect, linked=True)
                visible_rect = rect.clip(screen.get_clip() or rect)
                if visible_rect.w <= 0 or visible_rect.h <= 0:
                    linked["screen_rect"] = pygame.Rect(0, 0, 0, 0)
                    continue
                linked["screen_rect"] = visible_rect
                if self.show_links and parent_rect and parent_rect.w > 0:
                    self._draw_link_elbow(screen, parent_rect, rect, color)
                linked["_linked_path"] = path
                self.linked_item_targets.append((path, visible_rect))
                pygame.draw.rect(screen, color, rect.inflate(5, 5), 2)
                if path == self.selected_linked_path:
                    pygame.draw.rect(screen, self.COLORS["gold"], rect.inflate(9, 9), 3)
                label = field.replace("Items", "")
                if rect.w >= 20 and rect.h >= 20:
                    self._text(screen, label[:1], (rect.right - 10, rect.y + 1), 12, color)
                self._draw_linked_items(screen, linked, bg_rect, depth + 1, path, parent_rect=rect)

    def _draw_item(self, screen, item, index, bg_rect, linked=False):
        icon = None if item.get("kind") == "ImageItem" and not item.get("sheet") \
            else self._get_icon_surface(item["row"], item["column"], item.get("sheet"))
        item_sheet = self._sheet_by_name(item.get("sheet")) or self.active_sheet
        cw = item_sheet["cell_w"] if item_sheet else self.cell_width
        ch = item_sheet["cell_h"] if item_sheet else self.cell_height
        external_image = None
        if item.get("kind") == "EditableBox":
            sizes = item.get("Sizes") or {}
            cw = int(sizes.get("w", 120))
            ch = int(sizes.get("h", 32))
        elif item.get("kind") == "ImageItem":
            external_image = self._load_item_image_asset(item, "Image")
            if external_image:
                cw = external_image.get_width()
                ch = external_image.get_height()
            elif item.get("sheet"):
                icon = self._get_icon_surface(item.get("row", 1), item.get("column", 1), item.get("sheet"))
                if icon:
                    cw = icon.get_width()
                    ch = icon.get_height()
                else:
                    sizes = item.get("Sizes") or {}
                    cw = int(sizes.get("w", 64))
                    ch = int(sizes.get("h", 64))
            else:
                sizes = item.get("Sizes") or {}
                cw = int(sizes.get("w", 64))
                ch = int(sizes.get("h", 64))
        elif item.get("kind") == "TimerItem":
            timer_rect = (item.get("Timer") or {}).get("Rect", {})
            buttons = item.get("Buttons") or {}
            cw = int(timer_rect.get("w", 180))
            ch = int(timer_rect.get("h", 42))
            for cfg in buttons.values():
                rect_data = (cfg or {}).get("Rect", {})
                cw = max(cw, int(rect_data.get("x", 0)) + int(rect_data.get("w", 0)))
                ch = max(ch, int(rect_data.get("y", 0)) + int(rect_data.get("h", 0)))
        scale = bg_rect.w / self._canvas_size()[0]
        size = (max(1, int(cw * scale)), max(1, int(ch * scale)))
        x = bg_rect.x + int(item["x"] * scale)
        y = bg_rect.y + int(item["y"] * scale)
        rect = pygame.Rect(x, y, size[0], size[1])
        item["screen_rect"] = rect
        if item.get("kind") == "EditableBox":
            pygame.draw.rect(screen, (245, 245, 245), rect)
            pygame.draw.rect(screen, self.COLORS["green"], rect, 2)
            placeholder = item.get("PlaceHolder") or item.get("name") or "EditableBox"
            self._text(screen, placeholder, (rect.x + 5, rect.y + 3), max(10, int(13 * scale)),
                       (20, 20, 20))
        elif item.get("kind") == "TimerItem":
            pygame.draw.rect(screen, (12, 15, 22), rect)
            pygame.draw.rect(screen, self.COLORS["green"], rect, 2)
            self._text_center(screen, "00:00.00", rect, max(10, int(24 * scale)), self.COLORS["green"])
        elif item.get("kind") == "ImageItem":
            if external_image:
                image = pygame.transform.smoothscale(external_image, size)
                if not item.get("visible", True):
                    image = image.copy()
                    image.set_alpha(95)
                screen.blit(image, rect)
            elif icon:
                image = pygame.transform.smoothscale(icon, size)
                if not item.get("visible", True):
                    image = image.copy()
                    image.set_alpha(95)
                screen.blit(image, rect)
            else:
                pygame.draw.rect(screen, self.COLORS["panel_alt"], rect)
                self._text_center(screen, "Image", rect, max(10, int(13 * scale)), self.COLORS["muted"])
        elif icon:
            icon = pygame.transform.smoothscale(icon, size)
            if not item.get("visible", True):
                icon = icon.copy()
                icon.set_alpha(95)
            screen.blit(icon, rect)
        else:
            pygame.draw.rect(screen, self.COLORS["panel_alt"], rect)
        pygame.draw.rect(screen, self.COLORS["red"] if not item.get("visible", True) else self.COLORS["green"], rect, 2)
        if not item.get("visible", True) and rect.w >= 18 and rect.h >= 18:
            self._text(screen, "V", (rect.right - 10, rect.bottom - 16), 12, self.COLORS["red"])
        if size[0] >= 24 and size[1] >= 24:
            self._text(screen, str(item["id"]), (rect.x + 3, rect.y + 1), 12,
                       self.COLORS["muted"] if linked else self.COLORS["line_light"])
        return rect

    def _draw_items_list_tab(self, screen, panel, x, y, pad):
        entries = self._flatten_items_for_list()
        self.items_list_entries = entries
        self._text(screen, f"{len(entries)} item(s)", (x, y), 13, self.COLORS["muted"])
        self.items_list_buttons = {}
        btn_w = 48
        up_rect = pygame.Rect(panel.right - pad - btn_w * 2 - 6, y - 4, btn_w, 24)
        down_rect = pygame.Rect(panel.right - pad - btn_w, y - 4, btn_w, 24)
        self.items_list_buttons["item_order_up"] = up_rect
        self.items_list_buttons["item_order_down"] = down_rect
        self._draw_button(screen, up_rect, "Up", self.COLORS["button"], hover=(self.hover_key == "item_order_up"))
        self._draw_button(screen, down_rect, "Down", self.COLORS["button"], hover=(self.hover_key == "item_order_down"))
        y += 22
        area = pygame.Rect(x, y, panel.w - pad * 2, panel.bottom - y - 14)
        self._draw_card(screen, area, (10, 12, 18), border_color=(56, 62, 76), radius=8)
        self.items_list_rect = area
        self.items_list_rows = {}
        if not entries:
            self._text_center(screen, "No item yet", area, 16, self.COLORS["muted"])
            return
        row_h = 40
        view = area.inflate(-8, -8)
        content_h = len(entries) * row_h
        max_scroll = max(0, content_h - view.h)
        self.items_list_scroll = max(0, min(self.items_list_scroll, max_scroll))
        prev_clip = screen.get_clip()
        screen.set_clip(view)
        for index, entry in enumerate(entries):
            item = entry["item"]
            depth = entry["depth"]
            ry = view.y + index * row_h - self.items_list_scroll
            if ry + row_h < view.y or ry > view.bottom:
                continue
            indent = depth * 16
            row = pygame.Rect(view.x + indent, ry, view.w - indent, row_h - 4)
            self.items_list_rows[index] = row
            if entry["path"] == (self.selected_item_index,) and self.selected_item_index is not None and depth == 0:
                selected = True
            elif depth > 0 and entry["path"] == self.selected_linked_path:
                selected = True
            else:
                selected = False
            hovered = self.hover_key == f"itemrow_{index}"
            if selected:
                pygame.draw.rect(screen, (40, 46, 62), row)
                pygame.draw.rect(screen, self.COLORS["gold"], row, 1)
            elif hovered:
                pygame.draw.rect(screen, self.COLORS["panel_alt"], row)
            if entry["color"]:
                pygame.draw.rect(screen, entry["color"], (row.x, row.y, 3, row.h))
            icon = self._get_icon_surface(item.get("row", 1), item.get("column", 1), item.get("sheet"))
            ix = row.x + 8
            if icon:
                screen.blit(pygame.transform.smoothscale(icon, (28, 28)), (ix, row.y + 4))
            else:
                pygame.draw.rect(screen, (30, 35, 48), pygame.Rect(ix, row.y + 4, 28, 28))
            name = item.get("name", "Item")
            maxn = max(5, (row.w - 48) // 8)
            if len(name) > maxn:
                name = name[:maxn - 1] + "..."
            self._text(screen, name, (ix + 34, row.y + 4), 14, self.COLORS["line_light"])
            self._text(screen, item.get("kind", "Item"), (ix + 34, row.y + 22), 11, self.COLORS["muted"])
        screen.set_clip(prev_clip)
        track = pygame.Rect(area.right - 7, view.y, 4, view.h)
        self._register_scrollbar(screen, "items_list", track, self.items_list_scroll, max_scroll, content_h, view.h)

    def _draw_maps_tab(self, screen, panel, x, y, pad):
        self.maps_rows = {}
        self.maps_buttons = {}
        # Add / Remove buttons
        add_btn = pygame.Rect(panel.right - pad - 30, y - 2, 30, 26)
        rem_btn = pygame.Rect(add_btn.x - 36, y - 2, 30, 26)
        self.maps_buttons["map_add"] = add_btn
        self.maps_buttons["map_remove"] = rem_btn
        self._text(screen, f"{len(self.maps)} map(s)", (x, y), 13, self.COLORS["muted"])
        self._draw_button(screen, add_btn, "+", (36, 124, 87), hover=(self.hover_key == "map_add"))
        self._draw_button(screen, rem_btn, "-", self.COLORS["red"], hover=(self.hover_key == "map_remove"))
        y += 34

        # Warn when the window is too small to show the maps (placed right of items)
        ok, rw, rh = self._map_window_ok()
        if not ok:
            warn = pygame.Rect(x, y, panel.w - pad * 2, 46)
            pygame.draw.rect(screen, (60, 40, 20), warn)
            pygame.draw.rect(screen, (200, 140, 60), warn, 1)
            self._text(screen, "Window too small for maps!", (warn.x + 8, warn.y + 4), 13, (255, 200, 120))
            self._text(screen, f"need {rw}x{rh}, have {self.template_size[0]}x{self.template_size[1]}",
                       (warn.x + 8, warn.y + 22), 11, self.COLORS["muted"])
            fit_btn = pygame.Rect(warn.right - 70, warn.y + 12, 62, 22)
            self.maps_buttons["fit_window"] = fit_btn
            self._draw_button(screen, fit_btn, "Fit", (36, 124, 87), hover=(self.hover_key == "fit_window"))
            y += 52

        # Map list
        list_h = min(len(self.maps) * 34 + 8, 180)
        area = pygame.Rect(x, y, panel.w - pad * 2, max(40, list_h))
        self._draw_card(screen, area, (10, 12, 18), border_color=(56, 62, 76), radius=8)
        ry = area.y + 6
        for index, m in enumerate(self.maps):
            row = pygame.Rect(area.x + 4, ry, area.w - 8, 28)
            self.maps_rows[index] = row
            if index == self.selected_map_index:
                pygame.draw.rect(screen, (40, 46, 62), row)
                pygame.draw.rect(screen, self.COLORS["gold"], row, 1)
            elif self.hover_key == f"maprow_{index}":
                pygame.draw.rect(screen, self.COLORS["panel_alt"], row)
            thumb = m["assets"].get("Background")
            if thumb:
                screen.blit(pygame.transform.smoothscale(thumb, (22, 22)), (row.x + 4, row.y + 3))
            else:
                pygame.draw.rect(screen, (30, 35, 48), pygame.Rect(row.x + 4, row.y + 3, 22, 22))
            self._text(screen, m["name"], (row.x + 32, row.y + 6), 14, self.COLORS["line_light"])
            ry += 32
        y = area.bottom + 12

        # Selected map: rename + options + checks list
        if not (0 <= self.selected_map_index < len(self.maps)):
            return
        m = self.maps[self.selected_map_index]
        third = (panel.w - pad * 2 - 16) // 3
        rename_btn = pygame.Rect(x, y, third, 30)
        opt_btn = pygame.Rect(rename_btn.right + 8, y, third, 30)
        data_btn = pygame.Rect(opt_btn.right + 8, y, panel.right - pad - (opt_btn.right + 8), 30)
        self.maps_buttons["map_rename"] = rename_btn
        self.maps_buttons["map_options"] = opt_btn
        self.maps_buttons["map_data"] = data_btn
        self._draw_button(screen, rename_btn, f"{m['name']}"[:10], (70, 74, 86), hover=(self.hover_key == "map_rename"))
        self._draw_button(screen, opt_btn, "Options", (70, 74, 86), hover=(self.hover_key == "map_options"))
        self._draw_button(screen, data_btn, "Map data", (70, 74, 86), hover=(self.hover_key == "map_data"))
        y += 38

        # Checks / blocks list for this map (Blocks section + Simple checks section)
        checks = m["data"].get("ChecksList", [])
        blocks = [(i, c) for i, c in enumerate(checks) if c.get("Kind") == "Block"]
        popups = [(i, c) for i, c in enumerate(checks) if c.get("Kind") == "MapPopup"]
        simples = [(i, c) for i, c in enumerate(checks) if c.get("Kind") not in ("Block", "MapPopup")]
        self._text(screen, f"CHECKS  ({len(checks)})", (x, y), 12, self.COLORS["gold"])
        self._text(screen, "click=select  dbl=edit", (x + 110, y + 1), 11, self.COLORS["muted"])
        y += 20
        area = pygame.Rect(x, y, panel.w - pad * 2, panel.bottom - y - 12)
        self._draw_card(screen, area, (10, 12, 18), border_color=(56, 62, 76), radius=8)
        self.map_check_rows = []
        if not checks:
            self._text_center(screen, "Click the map to add a check", area, 14, self.COLORS["muted"])
            return

        # Build the flat render list (headers + blocks + expanded sub-checks + simples)
        entries = [("header", f"BLOCKS ({len(blocks)})")]
        for i, c in blocks:
            entries.append(("block", i, c))
            if i in self.expanded_blocks:
                for si, sub in enumerate(c.get("Checks") or []):
                    entries.append(("sub", i, si, sub))
        entries.append(("header", f"MAP POPUPS ({len(popups)})"))
        for i, c in popups:
            entries.append(("popup", i, c))
        entries.append(("header", f"SIMPLE CHECKS ({len(simples)})"))
        for i, c in simples:
            entries.append(("simple", i, c))

        row_h = 26
        view = area.inflate(-8, -8)
        content_h = len(entries) * row_h
        max_scroll = max(0, content_h - view.h)
        self.maps_checks_scroll = max(0, min(getattr(self, "maps_checks_scroll", 0), max_scroll))
        self.maps_checks_max_scroll = max_scroll
        self.maps_checks_rect = area
        prev_clip = screen.get_clip()
        screen.set_clip(view)
        for ei, entry in enumerate(entries):
            cy = view.y + ei * row_h - self.maps_checks_scroll
            if cy + row_h < view.y or cy > view.bottom:
                continue
            row = pygame.Rect(view.x, cy, view.w, row_h - 2)
            kind = entry[0]
            if kind == "header":
                self._text(screen, entry[1], (row.x + 4, row.y + 4), 12, self.COLORS["gold"])
                continue
            if kind in ("block", "popup"):
                i, c = entry[1], entry[2]
                is_popup = kind == "popup"
                if is_popup:
                    selrow = row
                    self.map_check_rows.append((selrow, {"t": "popup", "i": i}))
                else:
                    expanded = i in self.expanded_blocks
                    tri = pygame.Rect(row.x + 2, row.y, 18, row.h)
                    self.map_check_rows.append((tri, {"t": "toggle", "i": i}))
                    selrow = pygame.Rect(tri.right, row.y, row.w - tri.w, row.h)
                    self.map_check_rows.append((selrow, {"t": "block", "i": i}))
                if i == self.selected_check_index:
                    pygame.draw.rect(screen, (40, 46, 62), row)
                    pygame.draw.rect(screen, self.COLORS["gold"], row, 1)
                if not is_popup:
                    self._text(screen, "v" if expanded else ">", (tri.x + 4, row.y + 4), 13,
                               self.COLORS["line_light"])
                mk = pygame.Rect(row.x + 22, row.y + 6, 13, 13)
                pygame.draw.rect(screen, (80, 120, 210) if is_popup else (200, 40, 40), mk)
                pygame.draw.rect(screen, (0, 0, 0), mk, 1)
                nm = (("P " if is_popup else "") + str(c.get("Name", "")))[:max(6, (row.w - 70) // 8)]
                self._text(screen, nm, (row.x + 40, row.y + 4), 13, self.COLORS["line_light"])
                count = len(c.get("Items") or []) if is_popup else len(c.get("Checks") or [])
                self._text(screen, f"[{count}]", (row.right - 30, row.y + 4), 12, self.COLORS["muted"])
            elif kind == "sub":
                i, si, sub = entry[1], entry[2], entry[3]
                self.map_check_rows.append((row, {"t": "sub", "i": i, "si": si}))
                self._text(screen, "- " + str(sub.get("Name", ""))[:max(6, (row.w - 60) // 8)],
                           (row.x + 44, row.y + 4), 12, self.COLORS["muted"])
            else:  # simple
                i, c = entry[1], entry[2]
                self.map_check_rows.append((row, {"t": "simple", "i": i}))
                if i == self.selected_check_index:
                    pygame.draw.rect(screen, (40, 46, 62), row)
                    pygame.draw.rect(screen, self.COLORS["gold"], row, 1)
                mk = pygame.Rect(row.x + 8, row.y + 6, 13, 13)
                pygame.gfxdraw.filled_circle(screen, mk.centerx, mk.centery, 6, (200, 40, 40))
                pygame.gfxdraw.aacircle(screen, mk.centerx, mk.centery, 6, (0, 0, 0))
                nm = str(c.get("Name", ""))[:max(6, (row.w - 50) // 8)]
                self._text(screen, nm, (row.x + 28, row.y + 4), 13, self.COLORS["line_light"])
        screen.set_clip(prev_clip)
        track = pygame.Rect(area.right - 7, view.y, 4, view.h)
        self._register_scrollbar(screen, "maps_checks", track, self.maps_checks_scroll, max_scroll, content_h, view.h)

    def _draw_left_panel(self, screen):
        panel = self.left_panel_rect
        self._draw_card(screen, panel, self.COLORS["panel"], radius=14)
        pad = 14
        x = panel.x + pad
        y = panel.y + 12

        # Tabs: Sheets | Items List (| Maps when a map template)
        self.left_tabs = {}
        tabs = [("sheets", "Sheets"), ("items", "Items")]
        if self.is_map_template:
            tabs.append(("maps", "Maps"))
        tab_w = (panel.w - pad * 2 - 8 * (len(tabs) - 1)) // len(tabs)
        for i, (key, label) in enumerate(tabs):
            tr = pygame.Rect(x + i * (tab_w + 8), y, tab_w, 30)
            self.left_tabs[key] = tr
            active = self.left_tab == key
            pygame.draw.rect(screen, (40, 46, 62) if active else (20, 24, 34), tr)
            pygame.draw.rect(screen, self.COLORS["gold"] if active else (56, 62, 76), tr, 1)
            self._text_center(screen, label, tr, 15, self.COLORS["gold"] if active else self.COLORS["line_light"])
        y += 40

        if self.left_tab == "items":
            self.sheet_buttons = {}
            self.sheet_list_rows = {}
            self.sheet_rect = pygame.Rect(0, 0, 1, 1)
            self._draw_items_list_tab(screen, panel, x, y, pad)
            return

        if self.left_tab == "maps":
            self.sheet_buttons = {}
            self.sheet_list_rows = {}
            self.sheet_rect = pygame.Rect(0, 0, 1, 1)
            self._draw_maps_tab(screen, panel, x, y, pad)
            return

        # New (blank) / Add (import) / Remove buttons
        self.sheet_buttons = {}
        add_btn = pygame.Rect(panel.right - pad - 30, y - 2, 30, 26)
        rem_btn = pygame.Rect(add_btn.x - 36, y - 2, 30, 26)
        new_btn = pygame.Rect(rem_btn.x - 56, y - 2, 50, 26)
        self.sheet_buttons["new"] = new_btn
        self.sheet_buttons["add"] = add_btn
        self.sheet_buttons["remove"] = rem_btn
        self._draw_button(screen, new_btn, "New", (70, 74, 86), hover=(self.hover_key == "sheet_new"))
        self._draw_button(screen, add_btn, "+", (36, 124, 87), hover=(self.hover_key == "sheet_add"))
        self._draw_button(screen, rem_btn, "-", self.COLORS["red"], hover=(self.hover_key == "sheet_remove"))
        y += 36

        # Dropdown header (shows active sheet, click to expand)
        header_h = 34
        self.sheet_dropdown_rect = pygame.Rect(x, y, panel.w - pad * 2, header_h)
        self._draw_card(screen, self.sheet_dropdown_rect, (40, 46, 62), border_color=self.COLORS["gold"], radius=8)
        max_name = max(6, (self.sheet_dropdown_rect.w - 44) // 9)
        if self.active_sheet:
            name = self.active_sheet["name"]
            if len(name) > max_name:
                name = name[:max_name - 1] + "..."
            self._text(screen, name, (x + 10, y + 7), 16, self.COLORS["gold"])
        else:
            self._text(screen, "No spritesheet - press +", (x + 10, y + 7), 15, self.COLORS["muted"])
        chevron = "v" if not self.sheet_dropdown_open else "^"
        self._text(screen, chevron, (self.sheet_dropdown_rect.right - 20, y + 6), 16, self.COLORS["gold"])
        y += header_h + 12

        # Active tileset preview below the dropdown
        self.sheet_list_rows = {}
        if not self.active_sheet:
            self.sheet_rect = pygame.Rect(0, 0, 1, 1)
        else:
            self._text(screen, f"Tiles - cell {self.cell_width}x{self.cell_height}", (x, y), 14, self.COLORS["muted"])
            ty = y + 22
            # Reserve a strip at the bottom for the "set tile image" button
            set_tile_btn = pygame.Rect(x, panel.bottom - 48, panel.w - pad * 2, 34)
            area = pygame.Rect(x, ty, panel.w - pad * 2, set_tile_btn.y - ty - 10)
            self._draw_card(screen, area, (10, 12, 18), border_color=(56, 62, 76), radius=8)
            self._draw_tileset(screen, area)
            self.sheet_buttons["set_tile"] = set_tile_btn
            sel = self.selected_cell and self.active_sheet and self.selected_cell[0] == self.active_sheet["name"]
            label = "Set image in selected tile" if sel else "Select a tile first"
            self._draw_button(screen, set_tile_btn, label, (70, 74, 86) if sel else (44, 48, 62),
                              hover=(self.hover_key == "sheet_set_tile"))

        # Expanded dropdown list (overlay, drawn last so it sits on top)
        if self.sheet_dropdown_open and self.sheets:
            row_h = 30
            list_rect = pygame.Rect(self.sheet_dropdown_rect.x, self.sheet_dropdown_rect.bottom + 2,
                                    self.sheet_dropdown_rect.w, len(self.sheets) * row_h + 6)
            self._draw_card(screen, list_rect, (18, 21, 30), border_color=self.COLORS["gold"], radius=8)
            ry = list_rect.y + 3
            for index, sheet in enumerate(self.sheets):
                row = pygame.Rect(list_rect.x + 3, ry, list_rect.w - 6, row_h - 2)
                self.sheet_list_rows[index] = row
                active = index == self.active_sheet_index
                if active:
                    pygame.draw.rect(screen, (40, 46, 62), row)
                elif self.hover_key == f"sheetrow_{index}":
                    pygame.draw.rect(screen, self.COLORS["panel_alt"], row)
                name_color = self.COLORS["gold"] if active else self.COLORS["line_light"]
                dims = f"{sheet['cell_w']}x{sheet['cell_h']}"
                dims_w = len(dims) * 8
                dims_x = row.right - dims_w - 10
                name = sheet["name"]
                max_name = max(4, (dims_x - (row.x + 8)) // 9)
                if len(name) > max_name:
                    name = name[:max_name - 1] + "..."
                self._text(screen, name, (row.x + 8, row.y + 5), 16, name_color)
                self._text(screen, dims, (dims_x, row.y + 6), 14, self.COLORS["muted"])
                ry += row_h

    def _draw_right_panel(self, screen):
        panel = self.right_panel_rect
        self._draw_card(screen, panel, self.COLORS["panel"], radius=14)
        pad = 14
        x = panel.x + pad
        y = panel.y + 14
        if self.canvas_context == "submenu":
            header = "Choices" if (self.submenu_parent or {}).get("kind") == "MultipleChoiceItem" else "Submenu"
        else:
            header = "Template"
        self._text(screen, header, (x, y), 22, self.COLORS["gold"])
        y += 40
        self.info_buttons = {}

        if self.canvas_context == "submenu":
            self._draw_submenu_info_panel(screen, panel, x, y, pad)
            return

        # Scrollable content area (title above stays fixed)
        content_top = y
        view = pygame.Rect(panel.x + 2, content_top, panel.w - 4, panel.bottom - content_top - 8)
        self.info_panel_rect = view
        prev_clip = screen.get_clip()
        screen.set_clip(view)
        y = content_top - self.info_scroll

        # Name (clickable to rename)
        name_rect = pygame.Rect(x, y, panel.w - pad * 2, 50)
        self._draw_card(screen, name_rect, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        self.info_buttons["name"] = name_rect
        self._text(screen, "NAME", (name_rect.x + 10, name_rect.y + 6), 12, self.COLORS["gold"])
        display = self.project_name or "Untitled"
        if len(display) > 22:
            display = display[:19] + "..."
        self._text(screen, display, (name_rect.x + 10, name_rect.y + 24), 18, self.COLORS["line_light"])
        y = name_rect.bottom + 14

        # Icon
        self._text(screen, "ICON", (x, y), 12, self.COLORS["gold"])
        y += 18
        icon_rect = pygame.Rect(x, y, 72, 72)
        self._draw_card(screen, icon_rect, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        icon = self.project_icon
        if icon is None and self.sheets:
            icon = self._get_icon_surface(1, 1, self.sheets[0]["name"])
        if icon:
            scaled = pygame.transform.smoothscale(icon, (56, 56))
            screen.blit(scaled, (icon_rect.centerx - 28, icon_rect.centery - 28))
        btn_x = icon_rect.right + 14
        btn_w = panel.right - pad - btn_x
        set_icon = pygame.Rect(btn_x, icon_rect.y, btn_w, 30)
        self.info_buttons["set_icon"] = set_icon
        self._draw_button(screen, set_icon, "Set from tile", self.COLORS["button"], hover=(self.hover_key == "set_icon"))
        import_icon = pygame.Rect(btn_x, set_icon.bottom + 8, btn_w, 30)
        self.info_buttons["import_icon"] = import_icon
        self._draw_button(screen, import_icon, "Import image", (70, 74, 86), hover=(self.hover_key == "import_icon"))
        y = icon_rect.bottom + 16

        # Background color
        bg_row = pygame.Rect(x, y, panel.w - pad * 2, 44)
        self._draw_card(screen, bg_row, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        self.info_buttons["background_color"] = bg_row
        self._text(screen, "BACKGROUND COLOR", (bg_row.x + 10, bg_row.y + 6), 12, self.COLORS["gold"])
        bg = self.background_color or {"r": 0, "g": 0, "b": 0}
        swatch = pygame.Rect(bg_row.right - 56, bg_row.y + 10, 38, 24)
        pygame.draw.rect(screen, (bg.get("r", 0), bg.get("g", 0), bg.get("b", 0)), swatch)
        pygame.draw.rect(screen, self.COLORS["line_light"], swatch, 1)
        self._text(screen, f"{bg.get('r',0)}, {bg.get('g',0)}, {bg.get('b',0)}",
                   (bg_row.x + 10, bg_row.y + 24), 14, self.COLORS["line_light"])
        y = bg_row.bottom + 14

        dim_row = pygame.Rect(x, y, panel.w - pad * 2, 44)
        self._draw_card(screen, dim_row, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        self.info_buttons["dimensions"] = dim_row
        self._text(screen, "DIMENSIONS", (dim_row.x + 10, dim_row.y + 6), 12, self.COLORS["gold"])
        self._text(screen, f"{self.template_size[0]} x {self.template_size[1]}",
                   (dim_row.x + 10, dim_row.y + 24), 15, self.COLORS["line_light"])
        y = dim_row.bottom + 8

        bg_pos = self.background_position or {"x": 0, "y": 0}
        pos_row = pygame.Rect(x, y, panel.w - pad * 2, 44)
        self._draw_card(screen, pos_row, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        self.info_buttons["background_position"] = pos_row
        self._text(screen, "BACKGROUND POSITION", (pos_row.x + 10, pos_row.y + 6), 12, self.COLORS["gold"])
        self._text(screen, f"x {bg_pos.get('x', 0)} / y {bg_pos.get('y', 0)}",
                   (pos_row.x + 10, pos_row.y + 24), 15, self.COLORS["line_light"])
        y = pos_row.bottom + 14

        max_chars = max(8, (panel.w - pad * 2) // 9 - 2)

        # Editable Informations fields (click to edit). Always offer the standard keys.
        edit_keys = ["Creator", "Version", "Credits"]
        for key in (self.project_info or {}):
            if key != "Name" and key not in edit_keys:
                edit_keys.append(key)
        for key in edit_keys:
            row = pygame.Rect(x, y, panel.w - pad * 2, 44)
            self._draw_card(screen, row, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
            self.info_buttons[f"info_{key}"] = row
            self._text(screen, key.upper(), (row.x + 10, row.y + 6), 12, self.COLORS["gold"])
            value = str((self.project_info or {}).get(key) or "")
            display = value if value else "click to edit"
            color = self.COLORS["line_light"] if value else self.COLORS["muted"]
            if len(display) > max_chars:
                display = display[:max_chars - 3] + "..."
            self._text(screen, display, (row.x + 10, row.y + 24), 15, color)
            y += 50

        # Computed (read-only) info
        value_x = x + 120
        value_chars = max(4, (panel.right - pad - value_x) // 9)
        for label, value in [
            ("Background", os.path.basename(self.background_path) if self.background_path else "None"),
            ("Tilesets", str(len(self.sheets))),
            ("Items placed", str(len(self.placed_items))),
        ]:
            self._text(screen, label, (x, y), 13, self.COLORS["muted"])
            display = value if len(value) <= value_chars else value[:value_chars - 3] + "..."
            self._text(screen, display, (value_x, y), 15, self.COLORS["line_light"])
            y += 26

        # Illustration import button
        y += 8
        illu_btn = pygame.Rect(x, y, panel.w - pad * 2, 34)
        self.info_buttons["illustration"] = illu_btn
        illu_label = "Illustration: imported" if self.illustration is not None else "Import illustration"
        self._draw_button(screen, illu_btn, illu_label, (70, 74, 86), hover=(self.hover_key == "illustration"))
        y += 42

        # Fonts editor button
        fonts_btn = pygame.Rect(x, y, panel.w - pad * 2, 38)
        self.info_buttons["fonts"] = fonts_btn
        self._draw_button(screen, fonts_btn, "Edit fonts", (70, 74, 86), hover=(self.hover_key == "fonts"))
        y += 46

        # Map template toggle
        map_btn = pygame.Rect(x, y, panel.w - pad * 2, 34)
        self.info_buttons["map_template"] = map_btn
        on = self.is_map_template
        self._draw_button(screen, map_btn, f"Map template: {'ON' if on else 'OFF'}",
                          (36, 124, 87) if on else (70, 74, 86), hover=(self.hover_key == "map_template"))
        y += 38

        screen.set_clip(prev_clip)

        # Scroll clamping + scrollbar
        content_h = (y + self.info_scroll) - content_top
        max_scroll = max(0, content_h - view.h)
        self.info_scroll = max(0, min(self.info_scroll, max_scroll))
        self.info_max_scroll = max_scroll
        track = pygame.Rect(panel.right - 7, view.y + 2, 4, view.h - 4)
        self._register_scrollbar(screen, "info", track, self.info_scroll, max_scroll, content_h, view.h)

    def _draw_link_elbow(self, screen, a, b, color):
        ax, ay = a.center
        bx, by = b.center
        midx = (ax + bx) // 2
        pts = [(ax, ay), (midx, ay), (midx, by), (bx, by)]
        pygame.draw.lines(screen, color, False, pts, 2)
        pygame.draw.circle(screen, color, (bx, by), 3)

    def _draw_context_menu(self, screen):
        items = []
        has_target = self.context_menu_path is not None
        top_level = has_target and len(self.context_menu_path) == 1
        if has_target:
            items.append(("ctx_edit", "Edit"))
            if top_level:
                items.append(("ctx_duplicate", "Duplicate"))
                if self.context_menu_from_list:
                    items.append(("ctx_add_below", "Add item below  >"))
            else:
                items.append(("ctx_unlink", "Unlink"))
            items.append(("ctx_delete", "Delete"))
        # Reset is a view action, so it is available on the visible main canvas.
        # Adding still needs a valid template coordinate under the cursor.
        on_template = self.last_bg_rect.collidepoint(self.context_menu_pos)
        on_canvas_view = on_template
        if self.canvas_context == "main":
            on_canvas_view = self.canvas_view_rect.collidepoint(self.context_menu_pos)
        if on_canvas_view and self.canvas_context == "main":
            items.append(("ctx_reset_view", "Reset view"))
        if on_template:
            items.append(("ctx_add", "Add item  >"))
        w, rh = 160, 30
        mx, my = self.context_menu_pos
        h = len(items) * rh + 8
        mx = min(mx, screen.get_width() - w - 4)
        my = min(my, screen.get_height() - h - 4)
        menu = pygame.Rect(mx, my, w, h)
        self._draw_card(screen, menu, (20, 24, 34), border_color=self.COLORS["gold"], radius=6)
        self.context_menu_buttons = {}
        y = menu.y + 4
        add_row = None
        for key, label in items:
            row = pygame.Rect(menu.x + 4, y, menu.w - 8, rh - 2)
            self.context_menu_buttons[key] = row
            if key in ("ctx_add", "ctx_add_below"):
                add_row = row
            hov = row.collidepoint(pygame.mouse.get_pos())
            active_add = (
                (key == "ctx_add" and self.context_add_mode == "canvas")
                or (key == "ctx_add_below" and self.context_add_mode == "below")
            )
            highlighted = hov or (active_add and self.context_add_open)
            if highlighted:
                pygame.draw.rect(screen, (48, 54, 72), row)
                pygame.draw.rect(screen, self.COLORS["gold"], row, 1)
            color = self.COLORS["red"] if key == "ctx_delete" else self.COLORS["line_light"]
            if highlighted and key != "ctx_delete":
                color = self.COLORS["gold"]
            self._text(screen, label, (row.x + 12, row.y + 5), 15, color)
            y += rh

        # Kind submenu
        if self.context_add_open and add_row is not None:
            kinds = self._available_item_kinds()
            srh = 26
            longest_kind = max((self._render_ui_text(kind, 14).get_width() for kind in kinds), default=140)
            sw = min(max(170, longest_kind + 28), screen.get_width() - 8)
            sh = len(kinds) * srh + 8
            sx = menu.right + 2
            if sx + sw > screen.get_width() - 4:
                sx = menu.x - sw - 2
            sx = max(4, min(sx, screen.get_width() - sw - 4))
            sy = min(add_row.y, screen.get_height() - sh - 4)
            sub = pygame.Rect(sx, sy, sw, sh)
            self._draw_card(screen, sub, (24, 28, 40), border_color=self.COLORS["gold"], radius=6)
            ky = sub.y + 4
            for kind in kinds:
                krow = pygame.Rect(sub.x + 4, ky, sub.w - 8, srh - 2)
                self.context_menu_buttons[f"ctxkind_{kind}"] = krow
                hovered = krow.collidepoint(pygame.mouse.get_pos())
                if hovered:
                    pygame.draw.rect(screen, (48, 54, 72), krow)
                    pygame.draw.rect(screen, self.COLORS["gold"], krow, 1)
                color = self.COLORS["gold"] if hovered else self.COLORS["line_light"]
                self._text(screen, kind, (krow.x + 10, krow.y + 4), 14, color)
                ky += srh

    def _draw_position_pick(self, screen):
        item = self._selected_item()
        # Preview the dragged item at the mouse position on the canvas
        mx, my = pygame.mouse.get_pos()
        if item and self.last_bg_rect.collidepoint((mx, my)):
            icon = self._get_icon_surface(item["row"], item["column"], item.get("sheet"))
            if icon:
                sheet = self._sheet_by_name(item.get("sheet")) or self.active_sheet
                scale = self.last_bg_rect.w / self._canvas_size()[0]
                cw = (sheet["cell_w"] if sheet else 32) * scale
                ch = (sheet["cell_h"] if sheet else 32) * scale
                sized = pygame.transform.smoothscale(icon, (max(1, int(cw)), max(1, int(ch))))
                screen.blit(sized, (mx - sized.get_width() // 2, my - sized.get_height() // 2))
                pygame.draw.rect(screen, self.COLORS["gold"],
                                 (mx - sized.get_width() // 2, my - sized.get_height() // 2,
                                  sized.get_width(), sized.get_height()), 2)
        banner = pygame.Rect(self.canvas_rect.x, self.canvas_rect.y, self.canvas_rect.w, 30)
        pygame.draw.rect(screen, (40, 46, 62), banner)
        pygame.draw.rect(screen, self.COLORS["gold"], banner, 1)
        self._text_center(screen, "Click on the canvas to place the item  -  Esc to cancel", banner, 15, self.COLORS["gold"])

    def _draw_submenu_info_panel(self, screen, panel, x, y, pad):
        item = self.submenu_parent or {}
        name_rect = pygame.Rect(x, y, panel.w - pad * 2, 58)
        self._draw_card(screen, name_rect, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        self._text(screen, "EDITING", (name_rect.x + 10, name_rect.y + 6), 12, self.COLORS["gold"])
        display = item.get("name", item.get("kind", "Item"))
        if len(display) > 22:
            display = display[:19] + "..."
        self._text(screen, display, (name_rect.x + 10, name_rect.y + 25), 18, self.COLORS["line_light"])
        y = name_rect.bottom + 14

        bg_rect = pygame.Rect(x, y, panel.w - pad * 2, 44)
        self._draw_card(screen, bg_rect, self.COLORS["panel_alt"], border_color=(56, 62, 76), radius=8)
        self.info_buttons["submenu_background"] = bg_rect
        self._text(screen, "BACKGROUND", (bg_rect.x + 10, bg_rect.y + 6), 12, self.COLORS["gold"])
        bg_name = item.get("Background") or "None"
        if len(bg_name) > 24:
            bg_name = bg_name[:21] + "..."
        self._text(screen, bg_name, (bg_rect.x + 10, bg_rect.y + 24), 15, self.COLORS["line_light"])
        y = bg_rect.bottom + 10

        for key, label, color in [
            ("submenu_back", "Back to template", (70, 74, 86)),
        ]:
            btn = pygame.Rect(x, y, panel.w - pad * 2, 44)
            self.info_buttons[key] = btn
            self._draw_button(screen, btn, label, color, hover=(self.hover_key == key))
            y += 54

        size = self._canvas_size()
        infos = [
            ("Dimensions", f"{size[0]} x {size[1]}", None),
            ("Choices inside" if item.get("kind") == "MultipleChoiceItem" else "Items inside", str(len(self.placed_items)), None),
        ]
        if item.get("kind") in ("SubMenuItem", "MultipleChoiceItem"):
            infos.extend([
                ("Counter", "active" if item.get("ShowNumbersOfItemsActive") else "off", "submenu_counter"),
                ("Checked count", "active" if item.get("ShowNumberOfCheckedItems") else "off", "submenu_checked_counter"),
            ])
        value_x = x + 112
        for label, value, key in infos:
            row = pygame.Rect(x, y - 4, panel.w - pad * 2, 24)
            if key:
                self.info_buttons[key] = row
                hovered = self.hover_key == key
                if hovered:
                    pygame.draw.rect(screen, self.COLORS["panel_alt"], row)
            self._text(screen, label, (x, y), 13, self.COLORS["muted"])
            self._text(screen, value, (value_x, y), 15, self.COLORS["line_light"])
            y += 26
