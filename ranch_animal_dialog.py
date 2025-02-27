import sys
import os
import json
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector

from ranch_animal_product_dialog import RanchAnimalProductDialog

class RanchAnimalDialog(QtWidgets.QDialog):
    def __init__(self, connection, animal_id=None):
        super().__init__()
        self.connection = connection
        self.animal_id = animal_id
        self.setWindowTitle("Rančové Zvíře")
        self.setGeometry(100, 100, 900, 900)
        self.init_ui()
        if self.animal_id:
            self.load_animal()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_layout = QtWidgets.QFormLayout()

        # Sloupce z aprts_ranch_config_animals
        self.name_edit = QtWidgets.QLineEdit()
        self.price_edit = QtWidgets.QSpinBox()
        self.price_edit.setRange(0, 999999)
        self.model_edit = QtWidgets.QLineEdit()
        self.m_model_edit = QtWidgets.QLineEdit()
        self.health_edit = QtWidgets.QSpinBox()
        self.health_edit.setRange(0, 999999)
        self.adultAge_edit = QtWidgets.QSpinBox()
        self.adultAge_edit.setRange(0, 999999)

        self.walkOnly_checkbox = QtWidgets.QCheckBox("WalkOnly (true/false)")

        self.offsetX_edit = QtWidgets.QDoubleSpinBox()
        self.offsetX_edit.setDecimals(3)
        self.offsetX_edit.setRange(-999999.0, 999999.0)
        self.offsetY_edit = QtWidgets.QDoubleSpinBox()
        self.offsetY_edit.setDecimals(3)
        self.offsetY_edit.setRange(-999999.0, 999999.0)
        self.offsetZ_edit = QtWidgets.QDoubleSpinBox()
        self.offsetZ_edit.setDecimals(3)
        self.offsetZ_edit.setRange(-999999.0, 999999.0)

        self.food_edit = QtWidgets.QSpinBox()
        self.food_edit.setRange(0, 999999)
        self.water_edit = QtWidgets.QSpinBox()
        self.water_edit.setRange(0, 999999)
        self.foodMax_edit = QtWidgets.QSpinBox()
        self.foodMax_edit.setRange(0, 999999)
        self.waterMax_edit = QtWidgets.QSpinBox()
        self.waterMax_edit.setRange(0, 999999)

        self.kibble_edit = QtWidgets.QLineEdit()
        self.kibbleFood_edit = QtWidgets.QSpinBox()
        self.kibbleFood_edit.setRange(0, 999999)

        self.poop_edit = QtWidgets.QLineEdit()
        self.poopChance_edit = QtWidgets.QDoubleSpinBox()
        self.poopChance_edit.setRange(0, 1)
        self.poopChance_edit.setDecimals(2)

        self.dieAge_edit = QtWidgets.QSpinBox()
        self.dieAge_edit.setRange(0, 999999)
        self.pregnancyTime_edit = QtWidgets.QSpinBox()
        self.pregnancyTime_edit.setRange(0, 999999)
        self.pregnancyChance_edit = QtWidgets.QSpinBox()
        self.pregnancyChance_edit.setRange(0, 100)
        self.noFuckTime_edit = QtWidgets.QSpinBox()
        self.noFuckTime_edit.setRange(0, 999999)

        # Přidáváme do form_layout
        form_layout.addRow("Jméno (name):", self.name_edit)
        form_layout.addRow("Cena (price):", self.price_edit)
        form_layout.addRow("Model (F):", self.model_edit)
        form_layout.addRow("Model (M):", self.m_model_edit)
        form_layout.addRow("Zdraví (health):", self.health_edit)
        form_layout.addRow("Věk dospělosti (adultAge):", self.adultAge_edit)
        form_layout.addRow("", self.walkOnly_checkbox)

        form_layout.addRow("offsetX:", self.offsetX_edit)
        form_layout.addRow("offsetY:", self.offsetY_edit)
        form_layout.addRow("offsetZ:", self.offsetZ_edit)

        form_layout.addRow("food:", self.food_edit)
        form_layout.addRow("water:", self.water_edit)
        form_layout.addRow("foodMax:", self.foodMax_edit)
        form_layout.addRow("waterMax:", self.waterMax_edit)

        form_layout.addRow("kibble:", self.kibble_edit)
        form_layout.addRow("kibbleFood:", self.kibbleFood_edit)

        form_layout.addRow("poop:", self.poop_edit)
        form_layout.addRow("poopChance:", self.poopChance_edit)

        form_layout.addRow("dieAge:", self.dieAge_edit)
        form_layout.addRow("pregnancyTime:", self.pregnancyTime_edit)
        form_layout.addRow("pregnancyChance:", self.pregnancyChance_edit)
        form_layout.addRow("noFuckTime:", self.noFuckTime_edit)

        layout.addLayout(form_layout)

        # Tabulka pro "produkty" (aprts_ranch_config_animal_products)
        self.products_table = QtWidgets.QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels(["ID", "Název", "Item", "Chance", "Akce"])
        self.products_table.setSortingEnabled(True)
        layout.addWidget(self.products_table)

        # Tlačítka pro produkty
        product_buttons_layout = QtWidgets.QHBoxLayout()
        add_product_button = QtWidgets.QPushButton("Přidat Produkt")
        add_product_button.setStyleSheet("background-color: #5cb85c; color: white;")
        add_product_button.clicked.connect(self.add_product)
        product_buttons_layout.addWidget(add_product_button)

        refresh_product_button = QtWidgets.QPushButton("Obnovit Produkty")
        refresh_product_button.setStyleSheet("background-color: #5bc0de; color: white;")
        refresh_product_button.clicked.connect(self.load_products)
        product_buttons_layout.addWidget(refresh_product_button)

        layout.addLayout(product_buttons_layout)

        # Dialogová tlačítka OK / Cancel
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self
        )
        buttons.accepted.connect(self.save_animal)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def fill_form_with_data(self, data_dict):
        """Vyplní QLineEdit/QSpinBox atp. hodnotami z data_dict (kromě ID)."""
        # Příklad:
        self.name_edit.setText(str(data_dict.get('name', '')))
        self.price_edit.setValue(data_dict.get('price', 0))
        self.model_edit.setText(data_dict.get('model', ''))
        self.m_model_edit.setText(data_dict.get('m_model', ''))
        self.health_edit.setValue(data_dict.get('health', 0))
        self.adultAge_edit.setValue(data_dict.get('adultAge', 0))
        self.walkOnly_checkbox.setChecked(bool(data_dict.get('WalkOnly', 0)))
        self.offsetX_edit.setValue(float(data_dict.get('offsetX', 0)))
        self.offsetY_edit.setValue(float(data_dict.get('offsetY', 0)))
        self.offsetZ_edit.setValue(float(data_dict.get('offsetZ', 0)))
        self.food_edit.setValue(data_dict.get('food', 0))
        self.water_edit.setValue(data_dict.get('water', 0))
        self.foodMax_edit.setValue(data_dict.get('foodMax', 0))
        self.waterMax_edit.setValue(data_dict.get('waterMax', 0))
        self.kibble_edit.setText(data_dict.get('kibble', ''))
        self.kibbleFood_edit.setValue(data_dict.get('kibbleFood', 0))
        self.poop_edit.setText(data_dict.get('poop', ''))
        self.poopChance_edit.setValue(float(data_dict.get('poopChance', 0)))
        self.dieAge_edit.setValue(data_dict.get('dieAge', 0))
        self.pregnancyTime_edit.setValue(data_dict.get('pregnancyTime', 0))
        self.pregnancyChance_edit.setValue(data_dict.get('pregnancyChance', 0))
        self.noFuckTime_edit.setValue(data_dict.get('noFuckTime', 0))


    def load_animal(self):
        """Načteme záznam z aprts_ranch_config_animals a zobrazíme."""
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM aprts_ranch_config_animals WHERE animal_id = %s", (self.animal_id,))
        animal = cursor.fetchone()
        if animal:
            self.name_edit.setText(animal['name'])
            self.price_edit.setValue(animal['price'])
            self.model_edit.setText(animal['model'])
            self.m_model_edit.setText(animal['m_model'])
            self.health_edit.setValue(animal['health'])
            self.adultAge_edit.setValue(animal['adultAge'])
            self.walkOnly_checkbox.setChecked(bool(animal['WalkOnly']))
            self.offsetX_edit.setValue(float(animal['offsetX']))
            self.offsetY_edit.setValue(float(animal['offsetY']))
            self.offsetZ_edit.setValue(float(animal['offsetZ']))
            self.food_edit.setValue(animal['food'])
            self.water_edit.setValue(animal['water'])
            self.foodMax_edit.setValue(animal['foodMax'])
            self.waterMax_edit.setValue(animal['waterMax'])
            self.kibble_edit.setText(animal['kibble'])
            self.kibbleFood_edit.setValue(animal['kibbleFood'])
            self.poop_edit.setText(animal['poop'])
            self.poopChance_edit.setValue(float(animal['poopChance']))
            self.dieAge_edit.setValue(animal['dieAge'])
            self.pregnancyTime_edit.setValue(animal['pregnancyTime'])
            self.pregnancyChance_edit.setValue(animal['pregnancyChance'])
            self.noFuckTime_edit.setValue(animal['noFuckTime'])

            self.load_products()

    def load_products(self):
        """Načte seznam produktů pro animal_id z tabulky aprts_ranch_config_animal_products."""
        if not self.animal_id:
            return
        cursor = self.connection.cursor(dictionary=True)
        query = """SELECT * FROM aprts_ranch_config_animal_products
                   WHERE animal_id = %s"""
        cursor.execute(query, (self.animal_id,))
        products = cursor.fetchall()

        self.products_table.setRowCount(0)
        for row_number, product in enumerate(products):
            self.products_table.insertRow(row_number)

            # ID
            id_item = QtWidgets.QTableWidgetItem(str(product['product_id']))
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.products_table.setItem(row_number, 0, id_item)

            # Název
            name_item = QtWidgets.QTableWidgetItem(product['name'])
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.products_table.setItem(row_number, 1, name_item)

            # Item
            item_item = QtWidgets.QTableWidgetItem(product['item'])
            item_item.setFlags(item_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.products_table.setItem(row_number, 2, item_item)

            # Chance
            chance_item = QtWidgets.QTableWidgetItem(str(product['chance']))
            chance_item.setFlags(chance_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.products_table.setItem(row_number, 3, chance_item)

            # Akce
            action_widget = self.create_product_action_buttons(product['product_id'])
            self.products_table.setCellWidget(row_number, 4, action_widget)

        self.products_table.resizeColumnsToContents()

    def create_product_action_buttons(self, product_id):
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Upravit
        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        edit_button.clicked.connect(lambda _, pid=product_id: self.edit_product_by_id(pid))
        h_layout.addWidget(edit_button)

        # Smazat
        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        delete_button.clicked.connect(lambda _, pid=product_id: self.delete_product_by_id(pid))
        h_layout.addWidget(delete_button)

        widget.setLayout(h_layout)
        return widget

    def add_product(self):
        if not self.animal_id:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Nejdřív uložte zvíře, abyste mohli přidávat produkty.")
            return
        dialog = RanchAnimalProductDialog(self.connection, animal_id=self.animal_id)
        if dialog.exec_():
            self.load_products()

    def edit_product_by_id(self, product_id):
        dialog = RanchAnimalProductDialog(self.connection, animal_id=self.animal_id, product_id=product_id)
        if dialog.exec_():
            self.load_products()

    def delete_product_by_id(self, product_id):
        confirm = QtWidgets.QMessageBox.question(
            self, "Potvrdit smazání",
            "Opravdu chcete smazat tento produkt?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM aprts_ranch_config_animal_products WHERE product_id = %s", (product_id,))
            self.connection.commit()
            self.load_products()

    def save_animal(self):
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'Jméno' nesmí být prázdné.")
            return

        price = self.price_edit.value()
        model = self.model_edit.text().strip()
        m_model = self.m_model_edit.text().strip()
        health = self.health_edit.value()
        adultAge = self.adultAge_edit.value()
        walkOnly = 1 if self.walkOnly_checkbox.isChecked() else 0
        offsetX = self.offsetX_edit.value()
        offsetY = self.offsetY_edit.value()
        offsetZ = self.offsetZ_edit.value()
        food = self.food_edit.value()
        water = self.water_edit.value()
        foodMax = self.foodMax_edit.value()
        waterMax = self.waterMax_edit.value()
        kibble = self.kibble_edit.text().strip()
        kibbleFood = self.kibbleFood_edit.value()
        poop = self.poop_edit.text().strip()
        poopChance = self.poopChance_edit.value()
        dieAge = self.dieAge_edit.value()
        pregnancyTime = self.pregnancyTime_edit.value()
        pregnancyChance = self.pregnancyChance_edit.value()
        noFuckTime = self.noFuckTime_edit.value()

        cursor = self.connection.cursor()
        if self.animal_id:
            query = """
                UPDATE aprts_ranch_config_animals
                SET name=%s, price=%s, model=%s, m_model=%s, health=%s, adultAge=%s,
                    WalkOnly=%s, offsetX=%s, offsetY=%s, offsetZ=%s,
                    food=%s, water=%s, foodMax=%s, waterMax=%s, kibble=%s, kibbleFood=%s,
                    poop=%s, poopChance=%s, dieAge=%s, pregnancyTime=%s, pregnancyChance=%s,
                    noFuckTime=%s
                WHERE animal_id=%s
            """
            params = (name, price, model, m_model, health, adultAge,
                      walkOnly, offsetX, offsetY, offsetZ,
                      food, water, foodMax, waterMax, kibble, kibbleFood,
                      poop, poopChance, dieAge, pregnancyTime, pregnancyChance,
                      noFuckTime,
                      self.animal_id)
        else:
            query = """
                INSERT INTO aprts_ranch_config_animals
                (name, price, model, m_model, health, adultAge,
                 WalkOnly, offsetX, offsetY, offsetZ,
                 food, water, foodMax, waterMax, kibble, kibbleFood,
                 poop, poopChance, dieAge, pregnancyTime, pregnancyChance, noFuckTime)
                VALUES (%s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s)
            """
            params = (name, price, model, m_model, health, adultAge,
                      walkOnly, offsetX, offsetY, offsetZ,
                      food, water, foodMax, waterMax, kibble, kibbleFood,
                      poop, poopChance, dieAge, pregnancyTime, pregnancyChance,
                      noFuckTime)

        try:
            cursor.execute(query, params)
            self.connection.commit()
            if not self.animal_id:
                # Získáme nově vložené animal_id
                self.animal_id = cursor.lastrowid
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")
