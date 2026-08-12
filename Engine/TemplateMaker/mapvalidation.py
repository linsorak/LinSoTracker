import ast


class MapTemplateValidator:
    """Validate map payloads, which live outside tracker.json."""

    ACTION_TYPES = {
        "SetLeftClick", "SetRightClick", "SetWheelClick", "ResetItem", "SetRule",
    }

    def __init__(self, maps, extras, item_names=()):
        self.maps = maps or []
        self.extras = extras or {}
        self.item_names = set(item_names or ())
        self.errors = []
        self._validate()

    def is_valid(self):
        return not self.errors

    def _error(self, path, message):
        self.errors.append(f"{path}: {message}")

    @staticmethod
    def _is_int(value):
        return isinstance(value, int) and not isinstance(value, bool)

    def _item_count(self, container, path):
        value = container.get("ItemCount", 1)
        if not self._is_int(value) or value < 1:
            self._error(f"{path}.ItemCount", "must be an integer greater than zero")

    def _access_conditions(self, container, path):
        for field in (
                "Conditions", "OutOfLogicConditions",
                "ScoutableConditions", "UncertainConditions"):
            if field in container:
                self._expression(container.get(field), f"{path}.{field}")

    def _dict(self, value, path):
        if not isinstance(value, dict):
            self._error(path, "must be an object")
            return {}
        return value

    def _list(self, value, path):
        if not isinstance(value, list):
            self._error(path, "must be a list")
            return []
        return value

    def _string(self, value, path, allow_empty=True):
        if not isinstance(value, str):
            self._error(path, "must be text")
            return ""
        if not allow_empty and not value.strip():
            self._error(path, "cannot be empty")
        return value

    def _bool(self, value, path):
        if not isinstance(value, bool):
            self._error(path, "must be true or false")

    def _xy(self, value, path):
        value = self._dict(value, path)
        for key in ("x", "y"):
            if not self._is_int(value.get(key)):
                self._error(f"{path}.{key}", "must be an integer")

    def _wh(self, value, path, positive=False):
        value = self._dict(value, path)
        for key in ("w", "h"):
            if not self._is_int(value.get(key)):
                self._error(f"{path}.{key}", "must be an integer")
            elif positive and value[key] <= 0:
                self._error(f"{path}.{key}", "must be greater than zero")

    def _rect(self, value, path):
        value = self._dict(value, path)
        self._xy(value, path)
        self._wh(value, path, positive=True)

    def _dimensions(self, value, path):
        value = self._dict(value, path)
        for key in ("width", "height"):
            if not self._is_int(value.get(key)):
                self._error(f"{path}.{key}", "must be an integer")
            elif value[key] <= 0:
                self._error(f"{path}.{key}", "must be greater than zero")

    def _expression(self, value, path):
        value = self._string(value, path).strip()
        if not value.strip():
            return
        try:
            ast.parse(value, mode="eval")
        except (SyntaxError, ValueError) as exc:
            detail = exc.msg if isinstance(exc, SyntaxError) else str(exc)
            self._error(path, f"invalid condition ({detail})")

    def _arrow(self, value, path):
        value = self._dict(value, path)
        image = value.get("Image")
        if image is not None:
            self._string(image, f"{path}.Image")
        self._xy(value.get("Positions"), f"{path}.Positions")

    def _popup_box(self, value, path):
        value = self._dict(value, path)
        background = value.get("SubMenuBackground")
        if background is not None:
            self._string(background, f"{path}.SubMenuBackground")
        self._rect(value.get("DrawBoxRect"), f"{path}.DrawBoxRect")
        if not self._is_int(value.get("LabelY")):
            self._error(f"{path}.LabelY", "must be an integer")
        self._arrow(value.get("LeftArrow"), f"{path}.LeftArrow")
        self._arrow(value.get("RightArrow"), f"{path}.RightArrow")

    def _validate(self):
        if not self.maps:
            self._error("Maps", "a map template needs at least one map")
            return

        json_files = set()
        block_names = set()
        simple_names = set()
        block_subchecks = {}

        for index, map_model in enumerate(self.maps):
            path = f"Maps[{index}]"
            map_model = self._dict(map_model, path)
            json_file = self._string(map_model.get("json_file"), f"{path}.json_file", False)
            if json_file in json_files:
                self._error(f"{path}.json_file", "must be unique")
            json_files.add(json_file)

            payload = self._dict(map_model.get("data"), f"{path}.data")
            datas = self._dict(payload.get("Datas"), f"{path}.data.Datas")
            self._string(datas.get("Name"), f"{path}.data.Datas.Name", False)
            self._dimensions(datas.get("Dimensions"), f"{path}.data.Datas.Dimensions")
            for key in ("Background", "SubMenuBackground"):
                value = datas.get(key)
                if value is not None:
                    self._string(value, f"{path}.data.Datas.{key}")
            self._rect(datas.get("DrawBoxRect"), f"{path}.data.Datas.DrawBoxRect")
            if datas.get("DrawBoxRectSubTitle") is not None:
                self._rect(datas.get("DrawBoxRectSubTitle"),
                           f"{path}.data.Datas.DrawBoxRectSubTitle")
            if not self._is_int(datas.get("LabelY")):
                self._error(f"{path}.data.Datas.LabelY", "must be an integer")
            self._arrow(datas.get("LeftArrow"), f"{path}.data.Datas.LeftArrow")
            self._arrow(datas.get("RightArrow"), f"{path}.data.Datas.RightArrow")

            checks = self._list(payload.get("ChecksList"), f"{path}.data.ChecksList")
            for check_index, check in enumerate(checks):
                check_path = f"{path}.data.ChecksList[{check_index}]"
                check = self._dict(check, check_path)
                ident = check.get("Id")
                if not self._is_int(ident):
                    self._error(f"{check_path}.Id", "must be an integer")
                kind = self._string(check.get("Kind"), f"{check_path}.Kind", False)
                name = self._string(check.get("Name"), f"{check_path}.Name", False)
                self._xy(check.get("Positions"), f"{check_path}.Positions")
                if check.get("Zone") is not None:
                    self._string(check.get("Zone"), f"{check_path}.Zone")

                if kind == "SimpleCheck":
                    simple_names.add(name)
                    self._item_count(check, check_path)
                    self._access_conditions(check, check_path)
                    if check.get("Group") is not None:
                        self._string(check.get("Group"), f"{check_path}.Group")
                elif kind == "Block":
                    block_names.add(name)
                    sub_names = block_subchecks.setdefault(name, set())
                    for sub_index, subcheck in enumerate(
                            self._list(check.get("Checks"), f"{check_path}.Checks")):
                        sub_path = f"{check_path}.Checks[{sub_index}]"
                        subcheck = self._dict(subcheck, sub_path)
                        sub_id = subcheck.get("Id")
                        if not self._is_int(sub_id):
                            self._error(f"{sub_path}.Id", "must be an integer")
                        sub_name = self._string(subcheck.get("Name"), f"{sub_path}.Name", False)
                        sub_names.add(sub_name)
                        self._item_count(subcheck, sub_path)
                        self._access_conditions(subcheck, sub_path)
                        if subcheck.get("Group") is not None:
                            self._string(subcheck.get("Group"), f"{sub_path}.Group")
                elif kind == "MapPopup":
                    block_names.add(name)
                    self._expression(check.get("VisibleCondition", "True"),
                                     f"{check_path}.VisibleCondition")
                    if check.get("SubMenuBackground") is not None:
                        self._string(check.get("SubMenuBackground"),
                                     f"{check_path}.SubMenuBackground")
                    for item_index, popup_item in enumerate(
                            self._list(check.get("Items"), f"{check_path}.Items")):
                        item_path = f"{check_path}.Items[{item_index}]"
                        popup_item = self._dict(popup_item, item_path)
                        item_name = popup_item.get("Item", popup_item.get("Name"))
                        self._string(item_name, f"{item_path}.Item", False)
                        if self.item_names and item_name not in self.item_names:
                            self._error(f"{item_path}.Item", f"unknown item '{item_name}'")
                        self._xy(popup_item.get("Positions"), f"{item_path}.Positions")
                        scale = popup_item.get("Scale", 1.0)
                        if (not isinstance(scale, (int, float)) or isinstance(scale, bool)
                                or scale <= 0):
                            self._error(f"{item_path}.Scale", "must be a positive number")
                else:
                    self._error(f"{check_path}.Kind", f"unsupported check kind '{kind}'")

        self._wh(self.extras.get("SizeSimpleCheck"), "SizeSimpleCheck", positive=True)
        self._wh(self.extras.get("SizeGroupChecks"), "SizeGroupChecks", positive=True)
        self._xy(self.extras.get("CptChecksPosition"), "CptChecksPosition")

        action_conditions = self._dict(
            self.extras.get("ActionsConditions"), "ActionsConditions")
        for name, expression in action_conditions.items():
            self._string(name, "ActionsConditions name", False)
            self._expression(expression, f"ActionsConditions.{name}")

        rules_lists = self._list(self.extras.get("RulesOptionsLists", []), "RulesOptionsLists")
        rules_list_names = set()
        for index, rules_list in enumerate(rules_lists):
            path = f"RulesOptionsLists[{index}]"
            rules_list = self._dict(rules_list, path)
            name = self._string(rules_list.get("Name"), f"{path}.Name", False)
            if name in rules_list_names:
                self._error(f"{path}.Name", "must be unique")
            rules_list_names.add(name)
            self._rect(rules_list.get("ButtonRect"), f"{path}.ButtonRect")
            self._popup_box(rules_list.get("ListBox"), f"{path}.ListBox")

        rules = self._list(self.extras.get("RulesOptions", []), "RulesOptions")
        rule_names = set()
        for index, rule in enumerate(rules):
            path = f"RulesOptions[{index}]"
            rule = self._dict(rule, path)
            name = self._string(rule.get("Name"), f"{path}.Name")
            rule_names.add(name)
            parent = self._string(rule.get("ParentListName"),
                                  f"{path}.ParentListName", False)
            if parent not in rules_list_names:
                self._error(f"{path}.ParentListName", f"unknown rules list '{parent}'")
            self._bool(rule.get("Active", False), f"{path}.Active")
            self._bool(rule.get("CanBeClickable", True), f"{path}.CanBeClickable")
            if rule.get("ExclusiveGroup") is not None:
                self._string(rule.get("ExclusiveGroup"), f"{path}.ExclusiveGroup")

        for index, rule in enumerate(rules):
            path = f"RulesOptions[{index}]"
            self._validate_rule_actions(rule.get("Actions"), path, rule_names)
            self._validate_hide_checks(
                rule.get("HideChecks"), path, simple_names, block_names, block_subchecks)

        maps_list = self.extras.get("MapsList")
        if maps_list is not None:
            maps_list = self._dict(maps_list, "MapsList")
            self._rect(maps_list.get("MapListButtonLabelRect"),
                       "MapsList.MapListButtonLabelRect")
            self._popup_box(maps_list.get("MapsListBox"), "MapsList.MapsListBox")

    def _validate_rule_actions(self, actions, path, rule_names):
        if actions is None:
            return
        for index, action in enumerate(self._list(actions, f"{path}.Actions")):
            action_path = f"{path}.Actions[{index}]"
            action = self._dict(action, action_path)
            if len(action) != 1:
                self._error(action_path, "must contain exactly one action")
                continue
            action_type, data = next(iter(action.items()))
            if action_type not in self.ACTION_TYPES:
                self._error(action_path, f"unsupported action '{action_type}'")
                continue
            data = self._dict(data, f"{action_path}.{action_type}")
            if action_type == "SetRule":
                target = self._string(data.get("RuleName"),
                                      f"{action_path}.{action_type}.RuleName", False)
                if target not in rule_names:
                    self._error(f"{action_path}.{action_type}.RuleName",
                                f"unknown rule '{target}'")
                self._bool(data.get("Active"), f"{action_path}.{action_type}.Active")
                continue

            item_name = self._string(
                data.get("Item"), f"{action_path}.{action_type}.Item", False)
            if self.item_names and item_name not in self.item_names:
                self._error(f"{action_path}.{action_type}.Item",
                            f"unknown item '{item_name}'")
            if action_type != "ResetItem" and not self._is_int(data.get("Counter")):
                self._error(f"{action_path}.{action_type}.Counter", "must be an integer")

    def _validate_hide_checks(self, hide_checks, path, simple_names, block_names,
                              block_subchecks):
        if hide_checks is None:
            return
        for index, entry in enumerate(self._list(hide_checks, f"{path}.HideChecks")):
            entry_path = f"{path}.HideChecks[{index}]"
            entry = self._dict(entry, entry_path)
            kind = self._string(entry.get("Kind"), f"{entry_path}.Kind", False)
            checks = self._list(entry.get("Checks"), f"{entry_path}.Checks")
            if kind == "SimpleCheck":
                for check_name in checks:
                    self._string(check_name, f"{entry_path}.Checks[]", False)
            elif kind == "Block":
                self._string(entry.get("Name"), f"{entry_path}.Name", False)
                for check_name in checks:
                    self._string(check_name, f"{entry_path}.Checks[]", False)
            else:
                self._error(f"{entry_path}.Kind", f"unsupported hide kind '{kind}'")

