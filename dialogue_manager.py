import json
import os
import random

DIALOGUE_DB_FILE = "card_dialogues.json"

class DialogueManager:
    _instance = None

    def __init__(self):
        self.dialogues = {}
        self.load_data()
        self.queue = [] # Queue for dialogues: (card_ui, text, timing)

    @classmethod
    def get(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def load_data(self):
        if not os.path.exists(DIALOGUE_DB_FILE):
            return
        try:
            with open(DIALOGUE_DB_FILE, "r") as f:
                self.dialogues = json.load(f)
        except:
            print("Error loading dialogues.")
            self.dialogues = {}

    def get_dialogue(self, card_id, trigger, value=None):
        """
        Returns a dialogue entry (dict or str) if conditions met.
        Returns None if no dialogue found.
        """
        if card_id not in self.dialogues: return None
        entries = self.dialogues[card_id].get(trigger, [])
        
        if not entries: return None

        valid_entries = []
        for entry in entries:
            # Handle simple string entries (legacy support)
            if isinstance(entry, str):
                valid_entries.append({"text": entry})
                continue
            
            # Check Threshold
            threshold = entry.get("threshold", 0)
            if value is not None and value < threshold:
                continue
            
            valid_entries.append(entry)

        if not valid_entries: return None
        
        # Pick one random valid entry
        return random.choice(valid_entries)

    def trigger_event(self, card_ui, trigger, value=None):
        """
        Checks if the card has a dialogue for this trigger.
        If yes, adds it to the display queue.
        Returns the entry found (or None).
        """
        entry = self.get_dialogue(card_ui.data["id"], trigger, value)
        if entry:
            timing = entry.get("timing", "PRE") # Default PRE
            text = entry.get("text", "")
            return {"card": card_ui, "text": text, "timing": timing}
        return None
