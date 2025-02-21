# store_manager_stores.py

import sys
import os
import json
import re
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from store_manager_storedialog import StoreDialog

class StoreManagerStoresDialog(QtWidgets.QWidget):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Vyhledávací pole
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.store_search_edit = QtWidgets.QLineEdit()
        self.store_search_edit.setPlaceholderText("Zadejte hledaný text...")
        # Odpojíme automatické vyhledávání při změně textu
        # self.store_search_edit.textChanged.connect(self.load_stores)
        # Připojíme vyhledávání při stisku Enter
        self.store_search_edit.returnPressed.connect(self.load_stores)
        # Přidáme tlačítko "Vyhledat"
        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.load_stores)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.store_search_edit)
        search_layout.addWidget(search_button)

        layout.addLayout(search_layout)

        # Tabulka obchodů
        self.stores_table = QtWidgets.QTableWidget()
        self.stores_table.setColumnCount(6)
        self.stores_table.setHorizontalHeaderLabels(['ID', 'Název', 'Blip', 'Souřadnice', 'NPC', 'Akce'])
        self.stores_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.stores_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.stores_table)

        # Tlačítka
        buttons_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat Obchod")
        add_button.clicked.connect(self.add_store)
        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.clicked.connect(self.load_stores)
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(refresh_button)
        layout.addLayout(buttons_layout)

        self.load_stores()

    def load_stores(self):
        search_text = self.store_search_edit.text().strip()
        cursor = self.connection.cursor(dictionary=True)
        query = """
            SELECT s.id, s.name, s.blip_icon, s.blip, s.coords_x, s.coords_y, s.coords_z,
                   npc_list.name AS npc_name
            FROM aprts_stores s
            LEFT JOIN aprts_store_npc npc ON s.id = npc.store_id
            LEFT JOIN aprts_store_npc_list npc_list ON npc.npc_id = npc_list.npc_id
            WHERE s.name LIKE %s
        """
        search_pattern = f"%{search_text}%"
        cursor.execute(query, (search_pattern,))
        stores = cursor.fetchall()
        self.stores_table.setRowCount(0)
        for row_number, store in enumerate(stores):
            self.stores_table.insertRow(row_number)

            id_item = QtWidgets.QTableWidgetItem(str(store['id']))
            self.stores_table.setItem(row_number, 0, id_item)

            name_item = QtWidgets.QTableWidgetItem(store['name'])
            self.stores_table.setItem(row_number, 1, name_item)

            blip_item = QtWidgets.QTableWidgetItem(f"Icon: {store['blip_icon']}, Blip: {store['blip']}")
            self.stores_table.setItem(row_number, 2, blip_item)

            coords_item = QtWidgets.QTableWidgetItem(f"vector3({store['coords_x']}, {store['coords_y']}, {store['coords_z']})")
            self.stores_table.setItem(row_number, 3, coords_item)

            npc_name = store['npc_name'] or 'Žádné'
            npc_item = QtWidgets.QTableWidgetItem(npc_name)
            self.stores_table.setItem(row_number, 4, npc_item)

            # Akční tlačítka
            action_widget = self.create_store_action_buttons(store['id'])
            self.stores_table.setCellWidget(row_number, 5, action_widget)

        self.stores_table.resizeColumnsToContents()

    def create_store_action_buttons(self, store_id):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.clicked.connect(lambda: self.edit_store(store_id))
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        layout.addWidget(edit_button)

        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.clicked.connect(lambda: self.delete_store(store_id))
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        layout.addWidget(delete_button)

        widget.setLayout(layout)
        return widget

    def add_store(self):
        dialog = StoreDialog(self.connection)
        if dialog.exec_():
            self.load_stores()

    def edit_store(self, store_id):
        dialog = StoreDialog(self.connection, store_id)
        if dialog.exec_():
            self.load_stores()

    def delete_store(self, store_id):
        confirm = QtWidgets.QMessageBox.question(self, "Potvrdit smazání",
                                                 "Opravdu chcete smazat tento obchod? Tato akce je nevratná.",
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM aprts_stores WHERE id = %s", (store_id,))
            # Smažeme také přiřazené kategorie a NPC
            cursor.execute("DELETE FROM aprts_store_categories WHERE store_id = %s", (store_id,))
            cursor.execute("DELETE FROM aprts_store_npc WHERE store_id = %s", (store_id,))
            self.connection.commit()
            self.load_stores()

