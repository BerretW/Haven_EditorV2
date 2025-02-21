
from PyQt5 import QtWidgets, QtGui, QtCore
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
class CategoryManagerDialog(QtWidgets.QDialog):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.setWindowTitle("Správa Kategorií")
        self.resize(400, 300)
        self.load_stylesheet(os.path.join(BASE_DIR, "stylesheet.qss"))
        self.init_ui()
        self.load_categories()
    def load_stylesheet(self, filepath):
        """Načte stylesheet z externího souboru."""
        try:
            with open(filepath, "r") as file:
                self.setStyleSheet(file.read())
        except Exception as e:
            print(f"Chyba při načítání stylů: {e}")
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()

        # Tabulka pro zobrazení kategorií
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['ID', 'Název Kategorie'])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        # Tlačítka
        button_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat")
        add_button.clicked.connect(self.add_category)
        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.clicked.connect(self.edit_category)
        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.clicked.connect(self.delete_category)
        close_button = QtWidgets.QPushButton("Zavřít")
        close_button.clicked.connect(self.accept)

        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_categories(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT ID, name FROM recipes_category ORDER BY name")
        categories = cursor.fetchall()
        self.table.setRowCount(0)
        for row_number, category in enumerate(categories):
            self.table.insertRow(row_number)
            id_item = QtWidgets.QTableWidgetItem(str(category['ID']))
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            name_item = QtWidgets.QTableWidgetItem(category['name'])
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 0, id_item)
            self.table.setItem(row_number, 1, name_item)
        self.table.resizeColumnsToContents()

    def add_category(self):
        text, ok = QtWidgets.QInputDialog.getText(self, "Přidat Kategorii", "Název Kategorie:")
        if ok and text:
            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO recipes_category (name) VALUES (%s)", (text,))
            self.connection.commit()
            self.load_categories()

    def edit_category(self):
        selected_items = self.table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            category_id = int(self.table.item(row, 0).text())
            current_name = self.table.item(row, 1).text()
            text, ok = QtWidgets.QInputDialog.getText(self, "Upravit Kategorii", "Název Kategorie:", text=current_name)
            if ok and text:
                cursor = self.connection.cursor()
                cursor.execute("UPDATE recipes_category SET name = %s WHERE ID = %s", (text, category_id))
                self.connection.commit()
                self.load_categories()
        else:
            QtWidgets.QMessageBox.warning(self, "Upozornění", "Vyberte kategorii k úpravě.")

    def delete_category(self):
        selected_items = self.table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            category_id = int(self.table.item(row, 0).text())
            confirm = QtWidgets.QMessageBox.question(self, "Potvrdit smazání",
                                                     "Opravdu chcete smazat tuto kategorii?",
                                                     QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if confirm == QtWidgets.QMessageBox.Yes:
                cursor = self.connection.cursor()
                # Zkontrolujeme, zda jsou kategorie přiřazeny nějaké recepty
                cursor.execute("SELECT COUNT(*) AS count FROM recipes WHERE category_id = %s", (category_id,))
                result = cursor.fetchone()
                if result['count'] > 0:
                    QtWidgets.QMessageBox.warning(self, "Upozornění", "Nelze smazat kategorii, která je přiřazena receptům.")
                else:
                    cursor.execute("DELETE FROM recipes_category WHERE ID = %s", (category_id,))
                    self.connection.commit()
                    self.load_categories()
        else:
            QtWidgets.QMessageBox.warning(self, "Upozornění", "Vyberte kategorii ke smazání.")