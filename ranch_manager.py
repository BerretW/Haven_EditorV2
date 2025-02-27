import sys
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from ranch_animal_dialog import RanchAnimalDialog


class RanchAnimalManager(QtWidgets.QDialog):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.setWindowTitle("Správa Rančových Zvířat")
        self.setGeometry(100, 100, 1200, 600)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Vyhledávací pole
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Zadejte hledaný text (např. jméno zvířete)...")
        self.search_edit.returnPressed.connect(self.load_animals)

        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.load_animals)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)

        # Tabulka zvířat
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Název", "Model (F)", "Akce"])
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # Tlačítka
        buttons_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat Zvíře")
        add_button.setStyleSheet("background-color: #5cb85c; color: white;")
        add_button.clicked.connect(self.add_animal)

        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.setStyleSheet("background-color: #5bc0de; color: white;")
        refresh_button.clicked.connect(self.load_animals)

        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(refresh_button)
        layout.addLayout(buttons_layout)

        self.load_animals()

    def load_animals(self):
        search_text = self.search_edit.text().strip().lower()
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM aprts_ranch_config_animals"
        params = []
        if search_text:
            query += " WHERE (name LIKE %s OR model LIKE %s OR m_model LIKE %s)"
            like_str = f"%{search_text}%"
            params = [like_str, like_str, like_str]

        cursor.execute(query, params)
        animals = cursor.fetchall()
        self.table.setRowCount(0)
        for row_number, animal in enumerate(animals):
            self.table.insertRow(row_number)

            # ID
            id_item = QtWidgets.QTableWidgetItem(str(animal['animal_id']))
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 0, id_item)

            # Name
            name_item = QtWidgets.QTableWidgetItem(animal['name'])
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 1, name_item)

            # model (female)
            model_item = QtWidgets.QTableWidgetItem(animal['model'])
            model_item.setFlags(model_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 2, model_item)

            # Akce
            action_widget = self.create_action_buttons(animal['animal_id'])
            self.table.setCellWidget(row_number, 3, action_widget)

        self.table.resizeColumnsToContents()

    def create_action_buttons(self, animal_id):
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Upravit
        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        edit_button.clicked.connect(lambda _, aid=animal_id: self.edit_animal_by_id(aid))
        h_layout.addWidget(edit_button)

        # Smazat
        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        delete_button.clicked.connect(lambda _, aid=animal_id: self.delete_animal_by_id(aid))
        h_layout.addWidget(delete_button)

        widget.setLayout(h_layout)
        return widget

    def on_table_double_clicked(self, row, column):
        id_item = self.table.item(row, 0)  # Sloupec 0 je ID
        if id_item:
            animal_id = int(id_item.text())
            self.edit_animal_by_id(animal_id)

    def add_animal(self):
        dialog = RanchAnimalDialog(self.connection)
        if dialog.exec_():
            self.load_animals()

    def edit_animal_by_id(self, animal_id):
        dialog = RanchAnimalDialog(self.connection, animal_id=animal_id)
        if dialog.exec_():
            self.load_animals()

    def delete_animal_by_id(self, animal_id):
        confirm = QtWidgets.QMessageBox.question(self, "Potvrdit smazání",
                                                 "Opravdu chcete smazat toto zvíře?",
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM aprts_ranch_config_animals WHERE animal_id = %s", (animal_id,))
            self.connection.commit()
            self.load_animals()


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

    dialog = RanchAnimalManager(connection=connection)
    if dialog.exec_():
        print("Pole bylo úspěšně uloženo.")
    else:
        print("Ukládání pole bylo zrušeno.")

    connection.close()
    sys.exit(0)
