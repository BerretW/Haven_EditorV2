import sys
import os
import re
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from item_manager import ItemDialog
from housing_props_dialog import HousingPropDialog
from housing_category_dialog import CategoryManagerDialog  # Přidán import CategoryManagerDialog

class HousingPropsManager(QtWidgets.QDialog):
    def __init__(self, connection, item_code=None, is_new=False):
        super().__init__()
        self.connection = connection
        self.item_code = item_code
        self.is_new = is_new
        self.setWindowTitle("Správa Housing Props")
        self.setGeometry(100, 100, 1600, 800)  # Zvýšení šířky a výšky okna
        self.selected_category_id = None  # ID vybrané kategorie

        self.init_ui()

        # Pokud máme předaný item_code, buď jej přidáme (is_new), nebo jej rovnou editujeme
        if self.item_code:
            if self.is_new:
                self.add_housing_prop(item_code=self.item_code)
            else:
                self.edit_housing_prop_by_item_code(self.item_code)

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Vyhledávací pole a filtry
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Zadejte hledaný text...")
        self.search_edit.returnPressed.connect(self.load_housing_props)

        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.load_housing_props)

        # Checkbox pro filtrování propů bez existujícího itemu
        self.missing_items_checkbox = QtWidgets.QCheckBox("Zobrazit pouze propy bez existujícího itemu")
        self.missing_items_checkbox.stateChanged.connect(self.load_housing_props)

        # Filtr pro 'sell' status
        sell_filter_label = QtWidgets.QLabel("Prodej:")
        self.sell_filter_combo = QtWidgets.QComboBox()
        self.sell_filter_combo.addItems(["Vše", "Na prodej", "Neprodej"])
        self.sell_filter_combo.currentIndexChanged.connect(self.load_housing_props)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(search_button)
        search_layout.addWidget(self.missing_items_checkbox)
        search_layout.addWidget(sell_filter_label)
        search_layout.addWidget(self.sell_filter_combo)
        layout.addLayout(search_layout)

        # Filtr kategorií
        category_filter_layout = QtWidgets.QHBoxLayout()
        category_label = QtWidgets.QLabel("Kategorie:")
        self.category_combo = QtWidgets.QComboBox()
        self.category_combo.addItem("Všechny kategorie", None)
        self.category_combo.currentIndexChanged.connect(self.on_category_selected)

        category_filter_layout.addWidget(category_label)
        category_filter_layout.addWidget(self.category_combo)

        # Tlačítko pro správu kategorií
        self.manage_categories_button = QtWidgets.QPushButton("Správa kategorií")
        self.manage_categories_button.clicked.connect(self.manage_categories)
        category_filter_layout.addWidget(self.manage_categories_button)

        layout.addLayout(category_filter_layout)

        # Tabulka
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(9)  # Aktualizováno pro nové sloupce
        self.table.setHorizontalHeaderLabels([
            'ID', 'Item', 'Prop', 'Typ', 'Kategorie', 'Název',
            'Prodej', 'Cena ($)', 'Akce'
        ])
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # Tlačítka
        buttons_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat")
        add_button.setStyleSheet("background-color: #5cb85c; color: white;")
        add_button.clicked.connect(self.add_housing_prop)

        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.setStyleSheet("background-color: #5bc0de; color: white;")
        refresh_button.clicked.connect(self.refresh)

        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(refresh_button)
        layout.addLayout(buttons_layout)

        # Načteme kategorie a poté housing props
        self.load_categories()
        self.load_housing_props()

    def load_categories(self):
        """Načte seznam kategorií pro filtr z tabulky aprts_housing_category."""
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM aprts_housing_category ORDER BY name")
            categories = cursor.fetchall()

            # Zablokujeme signály během aktualizace
            self.category_combo.blockSignals(True)
            self.category_combo.clear()
            self.category_combo.addItem("Všechny kategorie", None)
            for cat in categories:
                self.category_combo.addItem(cat['name'], cat['id'])
            self.category_combo.blockSignals(False)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při načítání kategorií: {e}")

    def on_category_selected(self):
        """Uloží vybranou kategorii (ID) a znovu načte housing props."""
        self.selected_category_id = self.category_combo.currentData()
        self.load_housing_props()

    def load_housing_props(self):
        """Načte data z tabulky aprts_housing_props a zobrazí je v tabulce."""
        try:
            search_text = self.search_edit.text().strip()
            show_missing_items_only = self.missing_items_checkbox.isChecked()
            sell_filter = self.sell_filter_combo.currentText()

            cursor = self.connection.cursor(dictionary=True)
            conditions = []
            params = []

            # Postavíme WHERE klauzuli podle filtrů
            if search_text:
                conditions.append("(hp.item LIKE %s OR hp.prop LIKE %s OR i.label LIKE %s OR hp.name LIKE %s)")
                pattern = f"%{search_text}%"
                params.extend([pattern] * 4)

            if show_missing_items_only:
                conditions.append("i.item IS NULL")

            if sell_filter == "Na prodej":
                conditions.append("hp.sell = 1")
            elif sell_filter == "Neprodej":
                conditions.append("hp.sell = 0")

            if self.selected_category_id:
                conditions.append("hp.catID = %s")
                params.append(self.selected_category_id)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT
                    hp.*,
                    i.label AS item_label,
                    c.name AS category_name
                FROM aprts_housing_props hp
                LEFT JOIN items i ON hp.item = i.item
                LEFT JOIN aprts_housing_category c ON hp.catID = c.id
                {where_clause}
            """
            cursor.execute(query, params)
            housing_props = cursor.fetchall()

            # Optimalizace: Dočasně vypneme signály a třídění, pak tabulku najednou naplníme
            self.table.blockSignals(True)
            self.table.setSortingEnabled(False)
            self.table.setRowCount(len(housing_props))

            for row_number, prop in enumerate(housing_props):
                id_value = prop.get('id', '')
                item_value = prop.get('item', '')
                item_label = prop.get('item_label', '')
                prop_value = prop.get('prop', '')
                type_value = prop.get('type', '')
                cat_name_value = prop.get('category_name', '')
                name_value = prop.get('name', '')
                sell_value = prop.get('sell', 0)
                price_value = prop.get('price', 0)

                # ID
                id_item = QtWidgets.QTableWidgetItem(str(id_value))
                id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table.setItem(row_number, 0, id_item)

                # Item
                if item_label:
                    item_display = f"{item_value} ({item_label})"
                else:
                    item_display = item_value
                item_item = QtWidgets.QTableWidgetItem(item_display)
                item_item.setFlags(item_item.flags() & ~QtCore.Qt.ItemIsEditable)
                # Pokud k itemu neexistuje label, zbarvíme buňku
                if not item_label:
                    item_item.setBackground(QtGui.QColor(255, 200, 200))
                self.table.setItem(row_number, 1, item_item)

                # Prop
                prop_item = QtWidgets.QTableWidgetItem(prop_value)
                prop_item.setFlags(prop_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table.setItem(row_number, 2, prop_item)

                # Typ
                type_item = QtWidgets.QTableWidgetItem(type_value)
                type_item.setFlags(type_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table.setItem(row_number, 3, type_item)

                # Kategorie
                cat_item = QtWidgets.QTableWidgetItem(cat_name_value)
                cat_item.setFlags(cat_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table.setItem(row_number, 4, cat_item)

                # Název
                name_item = QtWidgets.QTableWidgetItem(name_value)
                name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table.setItem(row_number, 5, name_item)

                # Prodej
                sell_display = "Ano" if sell_value else "Ne"
                sell_item = QtWidgets.QTableWidgetItem(sell_display)
                sell_item.setFlags(sell_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table.setItem(row_number, 6, sell_item)

                # Cena
                price_display = f"${price_value}"
                price_item = QtWidgets.QTableWidgetItem(price_display)
                price_item.setFlags(price_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table.setItem(row_number, 7, price_item)

                # Akce
                action_widget = self.create_action_buttons(id_value, item_value)
                self.table.setCellWidget(row_number, 8, action_widget)

            # Jednorázové přizpůsobení sloupců
            self.table.resizeColumnsToContents()

            # Zase povolíme signály a zapneme třídění
            self.table.setSortingEnabled(True)
            self.table.blockSignals(False)

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při načítání dat: {e}")

    def create_action_buttons(self, prop_id, item_name):
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)

        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        edit_button.clicked.connect(lambda _, pid=prop_id: self.edit_housing_prop_by_id(pid))
        h_layout.addWidget(edit_button)

        edit_item_button = QtWidgets.QPushButton("Upravit Item")
        edit_item_button.setStyleSheet("background-color: #5bc0de; color: white;")
        edit_item_button.clicked.connect(lambda _, name=item_name: self.edit_item_by_name(name))
        h_layout.addWidget(edit_item_button)

        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        delete_button.clicked.connect(lambda _, pid=prop_id: self.delete_housing_prop_by_id(pid))
        h_layout.addWidget(delete_button)

        widget.setLayout(h_layout)
        return widget

    def edit_item_by_name(self, item_name):
        if not item_name:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Tento záznam nemá přiřazený item.")
            return
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM items WHERE item = %s", (item_name,))
        item = cursor.fetchone()
        if item:
            dialog = ItemDialog(self.connection, item_name)
            if dialog.exec_():
                # Po úpravě itemu můžeme aktualizovat zobrazení
                self.load_housing_props()
        else:
            QtWidgets.QMessageBox.warning(self, "Chyba", f"Item '{item_name}' nebyl nalezen v databázi.")

    def on_table_double_clicked(self, row, column):
        id_item = self.table.item(row, 0)  # Sloupec 0 je ID
        if id_item:
            prop_id = int(id_item.text())
            self.edit_housing_prop_by_id(prop_id)

    def add_housing_prop(self, item_code=None):
        dialog = HousingPropDialog(self.connection, item_code=item_code)
        if dialog.exec_():
            self.load_housing_props()

    def edit_housing_prop_by_id(self, prop_id):
        dialog = HousingPropDialog(self.connection, prop_id=prop_id)
        if dialog.exec_():
            self.load_housing_props()

    def edit_housing_prop_by_item_code(self, item_code):
        """Najde housing prop podle item_code, pokud neexistuje, tak vytvoří nový."""
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT id FROM aprts_housing_props WHERE item = %s", (item_code,))
        prop = cursor.fetchone()
        if prop:
            self.edit_housing_prop_by_id(prop['id'])
        else:
            self.add_housing_prop(item_code=item_code)

    def delete_housing_prop_by_id(self, prop_id):
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Potvrdit smazání",
            "Opravdu chcete smazat tento záznam?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            try:
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM aprts_housing_props WHERE id = %s", (prop_id,))
                self.connection.commit()
                self.load_housing_props()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při mazání záznamu: {e}")

    def manage_categories(self):
        """Otevře dialog pro správu kategorií a po jeho zavření znovu načte kategorie."""
        dialog = CategoryManagerDialog(self.connection)
        dialog.exec_()
        self.load_categories()  # Znovu načteme kategorie po zavření dialogu

    def refresh(self):
        """Obnoví jak kategorie, tak housing props."""
        self.load_categories()
        self.load_housing_props()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    try:
        connection = mysql.connector.connect(
            host='db-server.kkrp.cz',
            user='spoiledmouse',
            password='bE8e7AqiG8w43itITaf361Bu8182Ku*',
            database='s29_dev-redm'
        )
    except mysql.connector.Error as err:
        print(f"Chyba při připojování k databázi: {err}")
        sys.exit(1)

    dialog = HousingPropsManager(connection=connection)
    if dialog.exec_():
        print("Pole bylo úspěšně uloženo.")
    else:
        print("Ukládání pole bylo zrušeno.")

    connection.close()
    sys.exit(0)
