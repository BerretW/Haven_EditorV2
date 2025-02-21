from PyQt5 import QtWidgets, QtGui, QtCore
from consumable_dialog import ConsumableDialog
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class ConsumableManagerDialog(QtWidgets.QDialog):
    def __init__(self, connection, item_code=None, is_new=False):
        super().__init__()
        self.connection = connection
        self.item_code = item_code
        self.is_new = is_new
        self.setWindowTitle("Správa Konzumovatelných Položek")
        self.setGeometry(100, 100, 800, 600)
        self.load_stylesheet(os.path.join(BASE_DIR, "stylesheet1.qss"))
        self.init_ui()

    def load_stylesheet(self, filepath):
        """Načte stylesheet z externího souboru."""
        try:
            with open(filepath, "r") as file:
                self.setStyleSheet(file.read())
        except Exception as e:
            print(f"Chyba při načítání stylů: {e}")

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()

        # Vyhledávací pole
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Zadejte hledaný text...")
        self.search_edit.returnPressed.connect(self.load_consumables)
        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.load_consumables)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(search_button)

        layout.addLayout(search_layout)

        # Tabulka konzumovatelných položek
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ['ID', 'Item', 'Typ', 'Prop', 'Popis', 'Akce', ''])
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # Tlačítka
        buttons_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat")
        add_button.clicked.connect(self.add_consumable)
        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.clicked.connect(self.load_consumables)
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(refresh_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        self.load_consumables()

        # Pokud je předán item_code, otevřeme dialog pro přidání nebo úpravu
        if self.item_code:
            if self.is_new:
                self.add_consumable(item_code=self.item_code)
            else:
                self.edit_consumable_by_item_code(self.item_code)

    def load_consumables(self):
        search_text = self.search_edit.text().strip()
        cursor = self.connection.cursor(dictionary=True)
        if search_text:
            query = """
                SELECT * FROM aprts_consumable
                WHERE item LIKE %s OR dsc LIKE %s
            """
            search_pattern = f"%{search_text}%"
            cursor.execute(query, (search_pattern, search_pattern))
        else:
            query = "SELECT * FROM aprts_consumable"
            cursor.execute(query)
        consumables = cursor.fetchall()
        self.table.setRowCount(0)
        for row_number, consumable in enumerate(consumables):
            self.table.insertRow(row_number)

            id_item = QtWidgets.QTableWidgetItem(str(consumable['id']))
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 0, id_item)

            item_item = QtWidgets.QTableWidgetItem(consumable['item'])
            item_item.setFlags(item_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 1, item_item)

            type_item = QtWidgets.QTableWidgetItem(consumable['type'])
            type_item.setFlags(type_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 2, type_item)

            prop_item = QtWidgets.QTableWidgetItem(consumable['prop'])
            prop_item.setFlags(prop_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 3, prop_item)

            dsc_item = QtWidgets.QTableWidgetItem(consumable['dsc'] or '')
            dsc_item.setFlags(dsc_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 4, dsc_item)

            # Vytvoříme tlačítka pro akce
            action_widget = self.create_action_buttons(consumable['id'])
            self.table.setCellWidget(row_number, 5, action_widget)

        self.table.resizeColumnsToContents()

    def create_action_buttons(self, consumable_id):
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Tlačítko Upravit
        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.setStyleSheet(
            "background-color: #28a745; color: white; border-radius: 5px;")
        edit_button.clicked.connect(
            lambda _, cid=consumable_id: self.edit_consumable_by_id(cid))
        h_layout.addWidget(edit_button)

        # Tlačítko Smazat
        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.setStyleSheet(
            "background-color: #dc3545; color: white; border-radius: 5px;")
        delete_button.clicked.connect(
            lambda _, cid=consumable_id: self.delete_consumable_by_id(cid))
        h_layout.addWidget(delete_button)

        widget.setLayout(h_layout)
        return widget

    def on_table_double_clicked(self, row, column):
        id_item = self.table.item(row, 0)  # Sloupec 0 je ID
        if id_item:
            consumable_id = int(id_item.text())
            self.edit_consumable_by_id(consumable_id)

    def add_consumable(self, item_code=None):
        dialog = ConsumableDialog(self.connection, item_code=item_code)
        if dialog.exec_():
            self.load_consumables()

    def edit_consumable_by_id(self, consumable_id):
        dialog = ConsumableDialog(self.connection, consumable_id=consumable_id)
        if dialog.exec_():
            self.load_consumables()

    def edit_consumable_by_item_code(self, item_code):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id FROM aprts_consumable WHERE item = %s", (item_code,))
        consumable = cursor.fetchone()
        if consumable:
            self.edit_consumable_by_id(consumable['id'])
        else:
            self.add_consumable(item_code=item_code)

    def delete_consumable_by_id(self, consumable_id):
        confirm = QtWidgets.QMessageBox.question(self, "Potvrdit smazání",
                                                 "Opravdu chcete smazat tuto konzumovatelnou položku?",
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute(
                "DELETE FROM aprts_consumable WHERE id = %s", (consumable_id,))
            self.connection.commit()
            self.load_consumables()
