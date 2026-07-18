# Grocery Item Database and Catalog

GROCERY_ITEMS = {
    "apple": {
        "id": "apple",
        "name": "Honeycrisp Apple",
        "price": 1.99,
        "unit": "lb",
        "category": "Produce",
        "sku": "4011-APP",
        "color": "#FF3B30",
        "icon": "🍎",
        "coco_class": "apple"
    },
    "banana": {
        "id": "banana",
        "name": "Organic Banana",
        "price": 0.59,
        "unit": "lb",
        "category": "Produce",
        "sku": "4011-BAN",
        "color": "#FFCC00",
        "icon": "🍌",
        "coco_class": "banana"
    },
    "orange": {
        "id": "orange",
        "name": "Navel Orange",
        "price": 1.29,
        "unit": "lb",
        "category": "Produce",
        "sku": "3107-ORN",
        "color": "#FF9500",
        "icon": "🍊",
        "coco_class": "orange"
    },
    "broccoli": {
        "id": "broccoli",
        "name": "Crown Broccoli",
        "price": 2.49,
        "unit": "lb",
        "category": "Produce",
        "sku": "4060-BRC",
        "color": "#34C759",
        "icon": "🥦",
        "coco_class": "broccoli"
    },
    "carrot": {
        "id": "carrot",
        "name": "Organic Carrots",
        "price": 1.89,
        "unit": "lb",
        "category": "Produce",
        "sku": "4094-CRT",
        "color": "#FF9500",
        "icon": "🥕",
        "coco_class": "carrot"
    },
    "bottle": {
        "id": "bottle",
        "name": "Spring Water Bottle",
        "price": 0.99,
        "unit": "item",
        "category": "Beverage",
        "sku": "012000000133",
        "color": "#5AC8FA",
        "icon": "💧",
        "coco_class": "bottle"
    },
    "cup": {
        "id": "cup",
        "name": "Artisan Coffee Cup",
        "price": 2.49,
        "unit": "item",
        "category": "Beverage",
        "sku": "073366115933",
        "color": "#AF52DE",
        "icon": "☕",
        "coco_class": "cup"
    },
    "bowl": {
        "id": "bowl",
        "name": "Fresh Salad Bowl",
        "price": 6.99,
        "unit": "item",
        "category": "Deli",
        "sku": "099482419447",
        "color": "#4CD964",
        "icon": "🥗",
        "coco_class": "bowl"
    },
    # Extra items that can be scanned via barcode/manual/OCR
    "milk": {
        "id": "milk",
        "name": "Whole Milk 1Gal",
        "price": 3.49,
        "unit": "item",
        "category": "Dairy",
        "sku": "078742351866",
        "color": "#E5E5EA",
        "icon": "🥛"
    },
    "bread": {
        "id": "bread",
        "name": "Sliced Sourdough",
        "price": 2.99,
        "unit": "item",
        "category": "Bakery",
        "sku": "072250037127",
        "color": "#D1C4E9",
        "icon": "🍞"
    },
    "cereal": {
        "id": "cereal",
        "name": "Honey Nut O's Cereal",
        "price": 4.59,
        "unit": "item",
        "category": "Pantry",
        "sku": "016000123991",
        "color": "#FF8A65",
        "icon": "🥣"
    },
    "cookies": {
        "id": "cookies",
        "name": "Chocolate Chip Cookies",
        "price": 3.89,
        "unit": "item",
        "category": "Bakery",
        "sku": "044000032029",
        "color": "#8D6E63",
        "icon": "🍪"
    }
}

COCO_TO_GROCERY = {item["coco_class"]: item["id"] for item in GROCERY_ITEMS.values() if "coco_class" in item}

def get_item_by_id(item_id):
    return GROCERY_ITEMS.get(item_id)

def get_item_by_coco_class(coco_class):
    item_id = COCO_TO_GROCERY.get(coco_class)
    if item_id:
        return GROCERY_ITEMS.get(item_id)
    return None

def get_item_by_sku(sku):
    sku_clean = sku.strip().upper()
    for item in GROCERY_ITEMS.values():
        if item["sku"] == sku_clean:
            return item
    return None

def get_all_items():
    return list(GROCERY_ITEMS.values())
