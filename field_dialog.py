import json
import os
import re
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def decode_if_bytes(value):
    """
    Pokud je value typu bytes, dekóduje ho na str (UTF-8).
    Pokud je None nebo str, vrátí se tak, jak je.
    """
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return value


class HerbSelectionDialog(QtWidgets.QDialog):
    """
    Minimalistický dialog pro výběr bylinky (ze sloupce 'id' a 'source' v aprts_herbs).
    Po potvrzení (OK) uloží vybraný řádek do self.selected_herb (dict).
    """

    def __init__(self, connection, parent=None):
        super().__init__(parent)
        self.connection = connection
        self.setWindowTitle("Vybrat Bylinku")
        self.resize(400, 300)
        self.load_stylesheet(os.path.join(BASE_DIR, "stylesheet.qss"))
        self.selected_herb = None  # Tady se uloží vybraný záznam

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["ID", "source"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        self.table.doubleClicked.connect(self.accept_selection)
        layout.addWidget(self.table)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self
        )
        btns.accepted.connect(self.accept_selection)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.load_herbs()

    def load_stylesheet(self, filepath):
        """Načte stylesheet z externího souboru."""
        try:
            with open(filepath, "r") as file:
                self.setStyleSheet(file.read())
        except Exception as e:
            print(f"Chyba při načítání stylů: {e}")

    def load_herbs(self):
        """Načte data z aprts_herbs a naplní tabulku."""
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT id, source FROM aprts_herbs")
        herbs = cursor.fetchall()

        self.table.setRowCount(0)
        for row_number, herb in enumerate(herbs):
            self.table.insertRow(row_number)

            # ID do prvního sloupce
            id_item = QtWidgets.QTableWidgetItem(str(herb["id"]))
            # Schováme si celý záznam (dict) do UserRole
            id_item.setData(QtCore.Qt.UserRole, herb)
            self.table.setItem(row_number, 0, id_item)

            # source do druhého sloupce (dekódovat, pokud bytes)
            source_str = decode_if_bytes(herb["source"]) or ""
            source_item = QtWidgets.QTableWidgetItem(source_str)
            self.table.setItem(row_number, 1, source_item)

        self.table.resizeColumnsToContents()

    def accept_selection(self):
        """
        Při kliknutí na OK nebo doubleclick získáme vybraný řádek,
        vytáhneme z UserRole herb dict a uložíme do self.selected_herb.
        """
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Nic není vybráno.")
            return

        row = selected_rows[0].row()
        id_item = self.table.item(row, 0)
        if not id_item:
            return

        # slovník s celým záznamem
        herb_data = id_item.data(QtCore.Qt.UserRole)
        self.selected_herb = herb_data
        self.accept()

    def get_selected_herb(self):
        """Vrací vybraný záznam (dict) z tabulky aprts_herbs nebo None."""
        return self.selected_herb


