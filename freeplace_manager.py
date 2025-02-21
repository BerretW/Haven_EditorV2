import sys
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from freeplace_prop_dialog import FreeplacePropDialog
from item_manager import ItemDialog

class FreeplaceManager(QtWidgets.QDialog):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.setWindowTitle("Správa Freeplace")
        self.setGeometry(100, 100, 1200, 600)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Vyhledávací pole
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Zadejte hledaný text...")
        self.search_edit.returnPressed.connect(self.load_props)
        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.load_props)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)

        # Tabulka
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['ID', 'Prop', 'Item', 'Typ', 'Jobs', 'Akce'])
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # Tlačítka
        buttons_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat")
        add_button.setStyleSheet("background-color: #5cb85c; color: white;")
        add_button.clicked.connect(self.add_prop)
        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.setStyleSheet("background-color: #5bc0de; color: white;")
        refresh_button.clicked.connect(self.load_props)
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(refresh_button)
        layout.addLayout(buttons_layout)

        self.load_props()

    def load_props(self):
        search_text = self.search_edit.text().strip()
        cursor = self.connection.cursor(dictionary=True)
        if search_text:
            query = """
                SELECT * FROM aprts_freeplacing_props
                WHERE prop LIKE %s OR item LIKE %s
            """
            search_pattern = f"%{search_text}%"
            cursor.execute(query, (search_pattern, search_pattern))
        else:
            query = "SELECT * FROM aprts_freeplacing_props"
            cursor.execute(query)
        props = cursor.fetchall()
        self.table.setRowCount(0)
        for row_number, prop in enumerate(props):
            self.table.insertRow(row_number)
            id_item = QtWidgets.QTableWidgetItem(str(prop['id']))
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 0, id_item)

            prop_item = QtWidgets.QTableWidgetItem(prop['prop'])
            prop_item.setFlags(prop_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 1, prop_item)

            item_item = QtWidgets.QTableWidgetItem(prop['item'] or '')
            item_item.setFlags(item_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 2, item_item)

            type_item = QtWidgets.QTableWidgetItem(prop['type'])
            type_item.setFlags(type_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 3, type_item)

            # Dekódujeme 'jobs', pokud je typu bytes
            jobs_value = prop['jobs']
            if isinstance(jobs_value, bytes):
                jobs_value = jobs_value.decode('utf-8')

            jobs_item = QtWidgets.QTableWidgetItem(jobs_value)
            jobs_item.setFlags(jobs_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 4, jobs_item)

            action_widget = self.create_action_buttons(prop['id'], prop['item'])
            self.table.setCellWidget(row_number, 5, action_widget)
            self.table.setColumnWidth(5, 200)

    def create_action_buttons(self, prop_id, item_name):
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Tlačítko Upravit
        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        edit_button.clicked.connect(lambda _, pid=prop_id: self.edit_prop_by_id(pid))
        h_layout.addWidget(edit_button)

        # Tlačítko Upravit Item
        edit_item_button = QtWidgets.QPushButton("Upravit Item")
        edit_item_button.setStyleSheet("background-color: #5bc0de; color: white;")
        edit_item_button.clicked.connect(lambda _, name=item_name: self.edit_item_by_name(name))
        h_layout.addWidget(edit_item_button)

        # Tlačítko Smazat
        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        delete_button.clicked.connect(lambda _, pid=prop_id: self.delete_prop_by_id(pid))
        h_layout.addWidget(delete_button)

        widget.setLayout(h_layout)
        return widget

    def on_table_double_clicked(self, row, column):
        id_item = self.table.item(row, 0)  # Sloupec 0 je ID
        if id_item:
            prop_id = int(id_item.text())
            self.edit_prop_by_id(prop_id)

    def add_prop(self):
        dialog = FreeplacePropDialog(self.connection)
        if dialog.exec_():
            self.load_props()

    def edit_prop_by_id(self, prop_id):
        dialog = FreeplacePropDialog(self.connection, prop_id=prop_id)
        if dialog.exec_():
            self.load_props()

    def edit_item_by_name(self, item_name):
        if not item_name:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Tento záznam nemá přiřazený item.")
            return
        dialog = ItemDialog(self.connection, item_name)
        if dialog.exec_():
            self.load_props()

    def delete_prop_by_id(self, prop_id):
        confirm = QtWidgets.QMessageBox.question(self, "Potvrdit smazání",
                                                 "Opravdu chcete smazat tento záznam?",
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM aprts_freeplacing_props WHERE id = %s", (prop_id,))
            self.connection.commit()
            self.load_props()
