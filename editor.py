import random
import sys
import json
import os
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl

# Import externích souborů
from recipe_dialog import RecipeDialog
from item_manager import ItemManager
from longcraft_manager import LongcraftManager
from store_manager import StoreManagerDialog
from consumable_manager import ConsumableManagerDialog, ConsumableDialog
from housing_props_manager import HousingPropsManager, HousingPropDialog
from category_manager import CategoryManagerDialog
from freeplace_manager import FreeplaceManager
from book_manager import BookManager
from image_utils import get_item_image_label
from hunting_animal_manager import HuntingAnimalManager
from herbs_manager import HerbsManagerDialog
from plants_manager import PlantTypesManagerDialog
from treasure_manager import TreasureManagerDialog
from ranch_manager import RanchAnimalManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(BASE_DIR, 'config.json')
ASSET_PATH = os.path.join(BASE_DIR, 'assets')
SOUNDS = [
    os.path.join(ASSET_PATH, "click1.mp3"),
    os.path.join(ASSET_PATH, "click2.mp3"),
    os.path.join(ASSET_PATH, "click3.mp3"),
    os.path.join(ASSET_PATH, "click4.mp3"),
    os.path.join(ASSET_PATH, "click5.mp3"),
    os.path.join(ASSET_PATH, "click6.mp3"),
    # Přidej další zvuky podle potřeby
]

