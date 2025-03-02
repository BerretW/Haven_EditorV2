import json
import os
from PyQt5 import QtWidgets, QtCore, QtGui

class CharacterDialog(QtWidgets.QDialog):
    """
    Dialog pro editaci vybraného charakteru:
      - money (float)
      - group (str)
      - coords (JSON v jednom poli) s možností vybrat z safecoords.json
      - firstname, lastname
      - skinPlayer (JSON rozložený do klíč=hodnota + stromové zobrazení)
      - Filtr ve stromu pro klíče/hodnoty (např. hair / overlays / Beard)
    """

    def __init__(self, connection, row_data, safecoords_path="safecoords.json", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Character")
        self.setGeometry(200, 200, 600, 600)

        self.connection = connection
        self.row_data = row_data

        # Pro SkinPlayer
        self.skin_fields = {}
        self.original_skin_json_str = "" # Pro případné porovnání změn

        # Načteme safecoords
        self.safecoords = self.load_safecoords(safecoords_path)

        self.init_ui()

    def load_safecoords(self, path):
        """Načteme souřadnice ze safecoords.json, vrátíme dict nebo {}."""
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
            return data
        except Exception as e:
            print(f"Chyba při load_safecoords: {e}")
            return {}

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        form_layout = QtWidgets.QFormLayout()

        # charidentifier (read-only)
        charid_str = str(self.row_data.get('charidentifier', '???'))
        self.charidentifier_label = QtWidgets.QLabel(charid_str)
        form_layout.addRow("charidentifier:", self.charidentifier_label)

        # money
        self.money_edit = QtWidgets.QDoubleSpinBox()
        self.money_edit.setRange(-99999999, 999999999)
        self.money_edit.setDecimals(2)
        money_val = self.decode_if_needed(self.row_data.get('money', 0.0))
        try:
            money_val = float(money_val)
        except:
            money_val = 0.0
        self.money_edit.setValue(money_val)
        form_layout.addRow("money:", self.money_edit)

        # group
        group_val = self.decode_if_needed(self.row_data.get('group', 'user'))
        self.group_edit = QtWidgets.QLineEdit(group_val)
        form_layout.addRow("group:", self.group_edit)

        # coords (JSON)
        coords_val = self.decode_if_needed(self.row_data.get('coords', '{}'))
        self.coords_edit = QtWidgets.QLineEdit(coords_val)
        form_layout.addRow("coords (JSON):", self.coords_edit)

        # ComboBox s safecoords
        self.safe_coords_combo = QtWidgets.QComboBox()
        self.safe_coords_combo.addItem("Vyber z safecoords.json", userData=None)
        for key in self.safecoords.keys():
            self.safe_coords_combo.addItem(key, userData=key)
        self.safe_coords_combo.currentIndexChanged.connect(self.on_safe_coord_selected)
        form_layout.addRow("Předdef. coords:", self.safe_coords_combo)

        # firstname
        firstname_val = self.decode_if_needed(self.row_data.get('firstname', ''))
        self.firstname_edit = QtWidgets.QLineEdit(firstname_val)
        form_layout.addRow("firstname:", self.firstname_edit)

        # lastname
        lastname_val = self.decode_if_needed(self.row_data.get('lastname', ''))
        self.lastname_edit = QtWidgets.QLineEdit(lastname_val)
        form_layout.addRow("lastname:", self.lastname_edit)

        main_layout.addLayout(form_layout)

        # ========= SKINPLAYER sekce (TabWidget s formulářem a stromem) =========
        self.tab_widget = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tab_widget, stretch=1)

        # -- Tab 1: Formulář (klíč: hodnota) --
        self.skin_form_widget = QtWidgets.QWidget()
        self.skin_form_layout = QtWidgets.QFormLayout(self.skin_form_widget)
        self.skin_form_widget.setLayout(self.skin_form_layout)

        # **Přidáme ScrollArea pro formulář**
        self.skin_form_scroll_area = QtWidgets.QScrollArea()
        self.skin_form_scroll_area.setWidgetResizable(True) # Důležité pro správné scrollování
        self.skin_form_scroll_area.setWidget(self.skin_form_widget)
        self.tab_widget.addTab(self.skin_form_scroll_area, "Formulář (klíč: hodnota)")


        # -- Tab 2: Strom JSONu --
        tree_tab = QtWidgets.QWidget()
        tree_tab_layout = QtWidgets.QVBoxLayout()
        tree_tab.setLayout(tree_tab_layout)

        # Filtr (QLineEdit)
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText("Vyhledat (např. 'hair', 'Beard', 'overlays')...")
        self.filter_edit.textChanged.connect(self.filter_tree_items)
        tree_tab_layout.addWidget(self.filter_edit)

        # Samotný QTreeWidget
        self.skin_tree_widget = QtWidgets.QTreeWidget()
        self.skin_tree_widget.setColumnCount(2)
        self.skin_tree_widget.setHeaderLabels(["Klíč", "Hodnota"])
        tree_tab_layout.addWidget(self.skin_tree_widget, stretch=1)

        # **Přidáme ScrollArea pro strom**
        self.tree_scroll_area = QtWidgets.QScrollArea()
        self.tree_scroll_area.setWidgetResizable(True)
        self.tree_scroll_area.setWidget(tree_tab)
        self.tab_widget.addTab(self.tree_scroll_area, "Strom JSONu")


        # Naplníme obě reprezentace
        self.parse_skin_json()

        # Tlačítka
        btn_layout = QtWidgets.QHBoxLayout()
        save_btn = QtWidgets.QPushButton("Uložit")
        save_btn.clicked.connect(self.save_data)
        cancel_btn = QtWidgets.QPushButton("Zavřít")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)

    def decode_if_needed(self, val):
        """Pokud je val bytes/bytearray, dekóduj. Jinak str(val)."""
        if isinstance(val, (bytes, bytearray)):
            return val.decode('utf-8', errors='replace')
        return str(val)

    def on_safe_coord_selected(self):
        """Pokud vybereme něco v ComboBoxu, nastavíme coords_edit JSONem z safecoords."""
        key = self.safe_coords_combo.currentData()
        if not key:
            return
        coords_data = self.safecoords.get(key, {})
        coords_str = json.dumps(coords_data, ensure_ascii=False)
        self.coords_edit.setText(coords_str)

    # --------------------------------------------------------------------------
    # SKINPLAYER zpracování
    # --------------------------------------------------------------------------

    def parse_skin_json(self):
        """
        Rozparsuje row_data['skinPlayer'] jednak do lineeditů (skin_form_layout),
        jednak do stromu (skin_tree_widget).
        """
        self.skin_fields.clear()
        self.skin_tree_widget.clear()

        skin_raw = self.decode_if_needed(self.row_data.get('skinPlayer', ''))
        self.original_skin_json_str = skin_raw
        try:
            skin_dict = json.loads(skin_raw)
        except json.JSONDecodeError:
            skin_dict = {}

        if not isinstance(skin_dict, dict):
            skin_dict = {}

        # === 1) Vyplnění QFormLayout lineeditů ===
        for k, v in skin_dict.items():
            if k == "overlays" and isinstance(v, dict): # Special handling for 'overlays'
                overlays_dict = v
                group_box = QtWidgets.QGroupBox("overlays") # Rámeček pro vizuální seskupení
                group_layout = QtWidgets.QFormLayout()
                group_box.setLayout(group_layout)
                self.skin_form_layout.addRow(group_box) # Přidáme rámeček do hlavního layoutu

                for overlay_k, overlay_v in overlays_dict.items():
                    if isinstance(overlay_v, (dict, list)):
                        v_str = json.dumps(overlay_v, ensure_ascii=False)
                    else:
                        v_str = str(overlay_v)
                    le = QtWidgets.QLineEdit(v_str)
                    group_layout.addRow(f"{overlay_k}:", le) # Přidáváme do group_layout
                    self.skin_fields[f"overlays.{overlay_k}"] = le # Klíč s prefixem "overlays."
            else: # For other top-level keys (not 'overlays')
                if isinstance(v, (dict, list)):
                    v_str = json.dumps(v, ensure_ascii=False)
                else:
                    v_str = str(v)
                le = QtWidgets.QLineEdit(v_str)
                self.skin_form_layout.addRow(f"{k}:", le)
                self.skin_fields[k] = le

        # === 2) Vyplnění QTreeWidget === (beze změn)
        root_item = QtWidgets.QTreeWidgetItem(["root"])
        self.skin_tree_widget.addTopLevelItem(root_item)
        self.populate_json_tree(root_item, skin_dict)
        self.skin_tree_widget.expandAll()

    def populate_json_tree(self, parent_item, data):
        """Rekurzivně přidá data do stromu s ikonami."""
        if isinstance(data, dict):
            parent_item.setIcon(0, QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_DirIcon)) # Ikona složky pro objekty
            for k, v in data.items():
                child = QtWidgets.QTreeWidgetItem([str(k), ""])
                parent_item.addChild(child)
                self.populate_json_tree(child, v)
        elif isinstance(data, list):
            parent_item.setIcon(0, QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView)) # Ikona detailního zobrazení pro pole (můžeš vybrat jinou)
            for i, v in enumerate(data):
                child = QtWidgets.QTreeWidgetItem([f"[{i}]", ""])
                parent_item.addChild(child)
                self.populate_json_tree(child, v)
        else:
            # Primární hodnota (int, float, bool, str)
            # parent_item.setIcon(0, QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)) # Ikona souboru pro hodnoty (volitelné)
            parent_item.setText(1, str(data))

    # --------------------------------------------------------------------------
    # Filtr ve stromu
    # --------------------------------------------------------------------------

    def filter_tree_items(self, text):
        """
        Prochází všechna QTreeWidgetItem a schovává je, pokud
        neobsahují 'text' ani v klíči, ani v hodnotě, ani ho neobsahuje žádný potomek.
        """
        text = text.lower().strip()

        def match_item(item, filter_str):
            """Zjišťuje, zda item (nebo libovolný potomek) odpovídá filtru."""
            # Jestli klíč nebo hodnota obsahuje filter_str
            key_match = filter_str in item.text(0).lower()
            val_match = filter_str in item.text(1).lower()

            # Rekurzivní kontrola potomků
            for i in range(item.childCount()):
                child = item.child(i)
                if match_item(child, filter_str):
                    # Pokud potomek odpovídá, i tento parent se bere jako match
                    return True

            # Jinak vrátíme, jestli se přímo matchuje klíč nebo hodnota
            return key_match or val_match

        # Pokud je filtr prázdný, ukaž vše
        if not text:
            self.show_all_items()
            return

        # Pro každý top-level item zkusíme match
        for i in range(self.skin_tree_widget.topLevelItemCount()):
            top_item = self.skin_tree_widget.topLevelItem(i)
            self.apply_item_filter(top_item, text)

    def apply_item_filter(self, item, filter_str):
        """Skryje item, pokud neodpovídá filtru a žádný potomek také ne."""
        matched = match_item_recursively(item, filter_str)
        item.setHidden(not matched)

        # Highlightování textu v itemech, které odpovídají filtru (nebo jejich potomci odpovídají)
        self.highlight_filtered_items(item, filter_str)


    def highlight_filtered_items(self, item, filter_str):
        """
        Rekurzivně prochází strom a nastavuje styl itemů na základě filtru.
        Pokud item nebo potomek odpovídá filtru, nastaví se tučný font.
        """
        filter_str_lower = filter_str.lower()
        key_match = filter_str_lower in item.text(0).lower()
        val_match = filter_str_lower in item.text(1).lower()
        any_child_match = False

        for i in range(item.childCount()):
            child = item.child(i)
            if self.highlight_filtered_items(child, filter_str): # Rekurzivní volání a kontrola potomků
                any_child_match = True

        if key_match or val_match or any_child_match:
            font = item.font(0) or QtGui.QFont() # Získat aktuální font nebo vytvořit nový
            font.setBold(True)
            item.setFont(0, font)
            item.setFont(1, font)
            return True # Tento item nebo potomek odpovídá filtru
        else:
            font = item.font(0) or QtGui.QFont()
            font.setBold(False) # Reset na default font
            item.setFont(0, font)
            item.setFont(1, font)
            return False # Tento item ani potomek neodpovídá filtru


    def show_all_items(self):
        """Nastaví hidden=False a resetuje font pro všechny itemy ve stromu."""
        stack = []
        for i in range(self.skin_tree_widget.topLevelItemCount()):
            stack.append(self.skin_tree_widget.topLevelItem(i))
        while stack:
            it = stack.pop()
            it.setHidden(False)
            font = it.font(0) or QtGui.QFont()
            font.setBold(False) # Reset fontu
            it.setFont(0, font)
            it.setFont(1, font)
            for j in range(it.childCount()):
                stack.append(it.child(j))

    # --------------------------------------------------------------------------
    # Ukládání
    # --------------------------------------------------------------------------

    def construct_skin_json(self):
        """
        Projde self.skin_fields a sestaví skinPlayer JSON, správně handluje overlays.
        """
        new_dict = {}
        overlays_dict = {} # Pro overlays

        for k, le in self.skin_fields.items():
            val_str = le.text().strip()
            parsed_val = self.parse_value(val_str)

            if k.startswith("overlays."): # Detekce overlays polí
                overlay_key = k[len("overlays."):] # Odstraníme prefix "overlays."
                overlays_dict[overlay_key] = parsed_val
            else: # Běžná pole mimo overlays
                new_dict[k] = parsed_val

        if overlays_dict: # Pokud jsme načetli nějaké overlays, přidáme je do hlavního dict
            new_dict["overlays"] = overlays_dict

        return json.dumps(new_dict, ensure_ascii=False)

    def parse_value(self, s):
        """
        Zkusí:
           1) parse jako JSON (pokud je to např. '{"hair":{"id":0}}')
           2) bool (true/false)
           3) int
           4) float
           5) jinak string
        """
        # 1) Zkus JSON
        try:
            return json.loads(s)
        except:
            pass

        # 2) Zkus bool
        low_s = s.lower()
        if low_s == "true":
            return True
        if low_s == "false":
            return False

        # 3) Zkus int
        try:
            return int(s)
        except ValueError:
            pass

        # 4) Zkus float
        try:
            return float(s)
        except ValueError:
            pass

        # 5) Jinak string
        return s

    def save_data(self):
        """Uloží do DB: money, group, coords, firstname, lastname, skinPlayer."""
        charid = self.row_data['charidentifier']

        new_money = self.money_edit.value()
        new_group = self.group_edit.text().strip()

        # coords => zkusíme valid JSON?
        coords_str = self.coords_edit.text().strip()
        try:
            json.loads(coords_str)  # jen test validity
        except:
            QtWidgets.QMessageBox.warning(self, "Chyba JSON", "coords není validní JSON.")
            return

        new_firstname = self.firstname_edit.text().strip()
        new_lastname = self.lastname_edit.text().strip()

        # skinPlayer => sestavíme
        new_skin = self.construct_skin_json()

        # Pro kontrolu, co se do DB uloží:
        print("Final skin JSON to save:", new_skin)

        # Zkontrolujeme, zda se skinPlayer změnil oproti originálu
        if new_skin == self.original_skin_json_str:
            print("SkinPlayer JSON se nezměnil.") # Pro debug, můžeme i vynechat hlášku
        else:
            print("SkinPlayer JSON se změnil.")


        sql = """
            UPDATE characters
            SET
              money = %s,
              `group` = %s,
              coords = %s,
              firstname = %s,
              lastname = %s,
              skinPlayer = %s
            WHERE charidentifier = %s
        """
        params = (
            new_money,
            new_group,
            coords_str,
            new_firstname,
            new_lastname,
            new_skin,
            charid
        )

        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            self.connection.commit()
            QtWidgets.QMessageBox.information(self, "OK", "Změny uloženy.")
            self.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "DB Error", str(e))

