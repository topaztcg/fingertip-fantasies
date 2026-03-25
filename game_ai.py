import copy
import random
from card_manager import CardManager

class SmartAI:
    def __init__(self):
        self.card_mgr = CardManager()
        self.all_cards = self.card_mgr.get_all_cards()

    def generate_deck(self):
        valid = [c for c in self.all_cards]
        if len(valid) < 3: return valid
        return random.sample(valid, 3)

    def get_turn_actions(self, enemy_hand, enemy_cards, player_cards):
        """
        Calculates the best sequence of buffs ending with an attack (or no attack).
        Simulates all possible outcomes for the current turn.
        """
        def clone_state(state):
            return {
                "ai": [copy.copy(c) for c in state["ai"]],
                "player": [copy.copy(c) for c in state["player"]],
                "hand": list(state["hand"])
            }

        def eval_state(state):
            score = 0
            for c in state["ai"]:
                if c["is_dead"]: score -= 2000
                else:
                    score += c["hp"] * 20
                    score += c["energy"] * 15
                    score += c["temp_atk"] * 10
                    score += c["temp_def"] * 10
            for c in state["player"]:
                if c["is_dead"]: score += 2000
                else:
                    # Enemy alive penalty. 
                    # Multiply HP penalty by their threat level so AI naturally 
                    # prioritizes chunking high-threat targets.
                    threat_multiplier = 1.0 + (c["energy"] * 0.3) + (c["temp_atk"] * 0.2)
                    
                    score -= c["hp"] * 20 * threat_multiplier
                    score -= c["energy"] * 15
                    score -= c["temp_atk"] * 10
                    score -= c["temp_def"] * 10
                    if c["frozen"] > 0: score += 50
                    if c["dot_turns"] > 0: score += c["dot_val"] * 10
            return score

        def sim_buff(state, buff_idx, is_ally_target, target_idx):
            ns = clone_state(state)
            buff = ns["hand"].pop(buff_idx)
            b_type = buff.data["type"]
            val = buff.data["val"]
            target_list = ns["ai"] if is_ally_target else ns["player"]
            target = target_list[target_idx]
            
            if b_type == "HEAL":
                target["hp"] = min(target["max_hp"], target["hp"] + val)
            elif b_type == "BUFF_ATK":
                target["temp_atk"] += val
            elif b_type == "BUFF_DEF":
                target["temp_def"] += val
            elif b_type == "DEBUFF_FREEZE":
                target["frozen"] += val
            elif b_type == "DEBUFF_DOT":
                target["dot_turns"] += val
                target["dot_val"] = val  # Simplified assuming val is dot damage
                
            return ns

        def get_legal_buffs(state):
            moves = []
            for i, buff in enumerate(state["hand"]):
                b_type = buff.data["type"]
                is_buff = b_type in ["HEAL", "BUFF_ATK", "BUFF_DEF"]
                if is_buff:
                    for j, c in enumerate(state["ai"]):
                        if not c["is_dead"]:
                            # Optimization: Don't heal if full HP
                            if b_type == "HEAL" and c["hp"] >= c["max_hp"]: continue
                            moves.append(("BUFF", i, True, j))
                else:
                    for j, c in enumerate(state["player"]):
                        if not c["is_dead"]: moves.append(("BUFF", i, False, j))
            return moves

        def sim_attack(state, attacker_idx, target_idx, m_key):
            ns = clone_state(state)
            attacker = ns["ai"][attacker_idx]
            target = ns["player"][target_idx]
            
            m_data = attacker["moves"].get(m_key, {})
            base_dmg = int(m_data.get("dmg", 0))
            if m_key == "normal":
                attacker["energy"] = min(attacker["max_energy"], attacker["energy"] + 1)
            else:
                cost = int(m_data.get("cost", 0))
                attacker["energy"] -= cost
                
            tot_dmg = base_dmg + attacker["temp_atk"]
            actual_dmg = max(0, tot_dmg - target["temp_def"])
            target["hp"] -= actual_dmg
            
            if target["hp"] <= 0:
                target["hp"] = 0
                target["is_dead"] = True
                
            attacker["temp_atk"] = 0
            return ns

        def get_legal_attacks(state):
            moves = []
            for i, c in enumerate(state["ai"]):
                if c["is_dead"] or c["frozen"] > 0: continue
                # Gather available moves
                avail = []
                if "normal" in c["moves"]: avail.append("normal")
                if "skill" in c["moves"] and c["energy"] >= int(c["moves"]["skill"].get("cost", 0)): avail.append("skill")
                if "ult" in c["moves"] and c["energy"] >= int(c["moves"]["ult"].get("cost", 0)): avail.append("ult")
                
                for m_key in avail:
                    for j, trg in enumerate(state["player"]):
                        if not trg["is_dead"]:
                            moves.append(("ATTACK", i, j, m_key))
            return moves

        best_score = float('-inf')
        best_sequence = []

        def dfs(state, current_seq, can_attack):
            nonlocal best_score, best_sequence
            
            score = eval_state(state)
            # If this path is strictly better, record it
            if score > best_score:
                best_score = score
                best_sequence = list(current_seq)
            # If we don't have to attack, we might just be ending our turn early, which is fine, 
            # but usually more moves = better score unless it's a bad move.

            # Try Buffs
            for b_move in get_legal_buffs(state):
                b_idx, is_ally, t_idx = b_move[1], b_move[2], b_move[3]
                ns = sim_buff(state, b_idx, is_ally, t_idx)
                current_seq.append(b_move)
                dfs(ns, current_seq, can_attack)
                current_seq.pop()
                
            # Try Attacks (ends the sequence)
            if can_attack:
                for a_move in get_legal_attacks(state):
                    a_idx, t_idx, m_key = a_move[1], a_move[2], a_move[3]
                    ns = sim_attack(state, a_idx, t_idx, m_key)
                    
                    # Score after attack
                    final_score = eval_state(ns)
                    if final_score > best_score:
                        best_score = final_score
                        best_sequence = current_seq + [a_move]

        # Init state
        def to_sim_card(bc):
            return {
                "obj": bc, "hp": bc.current_hp, "max_hp": bc.max_hp,
                "energy": bc.energy, "max_energy": bc.max_energy,
                "temp_atk": bc.temp_atk_boost, "temp_def": bc.temp_def_boost,
                "frozen": bc.frozen_turns, "is_dead": bc.is_dead,
                "dot_turns": bc.dot_turns, "dot_val": bc.dot_val,
                "moves": bc.data.get("moves", {})
            }

        initial_state = {
            "ai": [to_sim_card(c) for c in enemy_cards],
            "player": [to_sim_card(c) for c in player_cards],
            "hand": list(enemy_hand)
        }

        dfs(initial_state, [], True)

        # Map sequence back to real objects
        resolved_actions = []
        # Because buffs modify indices (popping), we must track the hand as it shrinks 
        # to map indices back.
        sim_hand_list = list(enemy_hand)
        
        for move in best_sequence:
            if move[0] == "BUFF":
                _, b_idx, is_ally, t_idx = move
                real_buff = sim_hand_list.pop(b_idx)
                target_list = enemy_cards if is_ally else player_cards
                real_target = target_list[t_idx]
                resolved_actions.append(("BUFF", real_buff, real_target))
            elif move[0] == "ATTACK":
                _, a_idx, t_idx, m_key = move
                real_attacker = enemy_cards[a_idx]
                real_target = player_cards[t_idx]
                resolved_actions.append(("ATTACK", real_attacker, real_target, m_key))
                
        return resolved_actions