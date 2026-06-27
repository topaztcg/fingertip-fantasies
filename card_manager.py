import json
import os
import shutil

DB_FILE = "cards_data.json"
ASSETS_DIR = "assets/cards"

# Ensure assets folder exists
if not os.path.exists(ASSETS_DIR):
    try:
        os.makedirs(ASSETS_DIR)
    except:
        pass

class CardManager:
    def __init__(self):
        self.cards = []
        self.load_data()

    def load_data(self):
        if not os.path.exists(DB_FILE):
            self.save_data()
            return
        try:
            with open(DB_FILE, "r") as f:
                self.cards = json.load(f)
        except Exception as e:
            print(f"Error loading cards: {e}")
            self.cards = []

    def save_data(self):
        try:
            with open(DB_FILE, "w") as f:
                json.dump(self.cards, f, indent=4)
        except Exception as e:
            print(f"Error saving cards: {e}")

    def add_card(self, card_data, image_path, vid_normal, vid_skill, vid_ult):
        """
        Takes raw paths, copies files to assets/cards/, and saves metadata.
        """
        # 1. Create a safe filename ID
        safe_id = card_data["name"].lower().replace(" ", "_")

        # 2. Define Destination Paths
        card_dir = os.path.join(ASSETS_DIR, safe_id)
        if not os.path.exists(card_dir):
            os.makedirs(card_dir)

        # 3. Copy Media Files
        # Image
        new_img_path = ""
        if image_path and os.path.exists(image_path):
            ext_img = os.path.splitext(image_path)[1]
            new_img_path = os.path.join(card_dir, f"image{ext_img}")
            shutil.copy(image_path, new_img_path)

        # Videos
        v_paths = {}
        for v_type, v_path in [("normal", vid_normal), ("skill", vid_skill), ("ult", vid_ult)]:
            if v_path and os.path.exists(v_path):
                ext = os.path.splitext(v_path)[1]
                dest = os.path.join(card_dir, f"video_{v_type}{ext}")
                shutil.copy(v_path, dest)
                v_paths[v_type] = dest
            else:
                v_paths[v_type] = None

        # 4. Construct Final Data Object
        new_card = {
            "id": safe_id,
            "name": card_data["name"],
            "description": card_data["desc"],
            "hp": int(card_data["hp"]),
            "max_hp": int(card_data["hp"]),
            "energy_max": int(card_data["energy_max"]),
            "unlocked": True,
            "image_path": new_img_path,
            "videos": {
                "normal": v_paths["normal"],
                "skill": v_paths["skill"],
                "ult": v_paths["ult"]
            },
            "moves": {
                "normal": card_data["moves"]["normal"],
                "skill": card_data["moves"]["skill"],
                "ult": card_data["moves"]["ult"]
            }
        }

        self.cards.append(new_card)
        self.save_data()
        return True

    def get_all_cards(self):
        return self.cards

    def get_card(self, card_id):
        for c in self.cards:
            if c["id"] == card_id:
                return c
        return None

    def get_card_image(self, card_id):
        import pygame
        c = self.get_card(card_id)
        if c and c.get("image_path") and os.path.exists(c["image_path"]):
            try:
                return pygame.image.load(c["image_path"]).convert_alpha()
            except:
                pass
        return None