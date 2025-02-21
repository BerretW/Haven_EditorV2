import re
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class StoreDialog(QtWidgets.QDialog):
    def __init__(self, connection, store_id=None):
        super().__init__()
        self.connection = connection
        self.store_id = store_id
        self.setWindowTitle("Obchod")
        self.init_ui()
        if self.store_id:
            self.load_store()
        else:
            self.set_defaults()  # Nastavíme defaultní hodnoty

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_layout = QtWidgets.QFormLayout()

        self.name_edit = QtWidgets.QLineEdit()
        self.blip_icon_edit = QtWidgets.QDoubleSpinBox()
        self.blip_icon_edit.setMaximum(999999999999)
        self.blip_icon_edit.setMinimum(-999999999999)

        self.blip_check = QtWidgets.QCheckBox("Zobrazit Blip")

        self.coords_edit = QtWidgets.QLineEdit()
        self.coords_edit.setPlaceholderText("vector3(x, y, z)")
        self.heading_edit = QtWidgets.QDoubleSpinBox()
        self.heading_edit.setMaximum(360)
        self.heading_edit.setDecimals(3)

        # Přidáme ComboBox pro výběr NPC
        self.npc_combo = QtWidgets.QComboBox()
        self.load_npc_list()

        # Přidáme pole pro zadání jobu
        self.job_edit = QtWidgets.QLineEdit()
        self.job_edit.setPlaceholderText("Zadejte název jobu (nepovinné)")

        form_layout.addRow("Název:", self.name_edit)
        form_layout.addRow("Blip Icon:", self.blip_icon_edit)
        form_layout.addRow("", self.blip_check)
        form_layout.addRow("Souřadnice:", self.coords_edit)
        form_layout.addRow("Heading:", self.heading_edit)
        form_layout.addRow("NPC:", self.npc_combo)
        form_layout.addRow("Job:", self.job_edit)

        layout.addLayout(form_layout)

        # Sekce pro přiřazení kategorií
        categories_label = QtWidgets.QLabel("Kategorie Obchodu:")
        layout.addWidget(categories_label)

        self.categories_table = QtWidgets.QTableWidget()
        self.categories_table.setColumnCount(3)
        self.categories_table.setHorizontalHeaderLabels(['Kategorie', 'Zacházení', ''])
        layout.addWidget(self.categories_table)

        self.load_categories()

        # Tlačítka
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.save_store)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def set_defaults(self):
        # Nastavíme defaultní hodnotu pro blip ikonu
        self.blip_icon_edit.setValue(1475879922)
        # Nastavíme defaultní hodnotu 'none' pro zacházení s kategoriemi
        for row in range(self.categories_table.rowCount()):
            trade_combo = self.categories_table.cellWidget(row, 1)
            index = trade_combo.findText('none')
            if index >= 0:
                trade_combo.setCurrentIndex(index)
        # Nastavíme výchozí hodnotu pro NPC (žádné)
        index = self.npc_combo.findData(None)
        if index >= 0:
            self.npc_combo.setCurrentIndex(index)
        # Vyčistíme pole pro job
        self.job_edit.clear()

    def load_store(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM aprts_stores WHERE id = %s", (self.store_id,))
        store = cursor.fetchone()
        if store:
            self.name_edit.setText(store['name'])
            self.blip_icon_edit.setValue(store['blip_icon'])
            self.blip_check.setChecked(bool(store['blip']))
            coords = f"vector3({store['coords_x']}, {store['coords_y']}, {store['coords_z']})"
            self.coords_edit.setText(coords)
            self.heading_edit.setValue(store['heading'])
            self.job_edit.setText(store.get('job', ''))  # Načteme hodnotu job
            self.load_store_categories()
            self.load_store_npc()
        else:
            self.set_defaults()

    def load_npc_list(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT npc_id, name FROM aprts_store_npc_list ORDER BY name")
        npcs = cursor.fetchall()
        self.npc_combo.clear()
        self.npc_combo.addItem("Žádné", None)  # Výchozí možnost
        for npc in npcs:
            self.npc_combo.addItem(npc['name'], npc['npc_id'])

    def load_store_npc(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT npc_id FROM aprts_store_npc WHERE store_id = %s", (self.store_id,))
        result = cursor.fetchone()
        npc_id = result['npc_id'] if result else None
        index = self.npc_combo.findData(npc_id)
        if index >= 0:
            self.npc_combo.setCurrentIndex(index)
        else:
            index = self.npc_combo.findData(None)
            if index >= 0:
                self.npc_combo.setCurrentIndex(index)

    def load_categories(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM aprts_store_item_categories")
        self.all_categories = cursor.fetchall()
        self.populate_categories_table()

    def populate_categories_table(self):
        self.categories_table.setRowCount(0)
        for category in self.all_categories:
            row_position = self.categories_table.rowCount()
            self.categories_table.insertRow(row_position)

            category_item = QtWidgets.QTableWidgetItem(category['name'])
            category_item.setData(QtCore.Qt.UserRole, category['id'])
            self.categories_table.setItem(row_position, 0, category_item)

            trade_combo = QtWidgets.QComboBox()
            trade_combo.addItems(['buy', 'sell', 'all', 'none'])
            index = trade_combo.findText('none')
            if index >= 0:
                trade_combo.setCurrentIndex(index)
            self.categories_table.setCellWidget(row_position, 1, trade_combo)

    def load_store_categories(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT category_id, trade FROM aprts_store_categories WHERE store_id = %s", (self.store_id,))
        store_categories = cursor.fetchall()
        category_trade_map = {cat['category_id']: cat['trade'] for cat in store_categories}
        for row in range(self.categories_table.rowCount()):
            category_item = self.categories_table.item(row, 0)
            category_id = category_item.data(QtCore.Qt.UserRole)
            trade_combo = self.categories_table.cellWidget(row, 1)
            trade = category_trade_map.get(category_id, 'none')
            index = trade_combo.findText(trade)
            if index >= 0:
                trade_combo.setCurrentIndex(index)

    def save_store(self):
        name = self.name_edit.text().strip()
        blip_icon = self.blip_icon_edit.value()
        blip = 1 if self.blip_check.isChecked() else 0
        coords_text = self.coords_edit.text().strip()
        heading = self.heading_edit.value()
        npc_id = self.npc_combo.currentData()
        job = self.job_edit.text().strip() or None  # Pokud je prázdné, uložíme jako NULL

        if not name:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'Název' nesmí být prázdné.")
            return

        coords = self.parse_vector3(coords_text)
        if coords is None:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'Souřadnice' musí být ve formátu vector3(x, y, z).")
            return

        coords_x, coords_y, coords_z = coords

        cursor = self.connection.cursor()
        if self.store_id:
            query = """
                UPDATE aprts_stores SET
                name = %s, blip_icon = %s, blip = %s, coords_x = %s, coords_y = %s, coords_z = %s, heading = %s, job = %s
                WHERE id = %s
            """
            params = (name, blip_icon, blip, coords_x, coords_y, coords_z, heading, job, self.store_id)
        else:
            query = """
                INSERT INTO aprts_stores (name, blip_icon, blip, coords_x, coords_y, coords_z, heading, job)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (name, blip_icon, blip, coords_x, coords_y, coords_z, heading, job)
        try:
            cursor.execute(query, params)
            if not self.store_id:
                self.store_id = cursor.lastrowid
            self.connection.commit()
            self.save_store_categories()
            self.save_store_npc(npc_id)
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")
    def save_store_categories(self):
        cursor = self.connection.cursor()
        # Nejprve smažeme stávající přiřazení
        cursor.execute("DELETE FROM aprts_store_categories WHERE store_id = %s", (self.store_id,))
        # Poté vložíme nová přiřazení
        for row in range(self.categories_table.rowCount()):
            category_item = self.categories_table.item(row, 0)
            category_id = category_item.data(QtCore.Qt.UserRole)
            trade_combo = self.categories_table.cellWidget(row, 1)
            trade = trade_combo.currentText()
            if trade != 'none':
                query = """
                    INSERT INTO aprts_store_categories (store_id, category_id, trade)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(query, (self.store_id, category_id, trade))
            else:
                # Pokud je trade 'none', neukládáme do databáze
                continue
        self.connection.commit()

    def save_store_npc(self, npc_id):
        cursor = self.connection.cursor()
        # Nejprve smažeme stávající přiřazení NPC
        cursor.execute("DELETE FROM aprts_store_npc WHERE store_id = %s", (self.store_id,))
        if npc_id is not None:
            # Vložíme nové přiřazení
            query = """
                INSERT INTO aprts_store_npc (store_id, npc_id)
                VALUES (%s, %s)
            """
            cursor.execute(query, (self.store_id, npc_id))
            self.connection.commit()
    def parse_vector3(self, text):
        match = re.match(r'vector3\(\s*([-\d\.]+),\s*([-\d\.]+),\s*([-\d\.]+)\s*\)', text)
        if match:
            x, y, z = map(float, match.groups())
            return x, y, z
        else:
            return None
