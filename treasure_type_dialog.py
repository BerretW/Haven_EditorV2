
import sys
import json
import os
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector

def decode_if_bytes(value):
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return value

class TreasureTypeDialog(QtWidgets.QDialog):
    """Dialog pro editaci nebo přidání záznamu v aprts_treasure_types."""
    def __init__(self, connection, type_id=None):
        super().__init__()
        self.connection = connection
        self.type_id = type_id
        self.setWindowTitle("TreasureType")
        self.init_ui()
        if self.type_id is not None:
            self.load_data()

    def init_ui(self):
        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        self.name_edit = QtWidgets.QLineEdit()
        self.prop_edit = QtWidgets.QLineEdit()
        self.chance_spin = QtWidgets.QSpinBox()
        self.chance_spin.setRange(0, 10000)
        self.chance_spin.setValue(100)

        layout.addRow("Name:", self.name_edit)
        layout.addRow("Prop:", self.prop_edit)
        layout.addRow("Chance:", self.chance_spin)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self
        )
        btns.accepted.connect(self.save_data)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def load_data(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM aprts_treasure_types WHERE id=%s", (self.type_id,)
        )
        row = cursor.fetchone()
        if row:
            self.name_edit.setText(decode_if_bytes(row["name"]) or "")
            self.prop_edit.setText(decode_if_bytes(row["prop"]) or "")
            self.chance_spin.setValue(row["chance"])

    def save_data(self):
        name_val = self.name_edit.text().strip()
        prop_val = self.prop_edit.text().strip()
        chance_val = self.chance_spin.value()

        if not name_val:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'name' nesmí být prázdné.")
            return

        cursor = self.connection.cursor()
        if self.type_id is not None:
            query = """
                UPDATE aprts_treasure_types
                SET name=%s, prop=%s, chance=%s
                WHERE id=%s
            """
            params = (name_val, prop_val, chance_val, self.type_id)
        else:
            query = """
                INSERT INTO aprts_treasure_types (name, prop, chance)
                VALUES (%s, %s, %s)
            """
            params = (name_val, prop_val, chance_val)

        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")