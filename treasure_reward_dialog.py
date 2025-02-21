# treasure_reward_dialog.py

import sys
import json
import os
import re
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector

from item_manager import ItemSelectionDialog
from recipe_weapon_dialog import RecipeWeaponDialog  # Dialog pro nastavení zbraně


def decode_if_bytes(value):
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return value


def merge_dicts(default, override):
    """
    Rekurzivně sloučí dva slovníky.
    Hodnoty z 'override' přepíší ty z 'default'.
    """
    result = default.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


class TreasureRewardDialog(QtWidgets.QDialog):
    """Dialog pro přidání / úpravu odměny (aprts_treasure_rewards)."""

    def __init__(self, connection, reward_id=None, treasure_type_id=None):
        super().__init__()
        self.connection = connection
        self.reward_id = reward_id
        self.treasure_type_id = treasure_type_id  # abychom věděli, pro jaký typ
        self.setWindowTitle("Treasure Reward")
        self.setMinimumWidth(600)  # Zvětšíme šířku pro lepší zobrazení JSON
        self.weapons_data = self.load_weapons_data()  # Načteme weapons.json
        self.init_ui()

        # Klíčová data
        self.meta = {}  # Zde budeme držet data (částečně se propisují do JSON v meta_display)
        self.default_meta = {}  # Předdefinovaná metadata z tabulky items

        # Pokud už máme reward_id, načteme existující data
        if self.reward_id is not None:
            self.load_data()

    def load_weapons_data(self):
        """
        Načte weapons.json, pokud existuje, a vrátí dict.
        Pokud se nepodaří načíst, vrátí prázdný dict.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        weapons_path = os.path.join(base_dir, 'weapons.json')
        if os.path.exists(weapons_path):
            try:
                with open(weapons_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Chyba při načítání weapons.json: {e}")
                return {}
        return {}

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_layout = QtWidgets.QFormLayout()

        # 1) Řádek pro item + tlačítko na vybrání itemu
        self.item_edit = QtWidgets.QLineEdit()
        self.item_edit.setReadOnly(True)
        self.item_edit.setToolTip("Zobrazuje vybraný item. Klikněte na 'Vybrat Item' pro výběr.")
        self.select_item_button = QtWidgets.QPushButton("Vybrat Item")
        self.select_item_button.clicked.connect(self.select_item)
        self.clear_item_button = QtWidgets.QPushButton("Vyprázdnit Item")
        self.clear_item_button.clicked.connect(self.clear_item)

        item_layout = QtWidgets.QHBoxLayout()
        item_layout.addWidget(self.item_edit)
        item_layout.addWidget(self.select_item_button)
        item_layout.addWidget(self.clear_item_button)
        form_layout.addRow("Item:", item_layout)

        # 2) Count
        self.count_spin = QtWidgets.QSpinBox()
        self.count_spin.setRange(1, 9999)
        self.count_spin.setToolTip("Nastavte počet položek.")
        form_layout.addRow("Count:", self.count_spin)

        # 3) isWeapon
        self.isweapon_check = QtWidgets.QCheckBox("Je zbraň?")
        self.isweapon_check.setToolTip("Zaškrtněte, pokud je item zbraní.")
        self.isweapon_check.stateChanged.connect(self.on_isweapon_changed)
        form_layout.addRow("", self.isweapon_check)

        # 4) Tlačítko "Nastavit parametry zbraně..."
        self.weapon_button = QtWidgets.QPushButton("Nastavit parametry zbraně…")
        self.weapon_button.setEnabled(False)
        self.weapon_button.setToolTip("Klikněte pro nastavení parametrů zbraně.")
        self.weapon_button.clicked.connect(self.open_weapon_dialog)
        form_layout.addRow("", self.weapon_button)

        # 5) Textové pole pro meta_display (zobrazí JSON)
        self.meta_display = QtWidgets.QTextEdit()
        self.meta_display.setReadOnly(False)  # Chceme, aby šlo JSON přímo editovat
        self.meta_display.setPlaceholderText("Meta data se zobrazí a upraví zde...")
        self.meta_display.setToolTip("Zobrazení a úprava meta dat ve formátu JSON.")
        form_layout.addRow("Meta Data:", self.meta_display)

        # 6) custom_name – VŽDY viditelný (pro itemy != zbraň)
        self.custom_name_edit = QtWidgets.QLineEdit()
        self.custom_name_edit.setPlaceholderText("Zadejte vlastní název (ne-zbraň)")
        self.custom_name_edit.textChanged.connect(self.update_meta_display)
        form_layout.addRow("Custom Name:", self.custom_name_edit)

        # 7) Serial – pouze pro zbraně, necháme ho implementovaný
        self.serial_edit = QtWidgets.QLineEdit()
        self.serial_edit.setPlaceholderText("Zadejte sériové číslo (jen pro zbraň)")
        self.serial_edit.setVisible(False)  # Zobrazí se jen pokud isWeapon
        self.serial_edit.textChanged.connect(self.update_meta_display)
        form_layout.addRow("Serial:", self.serial_edit)

        # 8) Editor pro lístečky (skrytý na začátku)
        self.note_editor_group = QtWidgets.QGroupBox("Editor Lístečku")
        self.note_editor_layout = QtWidgets.QFormLayout()
        self.note_editor_group.setLayout(self.note_editor_layout)
        self.note_editor_group.setVisible(False)

        self.is_fill_check = QtWidgets.QCheckBox("Vyplněný lísteček")
        self.is_fill_check.setToolTip("Zaškrtněte, pokud je lísteček vyplněný.")
        self.is_fill_check.stateChanged.connect(self.update_meta_display)
        self.note_editor_layout.addRow(self.is_fill_check)

        self.paper_content_edit = QtWidgets.QTextEdit()
        self.paper_content_edit.setPlaceholderText("Zadejte obsah lístečku...")
        self.paper_content_edit.setToolTip("Zadejte text obsahu lístečku.")
        self.paper_content_edit.textChanged.connect(self.update_meta_display)
        self.note_editor_layout.addRow("Obsah:", self.paper_content_edit)

        self.signed_by_edit = QtWidgets.QLineEdit()
        self.signed_by_edit.setPlaceholderText("Zadejte jméno podpisu")
        self.signed_by_edit.setToolTip("Zadejte jméno osoby, která lísteček podepsala.")
        self.signed_by_edit.textChanged.connect(self.update_meta_display)
        self.note_editor_layout.addRow("Podepsal(a):", self.signed_by_edit)

        form_layout.addRow(self.note_editor_group)

        layout.addLayout(form_layout)

        # Tlačítka OK/Cancel
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self
        )
        btns.accepted.connect(self.save_data)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # Signál pro zachytávání změn v meta_display (JSON) a propsání zpátky do UI
        self.meta_display.textChanged.connect(self.sync_ui_from_meta_display)

    def on_isweapon_changed(self, state):
        """
        Pokud je isWeapon zaškrtnuto, aktivujeme tlačítko pro nastavení zbraně
        a skryjeme (nebo znepřístupníme) custom_name_edit, protože zbraň má vlastní implementaci.
        """
        is_checked = (state == QtCore.Qt.Checked)
        self.weapon_button.setEnabled(is_checked)

        # Pokud je to zbraň, pak custom_name neřešíme – schováme
        if is_checked:
            self.custom_name_edit.setVisible(False)
            self.custom_name_edit.clear()  # vymažeme, aby se nepřepisovala do JSONu
            self.serial_edit.setVisible(True)
        else:
            self.custom_name_edit.setVisible(True)
            self.serial_edit.setVisible(False)
            self.serial_edit.clear()

        # Znovu překreslíme meta_display
        self.update_meta_display()

    def open_weapon_dialog(self):
        """
        Otevře RecipeWeaponDialog pro konfiguraci zbraně a uloží výsledek do self.meta.
        """
        current_weapon_name = self.meta.get("weapon_name", "")
        current_comps_json = self.meta.get("comps_json", "")

        dlg = RecipeWeaponDialog(
            self.weapons_data,
            current_weapon=current_weapon_name,
            current_comps=current_comps_json,
            parent=self
        )
        if dlg.exec_():
            weapon_name, comps_json = dlg.get_result()
            if weapon_name:
                # Uložíme do meta
                self.meta["weapon_name"] = weapon_name
                self.meta["comps_json"] = comps_json

                # Automaticky nastavíme item_edit na spawn název zbraně
                self.item_edit.setText(weapon_name)

                # Zobrazíme meta data v meta_display
                try:
                    comps_dict = json.loads(comps_json)
                    formatted_meta = json.dumps(comps_dict, indent=4, ensure_ascii=False)
                    self.meta_display.setPlainText(formatted_meta)
                except json.JSONDecodeError:
                    self.meta_display.setPlainText(comps_json)

                self.update_meta_display()

    def select_item(self):
        """
        Otevře ItemSelectionDialog a uloží vybraný item do self.item_edit.
        """
        dialog = ItemSelectionDialog(self.connection, single_selection=True)
        if dialog.exec_():
            selected = dialog.selected_items
            if selected:
                chosen_item = selected[0]['item']
                label = selected[0].get('label', chosen_item)
                self.item_edit.setText(chosen_item)

                # Zobrazíme/skryjeme editor lístečku podle itemu
                if chosen_item.lower() == "note":
                    self.note_editor_group.setVisible(True)
                else:
                    self.note_editor_group.setVisible(False)

                # Načteme předdefinovaná metadata pro tento item
                self.load_default_meta(chosen_item)

                # Aktualizujeme meta display
                self.update_meta_display()

    def clear_item(self):
        """Vyprázdní pole pro item."""
        self.item_edit.clear()
        self.note_editor_group.setVisible(False)
        self.default_meta = {}
        self.meta = {}
        self.update_meta_display()

    def load_default_meta(self, item_name):
        """
        Načte předdefinovaná metadata pro daný item z tabulky items.
        """
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT metadata FROM items WHERE item=%s LIMIT 1"
        cursor.execute(query, (item_name,))
        row = cursor.fetchone()
        if row and row.get("metadata"):
            try:
                default_meta = json.loads(decode_if_bytes(row["metadata"]))
                self.default_meta = default_meta
            except json.JSONDecodeError:
                self.default_meta = {}
        else:
            self.default_meta = {}

        # Pokud existují existující meta data pro odměnu, sloučíme je s default_meta
        # Priorita mají existující meta data odměny
        self.meta = merge_dicts(self.default_meta, self.meta)
        cursor.close()

    def load_data(self):
        """
        Načteme data z DB a vyplníme UI.
        """
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM aprts_treasure_rewards WHERE id=%s", (self.reward_id,)
        )
        row = cursor.fetchone()
        if row:
            # Nastavíme item
            item_val = decode_if_bytes(row["item"]) or ""
            self.item_edit.setText(item_val)
            self.count_spin.setValue(row["count"])
            self.treasure_type_id = row["treasure_type_id"]

            # isWeapon
            isweapon_val = row.get("isWeapon", 0)
            self.isweapon_check.setChecked(bool(isweapon_val))

            # Načteme meta (JSON)
            meta_str = decode_if_bytes(row.get("meta") or "")
            try:
                if meta_str:
                    reward_meta = json.loads(meta_str)
                else:
                    reward_meta = {}
            except json.JSONDecodeError:
                reward_meta = {}

            # Načteme předdefinovaná metadata pro tento item
            self.load_default_meta(item_val)

            # Sloučíme předdefinovaná metadata s reward_meta
            self.meta = merge_dicts(self.default_meta, reward_meta)

            # Nastavíme meta do meta_display (pretty JSON)
            formatted_meta = json.dumps(self.meta, indent=4, ensure_ascii=False)
            self.meta_display.setPlainText(formatted_meta)

            # Nastavíme custom_name – jen pokud nejde o zbraň
            if isweapon_val:
                self.custom_name_edit.clear()
                self.custom_name_edit.setVisible(False)
                self.serial_edit.setVisible(True)
                self.serial_edit.setText(self.meta.get("serial", ""))
            else:
                self.custom_name_edit.setVisible(True)
                self.serial_edit.setVisible(False)
                self.serial_edit.clear()
                self.custom_name_edit.setText(self.meta.get("custom_name", ""))

            # Pokud je item "note", zobrazíme editor lístečku
            if item_val.lower() == "note":
                self.note_editor_group.setVisible(True)
                paper = self.meta.get("paper", {})
                self.is_fill_check.setChecked(paper.get("is_fill", False))
                self.paper_content_edit.setPlainText(paper.get("content", ""))
                self.signed_by_edit.setText(paper.get("signed_by", ""))
            else:
                self.note_editor_group.setVisible(False)

        cursor.close()

    def update_meta_display(self):
        """
        Z UI vyzobeme data a uložíme je do self.meta,
        poté je zobrazíme v meta_display v JSON formátu.
        """
        # Vycházíme z existujícího self.meta (abychom neztratili data o zbrani atd.)
        current_meta = self.meta.copy()

        # Zbraň?
        if self.isweapon_check.isChecked():
            # Pro zbraň ignorujeme custom_name z UI – má svoji vlastní logiku
            # Nicméně u serial si můžeme vybrat, zda ho chceme ukládat do JSONu
            serial_val = self.serial_edit.text().strip()
            if serial_val:
                current_meta["serial"] = serial_val
            else:
                current_meta.pop("serial", None)
        else:
            # Pro *všechny ostatní* itemy ukládáme custom_name
            custom_name_val = self.custom_name_edit.text().strip()
            if custom_name_val:
                current_meta["custom_name"] = custom_name_val
            else:
                current_meta.pop("custom_name", None)

        # Pokud je item "note", ukládáme paper data
        if self.item_edit.text().lower() == "note":
            paper = {}
            paper["is_fill"] = self.is_fill_check.isChecked()
            content = self.paper_content_edit.toPlainText().strip()
            signed_by = self.signed_by_edit.text().strip()

            if content:
                paper["content"] = content
            else:
                paper.pop("content", None)

            if signed_by:
                paper["signed_by"] = signed_by
            else:
                paper.pop("signed_by", None)

            # Pokud je paper prázdné, vyhodíme ho z meta
            if paper:
                current_meta["paper"] = paper
            else:
                current_meta.pop("paper", None)
        else:
            current_meta.pop("paper", None)

        self.meta = current_meta
        try:
            formatted_meta = json.dumps(self.meta, indent=4, ensure_ascii=False)
            self.meta_display.blockSignals(True)  # blokujeme signály, abychom se vyhnuli smyčce
            self.meta_display.setPlainText(formatted_meta)
            self.meta_display.blockSignals(False)
        except (TypeError, ValueError):
            self.meta_display.blockSignals(True)
            self.meta_display.setPlainText("Nevalidní meta data.")
            self.meta_display.blockSignals(False)

    def sync_ui_from_meta_display(self):
        """
        Pokud uživatel ručně upraví JSON v meta_display, zkusíme ho načíst a propsat do UI.
        Ale pozor na item zbraň: tam custom_name záměrně neřešíme, aby si to "nerozbilo" logiku zbraní.
        """
        text = self.meta_display.toPlainText().strip()
        if not text:
            self.meta = {}
            self.custom_name_edit.setText("")
            self.serial_edit.setText("")
            return

        try:
            new_meta = json.loads(text)
        except json.JSONDecodeError:
            return  # Neplatný JSON, necháme to tak

        self.meta = new_meta

        # Pokud není isWeapon, custom_name nastavíme do QLineEdit
        if not self.isweapon_check.isChecked():
            custom_name = new_meta.get("custom_name", "")
            if self.custom_name_edit.text() != custom_name:
                self.custom_name_edit.blockSignals(True)
                self.custom_name_edit.setText(custom_name)
                self.custom_name_edit.blockSignals(False)
        else:
            # Pro zbraň ho ignorujeme
            pass

        # Pokud je isWeapon, tak podle libosti nastavíme serial
        if self.isweapon_check.isChecked():
            serial_val = new_meta.get("serial", "")
            if self.serial_edit.text() != serial_val:
                self.serial_edit.blockSignals(True)
                self.serial_edit.setText(serial_val)
                self.serial_edit.blockSignals(False)

        # Pokud je note, propsat paper
        if self.item_edit.text().lower() == "note":
            paper = new_meta.get("paper", {})
            is_fill = paper.get("is_fill", False)
            content = paper.get("content", "")
            signed_by = paper.get("signed_by", "")

            self.is_fill_check.blockSignals(True)
            self.is_fill_check.setChecked(is_fill)
            self.is_fill_check.blockSignals(False)

            self.paper_content_edit.blockSignals(True)
            self.paper_content_edit.setPlainText(content)
            self.paper_content_edit.blockSignals(False)

            self.signed_by_edit.blockSignals(True)
            self.signed_by_edit.setText(signed_by)
            self.signed_by_edit.blockSignals(False)

            self.note_editor_group.setVisible(True)
        else:
            self.note_editor_group.setVisible(False)

    def save_data(self):
        """
        Uložíme do DB.
        """
        item_val = self.item_edit.text().strip()
        if not item_val:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'item' nesmí být prázdné.")
            return

        if not self.treasure_type_id:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Chybí treasure_type_id (vnitřní chyba?).")
            return

        # isWeapon
        isweapon_val = 1 if self.isweapon_check.isChecked() else 0
        count_val = self.count_spin.value()

        # Finalizujeme JSON, který uložíme
        meta_json = ""
        if self.meta:
            try:
                meta_json = json.dumps(self.meta, ensure_ascii=False)
            except (TypeError, ValueError):
                QtWidgets.QMessageBox.warning(
                    self, "Chyba", "Meta data nejsou validní JSON."
                )
                return

        cursor = self.connection.cursor()
        if self.reward_id is not None:
            # UPDATE
            query = """
                UPDATE aprts_treasure_rewards
                SET item=%s, count=%s, isWeapon=%s, meta=%s
                WHERE id=%s
            """
            params = (item_val, count_val, isweapon_val, meta_json, self.reward_id)
        else:
            # INSERT
            query = """
                INSERT INTO aprts_treasure_rewards (treasure_type_id, item, count, isWeapon, meta)
                VALUES (%s, %s, %s, %s, %s)
            """
            params = (self.treasure_type_id, item_val, count_val, isweapon_val, meta_json)

        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()  # Zavře dialog s úspěchem
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")
        finally:
            cursor.close()
