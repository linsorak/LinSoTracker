import ast

import pygame


HAS_INPUT = {"and", "or", "not", "output"}
HAS_OUTPUT = {"and", "or", "not", "have", "do", "rules", "bool", "raw"}
LEAF_FNS = ("have", "do", "rules")
NODE_W = 180
NODE_H = 58
PORT_R = 9


class CondBuilderMixin:
    """Node-graph editor (Blueprint style) for ActionsConditions logic.

    Nodes (have/do/and/or/not + a fixed OUTPUT) are wired output->input. The
    expression is regenerated from the graph; on open an existing expression is
    parsed and auto-laid-out into nodes."""

    # ---- open / parse ----------------------------------------------------
    def _open_cond_builder(self, name=None):
        expr = self.maps_extra.get("ActionsConditions", {}).get(name, "") if name else ""
        self._open_cond_graph(expr, title=name, sink=None)
        self.cond_builder_name = name

    def _open_cond_graph(self, initial_expr, title, sink):
        """Generic entry: edit `initial_expr` as a graph; on save call `sink(expr)`
        (or, when sink is None, write to ActionsConditions by name)."""
        self.cond_builder_open = True
        self.cond_builder_name = title
        self.cond_builder_sink = sink
        self.cond_builder_mode = None
        self.cond_pick_target = None
        self.cg_drag_node = None
        self.cg_drag_wire_src = None
        self.cg_wire_end = None
        self.cg_pan = [0, 0]
        self.cg_zoom = 1.0
        self.cg_panning = False
        self.cond_builder_scroll = 0
        self._build_graph_from_expr(initial_expr)
        self._cg_fit_view()

    def _cg_fit_view(self):
        if not self.cg_nodes:
            return
        screen = pygame.display.get_surface()
        if screen is None:
            return
        _, canvas = self._cg_area(screen)
        minx = min(n["x"] for n in self.cg_nodes)
        miny = min(n["y"] for n in self.cg_nodes)
        maxx = max(n["x"] + NODE_W for n in self.cg_nodes)
        maxy = max(n["y"] + NODE_H for n in self.cg_nodes)
        w = max(1, maxx - minx); h = max(1, maxy - miny)
        margin = 30
        zoom = min((canvas.w - margin * 2) / w, (canvas.h - margin * 2) / h, 1.0)
        zoom = max(0.4, zoom)
        self.cg_zoom = zoom
        # center the graph in the canvas
        self.cg_pan[0] = int((canvas.w - w * zoom) / 2 - minx * zoom)
        self.cg_pan[1] = int((canvas.h - h * zoom) / 2 - miny * zoom)

    def _cg_new(self, ntype, value=None, x=0, y=0):
        nid = self.cg_next_id
        self.cg_next_id += 1
        self.cg_nodes.append({"id": nid, "type": ntype, "value": value, "x": x, "y": y})
        return nid

    def _cg_by_id(self, nid):
        for n in self.cg_nodes:
            if n["id"] == nid:
                return n
        return None

    def _build_graph_from_expr(self, expr):
        self.cg_nodes = []
        self.cg_links = []
        self.cg_next_id = 0
        out = self._cg_new("output", x=760, y=180)
        tree = None
        expr = str(expr or "").strip()
        if expr:
            try:
                tree = self._ast_to_node(ast.parse(expr, mode="eval").body)
            except Exception:
                tree = {"type": "raw", "value": expr}
        if tree:
            self._leaf_y = 24
            self._cg_by_id(out)["_depth"] = 0
            child, cy = self._tree_to_nodes(tree, depth=1)
            self.cg_links.append({"src": child, "dst": out})
            self._cg_by_id(out)["y"] = int(cy - NODE_H / 2)
            # assign columns by depth: leaves on the left, OUTPUT on the right
            colw = NODE_W + 90
            maxd = max((n.get("_depth", 0) for n in self.cg_nodes), default=0)
            for n in self.cg_nodes:
                n["x"] = 40 + (maxd - n.get("_depth", 0)) * colw
                n.pop("_depth", None)

    def _ast_to_node(self, n):
        if isinstance(n, ast.BoolOp):
            t = "and" if isinstance(n.op, ast.And) else "or"
            return {"type": t, "children": [self._ast_to_node(v) for v in n.values]}
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            return {"type": "not", "child": self._ast_to_node(n.operand)}
        if isinstance(n, ast.Constant) and isinstance(n.value, bool):
            return {"type": "bool", "value": n.value}
        if isinstance(n, ast.Call) and isinstance(getattr(n, "func", None), ast.Name) \
                and n.func.id in LEAF_FNS and n.args:
            a0 = n.args[0]
            value = str(a0.value if isinstance(a0, ast.Constant) else "")
            node = {"type": n.func.id, "value": value}
            if n.func.id == "have" and len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
                node["count"] = str(n.args[1].value)
            return node
        try:
            return {"type": "raw", "value": ast.unparse(n)}
        except Exception:
            return {"type": "raw", "value": ""}

    def _tree_to_nodes(self, node, depth):
        """Place a node tree, leaves stacked vertically, group/not nodes centered
        on their children. Returns (node_id, center_y). Columns are spaced wider
        than a node so nothing overlaps."""
        t = node["type"]
        if t in ("have", "do", "rules", "bool", "raw"):
            cy = self._leaf_y + NODE_H / 2
            nid = self._cg_new(t, node.get("value", ""), 0, self._leaf_y)
            self._cg_by_id(nid)["_depth"] = depth
            if t == "have" and node.get("count"):
                self._cg_by_id(nid)["count"] = node["count"]
            self._leaf_y += NODE_H + 22
            return nid, cy
        if t == "not":
            child, cy = self._tree_to_nodes(node["child"], depth + 1)
            nid = self._cg_new("not", None, 0, int(cy - NODE_H / 2))
            self._cg_by_id(nid)["_depth"] = depth
            self.cg_links.append({"src": child, "dst": nid})
            return nid, cy
        centers = []
        children_ids = []
        for c in node.get("children", []):
            cid, cy = self._tree_to_nodes(c, depth + 1)
            children_ids.append(cid)
            centers.append(cy)
        mid = sum(centers) / len(centers) if centers else self._leaf_y
        nid = self._cg_new(t, None, 0, int(mid - NODE_H / 2))
        self._cg_by_id(nid)["_depth"] = depth
        for cid in children_ids:
            self.cg_links.append({"src": cid, "dst": nid})
        return nid, mid

    # ---- expression generation ------------------------------------------
    def _cond_expr(self):
        outs = [n for n in self.cg_nodes if n["type"] == "output"]
        return self._expr_of(outs[0]["id"], set()) if outs else ""

    def _expr_of(self, nid, visited):
        if nid in visited:
            return ""
        visited = visited | {nid}
        node = self._cg_by_id(nid)
        if not node:
            return ""
        t = node["type"]
        if t == "have":
            count = node.get("count")
            if count:
                return f"have('{node.get('value', '')}', '{count}')"
            return f"have('{node.get('value', '')}')"
        if t in ("do", "rules"):
            return f"{t}('{node.get('value', '')}')"
        if t == "bool":
            return "True" if node.get("value") else "False"
        if t == "raw":
            return node.get("value", "")
        incoming = sorted((l["src"] for l in self.cg_links if l["dst"] == nid),
                          key=lambda s: (self._cg_by_id(s) or {}).get("y", 0))
        if t == "output":
            return self._expr_of(incoming[0], visited) if incoming else ""
        if t == "not":
            inner = self._expr_of(incoming[0], visited) if incoming else ""
            return f"not({inner})" if inner else ""
        parts = [self._expr_of(s, visited) for s in incoming]
        parts = [p for p in parts if p]
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        return "(" + f" {t} ".join(parts) + ")"

    def _save_cond_builder(self):
        expr = self._cond_expr()
        # Generic sink (e.g. a check's Conditions) takes the expression directly
        if self.cond_builder_sink is not None:
            self.cond_builder_sink(expr)
            self.cond_builder_open = False
            self.cond_builder_sink = None
            self.message = "Condition saved."
            return
        # ActionsConditions mode (by name)
        if not self.cond_builder_name:
            def cb(name):
                if name:
                    self.cond_builder_name = name
                    self.maps_extra.setdefault("ActionsConditions", {})[name] = expr
                    self.cond_builder_open = False
                    self.message = f"Action '{name}' saved."
            self._open_text_prompt("Action name", "", cb, allow_empty=False, label="do('NAME'):")
            return
        self.maps_extra.setdefault("ActionsConditions", {})[self.cond_builder_name] = expr
        self.cond_builder_open = False
        self.message = f"Action '{self.cond_builder_name}' saved."

    def _cond_item_names(self):
        names, seen = [], set()
        for it in self._iter_all_items(self.main_items):
            n = it.get("name")
            if n and n not in seen:
                seen.add(n)
                names.append(n)
        return sorted(names)

    def _cond_action_names(self):
        return sorted(k for k in self.maps_extra.get("ActionsConditions", {}) if k != self.cond_builder_name)

    def _cond_rule_names(self):
        return sorted({r.get("Name", "") for r in self.maps_extra.get("RulesOptions", []) if r.get("Name")})

    def _picker_names(self):
        if self.cond_builder_mode == "have":
            return self._cond_item_names()
        if self.cond_builder_mode == "rules":
            return self._cond_rule_names()
        return self._cond_action_names()

    # ---- geometry --------------------------------------------------------
    def _cg_area(self, screen):
        sw, sh = screen.get_size()
        w = min(1180, sw - 80)
        h = min(820, sh - 80)
        modal = pygame.Rect((sw - w) // 2, (sh - h) // 2, w, h)
        canvas = pygame.Rect(modal.x + 16, modal.y + 104, modal.w - 32, modal.h - 162)
        return modal, canvas

    def _node_rect(self, canvas, node):
        z = self.cg_zoom
        return pygame.Rect(int(canvas.x + self.cg_pan[0] + node["x"] * z),
                           int(canvas.y + self.cg_pan[1] + node["y"] * z),
                           int(NODE_W * z), int(NODE_H * z))

    def _in_port(self, canvas, node):
        r = self._node_rect(canvas, node)
        return (r.x, r.centery)

    def _out_port(self, canvas, node):
        r = self._node_rect(canvas, node)
        return (r.right, r.centery)

    # ---- drawing ---------------------------------------------------------
    def _draw_cond_builder(self, screen):
        sw, sh = screen.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        screen.blit(overlay, (0, 0))
        modal, canvas = self._cg_area(screen)
        self._draw_popup(screen, modal, radius=12)
        self.cond_builder_buttons = {}
        self.cond_builder_rows = {}
        pad = 18
        title = f"Condition: {self.cond_builder_name}" if self.cond_builder_name else "New condition"
        self._text(screen, title, (modal.x + pad, modal.y + 14), 24, self.COLORS["gold"])
        # live expression
        self._text(screen, (self._cond_expr() or "(empty)")[:120], (modal.x + pad, modal.y + 46), 16, self.COLORS["green"])
        self._text(screen, "drag port->port to link  -  click a wire to cut  -  drag node to move",
                   (modal.x + 360, modal.y + 20), 12, self.COLORS["muted"])

        # palette
        px = modal.x + pad
        for key, lbl, col in (("pal_have", "+ item", (36, 124, 87)), ("pal_do", "+ cond", (40, 90, 150)),
                              ("pal_rules", "+ rule", (150, 120, 40)),
                              ("pal_and", "+ AND", (95, 70, 135)), ("pal_or", "+ OR", (95, 70, 135)),
                              ("pal_not", "+ NOT", (150, 70, 90)),
                              ("pal_true", "+ True", (60, 90, 90)), ("pal_false", "+ False", (60, 90, 90))):
            b = pygame.Rect(px, modal.y + 72, 108, 30)
            self.cond_builder_buttons[key] = b
            self._draw_button(screen, b, lbl, col, hover=(self.hover_modal_key == key))
            px += 112

        if self.cond_builder_mode in ("have", "do"):
            self._draw_cond_picker(screen, modal, canvas)
        else:
            self._draw_graph(screen, canvas)

        save = pygame.Rect(modal.right - pad - 110, modal.bottom - 44, 110, 30)
        cancel = pygame.Rect(modal.x + pad, modal.bottom - 44, 110, 30)
        self.cond_builder_buttons["cond_save"] = save
        self.cond_builder_buttons["cond_cancel"] = cancel
        self._draw_button(screen, save, "Save", (36, 124, 87), hover=(self.hover_modal_key == "cond_save"))
        self._draw_button(screen, cancel, "Cancel", self.COLORS["red"], hover=(self.hover_modal_key == "cond_cancel"))

    def _draw_graph(self, screen, canvas):
        pygame.draw.rect(screen, (10, 12, 18), canvas)
        pygame.draw.rect(screen, (56, 62, 76), canvas, 1)
        prev = screen.get_clip()
        screen.set_clip(canvas)
        # wires
        for link in self.cg_links:
            src = self._cg_by_id(link["src"]); dst = self._cg_by_id(link["dst"])
            if not src or not dst:
                continue
            a = self._out_port(canvas, src); b = self._in_port(canvas, dst)
            self._draw_wire(screen, a, b, self.COLORS["gold"])
        if self.cg_drag_wire_src is not None and self.cg_wire_end:
            src = self._cg_by_id(self.cg_drag_wire_src)
            if src:
                self._draw_wire(screen, self._out_port(canvas, src), self.cg_wire_end, self.COLORS["green"])
        # nodes
        colors = {"output": (60, 66, 82), "and": (95, 70, 135), "or": (95, 70, 135),
                  "not": (150, 70, 90), "have": (28, 90, 55), "do": (28, 60, 110),
                  "rules": (120, 95, 30), "bool": (60, 90, 90), "raw": (80, 80, 80)}
        z = self.cg_zoom
        pr = max(4, int(PORT_R * z))
        for node in self.cg_nodes:
            r = self._node_rect(canvas, node)
            pygame.draw.rect(screen, colors.get(node["type"], (70, 74, 86)), r, border_radius=max(2, int(6 * z)))
            pygame.draw.rect(screen, self.COLORS["line_light"], r, 1, border_radius=max(2, int(6 * z)))
            if node["type"] in LEAF_FNS:
                self._text(screen, node["type"], (r.x + int(12 * z), r.y + int(5 * z)), max(9, int(13 * z)), self.COLORS["muted"])
                val = str(node.get("value") or "(click to set)")
                if node["type"] == "have" and node.get("count"):
                    val = f"{val} {node['count']}"
                self._text(screen, val[:18], (r.x + int(12 * z), r.y + int(24 * z)), max(11, int(18 * z)), self.COLORS["line_light"])
                if node["type"] == "have":
                    cb = pygame.Rect(r.right - int(34 * z), r.bottom - int(20 * z), int(30 * z), int(16 * z))
                    self.cond_builder_rows[f"count_{node['id']}"] = (cb, node["id"])
                    pygame.draw.rect(screen, (40, 70, 50), cb)
                    self._text(screen, "#", (cb.x + int(8 * z), cb.y), max(9, int(12 * z)), self.COLORS["line_light"])
            elif node["type"] == "bool":
                self._text(screen, "TRUE" if node.get("value") else "FALSE",
                           (r.x + int(12 * z), r.y + int(16 * z)), max(11, int(20 * z)), self.COLORS["line_light"])
            else:
                label = "OUTPUT" if node["type"] == "output" else (
                    f"raw: {node.get('value','')}" if node["type"] == "raw" else node["type"].upper())
                self._text(screen, label[:20], (r.x + int(12 * z), r.y + int(16 * z)), max(11, int(20 * z)), self.COLORS["line_light"])
            if node["type"] in HAS_INPUT:
                ip = self._in_port(canvas, node)
                pygame.draw.circle(screen, (220, 220, 220), ip, pr)
                pygame.draw.circle(screen, (0, 0, 0), ip, pr, 1)
            if node["type"] in HAS_OUTPUT:
                op = self._out_port(canvas, node)
                pygame.draw.circle(screen, self.COLORS["gold"], op, pr)
                pygame.draw.circle(screen, (0, 0, 0), op, pr, 1)
            if node["type"] != "output":
                xs = max(14, int(16 * z))
                xb = pygame.Rect(r.right - xs - 2, r.y + 2, xs, xs)
                self.cond_builder_rows[f"del_{node['id']}"] = (xb, node["id"])
                self._text(screen, "x", (xb.x + 4, xb.y), max(11, int(13 * z)), self.COLORS["red"])
        screen.set_clip(prev)

    @staticmethod
    def _wire_points(a, b):
        midx = (a[0] + b[0]) // 2
        return [a, (midx, a[1]), (midx, b[1]), b]

    def _draw_wire(self, screen, a, b, color):
        pts = self._wire_points(a, b)
        pygame.draw.lines(screen, color, False, pts, 2)
        pygame.draw.circle(screen, color, b, 3)

    def _draw_cond_picker(self, screen, modal, canvas):
        names = self._picker_names()
        what = {"have": "an item", "do": "a condition", "rules": "a rule option"}.get(self.cond_builder_mode, "")
        self._text(screen, "Pick " + what, (canvas.x, canvas.y - 16), 14, self.COLORS["gold"])
        back = pygame.Rect(canvas.right - 90, canvas.y - 20, 90, 22)
        self.cond_builder_buttons["picker_back"] = back
        self._draw_button(screen, back, "Back", (70, 74, 86), hover=(self.hover_modal_key == "picker_back"))
        pygame.draw.rect(screen, (10, 12, 18), canvas)
        pygame.draw.rect(screen, (56, 62, 76), canvas, 1)
        view = canvas.inflate(-8, -8)
        row_h = 28
        content_h = len(names) * row_h
        max_scroll = max(0, content_h - view.h)
        self.cond_builder_scroll = max(0, min(self.cond_builder_scroll, max_scroll))
        self.cond_builder_max_scroll = max_scroll
        prev = screen.get_clip()
        screen.set_clip(view)
        for i, name in enumerate(names):
            ry = view.y + i * row_h - self.cond_builder_scroll
            if ry + row_h < view.y or ry > view.bottom:
                continue
            row = pygame.Rect(view.x, ry, view.w, row_h - 2)
            self.cond_builder_rows[f"pick_{i}"] = (row, name)
            if self.hover_modal_key == f"pick_{i}":
                pygame.draw.rect(screen, self.COLORS["panel_alt"], row)
            self._text(screen, name, (row.x + 8, row.y + 5), 14, self.COLORS["line_light"])
        screen.set_clip(prev)
        track = pygame.Rect(canvas.right - 7, view.y, 4, view.h)
        self._register_scrollbar(screen, "cond_builder", track, self.cond_builder_scroll, max_scroll, content_h, view.h)

    # ---- interaction helpers (called from input plumbing) ---------------
    def _cg_port_at(self, mouse_position, which):
        screen = pygame.display.get_surface()
        _, canvas = self._cg_area(screen)
        for node in self.cg_nodes:
            if which == "out" and node["type"] in HAS_OUTPUT:
                p = self._out_port(canvas, node)
            elif which == "in" and node["type"] in HAS_INPUT:
                p = self._in_port(canvas, node)
            else:
                continue
            if (mouse_position[0] - p[0]) ** 2 + (mouse_position[1] - p[1]) ** 2 <= (PORT_R + 4) ** 2:
                return node["id"]
        return None

    def _cg_node_body_at(self, mouse_position):
        screen = pygame.display.get_surface()
        _, canvas = self._cg_area(screen)
        for node in reversed(self.cg_nodes):
            if self._node_rect(canvas, node).collidepoint(mouse_position):
                return node["id"]
        return None

    def _cg_start_drag(self, mouse_position):
        if self.cond_builder_mode is not None:
            return False
        screen = pygame.display.get_surface()
        _, canvas = self._cg_area(screen)
        src = self._cg_port_at(mouse_position, "out")
        if src is not None:
            self.cg_drag_wire_src = src
            self.cg_wire_end = mouse_position
            self.suppress_next_click = True
            return True
        nid = self._cg_node_body_at(mouse_position)
        if nid is not None:
            r = self._node_rect(canvas, self._cg_by_id(nid))
            self.cg_drag_node = nid
            self.cg_drag_offset = (mouse_position[0] - r.x, mouse_position[1] - r.y)
            self.suppress_next_click = True
            return True
        # empty canvas -> pan
        if canvas.collidepoint(mouse_position):
            self.cg_panning = True
            self.cg_pan_start = mouse_position
            self.cg_pan_origin = list(self.cg_pan)
            self.suppress_next_click = True
            return True
        return False

    def _cg_drag_move(self, mouse_position):
        screen = pygame.display.get_surface()
        _, canvas = self._cg_area(screen)
        z = self.cg_zoom
        if self.cg_drag_node is not None:
            node = self._cg_by_id(self.cg_drag_node)
            if node:
                node["x"] = (mouse_position[0] - self.cg_drag_offset[0] - canvas.x - self.cg_pan[0]) / z
                node["y"] = (mouse_position[1] - self.cg_drag_offset[1] - canvas.y - self.cg_pan[1]) / z
            return True
        if self.cg_drag_wire_src is not None:
            self.cg_wire_end = mouse_position
            return True
        if self.cg_panning:
            self.cg_pan[0] = self.cg_pan_origin[0] + (mouse_position[0] - self.cg_pan_start[0])
            self.cg_pan[1] = self.cg_pan_origin[1] + (mouse_position[1] - self.cg_pan_start[1])
            return True
        return False

    def _cg_drag_end(self, mouse_position):
        if self.cg_drag_wire_src is not None:
            dst = self._cg_port_at(mouse_position, "in")
            if dst is not None and dst != self.cg_drag_wire_src:
                self._cg_connect(self.cg_drag_wire_src, dst)
            self.cg_drag_wire_src = None
            self.cg_wire_end = None
        self.cg_drag_node = None
        self.cg_panning = False

    def _cg_zoom_at(self, direction, pos):
        screen = pygame.display.get_surface()
        _, canvas = self._cg_area(screen)
        old = self.cg_zoom
        new = max(0.4, min(2.5, old * (1.15 if direction > 0 else 1 / 1.15)))
        if abs(new - old) < 1e-6:
            return
        # keep the world point under the cursor fixed
        wx = (pos[0] - canvas.x - self.cg_pan[0]) / old
        wy = (pos[1] - canvas.y - self.cg_pan[1]) / old
        self.cg_zoom = new
        self.cg_pan[0] = pos[0] - canvas.x - wx * new
        self.cg_pan[1] = pos[1] - canvas.y - wy * new

    def _cg_spawn_xy(self):
        screen = pygame.display.get_surface()
        _, canvas = self._cg_area(screen)
        z = self.cg_zoom
        wx = (canvas.w * 0.3 - self.cg_pan[0]) / z
        wy = (canvas.h * 0.4 - self.cg_pan[1]) / z
        return int(wx), int(wy + 20 * len(self.cg_nodes) % 120)

    def _cg_connect(self, src, dst):
        node = self._cg_by_id(dst)
        if not node:
            return
        # single-input nodes replace their incoming link
        if node["type"] in ("not", "output"):
            self.cg_links = [l for l in self.cg_links if l["dst"] != dst]
        # avoid duplicate
        if not any(l["src"] == src and l["dst"] == dst for l in self.cg_links):
            self.cg_links.append({"src": src, "dst": dst})

    # ---- click handling --------------------------------------------------
    def _handle_cond_builder_click(self, mouse_position):
        # picker mode
        if self.cond_builder_mode in LEAF_FNS:
            for key, (row, name) in self.cond_builder_rows.items():
                if key.startswith("pick_") and row.collidepoint(mouse_position):
                    if self.cond_pick_target is not None:
                        n = self._cg_by_id(self.cond_pick_target)
                        if n:
                            n["value"] = name
                    self.cond_builder_mode = None
                    self.cond_pick_target = None
                    return True
            if self.cond_builder_buttons.get("picker_back") and \
                    self.cond_builder_buttons["picker_back"].collidepoint(mouse_position):
                self.cond_builder_mode = None
            return True
        # palette + save/cancel
        screen = pygame.display.get_surface()
        modal, canvas = self._cg_area(screen)
        for key, rect in self.cond_builder_buttons.items():
            if not rect.collidepoint(mouse_position):
                continue
            if key == "cond_save":
                self._save_cond_builder()
            elif key == "cond_cancel":
                self.cond_builder_open = False
            elif key == "pal_have":
                sx, sy = self._cg_spawn_xy(); self._cg_new("have", "", sx, sy); self._enter_value_pick_latest("have")
            elif key == "pal_do":
                sx, sy = self._cg_spawn_xy(); self._cg_new("do", "", sx, sy); self._enter_value_pick_latest("do")
            elif key == "pal_rules":
                sx, sy = self._cg_spawn_xy(); self._cg_new("rules", "", sx, sy); self._enter_value_pick_latest("rules")
            elif key == "pal_and":
                sx, sy = self._cg_spawn_xy(); self._cg_new("and", None, sx, sy)
            elif key == "pal_or":
                sx, sy = self._cg_spawn_xy(); self._cg_new("or", None, sx, sy)
            elif key == "pal_not":
                sx, sy = self._cg_spawn_xy(); self._cg_new("not", None, sx, sy)
            elif key == "pal_true":
                sx, sy = self._cg_spawn_xy(); self._cg_new("bool", True, sx, sy)
            elif key == "pal_false":
                sx, sy = self._cg_spawn_xy(); self._cg_new("bool", False, sx, sy)
            return True
        # delete + count buttons on nodes
        for key, (rect, nid) in self.cond_builder_rows.items():
            if key.startswith("del_") and rect.collidepoint(mouse_position):
                self.cg_nodes = [n for n in self.cg_nodes if n["id"] != nid]
                self.cg_links = [l for l in self.cg_links if l["src"] != nid and l["dst"] != nid]
                return True
            if key.startswith("count_") and rect.collidepoint(mouse_position):
                self._edit_have_count(nid)
                return True
        # break a link by clicking on its wire
        for link in list(self.cg_links):
            src = self._cg_by_id(link["src"]); dst = self._cg_by_id(link["dst"])
            if not src or not dst:
                continue
            a = self._out_port(canvas, src); b = self._in_port(canvas, dst)
            pts = self._wire_points(a, b)
            if any(self._point_seg_dist(mouse_position, pts[k], pts[k + 1]) <= 7 for k in range(len(pts) - 1)):
                self.cg_links.remove(link)
                self.message = "Link removed."
                return True
        # click a have/do node body -> edit value
        nid = self._cg_node_body_at(mouse_position)
        if nid is not None:
            node = self._cg_by_id(nid)
            if node and node["type"] in LEAF_FNS:
                self._open_value_picker_for(nid, node["type"])
        return True

    @staticmethod
    def _point_seg_dist(p, a, b):
        px, py = p; ax, ay = a; bx, by = b
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        cx, cy = ax + t * dx, ay + t * dy
        return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5

    def _edit_have_count(self, nid):
        node = self._cg_by_id(nid)
        if not node or node["type"] != "have":
            return

        def cb(value):
            v = (value or "").strip()
            node["count"] = v if v else None
            self.message = "Count condition set." if v else "Count cleared."
        self._open_text_prompt("Count condition", str(node.get("count") or ""), cb,
                               label="e.g. >=4  ==2  <=1  (blank = none):")

    def _value_names_for(self, kind):
        if kind == "have":
            return self._cond_item_names()
        if kind == "rules":
            return self._cond_rule_names()
        return self._cond_action_names()

    def _open_value_picker_for(self, nid, kind):
        node = self._cg_by_id(nid)
        if not node:
            return
        titles = {"have": "Pick an item", "do": "Pick a condition", "rules": "Pick a rule option"}

        def cb(name):
            node["value"] = name
        self._open_name_picker(titles.get(kind, "Pick"), self._value_names_for(kind), cb)

    def _enter_value_pick_latest(self, kind):
        self._open_value_picker_for(self.cg_nodes[-1]["id"], kind)
