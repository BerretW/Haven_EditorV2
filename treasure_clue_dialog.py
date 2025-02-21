# treasure_clue_dialog.py

import sys
import json
import os
import re
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
from item_manager import ItemSelectionDialog  # Importujte podle vaší struktury projektu

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

class TreasureClueDialog(QtWidgets.QDialog):
    """Dialog pro úpravu záznamu v aprts_treasure_clues."""
    def __init__(self, connection, clue_id=None, treasure_id=None):
        super().__init__()
        self.connection = connection
        self.clue_id = clue_id
        self.treasure_id = treasure_id
        self.setWindowTitle("Treasure Clue")
        self.init_ui()
        if self.clue_id is not None:
            self.load_data()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_layout = QtWidgets.QFormLayout()

        # Text
        self.text_edit = QtWidgets.QPlainTextEdit()
        form_layout.addRow("Text:", self.text_edit)

        # Prop
        self.prop_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Prop:", self.prop_edit)

        # Ped
        self.ped_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Ped (model postavy?):", self.ped_edit)

        # Count
        self.count_spin = QtWidgets.QSpinBox()
        self.count_spin.setRange(0, 9999)
        form_layout.addRow("Count:", self.count_spin)

        # Item + Tlačítko pro výběr itemu a vyprázdnění
        self.item_edit = QtWidgets.QLineEdit()
        self.item_edit.setReadOnly(True)  # Zamezíme manuálnímu zadávání
        self.select_item_button = QtWidgets.QPushButton("Vybrat Item")
        self.clear_item_button = QtWidgets.QPushButton("Vyprázdnit Item")
        self.select_item_button.clicked.connect(self.select_item)
        self.clear_item_button.clicked.connect(self.clear_item)

        # Layout pro Item + Tlačítka
        item_layout = QtWidgets.QHBoxLayout()
        item_layout.addWidget(self.item_edit)
        item_layout.addWidget(self.select_item_button)
        item_layout.addWidget(self.clear_item_button)
        form_layout.addRow("Item:", item_layout)

        # Coordinates (vector3)
        self.coords_edit = QtWidgets.QLineEdit()
        self.coords_edit.setPlaceholderText("vector3(x, y, z)")
        form_layout.addRow("Coordinates (vector3):", self.coords_edit)

        layout.addLayout(form_layout)

        # Tlačítka OK/Cancel
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self
        )
        btns.accepted.connect(self.save_data)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def select_item(self):
        """
        Otevře ItemSelectionDialog pro výběr itemu.
        """
        dialog = ItemSelectionDialog(self.connection, single_selection=True)
        if dialog.exec_():
            selected = dialog.selected_items
            if selected:
                # Předpokládáme, že selected_items je list dictů: [{'item':'...', 'label':'...'}, ...]
                chosen_item = selected[0]['item']
                # Optional: zobrazit label pokud je dostupný
                label = selected[0].get('label', chosen_item)
                self.item_edit.setText(f"{label} ({chosen_item})")

    def clear_item(self):
        """Vyprázdní pole pro item."""
        self.item_edit.clear()

    def load_data(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM aprts_treasure_clues WHERE id=%s", (self.clue_id,)
        )
        row = cursor.fetchone()
        if row:
            self.text_edit.setPlainText(decode_if_bytes(row["text"]) or "")
            self.prop_edit.setText(decode_if_bytes(row["prop"]) or "")
            self.ped_edit.setText(decode_if_bytes(row["ped"]) or "")
            self.count_spin.setValue(row["count"])
            # Item
            item_text = decode_if_bytes(row["item"]) or ""
            if item_text:
                # Pokud máte label, můžete jej získat z jiné tabulky, zde předpokládáme, že ho máte
                # Pokud ne, zobrazíme jen item
                # Příklad: "Label (item)"
                # Pokud nemáte label, můžete zobrazit jen item
                self.item_edit.setText(item_text)  # Můžete upravit podle potřeby
            else:
                self.item_edit.clear()
            # Coordinates
            x = float(row["coord_x"])
            y = float(row["coord_y"])
            z = float(row["coord_z"])
            self.coords_edit.setText(format_vector3(x, y, z))
            self.treasure_id = row["treasure_id"]

    def save_data(self):
        text_val = self.text_edit.toPlainText().strip()
        prop_val = self.prop_edit.text().strip()
        ped_val = self.ped_edit.text().strip()
        count_val = self.count_spin.value()
        # Získání čistého itemu (bez labelu, pokud je zobrazen)
        item_text = self.item_edit.text().strip()
        item_val = None
        if item_text:
            match = re.match(r"^(.*)\s+\((.*)\)$", item_text)
            if match:
                item_val = match.group(2)
            else:
                item_val = item_text

        coords_str = self.coords_edit.text().strip()

        # Validace
        if not text_val:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'Text' nesmí být prázdné.")
            return
        if not self.treasure_id:
            QtWidgets.QMessageBox.warning(
                self, "Chyba", "Není zadán treasure_id (vnitřní chyba?)."
            )
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
        if self.clue_id is not None:
            # UPDATE
            query = """
                UPDATE aprts_treasure_clues
                SET text=%s, prop=%s, ped=%s, count=%s, item=%s,
                    coord_x=%s, coord_y=%s, coord_z=%s
                WHERE id=%s
            """
            params = (text_val, prop_val, ped_val, count_val, item_val,
                      x_val, y_val, z_val, self.clue_id)
        else:
            # INSERT
            query = """
                INSERT INTO aprts_treasure_clues
                (treasure_id, text, prop, ped, count, item, coord_x, coord_y, coord_z)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (self.treasure_id, text_val, prop_val, ped_val,
                      count_val, item_val, x_val, y_val, z_val)

        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")
