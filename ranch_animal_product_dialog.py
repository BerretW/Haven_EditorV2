import sys
import json
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os

# Předpokládáme, že ItemSelectionDialog existuje v item_manager.py
from item_manager import ItemSelectionDialog

class RanchAnimalProductDialog(QtWidgets.QDialog):
    def __init__(self, connection, animal_id, product_id=None):
        super().__init__()
        self.connection = connection
        self.animal_id = animal_id
        self.product_id = product_id

        self.setWindowTitle("Produkt Ranč. Zvířete")
        self.setGeometry(100, 100, 650, 550)

        self.init_ui()
        if self.product_id:
            self.load_product()
        # Když jsme nově otevřeli dialog (bez product_id), chceme rovnou aktualizovat stavy
        self.update_fields_for_gather()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_layout = QtWidgets.QFormLayout()

        # Název
        self.name_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Název (name):", self.name_edit)

        # ITEM (výsledný produkt)
        self.item_edit = QtWidgets.QLineEdit()
        item_button = QtWidgets.QPushButton("Vybrat Item")
        item_button.clicked.connect(self.select_item_for_product)

        item_layout = QtWidgets.QHBoxLayout()
        item_layout.addWidget(self.item_edit)
        item_layout.addWidget(item_button)

        form_layout.addRow("Item (item):", item_layout)

        # PROP
        self.prop_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Prop (prop):", self.prop_edit)

        # gather = 1 (kill), 2 (gather), 3 (pickup)
        self.gather_combo = QtWidgets.QComboBox()
        self.gather_combo.addItem("kill", 1)
        self.gather_combo.addItem("gather", 2)
        self.gather_combo.addItem("pickup", 3)
        self.gather_combo.currentIndexChanged.connect(self.update_fields_for_gather)
        form_layout.addRow("Způsob (gather):", self.gather_combo)

        # amount
        self.amount_edit = QtWidgets.QSpinBox()
        self.amount_edit.setRange(0, 99999)
        form_layout.addRow("amount:", self.amount_edit)

        # maxAmount
        self.maxAmount_edit = QtWidgets.QSpinBox()
        self.maxAmount_edit.setRange(0, 99999)
        self.maxAmount_edit.setValue(0)  # 0 => None
        form_layout.addRow("maxAmount:", self.maxAmount_edit)

        # lifetime
        self.lifetime_edit = QtWidgets.QSpinBox()
        self.lifetime_edit.setRange(0, 999999)
        form_layout.addRow("lifetime:", self.lifetime_edit)

        # TOOL
        self.tool_edit = QtWidgets.QLineEdit()
        tool_button = QtWidgets.QPushButton("Vybrat Tool")
        tool_button.clicked.connect(self.select_item_for_tool)

        tool_layout = QtWidgets.QHBoxLayout()
        tool_layout.addWidget(self.tool_edit)
        tool_layout.addWidget(tool_button)

        form_layout.addRow("tool:", tool_layout)

        layout.addLayout(form_layout)

        # Anim group: dict, name, time, flag, type, prop (JSON)
        self.anim_group = QtWidgets.QGroupBox("Anim (JSON)")
        anim_layout = QtWidgets.QFormLayout(self.anim_group)

        self.anim_dict_edit = QtWidgets.QLineEdit()
        self.anim_name_edit = QtWidgets.QLineEdit()

        self.anim_time_edit = QtWidgets.QSpinBox()
        self.anim_time_edit.setRange(0, 9999999)

        self.anim_flag_edit = QtWidgets.QSpinBox()
        self.anim_flag_edit.setRange(0, 9999)

        self.anim_type_edit = QtWidgets.QLineEdit()
        self.anim_prop_edit = QtWidgets.QLineEdit()

        anim_layout.addRow("dict:", self.anim_dict_edit)
        anim_layout.addRow("name:", self.anim_name_edit)
        anim_layout.addRow("time:", self.anim_time_edit)
        anim_layout.addRow("flag:", self.anim_flag_edit)
        anim_layout.addRow("type:", self.anim_type_edit)
        anim_layout.addRow("prop:", self.anim_prop_edit)

        layout.addWidget(self.anim_group)

        # chance
        bottom_form_layout = QtWidgets.QFormLayout()

        self.chance_edit = QtWidgets.QSpinBox()
        self.chance_edit.setRange(0, 100)
        self.chance_edit.setValue(100)
        bottom_form_layout.addRow("chance (%):", self.chance_edit)

        # gender => none => NULL, male => "male", female => "female"
        self.gender_combo = QtWidgets.QComboBox()
        self.gender_combo.addItem("none", None)
        self.gender_combo.addItem("male", "male")
        self.gender_combo.addItem("female", "female")
        bottom_form_layout.addRow("gender:", self.gender_combo)

        layout.addLayout(bottom_form_layout)

        # Dialogová tlačítka
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self
        )
        buttons.accepted.connect(self.save_product)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def update_fields_for_gather(self):
        """
        Pokud gather=1 (kill), tak se tool/anim/chance zakážou (setEnabled(False)).
        Jinak se povolí.
        """
        gather_val = self.gather_combo.currentData()  # 1=kill,2=gather,3=pickup
        is_kill = (gather_val == 1)

        # Zakážeme / povolíme tool a tlačítko pro tool
        self.tool_edit.setEnabled(not is_kill)
        # Nevíme, jestli je layout? Můžeme si uložit button do proměnné,
        # nebo zavoláme child. Tady to jen nastíníme:
        # Najdeme to tlačítko, co je v layoutu.
        # (Jednodušší je uložit ho do self tool_button, ale pro ukázku takto:)
        for w in self.tool_edit.parentWidget().findChildren(QtWidgets.QPushButton):
            if w.text() == "Vybrat Tool":
                w.setEnabled(not is_kill)

        # anim group
        self.anim_group.setEnabled(not is_kill)

        # chance
        self.chance_edit.setEnabled(not is_kill)

    # ---------------------------------------------------------------------
    #  Vybrat item z DB (funkce pro "item" pole)
    # ---------------------------------------------------------------------
    def select_item_for_product(self):
        dlg = ItemSelectionDialog(self.connection, single_selection=True)
        if dlg.exec_():
            selected = dlg.selected_items
            if selected:
                self.item_edit.setText(selected[0]['item'])

    # ---------------------------------------------------------------------
    #  Vybrat item z DB (funkce pro "tool" pole)
    # ---------------------------------------------------------------------
    def select_item_for_tool(self):
        dlg = ItemSelectionDialog(self.connection, single_selection=True)
        if dlg.exec_():
            selected = dlg.selected_items
            if selected:
                self.tool_edit.setText(selected[0]['item'])

    # ---------------------------------------------------------------------
    #  Load
    # ---------------------------------------------------------------------
    def load_product(self):
        """Načtení existujícího produktu z DB a vyplnění do formuláře."""
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM aprts_ranch_config_animal_products WHERE product_id=%s", (self.product_id,))
        product = cursor.fetchone()
        if not product:
            return

        self.name_edit.setText(product['name'])
        self.item_edit.setText(product['item'])
        self.prop_edit.setText(product['prop'] or '')

        gather_val = product['gather']
        idx = self.gather_combo.findData(gather_val)
        if idx >= 0:
            self.gather_combo.setCurrentIndex(idx)

        self.amount_edit.setValue(product['amount'])
        if product['maxAmount'] is not None:
            self.maxAmount_edit.setValue(product['maxAmount'])
        else:
            self.maxAmount_edit.setValue(0)  # 0 => None

        self.lifetime_edit.setValue(product['lifetime'])
        self.tool_edit.setText(product['tool'] or '')

        # anim
        anim_text = product['anim'] or ''
        if isinstance(anim_text, bytes):
            anim_text = anim_text.decode('utf-8', 'replace')

        if anim_text:
            try:
                anim_data = json.loads(anim_text)
                self.anim_dict_edit.setText(anim_data.get("dict", ""))
                self.anim_name_edit.setText(anim_data.get("name", ""))
                self.anim_time_edit.setValue(anim_data.get("time", 0))
                self.anim_flag_edit.setValue(anim_data.get("flag", 0))
                self.anim_type_edit.setText(anim_data.get("type", ""))
                self.anim_prop_edit.setText(anim_data.get("prop", "") or "")
            except json.JSONDecodeError:
                pass

        self.chance_edit.setValue(product['chance'])

        # gender
        g_val = product['gender']
        if g_val is None:
            self.gender_combo.setCurrentIndex(0)  # none
        elif g_val == "male":
            self.gender_combo.setCurrentIndex(1)
        elif g_val == "female":
            self.gender_combo.setCurrentIndex(2)

        # Pro jistotu nastavíme stavy
        self.update_fields_for_gather()

    # ---------------------------------------------------------------------
    #  Save
    # ---------------------------------------------------------------------
    def save_product(self):
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Název nesmí být prázdný.")
            return

        item_name = self.item_edit.text().strip()
        prop_name = self.prop_edit.text().strip() or None

        gather_val = self.gather_combo.currentData()  # 1=kill,2=gather,3=pickup
        amount = self.amount_edit.value()
        maxAmount = self.maxAmount_edit.value() or None
        lifetime = self.lifetime_edit.value()

        tool_val = self.tool_edit.text().strip() or None

        # Pokud je gather=kill, můžeme klidně tool= None, anim= None, chance=0
        # Anebo to necháme tak, jak to je, a jen je disabled. Záleží na tobě.
        # Pro demonstraci tu nic nebudeme mazat, necháme to tak.

        chance = self.chance_edit.value()
        gender_val = self.gender_combo.currentData()  # None, 'male', 'female'

        # anim => složit do JSON
        anim_data = {
            "dict": self.anim_dict_edit.text().strip(),
            "name": self.anim_name_edit.text().strip(),
            "time": self.anim_time_edit.value(),
            "flag": self.anim_flag_edit.value(),
            "type": self.anim_type_edit.text().strip(),
            "prop": self.anim_prop_edit.text().strip() or None
        }
        anim_text = json.dumps(anim_data, ensure_ascii=False)

        cursor = self.connection.cursor()
        if self.product_id:
            query = """
                UPDATE aprts_ranch_config_animal_products
                SET name=%s, item=%s, prop=%s, gather=%s,
                    amount=%s, maxAmount=%s, lifetime=%s, tool=%s,
                    anim=%s, chance=%s, gender=%s
                WHERE product_id=%s
            """
            params = (
                name, item_name, prop_name, gather_val,
                amount, maxAmount, lifetime, tool_val,
                anim_text, chance, gender_val,
                self.product_id
            )
        else:
            query = """
                INSERT INTO aprts_ranch_config_animal_products
                (animal_id, name, item, prop, gather,
                 amount, maxAmount, lifetime, tool,
                 anim, chance, gender)
                VALUES
                (%s, %s, %s, %s, %s,
                 %s, %s, %s, %s,
                 %s, %s, %s)
            """
            params = (
                self.animal_id, name, item_name, prop_name, gather_val,
                amount, maxAmount, lifetime, tool_val,
                anim_text, chance, gender_val
            )

        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(
                self, "Chyba", f"Nastala chyba při ukládání produktu: {err}"
            )
