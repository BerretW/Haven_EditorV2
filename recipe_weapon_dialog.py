import os
import json
from PyQt5 import QtWidgets, QtCore, QtGui

class RecipeWeaponDialog(QtWidgets.QDialog):
    """
    Dialog pro výběr zbraně a komponent z weapons.json.
    Uživatel vybere konkrétní zbraň a k ní libovolné komponenty.
    Po potvrzení tlačítkem OK dojde k nastavení 'weapon_name' a 'comps_json',
    které lze následně použít v receptu.
    """

    def __init__(self, weapons_data, current_weapon=None, current_comps=None, parent=None):
        """
        :param weapons_data: Dict načtený z weapons.json
        :param current_weapon: string s názvem (item) aktuálně zvolené zbraně (např. "WEAPON_REVOLVER_CATTLEMAN")
        :param current_comps: JSON string s komponentami (např. {"hash_barrel": "COMPONENT_REVOLVER_CATTLEMAN_BARREL_LONG"}), nebo None
        :param parent: Rodičovské okno
        """
        super().__init__(parent)
        self.weapons_data = weapons_data
        self.current_weapon = current_weapon
        # Parsujeme current_comps do slovníku
        try:
            self.current_comps = json.loads(current_comps) if current_comps else {}
        except json.JSONDecodeError:
            self.current_comps = {}
        self.chosen_weapon = None
        self.chosen_comps = {}
        self.setWindowTitle("Nastavení Zbraně a Komponent")
        self.resize(600, 400)
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        # 1) Vybereme zbraň
        self.weapon_combo = QtWidgets.QComboBox()
        self.weapon_combo.addItem("Vybrat zbraň...", None)

        # Naplníme ComboBox zbraněmi z weapons_data
        # weapons_data má strukturu: {"SHORTARM": {"WEAPON_REVOLVER_CATTLEMAN": {...}}, "LONGARM": {...}, ...}
        self.all_weapon_keys = []  # Abychom mohli dohledat, ke které "větvi" patří vybraný weapon_name
        for weapon_type, weapons_dict in self.weapons_data.items():
            for weapon_name in weapons_dict.keys():
                # Uložíme si weapon_type, weapon_name, abychom ho pak podle indexu dohledali
                display_text = f"{weapon_name} ({weapon_type})"
                self.weapon_combo.addItem(display_text, (weapon_type, weapon_name))
                self.all_weapon_keys.append((weapon_type, weapon_name))

        self.weapon_combo.currentIndexChanged.connect(self.on_weapon_selected)

        # 2) Sekce pro komponenty (ComboBoxy)
        self.components_layout = QtWidgets.QFormLayout()
        # Tady budeme dynamicky vytvářet ComboBoxy pro category (BARREL, GRIP, SIGHT,...)

        # Tlačítka OK a Cancel
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)

        # Poskládáme do Layoutu
        main_layout.addWidget(QtWidgets.QLabel("Zbraň:"))
        main_layout.addWidget(self.weapon_combo)
        main_layout.addLayout(self.components_layout)
        main_layout.addWidget(button_box)

        # Pokud existuje current_weapon, nastavíme ho v ComboBoxu
        if self.current_weapon:
            self.select_current_weapon(self.current_weapon)

    def select_current_weapon(self, weapon_name):
        """Vybere v ComboBoxu zbraň, která se rovná weapon_name, pokud existuje."""
        # weapon_name např. "WEAPON_REVOLVER_CATTLEMAN"
        for i in range(1, self.weapon_combo.count()):  # 0 je "Vybrat zbraň..."
            data = self.weapon_combo.itemData(i)
            if data and data[1] == weapon_name:
                self.weapon_combo.setCurrentIndex(i)
                break

    def on_weapon_selected(self, index):
        # Smažeme původní layout
        for i in reversed(range(self.components_layout.count())):
            item = self.components_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        if index <= 0:
            return  # Nic nevybráno

        weapon_type, weapon_name = self.weapon_combo.itemData(index)
        # Uložíme si do chosen_weapon
        self.chosen_weapon = weapon_name

        # Vytáhneme dictionary pro vybranou zbraň
        weapon_dict = self.weapons_data.get(weapon_type, {}).get(weapon_name, {})
        # Např. {"BARREL": [...], "GRIP": [...], "SIGHT": [...], ...}

        self.category_combos = {}  # Pro uložení odkazů na ComboBoxy

        for category, comp_list in weapon_dict.items():
            category_label = QtWidgets.QLabel(category)
            category_combo = QtWidgets.QComboBox()
            category_combo.addItem("Žádná", None)
            for comp_info in comp_list:
                category_combo.addItem(comp_info['title'], comp_info['hashname'])

            # Pokud v current_comps máme "hash_barrel": "COMPONENT_...", tak ho nastavíme
            # Klíč v current_comps je "hash_{category.lower()}"
            # hash_key = f"hash_{category.lower()}"
            hash_key = category
            if hash_key in self.current_comps:
                # Najdeme index
                saved_hash = self.current_comps[hash_key]
                for idx in range(category_combo.count()):
                    if category_combo.itemData(idx) == saved_hash:
                        category_combo.setCurrentIndex(idx)
                        break

            self.components_layout.addRow(category_label, category_combo)
            self.category_combos[category] = category_combo

    def on_accept(self):
        """Zpracujeme vybrané zbraň a komponenty a předáme je volajícímu dialogu."""
        # 1) Zbraň
        idx = self.weapon_combo.currentIndex()
        if idx <= 0:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Musíte vybrat zbraň, nebo stisknout Cancel.")
            return

        weapon_type, weapon_name = self.weapon_combo.itemData(idx)
        self.chosen_weapon = weapon_name

        # 2) Komponenty
        comps_dict = {}
        for category, combo in self.category_combos.items():
            hashname = combo.currentData()
            if hashname:
                # key = f"hash_{category.lower()}"
                key = category
                comps_dict[key] = hashname

        # Uložíme do self.chosen_comps JSON
        if comps_dict:
            self.chosen_comps = json.dumps(comps_dict)
        else:
            self.chosen_comps = ""  # Prázdný string

        self.accept()  # Uzavře dialog

    def get_result(self):
        """
        :return: (weapon_name: str, comps_json: str)
        """
        return self.chosen_weapon, self.chosen_comps
