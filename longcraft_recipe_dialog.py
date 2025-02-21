import json
import os
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from item_manager import ItemSelectionDialog

class LongcraftRecipeDialog(QtWidgets.QDialog):
    def __init__(self, connection, recipe_id=None, copy=False):
        super().__init__()
        self.connection = connection
        self.recipe_id = recipe_id
        self.copy = copy
        self.setWindowTitle("Dlouhý Recept")
        self.load_stylesheet(os.path.join(BASE_DIR, "stylesheet.qss"))
        self.cache_dir = 'cache'  # Adresář pro cache obrázků
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.init_ui()
        if self.recipe_id:
            self.load_recipe()
        else:
            self.recipe = {}
            self.update_materials_list()
    def load_stylesheet(self, filepath):
        """Načte stylesheet z externího souboru."""
        try:
            with open(filepath, "r") as file:
                self.setStyleSheet(file.read())
        except Exception as e:
            print(f"Chyba při načítání stylů: {e}")
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_layout = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit()
        self.reward_edit = QtWidgets.QLineEdit()
        self.reward_edit .setReadOnly(True)
        self.count_edit = QtWidgets.QSpinBox()
        self.count_edit.setMaximum(9999)
        self.time_edit = QtWidgets.QLineEdit()
        self.prop_edit = QtWidgets.QLineEdit()
        self.job_edit = QtWidgets.QLineEdit()

        # Nové pole pro chance
        self.chance_edit = QtWidgets.QSpinBox()
        self.chance_edit.setRange(0, 100)
        self.chance_edit.setValue(100)  # defaultně 100

        # Nové pole pro failed item (stejný princip jako reward)
        self.failed_edit = QtWidgets.QLineEdit()
        self.failed_edit.setReadOnly(False)
        self.select_failed_button = QtWidgets.QPushButton("Vybrat Failed Item")
        self.select_failed_button.clicked.connect(self.select_failed_item)

        failed_layout = QtWidgets.QHBoxLayout()
        failed_layout.addWidget(self.failed_edit)
        failed_layout.addWidget(self.select_failed_button)

        form_layout.addRow("Název:", self.name_edit)
        form_layout.addRow("Počet:", self.count_edit)
        form_layout.addRow("Čas:", self.time_edit)
        form_layout.addRow("Prop:", self.prop_edit)
        form_layout.addRow("Job:", self.job_edit)
        form_layout.addRow("Chance (%):", self.chance_edit)
        form_layout.addRow("Failed Item:", failed_layout)

        layout.addLayout(form_layout)

        # Obrázek výsledné položky
        self.result_image_label = QtWidgets.QLabel()
        self.result_image_label.setFixedSize(64, 64)
        self.result_image_label.setScaledContents(True)
        self.result_image_label.setAlignment(QtCore.Qt.AlignCenter)

        # Tlačítko pro výběr výsledné položky
        self.select_reward_button = QtWidgets.QPushButton("Vybrat Odměnu")
        self.select_reward_button.clicked.connect(self.select_reward_item)

        reward_layout = QtWidgets.QHBoxLayout()
        reward_layout.addWidget(QtWidgets.QLabel("Odměna:"))
        reward_layout.addWidget(self.reward_edit)
        reward_layout.addWidget(self.select_reward_button)
        reward_layout.addWidget(self.result_image_label)
        layout.addLayout(reward_layout)

        # Materiály
        self.materials_list = QtWidgets.QListWidget()
        self.materials_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.materials_list.customContextMenuRequested.connect(self.show_materials_context_menu)
        layout.addWidget(self.materials_list)

        add_material_button = QtWidgets.QPushButton("Přidat Materiál")
        add_material_button.clicked.connect(self.add_material)
        layout.addWidget(add_material_button)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.save_recipe)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_recipe(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM aprts_longCraft_recipes WHERE id = %s", (self.recipe_id,))
        recipe = cursor.fetchone()
        if recipe:
            self.name_edit.setText(recipe['name'])
            self.reward_edit.setText(recipe['reward'])
            self.count_edit.setValue(recipe['count'] or 0)
            self.time_edit.setText(recipe['time'])
            self.prop_edit.setText(recipe['prop'])
            self.job_edit.setText(recipe['job'] or '')
            self.chance_edit.setValue(recipe.get('chance', 100))
            failed_item = recipe.get('failed') or ''
            self.failed_edit.setText(failed_item)

            self.recipe = json.loads(recipe['recipe'])
            self.update_materials_list()
            # Nastavíme obrázek výsledné položky
            self.load_reward_image()
            if self.copy:
                # Pokud kopírujeme recept, resetujeme ID
                self.recipe_id = None

    def load_reward_image(self):
        reward_item_name = self.reward_edit.text().strip()
        if reward_item_name:
            pixmap = self.get_item_pixmap(reward_item_name)
            if pixmap:
                self.result_image_label.setPixmap(pixmap)
            else:
                self.result_image_label.setText('No Image')

    def get_item_pixmap(self, item_name):
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

        return pixmap

    def select_reward_item(self):
        dialog = ItemSelectionDialog(self.connection, single_selection=True)
        if dialog.exec_():
            result = dialog.selected_items
            if result:
                reward_item = result[0]
                self.reward_edit.setText(reward_item['item'])
                self.load_reward_image()

    def select_failed_item(self):
        dialog = ItemSelectionDialog(self.connection, single_selection=True)
        if dialog.exec_():
            result = dialog.selected_items
            if result:
                failed_item = result[0]
                self.failed_edit.setText(failed_item['item'])

    def update_materials_list(self):
        self.materials_list.clear()
        # Předpokládáme stejné sloty 1,2,3,4 jako dříve
        for slot in ['1', '2', '3', '4']:
            materials = self.recipe.get(slot, {})
            if materials:
                for item_name, count in materials.items():
                    label = self.get_item_label(item_name)
                    list_item_text = f"Slot {slot}: {label} x{count}"
                    list_item = QtWidgets.QListWidgetItem(list_item_text)
                    # Uložíme slot a název materiálu do UserRole
                    list_item.setData(QtCore.Qt.UserRole, {'slot': slot, 'item_name': item_name})
                    self.materials_list.addItem(list_item)
            else:
                list_item_text = f"Slot {slot}: Žádné položky"
                list_item = QtWidgets.QListWidgetItem(list_item_text)
                list_item.setData(QtCore.Qt.UserRole, {'slot': slot, 'item_name': None})
                self.materials_list.addItem(list_item)

    def get_item_label(self, item_name):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT label FROM items WHERE item = %s", (item_name,))
        result = cursor.fetchone()
        if result and result.get('label'):
            return result['label']
        else:
            return item_name

    def add_material(self):
        # Umožníme uživateli vybrat slot, do kterého chce přidat materiál
        slot, ok = QtWidgets.QInputDialog.getItem(
            self, "Vybrat Slot", "Vyberte slot pro materiál:", ['1', '2', '3', '4'], editable=False
        )
        if not ok:
            return
        dialog = ItemSelectionDialog(self.connection)
        if dialog.exec_():
            selected_items = dialog.selected_items
            for item in selected_items:
                item_name = item['item']
                count, ok = QtWidgets.QInputDialog.getInt(self, "Počet", f"Zadejte počet pro {item_name}:", 1, 1)
                if ok:
                    if slot not in self.recipe:
                        self.recipe[slot] = {}
                    self.recipe[slot][item_name] = count
            self.update_materials_list()

    def show_materials_context_menu(self, position):
        menu = QtWidgets.QMenu()
        change_quantity_action = menu.addAction("Změnit Množství")
        remove_action = menu.addAction("Odebrat Materiál")
        action = menu.exec_(self.materials_list.viewport().mapToGlobal(position))
        selected_items = self.materials_list.selectedItems()
        if selected_items:
            list_item = selected_items[0]
            data = list_item.data(QtCore.Qt.UserRole)
            slot = data['slot']
            item_name = data['item_name']
            if action == change_quantity_action and item_name:
                # Změna množství
                current_quantity = self.recipe[slot][item_name]
                new_quantity, ok = QtWidgets.QInputDialog.getInt(
                    self, "Změnit Množství", f"Zadejte nové množství pro {item_name}:",
                    value=current_quantity, min=1
                )
                if ok:
                    self.recipe[slot][item_name] = new_quantity
                    self.update_materials_list()
            elif action == remove_action:
                if item_name:
                    # Odebrat konkrétní materiál z daného slotu
                    del self.recipe[slot][item_name]
                    if not self.recipe[slot]:
                        # Pokud je slot prázdný, můžeme ho nechat prázdný
                        self.recipe[slot] = {}
                    self.update_materials_list()
                else:
                    # Odebrat celý prázdný slot
                    self.recipe[slot] = {}
                    self.update_materials_list()

    def save_recipe(self):
        name = self.name_edit.text().strip()
        reward = self.reward_edit.text().strip()
        count = self.count_edit.value()
        time_value = self.time_edit.text().strip()
        prop = self.prop_edit.text().strip()
        job = self.job_edit.text().strip() or None
        chance = self.chance_edit.value()
        failed_item = self.failed_edit.text().strip() or None
        recipe_text = json.dumps(self.recipe)

        if not name or not reward or not time_value or not prop:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Vyplňte prosím všechna povinná pole.")
            return

        cursor = self.connection.cursor()
        try:
            if self.recipe_id and not self.copy:
                # Aktualizace existujícího receptu
                query = """
                    UPDATE aprts_longCraft_recipes SET
                    name=%s, reward=%s, count=%s, time=%s, prop=%s, job=%s, recipe=%s,
                    chance=%s, failed=%s
                    WHERE id=%s
                """
                params = (name, reward, count, time_value, prop, job, recipe_text, chance, failed_item, self.recipe_id)
            else:
                # Vložení nového receptu
                query = """
                    INSERT INTO aprts_longCraft_recipes
                    (name, reward, count, time, prop, job, recipe, chance, failed)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (name, reward, count, time_value, prop, job, recipe_text, chance, failed_item)
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")