class AddPropDialog(QtWidgets.QDialog):
    """
    Jednoduchý dialog pro přidání/editaci jedné položky do `props`.
    Např. {"name": "Heřmánek", "prop": "mp005_s_inv_chocdaisy01dx", "chance":70}.
    """

    def __init__(self, prop_data=None, parent=None, connection=None):
        """
        prop_data je dict:
          {
            "name": ...,
            "prop": ...,
            "chance": ...
          }
        Pokud je None, je to nová položka.
        connection může být využito pro HerbSelectionDialog, 
        pokud chcete přebírat data z aprts_herbs.
        """
        super().__init__(parent)
        self.setWindowTitle("Přidat / Upravit Prop")
        self.connection = connection  # Může být None, pokud nepotřebujeme
        self.prop_data = prop_data or {}
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        self.name_edit = QtWidgets.QLineEdit()
        self.prop_edit = QtWidgets.QLineEdit()
        self.chance_spin = QtWidgets.QSpinBox()
        self.chance_spin.setRange(0, 100)
        self.chance_spin.setValue(70)

        if "name" in self.prop_data:
            self.name_edit.setText(str(self.prop_data["name"]))
        if "prop" in self.prop_data:
            self.prop_edit.setText(str(self.prop_data["prop"]))
        if "chance" in self.prop_data:
            self.chance_spin.setValue(self.prop_data["chance"])

        # Tlačítko pro vybrání bylinky (pokud chceme)
        self.select_herb_button = QtWidgets.QPushButton("Vybrat Bylinku…")
        self.select_herb_button.clicked.connect(self.select_herb)
        # Ale tlačítko zobrazíme jen tehdy, pokud máme self.connection
        if not self.connection:
            self.select_herb_button.setEnabled(False)

        layout.addRow("Název:", self.name_edit)
        layout.addRow("Prop (model):", self.prop_edit)
        layout.addRow("", self.select_herb_button)  # Tlačítko pod "prop"
        layout.addRow("Šance (%):", self.chance_spin)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self
        )
        btns.accepted.connect(self.accept_data)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def select_herb(self):
        """Otevře HerbSelectionDialog, abychom mohli nastavit např. prop z bylinky."""
        if not self.connection:
            QtWidgets.QMessageBox.warning(
                self, "Chyba", "Není k dispozici DB connection.")
            return

        dlg = HerbSelectionDialog(self.connection, self)
        if dlg.exec_():
            selected_herb = dlg.get_selected_herb()
            if selected_herb:
                # Např. do self.prop_edit dáme selected_herb["source"]
                prop_val = decode_if_bytes(selected_herb["source"])
                self.prop_edit.setText(prop_val or "")
                # Případně můžeme i name_edit vyplnit
                # self.name_edit.setText(f"Bylinka: {prop_val}")

    def accept_data(self):
        """Při odkliknutí OK zkontrolujeme vyplnění a uložíme do self.prop_data."""
        name_str = self.name_edit.text().strip()
        prop_str = self.prop_edit.text().strip()
        chance_val = self.chance_spin.value()

        # Minimální validace
        if not prop_str:
            QtWidgets.QMessageBox.warning(
                self, "Chyba", "Pole 'Prop' nesmí být prázdné.")
            return

        self.prop_data["name"] = name_str
        self.prop_data["prop"] = prop_str
        self.prop_data["chance"] = chance_val

        self.accept()

    def get_prop_data(self):
        """Vrací finální dict pro jednu položku v `props`."""
        return self.prop_data


