# plant_dialog.py

import json
from PyQt5 import QtWidgets, QtCore
import mysql.connector
from plants_dialogs import LandTypesDialog  # <-- dialog pro úpravu landTypes
from plants_dialogs import RewardItemEditor  # <-- funkce pro dekódování bytes
from item_manager import ItemSelectionDialog  # <-- dialog pro výběr itemu (předpokládáme existenci)
# Pokud je decode_if_bytes potřeba i jinde, můžete si ho importovat z utility, ale tady je inline:
def decode_if_bytes(value):
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return value





class PlantDialog(QtWidgets.QDialog):
    """Dialog pro úpravu/ přidání záznamu v aprts_farming_plant_types."""
    def __init__(self, connection, plant_type_id=None):
        super().__init__()
        self.connection = connection
        self.plant_type_id = plant_type_id
        self.setWindowTitle("Typ Rostliny")

        # Seznam pro reward (list of dict: [{"name":"...","quantity":...}, ...])
        self.reward = []
        # Seznam pro land_types (list of str)
        self.land_types = []

        self.init_ui()
        # Nastavíme defaultní hodnoty, pokud plant_type_id=None
        self.set_default_values()

        if self.plant_type_id:
            self.load_plant()

    def init_ui(self):
        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        self.name_edit = QtWidgets.QLineEdit()
        self.display_name_edit = QtWidgets.QLineEdit()
        self.model_edit = QtWidgets.QLineEdit()
        self.growing_model_edit = QtWidgets.QLineEdit()

        self.time_grow_spin = QtWidgets.QSpinBox()
        self.time_grow_spin.setRange(0, 999999)
        self.time_die_spin = QtWidgets.QSpinBox()
        self.time_die_spin.setRange(0, 999999)
        self.initial_water_spin = QtWidgets.QSpinBox()
        self.initial_water_spin.setRange(0, 999999)
        self.initial_fertilizer_spin = QtWidgets.QSpinBox()
        self.initial_fertilizer_spin.setRange(0, 999999)
        self.water_decay_spin = QtWidgets.QSpinBox()
        self.water_decay_spin.setRange(0, 999999)
        self.fertilizer_decay_spin = QtWidgets.QSpinBox()
        self.fertilizer_decay_spin.setRange(0, 999999)

        self.description_edit = QtWidgets.QPlainTextEdit()

        self.fert_time_reduction_spin = QtWidgets.QSpinBox()
        self.fert_time_reduction_spin.setRange(0, 999999)
        self.recommended_water_spin = QtWidgets.QSpinBox()
        self.recommended_water_spin.setRange(0, 999999)
        self.recommended_fertilizer_spin = QtWidgets.QSpinBox()
        self.recommended_fertilizer_spin.setRange(0, 999999)

        self.zmod_spin = QtWidgets.QDoubleSpinBox()
        self.zmod_spin.setRange(-999999.0, 999999.0)
        self.zmod_spin.setDecimals(1)

        self.bonusLand_spin = QtWidgets.QSpinBox()
        self.bonusLand_spin.setRange(-2147483648, 2147483647)

        # Reward: ukážeme v QListWidget
        reward_label = QtWidgets.QLabel("Reward (list of dict):")
        self.reward_list = QtWidgets.QListWidget()
        self.reward_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.reward_list.customContextMenuRequested.connect(self.reward_context_menu)

        # Tlačítko "Přidat položku"
        reward_btn_layout = QtWidgets.QHBoxLayout()
        reward_add_btn = QtWidgets.QPushButton("Přidat (ItemSelection)")
        reward_add_btn.clicked.connect(self.add_reward_item)
        reward_btn_layout.addWidget(reward_add_btn)

        # LandTypes
        land_label = QtWidgets.QLabel("LandTypes (list of string):")
        self.land_types_btn = QtWidgets.QPushButton("Upravit LandTypes…")
        self.land_types_btn.clicked.connect(self.edit_land_types)

        # Vložíme do formuláře
        layout.addRow("Semeno:", self.name_edit)
        layout.addRow("Název:", self.display_name_edit)
        layout.addRow("Model:", self.model_edit)
        layout.addRow("Model rostoucí rostliny:", self.growing_model_edit)
        layout.addRow("Doba růstu(min):", self.time_grow_spin)
        layout.addRow("Za jak dlouho zemře(min):", self.time_die_spin)
        layout.addRow("Počáteční úroveň vody:", self.initial_water_spin)
        layout.addRow("Počáteční úroveň hnojiva:", self.initial_fertilizer_spin)
        layout.addRow("Úbytek vody za 1m:", self.water_decay_spin)
        layout.addRow("Úbytek hnojiva za 1m:", self.fertilizer_decay_spin)
        layout.addRow("Popis rostliny:", self.description_edit)
        layout.addRow("Množství hnojiva potřebné pro redukci času:", self.fert_time_reduction_spin)
        layout.addRow("Doporučené % vody:", self.recommended_water_spin)
        layout.addRow("Doporučené % hnojiva:", self.recommended_fertilizer_spin)
        layout.addRow("Úprava výšky modelu:", self.zmod_spin)
        layout.addRow("Hash půdy kde má rostlinka zrychlený růst:", self.bonusLand_spin)

        layout.addRow(reward_label)
        layout.addRow(self.reward_list)
        layout.addRow(reward_btn_layout)

        layout.addRow(land_label, self.land_types_btn)

        # Tlačítka OK/Cancel
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self
        )
        btns.accepted.connect(self.save_plant)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def set_default_values(self):
        """
        Nastaví defaultní hodnoty pro případ, že plant_type_id je None (tj. vytváříme novou rostlinu).
        """
        if self.plant_type_id is not None:
            return  # Pokud editujeme existující, neřešíme default

        self.time_grow_spin.setValue(180)
        self.time_die_spin.setValue(360)
        self.initial_water_spin.setValue(25)
        self.initial_fertilizer_spin.setValue(25)
        self.water_decay_spin.setValue(1)
        self.fertilizer_decay_spin.setValue(1)
        self.fert_time_reduction_spin.setValue(30)
        self.recommended_water_spin.setValue(50)
        self.recommended_fertilizer_spin.setValue(50)
        self.zmod_spin.setValue(-1.0)
        self.bonusLand_spin.setValue(0)

        # Nastavíme default reward
        self.reward = [
            {"name": "onion", "quantity": 4},
            {"name": "onion_seed", "quantity": 2},
        ]
        # Nastavíme default landTypes
        self.land_types = ["home", "farm", "ranch"]
        self.update_reward_list()

    # ----------------------------------------------------------------
    #              Reward (list of dict)
    # ----------------------------------------------------------------
    def add_reward_item(self):
        """Otevře RewardItemEditor s prázdným data={} a ItemSelectionDialog uvnitř."""
        from plants_dialog import RewardItemEditor  # anebo definované nahoře
        dlg = RewardItemEditor(data=None, parent=self, connection=self.connection)
        if dlg.exec_():
            new_data = dlg.get_data()
            self.reward.append(new_data)
            self.update_reward_list()

    def reward_context_menu(self, position):
        menu = QtWidgets.QMenu()
        edit_action = menu.addAction("Upravit")
        remove_action = menu.addAction("Odebrat")

        action = menu.exec_(self.reward_list.viewport().mapToGlobal(position))
        if not action:
            return

        items = self.reward_list.selectedItems()
        if not items:
            return
        row_idx = self.reward_list.row(items[0])
        if row_idx < 0 or row_idx >= len(self.reward):
            return

        if action == remove_action:
            self.reward.pop(row_idx)
            self.update_reward_list()
        elif action == edit_action:
            from plants_dialog import RewardItemEditor
            old_data = self.reward[row_idx]
            dlg = RewardItemEditor(data=old_data.copy(), parent=self, connection=self.connection)
            if dlg.exec_():
                self.reward[row_idx] = dlg.get_data()
                self.update_reward_list()

    def update_reward_list(self):
        self.reward_list.clear()
        for rd in self.reward:
            nm = rd.get("name","???")
            qty = rd.get("quantity",0)
            self.reward_list.addItem(f"{nm} (qty={qty})")

    # ----------------------------------------------------------------
    #              LandTypes
    # ----------------------------------------------------------------
    def edit_land_types(self):
        from plants_dialog import LandTypesDialog
        dlg = LandTypesDialog(land_types=self.land_types, parent=self)
        if dlg.exec_():
            self.land_types = dlg.get_land_types()

    # ----------------------------------------------------------------
    #              Load plant
    # ----------------------------------------------------------------
    def load_plant(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM aprts_farming_plant_types WHERE plant_type_id=%s", (self.plant_type_id,))
        row = cursor.fetchone()
        if not row:
            return

        self.name_edit.setText(decode_if_bytes(row["name"]) or "")
        self.display_name_edit.setText(decode_if_bytes(row["display_name"]) or "")
        self.model_edit.setText(decode_if_bytes(row["model"]) or "")
        self.growing_model_edit.setText(decode_if_bytes(row["growing_model"]) or "")

        self.time_grow_spin.setValue(row["time_to_grow"])
        self.time_die_spin.setValue(row["time_to_die"])
        self.initial_water_spin.setValue(row["initial_water_level"])
        self.initial_fertilizer_spin.setValue(row["initial_fertilizer_level"])
        self.water_decay_spin.setValue(row["water_decay_rate"])
        self.fertilizer_decay_spin.setValue(row["fertilizer_decay_rate"])
        self.description_edit.setPlainText(decode_if_bytes(row["description"]) or "")
        self.fert_time_reduction_spin.setValue(row["fert_time_reduction"])
        self.recommended_water_spin.setValue(row["recommended_water_level"])
        self.recommended_fertilizer_spin.setValue(row["recommended_fertilizer_level"])
        self.zmod_spin.setValue(float(row["zmod"]))
        self.bonusLand_spin.setValue(int(row["bonusLand"]))

        # reward
        raw_reward = decode_if_bytes(row["reward"]) or "[]"
        try:
            reward_data = json.loads(raw_reward)
            if isinstance(reward_data, list):
                self.reward = reward_data
            else:
                self.reward = []
        except json.JSONDecodeError:
            self.reward = []
        self.update_reward_list()

        # landTypes
        raw_land = decode_if_bytes(row["landTypes"]) or "[]"
        try:
            land_data = json.loads(raw_land)
            if isinstance(land_data, list):
                self.land_types = land_data
            else:
                self.land_types = []
        except json.JSONDecodeError:
            self.land_types = []

    # ----------------------------------------------------------------
    #              Save plant
    # ----------------------------------------------------------------
    def save_plant(self):
        name_val = self.name_edit.text().strip()
        if not name_val:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'name' nesmí být prázdné.")
            return

        display_name_val = self.display_name_edit.text().strip()
        model_val = self.model_edit.text().strip()
        growing_model_val = self.growing_model_edit.text().strip()
        time_grow_val = self.time_grow_spin.value()
        time_die_val = self.time_die_spin.value()
        init_water_val = self.initial_water_spin.value()
        init_fert_val = self.initial_fertilizer_spin.value()
        water_decay_val = self.water_decay_spin.value()
        fert_decay_val = self.fertilizer_decay_spin.value()
        descr_val = self.description_edit.toPlainText()
        fert_time_red_val = self.fert_time_reduction_spin.value()
        rec_water_val = self.recommended_water_spin.value()
        rec_fert_val = self.recommended_fertilizer_spin.value()
        zmod_val = self.zmod_spin.value()
        bonusLand_val = self.bonusLand_spin.value()

        reward_str = json.dumps(self.reward, ensure_ascii=False)
        land_str = json.dumps(self.land_types, ensure_ascii=False)

        cursor = self.connection.cursor()
        if self.plant_type_id:
            query = """
                UPDATE aprts_farming_plant_types
                SET name=%s, display_name=%s, model=%s, growing_model=%s,
                    reward=%s, time_to_grow=%s, time_to_die=%s,
                    initial_water_level=%s, initial_fertilizer_level=%s,
                    water_decay_rate=%s, fertilizer_decay_rate=%s,
                    description=%s, fert_time_reduction=%s,
                    recommended_water_level=%s, recommended_fertilizer_level=%s,
                    zmod=%s, bonusLand=%s, landTypes=%s
                WHERE plant_type_id=%s
            """
            params = (
                name_val, display_name_val, model_val, growing_model_val,
                reward_str, time_grow_val, time_die_val,
                init_water_val, init_fert_val,
                water_decay_val, fert_decay_val,
                descr_val, fert_time_red_val,
                rec_water_val, rec_fert_val,
                zmod_val, bonusLand_val, land_str,
                self.plant_type_id
            )
        else:
            query = """
                INSERT INTO aprts_farming_plant_types
                (name, display_name, model, growing_model, reward,
                 time_to_grow, time_to_die, initial_water_level, initial_fertilizer_level,
                 water_decay_rate, fertilizer_decay_rate, description,
                 fert_time_reduction, recommended_water_level, recommended_fertilizer_level,
                 zmod, bonusLand, landTypes)
                VALUES
                (%s, %s, %s, %s, %s,
                 %s, %s, %s, %s,
                 %s, %s, %s,
                 %s, %s, %s,
                 %s, %s, %s)
            """
            params = (
                name_val, display_name_val, model_val, growing_model_val, reward_str,
                time_grow_val, time_die_val, init_water_val, init_fert_val,
                water_decay_val, fert_decay_val, descr_val,
                fert_time_red_val, rec_water_val, rec_fert_val,
                zmod_val, bonusLand_val, land_str
            )

        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")
