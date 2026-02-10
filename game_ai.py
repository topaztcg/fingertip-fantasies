import random
from card_manager import CardManager

class SmartAI:
    def __init__(self):
        self.card_mgr = CardManager()
        self.all_cards = self.card_mgr.get_all_cards()
        self.persona = random.choice(["AGGRESSIVE", "DEFENSIVE", "BALANCED", "CHAOTIC"])
        print(f"[AI] Initialized with Persona: {self.persona}")

    def generate_deck(self):
        valid_pool = [c for c in self.all_cards]
        if len(valid_pool) < 3: return valid_pool
        return random.sample(valid_pool, 3)

    def get_best_move(self, ai_hand, ai_board, player_board, current_energy_pool=99):
        """
        Analyzes the board and returns the best possible action.
        Returns: DICT with keys: type, card, target, score, desc
        """
        possible_moves = []

        # --- 1. IDENTIFY ALL POSSIBLE BUFF MOVES ---
        # AI Logic: We can play up to 2 buffs per turn usually, but let's just score them all
        # We need to pass 'buffs_played_this_turn' context if we want to enforce limits strictly here,
        # but for now let's assume the GameScreen handles the "2 per turn" validation or we return, fail, and retry.
        
        living_ai = [c for c in ai_board if not c.is_dead]
        living_player = [c for c in player_board if not c.is_dead]
        
        if not living_ai or not living_player: return None

        for buff_card in ai_hand:
            # Try applying to all valid targets
            b_type = buff_card.data["type"]
            val = buff_card.data["val"]
            
            # Buffs go on allies
            if b_type in ["HEAL", "BUFF_ATK", "BUFF_DEF"]:
                for target in living_ai:
                    score = self._score_buff(b_type, val, target, is_ally=True)
                    possible_moves.append({
                        "type": "PLAY_BUFF",
                        "card": buff_card,
                        "target": target,
                        "score": score,
                        "desc": f"Buff {target.data['name']} with {b_type}"
                    })
            
            # Debuffs go on enemies
            elif b_type in ["DEBUFF_FREEZE", "DEBUFF_DOT"]:
                for target in living_player:
                    score = self._score_buff(b_type, val, target, is_ally=False)
                    possible_moves.append({
                        "type": "PLAY_BUFF",
                        "card": buff_card,
                        "target": target,
                        "score": score,
                        "desc": f"Debuff {target.data['name']} with {b_type}"
                    })

        # --- 2. IDENTIFY ALL POSSIBLE ATTACK MOVES ---
        for attacker in living_ai:
            if attacker.frozen_turns > 0: continue # Can't move

            moves_data = attacker.data.get("moves", {})
            
            # Helper to get move cost safely
            def get_cost(m_key): 
                if m_key == "normal": return 0
                return int(moves_data.get(m_key, {}).get("cost", 0))

            # Helper to get move dmg safely
            def get_dmg(m_key):
                return int(moves_data.get(m_key, {}).get("dmg", 0))

            available_attacks = []
            # Check Energy for Skill/Ult
            if "ult" in moves_data and attacker.energy >= get_cost("ult"):
                available_attacks.append("ult")
            if "skill" in moves_data and attacker.energy >= get_cost("skill"):
                available_attacks.append("skill")
            if "normal" in moves_data:
                available_attacks.append("normal")

            for m_key in available_attacks:
                cost = get_cost(m_key)
                base_dmg = get_dmg(m_key)
                total_dmg = base_dmg + attacker.temp_atk_boost
                
                for target in living_player:
                    score = self._score_attack(attacker, target, m_key, total_dmg, cost)
                    possible_moves.append({
                        "type": "ATTACK",
                        "card": attacker,
                        "target": target,
                        "move": m_key, # Key change: use 'move' instead of m_key directly
                        "score": score,
                        "desc": f"{m_key.upper()} on {target.data['name']} ({total_dmg} dmg)"
                    })

        # --- 3. SELECT BEST MOVE ---
        if not possible_moves: return None

        # Sort by score descending
        possible_moves.sort(key=lambda x: x["score"], reverse=True)

        # Weighted Randomness for "Alice" feeling
        # Take top 3 moves and pick one based on weights, or strict top if huge gap
        top_moves = possible_moves[:3]
        best_move = top_moves[0]
        
        # If the best move is vastly superior (e.g. lethal), always take it
        if best_move["score"] > 500:
            return best_move

        # Otherwise, add a little randomness based on persona
        if self.persona == "CHAOTIC" and len(top_moves) > 1:
            return random.choice(top_moves)
        
        return best_move

    def _score_buff(self, b_type, val, target, is_ally):
        score = 0
        
        if b_type == "HEAL":
            missing_hp = target.max_hp - target.current_hp
            if missing_hp > 0:
                # Base score for healing per point
                score += val * 10
                # Critical HP Bonus (Unit below 30%)
                if target.current_hp < (target.max_hp * 0.3):
                    score += 100
            else:
                score -= 50 # Waste of heal

            if self.persona == "DEFENSIVE": score *= 1.5

        elif b_type == "BUFF_ATK":
            score += val * 15
            # Bonus if target has high energy (ready to Ult)
            if target.energy >= (target.max_energy - 1):
                score += 50
            if self.persona == "AGGRESSIVE": score *= 1.5

        elif b_type == "BUFF_DEF":
            score += val * 10
            if target.current_hp < (target.max_hp * 0.5):
                score += 30
            if self.persona == "DEFENSIVE": score *= 1.5
            
        elif b_type == "DEBUFF_FREEZE":
            score += val * 40
            # Great to freeze units with high energy
            if target.energy >= 3:
                score += 50
            if self.persona == "DEFENSIVE": score *= 1.2

        elif b_type == "DEBUFF_DOT":
            score += val * 2 * 10 # Total damage prediction
            if self.persona == "AGGRESSIVE": score *= 1.2

        return score

    def _score_attack(self, attacker, target, move_key, damage, cost):
        score = 0
        
        # 1. Damage Efficiency
        score += damage * 10
        
        # 2. Kill Potential (Huge Priority)
        if target.current_hp <= max(0, damage - target.temp_def_boost):
            score += 1000
        
        # 3. Energy Cost Penalty (Efficiency)
        # We generally want to save energy for big hits, unless we are killing
        if move_key != "normal":
             # If it's not a kill, using energy is a 'cost'
             if score < 1000: 
                 score -= (cost * 5)
        else:
            # Normal attacks generate energy, that's a plus
            score += 15 

        # 4. Overkill Penalty
        # If target has 1 HP and we use a 10 dmg Ult, that's wasteful
        if target.current_hp < damage and move_key == "ult":
            score -= 200 

        # 5. Persona Modifiers
        if self.persona == "AGGRESSIVE":
            score *= 1.2
        elif self.persona == "DEFENSIVE" and move_key == "normal":
            # Defensive AI prefers building energy for safe big hits later?
            score *= 1.1

        return score