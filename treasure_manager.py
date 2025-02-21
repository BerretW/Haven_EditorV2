# treasure_manager.py

import sys
import json
import os
import logging
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector

def decode_if_bytes(value):
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return value

from treasure_type_dialog import TreasureTypeDialog
from treasure_dialog import TreasureDialog
from treasure_reward_dialog import TreasureRewardDialog
from treasure_clue_dialog import TreasureClueDialog

# ============================================
# Nastavení logování
# ============================================
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Logy budou vypisovány do konzole
    ]
)

# ============================================
# Hlavní okno pro "správu pokladů"
# ============================================
class TreasureManagerDialog(QtWidgets.QDialog):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.setWindowTitle("Správa Pokladů")
        self.resize(1000, 600)

        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        self.tab_widget = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # --- TAB 1: Treasure Types & Rewards
        self.tab_types = QtWidgets.QWidget()
        self.init_types_tab()
        self.tab_widget.addTab(self.tab_types, "Treasure Types")

        # --- TAB 2: Treasures & Clues
        self.tab_treasures = QtWidgets.QWidget()
        self.init_treasures_tab()
        self.tab_widget.addTab(self.tab_treasures, "Treasures")

    # ==========================================
    # Metoda pro vykonávání a logování SQL dotazů
    # ==========================================
    def execute_query(self, query, params=None, dictionary=True):
        logging.debug(f"Executing SQL: {query}")
        if params:
            logging.debug(f"With params: {params}")
        try:
            cursor = self.connection.cursor(dictionary=dictionary)
            cursor.execute(query, params)
            return cursor
        except mysql.connector.Error as err:
            logging.error(f"Error executing query: {err}")
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Chyba při vykonávání dotazu: {err}")
            return None

    # ==========================================
    #  TAB 1: Treasure Types + Rewards
    # ==========================================
    def init_types_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.tab_types.setLayout(layout)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        layout.addWidget(splitter)

        # 1) Tabulka pro aprts_treasure_types
        top_widget = QtWidgets.QWidget()
        top_layout = QtWidgets.QVBoxLayout()
        top_widget.setLayout(top_layout)

        self.types_table = QtWidgets.QTableWidget()
        self.types_table.setColumnCount(4)
        self.types_table.setHorizontalHeaderLabels(["ID", "Name", "Prop", "Chance"])
        self.types_table.setSortingEnabled(True)
        self.types_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.types_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.types_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)  # Zabránění editování
        self.types_table.cellDoubleClicked.connect(self.edit_selected_type)  # Dvojklik pro editaci
        self.types_table.cellClicked.connect(self.on_type_selected)

        top_layout.addWidget(self.types_table)

        btn_layout = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Přidat Type")
        add_btn.clicked.connect(self.add_type)
        edit_btn = QtWidgets.QPushButton("Upravit Type")
        edit_btn.clicked.connect(self.edit_selected_type_button)  # Nová metoda
        del_btn = QtWidgets.QPushButton("Smazat Type")
        del_btn.clicked.connect(self.delete_selected_type)
        
        # Přidání tlačítka "Obnovit"
        refresh_btn = QtWidgets.QPushButton("Obnovit")
        refresh_btn.clicked.connect(self.load_types)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(refresh_btn)  # Přidání do layoutu

        top_layout.addLayout(btn_layout)

        splitter.addWidget(top_widget)

        # 2) Tabulka pro aprts_treasure_rewards (navázaná na vybraný type)
        bottom_widget = QtWidgets.QWidget()
        bottom_layout = QtWidgets.QVBoxLayout()
        bottom_widget.setLayout(bottom_layout)

        self.rewards_table = QtWidgets.QTableWidget()
        self.rewards_table.setColumnCount(4)
        self.rewards_table.setHorizontalHeaderLabels(["ID", "TreasureTypeID", "Item", "Count"])
        self.rewards_table.setSortingEnabled(True)
        self.rewards_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.rewards_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.rewards_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)  # Zabránění editování
        self.rewards_table.cellDoubleClicked.connect(self.edit_selected_reward)  # Dvojklik pro editaci

        bottom_layout.addWidget(self.rewards_table)

        rew_btn_layout = QtWidgets.QHBoxLayout()
        add_rew_btn = QtWidgets.QPushButton("Přidat Reward")
        add_rew_btn.clicked.connect(self.add_reward)
        edit_rew_btn = QtWidgets.QPushButton("Upravit Reward")
        edit_rew_btn.clicked.connect(self.edit_selected_reward_button)  # Nová metoda
        del_rew_btn = QtWidgets.QPushButton("Smazat Reward")
        del_rew_btn.clicked.connect(self.delete_selected_reward)
        
        # Přidání tlačítka "Obnovit" pro Rewards
        refresh_rew_btn = QtWidgets.QPushButton("Obnovit")
        refresh_rew_btn.clicked.connect(lambda: self.load_rewards(self.get_selected_type_id()))

        rew_btn_layout.addWidget(add_rew_btn)
        rew_btn_layout.addWidget(edit_rew_btn)
        rew_btn_layout.addWidget(del_rew_btn)
        rew_btn_layout.addWidget(refresh_rew_btn)  # Přidání do layoutu

        bottom_layout.addLayout(rew_btn_layout)

        splitter.addWidget(bottom_widget)

        # Načteme Type + Rewards
        self.load_types()
        # (rewards se načtou až při vybrání typu)

    def load_types(self):
        query = "SELECT * FROM aprts_treasure_types ORDER BY id"
        cursor = self.execute_query(query)
        if cursor is None:
            return

        rows = cursor.fetchall()

        self.types_table.setRowCount(0)
        for i, row in enumerate(rows):
            self.types_table.insertRow(i)
            id_item = QtWidgets.QTableWidgetItem(str(row["id"]))
            id_item.setData(QtCore.Qt.UserRole, row["id"])
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)  # Nepřímo zabezpečení
            self.types_table.setItem(i, 0, id_item)

            name_item = QtWidgets.QTableWidgetItem(row["name"])
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.types_table.setItem(i, 1, name_item)

            prop_item = QtWidgets.QTableWidgetItem(row["prop"])
            prop_item.setFlags(prop_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.types_table.setItem(i, 2, prop_item)

            chance_item = QtWidgets.QTableWidgetItem(str(row["chance"]))
            chance_item.setFlags(chance_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.types_table.setItem(i, 3, chance_item)

        self.types_table.resizeColumnsToContents()

    def on_type_selected(self, row, col):
        # Najdeme ID typu
        id_item = self.types_table.item(row, 0)
        if not id_item:
            return
        type_id = id_item.data(QtCore.Qt.UserRole)
        self.load_rewards(type_id)

    def load_rewards(self, type_id):
        query = "SELECT * FROM aprts_treasure_rewards WHERE treasure_type_id=%s"
        params = (type_id,)
        cursor = self.execute_query(query, params)
        if cursor is None:
            return

        rows = cursor.fetchall()

        self.rewards_table.setRowCount(0)
        for i, row in enumerate(rows):
            self.rewards_table.insertRow(i)

            # Sloupec ID
            rid_item = QtWidgets.QTableWidgetItem(str(row["id"]))
            rid_item.setData(QtCore.Qt.UserRole, row["id"])
            rid_item.setFlags(rid_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.rewards_table.setItem(i, 0, rid_item)

            # TreasureTypeID
            type_id_item = QtWidgets.QTableWidgetItem(str(row["treasure_type_id"]))
            type_id_item.setFlags(type_id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.rewards_table.setItem(i, 1, type_id_item)

            # Item
            item_item = QtWidgets.QTableWidgetItem(row["item"])
            item_item.setFlags(item_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.rewards_table.setItem(i, 2, item_item)

            # Count
            count_item = QtWidgets.QTableWidgetItem(str(row["count"]))
            count_item.setFlags(count_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.rewards_table.setItem(i, 3, count_item)

        self.rewards_table.resizeColumnsToContents()

    def get_selected_type_id(self):
        sel = self.types_table.selectedItems()
        if not sel:
            return None
        row = self.types_table.row(sel[0])
        id_item = self.types_table.item(row, 0)
        if not id_item:
            return None
        return id_item.data(QtCore.Qt.UserRole)

    def add_type(self):
        dialog = TreasureTypeDialog(self.connection)
        if dialog.exec_():
            self.load_types()

    def edit_selected_type_button(self):
        """Metoda spojená s tlačítkem pro úpravu typu."""
        self.edit_selected_type()

    def edit_selected_type(self, row=None, col=None):
        """Otevře dialog pro úpravu vybraného typu."""
        if row is not None and col is not None:
            # Pokud je metoda volána z cellDoubleClicked
            id_item = self.types_table.item(row, 0)
            if not id_item:
                return
            type_id = id_item.data(QtCore.Qt.UserRole)
        else:
            # Pokud je metoda volána z tlačítka
            type_id = self.get_selected_type_id()
            if type_id is None:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte typ.")
                return

        dialog = TreasureTypeDialog(self.connection, type_id=type_id)
        if dialog.exec_():
            self.load_types()

    def delete_selected_type(self):
        type_id = self.get_selected_type_id()
        if type_id is None:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte řádek.")
            return
        confirm = QtWidgets.QMessageBox.question(self, "Smazat?", "Opravdu chcete smazat vybraný treasure_type?")
        if confirm == QtWidgets.QMessageBox.Yes:
            query = "DELETE FROM aprts_treasure_types WHERE id=%s"
            params = (type_id,)
            cursor = self.execute_query(query, params, dictionary=False)
            if cursor is None:
                return
            try:
                self.connection.commit()
                logging.debug("Commit successful for DELETE aprts_treasure_types")
                self.load_types()
                # Vyprázdníme i rewards
                self.rewards_table.setRowCount(0)
            except mysql.connector.Error as err:
                logging.error(f"Error committing DELETE aprts_treasure_types: {err}")
                QtWidgets.QMessageBox.critical(self, "Chyba", f"Chyba při mazání: {err}")

    def get_selected_reward_id(self):
        sel = self.rewards_table.selectedItems()
        if not sel:
            return None
        row = self.rewards_table.row(sel[0])
        item_id = self.rewards_table.item(row, 0)
        if not item_id:
            return None
        return item_id.data(QtCore.Qt.UserRole)

    def add_reward(self):
        t_id = self.get_selected_type_id()
        if t_id is None:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte Treasure Type nahoře.")
            return
        dialog = TreasureRewardDialog(self.connection, reward_id=None, treasure_type_id=t_id)
        if dialog.exec_():
            self.load_rewards(t_id)

    def edit_selected_reward_button(self):
        """Metoda spojená s tlačítkem pro úpravu odměny."""
        self.edit_selected_reward()

    def edit_selected_reward(self, row=None, col=None):
        """Otevře dialog pro úpravu vybrané odměny."""
        if row is not None and col is not None:
            # Pokud je metoda volána z cellDoubleClicked
            id_item = self.rewards_table.item(row, 0)
            if not id_item:
                return
            rew_id = id_item.data(QtCore.Qt.UserRole)
            t_id = self.get_selected_type_id()
            if t_id is None:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte Treasure Type.")
                return
        else:
            # Pokud je metoda volána z tlačítka
            rew_id = self.get_selected_reward_id()
            if rew_id is None:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte odměnu v tabulce.")
                return
            t_id = self.get_selected_type_id()
            if t_id is None:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte Treasure Type.")
                return

        # Potřebujeme i treasure_type_id
        dialog = TreasureRewardDialog(self.connection, reward_id=rew_id, treasure_type_id=t_id)
        if dialog.exec_():
            self.load_rewards(t_id)

    def delete_selected_reward(self):
        rew_id = self.get_selected_reward_id()
        if rew_id is None:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte odměnu v tabulce.")
            return
        confirm = QtWidgets.QMessageBox.question(self, "Smazat?", "Opravdu chcete smazat vybraný reward?")
        if confirm == QtWidgets.QMessageBox.Yes:
            query = "DELETE FROM aprts_treasure_rewards WHERE id=%s"
            params = (rew_id,)
            cursor = self.execute_query(query, params, dictionary=False)
            if cursor is None:
                return
            try:
                self.connection.commit()
                logging.debug("Commit successful for DELETE aprts_treasure_rewards")
                t_id = self.get_selected_type_id()
                if t_id:
                    self.load_rewards(t_id)
            except mysql.connector.Error as err:
                logging.error(f"Error committing DELETE aprts_treasure_rewards: {err}")
                QtWidgets.QMessageBox.critical(self, "Chyba", f"Chyba při mazání: {err}")

    # ==========================================
    #  TAB 2: Treasures + Clues
    # ==========================================
    def init_treasures_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.tab_treasures.setLayout(layout)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        layout.addWidget(splitter)

        # Tabulka pokladů
        top_widget = QtWidgets.QWidget()
        top_layout = QtWidgets.QVBoxLayout()
        top_widget.setLayout(top_layout)

        self.treasures_table = QtWidgets.QTableWidget()
        self.treasures_table.setColumnCount(4)  # Změna z 6 na 4 sloupce
        self.treasures_table.setHorizontalHeaderLabels(["ID", "Name", "Active", "Coordinates"])  # Nový sloupec
        self.treasures_table.setSortingEnabled(True)
        self.treasures_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.treasures_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.treasures_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)  # Zabránění editování
        self.treasures_table.cellDoubleClicked.connect(self.edit_selected_treasure)  # Dvojklik pro editaci
        self.treasures_table.cellClicked.connect(self.on_treasure_selected)

        top_layout.addWidget(self.treasures_table)

        tre_btn_layout = QtWidgets.QHBoxLayout()
        add_tre_btn = QtWidgets.QPushButton("Přidat Treasure")
        add_tre_btn.clicked.connect(self.add_treasure)
        edit_tre_btn = QtWidgets.QPushButton("Upravit Treasure")
        edit_tre_btn.clicked.connect(self.edit_selected_treasure_button)  # Nová metoda
        del_tre_btn = QtWidgets.QPushButton("Smazat Treasure")
        del_tre_btn.clicked.connect(self.delete_selected_treasure)
        
        # Přidání tlačítka "Obnovit"
        refresh_tre_btn = QtWidgets.QPushButton("Obnovit")
        refresh_tre_btn.clicked.connect(self.load_treasures)

        tre_btn_layout.addWidget(add_tre_btn)
        tre_btn_layout.addWidget(edit_tre_btn)
        tre_btn_layout.addWidget(del_tre_btn)
        tre_btn_layout.addWidget(refresh_tre_btn)  # Přidání do layoutu

        top_layout.addLayout(tre_btn_layout)

        splitter.addWidget(top_widget)

        # Tabulka clues
        bottom_widget = QtWidgets.QWidget()
        bottom_layout = QtWidgets.QVBoxLayout()
        bottom_widget.setLayout(bottom_layout)

        self.clues_table = QtWidgets.QTableWidget()
        self.clues_table.setColumnCount(5)
        self.clues_table.setHorizontalHeaderLabels(["ID", "Text", "Prop", "Count", "Coordinates"])
        self.clues_table.setSortingEnabled(True)
        self.clues_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.clues_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.clues_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)  # Zabránění editování
        self.clues_table.cellDoubleClicked.connect(self.edit_selected_clue)  # Dvojklik pro editaci

        bottom_layout.addWidget(self.clues_table)

        clu_btn_layout = QtWidgets.QHBoxLayout()
        add_clu_btn = QtWidgets.QPushButton("Přidat Clue")
        add_clu_btn.clicked.connect(self.add_clue)
        edit_clu_btn = QtWidgets.QPushButton("Upravit Clue")
        edit_clu_btn.clicked.connect(self.edit_selected_clue_button)  # Nová metoda
        del_clu_btn = QtWidgets.QPushButton("Smazat Clue")
        del_clu_btn.clicked.connect(self.delete_selected_clue)
        
        # Přidání tlačítka "Obnovit" pro Clues
        refresh_clu_btn = QtWidgets.QPushButton("Obnovit")
        refresh_clu_btn.clicked.connect(lambda: self.load_clues(self.get_selected_treasure_id()))

        clu_btn_layout.addWidget(add_clu_btn)
        clu_btn_layout.addWidget(edit_clu_btn)
        clu_btn_layout.addWidget(del_clu_btn)
        clu_btn_layout.addWidget(refresh_clu_btn)  # Přidání do layoutu

        bottom_layout.addLayout(clu_btn_layout)

        splitter.addWidget(bottom_widget)

        # Načteme treasures
        self.load_treasures()

    def load_treasures(self):
        query = "SELECT * FROM aprts_treasures ORDER BY id"
        cursor = self.execute_query(query)
        if cursor is None:
            return

        rows = cursor.fetchall()

        self.treasures_table.setRowCount(0)
        for i, row in enumerate(rows):
            self.treasures_table.insertRow(i)
            id_item = QtWidgets.QTableWidgetItem(str(row["id"]))
            id_item.setData(QtCore.Qt.UserRole, row["id"])
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.treasures_table.setItem(i, 0, id_item)

            name_str = decode_if_bytes(row["name"])
            name_item = QtWidgets.QTableWidgetItem(name_str)
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.treasures_table.setItem(i, 1, name_item)

            active_str = "Yes" if row["active"] else "No"
            active_item = QtWidgets.QTableWidgetItem(active_str)
            active_item.setFlags(active_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.treasures_table.setItem(i, 2, active_item)

            # Sestavení formátu vector3(x, y, z)
            vector_str = f"vector3({row['coord_x']}, {row['coord_y']}, {row['coord_z']})"
            coords_item = QtWidgets.QTableWidgetItem(vector_str)
            coords_item.setFlags(coords_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.treasures_table.setItem(i, 3, coords_item)

        self.treasures_table.resizeColumnsToContents()

    def get_selected_treasure_id(self):
        sel = self.treasures_table.selectedItems()
        if not sel:
            return None
        row = self.treasures_table.row(sel[0])
        id_item = self.treasures_table.item(row, 0)
        if not id_item:
            return None
        return id_item.data(QtCore.Qt.UserRole)

    def on_treasure_selected(self, row, col):
        tr_id = self.get_selected_treasure_id()
        self.load_clues(tr_id)

    def load_clues(self, treasure_id):
        if not treasure_id:
            self.clues_table.setRowCount(0)
            return
        query = "SELECT * FROM aprts_treasure_clues WHERE treasure_id=%s"
        params = (treasure_id,)
        cursor = self.execute_query(query, params)
        if cursor is None:
            return

        rows = cursor.fetchall()

        self.clues_table.setRowCount(0)
        for i, row in enumerate(rows):
            self.clues_table.insertRow(i)
            id_item = QtWidgets.QTableWidgetItem(str(row["id"]))
            id_item.setData(QtCore.Qt.UserRole, row["id"])
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.clues_table.setItem(i, 0, id_item)

            text_str = decode_if_bytes(row["text"]) or ""
            text_item = QtWidgets.QTableWidgetItem(text_str)
            text_item.setFlags(text_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.clues_table.setItem(i, 1, text_item)

            prop_str = decode_if_bytes(row["prop"]) or ""
            prop_item = QtWidgets.QTableWidgetItem(prop_str)
            prop_item.setFlags(prop_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.clues_table.setItem(i, 2, prop_item)

            count_val = row["count"]
            count_item = QtWidgets.QTableWidgetItem(str(count_val))
            count_item.setFlags(count_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.clues_table.setItem(i, 3, count_item)

            # Sestavení formátu vector3(x, y, z)
            coords_txt = f"vector3({row['coord_x']}, {row['coord_y']}, {row['coord_z']})"
            coords_item = QtWidgets.QTableWidgetItem(coords_txt)
            coords_item.setFlags(coords_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.clues_table.setItem(i, 4, coords_item)

        self.clues_table.resizeColumnsToContents()

    def add_treasure(self):
        dialog = TreasureDialog(self.connection, treasure_id=None)
        if dialog.exec_():
            self.load_treasures()

    def edit_selected_treasure_button(self):
        """Metoda spojená s tlačítkem pro úpravu pokladu."""
        self.edit_selected_treasure()

    def edit_selected_treasure(self, row=None, col=None):
        """Otevře dialog pro úpravu vybraného pokladu."""
        if row is not None and col is not None:
            # Pokud je metoda volána z cellDoubleClicked
            id_item = self.treasures_table.item(row, 0)
            if not id_item:
                return
            tr_id = id_item.data(QtCore.Qt.UserRole)
        else:
            # Pokud je metoda volána z tlačítka
            tr_id = self.get_selected_treasure_id()
            if tr_id is None:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte poklad.")
                return

        dialog = TreasureDialog(self.connection, treasure_id=tr_id)
        if dialog.exec_():
            self.load_treasures()

    def delete_selected_treasure(self):
        tr_id = self.get_selected_treasure_id()
        if not tr_id:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte poklad.")
            return
        confirm = QtWidgets.QMessageBox.question(self, "Smazat?", "Opravdu chcete smazat vybraný poklad?")
        if confirm == QtWidgets.QMessageBox.Yes:
            query = "DELETE FROM aprts_treasures WHERE id=%s"
            params = (tr_id,)
            cursor = self.execute_query(query, params, dictionary=False)
            if cursor is None:
                return
            try:
                self.connection.commit()
                logging.debug("Commit successful for DELETE aprts_treasures")
                self.load_treasures()
                self.clues_table.setRowCount(0)
            except mysql.connector.Error as err:
                logging.error(f"Error committing DELETE aprts_treasures: {err}")
                QtWidgets.QMessageBox.critical(self, "Chyba", f"Chyba při mazání: {err}")

    # Clues
    def get_selected_clue_id(self):
        sel = self.clues_table.selectedItems()
        if not sel:
            return None
        row = self.clues_table.row(sel[0])
        id_item = self.clues_table.item(row, 0)
        if not id_item:
            return None
        return id_item.data(QtCore.Qt.UserRole)

    def add_clue(self):
        tr_id = self.get_selected_treasure_id()
        if not tr_id:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte poklad.")
            return
        dlg = TreasureClueDialog(self.connection, clue_id=None, treasure_id=tr_id)
        if dlg.exec_():
            self.load_clues(tr_id)

    def edit_selected_clue_button(self):
        """Metoda spojená s tlačítkem pro úpravu clue."""
        self.edit_selected_clue()

    def edit_selected_clue(self, row=None, col=None):
        """Otevře dialog pro úpravu vybrané clue."""
        if row is not None and col is not None:
            # Pokud je metoda volána z cellDoubleClicked
            id_item = self.clues_table.item(row, 0)
            if not id_item:
                return
            c_id = id_item.data(QtCore.Qt.UserRole)
            tr_id = self.get_selected_treasure_id()
            if tr_id is None:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte poklad.")
                return
        else:
            # Pokud je metoda volána z tlačítka
            c_id = self.get_selected_clue_id()
            if c_id is None:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte clue.")
                return
            tr_id = self.get_selected_treasure_id()
            if tr_id is None:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte poklad.")
                return

        dlg = TreasureClueDialog(self.connection, clue_id=c_id, treasure_id=tr_id)
        if dlg.exec_():
            self.load_clues(tr_id)

    def delete_selected_clue(self):
        c_id = self.get_selected_clue_id()
        if not c_id:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Nejprve vyberte clue.")
            return
        confirm = QtWidgets.QMessageBox.question(self, "Smazat?", "Opravdu chcete smazat vybraný clue?")
        if confirm == QtWidgets.QMessageBox.Yes:
            query = "DELETE FROM aprts_treasure_clues WHERE id=%s"
            params = (c_id,)
            cursor = self.execute_query(query, params, dictionary=False)
            if cursor is None:
                return
            try:
                self.connection.commit()
                logging.debug("Commit successful for DELETE aprts_treasure_clues")
                tr_id = self.get_selected_treasure_id()
                if tr_id:
                    self.load_clues(tr_id)
            except mysql.connector.Error as err:
                logging.error(f"Error committing DELETE aprts_treasure_clues: {err}")
                QtWidgets.QMessageBox.critical(self, "Chyba", f"Chyba při mazání: {err}")

# -----------------------------------------
# Hlavní spustitelná část pro test
# -----------------------------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    try:
        connection = mysql.connector.connect(
            host='db-server.kkrp.cz',
            user='spoiledmouse',
            password='bE8e7AqiG8w43itITaf361Bu8182Ku*',
            database='s29_dev-redm'
        )
        logging.info("Successfully connected to the database.")
    except mysql.connector.Error as err:
        logging.error(f"Chyba při připojování k databázi: {err}")
        sys.exit(1)

    dialog = TreasureManagerDialog(connection)
    dialog.exec_()
