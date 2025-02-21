# fields_manager.py
import json
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from field_dialog import FieldDialog


class FieldsManagerWidget(QtWidgets.QWidget):
    def __init__(self, connection, parent=None):
        super().__init__(parent)
        self.connection = connection
        self.setWindowTitle(f"Správa políček")
        self.setGeometry(100, 100, 1400, 600)
        self.load_stylesheet(os.path.join(BASE_DIR, "stylesheet.qss"))
        self.init_ui()

    def load_stylesheet(self, filepath):
        """Načte stylesheet z externího souboru."""
        try:
            with open(filepath, "r") as file:
                self.setStyleSheet(file.read())
        except Exception as e:
            print(f"Chyba při načítání stylů: {e}")

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        # Vyhledávací pole
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.fields_search_edit = QtWidgets.QLineEdit()
        self.fields_search_edit.setPlaceholderText(
            "Zadejte hledaný text (name, blip, ...)")
        # Necháme (zatím) na explicitní vyvolání load_fields()
        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.load_fields)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.fields_search_edit)
        search_layout.addWidget(search_button)
        main_layout.addLayout(search_layout)

        # Tabulka
        self.fields_table = QtWidgets.QTableWidget()
        self.fields_table.setColumnCount(6)
        self.fields_table.setHorizontalHeaderLabels([
            "ID", "Název", "Blip", "coords", "limit", "Akce"
        ])
        self.fields_table.setSortingEnabled(True)
        self.fields_table.cellDoubleClicked.connect(
            self.on_fields_double_click)
        main_layout.addWidget(self.fields_table)

        # Tlačítka
        button_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat Pole")
        add_button.setStyleSheet("background-color: #5cb85c; color: white;")
        add_button.clicked.connect(self.add_field)
        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.setStyleSheet(
            "background-color: #5bc0de; color: white;")
        refresh_button.clicked.connect(self.load_fields)
        button_layout.addWidget(add_button)
        button_layout.addWidget(refresh_button)
        main_layout.addLayout(button_layout)

        # Pozn.: load_fields() se explicitně zavolá až tehdy, kdy to opravdu potřebujeme
        # (tedy až při "přepnutí" na tuto záložku). Můžete to upravit dle potřeby.

    def load_fields(self):
        search_text = self.fields_search_edit.text().strip()
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM aprts_herbs_fields"
        params = []
        if search_text:
            query += " WHERE (name LIKE %s OR blip LIKE %s)"
            search_pattern = f"%{search_text}%"
            params = [search_pattern, search_pattern]

        cursor.execute(query, params)
        fields = cursor.fetchall()
        self.fields_table.setRowCount(0)
        for row_number, field in enumerate(fields):
            self.fields_table.insertRow(row_number)
            # ID
            id_item = QtWidgets.QTableWidgetItem(str(field['id']))
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.fields_table.setItem(row_number, 0, id_item)

            # name
            name_str = field['name']
            if isinstance(name_str, bytes):
                name_str = name_str.decode('utf-8', 'replace')
            name_item = QtWidgets.QTableWidgetItem(name_str or '')
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.fields_table.setItem(row_number, 1, name_item)

            # blip
            blip_str = field['blip']
            if isinstance(blip_str, bytes):
                blip_str = blip_str.decode('utf-8', 'replace')
            blip_item = QtWidgets.QTableWidgetItem(blip_str or '')
            blip_item.setFlags(blip_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.fields_table.setItem(row_number, 2, blip_item)

            # coords
            coords_str = field['coords']
            if isinstance(coords_str, bytes):
                coords_str = coords_str.decode('utf-8', 'replace')
            coords_item = QtWidgets.QTableWidgetItem(coords_str or '')
            coords_item.setFlags(coords_item.flags() & ~
                                 QtCore.Qt.ItemIsEditable)
            self.fields_table.setItem(row_number, 3, coords_item)

            # limit
            limit_item = QtWidgets.QTableWidgetItem(str(field['limit']))
            limit_item.setFlags(limit_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.fields_table.setItem(row_number, 4, limit_item)

            # akce
            action_widget = self.create_field_action_buttons(field['id'])
            self.fields_table.setCellWidget(row_number, 5, action_widget)

        self.fields_table.resizeColumnsToContents()

    def on_fields_double_click(self, row, column):
        id_item = self.fields_table.item(row, 0)
        if id_item:
            field_id = int(id_item.text())
            self.edit_field_by_id(field_id)

    def create_field_action_buttons(self, field_id):
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)

        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        edit_button.clicked.connect(
            lambda _, fid=field_id: self.edit_field_by_id(fid))
        h_layout.addWidget(edit_button)

        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        delete_button.clicked.connect(
            lambda _, fid=field_id: self.delete_field_by_id(fid))
        h_layout.addWidget(delete_button)

        widget.setLayout(h_layout)
        return widget

    def add_field(self):
        dialog = FieldDialog(self.connection)
        if dialog.exec_():
            self.load_fields()

    def edit_field_by_id(self, field_id):
        dialog = FieldDialog(self.connection, field_id)
        if dialog.exec_():
            self.load_fields()

    def delete_field_by_id(self, field_id):
        confirm = QtWidgets.QMessageBox.question(
            self, "Potvrdit smazání",
            "Opravdu chcete smazat toto políčko?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute(
                "DELETE FROM aprts_herbs_fields WHERE id = %s", (field_id,))
            self.connection.commit()
            self.load_fields()
