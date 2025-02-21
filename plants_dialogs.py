import json
from PyQt5 import QtWidgets, QtCore
import mysql.connector
from item_manager import ItemSelectionDialog  # (uvedený níže)
class LandTypesDialog(QtWidgets.QDialog):
    """
    Jednoduchý dialog pro úpravu seznamu landTypes (list of string).
    """
    def __init__(self, land_types=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LandTypes (seznam)")
        self.land_types = land_types or []
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.list_widget = QtWidgets.QListWidget()
        layout.addWidget(self.list_widget)

        # Naplníme listWidget
        for lt in self.land_types:
            self.list_widget.addItem(lt)

        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Přidat")
        self.remove_btn = QtWidgets.QPushButton("Odebrat")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        layout.addLayout(btn_layout)

        # Tlačítka OK / Cancel
        ok_cancel = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal
        )
        ok_cancel.accepted.connect(self.accept)
        ok_cancel.rejected.connect(self.reject)
        layout.addWidget(ok_cancel)

        self.add_btn.clicked.connect(self.on_add)
        self.remove_btn.clicked.connect(self.on_remove)

    def on_add(self):
        text, ok = QtWidgets.QInputDialog.getText(
            self, "Přidat LandType", "Zadejte nový typ (řetězec):"
        )
        if ok and text.strip():
            self.list_widget.addItem(text.strip())

    def on_remove(self):
        items = self.list_widget.selectedItems()
        for it in items:
            row = self.list_widget.row(it)
            self.list_widget.takeItem(row)

    def accept(self):
        # Uložíme do self.land_types
        self.land_types = []
        for i in range(self.list_widget.count()):
            val = self.list_widget.item(i).text()
            self.land_types.append(val)
        super().accept()

    def get_land_types(self):
        return self.land_types


class RewardItemEditor(QtWidgets.QDialog):
    """
    Dialog pro přidání / úpravu položky v reward,
    kde se místo prostého textového pole pro "name" použije `ItemSelectionDialog`.
    """
    def __init__(self, data=None, parent=None, connection=None):
        """
        data = {"name":"...", "quantity":...}
        pokud je None, vytvoříme prázdný.
        connection = pro ItemSelectionDialog
        """
        super().__init__(parent)
        self.setWindowTitle("Položka v Reward")
        self.data = data or {}
        self.connection = connection
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        # Tlačítka pro výběr itemu
        self.item_label = QtWidgets.QLabel("Žádný item")
        self.select_item_btn = QtWidgets.QPushButton("Vybrat Item")

        self.select_item_btn.clicked.connect(self.select_item)

        item_layout = QtWidgets.QHBoxLayout()
        item_layout.addWidget(self.item_label)
        item_layout.addWidget(self.select_item_btn)

        self.quantity_spin = QtWidgets.QSpinBox()
        self.quantity_spin.setRange(0, 9999)

        # Předvyplnění:
        if "name" in self.data:
            self.item_label.setText(self.data["name"])
        if "quantity" in self.data:
            self.quantity_spin.setValue(self.data["quantity"])

        layout.addRow("Item (ze seznamu):", item_layout)
        layout.addRow("Množství:", self.quantity_spin)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self
        )
        btns.accepted.connect(self.accept_data)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def select_item(self):
        """Otevře ItemSelectionDialog a uloží vybraný item do self.data["name"]."""
        if not self.connection:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Chybí připojení k databázi.")
            return
        dlg = ItemSelectionDialog(self.connection, single_selection=True)
        if dlg.exec_():
            items = dlg.selected_items
            if items:
                chosen = items[0]
                self.data["name"] = chosen["item"]
                # Zkusit získat label pro zobrazení:
                label_show = f"{chosen['label']} ({chosen['item']})" if chosen.get('label') else chosen['item']
                self.item_label.setText(label_show)

    def accept_data(self):
        if "name" not in self.data or not self.data["name"]:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Vyberte item.")
            return
        q_val = self.quantity_spin.value()
        self.data["quantity"] = q_val
        self.accept()

    def get_data(self):
        return self.data