class FieldDialog(QtWidgets.QDialog):
    def __init__(self, connection, field_id=None):
        super().__init__()
        self.connection = connection
        self.field_id = field_id
        self.setWindowTitle("Pole (Herb Field)")

        # V paměti držíme props jako list of dict
        self.props = []

        self.init_ui()
        if self.field_id:
            self.load_field()

    def init_ui(self):
        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        self.name_edit = QtWidgets.QLineEdit()
        self.blip_edit = QtWidgets.QLineEdit()
        self.coords_edit = QtWidgets.QLineEdit()  # Změněno na QLineEdit pro vector3
        self.size_edit = QtWidgets.QSpinBox()
        self.size_edit.setRange(1, 999999)
        self.limit_edit = QtWidgets.QSpinBox()
        self.limit_edit.setRange(1, 999999)

        layout.addRow("Název:", self.name_edit)
        layout.addRow("Blip:", self.blip_edit)
        layout.addRow("coords (vector3):", self.coords_edit)
        layout.addRow("size:", self.size_edit)
        layout.addRow("limit:", self.limit_edit)

        # --- props jako list of dict ---
        props_layout = QtWidgets.QVBoxLayout()
        props_label = QtWidgets.QLabel("Props (seznam):")
        props_layout.addWidget(props_label)

        self.props_list = QtWidgets.QListWidget()
        self.props_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.props_list.customContextMenuRequested.connect(
            self.show_props_context_menu)
        props_layout.addWidget(self.props_list)

        props_btns_layout = QtWidgets.QHBoxLayout()
        add_prop_btn = QtWidgets.QPushButton("Přidat Prop")
        add_prop_btn.setStyleSheet("background-color: #5cb85c; color: white;")
        add_prop_btn.clicked.connect(self.add_prop)

        remove_prop_btn = QtWidgets.QPushButton("Odebrat Prop")
        remove_prop_btn.setStyleSheet(
            "background-color: #d9534f; color: white;")
        remove_prop_btn.clicked.connect(self.remove_selected_props)

        props_btns_layout.addWidget(add_prop_btn)
        props_btns_layout.addWidget(remove_prop_btn)
        props_layout.addLayout(props_btns_layout)

        layout.addRow(props_layout)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self
        )
        buttons.accepted.connect(self.save_field)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------
    #  Parsování vector3() ↔ JSON objekt {x,y,z}
    # ------------------------------------------------------------
    def parse_vector3_to_dict(self, vector_str):
        """
        Převede string ve formátu 'vector3(x, y, z)' na dict {"x":x, "y":y, "z":z}.
        Např. "vector3(-1.23, 456.789, 0.0)" -> {"x":-1.23, "y":456.789, "z":0.0}
        """
        pattern = r"vector3\s*\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)"
        match = re.match(pattern, vector_str)
        if not match:
            return None
        x_str, y_str, z_str = match.groups()
        return {
            "x": float(x_str),
            "y": float(y_str),
            "z": float(z_str)
        }

    def format_dict_to_vector3(self, coords_dict):
        """
        Převede dict {"x":..., "y":..., "z":...} na string 'vector3(x, y, z)'.
        Např. {"x":-1.23,"y":456.78,"z":0.0} -> "vector3(-1.23, 456.78, 0.0)"
        """
        if not isinstance(coords_dict, dict):
            return ""
        if not all(k in coords_dict for k in ("x", "y", "z")):
            return ""
        x = coords_dict["x"]
        y = coords_dict["y"]
        z = coords_dict["z"]
        return f"vector3({x}, {y}, {z})"

    # ------------------------------------------------------------
    #  Správa props
    # ------------------------------------------------------------
    def show_props_context_menu(self, position):
        """Kontextové menu pro 'props_list' (úprava chance, smazání, atp.)."""
        menu = QtWidgets.QMenu()
        edit_chance_action = menu.addAction("Změnit Šanci")
        remove_action = menu.addAction("Odebrat Prop")

        action = menu.exec_(self.props_list.viewport().mapToGlobal(position))
        if not action:
            return

        selected = self.props_list.selectedItems()
        if not selected:
            return

        row_idx = self.props_list.row(selected[0])
        prop_obj = self.props[row_idx]

        if action == remove_action:
            self.props.pop(row_idx)
            self.update_props_list()
        elif action == edit_chance_action:
            old_chance = prop_obj.get("chance", 100)
            new_chance, ok = QtWidgets.QInputDialog.getInt(
                self, "Změnit Šanci", "Zadejte novou šanci (0-100):",
                value=old_chance, min=0, max=100
            )
            if ok:
                prop_obj["chance"] = new_chance
                self.update_props_list()

    def add_prop(self):
        """Otevře AddPropDialog pro přidání nového 'prop' záznamu."""
        dlg = AddPropDialog(prop_data=None, parent=self,
                            connection=self.connection)
        if dlg.exec_():
            data = dlg.get_prop_data()  # dict
            self.props.append(data)
            self.update_props_list()

    def remove_selected_props(self):
        """Odstraní vybrané položky v self.props_list i v self.props."""
        selected = self.props_list.selectedItems()
        if not selected:
            QtWidgets.QMessageBox.warning(
                self, "Chyba", "Nic není vybráno k odebrání.")
            return
        for item in selected:
            row_idx = self.props_list.row(item)
            self.props.pop(row_idx)
        self.update_props_list()

    def update_props_list(self):
        """Zobrazí self.props v QListWidget."""
        self.props_list.clear()
        for obj in self.props:
            # Např. {"name":"Heřmánek","prop":"mp005_s_inv_chocdaisy01dx","chance":70}
            name_str = obj.get("name", "???")
            prop_str = obj.get("prop", "???")
            chance_val = obj.get("chance", 100)
            item_txt = f"{name_str} | prop: {prop_str} | chance: {chance_val}%"
            self.props_list.addItem(item_txt)

    # ------------------------------------------------------------
    #  Načtení a uložení pole
    # ------------------------------------------------------------
    def load_field(self):
        """Načte pole z DB a naplní GUI."""
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM aprts_herbs_fields WHERE id=%s", (self.field_id,))
        field = cursor.fetchone()
        if field:
            self.name_edit.setText(decode_if_bytes(field["name"]) or "")
            self.blip_edit.setText(decode_if_bytes(field["blip"]) or "")

            # coords je uložen jako JSON objekt { "x":..., "y":..., "z":...}
            coords_str = decode_if_bytes(field["coords"]) or ""
            coords_str = coords_str.strip()

            if not coords_str:
                # Když je to prázdné
                self.coords_edit.setText("vector3(0.0, 0.0, 0.0)")
            else:
                # Zkusit parse jako JSON (objekt {x,y,z})
                try:
                    coords_dict = json.loads(coords_str)
                    # Může to být dict {x,y,z}
                    if isinstance(coords_dict, dict) and all(k in coords_dict for k in ("x", "y", "z")):
                        # převedeme na string "vector3(x, y, z)"
                        vect_str = self.format_dict_to_vector3(coords_dict)
                        self.coords_edit.setText(
                            vect_str or "vector3(0.0, 0.0, 0.0)")
                    else:
                        # Když je to cokoliv jiného
                        self.coords_edit.setText("vector3(0.0, 0.0, 0.0)")
                except json.JSONDecodeError:
                    # Pokud to není validní JSON, zkusíme, jestli to už není vector3 string
                    self.coords_edit.setText(coords_str)

            self.size_edit.setValue(field["size"])
            self.limit_edit.setValue(field["limit"])
            objects_str = decode_if_bytes(field["objects"]) or "[]"

            # Převedeme props_str na list of dict
            props_str = decode_if_bytes(field["props"]) or "[]"
            try:
                props_data = json.loads(props_str)
                if isinstance(props_data, list):
                    self.props = props_data
                else:
                    self.props = []
            except json.JSONDecodeError:
                self.props = []
            self.update_props_list()

    def save_field(self):
        """Uloží pole do DB."""
        name = self.name_edit.text().strip()
        blip = self.blip_edit.text().strip()
        coords_input = self.coords_edit.text().strip()
        size_val = self.size_edit.value()
        limit_val = self.limit_edit.value()
        objects_txt = "[]"

        # Z props sestavíme JSON
        props_str = json.dumps(self.props, ensure_ascii=False)

        # Koordináty - chceme ukládat jako JSON objekt {x,y,z}.
        # Zkusíme parse_vector3_to_dict
        coords_dict = self.parse_vector3_to_dict(coords_input)
        if coords_dict:
            # Máme vector3(...) => uložíme do DB jako dict
            coords_json_str = json.dumps(coords_dict)
        else:
            # Není to vector3(...), tak zkusíme přímo JSON
            # Např. {"x":..., "y":..., "z":...}
            try:
                coords_test = json.loads(coords_input)
                # Ověříme, zda je to dict s klíči x,y,z
                if isinstance(coords_test, dict) and all(k in coords_test for k in ("x", "y", "z")):
                    coords_json_str = coords_input  # Ok, ponecháme tak, jak je
                else:
                    QtWidgets.QMessageBox.warning(
                        self, "Chyba",
                        "coords musí být ve formátu 'vector3(x, y, z)' nebo validní JSON objekt {\"x\":..., \"y\":..., \"z\":...}."
                    )
                    return
            except json.JSONDecodeError:
                QtWidgets.QMessageBox.warning(
                    self, "Chyba",
                    "coords musí být ve formátu 'vector3(x, y, z)' nebo validní JSON objekt {\"x\":..., \"y\":..., \"z\":...}."
                )
                return

        # Ověříme JSON v objects_txt
        def check_json(s, field_name):
            if not s:
                return True
            try:
                json.loads(s)
                return True
            except json.JSONDecodeError as e:
                QtWidgets.QMessageBox.warning(
                    self, "Chyba", f"{field_name} musí být validní JSON.\n{e}")
                return False

        if not check_json(objects_txt, "objects"):
            return

        cursor = self.connection.cursor()
        if self.field_id:
            query = """
                UPDATE aprts_herbs_fields
                SET name=%s, blip=%s, coords=%s, size=%s, `limit`=%s, objects=%s, props=%s
                WHERE id=%s
            """
            params = (name, blip, coords_json_str, size_val,
                      limit_val, objects_txt, props_str, self.field_id)
        else:
            query = """
                INSERT INTO aprts_herbs_fields (name, blip, coords, size, `limit`, num, objects, props)
                VALUES (%s, %s, %s, %s, %s, 0, %s, %s)
            """
            params = (name, blip, coords_json_str, size_val,
                      limit_val, objects_txt, props_str)

        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(
                self, "Chyba", f"Nastala chyba při ukládání: {err}")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    try:
        connection = mysql.connector.connect(
            host='db-server.kkrp.cz',
            user='spoiledmouse',
            password='bE8e7AqiG8w43itITaf361Bu8182Ku*',
            database='s29_dev-redm'
        )
    except mysql.connector.Error as err:
        print(f"Chyba při připojování k databázi: {err}")
        sys.exit(1)

    dialog = FieldDialog(connection=connection, field_id=4)
    if dialog.exec_():
        print("Pole bylo úspěšně uloženo.")
    else:
        print("Ukládání pole bylo zrušeno.")

    connection.close()
    sys.exit(0)
