from PyPDF2 import PdfMerger
import os
import sys
import json
import mysql.connector

from graphviz import Digraph
from itertools import cycle

# Cesta k souboru config.json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(BASE_DIR, 'config.json')
image_cache_dir = os.path.join(BASE_DIR, 'item_images')

def load_config():
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config

def create_db_connection(config):
    print("Connecting to database...")
    try:
        connection = mysql.connector.connect(
            host=config['mysql']['host'],
            user=config['mysql']['user'],
            password=config['mysql']['password'],
            database=config['mysql']['database']
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        sys.exit(1)

def get_recipes(connection):
    cursor = connection.cursor(dictionary=True)
    query = """
        SELECT r.id, r.name, r.type, r.prop, r.triggerItem, r.result, r.materials, r.meta,
               r.category_id, rc.name AS category_name, i.label AS result_label, i.image AS result_image
        FROM recipes r
        LEFT JOIN recipes_category rc ON r.category_id = rc.ID
        LEFT JOIN items i ON JSON_UNQUOTE(JSON_EXTRACT(r.result, '$.item')) = i.item
    """
    cursor.execute(query)
    recipes = cursor.fetchall()
    return recipes

def get_longcraft_recipes(connection):
    cursor = connection.cursor(dictionary=True)
    query = """
        SELECT id, name, reward, count, time, prop, job, recipe
        FROM aprts_longCraft_recipes
    """
    cursor.execute(query)
    longcraft_recipes = cursor.fetchall()
    return longcraft_recipes

def parse_materials(materials_json):
    try:
        materials = json.loads(materials_json)
        items = []
        if isinstance(materials, dict):
            # Formát {"item": count}
            for item_name, count in materials.items():
                label = f"{item_name} x{count}"
                items.append({'item_name': item_name, 'label': label, 'count': count}) # Přidáno 'count'
        elif isinstance(materials, list):
            # Formát [{"item": "item_name", "count": count}, ...]
            for material in materials:
                item_name = material.get('item')
                count = material.get('count', 1)
                label = f"{item_name} x{count}"
                items.append({'item_name': item_name, 'label': label, 'count': count}) # Přidáno 'count'
        return items
    except json.JSONDecodeError:
        return []

def parse_longcraft_materials(recipe_json):
    try:
        recipe = json.loads(recipe_json)
        items = []
        for slot, materials in recipe.items():
            for item_name, count in materials.items():
                label = f"{item_name} x{count} (Slot {slot})"
                items.append({'item_name': item_name, 'label': label, 'count': count, 'slot': slot}) # Přidáno 'count' a 'slot'
        return items
    except json.JSONDecodeError:
        return []

def parse_result(result_json):
    try:
        result = json.loads(result_json)
        item_name = result.get('item')
        count = result.get('count', 1)
        label = f"{item_name} x{count}"
        return {'item_name': item_name, 'label': label, 'count': count} # Přidáno 'count'
    except json.JSONDecodeError:
        return None

def parse_longcraft_result(reward_item_name, count):
    if reward_item_name:
        label = f"{reward_item_name} x{count}"
        return {'item_name': reward_item_name, 'label': label, 'count': count} # Přidáno 'count'
    else:
        return None

def download_item_image(item_name, image_name):
    if not os.path.exists(image_cache_dir):
        os.makedirs(image_cache_dir)
    image_path = os.path.join(image_cache_dir, f"{item_name}.png")
    if not os.path.exists(image_path):
        url = f"https://api.westhavenrp.cz/storage/items/{image_name}"
        try:
            from urllib.request import urlopen, Request
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urlopen(req).read()
            with open(image_path, 'wb') as f:
                f.write(data)
        except Exception as e:
            print(f"Error downloading image for {item_name}: {e}")
            return None
    return image_path

def get_item_image_path(item_name, connection):
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT image FROM items WHERE item = %s", (item_name,))
    result = cursor.fetchone()
    if result and result.get('image'):
        image_name = result['image']
        image_path = download_item_image(item_name, image_name)
        return image_path
    else:
        return None

def get_item_info(item_name, connection):
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT label, image FROM items WHERE item = %s", (item_name,))
    result = cursor.fetchone()
    if result:
        item_label = result['label']
        image_name = result['image']
        image_path = None
        if image_name:
            image_path = download_item_image(item_name, image_name)
        return item_label, image_path
    return None, None

def generate_graph(recipes, longcraft_recipes, connection, graph_title="Recepty", output_format='pdf'):
    from itertools import cycle

    dot = Digraph(comment=graph_title, format=output_format)
    dot.attr('graph', rankdir='LR', size='11.7,8.3')  # A4 na šířku
    dot.attr('node', shape='box', style='rounded,filled', color='lightgrey', fontname='Arial')
    dot.attr('edge', arrowhead='none', fontname='Arial', fontsize='8') # Menší fontsize pro popisky hran

    # Rozšířená definice barevného palety a cyklu
    color_palette = [
        'red', 'blue', 'green', 'orange', 'purple',
        'brown', 'cyan', 'magenta', 'gold', 'lime',
        'teal', 'pink', 'lavender', 'gray', 'olive',
        'maroon', 'navy', 'aquamarine', 'turquoise', 'coral',
        'darkred', 'darkblue', 'darkgreen', 'darkorange', 'darkpurple',
        'darkcyan', 'darkmagenta',
        'forestgreen', 'firebrick', 'steelblue4', 'chocolate', 'deeppink' # Ještě více barev
    ]
    color_cycle = cycle(color_palette)

    # Cyklus stylů čar
    edge_styles = ['solid', 'dashed', 'dotted', 'bold', 'tapered', 'invis'] # Ještě více stylů
    edge_style_cycle = cycle(edge_styles)

    # Mapa pro přiřazení vizuálních vlastností ITEMŮM
    item_visual_map = {}

    all_recipes = recipes + longcraft_recipes

    # Před-procházení receptů pro přiřazení barev a stylů ITEMŮM
    for recipe in all_recipes:
        materials = []
        if 'materials' in recipe:
            materials = parse_materials(recipe['materials'])
        elif 'recipe' in recipe:
            materials = parse_longcraft_materials(recipe['recipe'])

        for material in materials:
            item_name = material['item_name']
            if item_name not in item_visual_map:
                item_visual_map[item_name] = {'color': next(color_cycle), 'style': next(edge_style_cycle)}

    # Standardní recepty
    for recipe in recipes:
        recipe_id = recipe['id']
        recipe_name = recipe['name'] or f"Recept {recipe_id}"
        recipe_type = recipe.get('type')  # Získání typu receptu
        prop = recipe.get('prop')  # Získání prop, pokud existuje
        trigger_item = recipe.get('triggerItem')  # Získání triggerItem, pokud existuje
        category_name = recipe.get('category_name') or 'Nezařazeno'
        try:
            meta = json.loads(recipe.get('meta', '{}'))
            recipe_desc = meta.get('description', '')
        except json.JSONDecodeError:
            recipe_desc = ''

        # Přidání typu a případně prop nebo triggerItem do názvu receptu
        if recipe_type in ['near_prop', 'on_prop']:
            prop_value = prop if prop else 'Neznámý prop'
            recipe_name_with_type = f"{recipe_name} ({recipe_type}: {prop_value})"
        elif recipe_type == 'item':
            trigger_item_value = trigger_item if trigger_item else 'Neznámý trigger item'
            recipe_name_with_type = f"{recipe_name} ({recipe_type}: {trigger_item_value})"
        elif recipe_type:
            recipe_name_with_type = f"{recipe_name} ({recipe_type})"
        else:
            recipe_name_with_type = recipe_name

        recipe_label = f"<b>{recipe_name_with_type}</b><br/><font point-size='10'>[{category_name}]<br/>{recipe_desc}</font>"

        recipe_node_id = f"recipe_{recipe_id}"
        dot.node(recipe_node_id, label=f"<{recipe_label}>", shape='ellipse', style='filled', color='lightblue')


        # Materiály
        materials = parse_materials(recipe['materials'])
        for material in materials:
            item_name = material['item_name']
            mat_count = material['count'] # Použijeme 'count' z parsovaných materiálů
            item_label, image_path = get_item_info(item_name, connection)
            if not item_label:
                item_label = material['label']
            else:
                item_label = f"<i>{item_label}</i> ({item_name}) x{mat_count}"

            item_node_id = f"item_{item_name}"
            if image_path:
                dot.node(item_node_id, label=f"<{item_label}>", image=image_path, shape='none', width='1', height='1', labelloc='b')
            else:
                dot.node(item_node_id, label=f"<{item_label}>", shape='box')

            # Získání vizuálních vlastností itemu z mapy
            item_visual = item_visual_map[item_name]
            item_color = item_visual['color']
            item_edge_style = item_visual['style']

            # Přidání edge s barvou, stylem čáry a popiskem počtu, barva a styl se řídí itemem
            dot.edge(item_node_id, recipe_node_id, color=item_color, headlabel=f'<<B><font point-size="14">{mat_count}</font></B>>', style=item_edge_style)

        # Výsledek
        result = parse_result(recipe['result'])
        if result and result['item_name']:
            result_item_name = result['item_name']
            res_count = result['count'] # Použijeme 'count' z parsovaného výsledku
            res_item_label, res_image_path = get_item_info(result_item_name, connection)
            if not res_item_label:
                res_item_label = result['label']
            else:
                res_item_label = f"<i>{res_item_label}</i> ({result_item_name}) x{res_count}"

            result_node_id = f"item_{result_item_name}"
            if res_image_path:
                dot.node(result_node_id, label=f"<{res_item_label}>", image=res_image_path, shape='none', width='1', height='1', labelloc='b')
            else:
                dot.node(result_node_id, label=f"<{res_item_label}>", shape='box')

            # Přidání edge s barvou (můžeš použít jinou barvu, např. černou)
            dot.edge(recipe_node_id, result_node_id, color='black')

    # Longcraft recepty
    for recipe in longcraft_recipes:
        recipe_id = f"longcraft_{recipe['id']}"
        recipe_name = recipe['name'] or f"Longcraft Recept {recipe['id']}"
        prop = recipe.get('prop', 'Nezařazeno')
        time = recipe.get('time', '')
        job = recipe.get('job', 'Všichni')

        recipe_label = f"<b>{recipe_name}</b><br/><font point-size='10'>[Prop: {prop}]<br/>Čas: {time}<br/>Job: {job}</font>"
        recipe_node_id = f"longcraft_recipe_{recipe['id']}"
        dot.node(recipe_node_id, label=f"<{recipe_label}>", shape='ellipse', style='filled', color='lightgreen')


        # Materiály Longcraft
        materials = parse_longcraft_materials(recipe['recipe'])
        for material in materials:
            item_name = material['item_name']
            mat_info = material['label']
            mat_count = material['count'] # Použijeme 'count' z parsovaných materiálů
            item_label, image_path = get_item_info(item_name, connection)
            if not item_label:
                item_label = mat_info
            else:
                item_label = f"<i>{item_label}</i> ({item_name}) {mat_info.split(item_name)[-1]}"

            item_node_id = f"item_{item_name}"
            if image_path:
                dot.node(item_node_id, label=f"<{item_label}>", image=image_path, shape='none', width='1', height='1', labelloc='b')
            else:
                dot.node(item_node_id, label=f"<{item_label}>", shape='box')

            # Získání vizuálních vlastností itemu z mapy
            item_visual = item_visual_map[item_name]
            item_color = item_visual['color']
            item_edge_style = item_visual['style']

            # Přidání edge s barvou, stylem čáry a popiskem počtu, barva a styl se řídí itemem
            dot.edge(item_node_id, recipe_node_id, color=item_color, headlabel=f'<<B><font point-size="14">{mat_count}</font></B>>', style=item_edge_style)

        # Výsledek Longcraft
        result = parse_longcraft_result(recipe['reward'], recipe['count'])
        if result and result['item_name']:
            result_item_name = result['item_name']
            res_count = result['count'] # Použijeme 'count' z parsovaného výsledku
            res_item_label, res_image_path = get_item_info(result_item_name, connection)
            if not res_item_label:
                res_item_label = result['label']
            else:
                res_item_label = f"<i>{res_item_label}</i> ({result_item_name}) x{res_count}"

            result_node_id = f"item_{result_item_name}"
            if res_image_path:
                dot.node(result_node_id, label=f"<{res_item_label}>", image=res_image_path, shape='none', width='1', height='1', labelloc='b')
            else:
                dot.node(result_node_id, label=f"<{res_item_label}>", shape='box')

            # Přidání edge s barvou (můžeš použít jinou barvu, např. černou)
            dot.edge(recipe_node_id, result_node_id, color='black')

    return dot

def export_pdfs(connection):
    # Načteme standardní recepty
    recipes = get_recipes(connection)
    print(f"Nalezeno {len(recipes)} standardních receptů.")

    # Načteme longcraft recepty
    longcraft_recipes = get_longcraft_recipes(connection)
    print(f"Nalezeno {len(longcraft_recipes)} longcraft receptů.")

    # Skupiny podle kategorií
    categories = {}

    # Kategorizace standardních receptů
    for recipe in recipes:
        category_name = recipe.get('category_name') or 'Nezařazeno'
        if category_name not in categories:
            categories[category_name] = {'standard': [], 'longcraft': []}
        categories[category_name]['standard'].append(recipe)

    # Kategorizace longcraft receptů podle 'prop'
    for recipe in longcraft_recipes:
        prop = recipe.get('prop', 'Nezařazeno')
        category_name = f"Longcraft - {prop}"
        if category_name not in categories:
            categories[category_name] = {'standard': [], 'longcraft': []}
        categories[category_name]['longcraft'].append(recipe)

    # Vytvoříme adresář pro PDF, pokud neexistuje
    pdf_dir = os.path.join(BASE_DIR, "PDFs")
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)

    # Seznam dočasných souborů
    pdf_files = []

    # Generování PDF pro každou kategorii
    for category_name, category_recipes in categories.items():
        print(f"Generuji PDF pro kategorii: {category_name}")
        standard_recipes = category_recipes['standard']
        longcraft_recipes = category_recipes['longcraft']
        dot = generate_graph(standard_recipes, longcraft_recipes, connection, category_name, output_format='pdf')

        safe_category_name = category_name.replace('/', '_').replace('\\', '_').replace(' ', '_')
        output_filename = f"recepty_{safe_category_name}.pdf"
        output_path = os.path.join(pdf_dir, output_filename)

        try:
            dot.render(filename=f'recepty_{safe_category_name}', directory=pdf_dir, cleanup=True)
            print(f"Recepty pro kategorii '{category_name}' byly exportovány do souboru {output_path}")
            pdf_files.append(output_path)
        except Exception as e:
            print(f"Nastala chyba při generování PDF pro kategorii '{category_name}': {e}")

    # Sloučení všech PDF do jednoho
    if pdf_files:
        merged_pdf_path = os.path.join(pdf_dir, "recepty_vsechny_kategorie.pdf")
        merger = PdfMerger()
        for pdf_file in pdf_files:
            merger.append(pdf_file)
        merger.write(merged_pdf_path)
        merger.close()
        print(f"Všechny kategorie byly sloučeny do jednoho PDF: {merged_pdf_path}")

if __name__ == '__main__':
    config = load_config()
    connection = create_db_connection(config)

    # Export do PDF rozdělený podle kategorií, včetně longcraft receptů
    export_pdfs(connection)