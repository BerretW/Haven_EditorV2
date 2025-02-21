import sys
import os
import json
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Importujeme ItemSelectionDialog
from item_manager import ItemSelectionDialog

# Importujeme StoreManagerStoresDialog z nového souboru
from store_manager_stores import StoreManagerStoresDialog

# Importujeme potřebné třídy
from PyQt5.QtWidgets import QStyledItemDelegate, QComboBox

class StoreManagerDialog(QtWidgets.QDialog):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.setWindowTitle("Správa Obchodů")
        self.resize(1000, 600)
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        # Přidáme tab widget pro položky a kategorie
        self.tab_widget = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Tab pro správu položek
        self.items_tab = QtWidgets.QWidget()
        self.init_items_tab()
        self.tab_widget.addTab(self.items_tab, "Položky")

        # Tab pro správu kategorií
        self.categories_tab = QtWidgets.QWidget()
        self.init_categories_tab()
        self.tab_widget.addTab(self.categories_tab, "Kategorie")

        # Tab pro správu obchodníků
        self.stores_tab = StoreManagerStoresDialog(self.connection)
        self.tab_widget.addTab(self.stores_tab, "Obchody")

    def init_items_tab(self):
        main_layout = QtWidgets.QVBoxLayout()
        self.items_tab.setLayout(main_layout)

        # Vyhledávací pole
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.item_search_edit = QtWidgets.QLineEdit()
        self.item_search_edit.setPlaceholderText("Zadejte hledaný text...")
        self.item_search_edit.returnPressed.connect(self.load_items)
        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.load_items)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.item_search_edit)
        search_layout.addWidget(search_button)

        main_layout.addLayout(search_layout)

        # Hlavní rozložení pro tabulku položek a seznam kategorií
        content_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(content_layout)

        # Tabulka položek
        self.items_table = QtWidgets.QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels(['ID', 'Item', 'Kategorie', 'Cena Nákup', 'Cena Prodej', 'Akce'])
        self.items_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.items_table.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)  # Povolit výběr více řádků
        self.items_table.setEditTriggers(QtWidgets.QAbstractItemView.SelectedClicked)
        self.items_table.setSortingEnabled(True)
        content_layout.addWidget(self.items_table)
        content_layout.setStretch(0, 3)  # Nastavíme poměr velikosti

        # Seznam kategorií
        self.category_list_widget = QtWidgets.QListWidget()
        self.category_list_widget.clicked.connect(self.category_selected)
        content_layout.addWidget(self.category_list_widget)
        content_layout.setStretch(1, 1)  # Nastavíme poměr velikosti
        self.category_list_widget.setFixedWidth(200)  # Nastavíme pevnou šířku seznamu kategorií

        # Tlačítka
        buttons_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat Položku")
        add_button.clicked.connect(self.add_item)
        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.clicked.connect(self.load_items)

        # Nová tlačítka pro hromadnou změnu cen
        bulk_price_b_button = QtWidgets.QPushButton("Hromadná Změna Cena Nákup")
        bulk_price_b_button.clicked.connect(self.bulk_change_price_b)
        bulk_price_s_button = QtWidgets.QPushButton("Hromadná Změna Cena Prodej")
        bulk_price_s_button.clicked.connect(self.bulk_change_price_s)

        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(refresh_button)
        buttons_layout.addWidget(bulk_price_b_button)
        buttons_layout.addWidget(bulk_price_s_button)
        main_layout.addLayout(buttons_layout)

        self.load_categories()  # Načteme kategorie do seznamu kategorií
        self.load_items()

        # Vytvoříme seznam kategorií pro delegate
        self.update_category_delegate()

    def load_categories(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM aprts_store_item_categories ORDER BY name")
        categories = cursor.fetchall()
        self.category_list_widget.clear()
        # Přidáme položku "Všechny Kategorie"
        all_item = QtWidgets.QListWidgetItem("Všechny Kategorie")
        all_item.setData(QtCore.Qt.UserRole, None)
        self.category_list_widget.addItem(all_item)
        for category in categories:
            item = QtWidgets.QListWidgetItem(category['name'])
            item.setData(QtCore.Qt.UserRole, category['id'])
            self.category_list_widget.addItem(item)

        # Aktualizujeme seznam kategorií pro delegate
        self.update_category_delegate()

    def category_selected(self, index):
        self.load_items()

    def load_items(self):
        search_text = self.item_search_edit.text().strip()
        selected_item = self.category_list_widget.currentItem()
        selected_category_id = selected_item.data(QtCore.Qt.UserRole) if selected_item else None

        cursor = self.connection.cursor(dictionary=True)
        query = """
            SELECT i.id, i.item_code, c.name AS category_name, i.price_b, i.price_s, i.category_id
            FROM aprts_store_items i
            LEFT JOIN aprts_store_item_categories c ON i.category_id = c.id
            WHERE (i.item_code LIKE %s OR c.name LIKE %s)
        """
        params = [f"%{search_text}%", f"%{search_text}%"]

        if selected_category_id is not None:
            query += " AND i.category_id = %s"
            params.append(selected_category_id)

        cursor.execute(query, params)
        items = cursor.fetchall()
        self.items_table.setRowCount(0)
        for row_number, item in enumerate(items):
            self.items_table.insertRow(row_number)

            id_item = QtWidgets.QTableWidgetItem(str(item['id']))
            self.items_table.setItem(row_number, 0, id_item)

            item_code_item = QtWidgets.QTableWidgetItem(item['item_code'])
            self.items_table.setItem(row_number, 1, item_code_item)

            category_item = QtWidgets.QTableWidgetItem(item['category_name'] or '')
            category_item.setData(QtCore.Qt.UserRole, item['category_id'])
            # Nastavíme flag, aby byla buňka editovatelná
            category_item.setFlags(category_item.flags() | QtCore.Qt.ItemIsEditable)
            self.items_table.setItem(row_number, 2, category_item)

            price_b_item = QtWidgets.QTableWidgetItem(f"{item['price_b']:.2f}")
            self.items_table.setItem(row_number, 3, price_b_item)

            price_s_item = QtWidgets.QTableWidgetItem(f"{item['price_s']:.2f}")
            self.items_table.setItem(row_number, 4, price_s_item)

            # Akční tlačítka
            action_widget = self.create_item_action_buttons(item['id'])
            self.items_table.setCellWidget(row_number, 5, action_widget)

        self.items_table.resizeColumnsToContents()
        # Nastavení pevné šířky sloupce 'Kategorie'
        self.items_table.setColumnWidth(2, 150)

    def create_item_action_buttons(self, item_id):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.clicked.connect(lambda: self.edit_item(item_id))
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        layout.addWidget(edit_button)

        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.clicked.connect(lambda: self.delete_item(item_id))
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        layout.addWidget(delete_button)

        widget.setLayout(layout)
        return widget

    def add_item(self):
        dialog = StoreItemDialog(self.connection)
        if dialog.exec_():
            self.load_items()

    def edit_item(self, item_id):
        dialog = StoreItemDialog(self.connection, item_id)
        if dialog.exec_():
            self.load_items()

    def delete_item(self, item_id):
        confirm = QtWidgets.QMessageBox.question(self, "Potvrdit smazání",
                                                 "Opravdu chcete smazat tuto položku?",
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM aprts_store_items WHERE id = %s", (item_id,))
            self.connection.commit()
            self.load_items()

    def init_categories_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.categories_tab.setLayout(layout)

        # Vyhledávací pole
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.category_search_edit = QtWidgets.QLineEdit()
        self.category_search_edit.setPlaceholderText("Zadejte hledaný text...")
        self.category_search_edit.returnPressed.connect(self.load_categories_tab)
        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.load_categories_tab)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.category_search_edit)
        search_layout.addWidget(search_button)

        layout.addLayout(search_layout)

        # Tabulka kategorií
        self.categories_table = QtWidgets.QTableWidget()
        self.categories_table.setColumnCount(3)
        self.categories_table.setHorizontalHeaderLabels(['ID', 'Název', 'Akce'])
        self.categories_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.categories_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.categories_table.setSortingEnabled(True)  # Povolit řazení
        layout.addWidget(self.categories_table)

        # Tlačítka
        buttons_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat Kategorii")
        add_button.clicked.connect(self.add_category)
        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.clicked.connect(self.load_categories_tab)
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(refresh_button)
        layout.addLayout(buttons_layout)

        self.load_categories_tab()

    def load_categories_tab(self):
        search_text = self.category_search_edit.text().strip()
        cursor = self.connection.cursor(dictionary=True)
        query = """
            SELECT id, name
            FROM aprts_store_item_categories
            WHERE name LIKE %s
            ORDER BY name
        """
        search_pattern = f"%{search_text}%"
        cursor.execute(query, (search_pattern,))
        categories = cursor.fetchall()
        self.categories_table.setRowCount(0)
        for row_number, category in enumerate(categories):
            self.categories_table.insertRow(row_number)

            id_item = QtWidgets.QTableWidgetItem(str(category['id']))
            self.categories_table.setItem(row_number, 0, id_item)

            name_item = QtWidgets.QTableWidgetItem(category['name'])
            self.categories_table.setItem(row_number, 1, name_item)

            # Akční tlačítka
            action_widget = self.create_category_action_buttons(category['id'])
            self.categories_table.setCellWidget(row_number, 2, action_widget)

        self.categories_table.resizeColumnsToContents()

    def create_category_action_buttons(self, category_id):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.clicked.connect(lambda: self.edit_category(category_id))
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        layout.addWidget(edit_button)

        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.clicked.connect(lambda: self.delete_category(category_id))
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        layout.addWidget(delete_button)

        widget.setLayout(layout)
        return widget

    def add_category(self):
        dialog = StoreCategoryDialog(self.connection)
        if dialog.exec_():
            self.load_categories_tab()
            self.load_categories()  # Aktualizujeme seznam kategorií
            self.load_items()  # Aktualizujeme položky
            self.update_category_delegate()

    def edit_category(self, category_id):
        dialog = StoreCategoryDialog(self.connection, category_id)
        if dialog.exec_():
            self.load_categories_tab()
            self.load_categories()  # Aktualizujeme seznam kategorií
            self.load_items()  # Aktualizujeme položky
            self.update_category_delegate()

    def delete_category(self, category_id):
        confirm = QtWidgets.QMessageBox.question(self, "Potvrdit smazání",
                                                 "Opravdu chcete smazat tuto kategorii? Položky v této kategorii budou ztraceny.",
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM aprts_store_item_categories WHERE id = %s", (category_id,))
            # Nastavíme category_id na NULL pro položky s touto kategorií
            cursor.execute("UPDATE aprts_store_items SET category_id = NULL WHERE category_id = %s", (category_id,))
            self.connection.commit()
            self.load_categories_tab()
            self.load_categories()  # Aktualizujeme seznam kategorií
            self.load_items()
            self.update_category_delegate()

    def update_category_delegate(self):
        # Aktualizujeme seznam kategorií pro delegate
        self.category_list = []
        for i in range(self.category_list_widget.count()):
            item = self.category_list_widget.item(i)
            category_id = item.data(QtCore.Qt.UserRole)
            category_name = item.text()
            if category_id is not None:  # Vynecháme "Všechny Kategorie"
                self.category_list.append((category_id, category_name))
        # Pokud již existuje delegate, aktualizujeme ho
        if hasattr(self, 'category_delegate'):
            self.category_delegate.categories = self.category_list
        else:
            # Vytvoříme delegate pro sloupec "Kategorie" (index 2)
            self.category_delegate = CategoryDelegate(self.items_table, self.category_list, self.connection)
            self.items_table.setItemDelegateForColumn(2, self.category_delegate)

    def bulk_change_price_b(self):
        self.bulk_change_price(price_type='price_b')

    def bulk_change_price_s(self):
        self.bulk_change_price(price_type='price_s')

    def bulk_change_price(self, price_type):
        selected_items = self.items_table.selectionModel().selectedRows()
        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "Upozornění", "Vyberte alespoň jednu položku.")
            return

        price_label = "Cena Nákup" if price_type == 'price_b' else "Cena Prodej"
        price, ok = QtWidgets.QInputDialog.getDouble(self, "Hromadná Změna", f"Zadejte novou hodnotu pro {price_label}:", decimals=2)
        if ok:
            cursor = self.connection.cursor()
            for index in selected_items:
                row = index.row()
                item_id = int(self.items_table.item(row, 0).text())
                query = f"UPDATE aprts_store_items SET {price_type} = %s WHERE id = %s"
                cursor.execute(query, (price, item_id))
                # Aktualizujeme hodnotu v tabulce
                if price_type == 'price_b':
                    self.items_table.item(row, 3).setText(f"{price:.2f}")
                else:
                    self.items_table.item(row, 4).setText(f"{price:.2f}")
            self.connection.commit()
            QtWidgets.QMessageBox.information(self, "Úspěch", f"{price_label} byla úspěšně změněna pro vybrané položky.")

class CategoryDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent, categories, connection):
        super().__init__(parent)
        self.categories = categories  # Seznam kategorií ve formátu [(id, name), ...]
        self.connection = connection

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        for category_id, category_name in self.categories:
            combo.addItem(category_name, category_id)
        return combo

    def setEditorData(self, editor, index):
        category_id = index.data(QtCore.Qt.UserRole)
        idx = editor.findData(category_id)
        if idx >= 0:
            editor.setCurrentIndex(idx)

    def setModelData(self, editor, model, index):
        category_id = editor.currentData()
        category_name = editor.currentText()
        model.setData(index, category_name, QtCore.Qt.DisplayRole)
        model.setData(index, category_id, QtCore.Qt.UserRole)
        # Získáme ID položky z modelu
        id_index = model.index(index.row(), 0, index.parent())  # Sloupec 0 je ID
        item_id = model.data(id_index, QtCore.Qt.DisplayRole)
        self.update_category_in_db(item_id, category_id)

    def update_category_in_db(self, item_id, category_id):
        cursor = self.connection.cursor()
        query = "UPDATE aprts_store_items SET category_id = %s WHERE id = %s"
        cursor.execute(query, (category_id, item_id))
        self.connection.commit()

class StoreItemDialog(QtWidgets.QDialog):
    def __init__(self, connection, item_id=None):
        super().__init__()
        self.connection = connection
        self.item_id = item_id
        self.setWindowTitle("Položka Obchodu")
        self.init_ui()
        if self.item_id:
            self.load_item()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_layout = QtWidgets.QFormLayout()

        # Nahradíme QLineEdit za QLineEdit s tlačítkem pro výběr položky
        item_layout = QtWidgets.QHBoxLayout()
        self.item_code_edit = QtWidgets.QLineEdit()
        self.item_code_edit.setReadOnly(True)  # Nastavíme pole pouze pro čtení
        select_item_button = QtWidgets.QPushButton("Vybrat Položku")
        select_item_button.clicked.connect(self.select_item)
        item_layout.addWidget(self.item_code_edit)
        item_layout.addWidget(select_item_button)

        self.category_combo = QtWidgets.QComboBox()
        self.load_categories()
        self.price_b_edit = QtWidgets.QDoubleSpinBox()
        self.price_b_edit.setMaximum(9999999)
        self.price_b_edit.setDecimals(2)
        self.price_s_edit = QtWidgets.QDoubleSpinBox()
        self.price_s_edit.setMaximum(9999999)
        self.price_s_edit.setDecimals(2)

        form_layout.addRow("Item:", item_layout)
        form_layout.addRow("Kategorie:", self.category_combo)
        form_layout.addRow("Cena Nákup:", self.price_b_edit)
        form_layout.addRow("Cena Prodej:", self.price_s_edit)

        layout.addLayout(form_layout)

        # Tlačítka
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.save_item)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def select_item(self):
        dialog = ItemSelectionDialog(self.connection, single_selection=True)
        if dialog.exec_():
            if dialog.selected_items:
                selected_item = dialog.selected_items[0]
                self.item_code_edit.setText(selected_item['item'])

    def load_categories(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM aprts_store_item_categories ORDER BY name")
        categories = cursor.fetchall()
        self.category_combo.clear()
        for category in categories:
            self.category_combo.addItem(category['name'], category['id'])

    def load_item(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM aprts_store_items WHERE id = %s", (self.item_id,))
        item = cursor.fetchone()
        if item:
            self.item_code_edit.setText(item['item_code'])
            index = self.category_combo.findData(item['category_id'])
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
            self.price_b_edit.setValue(float(item['price_b']))
            self.price_s_edit.setValue(float(item['price_s']))

    def save_item(self):
        item_code = self.item_code_edit.text().strip()
        category_id = self.category_combo.currentData()
        price_b = self.price_b_edit.value()
        price_s = self.price_s_edit.value()

        if not item_code:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Musíte vybrat položku.")
            return

        cursor = self.connection.cursor()
        if self.item_id:
            query = """
                UPDATE aprts_store_items SET
                item_code = %s, category_id = %s, price_b = %s, price_s = %s
                WHERE id = %s
            """
            params = (item_code, category_id, price_b, price_s, self.item_id)
        else:
            query = """
                INSERT INTO aprts_store_items (item_code, category_id, price_b, price_s)
                VALUES (%s, %s, %s, %s)
            """
            params = (item_code, category_id, price_b, price_s)
        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")

class StoreCategoryDialog(QtWidgets.QDialog):
    def __init__(self, connection, category_id=None):
        super().__init__()
        self.connection = connection
        self.category_id = category_id
        self.setWindowTitle("Kategorie Obchodu")
        self.init_ui()
        if self.category_id:
            self.load_category()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_layout = QtWidgets.QFormLayout()

        self.name_edit = QtWidgets.QLineEdit()

        form_layout.addRow("Název Kategorie:", self.name_edit)

        layout.addLayout(form_layout)

        # Tlačítka
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.save_category)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_category(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM aprts_store_item_categories WHERE id = %s", (self.category_id,))
        category = cursor.fetchone()
        if category:
            self.name_edit.setText(category['name'])

    def save_category(self):
        name = self.name_edit.text().strip()

        if not name:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'Název Kategorie' nesmí být prázdné.")
            return

        cursor = self.connection.cursor()
        if self.category_id:
            query = """
                UPDATE aprts_store_item_categories SET
                name = %s
                WHERE id = %s
            """
            params = (name, self.category_id)
        else:
            query = """
                INSERT INTO aprts_store_item_categories (name)
                VALUES (%s)
            """
            params = (name,)
        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # Zde můžete přidat připojení k databázi pro testování
    # connection = mysql.connector.connect(...)
    # dialog = StoreManagerDialog(connection)
    # dialog.exec_()
    pass
