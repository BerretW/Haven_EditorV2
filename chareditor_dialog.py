import sys
import json
import mysql.connector
from mysql.connector import Error
from PyQt5 import QtWidgets, QtCore

from character_dialog import CharacterDialog


class CharacterEditorDialog(QtWidgets.QWidget):
    def __init__(self, config_path="configmain.json"):
        super().__init__()
        self.setWindowTitle("Haven Editor V2 - Characters")
        self.setGeometry(100, 100, 900, 600)

        self.config_path = config_path
        self.config = {}
        self.connection = None

        self.load_config()  # načte self.config z JSON
        self.connection = self.create_db_connection()

        self.init_ui()
        self.load_characters()  # načteme všechny charaktery při startu

    def load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            QtWidgets.QMessageBox.critical(
                self, "Chyba", f"Nelze načíst config ({self.config_path}): {e}"
            )
            sys.exit(1)

    def create_db_connection(self):
        print("Connecting to database...")
        try:
            connection = mysql.connector.connect(
                host=self.config['mysql']['host'],
                user=self.config['mysql']['user'],
                password=self.config['mysql']['password'],
                database=self.config['mysql']['database']
            )
            if connection.is_connected():
                print("Spojeno s DB.")
            return connection
        except mysql.connector.Error as err:
            print(f"Error connecting to database: {err}")
            QtWidgets.QMessageBox.critical(
                self, "Chyba", f"Nelze se připojit k databázi: {err}")
            sys.exit(1)

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # --- Řádek pro vyhledávání ---
        search_layout = QtWidgets.QHBoxLayout()
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("charidentifier, steamname, firstname, lastname")
        search_btn = QtWidgets.QPushButton("Search")
        search_btn.clicked.connect(self.search_characters)

        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        # Seznam postav
        self.results_list = QtWidgets.QListWidget()
        # double-click pro editaci
        self.results_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.results_list)

        # Tlačítko reload
        reload_btn = QtWidgets.QPushButton("Reload Characters")
        reload_btn.clicked.connect(self.load_characters)
        layout.addWidget(reload_btn)

    def load_characters(self):
        """
        Načteme všechny postavy z tabulky `characters`.
        """
        if not self.connection or not self.connection.is_connected():
            return

        self.results_list.clear()

        sql = """
            SELECT
              charidentifier, steamname, firstname, lastname,
              money, `group`, skinPlayer, coords
            FROM characters
            ORDER BY charidentifier
            LIMIT 500
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                self.decode_bin_fields(row)
                item_text = f"[{row['charidentifier']}] {row['steamname']} - {row['firstname']} {row['lastname']} (money={row['money']})"
                item = QtWidgets.QListWidgetItem(item_text)
                item.setData(QtCore.Qt.UserRole, row)
                self.results_list.addItem(item)

        except Error as e:
            QtWidgets.QMessageBox.critical(self, "DB Error", str(e))

    def decode_bin_fields(self, row):
        """Dekóduj binární pole (group, firstname, lastname) pokud jsou bytearray."""
        for fld in ['group', 'firstname', 'lastname', 'coords', 'skinPlayer']:
            if fld in row and isinstance(row[fld], (bytes, bytearray)):
                row[fld] = row[fld].decode('utf-8', errors='replace')

    def search_characters(self):
        """
        Hledání podle textu z self.search_edit.
        Porovnáváme: CAST(charidentifier) LIKE ... OR steamname LIKE ... OR firstname LIKE ... OR lastname LIKE ...
        """
        if not self.connection or not self.connection.is_connected():
            return
        self.results_list.clear()

        query_str = self.search_edit.text().strip()
        if not query_str:
            # pokud nic nezadáno, načteme všechny
            self.load_characters()
            return

        like_str = f"%{query_str}%"
        sql = """
            SELECT
              charidentifier, steamname, firstname, lastname,
              money, `group`, skinPlayer, coords
            FROM characters
            WHERE
              CAST(charidentifier AS CHAR) LIKE %s
              OR steamname LIKE %s
              OR firstname LIKE %s
              OR lastname LIKE %s
            ORDER BY charidentifier
            LIMIT 500
        """
        params = (like_str, like_str, like_str, like_str)

        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            for row in rows:
                self.decode_bin_fields(row)
                item_text = f"[{row['charidentifier']}] {row['steamname']} - {row['firstname']} {row['lastname']} (money={row['money']})"
                item = QtWidgets.QListWidgetItem(item_text)
                item.setData(QtCore.Qt.UserRole, row)
                self.results_list.addItem(item)
        except Error as e:
            QtWidgets.QMessageBox.critical(self, "DB Error", str(e))

    def on_item_double_clicked(self, item):
        """
        Otevře detailní CharacterDialog na double-click.
        """
        from character_dialog import CharacterDialog
        row_data = item.data(QtCore.Qt.UserRole)
        dialog = CharacterDialog(self.connection, row_data, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            # Pokud user uložil, reloadneme
            self.load_characters()


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = CharacterEditorDialog()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
