import sys
import json
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from item_manager import ItemSelectionDialog, ItemDialog

class FreeplacePropDialog(QtWidgets.QDialog):
    def __init__(self, connection, prop_id=None):
        super().__init__()
        self.connection = connection
        self.prop_id = prop_id
        self.setWindowTitle("Freeplace Prop")
        self.init_ui()
        if self.prop_id:
            self.load_prop()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_layout = QtWidgets.QFormLayout()

        self.prop_edit = QtWidgets.QLineEdit()
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(['prop', 'storage'])
        self.zmod_edit = QtWidgets.QDoubleSpinBox()
        self.zmod_edit.setDecimals(2)
        self.zmod_edit.setRange(-10000, 10000)
        self.zmod_edit.setValue(0.00)

        # Pole pro výběr položky
        self.item_edit = QtWidgets.QLineEdit()
        self.item_edit.setReadOnly(True)
        self.select_item_button = QtWidgets.QPushButton("Vybrat Item")
        self.select_item_button.clicked.connect(self.select_item)
        self.create_item_button = QtWidgets.QPushButton("Vytvořit Nový Item")
        self.create_item_button.clicked.connect(self.create_new_item)

        item_layout = QtWidgets.QHBoxLayout()
        item_layout.addWidget(self.item_edit)
        item_layout.addWidget(self.select_item_button)
        item_layout.addWidget(self.create_item_button)

        # Pole pro zadání 'jobs'
        self.jobs_edit = QtWidgets.QLineEdit()
        self.jobs_edit.setPlaceholderText('Např.: ["job1", "job2"]')

        form_layout.addRow("Prop:", self.prop_edit)
        form_layout.addRow("Typ:", self.type_combo)
        form_layout.addRow("Z Modifikace:", self.zmod_edit)
        form_layout.addRow("Item:", item_layout)
        form_layout.addRow("Jobs:", self.jobs_edit)

        layout.addLayout(form_layout)

        # Tlačítka
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.save_prop)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_prop(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM aprts_freeplacing_props WHERE id = %s", (self.prop_id,))
        prop = cursor.fetchone()
        if prop:
            self.prop_edit.setText(prop['prop'] or '')
            type_index = self.type_combo.findText(prop['type'])
            self.type_combo.setCurrentIndex(type_index)
            self.zmod_edit.setValue(float(prop['zmod']))
            self.item_edit.setText(prop['item'] or '')

            # Dekódujeme 'jobs', pokud je typu bytes
            jobs_value = prop['jobs'] or '[]'
            if isinstance(jobs_value, bytes):
                jobs_value = jobs_value.decode('utf-8')
            self.jobs_edit.setText(jobs_value)

    def select_item(self):
        dialog = ItemSelectionDialog(self.connection, single_selection=True)
        if dialog.exec_():
            selected_items = dialog.selected_items
            if selected_items:
                self.item_edit.setText(selected_items[0]['item'])

    def create_new_item(self):
        dialog = ItemDialog(self.connection)
        if dialog.exec_():
            self.item_edit.setText(dialog.item_code)

    def save_prop(self):
        prop = self.prop_edit.text().strip()
        if not prop:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'Prop' nesmí být prázdné.")
            return
        type_ = self.type_combo.currentText()
        zmod = self.zmod_edit.value()
        item = self.item_edit.text() or None
        jobs_text = self.jobs_edit.text().strip()
        try:
            jobs = json.loads(jobs_text) if jobs_text else []
            if not isinstance(jobs, list):
                raise ValueError
            jobs_json = json.dumps(jobs)
        except (ValueError, json.JSONDecodeError):
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'Jobs' musí být platné pole JSON.")
            return

        cursor = self.connection.cursor()
        if self.prop_id:
            query = """
                UPDATE aprts_freeplacing_props SET
                prop=%s, type=%s, zmod=%s, item=%s, jobs=%s
                WHERE id=%s
            """
            params = (prop, type_, zmod, item, jobs_json, self.prop_id)
        else:
            query = """
                INSERT INTO aprts_freeplacing_props
                (prop, type, zmod, item, jobs)
                VALUES (%s, %s, %s, %s, %s)
            """
            params = (prop, type_, zmod, item, jobs_json)
        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")