class RecipeManager(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.load_config()
        self.setWindowTitle(f"Správa Receptů - {self.config['version']}")
        self.setGeometry(100, 100, 1800, 700)  # Rozšířená šířka pro nové sloupce
        self.load_stylesheet(os.path.join(BASE_DIR, "stylesheet.qss"))

        self.connection = self.create_db_connection()
        self.image_cache = {}
        self.cache_dir = 'cache'
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        self.selected_category_id = None
        self.click_sound = QMediaPlayer()

        # V této cache budeme držet namapované skill -> label
        self.skill_cache = {}

        self.all_recipes = []  # seznam všech receptů z DB

        self.init_ui()

    def load_stylesheet(self, filepath):
        try:
            with open(filepath, "r") as file:
                self.setStyleSheet(file.read())
        except Exception as e:
            print(f"Chyba při načítání stylů: {e}")

    def load_config(self):
        with open(config_path, 'r') as f:
            self.config = json.load(f)

    def create_db_connection(self):
        print("Connecting to database...")
        try:
            connection = mysql.connector.connect(
                host=self.config['mysql']['host'],
                user=self.config['mysql']['user'],
                password=self.config['mysql']['password'],
                database=self.config['mysql']['database']
            )
            return connection
        except mysql.connector.Error as err:
            print(f"Error connecting to database: {err}")
            QtWidgets.QMessageBox.critical(
                self, "Chyba", f"Nelze se připojit k databázi: {err}")
            sys.exit(1)

    def play_click_sound(self):
        if not self.sound_checkbox.isChecked():
            return
        random_sound = random.choice(SOUNDS)
        self.click_sound.setMedia(QMediaContent(QUrl.fromLocalFile(random_sound)))
        self.click_sound.play()

    def init_ui(self):
        # Hlavní rozložení s QSplitter
        main_splitter = QtWidgets.QSplitter()
        main_splitter.setOrientation(QtCore.Qt.Horizontal)
        self.setCentralWidget(main_splitter)

        # Levý panel
        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout()
        left_panel.setLayout(left_layout)

        # Filtr typu (ComboBox)
        type_layout = QtWidgets.QHBoxLayout()
        type_label = QtWidgets.QLabel("Typ:")
        self.type_combobox = QtWidgets.QComboBox()
        self.type_combobox.addItem("Vše", None)
        self.type_combobox.currentIndexChanged.connect(self.apply_filters)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combobox)
        left_layout.addLayout(type_layout)

        # Filtr prop (ComboBox)
        prop_layout = QtWidgets.QHBoxLayout()
        prop_label = QtWidgets.QLabel("Prop:")
        self.prop_combobox = QtWidgets.QComboBox()
        self.prop_combobox.addItem("Vše", None)
        self.prop_combobox.currentIndexChanged.connect(self.apply_filters)
        prop_layout.addWidget(prop_label)
        prop_layout.addWidget(self.prop_combobox)
        left_layout.addLayout(prop_layout)

        # Vyhledávací pole
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Zadejte hledaný text...")
        self.search_edit.returnPressed.connect(self.apply_filters)
        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.apply_filters)
        search_button.clicked.connect(self.play_click_sound)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(search_button)
        left_layout.addLayout(search_layout)

        # Tabulka receptů
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            'Obrázek', 'ID', 'Item (Label)', 'Food', 'Housing',
            'Skill', 'XP', 'Název', 'Typ', 'Kategorie',
            'Prop', 'Akce'
        ])
        self.table.cellDoubleClicked.connect(self.play_click_sound)
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        self.table.setSortingEnabled(False)
        left_layout.addWidget(self.table)

        # Kontextové menu
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # Pravý panel pro kategorie
        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout()
        right_panel.setLayout(right_layout)
        categories_label = QtWidgets.QLabel("Kategorie")
        self.categories_list = QtWidgets.QListWidget()
        self.categories_list.itemClicked.connect(self.on_category_selected)
        right_layout.addWidget(categories_label)
        right_layout.addWidget(self.categories_list)

        reset_filter_button = QtWidgets.QPushButton("Zobrazit všechny")
        reset_filter_button.clicked.connect(self.reset_category_filter)
        right_layout.addWidget(reset_filter_button)

        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 1)

        # Toolbar
        toolbar = self.addToolBar("Hlavní")

        # Checkbox pro zapnutí/vypnutí zvuku
        self.sound_checkbox = QtWidgets.QCheckBox("Zapnout zvuk")
        self.sound_checkbox.setChecked(True)
        toolbar.addWidget(self.sound_checkbox)

        # Akce v toolbaru
        add_action = QtWidgets.QAction("Přidat Recept", self)
        add_action.triggered.connect(self.play_click_sound)
        add_action.triggered.connect(self.add_recipe)
        toolbar.addAction(add_action)

        refresh_action = QtWidgets.QAction("Obnovit", self)
        refresh_action.triggered.connect(self.play_click_sound)
        refresh_action.triggered.connect(self.load_all_recipes)
        toolbar.addAction(refresh_action)

        manage_categories_action = QtWidgets.QAction("Spravovat Kategorie", self)
        manage_categories_action.triggered.connect(self.play_click_sound)
        manage_categories_action.triggered.connect(self.manage_categories)
        toolbar.addAction(manage_categories_action)

        manage_items_action = QtWidgets.QAction("Itemy", self)
        manage_items_action.triggered.connect(self.play_click_sound)
        manage_items_action.triggered.connect(self.manage_items)
        toolbar.addAction(manage_items_action)

        manage_longcraft_action = QtWidgets.QAction("Longcraft", self)
        manage_longcraft_action.triggered.connect(self.play_click_sound)
        manage_longcraft_action.triggered.connect(self.manage_longcraft)
        toolbar.addAction(manage_longcraft_action)

        manage_stores_action = QtWidgets.QAction("Obchody", self)
        manage_stores_action.triggered.connect(self.play_click_sound)
        manage_stores_action.triggered.connect(self.manage_stores)
        toolbar.addAction(manage_stores_action)

        manage_herbs_action = QtWidgets.QAction("Sběr (Bylinky/Políčka)", self)
        manage_herbs_action.triggered.connect(self.play_click_sound)
        manage_herbs_action.triggered.connect(self.manage_herbs)
        toolbar.addAction(manage_herbs_action)

        manage_consumables_action = QtWidgets.QAction("Konzumovatelné", self)
        manage_consumables_action.triggered.connect(self.play_click_sound)
        manage_consumables_action.triggered.connect(self.manage_consumables)
        toolbar.addAction(manage_consumables_action)

        manage_housing_props_action = QtWidgets.QAction("Housing Props", self)
        manage_housing_props_action.triggered.connect(self.play_click_sound)
        manage_housing_props_action.triggered.connect(self.manage_housing_props)
        toolbar.addAction(manage_housing_props_action)

        manage_freeplace_action = QtWidgets.QAction("Freeplace", self)
        manage_freeplace_action.triggered.connect(self.play_click_sound)
        manage_freeplace_action.triggered.connect(self.manage_freeplace)
        toolbar.addAction(manage_freeplace_action)

        manage_books_action = QtWidgets.QAction("Knihy", self)
        manage_books_action.triggered.connect(self.play_click_sound)
        manage_books_action.triggered.connect(self.manage_books)
        toolbar.addAction(manage_books_action)

        manage_hunting_animals_action = QtWidgets.QAction("Zvířata (Hunting)", self)
        manage_hunting_animals_action.triggered.connect(self.play_click_sound)
        manage_hunting_animals_action.triggered.connect(self.manage_hunting_animals)
        toolbar.addAction(manage_hunting_animals_action)

        manage_plants_action = QtWidgets.QAction("Rostliny (Farming)", self)
        manage_plants_action.triggered.connect(self.play_click_sound)
        manage_plants_action.triggered.connect(self.manage_plants)
        toolbar.addAction(manage_plants_action)


        manage_ranch_animals_action = QtWidgets.QAction("Zvířata (Ranch)", self)
        manage_ranch_animals_action.triggered.connect(self.play_click_sound)
        manage_ranch_animals_action.triggered.connect(self.manage_ranch_animals)
        toolbar.addAction(manage_ranch_animals_action)


        manage_treasures_action = QtWidgets.QAction("Poklady", self)
        manage_treasures_action.triggered.connect(self.play_click_sound)
        manage_treasures_action.triggered.connect(self.manage_treasures)
        toolbar.addAction(manage_treasures_action)

        self.load_all_recipes()

    def load_all_recipes(self):
        """Načte všechny recepty z DB a uloží je do self.all_recipes.
           Zároveň nacachuje skill -> label, aby se nemuselo volat DB pro každý řádek.
        """
        cursor = self.connection.cursor(dictionary=True)

        query = """
            SELECT
                r.id,
                r.name,
                r.type,
                r.prop,
                rc.name AS category_name,
                r.result,
                r.skill,
                r.XP,
                i.item AS item_code,
                i.label,
                CASE WHEN c.item IS NOT NULL THEN 1 ELSE 0 END AS is_consumable,
                CASE WHEN h.item IS NOT NULL THEN 1 ELSE 0 END AS is_housing_prop
            FROM recipes r
            LEFT JOIN recipes_category rc ON r.category_id = rc.ID
            LEFT JOIN items i ON JSON_UNQUOTE(JSON_EXTRACT(r.result, '$.item')) = i.item
            LEFT JOIN aprts_consumable c ON c.item = i.item
            LEFT JOIN aprts_housing_props h ON h.item = i.item
        """
        cursor.execute(query)
        self.all_recipes = cursor.fetchall()

        # Zde posbíráme všechna jména skillů a v jednom dotazu je načteme z tabulky skills
        all_skills = {r['skill'] for r in self.all_recipes if r.get('skill')}
        self.skill_cache.clear()
        if all_skills:
            placeholder = ", ".join(["%s"] * len(all_skills))
            query_skills = f"SELECT name, label FROM skills WHERE name IN ({placeholder})"
            cursor.execute(query_skills, tuple(all_skills))
            result_skills = cursor.fetchall()
            for row in result_skills:
                self.skill_cache[row['name']] = row['label']

        self.load_categories()
        self.populate_type_combobox()
        self.populate_prop_combobox()

        self.apply_filters()

    def populate_type_combobox(self):
        self.type_combobox.blockSignals(True)
        self.type_combobox.clear()
        self.type_combobox.addItem("Vše", None)
        types = set()

        for r in self.all_recipes:
            if r['type'] and r['type'].strip():
                types.add(r['type'])

        for t in sorted(types):
            self.type_combobox.addItem(t, t)
        self.type_combobox.blockSignals(False)

    def populate_prop_combobox(self):
        self.prop_combobox.blockSignals(True)
        self.prop_combobox.clear()
        self.prop_combobox.addItem("Vše", None)
        props = set()

        for r in self.all_recipes:
            if r['prop'] and r['prop'].strip():
                props.add(r['prop'])

        for p in sorted(props):
            self.prop_combobox.addItem(p, p)
        self.prop_combobox.blockSignals(False)

    def load_categories(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT ID, name FROM recipes_category ORDER BY name")
        categories = cursor.fetchall()
        self.categories_list.clear()
        all_categories_item = QtWidgets.QListWidgetItem("Všechny kategorie")
        all_categories_item.setData(QtCore.Qt.UserRole, None)
        self.categories_list.addItem(all_categories_item)

        for category in categories:
            item = QtWidgets.QListWidgetItem(category['name'])
            item.setData(QtCore.Qt.UserRole, category['ID'])
            self.categories_list.addItem(item)

    def on_category_selected(self, item):
        self.selected_category_id = item.data(QtCore.Qt.UserRole)
        self.apply_filters()

    def reset_category_filter(self):
        self.selected_category_id = None
        self.categories_list.clearSelection()
        self.apply_filters()

    def apply_filters(self):
        filtered = self.all_recipes

        # 1) Filtr kategorie
        if self.selected_category_id is not None:
            sel_cat_name = None
            for i in range(self.categories_list.count()):
                cat_item = self.categories_list.item(i)
                cat_id = cat_item.data(QtCore.Qt.UserRole)
                if cat_id == self.selected_category_id:
                    sel_cat_name = cat_item.text()
                    break
            if sel_cat_name and sel_cat_name != "Všechny kategorie":
                filtered = [
                    r for r in filtered
                    if r.get('category_name') and r['category_name'] == sel_cat_name
                ]

        # 2) Filtr vyhledávání
        search_text = self.search_edit.text().strip().lower()
        if search_text:
            def matches_search(r):
                name = r['name'].lower() if r['name'] else ""
                item_code = (r['item_code'] or "").lower()
                label = (r['label'] or "").lower()
                # Skill label (nebo fallback)
                skill_label = self.skill_cache.get(r['skill'], r['skill']) or ""
                skill_label = skill_label.lower()
                xp = str(r['XP'])

                return (
                    search_text in name or
                    search_text in item_code or
                    search_text in label or
                    search_text in skill_label or
                    search_text in xp
                )

            filtered = [r for r in filtered if matches_search(r)]

        # 3) Filtr typu
        selected_type = self.type_combobox.currentData()
        if selected_type:
            filtered = [r for r in filtered if r['type'] == selected_type]

        # 4) Filtr prop
        selected_prop = self.prop_combobox.currentData()
        if selected_prop:
            filtered = [r for r in filtered if r['prop'] == selected_prop]

        self.show_recipes_in_table(filtered)

    def show_recipes_in_table(self, recipes_to_show):
        self.table.setRowCount(len(recipes_to_show))

        for row_number, recipe in enumerate(recipes_to_show):
            item_code = recipe.get('item_code')
            item_label = recipe.get('label')

            # Obrázek
            if item_code:
                image_label = get_item_image_label(item_code, self.cache_dir, self.connection)
            else:
                image_label = QtWidgets.QLabel("No Image")
                image_label.setAlignment(QtCore.Qt.AlignCenter)
            self.table.setCellWidget(row_number, 0, image_label)

            # ID
            id_item = QtWidgets.QTableWidgetItem(str(recipe['id']))
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            id_item.setData(QtCore.Qt.UserRole, recipe['id'])
            self.table.setItem(row_number, 1, id_item)

            # Item (Label)
            if item_code and item_label:
                combined_label = f"{item_code} ({item_label})"
            elif item_code:
                combined_label = item_code
            else:
                combined_label = ""
            item_label_item = QtWidgets.QTableWidgetItem(combined_label)
            item_label_item.setFlags(item_label_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 2, item_label_item)

            # Food
            is_consumable = bool(recipe.get('is_consumable', 0))
            consumable_item = QtWidgets.QTableWidgetItem("Ano" if is_consumable else "Ne")
            consumable_item.setFlags(consumable_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 3, consumable_item)

            # Housing
            is_housing_prop = bool(recipe.get('is_housing_prop', 0))
            housing_prop_item = QtWidgets.QTableWidgetItem("Ano" if is_housing_prop else "Ne")
            housing_prop_item.setFlags(housing_prop_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 4, housing_prop_item)

            # Skill
            skill_label = self.skill_cache.get(recipe.get('skill'), recipe.get('skill') or "")
            skill_item = QtWidgets.QTableWidgetItem(skill_label)
            skill_item.setFlags(skill_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 5, skill_item)

            # XP
            xp_val = recipe.get('XP', 0)
            xp_item = QtWidgets.QTableWidgetItem(str(xp_val))
            xp_item.setFlags(xp_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 6, xp_item)

            # Název
            name_item = QtWidgets.QTableWidgetItem(recipe['name'] if recipe['name'] else "")
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 7, name_item)

            # Typ
            type_text = recipe['type'] if recipe['type'] else ""
            type_item = QtWidgets.QTableWidgetItem(type_text)
            type_item.setFlags(type_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 8, type_item)

            # Kategorie
            category_text = recipe['category_name'] or ""
            category_item = QtWidgets.QTableWidgetItem(category_text)
            category_item.setFlags(category_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 9, category_item)

            # Prop
            prop_value = recipe['prop'] if recipe['prop'] else ""
            prop_item = QtWidgets.QTableWidgetItem(prop_value)
            prop_item.setFlags(prop_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 10, prop_item)

            # Tlačítka
            action_widget = self.create_action_buttons(recipe['id'])
            self.table.setCellWidget(row_number, 11, action_widget)

            # Výška řádku
            self.table.setRowHeight(row_number, 98)

        # Nastavení šířek sloupců (lze zavolat jen jednou)
        self.table.setColumnWidth(0, 100)   # Obrázek
        self.table.setColumnWidth(1, 30)    # ID
        self.table.setColumnWidth(2, 150)   # Item (Label)
        self.table.setColumnWidth(3, 50)    # Food
        self.table.setColumnWidth(4, 60)    # Housing
        self.table.setColumnWidth(5, 70)   # Skill
        self.table.setColumnWidth(6, 50)    # XP
        self.table.setColumnWidth(7, 150)   # Název
        self.table.setColumnWidth(8, 100)   # Typ
        self.table.setColumnWidth(9, 100)   # Kategorie
        self.table.setColumnWidth(10, 100)  # Prop
        self.table.setColumnWidth(11, 300)  # Akce

    def manage_books(self):
        dialog = BookManager(self.connection)
        dialog.exec_()

    def manage_freeplace(self):
        dialog = FreeplaceManager(self.connection)
        dialog.exec_()

    def manage_stores(self):
        dialog = StoreManagerDialog(self.connection)
        dialog.exec_()

    def manage_items(self):
        dialog = ItemManager(self.connection)
        dialog.exec_()

    def manage_categories(self):
        dialog = CategoryManagerDialog(self.connection)
        dialog.exec_()
        self.load_categories()

    def manage_longcraft(self):
        dialog = LongcraftManager(self.connection)
        dialog.exec_()

    def manage_consumables(self):
        dialog = ConsumableManagerDialog(self.connection)
        dialog.exec_()

    def manage_housing_props(self):
        dialog = HousingPropsManager(self.connection)
        dialog.exec_()

    def manage_hunting_animals(self):
        dialog = HuntingAnimalManager(self.connection)
        dialog.exec_()

    def manage_herbs(self):
        dialog = HerbsManagerDialog(self.connection)
        dialog.exec_()

    def manage_plants(self):
        dialog = PlantTypesManagerDialog(self.connection)
        dialog.exec_()


    def manage_ranch_animals(self):
        dialog = RanchAnimalManager(self.connection)
        dialog.exec_()

    def manage_treasures(self):
        dialog = TreasureManagerDialog(self.connection)
        dialog.exec_()

    def create_action_buttons(self, recipe_id):
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Tlačítko Upravit
        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.setIcon(QtGui.QIcon.fromTheme('edit'))
        edit_button.setToolTip("Upravit")
        edit_button.clicked.connect(self.play_click_sound)
        edit_button.clicked.connect(lambda _, rid=recipe_id: self.edit_recipe_by_id(rid))
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        h_layout.addWidget(edit_button)

        # Tlačítko Kopírovat
        copy_button = QtWidgets.QPushButton("Kopírovat")
        copy_button.setIcon(QtGui.QIcon.fromTheme('edit-copy'))
        copy_button.setToolTip("Kopírovat")
        copy_button.clicked.connect(self.play_click_sound)
        copy_button.clicked.connect(lambda _, rid=recipe_id: self.copy_recipe_by_id(rid))
        copy_button.setStyleSheet("background-color: #5bc0de; color: white;")
        h_layout.addWidget(copy_button)

        # Tlačítko Smazat
        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.setIcon(QtGui.QIcon.fromTheme('edit-delete'))
        delete_button.setToolTip("Smazat")
        delete_button.clicked.connect(self.play_click_sound)
        delete_button.clicked.connect(lambda _, rid=recipe_id: self.delete_recipe_by_id(rid))
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        h_layout.addWidget(delete_button)

        widget.setLayout(h_layout)
        return widget

    def edit_recipe_by_id(self, recipe_id):
        dialog = RecipeDialog(self.connection, recipe_id)
        if dialog.exec_():
            self.load_all_recipes()

    def copy_recipe_by_id(self, recipe_id):
        dialog = RecipeDialog(self.connection, recipe_id, copy=True)
        if dialog.exec_():
            self.load_all_recipes()

    def delete_recipe_by_id(self, recipe_id):
        confirm = QtWidgets.QMessageBox.question(
            self, "Potvrdit smazání",
            "Opravdu chcete smazat tento recept?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
            self.connection.commit()
            self.load_all_recipes()

    def add_recipe(self):
        dialog = RecipeDialog(self.connection)
        if dialog.exec_():
            self.load_all_recipes()

    def on_table_double_clicked(self, row, column):
        id_item = self.table.item(row, 1)
        if id_item:
            recipe_id = int(id_item.text())
            self.edit_recipe_by_id(recipe_id)

    def show_context_menu(self, position):
        index = self.table.indexAt(position)
        if not index.isValid():
            return

        row = index.row()
        recipe_id_item = self.table.item(row, 1)  # Sloupec s ID receptu
        if recipe_id_item:
            recipe_id = int(recipe_id_item.text())
        else:
            return

        menu = QtWidgets.QMenu()
        set_consumable_action = menu.addAction("Nastavit výsledný item jako konzumovatelný")
        set_housing_prop_action = menu.addAction("Nastavit výsledný item jako housing prop")

        action = menu.exec_(self.table.viewport().mapToGlobal(position))

        if action == set_consumable_action:
            self.set_result_item_as_consumable(recipe_id)
        elif action == set_housing_prop_action:
            self.set_result_item_as_housing_prop(recipe_id)

    def set_result_item_as_consumable(self, recipe_id):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT result FROM recipes WHERE id = %s", (recipe_id,))
        recipe = cursor.fetchone()
        if not recipe:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Recept nebyl nalezen.")
            return

        try:
            result = json.loads(recipe['result'])
            item_code = result.get('item')
            if not item_code:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Výsledný item nebyl nalezen.")
                return
        except json.JSONDecodeError:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Chyba při načítání výsledného itemu.")
            return

        dialog = ConsumableDialog(self.connection, item_code=item_code)
        if dialog.exec_():
            QtWidgets.QMessageBox.information(self, "Úspěch", "Item byl nastaven jako konzumovatelný.")
            self.load_all_recipes()
        else:
            QtWidgets.QMessageBox.warning(self, "Zrušeno", "Akce byla zrušena.")

    def set_result_item_as_housing_prop(self, recipe_id):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT result FROM recipes WHERE id = %s", (recipe_id,))
        recipe = cursor.fetchone()
        if not recipe:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Recept nebyl nalezen.")
            return

        try:
            result = json.loads(recipe['result'])
            item_code = result.get('item')
            if not item_code:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Výsledný item nebyl nalezen.")
                return
        except json.JSONDecodeError:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Chyba při načítání výsledného itemu.")
            return

        dialog = HousingPropDialog(self.connection, item_code=item_code)
        if dialog.exec_():
            QtWidgets.QMessageBox.information(self, "Úspěch", "Item byl nastaven jako housing prop.")
            self.load_all_recipes()
        else:
            QtWidgets.QMessageBox.warning(self, "Zrušeno", "Akce byla zrušena.")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = RecipeManager()
    window.show()
    app.setWindowIcon(QtGui.QIcon('icon.ico'))
    sys.exit(app.exec_())
