import os
from PyQt5 import QtWidgets, QtGui, QtCore
from longcraft_recipe_dialog import LongcraftRecipeDialog
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
class LongcraftManager(QtWidgets.QDialog):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.setWindowTitle("Správa Dlouhých Receptů")
        self.setGeometry(100, 100, 1200, 600)
        self.load_stylesheet(os.path.join(BASE_DIR, "stylesheet.qss"))
        self.cache_dir = 'cache'  # Adresář pro cache obrázků
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.selected_prop = None  # Přidáno
        self.init_ui()
    def load_stylesheet(self, filepath):
        """Načte stylesheet z externího souboru."""
        try:
            with open(filepath, "r") as file:
                self.setStyleSheet(file.read())
        except Exception as e:
            print(f"Chyba při načítání stylů: {e}")
    def init_ui(self):
        # Hlavní rozložení s QSplitter
        main_splitter = QtWidgets.QSplitter()
        main_splitter.setOrientation(QtCore.Qt.Horizontal)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(main_splitter)

        # Levý panel pro vyhledávání a tabulku
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout()
        left_widget.setLayout(left_layout)

        # Vyhledávací pole
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Zadejte hledaný text...")
        self.search_edit.textChanged.connect(self.load_recipes)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        left_layout.addLayout(search_layout)

        # Tabulka receptů
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['Obrázek', 'ID', 'Název', 'Odměna', 'Prop', 'Akce'])
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        left_layout.addWidget(self.table)

        # Tlačítka
        button_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat Recept")
        add_button.clicked.connect(self.add_recipe)
        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.clicked.connect(self.load_recipes)
        button_layout.addWidget(add_button)
        button_layout.addWidget(refresh_button)
        left_layout.addLayout(button_layout)

        # Pravý panel pro filtry
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout()
        right_widget.setLayout(right_layout)

        filters_label = QtWidgets.QLabel("Filtry podle Prop")
        right_layout.addWidget(filters_label)

        # Seznam filtrů
        self.prop_filters_list = QtWidgets.QListWidget()
        self.prop_filters_list.itemClicked.connect(self.on_filter_selected)
        right_layout.addWidget(self.prop_filters_list)

        # Tlačítko pro resetování filtru
        reset_filter_button = QtWidgets.QPushButton("Zobrazit všechny")
        reset_filter_button.clicked.connect(self.reset_prop_filter)
        right_layout.addWidget(reset_filter_button)

        # Přidáme panely do splitteru
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)

        # Nastavíme poměr velikosti panelů
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 1)

        self.load_prop_filters()
        self.load_recipes()

    def load_prop_filters(self):
        cursor = self.connection.cursor()
        query = "SELECT DISTINCT prop FROM aprts_longCraft_recipes WHERE prop IS NOT NULL AND prop != ''"
        cursor.execute(query)
        props = cursor.fetchall()
        self.prop_filters_list.clear()
        all_props_item = QtWidgets.QListWidgetItem("Všechny Prop")
        all_props_item.setData(QtCore.Qt.UserRole, None)
        self.prop_filters_list.addItem(all_props_item)
        for (prop_value,) in props:
            item = QtWidgets.QListWidgetItem(prop_value)
            item.setData(QtCore.Qt.UserRole, prop_value)
            self.prop_filters_list.addItem(item)

    def on_filter_selected(self, item):
        self.selected_prop = item.data(QtCore.Qt.UserRole)
        self.load_recipes()

    def reset_prop_filter(self):
        self.selected_prop = None
        self.prop_filters_list.clearSelection()
        self.load_recipes()

    def load_recipes(self):
        search_text = self.search_edit.text().strip()
        cursor = self.connection.cursor(dictionary=True)
        params = []
        conditions = []
        if search_text:
            conditions.append("(name LIKE %s OR reward LIKE %s)")
            search_pattern = f"%{search_text}%"
            params.extend([search_pattern, search_pattern])
        if self.selected_prop:
            conditions.append("prop = %s")
            params.append(self.selected_prop)
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"""
            SELECT id, name, reward, count, time, prop, job, recipe
            FROM aprts_longCraft_recipes
            {where_clause}
        """
        cursor.execute(query, params)
        recipes = cursor.fetchall()
        self.table.setRowCount(0)
        for row_number, recipe in enumerate(recipes):
            self.table.insertRow(row_number)

            # Obrázek výsledné položky
            reward_item_name = recipe['reward']
            image_label = self.get_item_image_label(reward_item_name)
            self.table.setCellWidget(row_number, 0, image_label)

            # ID
            id_item = QtWidgets.QTableWidgetItem(str(recipe['id']))
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 1, id_item)

            # Název
            name_item = QtWidgets.QTableWidgetItem(recipe['name'])
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 2, name_item)

            # Odměna
            reward_item = QtWidgets.QTableWidgetItem(reward_item_name)
            reward_item.setFlags(reward_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 3, reward_item)

            # Prop
            prop_item = QtWidgets.QTableWidgetItem(recipe['prop'])
            prop_item.setFlags(prop_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 4, prop_item)

            # Akce
            action_widget = self.create_action_buttons(recipe['id'])
            self.table.setCellWidget(row_number, 5, action_widget)

            # Nastavíme výšku řádku
            self.table.setRowHeight(row_number, 64)

        self.table.resizeColumnsToContents()

    def get_item_image_label(self, item_name):
        # Vytvoříme název souboru pro cache
        cache_file_path = os.path.join(self.cache_dir, f"{item_name}.png")

        # Zkontrolujeme, zda soubor existuje v cache
        if os.path.exists(cache_file_path):
            # Načteme obrázek z cache
            pixmap = QtGui.QPixmap(cache_file_path)
        else:
            # Pokud není v cache, stáhneme obrázek a uložíme ho
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
                    # Uložíme data do souboru
                    with open(cache_file_path, 'wb') as f:
                        f.write(data)
                    pixmap = QtGui.QPixmap()
                    pixmap.loadFromData(data)
                except Exception as e:
                    print(f"Error loading image for {item_name}: {e}")
                    pixmap = None
            else:
                print(f"No image found for item {item_name}")
                pixmap = None

        label = QtWidgets.QLabel()
        if pixmap:
            label.setPixmap(pixmap)
        else:
            label.setText('No Image')
        label.setFixedSize(64, 64)
        label.setScaledContents(True)
        label.setAlignment(QtCore.Qt.AlignCenter)
        return label

    def create_action_buttons(self, recipe_id):
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Tlačítko Upravit
        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.setIcon(QtGui.QIcon.fromTheme('edit'))
        edit_button.setToolTip("Upravit")
        edit_button.clicked.connect(lambda _, rid=recipe_id: self.edit_recipe_by_id(rid))
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        h_layout.addWidget(edit_button)

        # Tlačítko Kopírovat
        copy_button = QtWidgets.QPushButton("Kopírovat")
        copy_button.setIcon(QtGui.QIcon.fromTheme('edit-copy'))
        copy_button.setToolTip("Kopírovat")
        copy_button.clicked.connect(lambda _, rid=recipe_id: self.copy_recipe_by_id(rid))
        copy_button.setStyleSheet("background-color: #5bc0de; color: white;")
        h_layout.addWidget(copy_button)

        # Tlačítko Smazat
        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.setIcon(QtGui.QIcon.fromTheme('edit-delete'))
        delete_button.setToolTip("Smazat")
        delete_button.clicked.connect(lambda _, rid=recipe_id: self.delete_recipe_by_id(rid))
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        h_layout.addWidget(delete_button)

        widget.setLayout(h_layout)
        return widget

    def on_table_double_clicked(self, row, column):
        id_item = self.table.item(row, 1)  # Sloupec 1 je ID
        if id_item:
            recipe_id = int(id_item.text())
            self.edit_recipe_by_id(recipe_id)

    def add_recipe(self):
        dialog = LongcraftRecipeDialog(self.connection)
        if dialog.exec_():
            self.load_recipes()
            self.load_prop_filters()  # Aktualizujeme seznam filtrů

    def edit_recipe_by_id(self, recipe_id):
        dialog = LongcraftRecipeDialog(self.connection, recipe_id)
        if dialog.exec_():
            self.load_recipes()
            self.load_prop_filters()  # Aktualizujeme seznam filtrů

    def copy_recipe_by_id(self, recipe_id):
        dialog = LongcraftRecipeDialog(self.connection, recipe_id, copy=True)
        if dialog.exec_():
            self.load_recipes()
            self.load_prop_filters()  # Aktualizujeme seznam filtrů

    def delete_recipe_by_id(self, recipe_id):
        confirm = QtWidgets.QMessageBox.question(self, "Potvrdit smazání",
                                                 f"Opravdu chcete smazat recept s ID {recipe_id}?",
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM aprts_longCraft_recipes WHERE id = %s", (recipe_id,))
            self.connection.commit()
            self.load_recipes()
            self.load_prop_filters()  # Aktualizujeme seznam filtrů
