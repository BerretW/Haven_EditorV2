import sys
import os
import webbrowser
from PyQt5 import QtWidgets, QtGui, QtCore
import mysql.connector
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from book_dialog import BookDialog
from item_manager import ItemDialog
from image_utils import get_item_image_label

class BookManager(QtWidgets.QDialog):
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.setWindowTitle("Správa Knih")
        self.setGeometry(100, 100, 1000, 600)
        self.load_stylesheet(os.path.join(BASE_DIR, "stylesheet.qss"))
        self.cache_dir = 'cache'  # Adresář pro cache obrázků
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.init_ui()
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

        # Vyhledávací pole
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Vyhledávání:")
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Zadejte hledaný text...")
        self.search_edit.returnPressed.connect(self.load_books)
        search_button = QtWidgets.QPushButton("Vyhledat")
        search_button.clicked.connect(self.load_books)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(search_button)

        # Přidáme filtr podle toho, zda kniha má item
        filter_layout = QtWidgets.QHBoxLayout()
        filter_label = QtWidgets.QLabel("Filtr:")
        self.filter_combo = QtWidgets.QComboBox()
        self.filter_combo.addItems(["Všechny knihy", "Knihy s itemem", "Knihy bez itemu"])
        self.filter_combo.currentIndexChanged.connect(self.load_books)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_combo)

        # Přidáme vyhledávací pole a filtr do hlavního layoutu
        layout.addLayout(search_layout)
        layout.addLayout(filter_layout)

        # Tabulka knih
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(['Obrázek', 'ID', 'Item', 'Název', 'Autor', 'PDF URL', 'Akce'])
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # Tlačítka
        buttons_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Přidat Knihu")
        add_button.setStyleSheet("background-color: #5cb85c; color: white;")
        add_button.clicked.connect(self.add_book)
        refresh_button = QtWidgets.QPushButton("Obnovit")
        refresh_button.setStyleSheet("background-color: #5bc0de; color: white;")
        refresh_button.clicked.connect(self.load_books)
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(refresh_button)
        layout.addLayout(buttons_layout)

        self.load_books()

    def load_books(self):
        search_text = self.search_edit.text().strip()
        filter_option = self.filter_combo.currentIndex()
        cursor = self.connection.cursor(dictionary=True)
        params = []
        conditions = []
        if search_text:
            conditions.append("(title LIKE %s OR author LIKE %s OR item LIKE %s)")
            search_pattern = f"%{search_text}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        # Aplikace filtru podle výběru
        if filter_option == 1:
            # Knihy s itemem
            conditions.append("item IS NOT NULL AND item != ''")
        elif filter_option == 2:
            # Knihy bez itemu
            conditions.append("(item IS NULL OR item = '')")

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"""
            SELECT * FROM books
            {where_clause}
            ORDER BY title
        """
        cursor.execute(query, params)
        books = cursor.fetchall()
        self.table.setRowCount(0)
        for row_number, book in enumerate(books):
            self.table.insertRow(row_number)

            # Obrázek položky
            item_code = book['item']
            image_label = get_item_image_label(item_code, self.cache_dir, self.connection)
            self.table.setCellWidget(row_number, 0, image_label)

            # ID
            id_item = QtWidgets.QTableWidgetItem(str(book['id']))
            id_item.setFlags(id_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 1, id_item)

            # Item
            item_item = QtWidgets.QTableWidgetItem(book['item'])
            item_item.setFlags(item_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 2, item_item)

            # Název
            title_item = QtWidgets.QTableWidgetItem(book['title'])
            title_item.setFlags(title_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 3, title_item)

            # Autor
            author_item = QtWidgets.QTableWidgetItem(book['author'])
            author_item.setFlags(author_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 4, author_item)

            # PDF URL
            pdf_url_item = QtWidgets.QTableWidgetItem(book['pdf_url'])
            pdf_url_item.setFlags(pdf_url_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row_number, 5, pdf_url_item)

            # Akce
            action_widget = self.create_action_buttons(book['id'], book['item'], book['pdf_url'])
            self.table.setCellWidget(row_number, 6, action_widget)

            # Nastavíme výšku řádku
            self.table.setRowHeight(row_number, 64)

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(5, 200)
        self.table.setColumnWidth(6, 200)

    def create_action_buttons(self, book_id, item_name, pdf_url):
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Tlačítko Otevřít PDF
        open_pdf_button = QtWidgets.QPushButton("Otevřít PDF")
        open_pdf_button.setStyleSheet("background-color: #f0ad4e; color: white;")
        open_pdf_button.clicked.connect(lambda _, url=pdf_url: self.open_pdf(url))
        h_layout.addWidget(open_pdf_button)

        # Tlačítko Upravit
        edit_button = QtWidgets.QPushButton("Upravit")
        edit_button.setStyleSheet("background-color: #5cb85c; color: white;")
        edit_button.clicked.connect(lambda _, bid=book_id: self.edit_book_by_id(bid))
        h_layout.addWidget(edit_button)

        # Tlačítko Upravit Item
        edit_item_button = QtWidgets.QPushButton("Upravit Item")
        edit_item_button.setStyleSheet("background-color: #5bc0de; color: white;")
        edit_item_button.clicked.connect(lambda _, name=item_name: self.edit_item_by_name(name))
        h_layout.addWidget(edit_item_button)

        # Tlačítko Smazat
        delete_button = QtWidgets.QPushButton("Smazat")
        delete_button.setStyleSheet("background-color: #d9534f; color: white;")
        delete_button.clicked.connect(lambda _, bid=book_id: self.delete_book_by_id(bid))
        h_layout.addWidget(delete_button)

        widget.setLayout(h_layout)
        return widget

    def open_pdf(self, pdf_url):
        if pdf_url:
            webbrowser.open(pdf_url)
        else:
            QtWidgets.QMessageBox.warning(self, "Chyba", "URL PDF není dostupné.")

    def add_book(self):
        dialog = BookDialog(self.connection)
        if dialog.exec_():
            self.load_books()

    def edit_book_by_id(self, book_id):
        dialog = BookDialog(self.connection, book_id=book_id)
        if dialog.exec_():
            self.load_books()

    def edit_item_by_name(self, item_name):
        if not item_name:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Tato kniha nemá přiřazený item.")
            return
        dialog = ItemDialog(self.connection, item_name)
        if dialog.exec_():
            self.load_books()

    def delete_book_by_id(self, book_id):
        confirm = QtWidgets.QMessageBox.question(self, "Potvrdit smazání",
                                                 "Opravdu chcete smazat tuto knihu?",
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if confirm == QtWidgets.QMessageBox.Yes:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM books WHERE id = %s", (book_id,))
            self.connection.commit()
            self.load_books()

    def on_table_double_clicked(self, row, column):
        id_item = self.table.item(row, 1)  # Sloupec 1 je ID
        if id_item:
            book_id = int(id_item.text())
            self.edit_book_by_id(book_id)
