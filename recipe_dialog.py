import sys
import json
import os
from PyQt5 import QtWidgets, QtCore, QtGui
import mysql.connector
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from item_manager import ItemSelectionDialog
from recipe_weapon_dialog import RecipeWeaponDialog  # <-- nový dialog pro nastavení zbraně

class CategoryComboBox(QtWidgets.QComboBox):
    def __init__(self, connection, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection = connection
        self.setEditable(True)
        self.load_categories()
        self.completer = QtWidgets.QCompleter(self.categories_names)
        self.setCompleter(self.completer)

    def load_categories(self):
        cursor = self.connection.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT ID, name FROM recipes_category ORDER BY name")
        categories = cursor.fetchall()
        self.categories = categories
        self.categories_names = [category['name'] for category in categories]
        self.clear()
        for category in categories:
            self.addItem(category['name'], category['ID'])

class NewItemDialog(QtWidgets.QDialog):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.setWindowTitle("Vytvořit Nový Item")
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
        layout = QtWidgets.QFormLayout()

        self.item_name_edit = QtWidgets.QLineEdit()
        self.label_edit = QtWidgets.QLineEdit()
        self.weight_spin = QtWidgets.QDoubleSpinBox()
        self.weight_spin.setRange(0.0, 1000.0)
        self.weight_spin.setValue(1.0)
        self.limit_spin = QtWidgets.QSpinBox()
        self.limit_spin.setRange(1, 1000)
        self.limit_spin.setValue(10)

        layout.addRow("Spawn Name (item):", self.item_name_edit)
        layout.addRow("Název (label):", self.label_edit)
        layout.addRow("Váha (weight):", self.weight_spin)
        layout.addRow("Limit:", self.limit_spin)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def validate_and_accept(self):
        item_name = self.item_name_edit.text().strip()
        label = self.label_edit.text().strip()
        if not item_name or not label:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Spawn Name a Název nesmí být prázdné.")
            return
        self.accept()

    def get_item_data(self):
        return {
            'item': self.item_name_edit.text().strip(),
            'label': self.label_edit.text().strip(),
            'weight': self.weight_spin.value(),
            'limit': self.limit_spin.value()
        }

class RecipeDialog(QtWidgets.QDialog):
    def __init__(self, connection, recipe_id=None, copy=False):
        super().__init__()
        self.connection = connection
        self.recipe_id = recipe_id
        self.copy = copy
        self.image_cache = {}
        self.cache_dir = 'cache'
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.setWindowTitle("Recept")
        self.setGeometry(100, 100, 800, 600)
        
        # Načteme weapons.json, pokud existuje
        self.weapons_data = self.load_weapons_data()

        self.init_ui()
        if self.recipe_id:
            self.load_recipe()

    def load_weapons_data(self):
        """Načtení weapons.json, vrací dict nebo prázdný dict při chybě."""
        weapons_path = os.path.join(os.path.dirname(__file__), 'weapons.json')
        if os.path.exists(weapons_path):
            try:
                with open(weapons_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Chyba při načítání weapons.json: {e}")
                return {}
        return {}

    def load_skills(self):
        """Načte dovednosti ze tabulky `skills` a vrátí je jako seznam."""
        cursor = self.connection.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT name, label FROM skills ORDER BY label")
        skills = cursor.fetchall()
        return skills

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Formulář s receptem
        self.name_edit = QtWidgets.QLineEdit()
        self.type_edit = QtWidgets.QComboBox()
        self.type_edit.addItems(['hand', 'near_prop', 'on_prop', 'item'])
        self.type_edit.currentTextChanged.connect(self.update_defaults_based_on_type)

        self.trigger_item_edit = QtWidgets.QLineEdit()
        self.prop_edit = QtWidgets.QLineEdit()
        self.timer_edit = QtWidgets.QSpinBox()
        self.timer_edit.setMaximum(9999999)
        self.category_edit = CategoryComboBox(self.connection)
        self.isweapon_edit = QtWidgets.QCheckBox("Je zbraň")
        self.isweapon_edit.stateChanged.connect(self.weapon_state_changed)
        self.job_edit = QtWidgets.QLineEdit()
        self.grade_edit = QtWidgets.QSpinBox()
        self.grade_edit.setRange(0, 100)  # Přidej rozsah podle potřeby
        self.anim_dict_edit = QtWidgets.QLineEdit()
        self.anim_body_edit = QtWidgets.QLineEdit()
        self.comps_edit = QtWidgets.QLineEdit()

        # Dynamické pole pro skill
        self.skill_edit = QtWidgets.QComboBox()
        self.skill_edit.setEditable(True)
        skills = self.load_skills()
        self.skill_edit.addItem("")  # Prázdný výchozí prvek
        for skill in skills:
            self.skill_edit.addItem(skill['label'], skill['name'])  # Zobrazuje label, ukládá name

        # Nové pole pro XP
        self.xp_spin = QtWidgets.QSpinBox()
        self.xp_spin.setRange(0, 100)
        self.xp_spin.setValue(1)  # Výchozí hodnota podle databáze

        # Výchozí animace podle typu
        self.anim_dict_options = {
            'hand': 'script_mp@emotes@lets_craft@male@unarmed@upper',
            'near_prop': 'script_rc@sad1@ig@rsc2_ig0_bickering',
            'on_prop': 'script_proc@robberies@homestead@aberdeen@cooking',
            'cooking': 'script_proc@robberies@homestead@aberdeen@cooking',
            'item': 'script_mp@emotes@lets_craft@male@unarmed@upper'
        }
        self.anim_body_options = {
            'hand': ['action', 'action_alt1'],
            'near_prop': ['chopping_loop_01_pearson', 'chopping_base_sadie'],
            'on_prop': ['stir_loop_sis', 'react_look_front_loop'],
            'cooking': ['stir_loop_sis'],
            'item': ['action', 'action_alt1']
        }
        self.prop_options = {
            'hand': None,
            'near_prop': 'p_meatcuttingboard01x',
            'on_prop': 'p_stove01x',
            'cooking': 'p_stove01x',
            'item': None
        }

        self.anim_dict_completer = QtWidgets.QCompleter(list(self.anim_dict_options.values()))
        self.anim_dict_edit.setCompleter(self.anim_dict_completer)
        self.anim_body_model = QtCore.QStringListModel()
        self.anim_body_completer = QtWidgets.QCompleter(self.anim_body_model)
        self.anim_body_edit.setCompleter(self.anim_body_completer)

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Název:", self.name_edit)
        form_layout.addRow("Typ:", self.type_edit)
        form_layout.addRow("Spouštěcí Položka:", self.trigger_item_edit)
        form_layout.addRow("Prop:", self.prop_edit)
        form_layout.addRow("Časovač (ms):", self.timer_edit)
        form_layout.addRow("Kategorie:", self.category_edit)
        form_layout.addRow("", self.isweapon_edit)
        form_layout.addRow("Job:", self.job_edit)
        form_layout.addRow("Grade:", self.grade_edit)
        form_layout.addRow("Animace Dict:", self.anim_dict_edit)
        form_layout.addRow("Animace Body:", self.anim_body_edit)
        form_layout.addRow("Komponenty:", self.comps_edit)

        # Přidání nových polí do formuláře
        form_layout.addRow("Dovednost (skill):", self.skill_edit)
        form_layout.addRow("XP:", self.xp_spin)

        layout.addLayout(form_layout)

        # Tlačítko pro zbraň (otevře RecipeWeaponDialog, pokud je zaškrtnut isweapon)
        self.weapon_button = QtWidgets.QPushButton("Nastavit / Editovat zbraň…")
        self.weapon_button.clicked.connect(self.open_weapon_dialog)
        # Ve výchozím stavu skryté, zobrazí se jen pokud isweapon_edit je True
        self.weapon_button.setVisible(False)
        layout.addWidget(self.weapon_button)

        # Materiály
        materials_layout = QtWidgets.QVBoxLayout()
        materials_label = QtWidgets.QLabel("Materiály:")
        materials_layout.addWidget(materials_label)
        self.materials_list = QtWidgets.QListWidget()
        self.materials_list.setViewMode(QtWidgets.QListView.IconMode)
        self.materials_list.setIconSize(QtCore.QSize(64, 64))
        self.materials_list.setResizeMode(QtWidgets.QListView.Adjust)
        self.materials_list.setSpacing(10)
        self.materials_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.materials_list.customContextMenuRequested.connect(self.show_materials_context_menu)
        self.materials_list.itemDoubleClicked.connect(self.edit_material)
        self.materials_list.setMinimumHeight(200)
        self.materials_list.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        materials_layout.addWidget(self.materials_list)

        materials_buttons_layout = QtWidgets.QHBoxLayout()
        materials_add_button = QtWidgets.QPushButton("Přidat")
        materials_add_button.clicked.connect(self.add_material)
        materials_buttons_layout.addWidget(materials_add_button)
        materials_layout.addLayout(materials_buttons_layout)
        layout.addLayout(materials_layout)

        # Výsledek
        result_layout = QtWidgets.QFormLayout()
        result_buttons_layout = QtWidgets.QHBoxLayout()
        result_button = QtWidgets.QPushButton("Vybrat Výsledek")
        result_button.clicked.connect(self.select_result)
        create_result_button = QtWidgets.QPushButton("Vytvořit Nový Item")
        create_result_button.clicked.connect(self.create_new_result_item)
        result_buttons_layout.addWidget(result_button)
        result_buttons_layout.addWidget(create_result_button)
        result_layout.addRow(result_buttons_layout)

        self.result_item_name = QtWidgets.QLabel()
        self.result_item_image = QtWidgets.QLabel()
        self.result_item_image.setFixedSize(64, 64)
        self.result_item_image.setScaledContents(True)
        self.result_count = QtWidgets.QSpinBox()
        self.result_count.setMinimum(1)
        self.result_count.setMaximum(9999)
        self.result_count.valueChanged.connect(self.update_result_count)

        result_layout.addRow("Název:", self.result_item_name)
        result_layout.addRow("Počet:", self.result_count)
        result_layout.addRow("Obrázek:", self.result_item_image)
        layout.addLayout(result_layout)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.save_recipe)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.update_defaults_based_on_type(self.type_edit.currentText())

        self.materials = []
        self.result_item = None

    def open_weapon_dialog(self):
        """Otevře RecipeWeaponDialog pro konfiguraci zbraně a komponent."""
        if not self.isweapon_edit.isChecked():
            QtWidgets.QMessageBox.information(
                self, "Zbraň není aktivní",
                "Nejdříve zaškrtněte, že se jedná o zbraň (pole 'Je zbraň'), abyste mohli nastavit zbraň."
            )
            return

        # current_weapon = result_item.item (pokud je to zbraň)
        current_weapon = None
        if self.result_item:
            current_weapon = self.result_item['item']  # např. "WEAPON_REVOLVER_CATTLEMAN"

        current_comps = self.comps_edit.text().strip() or ""

        dialog = RecipeWeaponDialog(
            self.weapons_data,
            current_weapon=current_weapon,
            current_comps=current_comps,
            parent=self
        )
        if dialog.exec_():
            weapon_name, comps_json = dialog.get_result()
            if weapon_name:
                # Nastavíme výsledek receptu = vybraná zbraň
                self.result_item = {'item': weapon_name, 'count': 1}
                item_label = self.get_item_label(weapon_name) or weapon_name
                self.result_item_name.setText(item_label + f" ({weapon_name})")
                self.result_count.setValue(1)
                pixmap = self.load_item_image(weapon_name)
                if pixmap:
                    self.result_item_image.setPixmap(pixmap)
                else:
                    self.result_item_image.setText('No Image')

                # Uložíme JSON s komponentami
                self.comps_edit.setText(comps_json)

    def weapon_state_changed(self, state):
        """Zobrazí/skryje tlačítko pro konfiguraci zbraně dle zaškrtnutí."""
        self.weapon_button.setVisible(self.isweapon_edit.isChecked())
        if not self.isweapon_edit.isChecked():
            # Pokud zbraň odškrtáváme, odstraníme jakékoliv existující comps a result_item
            self.comps_edit.clear()

    def update_defaults_based_on_type(self, type_value):
        anim_dict = self.anim_dict_options.get(type_value, '')
        anim_body_list = self.anim_body_options.get(type_value, [])
        prop = self.prop_options.get(type_value, '')

        if anim_dict:
            self.anim_dict_edit.setText(anim_dict)
        else:
            self.anim_dict_edit.clear()

        self.anim_body_model.setStringList(anim_body_list)
        if anim_body_list:
            self.anim_body_edit.setText(anim_body_list[0])
        else:
            self.anim_body_edit.setText('')

        if prop:
            self.prop_edit.setText(prop)
        else:
            self.prop_edit.setText('')

    def load_recipe(self):
        cursor = self.connection.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM recipes WHERE id = %s", (self.recipe_id,))
        recipe = cursor.fetchone()
        if recipe:
            self.name_edit.setText(recipe['name'])
            index = self.type_edit.findText(recipe['type'])
            self.type_edit.setCurrentIndex(index)
            self.trigger_item_edit.setText(recipe.get('triggerItem') or '')
            self.prop_edit.setText(recipe.get('prop') or '')
            self.timer_edit.setValue(recipe.get('timer') or 0)

            category_id = recipe.get('category_id', 0)
            idx_cat = self.category_edit.findData(category_id)
            if idx_cat >= 0:
                self.category_edit.setCurrentIndex(idx_cat)
            else:
                self.category_edit.setCurrentIndex(-1)

            self.isweapon_edit.setChecked(recipe.get('isweapon', 0) == 1)
            self.job_edit.setText(recipe.get('job') or '')
            self.grade_edit.setValue(recipe.get('grade') or 0)
            self.anim_dict_edit.setText(recipe.get('animDict') or '')
            self.anim_body_edit.setText(recipe.get('animBody') or '')
            self.comps_edit.setText(recipe.get('comps') or '')

            # Načtení skill
            skill = recipe.get('skill', 'crafting')
            cursor.execute("SELECT label FROM skills WHERE name = %s", (skill,))
            skill_result = cursor.fetchone()
            skill_label = skill_result['label'] if skill_result else skill
            index = self.skill_edit.findText(skill_label)
            if index >= 0:
                self.skill_edit.setCurrentIndex(index)
            else:
                self.skill_edit.setEditText(skill_label)

            # Načtení XP
            xp = recipe.get('XP', 1)
            self.xp_spin.setValue(xp)

            # Materiály
            materials_json = recipe.get('materials') or '{}'
            try:
                materials_data = json.loads(materials_json)
                self.materials = [{'item': key, 'count': value} for key, value in materials_data.items()]
            except json.JSONDecodeError:
                self.materials = []
            self.update_materials_list()

            # Výsledek
            result_json = recipe.get('result') or '{}'
            try:
                result_data = json.loads(result_json)
                self.result_item = {'item': result_data['item'], 'count': result_data['count']}
                item_label = self.get_item_label(self.result_item['item']) or self.result_item['item']
                self.result_item_name.setText(item_label + f" ({self.result_item['item']})")
                self.result_count.setValue(self.result_item['count'])
                pixmap = self.load_item_image(self.result_item['item'])
                if pixmap:
                    self.result_item_image.setPixmap(pixmap)
                else:
                    self.result_item_image.setText('No Image')
            except (json.JSONDecodeError, KeyError):
                self.result_item = None
                self.result_item_name.setText('')
                self.result_count.setValue(1)
                self.result_item_image.clear()

            # Pokud kopírujeme, smažeme původní ID
            if self.copy:
                self.recipe_id = None

            # Případně zobrazíme tlačítko pro nastavení zbraně
            self.weapon_button.setVisible(self.isweapon_edit.isChecked())

    def save_recipe(self):
        name = self.name_edit.text().strip()
        type_ = self.type_edit.currentText()
        trigger_item = self.trigger_item_edit.text().strip()
        prop = self.prop_edit.text().strip()
        timer = self.timer_edit.value()
        category_id = self.category_edit.currentData()
        isweapon = 1 if self.isweapon_edit.isChecked() else 0
        job = self.job_edit.text().strip()
        grade = self.grade_edit.value()
        anim_dict = self.anim_dict_edit.text().strip()
        anim_body = self.anim_body_edit.text().strip()
        comps = self.comps_edit.text().strip()

        # Získání nových hodnot
        skill_label = self.skill_edit.currentText().strip()
        skill_name = None
        if self.skill_edit.currentIndex() > 0:
            skill_name = self.skill_edit.itemData(self.skill_edit.currentIndex())
        else:
            # Pokud je zadán vlastní skill, pokusíme se ho najít podle labelu
            cursor = self.connection.cursor(dictionary=True, buffered=True)
            cursor.execute("SELECT name FROM skills WHERE label = %s", (skill_label,))
            result = cursor.fetchone()
            if result:
                skill_name = result['name']
            else:
                # Pokud skill neexistuje, zobrazíme chybu
                QtWidgets.QMessageBox.warning(self, "Chyba", "Zadaná dovednost (skill) není definována v databázi.")
                return

        xp = self.xp_spin.value()

        if not name or not skill_name:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Název a Dovednost (skill) nesmí být prázdné.")
            return

        # Uložíme materiály
        materials_dict = {}
        for material in self.materials:
            materials_dict[material['item']] = materials_dict.get(material['item'], 0) + material['count']
        materials_json = json.dumps(materials_dict)

        # Uložíme výsledek
        if self.result_item:
            result_json = json.dumps({'item': self.result_item['item'], 'count': self.result_item['count']})
        else:
            result_json = '{}'

        cursor = self.connection.cursor()
        if self.recipe_id:
            query = """
                UPDATE recipes SET
                name=%s, type=%s, triggerItem=%s, prop=%s, timer=%s, category_id=%s,
                isweapon=%s, job=%s, grade=%s, animDict=%s, animBody=%s, comps=%s,
                materials=%s, result=%s, skill=%s, XP=%s, updated_at=NOW()
                WHERE id=%s
            """
            params = (name, type_, trigger_item, prop, timer, category_id, isweapon,
                      job, grade, anim_dict, anim_body, comps, materials_json, result_json,
                      skill_name, xp, self.recipe_id)
        else:
            query = """
                INSERT INTO recipes (name, type, triggerItem, prop, timer, category_id,
                isweapon, job, grade, animDict, animBody, comps, materials, result, skill, XP, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            params = (name, type_, trigger_item, prop, timer, category_id, isweapon,
                      job, grade, anim_dict, anim_body, comps, materials_json, result_json,
                      skill_name, xp)
        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except Exception as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")

    def add_material(self):
        dialog = ItemSelectionDialog(self.connection)
        if dialog.exec_():
            materials = dialog.selected_items
            for item in materials:
                count = item.get('count', 1)
                self.materials.append({'item': item['item'], 'count': count})
            self.update_materials_list()

    def edit_material(self, list_item):
        item_name = list_item.data(QtCore.Qt.UserRole)
        for material in self.materials:
            if material['item'] == item_name:
                break
        else:
            return
        new_count, ok = QtWidgets.QInputDialog.getInt(
            self,
            "Upravit počet",
            f"Zadejte nový počet pro {self.get_item_label(item_name) or item_name}:",
            material['count'],
            1
        )
        if ok:
            material['count'] = new_count
            self.update_materials_list()

    def update_materials_list(self):
        self.materials_list.clear()
        for material in self.materials:
            item_label = self.get_item_label(material['item']) or material['item']
            pixmap = self.load_item_image(material['item'])
            icon = QtGui.QIcon(pixmap) if pixmap else QtGui.QIcon()
            list_item = QtWidgets.QListWidgetItem(icon, f"{item_label}\nPočet: {material['count']}")
            list_item.setData(QtCore.Qt.UserRole, material['item'])
            list_item.setSizeHint(QtCore.QSize(80, 100))
            self.materials_list.addItem(list_item)

    def show_materials_context_menu(self, position):
        menu = QtWidgets.QMenu()
        edit_action = menu.addAction("Změnit množství")
        remove_action = menu.addAction("Odebrat")
        action = menu.exec_(self.materials_list.viewport().mapToGlobal(position))
        selected_items = self.materials_list.selectedItems()
        if not selected_items:
            return
        list_item = selected_items[0]
        item_name = list_item.data(QtCore.Qt.UserRole)

        if action == remove_action:
            self.materials = [m for m in self.materials if m['item'] != item_name]
            self.update_materials_list()
        elif action == edit_action:
            self.edit_material(list_item)

    def load_item_image(self, item_name):
        cache_file_path = os.path.join(self.cache_dir, f"{item_name}.png")
        if os.path.exists(cache_file_path):
            pixmap = QtGui.QPixmap(cache_file_path)
        else:
            cursor = self.connection.cursor(dictionary=True, buffered=True)
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
                print(f"No image found for item {item_name}")
                pixmap = None
        return pixmap

    def get_item_label(self, item_name):
        cursor = self.connection.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT label FROM items WHERE item = %s", (item_name,))
        result = cursor.fetchone()
        if result and result.get('label'):
            return result['label']
        else:
            return None

    def select_result(self):
        dialog = ItemSelectionDialog(self.connection, single_selection=True)
        if dialog.exec_():
            selected = dialog.selected_items
            if selected:
                chosen = selected[0]
                self.result_item = {'item': chosen['item'], 'count': 1}
                item_label = self.get_item_label(chosen['item']) or chosen['item']
                self.result_item_name.setText(item_label + f" ({chosen['item']})")
                self.result_count.setValue(1)
                pixmap = self.load_item_image(chosen['item'])
                if pixmap:
                    self.result_item_image.setPixmap(pixmap)
                else:
                    self.result_item_image.setText('No Image')

    def create_new_result_item(self):
        dialog = NewItemDialog(self.connection)
        if dialog.exec_():
            item_data = dialog.get_item_data()
            item_name = item_data['item']
            label = item_data['label']
            weight = item_data['weight']
            limit_ = item_data['limit']

            if not item_name or not label:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Spawn Name a Název nesmí být prázdné.")
                return

            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM items WHERE item = %s", (item_name,))
            exists = cursor.fetchone()
            if exists and exists[0] > 0:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Item s tímto Spawn Name již existuje.")
                return

            try:
                insert_query = """
                    INSERT INTO items (item, label, weight, `limit`, usable)
                    VALUES (%s, %s, %s, %s, 1)
                """
                cursor.execute(insert_query, (item_name, label, weight, limit_))
                self.connection.commit()
                QtWidgets.QMessageBox.information(self, "Úspěch", f"Nový item '{label}' byl vytvořen.")
                # Nastavíme ho jako výsledek
                self.result_item = {'item': item_name, 'count': 1}
                self.result_item_name.setText(label + f" ({item_name})")
                self.result_count.setValue(1)
                pixmap = self.load_item_image(item_name)
                if pixmap:
                    self.result_item_image.setPixmap(pixmap)
                else:
                    self.result_item_image.setText('No Image')
            except mysql.connector.Error as err:
                QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při vytváření itemu: {err}")

    def update_result_count(self, value):
        if self.result_item:
            self.result_item['count'] = value

# Metoda byla přesunuta níže, abychom zajistili, že všechny potřebné části jsou definovány
    def load_recipe(self):
        cursor = self.connection.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM recipes WHERE id = %s", (self.recipe_id,))
        recipe = cursor.fetchone()
        if recipe:
            self.name_edit.setText(recipe['name'])
            index = self.type_edit.findText(recipe['type'])
            self.type_edit.setCurrentIndex(index)
            self.trigger_item_edit.setText(recipe.get('triggerItem') or '')
            self.prop_edit.setText(recipe.get('prop') or '')
            self.timer_edit.setValue(recipe.get('timer') or 0)

            category_id = recipe.get('category_id', 0)
            idx_cat = self.category_edit.findData(category_id)
            if idx_cat >= 0:
                self.category_edit.setCurrentIndex(idx_cat)
            else:
                self.category_edit.setCurrentIndex(-1)

            self.isweapon_edit.setChecked(recipe.get('isweapon', 0) == 1)
            self.job_edit.setText(recipe.get('job') or '')
            self.grade_edit.setValue(recipe.get('grade') or 0)
            self.anim_dict_edit.setText(recipe.get('animDict') or '')
            self.anim_body_edit.setText(recipe.get('animBody') or '')
            self.comps_edit.setText(recipe.get('comps') or '')

            # Načtení skill
            skill = recipe.get('skill', 'crafting')
            cursor.execute("SELECT label FROM skills WHERE name = %s", (skill,))
            skill_result = cursor.fetchone()
            skill_label = skill_result['label'] if skill_result else skill
            index = self.skill_edit.findText(skill_label)
            if index >= 0:
                self.skill_edit.setCurrentIndex(index)
            else:
                self.skill_edit.setEditText(skill_label)

            # Načtení XP
            xp = recipe.get('XP', 1)
            self.xp_spin.setValue(xp)

            # Materiály
            materials_json = recipe.get('materials') or '{}'
            try:
                materials_data = json.loads(materials_json)
                self.materials = [{'item': key, 'count': value} for key, value in materials_data.items()]
            except json.JSONDecodeError:
                self.materials = []
            self.update_materials_list()

            # Výsledek
            result_json = recipe.get('result') or '{}'
            try:
                result_data = json.loads(result_json)
                self.result_item = {'item': result_data['item'], 'count': result_data['count']}
                item_label = self.get_item_label(self.result_item['item']) or self.result_item['item']
                self.result_item_name.setText(item_label + f" ({self.result_item['item']})")
                self.result_count.setValue(self.result_item['count'])
                pixmap = self.load_item_image(self.result_item['item'])
                if pixmap:
                    self.result_item_image.setPixmap(pixmap)
                else:
                    self.result_item_image.setText('No Image')
            except (json.JSONDecodeError, KeyError):
                self.result_item = None
                self.result_item_name.setText('')
                self.result_count.setValue(1)
                self.result_item_image.clear()

            # Pokud kopírujeme, smažeme původní ID
            if self.copy:
                self.recipe_id = None

            # Případně zobrazíme tlačítko pro nastavení zbraně
            self.weapon_button.setVisible(self.isweapon_edit.isChecked())

    def save_recipe(self):
        name = self.name_edit.text().strip()
        type_ = self.type_edit.currentText()
        trigger_item = self.trigger_item_edit.text().strip()
        prop = self.prop_edit.text().strip()
        timer = self.timer_edit.value()
        category_id = self.category_edit.currentData()
        isweapon = 1 if self.isweapon_edit.isChecked() else 0
        job = self.job_edit.text().strip()
        grade = self.grade_edit.value()
        anim_dict = self.anim_dict_edit.text().strip()
        anim_body = self.anim_body_edit.text().strip()
        comps = self.comps_edit.text().strip()

        # Získání nových hodnot
        skill_label = self.skill_edit.currentText().strip()
        skill_name = None
        if self.skill_edit.currentIndex() > 0:
            skill_name = self.skill_edit.itemData(self.skill_edit.currentIndex())
        else:
            # Pokud je zadán vlastní skill, pokusíme se ho najít podle labelu
            cursor = self.connection.cursor(dictionary=True, buffered=True)
            cursor.execute("SELECT name FROM skills WHERE label = %s", (skill_label,))
            result = cursor.fetchone()
            if result:
                skill_name = result['name']
            else:
                # Pokud skill neexistuje, zobrazíme chybu
                QtWidgets.QMessageBox.warning(self, "Chyba", "Zadaná dovednost (skill) není definována v databázi.")
                return

        xp = self.xp_spin.value()

        if not name or not skill_name:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Název a Dovednost (skill) nesmí být prázdné.")
            return

        # Uložíme materiály
        materials_dict = {}
        for material in self.materials:
            materials_dict[material['item']] = materials_dict.get(material['item'], 0) + material['count']
        materials_json = json.dumps(materials_dict)

        # Uložíme výsledek
        if self.result_item:
            result_json = json.dumps({'item': self.result_item['item'], 'count': self.result_item['count']})
        else:
            result_json = '{}'

        cursor = self.connection.cursor()
        if self.recipe_id:
            query = """
                UPDATE recipes SET
                name=%s, type=%s, triggerItem=%s, prop=%s, timer=%s, category_id=%s,
                isweapon=%s, job=%s, grade=%s, animDict=%s, animBody=%s, comps=%s,
                materials=%s, result=%s, skill=%s, XP=%s, updated_at=NOW()
                WHERE id=%s
            """
            params = (name, type_, trigger_item, prop, timer, category_id, isweapon,
                      job, grade, anim_dict, anim_body, comps, materials_json, result_json,
                      skill_name, xp, self.recipe_id)
        else:
            query = """
                INSERT INTO recipes (name, type, triggerItem, prop, timer, category_id,
                isweapon, job, grade, animDict, animBody, comps, materials, result, skill, XP, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            params = (name, type_, trigger_item, prop, timer, category_id, isweapon,
                      job, grade, anim_dict, anim_body, comps, materials_json, result_json,
                      skill_name, xp)
        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except Exception as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")

    def add_material(self):
        dialog = ItemSelectionDialog(self.connection)
        if dialog.exec_():
            materials = dialog.selected_items
            for item in materials:
                count = item.get('count', 1)
                self.materials.append({'item': item['item'], 'count': count})
            self.update_materials_list()

    def edit_material(self, list_item):
        item_name = list_item.data(QtCore.Qt.UserRole)
        for material in self.materials:
            if material['item'] == item_name:
                break
        else:
            return
        new_count, ok = QtWidgets.QInputDialog.getInt(
            self,
            "Upravit počet",
            f"Zadejte nový počet pro {self.get_item_label(item_name) or item_name}:",
            material['count'],
            1
        )
        if ok:
            material['count'] = new_count
            self.update_materials_list()

    def update_materials_list(self):
        self.materials_list.clear()
        for material in self.materials:
            # print(material['item'])
            item_label = self.get_item_label(material['item']) or material['item']
            pixmap = self.load_item_image(material['item'])
            icon = QtGui.QIcon(pixmap) if pixmap else QtGui.QIcon()
            list_item = QtWidgets.QListWidgetItem(icon, f"{item_label}\nPočet: {material['count']}")
            list_item.setData(QtCore.Qt.UserRole, material['item'])
            list_item.setSizeHint(QtCore.QSize(80, 100))
            self.materials_list.addItem(list_item)

    def show_materials_context_menu(self, position):
        menu = QtWidgets.QMenu()
        edit_action = menu.addAction("Změnit množství")
        remove_action = menu.addAction("Odebrat")
        action = menu.exec_(self.materials_list.viewport().mapToGlobal(position))
        selected_items = self.materials_list.selectedItems()
        if not selected_items:
            return
        list_item = selected_items[0]
        item_name = list_item.data(QtCore.Qt.UserRole)

        if action == remove_action:
            self.materials = [m for m in self.materials if m['item'] != item_name]
            self.update_materials_list()
        elif action == edit_action:
            self.edit_material(list_item)

    def load_item_image(self, item_name):
        cache_file_path = os.path.join(self.cache_dir, f"{item_name}.png")
        if os.path.exists(cache_file_path):
            pixmap = QtGui.QPixmap(cache_file_path)
        else:
            cursor = self.connection.cursor(dictionary=True, buffered=True)
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
                print(f"No image found for item {item_name}")
                pixmap = None
        return pixmap

    def get_item_label(self, item_name):
        cursor = self.connection.cursor(dictionary=True, buffered=True)
        print(item_name)
        cursor.execute("SELECT label FROM items WHERE item = %s", (item_name,))
        result = cursor.fetchone()
        if result and result.get('label'):
            return result['label']
        else:
            return None
        # return item_name

    def select_result(self):
        dialog = ItemSelectionDialog(self.connection, single_selection=True)
        if dialog.exec_():
            selected = dialog.selected_items
            if selected:
                chosen = selected[0]
                self.result_item = {'item': chosen['item'], 'count': 1}
                item_label = self.get_item_label(chosen['item']) or chosen['item']
                self.result_item_name.setText(item_label + f" ({chosen['item']})")
                self.result_count.setValue(1)
                pixmap = self.load_item_image(chosen['item'])
                if pixmap:
                    self.result_item_image.setPixmap(pixmap)
                else:
                    self.result_item_image.setText('No Image')

    def create_new_result_item(self):
        dialog = NewItemDialog(self.connection)
        if dialog.exec_():
            item_data = dialog.get_item_data()
            item_name = item_data['item']
            label = item_data['label']
            weight = item_data['weight']
            limit_ = item_data['limit']

            if not item_name or not label:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Spawn Name a Název nesmí být prázdné.")
                return

            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM items WHERE item = %s", (item_name,))
            exists = cursor.fetchone()
            if exists and exists[0] > 0:
                QtWidgets.QMessageBox.warning(self, "Chyba", "Item s tímto Spawn Name již existuje.")
                return

            try:
                insert_query = """
                    INSERT INTO items (item, label, weight, `limit`, usable)
                    VALUES (%s, %s, %s, %s, 1)
                """
                cursor.execute(insert_query, (item_name, label, weight, limit_))
                self.connection.commit()
                QtWidgets.QMessageBox.information(self, "Úspěch", f"Nový item '{label}' byl vytvořen.")
                # Nastavíme ho jako výsledek
                self.result_item = {'item': item_name, 'count': 1}
                self.result_item_name.setText(label + f" ({item_name})")
                self.result_count.setValue(1)
                pixmap = self.load_item_image(item_name)
                if pixmap:
                    self.result_item_image.setPixmap(pixmap)
                else:
                    self.result_item_image.setText('No Image')
            except mysql.connector.Error as err:
                QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při vytváření itemu: {err}")

    def update_result_count(self, value):
        if self.result_item:
            self.result_item['count'] = value

