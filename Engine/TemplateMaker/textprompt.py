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
        self.prompt_error = None
        self.prompt_callback = callback
        self.prompt_kind = kind
        self.prompt_allow_empty = allow_empty
        self.prompt_min = minvalue

    def _close_text_prompt(self):
        self.prompt_open = False
        self.prompt_callback = None
        self.prompt_error = None

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

    def _handle_text_prompt_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self._close_text_prompt()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._submit_text_prompt()
        elif event.key == pygame.K_BACKSPACE:
            self.prompt_text = self.prompt_text[:-1]
            self.prompt_error = None
        elif event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
            self.prompt_text += self._prompt_clipboard().strip()
            self.prompt_error = None
        elif event.unicode and event.unicode.isprintable():
            self.prompt_text += event.unicode
            self.prompt_error = None

    def _handle_text_prompt_click(self, mouse_position):
        if self.prompt_ok_rect and self.prompt_ok_rect.collidepoint(mouse_position):
            self._submit_text_prompt()
        elif self.prompt_cancel_rect and self.prompt_cancel_rect.collidepoint(mouse_position):
            self._close_text_prompt()

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

        visible = self.prompt_text
        # ptext not ideal for editable text; use a plain font for the field
        font = pygame.font.Font(None, 30)
        max_w = self.prompt_input_rect.width - 20
        while visible and font.size(visible)[0] > max_w:
            visible = visible[1:]
        tsurf = font.render(visible, True, (20, 20, 20))
        screen.blit(tsurf, (self.prompt_input_rect.x + 10, self.prompt_input_rect.y + 8))
        cx = self.prompt_input_rect.x + 10 + tsurf.get_width() + 1
        pygame.draw.line(screen, (20, 20, 20), (cx, self.prompt_input_rect.y + 8),
                         (cx, self.prompt_input_rect.bottom - 8), 1)

        if self.prompt_error:
            self._text(screen, self.prompt_error, (px + 24, py + 128), 14, self.COLORS["red"])

        bw, bh = 120, 38
        by = py + ph - bh - 20
        self.prompt_cancel_rect = pygame.Rect(px + pw - 24 - bw, by, bw, bh)
        self.prompt_ok_rect = pygame.Rect(self.prompt_cancel_rect.x - bw - 12, by, bw, bh)
        self._draw_button(screen, self.prompt_ok_rect, "OK", (36, 124, 87), hover=False)
        self._draw_button(screen, self.prompt_cancel_rect, "Cancel", (70, 74, 86), hover=False)