# Pomocná funkce: rekurzivní match pro apply_item_filter
def match_item_recursively(item, filter_str):
    """Vrátí True, pokud item (nebo jeho potomek) obsahuje filter_str v klíči/hodnotě."""
    key_match = filter_str in item.text(0).lower()
    val_match = filter_str in item.text(1).lower()

    # Pokud potomek odpovídá, parent je také match.
    for i in range(item.childCount()):
        child = item.child(i)
        if match_item_recursively(child, filter_str):
            return True

    return key_match or val_match

# ========================================
# Příklad samostatného spuštění (test bez DB):
if __name__ == "__main__":
    import sys

    # Mock "connection" a "row_data"
    class FakeConnection:
        def cursor(self):
            return self
        def execute(self, sql, params):
            print("SQL:", sql)
            print("Params:", params)
        def commit(self):
            pass

    # Vzorek row_data
    row_data = {
        "charidentifier": 123,
        "money": 100.0,
        "group": "user",
        "coords": '{"x":1,"y":2,"z":3}',
        "firstname": "John",
        "lastname": "Doe",
        # Sem můžeš vložit svůj obrovský JSON z DB:
        "skinPlayer": """
{"grime_tx_id": 0, "complex_opacity": 0, "CalvesS": 0.2, "EyeLidL": 0.0, "eyebrows_opacity": 0.0, "freckles_opacity": 0, "moles_tx_id": 0, "spots_opacity": 0, "NoseDis": 0.1, "BodyType": 2196852103, "acne_visibility": 0, "EarsW": 0, "NeckD": -1.0, "disc_visibility": 0, "foundation_palette_color_primary": 0, "NoseAng": 0.2, "ChinH": 0, "EyeH": 0.0, "EyeBrowD": 0.3, "blush_palette_id": 0, "hair_opacity": 0, "NoseW": -0.2, "Torso": 1519555092, "albedo": -343742430, "foundation_palette_id": 0, "EyeLidR": 0.0, "EyeD": 0.0, "MouthCRLD": 0.0, "NoseH": -0.1, "ArmsS": 0.3, "ShouldersS": 0.3, "MouthX": 0.0, "Scale": 0.0, "Body": 0, "eyebrows_visibility": 0, "scars_visibility": 0, "lipsticks_tx_id": 0, "hair_visibility": 0, "lipsticks_palette_id": 0, "blush_opacity": 0, "EarsA": -0.3, "paintedmasks_palette_id": 0, "FaceD": 0.0, "HipsS": -0.7, "EyeDis": 0.0, "beardstabble_opacity": 0, "paintedmasks_tx_id": 0, "sex": "mp_male", "freckles_visibility": 0, "ShouldersM": -0.5, "moles_visibility": 0, "MouthD": 0.0, "paintedmasks_opacity": 0, "LegsS": 0.2, "lipsticks_palette_color_tertiary": 0, "ageing_tx_id": 0, "NoseC": -0.1, "LLiphD": 0.0, "disc_tx_id": 0, "EyeLidH": 0.0, "FaceS": 0.0, "NeckW": -0.5, "eyeliner_palette_id": 0, "eyebrows_color": 0, "shadows_opacity": 0, "MouthCLH": 0.0, "shadows_tx_id": 0, "shadows_palette_id": 0, "Beard": 0, "shadows_visibility": 0, "EyeBrowH": 0.0, "CheekBonesW": 0.4, "paintedmasks_palette_color_primary": 0, "JawD": 0, "EyeLidW": 0.0, "lipsticks_visibility": 0, "LLiphH": 0.0, "disc_opacity": 0, "LegsType": 0, "NoseS": -0.2, "moles_opacity": 0, "foundation_tx_id": 0, "EyeAng": 0, "ULiphH": 0.0, "ChinW": -0.6, "eyeliner_opacity": 0, "eyeliner_color_primary": 0, "MouthCLD": 0.0, "paintedmasks_visibility": 0, "blush_visibility": 0, "blush_palette_color_primary": 0, "MouthCRH": 0.0, "lipsticks_opacity": 0, "Waist": 0, "spots_visibility": 0, "MouthCLLD": 0.0, "acne_tx_id": 0, "ageing_visibility": 0, "blush_tx_id": 0, "Hair": {"hash": -465491826}, "EarsD": -0.2, "spots_tx_id": 0, "acne_opacity": 0, "complex_tx_id": 0, "ageing_opacity": 0, "complex_visibility": 0, "beardstabble_visibility": 0, "grime_opacity": 0, "HeadSize": 0.0, "ULiphW": 0, "eyebrows_tx_id": 0, "EyeBrowW": 0.0, "foundation_visibility": 0, "eyeliner_tx_id": 0, "paintedmasks_palette_color_tertiary": 0, "shadows_palette_color_primary": 0, "shadows_palette_color_secondary": 0, "shadows_palette_color_tertiary": 0, "LLiphW": 0.0, "ChinD": 0.6, "beardstabble_tx_id": 0, "grime_visibility": 0, "ShouldersT": 0.0, "scars_tx_id": 0, "CheekBonesD": 0.2, "Legs": 0, "EarsH": -0.1, "foundation_opacity": 0, "MouthCRD": 0.0, "ChestS": 0.3, "Teeth": 712446626, "overlays": {"hair": {"albedo": "mp_u_faov_m_hair_002", "opacity": 1.0, "tint0": 1064202495}, "scar": {"opacity": 0.735, "id": 8}, "eyebrow": {"opacity": 0.882, "palette": "metaped_tint_hair", "id": 13, "sexe": "m", "tint0": 21}, "moles": {"opacity": 0.5, "id": 0}, "ageing": {"opacity": 0.305, "id": 0}, "beard": {"id": 0, "palette": "metaped_tint_hair", "opacity": 1.0, "tint0": 135}, "freckles": {"opacity": 0.67, "id": 8}}, "Eyes": 642477207, "MouthCRW": 0.0, "freckles_tx_id": 0, "FaceW": 0.0, "beardstabble_color_primary": 0, "lipsticks_palette_color_primary": 0, "paintedmasks_palette_color_secondary": 0, "MouthW": 0.0, "WaistW": 0, "HeadType": 908431499, "JawW": 0.3, "scars_opacity": 0, "hair_color_primary": 0, "MouthCLW": 0.0, "CheekBonesH": 0.7, "ULiphD": 0.0, "JawH": -0.5, "MouthY": 0.0, "lipsticks_palette_color_secondary": 0, "eyeliner_visibility": 0, "hair_tx_id": 0, "foundation_palette_color_secondary": 0, "foundation_palette_color_tertiary": 0}
        """
    }