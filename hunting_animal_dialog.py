import sys
import json
import os
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
from mysql.connector import Error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from item_manager import ItemSelectionDialog  # Předpokládáme, že existuje a funguje.

class HuntingAnimalDialog(QtWidgets.QDialog):
    def __init__(self, connection, animal_id=None):
        super().__init__()
        self.connection = connection
        self.animal_id = animal_id
        self.setWindowTitle("Zvíře - Hunting")
        self.setGeometry(100, 100, 1000, 600)

        self.cache_dir = 'cache'
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        self.current_item_data = []
        self.grid_rows = 5
        self.grid_cols = 5

        self.init_ui()
        if self.animal_id:
            self.load_animal()
        else:
            # Nové zvíře
            self.current_item_data = []

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_layout = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit()
        self.label_edit = QtWidgets.QLineEdit()

        # Outfit a Model jako QSpinBox
        self.outfit_edit = QtWidgets.QSpinBox()
        self.outfit_edit.setRange(-2147483648, 2147483647)  # 32-bit integer range
        self.outfit_edit.setValue(0)

        self.model_edit = QtWidgets.QSpinBox()
        self.model_edit.setRange(-2147483648, 2147483647)
        self.model_edit.setValue(0)

        # Perfect
        self.perfect_checkbox = QtWidgets.QCheckBox("NULL")
        self.perfect_edit = QtWidgets.QSpinBox()
        self.perfect_edit.setRange(-2147483648, 2147483647)
        self.perfect_edit.setValue(0)
        self.perfect_checkbox.stateChanged.connect(self.toggle_perfect)

        # Poor
        self.poor_checkbox = QtWidgets.QCheckBox("NULL")
        self.poor_edit = QtWidgets.QSpinBox()
        self.poor_edit.setRange(-2147483648, 2147483647)
        self.poor_edit.setValue(0)
        self.poor_checkbox.stateChanged.connect(self.toggle_poor)

        # Good
        self.good_checkbox = QtWidgets.QCheckBox("NULL")
        self.good_edit = QtWidgets.QSpinBox()
        self.good_edit.setRange(-2147483648, 2147483647)
        self.good_edit.setValue(0)
        self.good_checkbox.stateChanged.connect(self.toggle_good)

        # Cenová pole jako QDoubleSpinBox
        self.base_price_edit = QtWidgets.QDoubleSpinBox()
        self.base_price_edit.setDecimals(2)
        self.base_price_edit.setRange(0.0, 1e9)
        self.base_price_edit.setValue(1.0)

        self.poor_price_edit = QtWidgets.QDoubleSpinBox()
        self.poor_price_edit.setDecimals(2)
        self.poor_price_edit.setRange(0.0, 1e9)
        self.poor_price_edit.setValue(0.0)

        self.good_price_edit = QtWidgets.QDoubleSpinBox()
        self.good_price_edit.setDecimals(2)
        self.good_price_edit.setRange(0.0, 1e9)
        self.good_price_edit.setValue(0.0)

        self.perfect_price_edit = QtWidgets.QDoubleSpinBox()
        self.perfect_price_edit.setDecimals(2)
        self.perfect_price_edit.setRange(0.0, 1e9)
        self.perfect_price_edit.setValue(0.0)

        # Nové pole pro Level
        self.level_edit = QtWidgets.QSpinBox()
        self.level_edit.setRange(0, 100)
        self.level_edit.setValue(0)

        # Nové pole pro XP
        self.xp_edit = QtWidgets.QSpinBox()
        self.xp_edit.setRange(0, 100)
        self.xp_edit.setValue(1)

        # Přidání widgetů do formuláře
        form_layout.addRow("Name:", self.name_edit)
        form_layout.addRow("Label:", self.label_edit)
        form_layout.addRow("Outfit:", self.outfit_edit)
        form_layout.addRow("Model:", self.model_edit)

        # Perfect
        perfect_layout = QtWidgets.QHBoxLayout()
        perfect_layout.addWidget(self.perfect_edit)
        perfect_layout.addWidget(self.perfect_checkbox)
        form_layout.addRow("Perfect:", perfect_layout)

        # Poor
        poor_layout = QtWidgets.QHBoxLayout()
        poor_layout.addWidget(self.poor_edit)
        poor_layout.addWidget(self.poor_checkbox)
        form_layout.addRow("Poor:", poor_layout)

        # Good
        good_layout = QtWidgets.QHBoxLayout()
        good_layout.addWidget(self.good_edit)
        good_layout.addWidget(self.good_checkbox)
        form_layout.addRow("Good:", good_layout)

        # Cenová pole
        form_layout.addRow("Base Price:", self.base_price_edit)
        form_layout.addRow("Poor Price:", self.poor_price_edit)
        form_layout.addRow("Good Price:", self.good_price_edit)
        form_layout.addRow("Perfect Price:", self.perfect_price_edit)

        # Přidání Level a XP do formuláře
        form_layout.addRow("Level:", self.level_edit)
        form_layout.addRow("XP:", self.xp_edit)

        # **Sekce Lovecká sezóna**
        season_group = QtWidgets.QGroupBox("Lovecká sezóna")
        season_layout = QtWidgets.QGridLayout()
        season_group.setLayout(season_layout)
        self.month_checkboxes = {}
        months = ["Leden", "Únor", "Březen", "Duben", "Květen", "Červen", "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"]
        for i, month in enumerate(months):
            checkbox = QtWidgets.QCheckBox(month)
            self.month_checkboxes[i+1] = checkbox # Měsíce indexujeme od 1
            season_layout.addWidget(checkbox, i // 4, i % 4) # Rozložení do 3 řádků a 4 sloupců
        layout.addWidget(season_group)


        layout.addLayout(form_layout) # Formulář s textovými poli a číselníky přidáme NAD sekci lovecké sezóny.

        # Loot section
        loot_group = QtWidgets.QGroupBox("Loot (5x5)")
        loot_layout = QtWidgets.QVBoxLayout()
        loot_group.setLayout(loot_layout)

        # Tlačítko pro přidání itemu z item_manageru
        add_item_button = QtWidgets.QPushButton("Přidat Item z ItemManageru")
        add_item_button.setIcon(QtGui.QIcon.fromTheme("list-add"))
        add_item_button.setToolTip("Přidat item z ItemManageru")
        add_item_button.clicked.connect(self.add_item_from_manager)
        loot_layout.addWidget(add_item_button)

        self.loot_table = QtWidgets.QTableWidget()
        self.loot_table.setRowCount(self.grid_rows)
        self.loot_table.setColumnCount(self.grid_cols)
        self.loot_table.horizontalHeader().setVisible(False)
        self.loot_table.verticalHeader().setVisible(False)
        self.loot_table.setIconSize(QtCore.QSize(64, 64))
        self.loot_table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.loot_table.customContextMenuRequested.connect(self.show_loot_context_menu)

        # Nastavení velikosti buněk na 150x150
        for c in range(self.grid_cols):
            self.loot_table.setColumnWidth(c, 150)
        for r in range(self.grid_rows):
            self.loot_table.setRowHeight(r, 150)

        loot_layout.addWidget(self.loot_table)

        layout.addWidget(loot_group)

        # Dialogové tlačítka
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.save_animal)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def toggle_perfect(self, state):
        if state == QtCore.Qt.Checked:
            self.perfect_edit.setEnabled(False)
        else:
            self.perfect_edit.setEnabled(True)

    def toggle_poor(self, state):
        if state == QtCore.Qt.Checked:
            self.poor_edit.setEnabled(False)
        else:
            self.poor_edit.setEnabled(True)

    def toggle_good(self, state):
        if state == QtCore.Qt.Checked:
            self.good_edit.setEnabled(False)
        else:
            self.good_edit.setEnabled(True)

    def load_animal(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM aprts_hunting_animals WHERE id = %s", (self.animal_id,))
        animal = cursor.fetchone()
        if animal:
            self.name_edit.setText(animal['name'])
            self.label_edit.setText(animal['label'] if animal['label'] else '')
            self.outfit_edit.setValue(int(animal.get('outfit') or 0))
            self.model_edit.setValue(int(animal.get('model') or 0))

            # Perfect
            perfect = animal.get('perfect')
            if perfect is None:
                self.perfect_checkbox.setChecked(True)
                self.perfect_edit.setValue(0)
            else:
                self.perfect_checkbox.setChecked(False)
                self.perfect_edit.setValue(int(perfect))

            # Poor
            poor = animal.get('poor')
            if poor is None:
                self.poor_checkbox.setChecked(True)
                self.poor_edit.setValue(0)
            else:
                self.poor_checkbox.setChecked(False)
                self.poor_edit.setValue(int(poor))

            # Good
            good = animal.get('good')
            if good is None:
                self.good_checkbox.setChecked(True)
                self.good_edit.setValue(0)
            else:
                self.good_checkbox.setChecked(False)
                self.good_edit.setValue(int(good))

            self.base_price_edit.setValue(float(animal.get('base_price') or 1.0))
            self.poor_price_edit.setValue(float(animal.get('poor_price') or 0.0))
            self.good_price_edit.setValue(float(animal.get('good_price') or 0.0))
            self.perfect_price_edit.setValue(float(animal.get('perfect_price') or 0.0))

            # **Načtení Level a XP**
            self.level_edit.setValue(int(animal.get('level') or 0))
            self.xp_edit.setValue(int(animal.get('XP') or 1))

            # **Načtení lovecké sezóny**
            hunting_season_text = animal.get('hunting_season', '[]')
            if isinstance(hunting_season_text, (bytes, bytearray)):
                hunting_season_text = hunting_season_text.decode('utf-8')
            try:
                hunting_season_data = json.loads(hunting_season_text)
                for month in hunting_season_data:
                    if month in self.month_checkboxes:
                        self.month_checkboxes[month].setChecked(True)
            except json.JSONDecodeError:
                pass # Pokud se JSON nepodaří načíst, necháme checkboxy nezaškrtnuté

            item_text = animal.get('item', '[{"name":"raw_meat","quantity":1}]')
            if isinstance(item_text, (bytes, bytearray)):
                item_text = item_text.decode('utf-8')

            try:
                self.current_item_data = json.loads(item_text)
            except json.JSONDecodeError:
                self.current_item_data = []

            self.load_loot_data()
        else:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Zvíře nebylo nalezeno.")
            self.reject()

    def load_loot_data(self):
        # Vymažeme tabulku
        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                self.loot_table.setItem(r, c, None)

        index = 0
        for entry in self.current_item_data:
            if index >= self.grid_rows * self.grid_cols:
                break
            r = index // self.grid_cols
            c = index % self.grid_cols
            item_name = entry.get("name", "")
            quantity = entry.get("quantity", 1)
            icon = self.get_item_icon(item_name)
            item_widget = QtWidgets.QTableWidgetItem()
            if icon:
                item_widget.setIcon(QtGui.QIcon(icon))
            item_widget.setText(f"{item_name}\n{quantity}")
            item_widget.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            self.loot_table.setItem(r, c, item_widget)
            index += 1

    def add_item_from_manager(self):
        dialog = ItemSelectionDialog(self.connection, single_selection=True)
        if dialog.exec_():
            selected_items = dialog.selected_items
            if selected_items:
                selected_item = selected_items[0]
                item_name = selected_item['item']
                label = selected_item['label']
                count, ok = QtWidgets.QInputDialog.getInt(
                    self, "Množství", f"Zadejte množství pro {label}:", 1, 1
                )
                if ok:
                    if len(self.current_item_data) >= self.grid_rows * self.grid_cols:
                        QtWidgets.QMessageBox.warning(
                            self, "Chyba", "Už není místo pro další itemy (5x5 zaplněno)."
                        )
                        return
                    self.current_item_data.append({"name": item_name, "quantity": count})
                    self.load_loot_data()

    def show_loot_context_menu(self, position):
        item = self.loot_table.itemAt(position)
        if not item:
            return
        text = item.text()
        lines = text.split('\n')
        if len(lines) < 2:
            return
        item_name = lines[0]
        quantity_str = lines[1]
        try:
            quantity = int(quantity_str)
        except ValueError:
            quantity = 1

        menu = QtWidgets.QMenu()
        change_qty_action = menu.addAction("Změnit množství")
        remove_action = menu.addAction("Odebrat")
        action = menu.exec_(self.loot_table.viewport().mapToGlobal(position))
        if action == remove_action:
            # Odstranit daný item z current_item_data
            for i, x in enumerate(self.current_item_data):
                if x['name'] == item_name and x['quantity'] == quantity:
                    del self.current_item_data[i]
                    break
            self.load_loot_data()
        elif action == change_qty_action:
            new_qty, ok = QtWidgets.QInputDialog.getInt(
                self, "Změnit množství", f"Zadejte nové množství pro {item_name}:", quantity, 1
            )
            if ok:
                # Najdeme první výskyt a změníme množství
                for x in self.current_item_data:
                    if x['name'] == item_name and x['quantity'] == quantity:
                        x['quantity'] = new_qty
                        break
                self.load_loot_data()

    def save_animal(self):
        name = self.name_edit.text().strip()
        label = self.label_edit.text().strip()
        outfit = self.outfit_edit.value()
        model = self.model_edit.value()

        # Perfect
        if self.perfect_checkbox.isChecked():
            perfect = None
        else:
            perfect = self.perfect_edit.value()

        # Poor
        if self.poor_checkbox.isChecked():
            poor = None
        else:
            poor = self.poor_edit.value()

        # Good
        if self.good_checkbox.isChecked():
            good = None
        else:
            good = self.good_edit.value()

        base_price = self.base_price_edit.value()
        poor_price = self.poor_price_edit.value()
        good_price = self.good_price_edit.value()
        perfect_price = self.perfect_price_edit.value()

        # Získání hodnot Level a XP
        level = self.level_edit.value()
        xp = self.xp_edit.value()

        # **Získání vybraných měsíců pro loveckou sezónu**
        selected_months = []
        for month_number, checkbox in self.month_checkboxes.items():
            if checkbox.isChecked():
                selected_months.append(month_number)
        hunting_season_text = json.dumps(selected_months, ensure_ascii=False)


        item_text = json.dumps(self.current_item_data, ensure_ascii=False)

        cursor = self.connection.cursor()
        if self.animal_id:
            query = """
                UPDATE aprts_hunting_animals SET
                name = %s, label = %s, outfit = %s, model = %s, perfect = %s, item = %s,
                poor = %s, good = %s, base_price = %s, poor_price = %s, good_price = %s,
                perfect_price = %s, XP = %s, level = %s, hunting_season = %s
                WHERE id = %s
            """
            params = (
                name, label, outfit, model, perfect, item_text,
                poor, good, base_price, poor_price, good_price, perfect_price,
                xp, level, hunting_season_text, self.animal_id
            )
        else:
            query = """
                INSERT INTO aprts_hunting_animals (
                    name, label, outfit, model, perfect, item, poor, good,
                    base_price, poor_price, good_price, perfect_price, XP, level, hunting_season
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                name, label, outfit, model, perfect, item_text,
                poor, good, base_price, poor_price, good_price, perfect_price,
                xp, level, hunting_season_text
            )

        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except Error as err:
            QtWidgets.QMessageBox.critical(
                self, "Chyba", f"Nastala chyba při ukládání: {err}"
            )

    def get_item_icon(self, item_name):
        return self.load_item_image(item_name)

    def load_item_image(self, item_name):
        cache_file_path = os.path.join(self.cache_dir, f"{item_name}.png")

        if os.path.exists(cache_file_path):
            pixmap = QtGui.QPixmap(cache_file_path)
        else:
            # Stáhneme obrázek z DB a URL pokud je dostupný
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT image FROM items WHERE item = %s", (item_name,))
            result = cursor.fetchone()
            if result and result.get('image'):
                image_file = result['image']
                url = f"https://api.westhavenrp.cz/storage/items/{image_file}"
                try:
                    from urllib.request import urlopen, Request
                    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    data = urlopen(req).read()
                    with open(cache_file_path, 'wb') as f:
                        f.write(data)
                    pixmap = QtGui.QPixmap()
                    pixmap.loadFromData(data)
                except Exception as e:
                    print(f"Error loading image for {item_name}: {e}")
                    pixmap = None
            else:
                pixmap = None
        return pixmap