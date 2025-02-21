# herb_dialog.py
import json
import os
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from item_manager import ItemSelectionDialog

########################################
# DIALOG PRO PŘIDÁNÍ / ÚPRAVU JEDNÉ ODMĚNY
########################################
class RewardDialog(QtWidgets.QDialog):
    """Dialog pro přidání nebo úpravu jedné odměny (item, chance, maxamount)."""
    def __init__(self, connection, reward=None, parent=None):
        """
        :param reward: dict typu {"item": ..., "chance": ..., "maxamount": ...},
                       pokud je None, jde o přidání nové.
        """
        super().__init__(parent)
        self.connection = connection
        self.setWindowTitle("Odměna")
        self.init_ui()

        self.selected_item = None  # item code
        self.chance = 100
        self.maxamount = 1

        if reward:
            # Pokud jsme dostali existující odměnu, vyplníme pole
            self.selected_item = reward.get('item')
            self.chance = reward.get('chance', 100)
            self.maxamount = reward.get('maxamount', 1)

            # Nastavíme zobrazení
            if self.selected_item:
                lbl = self.get_item_label(self.selected_item) or self.selected_item
                self.item_label.setText(f"{lbl} ({self.selected_item})")

            self.chance_spin.setValue(self.chance)
            self.maxamount_spin.setValue(self.maxamount)

    def init_ui(self):
        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        # Výběr itemu
        self.item_select_button = QtWidgets.QPushButton("Vybrat Item")
        self.item_label = QtWidgets.QLabel("Žádný item vybrán")
        self.item_select_button.clicked.connect(self.select_item)

        layout.addRow("Item:", self.item_select_button)
        layout.addRow("", self.item_label)

        # Číselníky pro chance a maxamount
        self.chance_spin = QtWidgets.QSpinBox()
        self.chance_spin.setRange(0, 100)
        self.chance_spin.setValue(100)

        self.maxamount_spin = QtWidgets.QSpinBox()
        self.maxamount_spin.setRange(1, 9999)
        self.maxamount_spin.setValue(1)

        layout.addRow("Šance (%):", self.chance_spin)
        layout.addRow("Max. množství:", self.maxamount_spin)

        # Tlačítka OK/Cancel
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def select_item(self):
        dialog = ItemSelectionDialog(self.connection, single_selection=True)
        if dialog.exec_():
            selected = dialog.selected_items
            if selected:
                self.selected_item = selected[0]['item']
                lbl = self.get_item_label(self.selected_item) or self.selected_item
                self.item_label.setText(f"{lbl} ({self.selected_item})")

    def get_item_label(self, item_name):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT label FROM items WHERE item = %s", (item_name,))
        result = cursor.fetchone()
        if result and result.get('label'):
            return result['label']
        else:
            return None

    def accept_dialog(self):
        # Kontrola, zda uživatel vybral item
        if not self.selected_item:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Musíte vybrat item jako odměnu.")
            return
        self.chance = self.chance_spin.value()
        self.maxamount = self.maxamount_spin.value()
        self.accept()

    def get_reward_data(self):
        # Vrátíme dict s parametry
        return {
            'item': self.selected_item,
            'chance': self.chance,
            'maxamount': self.maxamount
        }


