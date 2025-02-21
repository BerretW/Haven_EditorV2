import sys
import json
import os
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from item_manager import ItemSelectionDialog, ItemDialog  # Importujeme ItemDialog


class ConsumableDialog(QtWidgets.QDialog):
    def __init__(self, connection, consumable_id=None, item_code=None):
        super().__init__()
        self.connection = connection
        self.consumable_id = consumable_id
        self.item_code = item_code
        self.setWindowTitle("Konzumovatelná Položka")
        self.setGeometry(100, 100, 500, 700)  # Zvýšili jsme velikost okna
        self.load_stylesheet(os.path.join(BASE_DIR, "stylesheet1.qss"))
        self.init_ui()
        if self.consumable_id:
            self.load_consumable()
        elif self.item_code:
            self.item_edit.setText(self.item_code)

    def load_stylesheet(self, filepath):
        """Načte stylesheet z externího souboru."""
        try:
            with open(filepath, "r") as file:
                self.setStyleSheet(file.read())
        except Exception as e:
            print(f"Chyba při načítání stylů: {e}")

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()

        # --- Výběr / vytvoření Itemu ---
        self.item_edit = QtWidgets.QLineEdit()
        self.item_edit.setReadOnly(True)

        self.select_item_button = QtWidgets.QPushButton("Vybrat Item")
        self.create_item_button = QtWidgets.QPushButton("Vytvořit Nový Item")

        # Propojení tlačítek s metodami
        self.select_item_button.clicked.connect(self.select_item)
        self.create_item_button.clicked.connect(self.create_new_item)

        item_layout = QtWidgets.QHBoxLayout()
        item_layout.addWidget(self.item_edit)
        item_layout.addWidget(self.select_item_button)
        item_layout.addWidget(self.create_item_button)

        # --- Další pole ---
        self.type_edit = QtWidgets.QComboBox()
        self.type_edit.addItems([
            'snack', 'plate', 'syringe', 'bottle', 'glass', 'shot',
            'cigar', 'cigarette', 'pipe', 'opiumPipe', 'longPipe', 'bandage'
        ])
        self.prop_edit = QtWidgets.QLineEdit()
        self.dsc_edit = QtWidgets.QTextEdit()

        # SpinBoxy pro různé atributy
        attributes = [
            ("Jídlo:", "food_edit", -1000, 1000),
            ("Voda:", "water_edit", -1000, 1000),
            ("Toxin:", "toxin_edit", -100, 100),
            ("Obrana:", "defense_edit", 0, 1000),
            ("Závislost:", "addiction_edit", -100, 100),
            ("Alkohol:", "alcohol_edit", -100, 100),
            ("Vnitřní Zdraví:", "innerHealth_edit", -100, 100),
            ("Vnější Zdraví:", "outerHealth_edit", -600, 600),
            ("Vnitřní Stamina:", "innerStamina_edit", -100, 100),
            ("Vnější Stamina:", "outerStamina_edit", -135, 135),
            ("Effect ID:", "effect_id_edit", 0, 10000000),
            ("Délka efektu:", "effect_duration_edit", 0, 10000000),
            ("Kapacita:", "capacity_edit", 0, 10),
        ]

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Item:", item_layout)
        form_layout.addRow("Typ:", self.type_edit)
        form_layout.addRow("Prop:", self.prop_edit)
        form_layout.addRow("Popis:", self.dsc_edit)

        # Dynamicky přidáváme SpinBoxy do formuláře
        for label, attr_name, min_val, max_val in attributes:
            spinbox = QtWidgets.QSpinBox()
            spinbox.setRange(min_val, max_val)
            setattr(self, attr_name, spinbox)
            form_layout.addRow(label, spinbox)

        self.return_item_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Vrácený Item:", self.return_item_edit)

        layout.addLayout(form_layout)

        # Checkbox pro vytvoření itemu
        self.create_item_checkbox = QtWidgets.QCheckBox("Vytvořit Item")
        layout.addWidget(self.create_item_checkbox)

        # Dialogové tlačítka
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self
        )
        layout.addWidget(buttons)
        buttons.accepted.connect(self.save_consumable)
        buttons.rejected.connect(self.reject)

        self.setLayout(layout)

    # ----------------------------------------------------------------
    #                  Výběr / vytvoření itemu
    # ----------------------------------------------------------------
    def select_item(self):
        dialog = ItemSelectionDialog(self.connection, single_selection=True)
        if dialog.exec_():
            selected_items = dialog.selected_items
            if selected_items:
                self.item_edit.setText(selected_items[0]['item'])

    def create_new_item(self):
        # Otevřeme dialog pro vytvoření nového itemu
        dialog = ItemDialog(self.connection)
        if dialog.exec_():
            new_item_code = dialog.item_name_edit.text()
            self.item_edit.setText(new_item_code)

    # ----------------------------------------------------------------
    #                  Načtení stávajícího záznamu
    # ----------------------------------------------------------------
    def load_consumable(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM aprts_consumable WHERE id = %s", (self.consumable_id,))
        consumable = cursor.fetchone()
        if consumable:
            self.item_edit.setText(consumable['item'])

            idx_type = self.type_edit.findText(consumable['type'])
            if idx_type >= 0:
                self.type_edit.setCurrentIndex(idx_type)

            self.prop_edit.setText(consumable['prop'] or '')
            self.dsc_edit.setPlainText(consumable['dsc'] or '')

            self.food_edit.setValue(consumable['food'])
            self.water_edit.setValue(consumable['water'])
            self.toxin_edit.setValue(consumable['toxin'])
            self.defense_edit.setValue(consumable['defense'])
            self.addiction_edit.setValue(consumable['addiction'])
            self.alcohol_edit.setValue(consumable['alcohol'])

            # Načtení nových atributů
            self.innerHealth_edit.setValue(consumable.get('innerHealth', 0))
            self.outerHealth_edit.setValue(consumable.get('outerHealth', 0))
            self.innerStamina_edit.setValue(consumable.get('innerStamina', 0))
            self.outerStamina_edit.setValue(consumable.get('outerStamina', 0))

            self.effect_id_edit.setValue(consumable['effect_id'])
            self.effect_duration_edit.setValue(consumable['effect_duration'])
            self.return_item_edit.setText(consumable['return_item'] or '')
            self.capacity_edit.setValue(consumable['capacity'])

    # ----------------------------------------------------------------
    #                  Uložení záznamu
    # ----------------------------------------------------------------
    def save_consumable(self):
        # Získání hodnot z polí
        item = self.item_edit.text().strip()
        type_ = self.type_edit.currentText()
        prop = self.prop_edit.text()
        dsc = self.dsc_edit.toPlainText()

        food = self.food_edit.value()
        water = self.water_edit.value()
        toxin = self.toxin_edit.value()
        defense = self.defense_edit.value()
        addiction = self.addiction_edit.value()
        alcohol = self.alcohol_edit.value()

        # Nové atributy
        innerHealth = self.innerHealth_edit.value()
        outerHealth = self.outerHealth_edit.value()
        innerStamina = self.innerStamina_edit.value()
        outerStamina = self.outerStamina_edit.value()

        effect_id = self.effect_id_edit.value()
        effect_duration = self.effect_duration_edit.value()
        return_item = self.return_item_edit.text()
        capacity = self.capacity_edit.value()

        # Kontrola povinných polí
        if not item:
            QtWidgets.QMessageBox.warning(
                self, "Chyba", "Pole 'Item' nesmí být prázdné.")
            return

        cursor = self.connection.cursor()
        try:
            if self.consumable_id:
                # UPDATE existujícího záznamu
                query = """
                    UPDATE aprts_consumable SET
                      item=%s, type=%s, prop=%s, dsc=%s,
                      food=%s, water=%s, toxin=%s, defense=%s,
                      addiction=%s, alcohol=%s,
                      innerHealth=%s, outerHealth=%s, innerStamina=%s, outerStamina=%s,
                      effect_id=%s, effect_duration=%s, return_item=%s, capacity=%s
                    WHERE id=%s
                """
                params = (
                    item, type_, prop, dsc,
                    food, water, toxin, defense,
                    addiction, alcohol,
                    innerHealth, outerHealth, innerStamina, outerStamina,
                    effect_id, effect_duration, return_item, capacity,
                    self.consumable_id
                )
                cursor.execute(query, params)
            else:
                # INSERT nového záznamu
                query = """
                    INSERT INTO aprts_consumable
                    ( item, type, prop, dsc,
                      food, water, toxin, defense,
                      addiction, alcohol,
                      innerHealth, outerHealth, innerStamina, outerStamina,
                      effect_id, effect_duration, return_item, capacity
                    )
                    VALUES
                    (%s, %s, %s, %s,
                     %s, %s, %s, %s,
                     %s, %s,
                     %s, %s, %s, %s,
                     %s, %s, %s, %s
                    )
                """
                params = (
                    item, type_, prop, dsc,
                    food, water, toxin, defense,
                    addiction, alcohol,
                    innerHealth, outerHealth, innerStamina, outerStamina,
                    effect_id, effect_duration, return_item, capacity
                )
                cursor.execute(query, params)

            self.connection.commit()

            # Pokud je zaškrtnuto "Vytvořit Item", pokusíme se item vytvořit
            if self.create_item_checkbox.isChecked():
                self.create_item()

            self.accept()

        except Exception as err:
            QtWidgets.QMessageBox.critical(
                self, "Chyba", f"Nastala chyba při ukládání: {err}")

    def create_item(self):
        item_name = self.item_edit.text().strip()
        if not item_name:
            QtWidgets.QMessageBox.warning(
                self, "Chyba", "Pole 'Item' nesmí být prázdné.")
            return

        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM items WHERE item = %s", (item_name,))
        existing_item = cursor.fetchone()
        if existing_item:
            QtWidgets.QMessageBox.warning(self, "Chyba", f"Item '{item_name}' již existuje.")
            return

        # Vygenerování metadata
        capacity = self.capacity_edit.value()
        metadata = {
            "max": capacity,
            "capacity": capacity,
            "description": f"Zbývá {capacity}"
        }
        metadata_json = json.dumps(metadata, ensure_ascii=False)

        # Vložení nového itemu do tabulky items
        label = item_name
        weight = 0.1
        limit = 10
        usable = 1

        insert_query = """
            INSERT INTO items (item, label, weight, `limit`, usable, metadata, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (item_name, label, weight, limit,
                  usable, metadata_json, "item_food")

        try:
            cursor.execute(insert_query, params)
            self.connection.commit()
            QtWidgets.QMessageBox.information(
                self, "Úspěch", f"Item '{item_name}' byl vytvořen.")
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(
                self, "Chyba", f"Nastala chyba při vytváření itemu: {err}")
