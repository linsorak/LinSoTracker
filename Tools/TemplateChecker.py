class TemplateChecker:
    def __init__(self, template_json_data):
        self.errors = []

        self.ERROR_EXCEPTED_NUMBER_ELEMENTS = "'{}' doesn't contain the expected number of elements"
        self.ERROR_IS_NOT_IN_EXCEPTED_TYPE = "'{}' is not a '{}' type"
        self.ERROR_MISSING_SECTION_IN = "'{}' is missing in '{}'"
        self.ERROR_MISSING_ELEMENT_ON_MAIN_STRUCTURE = "'{}' is missing in the main structure"
        self.ERROR_THE_STRUCTURE_IS_NOT_VALID = "The '{}' structure is not valid"

        self.template_json_data = template_json_data

        self.__validation()

    def is_valid(self):
        if self.errors:
            print(self.errors)
        return not bool(self.errors)

    def __validation(self):
        self.__is_structure_valid()
        self.__is_information_valid()
        self.__is_datas_valid()
        self.__is_fonts_valid()
        self.__is_items_valid()

    def __check_element_is_in_section_and_valid(self, element, section, section_name, needed_type):
        if element in section.keys():
            if not isinstance(section[element], needed_type):
                self.errors.append(self.ERROR_IS_NOT_IN_EXCEPTED_TYPE.format(section_name + "." + element, needed_type))
        else:
            self.errors.append(self.ERROR_MISSING_SECTION_IN.format(element, section_name))

    def __dimension_check(self, element, section, section_name):
        if element in section.keys():
            if len(section[element]) == 2:
                self.__check_element_is_in_section_and_valid("width", section[element], element, int)
                self.__check_element_is_in_section_and_valid("height", section[element], element, int)
            else:
                self.errors.append(self.ERROR_EXCEPTED_NUMBER_ELEMENTS.format(element))
        else:
            self.errors.append(self.ERROR_MISSING_SECTION_IN.format(element, section_name))

    def __color_check(self, element, section, section_name):
        if element in section.keys():
            if len(section[element]) == 3:
                self.__check_element_is_in_section_and_valid("r", section[element], element, int)
                self.__check_element_is_in_section_and_valid("g", section[element], element, int)
                self.__check_element_is_in_section_and_valid("b", section[element], element, int)
            else:
                self.errors.append(self.ERROR_EXCEPTED_NUMBER_ELEMENTS.format(element))
        else:
            self.errors.append(self.ERROR_MISSING_SECTION_IN.format(element, section_name))

    def __positions_check(self, element, section, section_name):
        if element in section.keys():
            if len(section[element]) == 2:
                self.__check_element_is_in_section_and_valid("x", section[element], element, int)
                self.__check_element_is_in_section_and_valid("y", section[element], element, int)
            else:
                self.errors.append(self.ERROR_EXCEPTED_NUMBER_ELEMENTS.format(section))
        else:
            self.errors.append(self.ERROR_MISSING_SECTION_IN.format(element, section_name))

    def __sheet_positions_check(self, element, section, section_name):
        if element in section.keys():
            if len(section[element]) == 3:
                self.__check_element_is_in_section_and_valid("row", section[element], element, int)
                self.__check_element_is_in_section_and_valid("column", section[element], element, int)
                self.__check_element_is_in_section_and_valid("SpriteSheet", section[element], element, str)
            else:
                self.errors.append(self.ERROR_EXCEPTED_NUMBER_ELEMENTS.format(element))
        else:
            self.errors.append(self.ERROR_MISSING_SECTION_IN.format(element, section_name))

    def __is_on_main_structure(self, section, json_data):
        if not section in json_data:
            self.errors.append(self.ERROR_MISSING_ELEMENT_ON_MAIN_STRUCTURE.format(section))

    def __is_item_font_valid(self, element, section):
        if element in section:
            font = section[element]
            self.__check_element_is_in_section_and_valid("Name", font, element, str)
            self.__check_element_is_in_section_and_valid("Size", font, element, int)
            if "Colors" in font:
                self.__color_check("Normal", font["Colors"], "Colors")
                self.__color_check("Max", font["Colors"], "Colors")
            else:
                self.errors.append(self.ERROR_MISSING_SECTION_IN.format("Colors", element))

        else:
            self.errors.append(self.ERROR_MISSING_SECTION_IN.format(element, "Fonts"))

    def __check_item(self, section, index):
        self.__check_element_is_in_section_and_valid("Id", section, "Item ID = {}".format(index), int)
        self.__check_element_is_in_section_and_valid("Kind", section, "Item ID = {}".format(index), str)
        self.__check_element_is_in_section_and_valid("Name", section, "Item ID = {}".format(index), str)
        self.__positions_check("Positions", section, "Item ID = {}".format(index))
        self.__sheet_positions_check("SheetInformation", section, "Item ID = {}".format(index))
        self.__check_element_is_in_section_and_valid("isActive", section, "Item ID = {}".format(index), bool)

        if "Hint" in section.keys():
            if not isinstance(section["Hint"], str):
                if section["Hint"] is not None:
                    self.errors.append(
                        self.ERROR_IS_NOT_IN_EXCEPTED_TYPE.format("Hint" + "." + "Item ID = {}".format(index), str))
        else:
            self.errors.append(self.ERROR_MISSING_SECTION_IN.format("Hint", "Item ID = {}".format(index)))

        self.__check_element_is_in_section_and_valid("OpacityDisable", section, "Item ID = {}".format(index), float)

    def __check_incremental_item(self, section, index):
        if len(section.keys()) >= 9:
            if "StartIncrementIndex" in section.keys():
                self.__check_element_is_in_section_and_valid("StartIncrementIndex", section,
                                                             "Item ID = {}".format(index), int)
            if "Increment" in section:
                if isinstance(section["Increment"], list):
                    if len(section["Increment"]) > 0:
                        for increment in section["Increment"]:
                            if not isinstance(increment, str):
                                self.errors.append(self.ERROR_IS_NOT_IN_EXCEPTED_TYPE.format(
                                    "Increment in Item ID = {} | Increment = {}".format(index, increment), str))
                    else:
                        self.errors.append("Increment list is empty on Item ID = {}".format(index))
                else:
                    self.errors.append(
                        self.ERROR_IS_NOT_IN_EXCEPTED_TYPE.format("Increment in Item ID = {}".format(index), list))
            else:
                self.errors.append(self.ERROR_MISSING_SECTION_IN.format("Increment", "Item ID = {}".format(index)))
        else:
            self.errors.append(self.ERROR_THE_STRUCTURE_IS_NOT_VALID.format("Item ID = {}".format(index)))

    def __check_label(self, section, section_name):
        if "Label" in section.keys():
            if not isinstance(section["Label"], str):
                if section["Label"] is not None:
                    self.errors.append(
                        self.ERROR_IS_NOT_IN_EXCEPTED_TYPE.format(section_name, str))
        else:
            self.errors.append(self.ERROR_MISSING_SECTION_IN.format("Label", section_name))

    def __check_evolution_item(self, section, index):
        if len(section.keys()) >= 11:
            self.__check_label(section, "Item ID = {}".format(index))
            self.__check_element_is_in_section_and_valid("LabelCenter", section, "Item ID = {}".format(index), bool)

            if "NextItems" in section:
                if isinstance(section["NextItems"], list):
                    if len(section["NextItems"]) >= 0:
                        for next_item in section["NextItems"]:
                            if isinstance(next_item, dict):
                                self.__check_subitem_evolution_item(next_item, index)
                            else:
                                self.errors.append(
                                    self.ERROR_IS_NOT_IN_EXCEPTED_TYPE.format("NextItem in Item ID = {}".format(index),
                                                                              dict))
                else:
                    self.errors.append(
                        self.ERROR_IS_NOT_IN_EXCEPTED_TYPE.format("Increment in Item ID = {}".format(index), list))
            else:
                self.errors.append(self.ERROR_MISSING_SECTION_IN.format("NextItems", "Item ID = {}".format(index)))
        else:
            self.errors.append(self.ERROR_THE_STRUCTURE_IS_NOT_VALID.format("Item ID = {}".format(index)))

    def __check_subitem_evolution_item(self, section, index):
        if len(section.keys()) >= 4:
            self.__check_element_is_in_section_and_valid("Id", section, "Item ID = {}".format(index), int)
            self.__check_element_is_in_section_and_valid("Name", section, "Item ID = {}".format(index), str)
            self.__sheet_positions_check("SheetInformation", section, "Item ID = {}".format(index))
            self.__check_label(section, "Item ID = {}".format(index))
        else:
            self.errors.append(self.ERROR_THE_STRUCTURE_IS_NOT_VALID.format("Item ID = {}".format(index)))

    def __check_count_item(self, section, index):
        if len(section.keys()) == 12:
            self.__check_element_is_in_section_and_valid("valueMin", section, "Item ID = {}".format(index), int)
            self.__check_element_is_in_section_and_valid("valueMax", section, "Item ID = {}".format(index), int)
            self.__check_element_is_in_section_and_valid("valueIncrease", section, "Item ID = {}".format(index), int)
            self.__check_element_is_in_section_and_valid("valueStart", section, "Item ID = {}".format(index), int)
            pass
        else:
            self.errors.append(self.ERROR_THE_STRUCTURE_IS_NOT_VALID.format("Item ID = {}".format(index)))

    def __check_alternate_count_item(self, section, index):
        if len(section.keys()) >= 10:
            self.__check_element_is_in_section_and_valid("maxValue", section, "Item ID = {}".format(index), int)
            self.__check_element_is_in_section_and_valid("maxValueAlternate", section, "Item ID = {}".format(index),
                                                         int)
        else:
            self.errors.append(self.ERROR_THE_STRUCTURE_IS_NOT_VALID.format("Item ID = {}".format(index)))

    def __check_label_item(self, section, index):
        if len(section.keys()) >= 9:
            if "LabelList" in section.keys():
                if isinstance(section["LabelList"], list):
                    if len(section["LabelList"]) > 0:
                        for label in section["LabelList"]:
                            if not isinstance(label, str):
                                self.errors.append(
                                    self.ERROR_IS_NOT_IN_EXCEPTED_TYPE.format("LabelList in Item ID = {}".format(index),
                                                                              str))
                    else:
                        self.errors.append("LabelList list is empty on Item ID = {}".format(index))
                else:
                    self.errors.append(
                        self.ERROR_IS_NOT_IN_EXCEPTED_TYPE.format("LabelList in Item ID = {}".format(index), list))
        else:
            self.errors.append(self.ERROR_THE_STRUCTURE_IS_NOT_VALID.format("Item ID = {}".format(index)))

    def _check_check_item(self, section, index):
        if len(section.keys()) == 9:
            self.__sheet_positions_check("CheckImageSheetInformation", section, "Item ID = {}".format(index))
        else:
            self.errors.append(self.ERROR_THE_STRUCTURE_IS_NOT_VALID.format("Item ID = {}".format(index)))

    def __check_go_mode_item(self, section, index):
        if len(section.keys()) == 9:
            self.__check_element_is_in_section_and_valid("BackgroundGlow", section, "Item ID = {}".format(index), str)
        else:
            self.errors.append(self.ERROR_THE_STRUCTURE_IS_NOT_VALID.format("Item ID = {}".format(index)))

    def __is_structure_valid(self):
        if len(self.template_json_data) == 4:
            self.__is_on_main_structure("Informations", self.template_json_data[0])
            self.__is_on_main_structure("Datas", self.template_json_data[1])
            self.__is_on_main_structure("Fonts", self.template_json_data[2])
            self.__is_on_main_structure("Items", self.template_json_data[3])
        elif len(self.template_json_data) == 5:
            self.__is_on_main_structure("Maps", self.template_json_data[4])
        else:
            self.errors.append(self.ERROR_THE_STRUCTURE_IS_NOT_VALID.format("Main"))

    def __is_information_valid(self):
        informations = self.template_json_data[0]["Informations"]

        if len(informations.keys()) >= 3:
            self.__check_element_is_in_section_and_valid("Creator", informations, "Informations", str)
            self.__check_element_is_in_section_and_valid("Name", informations, "Informations", str)
            self.__check_element_is_in_section_and_valid("Version", informations, "Informations", str)
            if "Comments" in informations:
                self.__check_element_is_in_section_and_valid("Comments", informations, "Informations", str)
        else:
            self.errors.append(self.ERROR_THE_STRUCTURE_IS_NOT_VALID.format("Informations"))

    def __is_datas_valid(self):
        datas = self.template_json_data[1]["Datas"]

        if len(datas.keys()) == 4:
            self.__dimension_check("Dimensions", datas, "Datas")
            self.__check_element_is_in_section_and_valid("Background", datas, "Datas", str)
            self.__color_check("BackgroundColor", datas, "Datas")
            # self.__dimension_check("ItemSheetDimensions", datas, "Datas")
        else:
            self.errors.append(self.ERROR_THE_STRUCTURE_IS_NOT_VALID.format("Datas"))

    def __is_fonts_valid(self):
        fonts = self.template_json_data[2]["Fonts"]
        self.__is_item_font_valid("incrementalItemFont", fonts)
        self.__is_item_font_valid("evolutionItemFont", fonts)
        self.__is_item_font_valid("countItemFont", fonts)
        self.__is_item_font_valid("labelItemFont", fonts)
        self.__is_item_font_valid("labelItemFont", fonts)
        self.__is_item_font_valid("hintFont", fonts)

    def __is_items_valid(self):
        items = self.template_json_data[3]["Items"]

        for i in range(0, len(items)):
            item = items[i]

            if "Kind" in item.keys():
                # if len(item.keys()) >= 8:
                if item["Kind"] != "EditableBox":
                    self.__check_item(item, i)
                if item["Kind"] == "IncrementalItem":
                    self.__check_incremental_item(item, i)
                elif item["Kind"] == "EvolutionItem":
                    self.__check_evolution_item(item, i)
                elif item["Kind"] == "DraggableEvolutionItem":
                    self.__check_evolution_item(item, i)
                elif item["Kind"] == "CountItem":
                    self.__check_count_item(item, i)
                elif item["Kind"] == "AlternateCountItem":
                    self.__check_alternate_count_item(item, i)
                elif item["Kind"] == "LabelItem":
                    self.__check_label_item(item, i)
                elif item["Kind"] == "CheckItem":
                    self._check_check_item(item, i)
                elif item["Kind"] == "GoModeItem":
                    self.__check_go_mode_item(item, i)
                elif item["Kind"] == "Item":
                    pass
                elif item["Kind"] == "SubMenuItem":
                    pass
                elif item["Kind"] == "AlternateEvolutionItem":
                    pass
                elif item["Kind"] == "EditableBox":
                    pass
                elif item["Kind"] == "ImageItem":
                    pass
                elif item["Kind"] == "OpenLinkItem":
                    pass
                else:
                    self.errors.append("Kind of Item '{} | ID = {} doesn't exist'".format(item["Kind"], i))

            else:
                self.errors.append(self.ERROR_MISSING_SECTION_IN.format("Kind", "Items"))
