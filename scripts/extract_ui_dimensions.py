import os
import json
from PIL import Image

RESOURCE_PACKS_PATH = "resource_packs_repo/src/main/resources"
UI_DATA_PATH = "scripts/src/data/user-interface.jsonc"

def extract_image_dimensions(base_path: str) -> dict:
    dimensions = {}
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                file_path = os.path.join(root, file)
                try:
                    with Image.open(file_path) as img:
                        width, height = img.size
                        # Store with relative path from resources, and without extension
                        relative_path = os.path.relpath(file_path, base_path)
                        name_without_ext = os.path.splitext(relative_path)[0]
                        dimensions[name_without_ext] = {"width": width, "height": height}
                except Exception as e:
                    print(f"Could not read image {file_path}: {e}")
    return dimensions

def update_ui_data(ui_data: dict, image_dimensions: dict) -> dict:
    # Heuristic mapping: This part will need manual refinement based on actual UI elements
    # For now, let's try to map some common ones.

    # Inventory
    if "inventory" in ui_data:
        # Common inventory slot image names might be like "inventory_slot" or similar
        # This is a placeholder and needs to be adjusted based on actual image names in the repo
        inventory_slot_dim = image_dimensions.get("sprites/item_slot_background") or \
                             image_dimensions.get("widgets/inventory/inventory_slot") or \
                             image_dimensions.get("inventory/slot")
        if inventory_slot_dim:
            ui_data["inventory"]["cellSize"]["width"] = inventory_slot_dim["width"]
            ui_data["inventory"]["cellSize"]["height"] = inventory_slot_dim["height"]
            print(f"Updated inventory cellSize to {inventory_slot_dim['width']}x{inventory_slot_dim['height']}")

    # Prayer
    if "prayer" in ui_data:
        # Common prayer icon image names might be like "prayer_icon_active"
        prayer_icon_dim = image_dimensions.get("sprites/prayer_icon") or \
                          image_dimensions.get("widgets/prayer/prayer_icon") or \
                          image_dimensions.get("prayer/icon")
        if prayer_icon_dim:
            ui_data["prayer"]["cellSize"]["width"] = prayer_icon_dim["width"]
            ui_data["prayer"]["cellSize"]["height"] = prayer_icon_dim["height"]
            print(f"Updated prayer cellSize to {prayer_icon_dim['width']}x{prayer_icon_dim['height']}")

    # Magic
    if "magic" in ui_data:
        # Common magic spell icon image names
        magic_icon_dim = image_dimensions.get("sprites/spell_icon") or \
                         image_dimensions.get("widgets/magic/spell_icon") or \
                         image_dimensions.get("magic/icon")
        if magic_icon_dim:
            ui_data["magic"]["cellSize"]["width"] = magic_icon_dim["width"]
            ui_data["magic"]["cellSize"]["height"] = magic_icon_dim["height"]
            print(f"Updated magic cellSize to {magic_icon_dim['width']}x{magic_icon_dim['height']}")
            
    # Equipment (if we want to update individual slot sizes, this would be more complex)
    # For now, we'll leave equipment as is, as it uses fixed coordinates.

    return ui_data

def main():
    print(f"Extracting image dimensions from {RESOURCE_PACKS_PATH}...")
    image_dims = extract_image_dimensions(RESOURCE_PACKS_PATH)
    # print(json.dumps(image_dims, indent=2)) # For debugging extracted dimensions

    print(f"Loading UI data from {UI_DATA_PATH}...")
    with open(UI_DATA_PATH, 'r') as f:
        # JSONC files can have comments, so we need to strip them before parsing
        content = "".join(line for line in f if not line.strip().startswith("//"))
        ui_data = json.loads(content)

    print("Updating UI data with extracted dimensions...")
    updated_ui_data = update_ui_data(ui_data, image_dims)

    print(f"Saving updated UI data to {UI_DATA_PATH}...")
    with open(UI_DATA_PATH, 'w') as f:
        json.dump(updated_ui_data, f, indent=4)
    print("UI data updated successfully.")

if __name__ == "__main__":
    main()
