import os
from PyQt5 import QtWidgets, QtGui, QtCore
from urllib.request import urlopen, Request

def get_item_image_label(item_name, cache_dir, connection):
        # Vytvoříme název souboru pro cache
        cache_file_path = os.path.join(cache_dir, f"{item_name}.png")

        # Zkontrolujeme, zda soubor existuje v cache
        if os.path.exists(cache_file_path):
            # Načteme obrázek z cache
            pixmap = QtGui.QPixmap(cache_file_path)
        else:
            # Pokud není v cache, stáhneme obrázek a uložíme ho
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT image FROM items WHERE item = %s", (item_name,))
            result = cursor.fetchone()
            if result and result.get('image'):
                image_file = result['image']
                url = f"https://api.westhavenrp.cz/storage/items/{image_file}"
                try:
                    from urllib.request import urlopen, Request
                    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    data = urlopen(req).read()
                    # Uložíme data do souboru
                    with open(cache_file_path, 'wb') as f:
                        f.write(data)
                    pixmap = QtGui.QPixmap()
                    pixmap.loadFromData(data)
                except Exception as e:
                    print(f"Error loading image for {item_name}: {e}")
                    pixmap = None
            else:
                print(f"No image found for item {item_name}")
                pixmap = None

        label = QtWidgets.QLabel()
        if pixmap:
            label.setPixmap(pixmap)
        else:
            label.setText('No Image')
        label.setFixedSize(64, 64)
        label.setScaledContents(True)
        label.setAlignment(QtCore.Qt.AlignCenter)
        return label