########################################
# HLAVNÍ DIALOG PRO BYLINKU
########################################
class HerbDialog(QtWidgets.QDialog):
    def __init__(self, connection, herb_id=None):
        super().__init__()
        self.connection = connection
        self.herb_id = herb_id
        self.setWindowTitle("Bylinka")
        self.load_stylesheet(os.path.join(BASE_DIR, "stylesheet.qss"))
        # Seznam odměn (list of dict: {item, chance, maxamount})
        self.rewards = []

        self.cache_dir = 'cache'
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        self.init_ui()
        if self.herb_id:
            self.load_herb()
    def load_stylesheet(self, filepath):
        """Načte stylesheet z externího souboru."""
        try:
            with open(filepath, "r") as file:
                self.setStyleSheet(file.read())
        except Exception as e:
            print(f"Chyba při načítání stylů: {e}")

    def init_ui(self):
        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        # Základní pole
        self.source_edit = QtWidgets.QLineEdit()
        self.animDict_edit = QtWidgets.QLineEdit()
        self.animBody_edit = QtWidgets.QLineEdit()
        self.gatherTime_edit = QtWidgets.QSpinBox()
        self.gatherTime_edit.setMaximum(999999)
        self.failedText_edit = QtWidgets.QLineEdit()

        layout.addRow("source:", self.source_edit)
        layout.addRow("animDict:", self.animDict_edit)
        layout.addRow("animBody:", self.animBody_edit)
        layout.addRow("GatherTime:", self.gatherTime_edit)
        layout.addRow("failedText:", self.failedText_edit)

        # --- Odměny ---
        rewards_layout = QtWidgets.QVBoxLayout()
        rewards_label = QtWidgets.QLabel("Odměny:")
        rewards_layout.addWidget(rewards_label)

        self.rewards_list = QtWidgets.QListWidget()
        self.rewards_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.rewards_list.customContextMenuRequested.connect(self.show_rewards_context_menu)
        rewards_layout.addWidget(self.rewards_list)

        # Tlačítka pro správu odměn
        rewards_buttons_layout = QtWidgets.QHBoxLayout()
        add_reward_button = QtWidgets.QPushButton("Přidat Odměnu")
        add_reward_button.setStyleSheet("background-color: #5cb85c; color: white;")
        add_reward_button.clicked.connect(self.add_reward)

        remove_reward_button = QtWidgets.QPushButton("Odebrat Odměnu")
        remove_reward_button.setStyleSheet("background-color: #d9534f; color: white;")
        remove_reward_button.clicked.connect(self.remove_selected_reward)

        rewards_buttons_layout.addWidget(add_reward_button)
        rewards_buttons_layout.addWidget(remove_reward_button)
        rewards_layout.addLayout(rewards_buttons_layout)

        layout.addRow(rewards_layout)

        # Tlačítka OK/Cancel
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self
        )
        buttons.accepted.connect(self.save_herb)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def show_rewards_context_menu(self, position):
        """Kontextové menu pro odměny (změna chance, maxamount, odstranění)."""
        menu = QtWidgets.QMenu()

        edit_chance_action = menu.addAction("Změnit Šanci")
        edit_maxamount_action = menu.addAction("Změnit Množství")
        remove_action = menu.addAction("Odebrat Odměnu")

        action = menu.exec_(self.rewards_list.viewport().mapToGlobal(position))
        if not action:
            return

        selected_items = self.rewards_list.selectedItems()
        if not selected_items:
            return

        list_item = selected_items[0]
        index = self.rewards_list.row(list_item)
        reward = self.rewards[index]

        if action == remove_action:
            self.rewards.pop(index)
            self.update_rewards_list()
        elif action == edit_chance_action:
            new_chance, ok = QtWidgets.QInputDialog.getInt(
                self, "Změnit Šanci", "Zadejte novou šanci (0-100):",
                value=reward.get('chance', 100), min=0, max=100
            )
            if ok:
                reward['chance'] = new_chance
                self.update_rewards_list()
        elif action == edit_maxamount_action:
            new_max, ok = QtWidgets.QInputDialog.getInt(
                self, "Změnit Množství", "Zadejte nové max. množství:",
                value=reward.get('maxamount', 1), min=1, max=9999
            )
            if ok:
                reward['maxamount'] = new_max
                self.update_rewards_list()

    def add_reward(self):
        """Otevře dialog pro přidání nové odměny."""
        dialog = RewardDialog(self.connection, parent=self)
        if dialog.exec_():
            reward = dialog.get_reward_data()
            # NEDĚLÁME self.rewards = [reward], ale append:
            self.rewards.append(reward)
            self.update_rewards_list()

    def remove_selected_reward(self):
        """Odstraní vybranou odměnu (tlačítko 'Odebrat Odměnu')."""
        selected_items = self.rewards_list.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Musíte vybrat odměnu k odebrání.")
            return

        for item in selected_items:
            index = self.rewards_list.row(item)
            self.rewards.pop(index)
        self.update_rewards_list()

    def update_rewards_list(self):
        """Zobrazí self.rewards v ListWidgetu i s ikonami."""
        self.rewards_list.clear()
        for rwd in self.rewards:
            # Najdeme label itemu
            item_label = self.get_item_label(rwd['item']) or rwd['item']
            chance = rwd.get("chance", 100)
            maxamt = rwd.get("maxamount", 1)

            # Pokusíme se načíst ikonku
            icon = QtGui.QIcon()
            pixmap = self.load_item_image(rwd['item'])
            if pixmap:
                icon = QtGui.QIcon(pixmap)

            # Vypíšeme
            text = f"{item_label} ({rwd['item']}) | chance:{chance}% | max:{maxamt}"
            list_item = QtWidgets.QListWidgetItem(icon, text)
            self.rewards_list.addItem(list_item)

    def load_item_image(self, item_name):
        """Načte obrázek z cache nebo z DB (podobně jako v recipe_dialog)."""
        cache_file_path = os.path.join(self.cache_dir, f"{item_name}.png")
        if os.path.exists(cache_file_path):
            pixmap = QtGui.QPixmap(cache_file_path)
        else:
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

    def get_item_label(self, item_name):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT label FROM items WHERE item = %s", (item_name,))
        result = cursor.fetchone()
        if result and result.get('label'):
            return result['label']
        return None

    def decode_if_bytes(self, value):
        if isinstance(value, bytes):
            return value.decode('utf-8', 'replace')
        return value

    def load_herb(self):
        """Načteme data bylinky z DB a naplníme formulář."""
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM aprts_herbs WHERE id=%s", (self.herb_id,))
        herb = cursor.fetchone()
        if herb:
            self.source_edit.setText(self.decode_if_bytes(herb['source']) or '')
            self.animDict_edit.setText(self.decode_if_bytes(herb['animDict']) or '')
            self.animBody_edit.setText(self.decode_if_bytes(herb['animBody']) or '')
            self.gatherTime_edit.setValue(herb['GatherTime'])
            self.failedText_edit.setText(self.decode_if_bytes(herb['failedText']) or '')

            # Načteme reward do self.rewards
            raw_reward = herb.get('reward', b'')
            if isinstance(raw_reward, bytes):
                raw_reward = raw_reward.decode('utf-8', 'replace')
            if not raw_reward:
                raw_reward = '[]'
            try:
                rewards_data = json.loads(raw_reward)
                if isinstance(rewards_data, list):
                    self.rewards = rewards_data
                elif isinstance(rewards_data, dict):
                    # Pokud by byl uložen dict, např. {"branch":2}, ale vy zřejmě máte list
                    # tak to v takovém případě překlopíme do listu
                    self.rewards = [
                        {'item': k, 'maxamount': v, 'chance': 100}
                        for k, v in rewards_data.items()
                    ]
                else:
                    self.rewards = []
            except json.JSONDecodeError:
                self.rewards = []

            self.update_rewards_list()

    def save_herb(self):
        """Uloží bylinku do DB."""
        source = self.source_edit.text().strip()
        animDict = self.animDict_edit.text().strip()
        animBody = self.animBody_edit.text().strip()
        gatherTime = self.gatherTime_edit.value()
        failedText = self.failedText_edit.text().strip()

        # Převést self.rewards na JSON
        reward_json = json.dumps(self.rewards, ensure_ascii=False)

        cursor = self.connection.cursor()
        if self.herb_id:
            query = """
                UPDATE aprts_herbs
                SET source=%s, animDict=%s, animBody=%s, GatherTime=%s, failedText=%s, reward=%s
                WHERE id=%s
            """
            params = (source, animDict, animBody, gatherTime, failedText, reward_json, self.herb_id)
        else:
            query = """
                INSERT INTO aprts_herbs
                (source, animDict, animBody, globalBlock, GatherTime, failedText, text, reward)
                VALUES (%s, %s, %s, 0, %s, %s, 'Sebral jsi ', %s)
            """
            params = (source, animDict, animBody, gatherTime, failedText, reward_json)

        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")

