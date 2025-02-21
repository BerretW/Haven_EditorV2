import sys
import json
import re
from PyQt5 import QtWidgets, QtGui, QtCore

from item_manager import ItemSelectionDialog  # Importujeme ItemSelectionDialog
import mysql.connector
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class BookDialog(QtWidgets.QDialog):
    def __init__(self, connection, book_id=None):
        super().__init__()
        self.connection = connection
        self.book_id = book_id
        self.setWindowTitle("Kniha")
        self.load_stylesheet(os.path.join(BASE_DIR, "stylesheet.qss"))
        self.item_code = None
        self.init_ui()
        if self.book_id:
            self.load_book()
    def load_stylesheet(self, filepath):
        """Načte stylesheet z externího souboru."""
        try:
            with open(filepath, "r") as file:
                self.setStyleSheet(file.read())
        except Exception as e:
            print(f"Chyba při načítání stylů: {e}")
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_layout = QtWidgets.QFormLayout()

        # Pole pro název knihy
        self.title_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Název:", self.title_edit)

        # Pole pro autora
        self.author_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Autor:", self.author_edit)

        # Pole pro PDF URL
        self.pdf_url_edit = QtWidgets.QLineEdit()
        form_layout.addRow("PDF URL:", self.pdf_url_edit)

        # Pole pro výběr položky
        self.item_edit = QtWidgets.QLineEdit()
        self.item_edit.setReadOnly(True)
        self.select_item_button = QtWidgets.QPushButton("Vybrat Item")
        self.select_item_button.clicked.connect(self.select_item)
        self.create_item_button = QtWidgets.QPushButton("Vytvořit Nový Item")
        self.create_item_button.clicked.connect(self.create_new_item)

        item_layout = QtWidgets.QHBoxLayout()
        item_layout.addWidget(self.item_edit)
        item_layout.addWidget(self.select_item_button)
        item_layout.addWidget(self.create_item_button)

        form_layout.addRow("Item:", item_layout)

        layout.addLayout(form_layout)

        # Tlačítka
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.save_book)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_book(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM books WHERE id = %s", (self.book_id,))
        book = cursor.fetchone()
        if book:
            self.title_edit.setText(book['title'])
            self.author_edit.setText(book['author'])
            self.pdf_url_edit.setText(book['pdf_url'])
            self.item_edit.setText(book['item'])
            self.item_code = book['item']

    def select_item(self):
        # Použijeme ItemSelectionDialog z item_manager.py
        dialog = ItemSelectionDialog(self.connection, single_selection=True)
        if dialog.exec_():
            selected_items = dialog.selected_items
            if selected_items:
                self.item_code = selected_items[0]['item']
                self.item_edit.setText(self.item_code)

    def create_new_item(self):
        cursor = self.connection.cursor()

        # Získáme existující položky s prefixem 'book_'
        query = "SELECT item FROM items WHERE item LIKE 'book_%'"
        cursor.execute(query)
        existing_items = cursor.fetchall()

        # Extrahujeme čísla z názvů položek
        pattern = re.compile(r'book_(\d+)')
        existing_numbers = []
        for (item_name,) in existing_items:
            match = pattern.fullmatch(item_name)
            if match:
                existing_numbers.append(int(match.group(1)))

        # Určíme další dostupné číslo
        next_number = 1
        if existing_numbers:
            next_number = max(existing_numbers) + 1

        # Získáme název knihy pro label
        new_item_label = self.title_edit.text().strip() or "Nová Kniha"
        new_item_name = f"book_{next_number}"

        # Vložíme nový item do databáze
        insert_query = """
            INSERT INTO items (item, label, weight, `limit`, usable, metadata) VALUES (%s, %s, %s, %s, %s, %s)
        """
        metadata = {
            'type': 'book',
            'title': self.title_edit.text().strip(),
            'author': self.author_edit.text().strip(),
            'pdf_url': self.pdf_url_edit.text().strip()
        }
        meta_json = json.dumps(metadata)
        params = (new_item_name, new_item_label, 1, 10, 1, meta_json)
        try:
            cursor.execute(insert_query, params)
            self.connection.commit()
            self.item_code = new_item_name
            self.item_edit.setText(self.item_code)
            QtWidgets.QMessageBox.information(self, "Úspěch", f"Nový item '{new_item_name}' byl vytvořen.")
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při vytváření itemu: {err}")

    def save_book(self):
        title = self.title_edit.text().strip()
        author = self.author_edit.text().strip()
        pdf_url = self.pdf_url_edit.text().strip()
        item_code = self.item_code or ''

        if not title:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'Název' nesmí být prázdné.")
            return
        if not author:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'Autor' nesmí být prázdné.")
            return
        if not pdf_url:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Pole 'PDF URL' nesmí být prázdné.")
            return

        cursor = self.connection.cursor()
        if self.book_id:
            query = """
                UPDATE books SET
                title=%s, author=%s, pdf_url=%s, item=%s
                WHERE id=%s
            """
            params = (title, author, pdf_url, item_code, self.book_id)
        else:
            query = """
                INSERT INTO books
                (title, author, pdf_url, item)
                VALUES (%s, %s, %s, %s)
            """
            params = (title, author, pdf_url, item_code)
        try:
            cursor.execute(query, params)
            self.connection.commit()
            self.accept()
        except mysql.connector.Error as err:
            QtWidgets.QMessageBox.critical(self, "Chyba", f"Nastala chyba při ukládání: {err}")
