import sys
import json
import os
import re
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector

def decode_if_bytes(value):
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return value

def parse_vector3(input_str: str):
    """
    Pokusí se z řetězce typu 'vector3(x, y, z)' vyparsovat x, y, z jako float.
    Např.: 'vector3(-379.382904, -118.040138, 45.169785)' -> (-379.382904, -118.040138, 45.169785)
    Pokud se nepodaří, vrátí None.
    """
    pattern = r"^\s*vector3\s*\(\s*([\-0-9\.]+)\s*,\s*([\-0-9\.]+)\s*,\s*([\-0-9\.]+)\s*\)\s*$"
    match = re.match(pattern, input_str.strip())
    if not match:
        return None
    try:
        x = float(match.group(1))
        y = float(match.group(2))
        z = float(match.group(3))
        return (x, y, z)
    except ValueError:
        return None

def format_vector3(x: float, y: float, z: float) -> str:
    """
    Z trojice float (x, y, z) vyrobí řetězec 'vector3(x, y, z)' s cca 6 des. místy.
    """
    return f"vector3({x:.6f}, {y:.6f}, {z:.6f})"

class TreasureDialog(QtWidgets.QDialog):
    """Dialog pro úpravu záznamu v aprts_treasures."""
    def __init__(self, connection, treasure_id=None):
        super().__init__()
        self.connection = connection
        self.treasure_id = treasure_id
        self.setWindowTitle("Treasure")
        self.resize(600, 200)
        self.init_ui()
        if self.treasure_id is not None:
            self.load_data()

    def init_ui(self):
        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        self.name_edit = QtWidgets.QLineEdit()
        self.active_check = QtWidgets.QCheckBox("Aktivní?")

        # Místo 3 spinboxů jen jediné QLineEdit pro vector3
        self.coords_edit = QtWidgets.QLineEdit()
        self.coords_edit.setPlaceholderText("vector3(x, y, z)")

        # ComboBox pro treasure_type_id
        self.type_combo = QtWidgets.QComboBox()
        # Naplníme z DB
        self.load_types_to_combo()

        layout.addRow("Name:", self.name_edit)
        layout.addRow("", self.active_check)
        layout.addRow("Coordinates (vector3):", self.coords_edit)
        layout.addRow("Treasure Type:", self.type_combo)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self
        )
        btns.accepted.connect(self.save_data)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def load_types_to_combo(self):
        """Načte existující `aprts_treasure_types` a naplní self.type_combo."""
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM aprts_treasure_types ORDER BY name")
        types = cursor.fetchall()
        self.type_combo.clear()
        for t in types:
            self.type_combo.addItem(t["name"], t["id"])

    def load_data(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM aprts_treasures WHERE id=%s", (self.treasure_id,))
        row = cursor.fetchone()
        if row:
            self.name_edit.setText(decode_if_bytes(row["name"]) or "")
            self.active_check.setChecked(bool(row["active"]))

            # Souřadnice z DB do textu 'vector3(...)'
            x = float(row["coord_x"])
            y = float(row["coord_y"])
            z = float(row["coord_z"])
            self.coords_edit.setText(format_vector3(x, y, z))

            # Nastavíme treasure_type_id
            type_id = row["treasure_type_id"]
            index = self.type_combo.findData(type_id)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)

    def save_data(self):
        name_val = self.name_edit.text().strip()
        active_val = self.active_check.isChecked()
        coords_str = self.coords_edit.text().strip()
        type_id = self.type_combo.currentData()

        # Validace
        if not name_val:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'name' nesmí být prázdné.")
            return
        if type_id is None:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Vyberte Treasure Type.")
            return

        # Parsování vector3
        coords_tuple = parse_vector3(coords_str)
        if not coords_tuple:
            QtWidgets.QMessageBox.warning(
                self, "Chyba",
                "Chybný formát souřadnic. Použijte např. 'vector3(-379.382904, -118.040138, 45.169785)'."
            )
            return

        x_val, y_val, z_val = coords_tuple

        cursor = self.connection.cursor()
        if self.treasure_id is not None:
            query = """
                UPDATE aprts_treasures
                SET name=%s, active=%s, coord_x=%s, coord_y=%s, coord_z=%s, treasure_type_id=%s
                WHERE id=%s
            """
            params = (name_val, active_val, x_val, y_val, z_val, type_id, self.treasure_id)
        else:
            query = """
                INSERT INTO aprts_treasures (name, active, coord_x, coord_y, coord_z, treasure_type_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (name_val, active_val, x_val, y_val, z_val, type_id)

        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")
