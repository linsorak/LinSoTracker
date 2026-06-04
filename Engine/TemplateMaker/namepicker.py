import pygame


class NamePickerMixin:
    """Reusable searchable name picker overlay. Open it with a list of names and
    a callback; the user filters by typing and clicks a row to choose."""

    def _open_name_picker(self, title, names, callback):
        self.name_picker_open = True
        self.name_picker_title = title
        self.name_picker_all = list(names)
        self.name_picker_query = ""
        self.name_picker_scroll = 0
        self.name_picker_max_scroll = 0
        self.name_picker_callback = callback
        self.name_picker_rows = {}
        self.name_picker_buttons = {}

    def _np_filtered(self):
        q = self.name_picker_query.lower().strip()
        if not q:
            return self.name_picker_all
        return [n for n in self.name_picker_all if q in n.lower()]

    def _draw_name_picker(self, screen):
        sw, sh = screen.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))
        modal = pygame.Rect(sw // 2 - 280, sh // 2 - 280, 560, 560)
        self._draw_popup(screen, modal, radius=12)
        self.name_picker_rows = {}
        self.name_picker_buttons = {}
        pad = 18
        x = modal.x + pad
        self._text(screen, self.name_picker_title, (x, modal.y + 14), 22, self.COLORS["gold"])
        close = pygame.Rect(modal.right - pad - 80, modal.y + 14, 80, 26)
        self.name_picker_buttons["close"] = close
        self._draw_button(screen, close, "Cancel", self.COLORS["red"], hover=(self.hover_modal_key == "np_close"))

        # search box
        sb = pygame.Rect(x, modal.y + 50, modal.w - pad * 2, 30)
        pygame.draw.rect(screen, (12, 15, 22), sb)
        pygame.draw.rect(screen, self.COLORS["gold"], sb, 1)
        q = self.name_picker_query or ""
        self._text(screen, ("Search: " + q + "|"), (sb.x + 8, sb.y + 6), 15, self.COLORS["line_light"])

        names = self._np_filtered()
        self._text(screen, f"{len(names)} match(es)", (sb.right - 110, modal.y + 56), 11, self.COLORS["muted"])
        area = pygame.Rect(x, modal.y + 90, modal.w - pad * 2, modal.bottom - (modal.y + 90) - 16)
        self._draw_card(screen, area, (10, 12, 18), border_color=(56, 62, 76), radius=8)
        view = area.inflate(-8, -8)
        row_h = 28
        content_h = len(names) * row_h
        max_scroll = max(0, content_h - view.h)
        self.name_picker_scroll = max(0, min(self.name_picker_scroll, max_scroll))
        self.name_picker_max_scroll = max_scroll
        prev = screen.get_clip()
        screen.set_clip(view)
        if not names:
            self._text_center(screen, "No match", view, 15, self.COLORS["muted"])
        for i, nm in enumerate(names):
            ry = view.y + i * row_h - self.name_picker_scroll
            if ry + row_h < view.y or ry > view.bottom:
                continue
            row = pygame.Rect(view.x, ry, view.w, row_h - 2)
            self.name_picker_rows[i] = (row, nm)
            if self.hover_modal_key == f"np_row_{i}":
                pygame.draw.rect(screen, self.COLORS["panel_alt"], row)
            self._text(screen, nm, (row.x + 8, row.y + 5), 14, self.COLORS["line_light"])
        screen.set_clip(prev)
        track = pygame.Rect(area.right - 7, view.y, 4, view.h)
        self._register_scrollbar(screen, "name_picker", track, self.name_picker_scroll, max_scroll, content_h, view.h)

    def _handle_name_picker_click(self, mouse_position):
        if self.name_picker_buttons.get("close") and self.name_picker_buttons["close"].collidepoint(mouse_position):
            self.name_picker_open = False
            self.name_picker_callback = None
            return True
        for i, (row, nm) in self.name_picker_rows.items():
            if row.collidepoint(mouse_position):
                cb = self.name_picker_callback
                self.name_picker_open = False
                self.name_picker_callback = None
                if cb:
                    cb(nm)
                return True
        return True

    def _name_picker_key(self, event):
        if event.key == pygame.K_ESCAPE:
            self.name_picker_open = False
            self.name_picker_callback = None
        elif event.key == pygame.K_BACKSPACE:
            self.name_picker_query = self.name_picker_query[:-1]
            self.name_picker_scroll = 0
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            names = self._np_filtered()
            if len(names) == 1:
                cb = self.name_picker_callback
                self.name_picker_open = False
                self.name_picker_callback = None
                if cb:
                    cb(names[0])
        elif event.unicode and event.unicode.isprintable():
            self.name_picker_query += event.unicode
            self.name_picker_scroll = 0
