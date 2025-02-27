import json
import os
from PyQt5 import QtWidgets, QtCore

class CharacterDialog(QtWidgets.QDialog):
    """
    Dialog pro editaci vybraného charakteru:
      - money (float)
      - group (str)
      - coords (JSON v jednom poli) s možností vybrat z safecoords.json
      - firstname, lastname
      - skinPlayer (JSON rozložený do klíč=hodnota, s parsováním int/float/bool)
    """

    def __init__(self, connection, row_data, safecoords_path="safecoords.json", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Character")
        self.setGeometry(200, 200, 600, 600)

        self.connection = connection
        self.row_data = row_data

        # Pro SkinPlayer
        self.skin_fields = {}

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
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

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
        print(self.row_data.get('coords'))
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

        layout.addLayout(form_layout)

        # SKINPLAYER sekce
        layout.addWidget(QtWidgets.QLabel("<b>skinPlayer (JSON) - klíč:hodnota</b>"))

        self.skin_form_layout = QtWidgets.QFormLayout()
        skin_group = QtWidgets.QGroupBox("skinPlayer")
        skin_group.setLayout(self.skin_form_layout)

        self.parse_skin_json()

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(skin_group)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area, stretch=1)

        # Tlačítka
        btn_layout = QtWidgets.QHBoxLayout()
        save_btn = QtWidgets.QPushButton("Uložit")
        save_btn.clicked.connect(self.save_data)
        cancel_btn = QtWidgets.QPushButton("Zavřít")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

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

    def parse_skin_json(self):
        """Rozparsuje row_data['skinPlayer'] do lineeditů."""
        skin_raw = self.decode_if_needed(self.row_data.get('skinPlayer', ''))
        try:
            skin_dict = json.loads(skin_raw)
        except json.JSONDecodeError:
            skin_dict = {}

        if not isinstance(skin_dict, dict):
            skin_dict = {}

        for k, v in skin_dict.items():
            v_str = str(v)
            le = QtWidgets.QLineEdit(v_str)
            self.skin_form_layout.addRow(f"{k}:", le)
            self.skin_fields[k] = le

    def construct_skin_json(self):
        """Projde self.skin_fields a zkusí parse int/float/bool, jinak string."""
        new_dict = {}
        for k, le in self.skin_fields.items():
            val_str = le.text().strip()
            parsed_val = self.parse_value(val_str)
            new_dict[k] = parsed_val
        return json.dumps(new_dict, ensure_ascii=False)

    def parse_value(self, s):
        """Zkus bool, int, float, jinak string."""
        low_s = s.lower()
        if low_s == "true":
            return True
        if low_s == "false":
            return False
        # int?
        try:
            return int(s)
        except ValueError:
            pass
        # float?
        try:
            return float(s)
        except ValueError:
            pass

        # jinak string
        return s

    def save_data(self):
        """Uloží do DB: money, group, coords, firstname, lastname, skinPlayer."""
        charid = self.row_data['charidentifier']

        new_money = self.money_edit.value()
        new_group = self.group_edit.text().strip()

        # coords => zkusíme valid JSON?
        coords_str = self.coords_edit.text().strip()
        try:
            json.loads(coords_str)  # jen test
        except:
            QtWidgets.QMessageBox.warning(self, "Chyba JSON", "coords není validní JSON.")
            return

        new_firstname = self.firstname_edit.text().strip()
        new_lastname = self.lastname_edit.text().strip()

        # skinPlayer
        new_skin = self.construct_skin_json()

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
