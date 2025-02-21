import json
import os
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector

from plants_dialog import PlantDialog  # (uvedený níže)

class PlantTypesManagerDialog(QtWidgets.QDialog):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.setWindowTitle("Správa Typů Rostlin (aprts_farming_plant_types)")
        self.resize(1100, 600)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Vyhledávací pole
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Hledat (name, display_name)...")
        # Tlačítko pro vyhledávání
        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.load_plant_types)
        # Při Enteru ve vyhledávání
        self.search_edit.returnPressed.connect(self.load_plant_types)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)

        # Tabulka
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Název (name)", "Zobraz. Jméno", "Model",
            "Grow (čas)", "Die (čas)", "Akce"
        ])
        self.table.cellDoubleClicked.connect(self.on_table_doubleclick)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # Tlačítka dole
        button_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat Rostlinu")
        add_button.setStyleSheet("background-color: #5cb85c; color: white;")
        add_button.clicked.connect(self.add_plant_type)

        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.setStyleSheet("background-color: #5bc0de; color: white;")
        refresh_button.clicked.connect(self.load_plant_types)

        button_layout.addWidget(add_button)
        button_layout.addWidget(refresh_button)
        layout.addLayout(button_layout)

        self.load_plant_types()

    def load_plant_types(self):
        """Načte záznamy z tabulky aprts_farming_plant_types a zobrazí v QTableWidget."""
        search_text = self.search_edit.text().strip()
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM aprts_farming_plant_types"
        params = []
        if search_text:
            query += " WHERE (name LIKE %s OR display_name LIKE %s)"
            like_val = f"%{search_text}%"
            params = [like_val, like_val]

        cursor.execute(query, params)
        rows = cursor.fetchall()

        self.table.setRowCount(0)
        for row_number, row_data in enumerate(rows):
            self.table.insertRow(row_number)
            # ID
            id_item = QtWidgets.QTableWidgetItem(str(row_data["plant_type_id"]))
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 0, id_item)

            name_item = QtWidgets.QTableWidgetItem(row_data["name"])
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 1, name_item)

            display_name_item = QtWidgets.QTableWidgetItem(row_data["display_name"])
            display_name_item.setFlags(display_name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 2, display_name_item)

            model_item = QtWidgets.QTableWidgetItem(row_data["model"])
            model_item.setFlags(model_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 3, model_item)

            grow_item = QtWidgets.QTableWidgetItem(str(row_data["time_to_grow"]))
            grow_item.setFlags(grow_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 4, grow_item)

            die_item = QtWidgets.QTableWidgetItem(str(row_data["time_to_die"]))
            die_item.setFlags(die_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 5, die_item)

            # Akce (Upravit / Smazat)
            action_widget = self.create_action_buttons(row_data["plant_type_id"])
            self.table.setCellWidget(row_number, 6, action_widget)

        self.table.resizeColumnsToContents()

    def create_action_buttons(self, plant_type_id):
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)

        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        edit_button.clicked.connect(lambda _, pid=plant_type_id: self.edit_plant_type(pid))
        h_layout.addWidget(edit_button)

        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        delete_button.clicked.connect(lambda _, pid=plant_type_id: self.delete_plant_type(pid))
        h_layout.addWidget(delete_button)

        widget.setLayout(h_layout)
        return widget

    def on_table_doubleclick(self, row, column):
        id_item = self.table.item(row, 0)  # Sloupec 0 je ID
        if id_item:
            pid = int(id_item.text())
            self.edit_plant_type(pid)

    def add_plant_type(self):
        dialog = PlantDialog(self.connection)
        if dialog.exec_():
            self.load_plant_types()

    def edit_plant_type(self, plant_type_id):
        dialog = PlantDialog(self.connection, plant_type_id=plant_type_id)
        if dialog.exec_():
            self.load_plant_types()

    def delete_plant_type(self, plant_type_id):
        confirm = QtWidgets.QMessageBox.question(
            self, "Potvrdit smazání",
            "Opravdu chcete smazat tento záznam?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM aprts_farming_plant_types WHERE plant_type_id=%s", (plant_type_id,))
            self.connection.commit()
            self.load_plant_types()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    try:
        connection = mysql.connector.connect(
            host='db-server.kkrp.cz',
            user='u29_GTcP77m4BF',
            password='BLIb!.QW415iG+EOVcuV!3=Q',
            database='s29_dev-redm'
        )
    except mysql.connector.Error as err:
        print(f"Chyba při připojování k databázi: {err}")
        sys.exit(1)

    dialog = PlantTypesManagerDialog(connection=connection)
    if dialog.exec_():
        print("Pole bylo úspěšně uloženo.")
    else:
        print("Ukládání pole bylo zrušeno.")

    connection.close()
    sys.exit(0)
