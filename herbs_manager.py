# herbs_manager.py
import json
import os
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from herb_dialog import HerbDialog
# Widget pro druhou záložku (pole)
from fields_manager import FieldsManagerWidget


def decode_if_bytes(value):
    """
    Pokud je value typu bytes, dekóduje ho na str (UTF-8).
    Pokud je None nebo str, vrátí se tak, jak je.
    """
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return value


class HerbsManagerDialog(QtWidgets.QDialog):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.setWindowTitle("Správa Sběru (Bylinky a Políčka)")
        self.resize(1000, 600)  # Můžete upravit velikost dle potřeby
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

        # Vytvoříme QTabWidget
        self.tab_widget = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # --- TAB 1: BYLINKY (aprts_herbs) ---
        self.herbs_tab = QtWidgets.QWidget()
        self.tab_widget.addTab(self.herbs_tab, "Bylinky")
        self.init_herbs_tab()

        # --- TAB 2: FIELDS (aprts_herbs_fields) ---
        # Použijeme FieldsManagerWidget
        self.fields_tab = QtWidgets.QWidget()
        self.fields_layout = QtWidgets.QVBoxLayout()
        self.fields_tab.setLayout(self.fields_layout)
        self.fields_widget = None  # Lazy load

        self.tab_widget.addTab(self.fields_tab, "Políčka")
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        """Aktivace/načtení druhé záložky – políčka."""
        if index == 1:  # Políčka
            if not self.fields_widget:
                self.fields_widget = FieldsManagerWidget(self.connection)
                self.fields_layout.addWidget(self.fields_widget)
            self.fields_widget.load_fields()

    # ----------------------------------------------------------------
    #                   TAB 1: BYLINKY
    # ----------------------------------------------------------------
    def init_herbs_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.herbs_tab.setLayout(layout)

        # Vyhledávací pole
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.herb_search_edit = QtWidgets.QLineEdit()
        self.herb_search_edit.setPlaceholderText(
            "Zadejte hledaný text (source, ...)")
        self.herb_search_edit.returnPressed.connect(self.load_herbs)
        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.load_herbs)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.herb_search_edit)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)

        # Tabulka
        self.herbs_table = QtWidgets.QTableWidget()
        self.herbs_table.setColumnCount(4)  # ID, source, GatherTime, Akce
        self.herbs_table.setHorizontalHeaderLabels(
            ["ID", "source", "GatherTime", "Akce"])
        self.herbs_table.setSortingEnabled(True)
        self.herbs_table.cellDoubleClicked.connect(self.edit_herb_by_row)
        layout.addWidget(self.herbs_table)

        # Tlačítka pod tabulkou
        button_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat Položku")
        add_button.setStyleSheet(
            "background-color: #5cb85c; color: white;")  # Zelené
        add_button.clicked.connect(self.add_herb)

        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.setStyleSheet(
            "background-color: #5bc0de; color: white;")  # Modré
        refresh_button.clicked.connect(self.load_herbs)

        button_layout.addWidget(add_button)
        button_layout.addWidget(refresh_button)
        layout.addLayout(button_layout)

        self.load_herbs()

    def load_herbs(self):
        """Načte bylinky z aprts_herbs, filtruje dle zadaného vyhledávacího textu."""
        search_text = self.herb_search_edit.text().strip()
        cursor = self.connection.cursor(dictionary=True)

        query = "SELECT * FROM aprts_herbs"
        params = []
        if search_text:
            query += " WHERE (source LIKE %s OR animDict LIKE %s OR animBody LIKE %s OR failedText LIKE %s)"
            pattern = f"%{search_text}%"
            params = [pattern, pattern, pattern, pattern]

        cursor.execute(query, params)
        herbs = cursor.fetchall()
        cursor.close()

        self.herbs_table.setRowCount(0)
        for row_number, herb in enumerate(herbs):
            self.herbs_table.insertRow(row_number)

            # ID
            id_item = QtWidgets.QTableWidgetItem(str(herb['id']))
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.herbs_table.setItem(row_number, 0, id_item)

            # source (může být bytes -> decode)
            source_val = decode_if_bytes(herb['source'])
            source_item = QtWidgets.QTableWidgetItem(source_val)
            source_item.setFlags(source_item.flags() & ~
                                 QtCore.Qt.ItemIsEditable)
            self.herbs_table.setItem(row_number, 1, source_item)

            # GatherTime
            gather_time_item = QtWidgets.QTableWidgetItem(
                str(herb['GatherTime']))
            gather_time_item.setFlags(
                gather_time_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.herbs_table.setItem(row_number, 2, gather_time_item)

            # Akce
            action_widget = self.create_herb_action_buttons(herb)
            self.herbs_table.setCellWidget(row_number, 3, action_widget)

        self.herbs_table.resizeColumnsToContents()

    def create_herb_action_buttons(self, herb_dict):
        """Vytvoří widget s tlačítky pro Upravit / Kopírovat / Smazat."""
        herb_id = herb_dict['id']
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Upravit
        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.setStyleSheet(
            "background-color: #5cb85c; color: white;")  # Zelené
        edit_button.clicked.connect(
            lambda _, hid=herb_id: self.edit_herb_by_id(hid))
        h_layout.addWidget(edit_button)

        # Kopírovat
        copy_button = QtWidgets.QPushButton("Kopírovat")
        copy_button.setStyleSheet(
            "background-color: #5bc0de; color: white;")  # Modré
        copy_button.clicked.connect(
            lambda _, hdict=herb_dict: self.copy_herb(hdict))
        h_layout.addWidget(copy_button)

        # Smazat
        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.setStyleSheet(
            "background-color: #d9534f; color: white;")  # Červené
        delete_button.clicked.connect(
            lambda _, hid=herb_id: self.delete_herb_by_id(hid))
        h_layout.addWidget(delete_button)

        widget.setLayout(h_layout)
        return widget

    def copy_herb(self, herb_dict):
        """
        Zkopíruje danou bylinku (herb_dict) do nového záznamu.
        Rovnou otevře okno HerbDialog pro editaci nové bylinky.
        """
        # 1) Vytvořit kopii záznamu s vynecháním původního id
        #    (zdroj: herb_dict, zkopírovat např. source, animDict, animBody, GatherTime, failedText, reward, atd.)
        new_data = dict(herb_dict)
        new_data.pop('id', None)  # Odstraníme původní ID

        # 2) Vložit do DB
        columns = []
        placeholders = []
        values = []
        for key in new_data.keys():
            if key == 'id':
                continue
            columns.append(key)
            placeholders.append("%s")
            values.append(new_data[key])

        col_str = ", ".join(columns)
        place_str = ", ".join(placeholders)
        insert_query = f"INSERT INTO aprts_herbs ({col_str}) VALUES ({
            place_str})"

        cursor = self.connection.cursor()
        try:
            cursor.execute(insert_query, values)
            self.connection.commit()
            new_id = cursor.lastrowid
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(
                self, "Chyba", f"Nastala chyba při kopírování bylinky: {err}")
            return
        finally:
            cursor.close()

        # 3) Otevřít okno pro nově vytvořenou bylinku
        dialog = HerbDialog(self.connection, new_id)
        if dialog.exec_():
            self.load_herbs()

    def edit_herb_by_row(self, row, col):
        id_item = self.herbs_table.item(row, 0)
        if id_item:
            herb_id = int(id_item.text())
            self.edit_herb_by_id(herb_id)

    def add_herb(self):
        dialog = HerbDialog(self.connection)
        if dialog.exec_():
            self.load_herbs()

    def edit_herb_by_id(self, herb_id):
        dialog = HerbDialog(self.connection, herb_id)
        if dialog.exec_():
            self.load_herbs()

    def delete_herb_by_id(self, herb_id):
        confirm = QtWidgets.QMessageBox.question(
            self, "Potvrdit smazání",
            "Opravdu chcete smazat tuto bylinku?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM aprts_herbs WHERE id = %s", (herb_id,))
            self.connection.commit()
            self.load_herbs()
