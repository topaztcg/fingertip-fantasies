import random
from card_manager import CardManager


class GameAI:
    def __init__(self):
        self.card_mgr = CardManager()
        self.all_cards = self.card_mgr.get_all_cards()

    def generate_deck(self):
        valid_pool = [c for c in self.all_cards]
        if len(valid_pool) < 3: return valid_pool
        return random.sample(valid_pool, 3)

    def choose_buff(self, hand, ai_cards, player_cards):
        """
        Scans hand for ONE beneficial buff to use.
        """
        if not hand: return None

        living_ai = [c for c in ai_cards if not c.is_dead]
        living_player = [c for c in player_cards if not c.is_dead]

        # Sorting
        living_ai.sort(key=lambda c: c.current_hp)  # Weakest
        living_player.sort(key=lambda c: c.current_hp, reverse=True)  # Strongest

        # 1. HEAL (Critical)
        for card in hand:
            if card.data["type"] == "HEAL":
                if living_ai and living_ai[0].current_hp < (living_ai[0].max_hp * 0.6):
                    return (card, living_ai[0])

        # 2. BUFF ATK (Offensive)
        for card in hand:
            if card.data["type"] == "BUFF_ATK":
                # Buff unit with most energy
                if living_ai:
                    best = max(living_ai, key=lambda c: c.energy)
                    return (card, best)

        # 3. DEBUFF (Control)
        for card in hand:
            if card.data["type"] in ["DEBUFF_FREEZE", "DEBUFF_DOT"]:
                if living_player:
                    return (card, living_player[0])

        # 4. DEFENSE (Survival)
        for card in hand:
            if card.data["type"] == "BUFF_DEF":
                if living_ai:
                    return (card, living_ai[0])

        return None

    def choose_attack(self, ai_cards, player_cards):
        living_ai = [c for c in ai_cards if not c.is_dead and c.frozen_turns == 0]
        living_player = [c for c in player_cards if not c.is_dead]

        if not living_ai or not living_player: return None

        # Kill Logic
        for ai_c in living_ai:
            dmg_base = ai_c.temp_atk_boost

            if ai_c.energy >= 4:
                dmg = 8 + dmg_base
                for p in living_player:
                    if p.current_hp <= max(0, dmg - p.temp_def_boost): return (ai_c, p, "ult")

            if ai_c.energy >= 2:
                dmg = 4 + dmg_base
                for p in living_player:
                    if p.current_hp <= max(0, dmg - p.temp_def_boost): return (ai_c, p, "skill")

            dmg = 2 + dmg_base
            for p in living_player:
                if p.current_hp <= max(0, dmg - p.temp_def_boost): return (ai_c, p, "normal")

        # Standard Attack
        living_player.sort(key=lambda c: c.current_hp)
        target = living_player[0]

        living_ai.sort(key=lambda c: c.energy, reverse=True)
        attacker = living_ai[0]

        if attacker.energy >= 4: return (attacker, target, "ult")
        if attacker.energy >= 2: return (attacker, target, "skill")
        return (attacker, target, "normal")