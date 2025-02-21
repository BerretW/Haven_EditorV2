import sys
import json
import os
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
from mysql.connector import Error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from hunting_animal_dialog import HuntingAnimalDialog

class HuntingAnimalManager(QtWidgets.QDialog):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.setWindowTitle("Správa Zvířat - Hunting")
        self.setGeometry(100, 100, 1200, 600)  # Zvýšení šířky pro nové sloupce
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        # Vyhledávací pole
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Zadejte hledaný text...")
        self.search_edit.returnPressed.connect(self.filter_items)
        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.filter_items)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(search_button)
        main_layout.addLayout(search_layout)

        # Tabulka zvířat
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)  # Změna z 4 na 6
        self.table.setHorizontalHeaderLabels(['ID', 'Name', 'Label', 'Level', 'XP', 'Akce'])
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        main_layout.addWidget(self.table)

        # Tlačítka
        button_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat Zvíře")
        add_button.setIcon(QtGui.QIcon.fromTheme("list-add"))
        add_button.setToolTip("Přidat nové zvíře")
        add_button.clicked.connect(self.add_item)
        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.setIcon(QtGui.QIcon.fromTheme("view-refresh"))
        refresh_button.setToolTip("Obnovit seznam zvířat")
        refresh_button.clicked.connect(self.load_items)
        button_layout.addWidget(add_button)
        button_layout.addWidget(refresh_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.load_items()

    def load_items(self):
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM aprts_hunting_animals"
        cursor.execute(query)
        self.animals = cursor.fetchall()
        self.filter_items()

    def filter_items(self):
        search_text = self.search_edit.text().strip().lower()
        filtered = []
        for a in self.animals:
            if (
                search_text in a['name'].lower() or
                (a['label'] and search_text in a['label'].lower()) or
                search_text in str(a['level']) or
                search_text in str(a['XP'])
            ):
                filtered.append(a)
        self.populate_table(filtered)

    def populate_table(self, items):
        self.table.setRowCount(0)
        for row_number, a in enumerate(items):
            self.table.insertRow(row_number)

            # ID
            id_item = QtWidgets.QTableWidgetItem(str(a['id']))
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 0, id_item)

            # Name
            name_item = QtWidgets.QTableWidgetItem(a['name'])
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 1, name_item)

            # Label
            label_item = QtWidgets.QTableWidgetItem(a['label'] if a['label'] else '')
            label_item.setFlags(label_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 2, label_item)

            # Level
            level_item = QtWidgets.QTableWidgetItem(str(a['level']))
            level_item.setFlags(level_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 3, level_item)

            # XP
            xp_item = QtWidgets.QTableWidgetItem(str(a['XP']))
            xp_item.setFlags(xp_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 4, xp_item)

            # Akce
            action_widget = self.create_action_buttons(a['id'])
            self.table.setCellWidget(row_number, 5, action_widget)

            self.table.setRowHeight(row_number, 40)  # Zvýšení výšky řádku pro lepší vzhled

        self.table.resizeColumnsToContents()

    def create_action_buttons(self, animal_id):
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Upravit
        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.setToolTip("Upravit zvíře")
        edit_button.clicked.connect(lambda _, id=animal_id: self.edit_item_by_id(id))
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        h_layout.addWidget(edit_button)

        # Kopírovat
        copy_button = QtWidgets.QPushButton("Kopírovat")
        copy_button.setToolTip("Kopírovat zvíře")
        copy_button.clicked.connect(lambda _, id=animal_id: self.copy_item_by_id(id))
        copy_button.setStyleSheet("background-color: #5bc0de; color: white;")
        h_layout.addWidget(copy_button)

        # Smazat
        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.setToolTip("Smazat zvíře")
        delete_button.clicked.connect(lambda _, id=animal_id: self.delete_item_by_id(id))
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        h_layout.addWidget(delete_button)

        widget.setLayout(h_layout)
        return widget

    def on_table_double_clicked(self, row, column):
        id_item = self.table.item(row, 0)
        if id_item:
            animal_id = int(id_item.text())
            self.edit_item_by_id(animal_id)

    def add_item(self):
        dialog = HuntingAnimalDialog(self.connection)
        if dialog.exec_():
            self.load_items()

    def edit_item_by_id(self, animal_id):
        dialog = HuntingAnimalDialog(self.connection, animal_id)
        if dialog.exec_():
            self.load_items()

    def copy_item_by_id(self, animal_id):
        # Načteme data z databáze pro dané zvíře
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM aprts_hunting_animals WHERE id = %s", (animal_id,))
        animal = cursor.fetchone()
        if not animal:
            QtWidgets.QMessageBox.warning(self, "Chyba", f"Zvíře s ID '{animal_id}' nebylo nalezeno.")
            return

        # Otevřeme dialog s předvyplněnými daty, ale bez ID a s výchozími hodnotami pro Level a XP
        dialog = HuntingAnimalDialog(self.connection)
        dialog.name_edit.setText(animal['name'])
        dialog.label_edit.setText(animal['label'] if animal['label'] else '')

        # Předávání hodnot jako int, nikoli float
        dialog.outfit_edit.setValue(int(animal['outfit']) if animal['outfit'] is not None else 0)
        dialog.model_edit.setValue(int(animal['model']) if animal['model'] is not None else 0)

        # Nastavení hodnot a checkboxů pro perfect, poor, good
        if animal['perfect'] is None:
            dialog.perfect_checkbox.setChecked(True)
            dialog.perfect_edit.setValue(0)
        else:
            dialog.perfect_checkbox.setChecked(False)
            dialog.perfect_edit.setValue(int(animal['perfect']))

        if animal['poor'] is None:
            dialog.poor_checkbox.setChecked(True)
            dialog.poor_edit.setValue(0)
        else:
            dialog.poor_checkbox.setChecked(False)
            dialog.poor_edit.setValue(int(animal['poor']))

        if animal['good'] is None:
            dialog.good_checkbox.setChecked(True)
            dialog.good_edit.setValue(0)
        else:
            dialog.good_checkbox.setChecked(False)
            dialog.good_edit.setValue(int(animal['good']))

        dialog.base_price_edit.setValue(float(animal['base_price']))
        dialog.poor_price_edit.setValue(float(animal['poor_price']) if animal['poor_price'] else 0.0)
        dialog.good_price_edit.setValue(float(animal['good_price']) if animal['good_price'] else 0.0)
        dialog.perfect_price_edit.setValue(float(animal['perfect_price']) if animal['perfect_price'] else 0.0)

        # **Nastavení výchozích hodnot pro Level a XP při kopírování**
        dialog.level_edit.setValue(0)  # Výchozí hodnota pro kopírované zvíře
        dialog.xp_edit.setValue(1)     # Výchozí hodnota pro kopírované zvíře

        # Načteme loot data
        item_text = animal.get('item', '[]')
        try:
            dialog.current_item_data = json.loads(item_text)
        except json.JSONDecodeError:
            dialog.current_item_data = []
        dialog.load_loot_data()

        # Uložení nové kopie zvířete
        if dialog.exec_():
            self.load_items()

    def delete_item_by_id(self, animal_id):
        confirm = QtWidgets.QMessageBox.question(
            self, "Potvrdit smazání",
            f"Opravdu chcete smazat zvíře ID '{animal_id}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM aprts_hunting_animals WHERE id = %s", (animal_id,))
            self.connection.commit()
            self.load_items()
