import pygame


class TextPromptMixin:
    """In-app text input overlay (same style as the tracker's import-settings popup).

    Replaces blocking tkinter dialogs. Asynchronous: the caller passes a callback
    that receives the typed value when the user confirms. Sequences are chained
    by opening another prompt from within a callback.
    """

    def _init_text_prompt(self):
        self.prompt_open = False
        self.prompt_title = ""
        self.prompt_label = ""
        self.prompt_text = ""
        self.prompt_cursor = 0
        self.prompt_selection_anchor = 0
        self.prompt_view_start = 0
        self.prompt_selecting = False
        self.prompt_error = None
        self.prompt_callback = None
        self.prompt_kind = "str"
        self.prompt_allow_empty = True
        self.prompt_min = None
        self.prompt_input_rect = None
        self.prompt_ok_rect = None
        self.prompt_cancel_rect = None

    def _open_text_prompt(self, title, initial, callback, kind="str",
                          allow_empty=True, label=None, minvalue=None):
        self.prompt_open = True
        self.prompt_title = title
        self.prompt_label = label or "Enter a value:"
        self.prompt_text = "" if initial is None else str(initial)
        self.prompt_cursor = len(self.prompt_text)
        self.prompt_selection_anchor = 0
        self.prompt_view_start = 0
        self.prompt_selecting = False
        self.prompt_error = None
        self.prompt_callback = callback
        self.prompt_kind = kind
        self.prompt_allow_empty = allow_empty
        self.prompt_min = minvalue

    def _close_text_prompt(self):
        self.prompt_open = False
        self.prompt_callback = None
        self.prompt_error = None
        self.prompt_selecting = False

    def _submit_text_prompt(self):
        raw = self.prompt_text.strip()
        if raw == "" and not self.prompt_allow_empty:
            self.prompt_error = "Value required."
            return
        value = raw
        if self.prompt_kind in ("int", "float") and raw != "":
            try:
                value = int(raw) if self.prompt_kind == "int" else float(raw)
            except ValueError:
                self.prompt_error = "Enter a number."
                return
            if self.prompt_min is not None and value < self.prompt_min:
                self.prompt_error = f"Min {self.prompt_min}."
                return
        elif self.prompt_kind in ("int", "float") and raw == "":
            value = None
        callback = self.prompt_callback
        self._close_text_prompt()
        if callback:
            callback(value)

    @staticmethod
    def _prompt_clipboard():
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            data = pygame.scrap.get(pygame.SCRAP_TEXT)
            if not data:
                return ""
            if isinstance(data, bytes):
                return data.decode("utf-8", errors="ignore").replace("\x00", "")
            return str(data)
        except Exception:
            return ""

    @staticmethod
    def _set_prompt_clipboard(text):
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT, str(text).encode("utf-8"))
        except Exception:
            pass

    def _prompt_selection_range(self):
        start = min(self.prompt_cursor, self.prompt_selection_anchor)
        end = max(self.prompt_cursor, self.prompt_selection_anchor)
        return start, end

    def _prompt_has_selection(self):
        start, end = self._prompt_selection_range()
        return start != end

    def _clear_prompt_selection(self):
        self.prompt_selection_anchor = self.prompt_cursor

    def _delete_prompt_selection(self):
        start, end = self._prompt_selection_range()
        if start == end:
            return False
        self.prompt_text = self.prompt_text[:start] + self.prompt_text[end:]
        self.prompt_cursor = start
        self.prompt_selection_anchor = start
        self.prompt_error = None
        return True

    def _insert_prompt_text(self, text):
        if not text:
            return
        self._delete_prompt_selection()
        self.prompt_text = self.prompt_text[:self.prompt_cursor] + text + self.prompt_text[self.prompt_cursor:]
        self.prompt_cursor += len(text)
        self.prompt_selection_anchor = self.prompt_cursor
        self.prompt_error = None

    def _move_prompt_cursor(self, position, select=False):
        position = max(0, min(len(self.prompt_text), position))
        if not select:
            self.prompt_selection_anchor = position
        elif not self._prompt_has_selection():
            self.prompt_selection_anchor = self.prompt_cursor
        self.prompt_cursor = position

    def _prompt_index_from_x(self, x, font):
        if not self.prompt_input_rect:
            return len(self.prompt_text)
        text_x = self.prompt_input_rect.x + 10
        local_x = max(0, x - text_x)
        text = self.prompt_text
        start = min(self.prompt_view_start, len(text))
        best_index = start
        best_distance = abs(local_x)
        for index in range(start, len(text) + 1):
            width = font.size(text[start:index])[0]
            distance = abs(local_x - width)
            if distance <= best_distance:
                best_distance = distance
                best_index = index
            if width > local_x and distance > best_distance:
                break
        return best_index

    def _prompt_visible_range(self, font, max_width):
        text = self.prompt_text
        self.prompt_view_start = max(0, min(self.prompt_view_start, len(text)))
        if self.prompt_cursor < self.prompt_view_start:
            self.prompt_view_start = self.prompt_cursor
        while self.prompt_view_start < self.prompt_cursor and \
                font.size(text[self.prompt_view_start:self.prompt_cursor])[0] > max_width:
            self.prompt_view_start += 1

        end = self.prompt_view_start
        while end < len(text) and font.size(text[self.prompt_view_start:end + 1])[0] <= max_width:
            end += 1
        return self.prompt_view_start, end

    def _handle_text_prompt_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        ctrl = bool(event.mod & pygame.KMOD_CTRL)
        shift = bool(event.mod & pygame.KMOD_SHIFT)
        if event.key == pygame.K_ESCAPE:
            self._close_text_prompt()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._submit_text_prompt()
        elif ctrl and event.key == pygame.K_a:
            self.prompt_selection_anchor = 0
            self.prompt_cursor = len(self.prompt_text)
        elif ctrl and event.key in (pygame.K_c, pygame.K_x):
            start, end = self._prompt_selection_range()
            if start != end:
                self._set_prompt_clipboard(self.prompt_text[start:end])
                if event.key == pygame.K_x:
                    self._delete_prompt_selection()
        elif ctrl and event.key == pygame.K_v:
            pasted = self._prompt_clipboard().replace("\r", "").replace("\n", "")
            self._insert_prompt_text(pasted)
        elif event.key == pygame.K_LEFT:
            if self._prompt_has_selection() and not shift:
                self._move_prompt_cursor(self._prompt_selection_range()[0])
            else:
                self._move_prompt_cursor(self.prompt_cursor - 1, select=shift)
        elif event.key == pygame.K_RIGHT:
            if self._prompt_has_selection() and not shift:
                self._move_prompt_cursor(self._prompt_selection_range()[1])
            else:
                self._move_prompt_cursor(self.prompt_cursor + 1, select=shift)
        elif event.key == pygame.K_HOME:
            self._move_prompt_cursor(0, select=shift)
        elif event.key == pygame.K_END:
            self._move_prompt_cursor(len(self.prompt_text), select=shift)
        elif event.key == pygame.K_BACKSPACE:
            if not self._delete_prompt_selection() and self.prompt_cursor > 0:
                self.prompt_text = self.prompt_text[:self.prompt_cursor - 1] + self.prompt_text[self.prompt_cursor:]
                self._move_prompt_cursor(self.prompt_cursor - 1)
                self.prompt_error = None
        elif event.key == pygame.K_DELETE:
            if not self._delete_prompt_selection() and self.prompt_cursor < len(self.prompt_text):
                self.prompt_text = self.prompt_text[:self.prompt_cursor] + self.prompt_text[self.prompt_cursor + 1:]
                self.prompt_error = None
        elif event.unicode and event.unicode.isprintable():
            self._insert_prompt_text(event.unicode)

    def _handle_text_prompt_click(self, mouse_position):
        if self.prompt_ok_rect and self.prompt_ok_rect.collidepoint(mouse_position):
            self._submit_text_prompt()
        elif self.prompt_cancel_rect and self.prompt_cancel_rect.collidepoint(mouse_position):
            self._close_text_prompt()

    def _handle_text_prompt_mouse_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.prompt_input_rect and self.prompt_input_rect.collidepoint(event.pos):
                font = pygame.font.Font(None, 30)
                index = self._prompt_index_from_x(event.pos[0], font)
                self.prompt_cursor = index
                self.prompt_selection_anchor = index
                self.prompt_selecting = True
                return True
            return False
        if event.type == pygame.MOUSEMOTION and self.prompt_selecting:
            font = pygame.font.Font(None, 30)
            self.prompt_cursor = self._prompt_index_from_x(event.pos[0], font)
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.prompt_selecting:
            font = pygame.font.Font(None, 30)
            self.prompt_cursor = self._prompt_index_from_x(event.pos[0], font)
            self.prompt_selecting = False
            return True
        return False

    def _draw_text_prompt(self, screen):
        if not self.prompt_open:
            return
        width, height = screen.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        screen.blit(overlay, (0, 0))

        pw = min(640, max(440, int(width * 0.5)))
        ph = 220
        px = (width - pw) // 2
        py = (height - ph) // 2
        rect = pygame.Rect(px, py, pw, ph)
        self._draw_card(screen, rect, (16, 19, 28), border_color=self.COLORS["gold"])

        self._text(screen, self.prompt_title, (px + 24, py + 18), 24, self.COLORS["gold"])
        self._text(screen, self.prompt_label, (px + 24, py + 58), 15, self.COLORS["muted"])

        self.prompt_input_rect = pygame.Rect(px + 24, py + 84, pw - 48, 38)
        pygame.draw.rect(screen, (245, 245, 245), self.prompt_input_rect)
        pygame.draw.rect(screen, self.COLORS["gold"], self.prompt_input_rect, 2)

        # ptext not ideal for editable text; use a plain font for the field
        font = pygame.font.Font(None, 30)
        max_w = self.prompt_input_rect.width - 20
        view_start, view_end = self._prompt_visible_range(font, max_w)
        visible = self.prompt_text[view_start:view_end]

        if self._prompt_has_selection():
            selection_start, selection_end = self._prompt_selection_range()
            draw_start = max(selection_start, view_start)
            draw_end = min(selection_end, view_end)
            if draw_start < draw_end:
                sx = self.prompt_input_rect.x + 10 + font.size(self.prompt_text[view_start:draw_start])[0]
                ex = self.prompt_input_rect.x + 10 + font.size(self.prompt_text[view_start:draw_end])[0]
                selection_rect = pygame.Rect(sx, self.prompt_input_rect.y + 6, ex - sx, self.prompt_input_rect.h - 12)
                pygame.draw.rect(screen, (84, 140, 230), selection_rect)

        tsurf = font.render(visible, True, (20, 20, 20))
        screen.blit(tsurf, (self.prompt_input_rect.x + 10, self.prompt_input_rect.y + 8))
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            cursor_x = self.prompt_input_rect.x + 10 + font.size(
                self.prompt_text[view_start:self.prompt_cursor]
            )[0]
            pygame.draw.line(screen, (20, 20, 20), (cursor_x, self.prompt_input_rect.y + 8),
                             (cursor_x, self.prompt_input_rect.bottom - 8), 1)

        if self.prompt_error:
            self._text(screen, self.prompt_error, (px + 24, py + 128), 14, self.COLORS["red"])

        bw, bh = 120, 38
        by = py + ph - bh - 20
        self.prompt_cancel_rect = pygame.Rect(px + pw - 24 - bw, by, bw, bh)
        self.prompt_ok_rect = pygame.Rect(self.prompt_cancel_rect.x - bw - 12, by, bw, bh)
        self._draw_button(screen, self.prompt_ok_rect, "OK", (36, 124, 87), hover=False)
        self._draw_button(screen, self.prompt_cancel_rect, "Cancel", (70, 74, 86), hover=False)
