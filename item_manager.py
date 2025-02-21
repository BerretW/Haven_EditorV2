import sys
import json
import os
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class ItemManager(QtWidgets.QDialog):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.setWindowTitle("Správa Položek")
        self.setGeometry(100, 100, 800, 600)
        self.load_stylesheet(os.path.join(BASE_DIR, "stylesheet.qss"))
        self.image_cache = {}
        self.cache_dir = 'cache'
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.items_data_cache = {}  # In-memory cache pro data položek
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
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Zadejte hledaný text...")
        # Odpojíme automatické vyhledávání při změně textu
        # self.search_edit.textChanged.connect(self.filter_items)
        # Připojíme vyhledávání při stisku Enter
        self.search_edit.returnPressed.connect(self.filter_items)
        # Přidáme tlačítko "Vyhledat"
        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.filter_items)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(search_button)
        main_layout.addLayout(search_layout)

        # Tabulka položek bez obrázků
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Item', 'Label', 'Akce'])
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        main_layout.addWidget(self.table)

        # Tlačítka
        button_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat Položku")
        add_button.clicked.connect(self.add_item)
        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.clicked.connect(self.load_items)
        manage_presets_button = QtWidgets.QPushButton("Správa Presetů")
        manage_presets_button.clicked.connect(self.manage_presets)
        button_layout.addWidget(add_button)
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(manage_presets_button)
        main_layout.addLayout(button_layout)

        self.load_items()

    def load_items(self):
        # Načteme všechna data položek z databáze a uložíme je do cache
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM items"
        cursor.execute(query)
        items = cursor.fetchall()
        self.items_data_cache = {item['item']: item for item in items}
        self.filter_items()

    def filter_items(self):
        search_text = self.search_edit.text().strip().lower()
        # Filtrovat položky v cache podle vyhledávacího textu
        filtered_items = []
        for item in self.items_data_cache.values():
            if (search_text in item['item'].lower()) or (search_text in item['label'].lower()):
                filtered_items.append(item)
        self.populate_table(filtered_items)

    def populate_table(self, items):
        self.table.setRowCount(0)
        for row_number, item in enumerate(items):
            self.table.insertRow(row_number)

            # Item
            item_item = QtWidgets.QTableWidgetItem(item['item'])
            item_item.setFlags(item_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 0, item_item)

            # Label
            label_item = QtWidgets.QTableWidgetItem(item['label'])
            label_item.setFlags(label_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 1, label_item)

            # Akce
            action_widget = self.create_action_buttons(item['item'])
            self.table.setCellWidget(row_number, 2, action_widget)

            # Nastavíme výšku řádku
            self.table.setRowHeight(row_number, 30)

        self.table.resizeColumnsToContents()

    def create_action_buttons(self, item_name):
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Tlačítko Upravit
        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.setIcon(QtGui.QIcon.fromTheme('edit'))
        edit_button.setToolTip("Upravit")
        edit_button.clicked.connect(lambda _, name=item_name: self.edit_item_by_name(name))
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        h_layout.addWidget(edit_button)

        # Tlačítko Smazat
        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.setIcon(QtGui.QIcon.fromTheme('edit-delete'))
        delete_button.setToolTip("Smazat")
        delete_button.clicked.connect(lambda _, name=item_name: self.delete_item_by_name(name))
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        h_layout.addWidget(delete_button)

        widget.setLayout(h_layout)
        return widget

    def on_table_double_clicked(self, row, column):
        item_item = self.table.item(row, 0)  # Sloupec 0 je Item
        if item_item:
            item_name = item_item.text()
            self.edit_item_by_name(item_name)

    def add_item(self):
        dialog = ItemDialog(self.connection)
        if dialog.exec_():
            self.load_items()

    def edit_item_by_name(self, item_name):
        dialog = ItemDialog(self.connection, item_name)
        if dialog.exec_():
            self.load_items()

    def delete_item_by_name(self, item_name):
        confirm = QtWidgets.QMessageBox.question(self, "Potvrdit smazání",
                                                 f"Opravdu chcete smazat položku '{item_name}'?",
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM items WHERE item = %s", (item_name,))
            self.connection.commit()
            self.load_items()

    def manage_presets(self):
        dialog = MetaPresetManager()
        dialog.exec_()

class ItemDialog(QtWidgets.QDialog):
    def __init__(self, connection, item_name=None):
        super().__init__()
        self.connection = connection
        self.item_name = item_name
        self.setWindowTitle("Položka")
        self.cache_dir = 'cache'
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.setStyleSheet("""
            QDialog {
                background-color: #f7f9fc;
                font-family: Arial;
                font-size: 12pt;
            }
            QLabel {
                font-weight: bold;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #c0c0c0;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #0078d7;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QTableWidget {
                border: 1px solid #c0c0c0;
                background-color: #ffffff;
                gridline-color: #dcdcdc;
                selection-background-color: #0078d7;
                selection-color: #ffffff;
            }
        """)
        self.init_ui()
        if self.item_name:
            self.load_item()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_layout = QtWidgets.QFormLayout()
        self.item_edit = QtWidgets.QLineEdit()
        self.label_edit = QtWidgets.QLineEdit()
        self.image_edit = QtWidgets.QLineEdit()
        self.weight_edit = QtWidgets.QDoubleSpinBox()
        self.weight_edit.setMaximum(100000)
        self.weight_edit.setDecimals(4)
        self.limit_edit = QtWidgets.QSpinBox()
        self.limit_edit.setMaximum(100000)
        self.description_edit = QtWidgets.QLineEdit()
        self.metadata_edit = QtWidgets.QPlainTextEdit()

        form_layout.addRow("Item:", self.item_edit)
        form_layout.addRow("Label:", self.label_edit)
        form_layout.addRow("Image:", self.image_edit)
        form_layout.addRow("Weight:", self.weight_edit)
        form_layout.addRow("Limit:", self.limit_edit)
        form_layout.addRow("Description:", self.description_edit)
        form_layout.addRow("Metadata (JSON):", self.metadata_edit)

        layout.addLayout(form_layout)

        # Tlačítka pro presety
        preset_layout = QtWidgets.QHBoxLayout()
        load_preset_button = QtWidgets.QPushButton("Načíst Preset")
        load_preset_button.clicked.connect(self.load_preset)
        save_preset_button = QtWidgets.QPushButton("Uložit jako Preset")
        save_preset_button.clicked.connect(self.save_as_preset)
        preset_layout.addWidget(load_preset_button)
        preset_layout.addWidget(save_preset_button)
        layout.addLayout(preset_layout)

        # Obrázek položky
        self.image_label = QtWidgets.QLabel()
        self.image_label.setFixedSize(128, 128)
        self.image_label.setScaledContents(True)
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.image_label)

        # Tlačítko pro načtení obrázku
        load_image_button = QtWidgets.QPushButton("Načíst Obrázek")
        load_image_button.clicked.connect(self.load_item_image)
        layout.addWidget(load_image_button)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.save_item)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_item(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM items WHERE item = %s", (self.item_name,))
        item = cursor.fetchone()
        if item:
            self.item_edit.setText(item['item'])
            self.label_edit.setText(item['label'])
            self.image_edit.setText(item['image'])
            self.weight_edit.setValue(item.get('weight') or 0.0)
            self.limit_edit.setValue(item.get('limit') or 0)
            self.description_edit.setText(item.get('desc') or '')
            metadata_text = json.dumps(json.loads(item.get('metadata') or '{}'), indent=4, ensure_ascii=False)
            self.metadata_edit.setPlainText(metadata_text)
            self.item_edit.setReadOnly(True)  # Neumožníme změnit název položky
            self.load_item_image()

    def load_item_image(self):
        item_name = self.item_edit.text().strip()
        image_file = self.image_edit.text().strip()
        if not image_file:
            image_file = 'default.png'  # Nastavíme výchozí obrázek

        cache_file_path = os.path.join(self.cache_dir, f"{item_name}.png")
        if os.path.exists(cache_file_path):
            pixmap = QtGui.QPixmap(cache_file_path)
        else:
            # Zkontrolujeme, zda default.png existuje v cache
            default_image_path = os.path.join(self.cache_dir, 'default.png')
            if not os.path.exists(default_image_path):
                # Stáhneme default.png z URL
                url = f"https://api.westhavenrp.cz/storage/items/default.png"
                try:
                    from urllib.request import urlopen, Request
                    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    data = urlopen(req).read()
                    with open(default_image_path, 'wb') as f:
                        f.write(data)
                except Exception as e:
                    print(f"Error loading default image: {e}")
            # Použijeme default.png
            pixmap = QtGui.QPixmap(default_image_path)
        if pixmap:
            self.image_label.setPixmap(pixmap)
        else:
            self.image_label.setText('No Image')

    def save_item(self):
        item_name = self.item_edit.text().strip()
        label = self.label_edit.text().strip()
        image = self.image_edit.text().strip()
        ## pokud je image prazdny, nastavime defaultni obrazek podle item_name.png
        if not image:
            image = f"{item_name}.png"

        weight = self.weight_edit.value()
        limit = self.limit_edit.value()
        description = self.description_edit.text().strip()
        metadata_text = self.metadata_edit.toPlainText().strip()

        if not item_name:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'Item' nesmí být prázdné.")
            return

        # Ověříme, zda je metadata platný JSON
        try:
            metadata_data = json.loads(metadata_text) if metadata_text else {}
            metadata_text = json.dumps(metadata_data, ensure_ascii=False)
        except json.JSONDecodeError as e:
            QtWidgets.QMessageBox.warning(self, "Chyba", f"Pole 'Metadata' musí být platný JSON.\nChyba: {e}")
            return

        cursor = self.connection.cursor()
        if self.item_name:
            query = """
                UPDATE items SET
                label = %s, image = %s, weight = %s, `limit` = %s, `desc` = %s, metadata = %s
                WHERE item = %s
            """
            params = (label, image, weight, limit, description, metadata_text, self.item_name)
        else:
            query = """
                INSERT INTO items (item, label, image, weight, `limit`, `desc`, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (item_name, label, image, weight, limit, description, metadata_text)
        try:
            print(query, params)
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")

    def load_preset(self):
        dialog = PresetSelectionDialog()
        if dialog.exec_():
            selected_preset = dialog.selected_preset
            if selected_preset:
                self.metadata_edit.setPlainText(json.dumps(selected_preset['metadata'], indent=4, ensure_ascii=False))

    def save_as_preset(self):
        preset_name, ok = QtWidgets.QInputDialog.getText(self, "Uložit jako Preset", "Zadejte název presetu:")
        if ok and preset_name:
            metadata_text = self.metadata_edit.toPlainText().strip()
            # Ověříme, zda je metadata platný JSON
            try:
                metadata_data = json.loads(metadata_text) if metadata_text else {}
            except json.JSONDecodeError as e:
                QtWidgets.QMessageBox.warning(self, "Chyba", f"Pole 'Metadata' musí být platný JSON.\nChyba: {e}")
                return
            # Uložíme preset
            presets = MetaPresetManager.load_presets()
            presets[preset_name] = metadata_data
            MetaPresetManager.save_presets(presets)
            QtWidgets.QMessageBox.information(self, "Uloženo", f"Preset '{preset_name}' byl uložen.")
            
class ItemSelectionDialog(QtWidgets.QDialog):
    def __init__(self, connection, single_selection=False):
        super().__init__()
        self.connection = connection
        self.single_selection = single_selection
        self.setWindowTitle("Výběr Položky")
        self.setGeometry(100, 100, 800, 600)
        self.selected_items = []
        self.init_ui()
    
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Vyhledat...")
        self.search_edit.textChanged.connect(self.load_items)
        layout.addWidget(self.search_edit)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['Item', 'Label'])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection if self.single_selection else QtWidgets.QAbstractItemView.MultiSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        
        self.table.doubleClicked.connect(self.select_item)
        layout.addWidget(self.table)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.load_items()
    
    def load_items(self):
        search_text = self.search_edit.text().strip()
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT item, label FROM items WHERE item LIKE %s OR label LIKE %s"
        search_pattern = f"%{search_text}%"
        cursor.execute(query, (search_pattern, search_pattern))
        items = cursor.fetchall()
        self.table.setRowCount(0)
        for row_number, item in enumerate(items):
            self.table.insertRow(row_number)
            item_item = QtWidgets.QTableWidgetItem(item['item'])
            self.table.setItem(row_number, 0, item_item)
            label_item = QtWidgets.QTableWidgetItem(item['label'])
            item_item.setFlags(item_item.flags() & ~QtCore.Qt.ItemIsEditable)
            label_item.setFlags(label_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 1, label_item)
        self.table.resizeColumnsToContents()
    
    def select_item(self, index):
        row = index.row()
        item_code = self.table.item(row, 0).text()
        label = self.table.item(row, 1).text()
        self.selected_items = [{'item': item_code, 'label': label}]
        if self.single_selection:
            self.accept()
    
    def accept_selection(self):
        selected_rows = self.table.selectionModel().selectedRows()
        self.selected_items = []
        for row_index in selected_rows:
            row = row_index.row()
            item_code = self.table.item(row, 0).text()
            label = self.table.item(row, 1).text()
            self.selected_items.append({'item': item_code, 'label': label})
        self.accept()
        
class MetaPresetManager(QtWidgets.QDialog):
    presets_file = 'metaPresets.json'

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Správa Presetů")
        self.presets = self.load_presets()
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Seznam presetů
        self.preset_list = QtWidgets.QListWidget()
        self.preset_list.itemDoubleClicked.connect(self.edit_preset)
        layout.addWidget(self.preset_list)

        # Tlačítka
        button_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat Preset")
        add_button.clicked.connect(self.add_preset)
        edit_button = QtWidgets.QPushButton("Upravit Preset")
        edit_button.clicked.connect(self.edit_selected_preset)
        delete_button = QtWidgets.QPushButton("Smazat Preset")
        delete_button.clicked.connect(self.delete_selected_preset)
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        layout.addLayout(button_layout)

        self.load_preset_list()

    def load_preset_list(self):
        self.preset_list.clear()
        for preset_name in self.presets.keys():
            item = QtWidgets.QListWidgetItem(preset_name)
            self.preset_list.addItem(item)

    def add_preset(self):
        dialog = PresetEditorDialog()
        if dialog.exec_():
            preset_name = dialog.preset_name
            metadata = dialog.metadata
            self.presets[preset_name] = metadata
            self.save_presets(self.presets)
            self.load_preset_list()

    def edit_selected_preset(self):
        selected_items = self.preset_list.selectedItems()
        if selected_items:
            preset_name = selected_items[0].text()
            self.edit_preset_by_name(preset_name)
        else:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Nevybrali jste žádný preset.")

    def delete_selected_preset(self):
        selected_items = self.preset_list.selectedItems()
        if selected_items:
            preset_name = selected_items[0].text()
            confirm = QtWidgets.QMessageBox.question(self, "Potvrdit smazání",
                                                     f"Opravdu chcete smazat preset '{preset_name}'?",
                                                     QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if confirm == QtWidgets.QMessageBox.Yes:
                del self.presets[preset_name]
                self.save_presets(self.presets)
                self.load_preset_list()
        else:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Nevybrali jste žádný preset.")

    def edit_preset(self, item):
        preset_name = item.text()
        self.edit_preset_by_name(preset_name)

    def edit_preset_by_name(self, preset_name):
        metadata = self.presets[preset_name]
        dialog = PresetEditorDialog(preset_name, metadata)
        if dialog.exec_():
            new_preset_name = dialog.preset_name
            new_metadata = dialog.metadata
            if new_preset_name != preset_name:
                del self.presets[preset_name]
            self.presets[new_preset_name] = new_metadata
            self.save_presets(self.presets)
            self.load_preset_list()

    @classmethod
    def load_presets(cls):
        if os.path.exists(cls.presets_file):
            with open(cls.presets_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {}

    @classmethod
    def save_presets(cls, presets):
        with open(cls.presets_file, 'w', encoding='utf-8') as f:
            json.dump(presets, f, ensure_ascii=False, indent=4)

class PresetEditorDialog(QtWidgets.QDialog):
    def __init__(self, preset_name='', metadata=None):
        super().__init__()
        self.setWindowTitle("Editor Presetu")
        self.preset_name = preset_name
        self.metadata = metadata or {}
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_layout = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit(self.preset_name)
        self.metadata_edit = QtWidgets.QPlainTextEdit(json.dumps(self.metadata, indent=4, ensure_ascii=False))

        form_layout.addRow("Název Presetu:", self.name_edit)
        form_layout.addRow("Metadata (JSON):", self.metadata_edit)

        layout.addLayout(form_layout)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.save_preset)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save_preset(self):
        self.preset_name = self.name_edit.text().strip()
        metadata_text = self.metadata_edit.toPlainText().strip()
        if not self.preset_name:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'Název Presetu' nesmí být prázdné.")
            return
        # Ověříme, zda je metadata platný JSON
        try:
            self.metadata = json.loads(metadata_text) if metadata_text else {}
            self.accept()
        except json.JSONDecodeError as e:
            QtWidgets.QMessageBox.warning(self, "Chyba", f"Pole 'Metadata' musí být platný JSON.\nChyba: {e}")
            return

class PresetSelectionDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Výběr Presetu")
        self.selected_preset = None
        self.presets = MetaPresetManager.load_presets()
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.preset_list = QtWidgets.QListWidget()
        for preset_name in self.presets.keys():
            item = QtWidgets.QListWidgetItem(preset_name)
            self.preset_list.addItem(item)
        layout.addWidget(self.preset_list)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.select_preset)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def select_preset(self):
        selected_items = self.preset_list.selectedItems()
        if selected_items:
            preset_name = selected_items[0].text()
            self.selected_preset = {
                'name': preset_name,
                'metadata': self.presets[preset_name]
            }
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Nevybrali jste žádný preset.")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # Pro testování můžete odkomentovat následující řádky a zadat své přihlašovací údaje
    # connection = mysql.connector.connect(
    #     host='your_host',
    #     user='your_username',
    #     password='your_password',
    #     database='your_database'
    # )
    # window = ItemManager(connection)
    # window.show()
    # sys.exit(app.exec_())
    pass  # V produkčním prostředí tento soubor importujeme, takže main není potřeba
