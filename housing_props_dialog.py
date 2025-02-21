import sys
import os
import re
import json
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from item_manager import ItemSelectionDialog
from housing_category_dialog import CategoryManagerDialog


class HousingPropDialog(QtWidgets.QDialog):
    def __init__(self, connection, prop_id=None, item_code=None):
        super().__init__()
        self.connection = connection
        self.prop_id = prop_id
        self.item_code = item_code

        self.setWindowTitle("Housing Prop")
        self.setGeometry(100, 100, 700, 600)  # Zvýšení výšky okna pro nové pole
        self.load_stylesheet(os.path.join(BASE_DIR, "stylesheet.qss"))

        self.materials_data = {}
        self.repairjobs_data = []

        self.init_ui()

        if self.prop_id:
            self.load_housing_prop()
        elif self.item_code:
            self.item_edit.setText(self.item_code)
            self.check_required_fields()

    def load_stylesheet(self, filepath):
        try:
            with open(filepath, "r") as file:
                self.setStyleSheet(file.read())
        except Exception as e:
            print(f"Chyba při načítání stylů: {e}")

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        # --- FORMULÁŘ PRO BĚŽNÉ POLE ---
        self.item_edit = QtWidgets.QLineEdit()
        self.item_edit.setReadOnly(True)
        self.select_item_button = QtWidgets.QPushButton("Vybrat Item")
        self.select_item_button.clicked.connect(self.select_item)

        self.create_item_button = QtWidgets.QPushButton("Vytvořit Nový Item")
        self.create_item_button.clicked.connect(self.create_new_item)
        self.create_item_button.setEnabled(False)

        item_layout = QtWidgets.QHBoxLayout()
        item_layout.addWidget(self.item_edit)
        item_layout.addWidget(self.select_item_button)
        item_layout.addWidget(self.create_item_button)

        # Prop, Type, Cat, Name, Dur
        self.prop_edit = QtWidgets.QLineEdit()
        self.type_edit = QtWidgets.QComboBox()
        self.type_edit.addItems(['house', 'prop', 'light'])

        self.cat_edit = QtWidgets.QComboBox()
        self.load_categories()
        self.manage_categories_button = QtWidgets.QPushButton("Správa kategorií")
        self.manage_categories_button.clicked.connect(self.manage_categories)

        cat_layout = QtWidgets.QHBoxLayout()
        cat_layout.addWidget(self.cat_edit)
        cat_layout.addWidget(self.manage_categories_button)

        self.name_edit = QtWidgets.QLineEdit()

        # Nové pole pro 'dur' (životnost)
        self.dur_edit = QtWidgets.QSpinBox()
        self.dur_edit.setRange(0, 3650)  # 0 až 10 let
        self.dur_edit.setValue(60)  # Výchozí hodnota

        # Nová pole pro 'sell' a 'price'
        self.sell_checkbox = QtWidgets.QCheckBox("Prodat")
        self.sell_checkbox.setChecked(False)  # Výchozí hodnota
        self.sell_checkbox.stateChanged.connect(self.on_sell_changed)

        self.price_spinbox = QtWidgets.QSpinBox()
        self.price_spinbox.setRange(0, 100000)
        self.price_spinbox.setPrefix("$")
        self.price_spinbox.setValue(0)
        self.price_spinbox.setEnabled(False)  # Neaktivní, pokud není 'sell' zaškrtnutý

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Název:", self.name_edit)
        form_layout.addRow("Prop:", self.prop_edit)
        form_layout.addRow("Typ:", self.type_edit)
        form_layout.addRow("Kategorie:", cat_layout)
        form_layout.addRow("Item:", item_layout)
        form_layout.addRow("Životnost (dny):", self.dur_edit)  # Přidání nového pole
        form_layout.addRow(self.sell_checkbox)
        form_layout.addRow("Cena:", self.price_spinbox)  # Nový řádek

        main_layout.addLayout(form_layout)

        self.name_edit.textChanged.connect(self.check_required_fields)
        self.prop_edit.textChanged.connect(self.check_required_fields)
        self.type_edit.currentIndexChanged.connect(self.check_required_fields)
        self.cat_edit.currentIndexChanged.connect(self.check_required_fields)
        self.dur_edit.valueChanged.connect(self.check_required_fields)  # Volitelně, pokud chceš sledovat změny
        self.sell_checkbox.stateChanged.connect(self.check_required_fields)
        self.price_spinbox.valueChanged.connect(self.check_required_fields)  # Volitelně, pokud chceš sledovat změny

        # --- TABULKA PRO MATERIALS ---
        self.materials_table = QtWidgets.QTableWidget()
        self.materials_table.setColumnCount(2)
        self.materials_table.setHorizontalHeaderLabels(["Materiál", "Množství"])
        self.materials_table.horizontalHeader().setStretchLastSection(True)
        self.materials_table.cellDoubleClicked.connect(self.on_material_cell_dblclick)

        materials_buttons_layout = QtWidgets.QHBoxLayout()
        self.add_material_button = QtWidgets.QPushButton("Přidat materiál")
        self.add_material_button.clicked.connect(self.add_material_row)
        self.remove_material_button = QtWidgets.QPushButton("Odebrat označený")
        self.remove_material_button.clicked.connect(self.remove_material_row)
        materials_buttons_layout.addWidget(self.add_material_button)
        materials_buttons_layout.addWidget(self.remove_material_button)

        materials_layout = QtWidgets.QVBoxLayout()
        materials_layout.addWidget(QtWidgets.QLabel("Materials (cena materiálu na opravu):"))
        materials_layout.addWidget(self.materials_table)
        materials_layout.addLayout(materials_buttons_layout)

        # --- TABULKA PRO REPAIR JOBS ---
        self.repairjobs_table = QtWidgets.QTableWidget()
        self.repairjobs_table.setColumnCount(1)
        self.repairjobs_table.setHorizontalHeaderLabels(["Zaměstnání"])
        self.repairjobs_table.horizontalHeader().setStretchLastSection(True)

        repairjobs_buttons_layout = QtWidgets.QHBoxLayout()
        self.add_repairjob_button = QtWidgets.QPushButton("Přidat job")
        self.add_repairjob_button.clicked.connect(self.add_repairjob_row)
        self.remove_repairjob_button = QtWidgets.QPushButton("Odebrat označený")
        self.remove_repairjob_button.clicked.connect(self.remove_repairjob_row)
        repairjobs_buttons_layout.addWidget(self.add_repairjob_button)
        repairjobs_buttons_layout.addWidget(self.remove_repairjob_button)

        repairjobs_layout = QtWidgets.QVBoxLayout()
        repairjobs_layout.addWidget(QtWidgets.QLabel("Repair Jobs (zaměstnání potřebné pro opravu):"))
        repairjobs_layout.addWidget(self.repairjobs_table)
        repairjobs_layout.addLayout(repairjobs_buttons_layout)

        tables_layout = QtWidgets.QHBoxLayout()
        tables_layout.addLayout(materials_layout)
        tables_layout.addLayout(repairjobs_layout)

        main_layout.addLayout(tables_layout)

        # --- OK / CANCEL ---
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self
        )
        buttons.accepted.connect(self.save_housing_prop)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    # --------------------------------------------------------------------------------
    # FUNKCE PRO EVENTS: DVOJITÝ KLIK V TABULCE MATERIALS
    # --------------------------------------------------------------------------------
    def on_material_cell_dblclick(self, row, column):
        """
        Pokud uživatel dvojklikne na sloupec „Materiál“, otevře se stejný dialog
        jako při stisku tlačítka 'Vybrat Item' a do buňky se zapíše vybraný `item`.
        """
        if column == 0:
            dialog = ItemSelectionDialog(self.connection, single_selection=True)
            if dialog.exec_():
                selected_items = dialog.selected_items
                if selected_items:
                    item_str = selected_items[0]['item']
                    self.materials_table.setItem(row, column, QtWidgets.QTableWidgetItem(item_str))

    # --------------------------------------------------------------------------------
    # MATERIÁLY A REPAIR JOBS
    # --------------------------------------------------------------------------------
    def add_material_row(self):
        row = self.materials_table.rowCount()
        self.materials_table.insertRow(row)
        self.materials_table.setItem(row, 0, QtWidgets.QTableWidgetItem(""))  # Materiál
        self.materials_table.setItem(row, 1, QtWidgets.QTableWidgetItem("0")) # Množství

    def remove_material_row(self):
        selected_rows = self.materials_table.selectionModel().selectedRows()
        for index in sorted(selected_rows, reverse=True):
            self.materials_table.removeRow(index.row())

    def add_repairjob_row(self):
        row = self.repairjobs_table.rowCount()
        self.repairjobs_table.insertRow(row)
        self.repairjobs_table.setItem(row, 0, QtWidgets.QTableWidgetItem(""))

    def remove_repairjob_row(self):
        selected_rows = self.repairjobs_table.selectionModel().selectedRows()
        for index in sorted(selected_rows, reverse=True):
            self.repairjobs_table.removeRow(index.row())

    def table_to_materials_dict(self):
        materials = {}
        for row in range(self.materials_table.rowCount()):
            mat_item = self.materials_table.item(row, 0)
            qty_item = self.materials_table.item(row, 1)
            if mat_item and qty_item:
                mat_name = mat_item.text().strip()
                try:
                    quantity = int(qty_item.text().strip())
                except ValueError:
                    quantity = 0
                if mat_name:
                    materials[mat_name] = quantity
        return materials

    def table_to_repairjobs_list(self):
        jobs = []
        for row in range(self.repairjobs_table.rowCount()):
            job_item = self.repairjobs_table.item(row, 0)
            if job_item:
                job_name = job_item.text().strip()
                if job_name:
                    jobs.append(job_name)
        return jobs

    def load_materials_table(self, materials_dict):
        self.materials_table.setRowCount(0)
        for mat_name, quantity in materials_dict.items():
            row_idx = self.materials_table.rowCount()
            self.materials_table.insertRow(row_idx)
            self.materials_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(mat_name))
            self.materials_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(quantity)))

    def load_repairjobs_table(self, jobs_list):
        self.repairjobs_table.setRowCount(0)
        for job_name in jobs_list:
            row_idx = self.repairjobs_table.rowCount()
            self.repairjobs_table.insertRow(row_idx)
            self.repairjobs_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(job_name))

    # --------------------------------------------------------------------------------
    # DALŠÍ FUNKCE
    # --------------------------------------------------------------------------------
    def load_categories(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM aprts_housing_category ORDER BY name")
        categories = cursor.fetchall()

        self.cat_edit.clear()
        for cat in categories:
            self.cat_edit.addItem(cat['name'], cat['id'])

    def manage_categories(self):
        dialog = CategoryManagerDialog(self.connection)
        dialog.exec_()
        current_cat_id = self.cat_edit.currentData()
        self.load_categories()
        if current_cat_id:
            idx = self.cat_edit.findData(current_cat_id)
            if idx >= 0:
                self.cat_edit.setCurrentIndex(idx)

    def check_required_fields(self):
        name_filled = bool(self.name_edit.text().strip())
        prop_filled = bool(self.prop_edit.text().strip())
        type_selected = self.type_edit.currentText() != ''
        cat_selected = self.cat_edit.currentData() is not None
        dur_filled = True  # QSpinBox vždy obsahuje hodnotu
        
        # Nová logika pro 'sell' a 'price'
        sell_checked = self.sell_checkbox.isChecked()
        price_filled = True
        if sell_checked:
            price_filled = self.price_spinbox.value() > 0

        self.create_item_button.setEnabled(
            name_filled and prop_filled and type_selected and cat_selected and dur_filled and price_filled
        )

    def on_sell_changed(self, state):
        self.price_spinbox.setEnabled(state == QtCore.Qt.Checked)
        self.check_required_fields()

    def select_item(self):
        dialog = ItemSelectionDialog(self.connection, single_selection=True)
        if dialog.exec_():
            selected_items = dialog.selected_items
            if selected_items:
                self.item_edit.setText(selected_items[0]['item'])
                self.check_required_fields()

    def create_new_item(self):
        cursor = self.connection.cursor()

        query = "SELECT item FROM items WHERE item LIKE 'housing_prop_%'"
        cursor.execute(query)
        existing_items = cursor.fetchall()

        pattern = re.compile(r'housing_prop_(\d+)')
        existing_numbers = []
        for (item_name,) in existing_items:
            match = pattern.fullmatch(item_name)
            if match:
                existing_numbers.append(int(match.group(1)))

        next_number = 1 if not existing_numbers else (max(existing_numbers) + 1)
        new_item_label = self.name_edit.text()
        new_item_name = f"housing_prop_{next_number:03d}"

        # Získání hodnot z UI
        sell = 1 if self.sell_checkbox.isChecked() else 0
        price = self.price_spinbox.value()

        metadata = {
            'prop': self.prop_edit.text(),
            'type': self.type_edit.currentText(),
            'catID': self.cat_edit.currentData(),
            'catName': self.cat_edit.currentText(),
            'name': self.name_edit.text(),
            'sell': sell,
            'price': price
        }
        meta_json = json.dumps(metadata, ensure_ascii=False)

        insert_query = """
            INSERT INTO items (item, label, weight, `limit`, usable, metadata, image)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            new_item_name,
            new_item_label,
            1,
            10,
            1,
            meta_json,
            new_item_name + '.png'
        )
        try:
            cursor.execute(insert_query, params)
            self.connection.commit()
            self.item_edit.setText(new_item_name)
            QtWidgets.QMessageBox.information(
                self, "Úspěch", f"Nový item '{new_item_name}' byl vytvořen."
            )
            self.check_required_fields()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(
                self, "Chyba", f"Nastala chyba při vytváření itemu: {err}"
            )

    def load_housing_prop(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM aprts_housing_props WHERE id = %s", (self.prop_id,))
        prop = cursor.fetchone()

        if prop:
            self.item_edit.setText(prop['item'] or '')
            self.prop_edit.setText(prop['prop'] or '')
            idx_type = self.type_edit.findText(prop.get('type', 'house'))
            if idx_type >= 0:
                self.type_edit.setCurrentIndex(idx_type)

            cat_id = prop.get('catID')
            if cat_id:
                idx_cat = self.cat_edit.findData(cat_id)
                if idx_cat >= 0:
                    self.cat_edit.setCurrentIndex(idx_cat)

            self.name_edit.setText(prop.get('name') or '')

            # Načtení 'dur'
            dur_value = prop.get('dur', 60)
            try:
                dur_int = int(dur_value)
                self.dur_edit.setValue(dur_int)
            except ValueError:
                self.dur_edit.setValue(60)  # Výchozí hodnota při chybě

            # Načtení 'sell' a 'price'
            sell_value = prop.get('sell', 0)
            self.sell_checkbox.setChecked(bool(sell_value))
            price_value = prop.get('price', 0)
            self.price_spinbox.setValue(price_value)
            self.price_spinbox.setEnabled(bool(sell_value))

            materials_json = prop.get('materials', '{}') or '{}'
            repairjobs_json = prop.get('repairJobs', '[]') or '[]'

            try:
                self.materials_data = json.loads(materials_json)
                if not isinstance(self.materials_data, dict):
                    self.materials_data = {}
            except:
                self.materials_data = {}

            try:
                self.repairjobs_data = json.loads(repairjobs_json)
                if not isinstance(self.repairjobs_data, list):
                    self.repairjobs_data = []
            except:
                self.repairjobs_data = []

            self.load_materials_table(self.materials_data)
            self.load_repairjobs_table(self.repairjobs_data)
            self.check_required_fields()

    def save_housing_prop(self):
        item = self.item_edit.text() or None
        prop = self.prop_edit.text() or None
        type_ = self.type_edit.currentText()
        cat_id = self.cat_edit.currentData()
        name = self.name_edit.text() or None
        dur = self.dur_edit.value()  # Získání hodnoty z QSpinBox
        sell = 1 if self.sell_checkbox.isChecked() else 0  # 1 = True, 0 = False
        price = self.price_spinbox.value()

        if not item:
            QtWidgets.QMessageBox.warning(
                self, "Chyba", "Pole 'Item' nesmí být prázdné."
            )
            return

        # Validace ceny, pokud je 'sell' zaškrtnutý
        if sell and not (0 <= price <= 100000):
            QtWidgets.QMessageBox.warning(
                self, "Chyba", "Cena musí být v rozmezí 0 - 100000."
            )
            return

        self.materials_data = self.table_to_materials_dict()
        self.repairjobs_data = self.table_to_repairjobs_list()

        materials_json = json.dumps(self.materials_data, ensure_ascii=False)
        repairjobs_json = json.dumps(self.repairjobs_data, ensure_ascii=False)

        cursor = self.connection.cursor()
        if self.prop_id:
            query = """
                UPDATE aprts_housing_props
                   SET item=%s, prop=%s, type=%s, catID=%s, name=%s,
                       dur=%s, materials=%s, repairJobs=%s,
                       sell=%s, price=%s
                 WHERE id=%s
            """
            params = (item, prop, type_, cat_id, name, dur,
                      materials_json, repairjobs_json, sell, price, self.prop_id)
        else:
            query = """
                INSERT INTO aprts_housing_props
                    (item, prop, type, catID, name, dur, materials, repairJobs, sell, price)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (item, prop, type_, cat_id, name, dur,
                      materials_json, repairjobs_json, sell, price)

        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except Exception as err:
            QtWidgets.QMessageBox.critical(
                self, "Chyba", f"Nastala chyba při ukládání: {err}"
            )


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='s29_dev-redm'
    )

    dialog = HousingPropDialog(conn)
    if dialog.exec_():
        print("Uloženo")
    else:
        print("Storno")

    sys.exit(app.exec_())
