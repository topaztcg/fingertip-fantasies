import json
import os
import base64
import io
import pygame

DB_FILE = "users_data.json"


class UserManager:
    def __init__(self):
        self.users = {}
        self.load_data()

    def load_data(self):
        if not os.path.exists(DB_FILE):
            self.save_data()
            return

        try:
            with open(DB_FILE, "r") as f:
                self.users = json.load(f)
            print(f"Database loaded. Found {len(self.users)} users.")
        except Exception as e:
            print(f"Error loading database: {e}")
            self.users = {}

    def save_data(self):
        try:
            # Atomic Write: Write to temp file first, then rename
            import tempfile
            dir_name = os.path.dirname(os.path.abspath(DB_FILE))
            # Create temp file in same directory to ensure atomic rename
            with tempfile.NamedTemporaryFile(mode='w', dir=dir_name, delete=False, encoding='utf-8') as tf:
                json.dump(self.users, tf, indent=4)
                temp_name = tf.name
            
            # Atomic replacement
            os.replace(temp_name, DB_FILE)
        except Exception as e:
            print(f"Error saving database: {e}")
            if 'temp_name' in locals() and os.path.exists(temp_name):
                os.remove(temp_name)

    def user_exists(self, username):
        return username in self.users

    def validate_login(self, username, password):
        if username in self.users:
            if self.users[username]['password'] == password:
                return True
        return False

    def load_user(self, username):
        """Returns the full user dictionary data."""
        return self.users.get(username, None)

    def create_user(self, username, password, avatar_surface=None):
        if username in self.users:
            return False, "User already exists!"

        b64_str = ""
        if avatar_surface:
            try:
                byte_io = io.BytesIO()
                pygame.image.save(avatar_surface, byte_io, "PNG")
                byte_io.seek(0)
                b64_str = base64.b64encode(byte_io.getvalue()).decode('utf-8')
            except Exception as e:
                print(f"Avatar encoding error: {e}")

        self.users[username] = {
            "password": password,
            "avatar_base64": b64_str,  # Renamed to match main.py expectation
            "stats": {
                "wins": 0,
                "losses": 0,
                "games_played": 0,
                "rank": "Novice"
            },
            "decks": {}
        }
        self.save_data()
        return True, "User created successfully!"

    def update_user_profile(self, old_username, new_username, new_avatar_surf):
        if new_username != old_username:
            if new_username in self.users:
                return False, "Username already taken!"
            if not new_username.strip():
                return False, "Username cannot be empty!"

        # Keep old avatar if no new one provided
        b64_str = self.users[old_username].get("avatar_base64", "")

        if new_avatar_surf:
            try:
                byte_io = io.BytesIO()
                pygame.image.save(new_avatar_surf, byte_io, "PNG")
                byte_io.seek(0)
                b64_str = base64.b64encode(byte_io.getvalue()).decode('utf-8')
            except Exception as e:
                print(f"Avatar encoding error: {e}")

        # Clone data
        user_data = self.users[old_username]
        user_data["avatar_base64"] = b64_str

        # Handle username change
        if new_username != old_username:
            self.users[new_username] = user_data
            del self.users[old_username]
        else:
            self.users[old_username] = user_data

        self.save_data()
        return True, "Profile Updated!"

    def get_avatar_image(self, username):
        user = self.users.get(username)
        # Check for both keys just in case old data exists
        avatar_data = user.get("avatar_base64") or user.get("avatar")

        if not user or not avatar_data:
            return None
        try:
            image_bytes = base64.b64decode(avatar_data)
            byte_io = io.BytesIO(image_bytes)
            return pygame.image.load(byte_io).convert_alpha()
        except Exception as e:
            print(f"Avatar decoding error: {e}")
            return None

    def get_user_stats(self, username):
        user = self.users.get(username)
        if user and "stats" in user:
            return user["stats"]
        return {"wins": 0, "losses": 0, "rank": "Unknown"}

    # --- DECK METHODS ---
    def get_user_decks(self, username):
        user = self.users.get(username)
        if user and "decks" in user:
            return user["decks"]
        return {}

    def get_active_deck_name(self, username):
        user = self.users.get(username)
        if not user: return None
        # Return saved active deck or default to first one
        if "active_deck" in user:
            # Verify it still exists
            if user["active_deck"] in user.get("decks", {}):
                return user["active_deck"]
        
        # Fallback: First deck
        decks = user.get("decks", {})
        if decks:
            first = list(decks.keys())[0]
            self.set_active_deck(username, first) # Save preference
            return first
        return None

    def set_active_deck(self, username, deck_name):
        user = self.users.get(username)
        if user:
            if "decks" in user and deck_name in user["decks"]:
                user["active_deck"] = deck_name
                self.save_data()
                print(f"[UserManager] Active Deck set to: {deck_name}")

    def save_deck(self, username, deck_name, card_ids):
        if username not in self.users: return
        if "decks" not in self.users[username]:
            self.users[username]["decks"] = {}

        self.users[username]["decks"][deck_name] = card_ids
        self.save_data()

    def delete_deck(self, username, deck_name):
        if username in self.users and "decks" in self.users[username]:
            if deck_name in self.users[username]["decks"]:
                del self.users[username]["decks"][deck_name]
                self.save_data()