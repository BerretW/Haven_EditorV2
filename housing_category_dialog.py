import sys
import os
from PyQt5 import QtWidgets, QtCore
import mysql.connector

class CategoryManagerDialog(QtWidgets.QDialog):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.setWindowTitle("Správa kategorií")
        self.setGeometry(100, 100, 400, 300)

        self.init_ui()
        self.load_categories()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Tabulka kategorií
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['ID', 'Název'])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.cellDoubleClicked.connect(self.edit_selected)
        layout.addWidget(self.table)

        # Tlačítka pro správu
        btn_layout = QtWidgets.QHBoxLayout()

        btn_add = QtWidgets.QPushButton("Přidat kategorii")
        btn_add.clicked.connect(self.add_category)
        btn_layout.addWidget(btn_add)

        btn_edit = QtWidgets.QPushButton("Upravit vybranou")
        btn_edit.clicked.connect(self.edit_selected)
        btn_layout.addWidget(btn_edit)

        btn_delete = QtWidgets.QPushButton("Smazat vybranou")
        btn_delete.clicked.connect(self.delete_selected)
        btn_layout.addWidget(btn_delete)

        layout.addLayout(btn_layout)

    def load_categories(self):
        """Načte kategorie z tabulky aprts_housing_category a zobrazí v tabulce."""
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM aprts_housing_category ORDER BY name")
            rows = cursor.fetchall()

            self.table.setRowCount(0)
            for row_num, row in enumerate(rows):
                self.table.insertRow(row_num)
                id_item = QtWidgets.QTableWidgetItem(str(row['id']))
                id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table.setItem(row_num, 0, id_item)

                name_item = QtWidgets.QTableWidgetItem(row['name'])
                self.table.setItem(row_num, 1, name_item)
            self.table.resizeColumnsToContents()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při načítání kategorií: {e}")

    def add_category(self):
        """Zobrazí dialog pro přidání nové kategorie."""
        text, ok = QtWidgets.QInputDialog.getText(self, "Nová kategorie", "Zadej název kategorie:")
        if ok and text.strip():
            try:
                cursor = self.connection.cursor()
                cursor.execute("INSERT INTO aprts_housing_category (name) VALUES (%s)", (text.strip(),))
                self.connection.commit()
                self.load_categories()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání kategorie: {e}")

    def edit_selected(self):
        """Upravit kategorii, na které je nastavený výběr v tabulce."""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Musíš vybrat řádek pro úpravu.")
            return
        id_item = self.table.item(selected_row, 0)
        if not id_item:
            return
        category_id = int(id_item.text())
        current_name = self.table.item(selected_row, 1).text()

        text, ok = QtWidgets.QInputDialog.getText(self, "Upravit kategorii", "Zadej nový název:", text=current_name)
        if ok and text.strip():
            try:
                cursor = self.connection.cursor()
                cursor.execute("UPDATE aprts_housing_category SET name=%s WHERE id=%s", (text.strip(), category_id))
                self.connection.commit()
                self.load_categories()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při úpravě kategorie: {e}")

    def delete_selected(self):
        """Smaže vybranou kategorii po potvrzení."""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Musíš vybrat řádek pro smazání.")
            return
        id_item = self.table.item(selected_row, 0)
        if not id_item:
            return
        category_id = int(id_item.text())

        confirm = QtWidgets.QMessageBox.question(
            self, "Potvrdit smazání",
            f"Opravdu chcete smazat kategorii (ID: {category_id})?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            try:
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM aprts_housing_category WHERE id=%s", (category_id,))
                self.connection.commit()
                self.load_categories()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při mazání kategorie: {e}")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # Připojení k DB
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

    dialog = CategoryManagerDialog(connection)
    dialog.exec_()

    connection.close()
    sys.exit(0)
