import json
from game_ai import SmartAI

class DummyCard:
    def __init__(self, hp, energy, is_ai):
        self.current_hp = hp
        self.max_hp = hp
        self.energy = energy
        self.max_energy = 5
        self.temp_atk_boost = 0
        self.temp_def_boost = 0
        self.frozen_turns = 0
        self.dot_turns = 0
        self.dot_val = 0
        self.is_dead = False
        self.data = {
            "name": "Dummy",
            "moves": {
                "normal": {"dmg": 2},
                "skill": {"cost": 2, "dmg": 5},
                "ult": {"cost": 4, "dmg": 10}
            }
        }
    def take_damage(self, dmg):
        self.current_hp -= dmg
        if self.current_hp <= 0:
            self.current_hp = 0
            self.is_dead = True

class DummyBuff:
    def __init__(self, type, val):
        self.data = {"type": type, "val": val, "name": type}

def run_test():
    ai = SmartAI()
    
    ai_cards = [
        DummyCard(10, 4, True),
        DummyCard(10, 0, True)
    ]
    player_cards = [
        DummyCard(5, 0, False), # 5 HP, in range of basic attack + skill
        DummyCard(20, 0, False)
    ]
    
    ai_hand = [
        DummyBuff("BUFF_ATK", 3),
        DummyBuff("HEAL", 5)
    ]
    
    print("Testing get_turn_actions...")
    actions = ai.get_turn_actions(ai_hand, ai_cards, player_cards)
    print("Actions returned:")
    for a in actions:
        if a[0] == "BUFF":
            print(f"- BUFF {a[1].data['name']} on {a[2].data['name']}")
        elif a[0] == "ATTACK":
            print(f"- ATTACK {a[3]} from {a[1].data['name']} to {a[2].data['name']}")
    
    print("Test Complete.")

if __name__ == "__main__":
    run_test()
