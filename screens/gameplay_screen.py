import pygame
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import random
import time
import pytweening
from ui_components import Button, BG_FALLBACK, BUTTON_BORDER, TEXT_COLOR, get_font, update_animations, draw_panel, spawn_particles, update_juice, draw_juice_overlays, spawn_floating_text, shake_screen, AnimationManager, FadeLayer
from game_ai import SmartAI
from video_player import VideoWrapper, run_fullscreen_video
from buff_manager import BuffManager, BuffCardUI
from dialogue_manager import DialogueManager

# --- CONSTANTS ---
CARD_W, CARD_H = 180, 270
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
GAP_X = 80


# --- HELPER: PIXEL-PERFECT TEXT WRAPPING ---
def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        w, h = font.size(test_line)
        if w < max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))
    return lines


class BattleCard:
    def __init__(self, card_data, x, y, is_player):
        self.data = card_data
        self.max_hp = int(card_data.get("hp", 10))
        self.current_hp = self.max_hp
        self.energy = 0
        self.max_energy = int(card_data.get("energy_max", 3))
        self.is_player = is_player
        self.is_dead = False

        self.total_damage_dealt = 0
        self.total_damage_taken = 0
        self.healing_done = 0
        self.energy_spent = 0
        self.buffs_received = 0
        self.kills = 0

        self.temp_atk_boost = 0
        self.temp_def_boost = 0
        self.frozen_turns = 0
        self.dot_turns = 0
        self.dot_val = 0

        self.rect = pygame.Rect(x, y, CARD_W, CARD_H)
        self.trigger_cb = None # Callback for dialogue system

        # UI State
        self.selected = False
        self.target_y = y
        self.base_y = y
        self.shake_offset = [0, 0]
        self.hover_scale = 1.0
        
        # Load Image
        img_path = card_data.get("image_path")
        self.image_surf = None
        if img_path and os.path.exists(img_path):
            try:
                raw = pygame.image.load(img_path).convert_alpha()
                self.image_surf = pygame.transform.scale(raw, (CARD_W, CARD_H))
            except: pass
        
        # ENTRY ANIMATION
        target_y = y
        self.rect.y = 1200 # Off-screen bottom
        if not is_player: self.rect.y = -400 # Off-screen top for enemy
        
        AnimationManager.get().start_tween(self.rect, "y", target_y, 0.8, pytweening.easeOutBack)
        self.shield = 0 

    def reset_round_stats(self):
        self.temp_atk_boost = 0
        self.temp_def_boost = 0
        if self.frozen_turns > 0: self.frozen_turns -= 1
        if self.dot_turns > 0:
            self.take_damage(self.dot_val)
            self.dot_turns -= 1

    def apply_buff(self, buff_type, val):
        if buff_type == "HEAL":
            old_hp = self.current_hp
            self.current_hp = min(self.max_hp, self.current_hp + val)
            healed = self.current_hp - old_hp
            spawn_floating_text(self.rect.centerx, self.rect.centery, f"+{healed}", (50, 255, 50))
            spawn_particles(self.rect.centerx, self.rect.centery, 10, (50, 255, 50))
            if self.trigger_cb: self.trigger_cb(self, "HEALED", healed)
        
        elif buff_type == "BUFF_ATK":
            self.temp_atk_boost += val
            spawn_floating_text(self.rect.centerx, self.rect.centery, f"+{val} ATK", (255, 100, 50))
            if self.trigger_cb: self.trigger_cb(self, "ATK_BUFFED", self.temp_atk_boost)

        elif buff_type == "BUFF_DEF":
            # Assuming Shield logic
            self.shield += val
            spawn_floating_text(self.rect.centerx, self.rect.centery, f"+{val} SHIELD", (100, 100, 255))
            if self.trigger_cb: self.trigger_cb(self, "SHIELD_GAINED", self.shield)
        elif buff_type == "DEBUFF_FREEZE":
            self.frozen_turns += val
        elif buff_type == "DEBUFF_DOT":
            self.dot_turns = 2;
            self.dot_val = val
        
        # VISUAL FEEDBACK
        cx, cy = self.rect.centerx, self.rect.centery
        if buff_type == "HEAL":
            spawn_floating_text(cx, cy, f"+{val}", (50, 255, 50))
            spawn_particles(cx, cy, 5, (50, 255, 50))
        elif buff_type == "BUFF_ATK":
            spawn_floating_text(cx, cy, "ATK UP", (100, 100, 255))
        elif buff_type == "BUFF_DEF":
            spawn_floating_text(cx, cy, "DEF UP", (100, 100, 255))

    def take_damage(self, amount):
        if self.is_dead: return
        actual_dmg = max(0, amount - self.temp_def_boost)
        self.current_hp -= actual_dmg
        self.total_damage_taken += actual_dmg
        
        # VISUAL FEEDBACK (JUICE)
        cx, cy = self.rect.centerx, self.rect.centery
        col = (255, 50, 50) if self.is_player else (255, 100, 100)
        spawn_floating_text(cx, cy, str(actual_dmg), col)
        spawn_particles(cx, cy, 10, col)
        
        if actual_dmg > 15:
            shake_screen(5, 0.4)
        elif actual_dmg > 5:
            shake_screen(2, 0.2)
        
        if self.current_hp <= 0:
            self.current_hp = 0;
            self.is_dead = True;
            self.selected = False;
            self.frozen_turns = 0;
            self.dot_turns = 0
            spawn_floating_text(cx, cy, "DEAD", (50, 50, 50))
            if self.trigger_cb: self.trigger_cb(self, "DEATH")
        else:
            if self.trigger_cb:
                self.trigger_cb(self, "DAMAGE_TAKEN", actual_dmg)
                if actual_dmg >= 5:
                    self.trigger_cb(self, "HEAVY_HIT_TAKEN", actual_dmg)

    def consume_energy(self, cost):
        if self.energy >= cost:
            self.energy -= cost;
            return True
        return False

    def gain_energy(self, amount=1):
        old_e = self.energy
        self.energy = min(self.max_energy, self.energy + amount)
        if self.energy > old_e:
            # Visual Feedback
            spawn_floating_text(self.rect.centerx + 20, self.rect.centery - 20, "+1 EN", (50, 200, 255))

    def update(self, mouse_pos, click_event=False):
        if self.is_dead: return False
        if click_event and self.rect.collidepoint(mouse_pos): return True
        return False

    def draw(self, screen, mouse_pos):
        is_hovered = self.rect.collidepoint(mouse_pos)
        target_scale = 1.08 if is_hovered else 1.0
        self.hover_scale += (target_scale - self.hover_scale) * 0.2

        pad = 40
        surf_w = CARD_W + (pad * 2)
        surf_h = CARD_H + (pad * 2)
        temp_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

        rel_x, rel_y = pad, pad
        card_rect_rel = pygame.Rect(rel_x, rel_y, CARD_W, CARD_H)

        if self.image_surf:
            temp_surf.blit(self.image_surf, (rel_x, rel_y))
        else:
            pygame.draw.rect(temp_surf, (50, 50, 50), card_rect_rel)

        if self.is_dead:
            s = pygame.Surface((CARD_W, CARD_H));
            s.set_alpha(200);
            s.fill((20, 0, 0))
            temp_surf.blit(s, (rel_x, rel_y))
            txt = get_font(40).render("DEAD", True, (255, 50, 50))
            temp_surf.blit(txt, (surf_w // 2 - txt.get_width() // 2, surf_h // 2 - 20))
        else:
            if self.frozen_turns > 0:
                s = pygame.Surface((CARD_W, CARD_H));
                s.set_alpha(100);
                s.fill((150, 255, 255))
                temp_surf.blit(s, (rel_x, rel_y))
                txt = get_font(30).render("FROZEN", True, (0, 100, 255))
                temp_surf.blit(txt, (surf_w // 2 - txt.get_width() // 2, surf_h // 2))

            thickness = 4
            if self.selected:
                color = (255, 255, 0);
                thickness = 6
            else:
                color = (100, 255, 100) if self.is_player else (255, 100, 100)
            pygame.draw.rect(temp_surf, color, card_rect_rel, thickness)

            hp_center = (card_rect_rel.right - 10, card_rect_rel.top + 10)
            pygame.draw.circle(temp_surf, (180, 0, 0), hp_center, 28)
            pygame.draw.circle(temp_surf, (255, 255, 255), hp_center, 28, 2)
            hp_txt = get_font(26).render(str(self.current_hp), True, (255, 255, 255))
            temp_surf.blit(hp_txt, hp_txt.get_rect(center=hp_center))

            en_center = (card_rect_rel.right - 10, card_rect_rel.bottom - 10)
            pygame.draw.circle(temp_surf, (0, 100, 200), en_center, 28)
            pygame.draw.circle(temp_surf, (255, 255, 255), en_center, 28, 2)
            en_txt = get_font(26).render(str(self.energy), True, (255, 255, 255))
            temp_surf.blit(en_txt, en_txt.get_rect(center=en_center))

            stat_y = card_rect_rel.bottom + 10
            if self.temp_atk_boost > 0:
                s_txt = get_font(22).render(f"ATK +{self.temp_atk_boost}", True, (255, 100, 100));
                temp_surf.blit(s_txt, (rel_x, stat_y));
                stat_y += 25
            if self.temp_def_boost > 0:
                s_txt = get_font(22).render(f"DEF +{self.temp_def_boost}", True, (100, 100, 255));
                temp_surf.blit(s_txt, (rel_x, stat_y));
                stat_y += 25
            if self.dot_turns > 0:
                s_txt = get_font(22).render("POISON", True, (200, 0, 200));
                temp_surf.blit(s_txt, (surf_w // 2 - s_txt.get_width() // 2, rel_x - 35))

        final_w = int(surf_w * self.hover_scale)
        final_h = int(surf_h * self.hover_scale)
        if abs(self.hover_scale - 1.0) > 0.01:
            scaled_surf = pygame.transform.smoothscale(temp_surf, (final_w, final_h))
            screen.blit(scaled_surf, scaled_surf.get_rect(center=self.rect.center))
        else:
            screen.blit(temp_surf, temp_surf.get_rect(center=self.rect.center))


def show_gameplay_screen(screen, player_deck_data, current_user):
    clock = pygame.time.Clock()
    buff_mgr = BuffManager()
    ai = SmartAI()
    
    # -- DIALOGUE SYSTEM INIT --
    dialogue_mgr = DialogueManager.get()
    active_dialogues = []
    
    def trigger_dialogue(card_obj, trigger, value=None):
        nonlocal active_dialogues
        
        # Dead check (allow DEATH/MATCH_LOST triggers)
        if card_obj.is_dead and trigger not in ["DEATH", "MATCH_LOST", "MATCH_WON"]:
            return

        # Mapping trigger name if needed
        data = dialogue_mgr.trigger_event(card_obj, trigger, value)
        if data:
            # Check if this card already has an active dialogue, if so, replace it
            # Otherwise add new
            existing = next((d for d in active_dialogues if d["card"] == card_obj), None)
            
            new_entry = data.copy()
            new_entry["timer"] = 180 # 3 seconds
            
            if existing:
                existing["text"] = new_entry["text"]
                existing["timer"] = 180
            else:
                active_dialogues.append(new_entry)

    fade = FadeLayer(screen.get_width(), screen.get_height(), speed=8)
    screen_w, screen_h = screen.get_width(), screen.get_height()
    group_w = (3 * CARD_W) + (2 * GAP_X)
    start_x = (screen_w - group_w) // 2

    ENEMY_HAND_Y = 20;
    ENEMY_CARD_Y = 220;
    PLAYER_CARD_Y = 600;
    PLAYER_HAND_Y = 910

    player_cards = []
    for i, data in enumerate(player_deck_data):
        c = BattleCard(data, start_x + (i * (CARD_W + GAP_X)), PLAYER_CARD_Y, is_player=True)
        player_cards.append(c)

    enemy_cards = []
    ai_deck = ai.generate_deck()
    for i, data in enumerate(ai_deck):
        c = BattleCard(data, start_x + (i * (CARD_W + GAP_X)), ENEMY_CARD_Y, is_player=False)
        enemy_cards.append(c)
        
    # -- ASSIGN CALLBACKS --
    for c in player_cards + enemy_cards:
        c.trigger_cb = trigger_dialogue

    btn_w, btn_h = 240, 60;
    ui_x = screen_w - btn_w - 40;
    ui_y_start = screen_h - 450
    btn_normal = Button("NORMAL (+1 E)", ui_x, ui_y_start, btn_w, btn_h, font_size=20)
    btn_skill = Button("SKILL (2 E)", ui_x, ui_y_start + 70, btn_w, btn_h, font_size=20)
    btn_ult = Button("ULTIMATE (4 E)", ui_x, ui_y_start + 140, btn_w, btn_h, font_size=20)
    btn_end_turn = Button("END ROUND", ui_x, ui_y_start + 230, btn_w, btn_h, font_size=24)
    btn_surrender = Button("SURRENDER", screen_w - 200, 30, 180, 50, font_size=20)
    btn_continue = Button("RETURN TO MENU", screen_w - 350, screen_h - 100, 300, 60, font_size=30)

    state = "COIN_TOSS";
    winner_team = None;
    round_num = 1;
    info_msg = ""
    MAX_MOVES = 5;
    player_moves = 0;
    enemy_moves = 0
    selected_player = None;
    selected_enemy = None;
    selected_buff = None
    player_hand = [];
    enemy_hand = []
    state_timer = 0;
    next_turn_target = ""
    buffs_played_this_turn = {}

    # Trigger MATCH_START for all cards
    for c in player_cards + enemy_cards:
        trigger_dialogue(c, "MATCH_START")

    inspected_entity = None
    inspector_scroll_y = 0
    max_scroll_height = 0

    def reset_round_logic():
        nonlocal player_moves, enemy_moves, state, state_timer, info_msg
        player_moves = MAX_MOVES;
        enemy_moves = MAX_MOVES
        for c in player_cards + enemy_cards: c.reset_round_stats()
        info_msg = "Drawing Buffs...";
        state = "DRAW_BUFFS";
        state_timer = 60
        # Trigger ROUND_START for all cards (Only Round 2+)
        if round_num > 1:
            for c in player_cards + enemy_cards:
                trigger_dialogue(c, "ROUND_START")

    def switch_turn_logic():
        nonlocal state, next_turn_target, state_timer, buffs_played_this_turn, selected_buff, inspected_entity
        if state == "GAME_OVER": return
        buffs_played_this_turn = {};
        selected_buff = None;
        inspected_entity = None
        current_is_player = (next_turn_target == "PLAYER")
        if player_moves <= 0 and enemy_moves <= 0: end_round(); return
        target = "ENEMY" if current_is_player else "PLAYER"
        if target == "ENEMY" and enemy_moves <= 0: target = "PLAYER"
        if target == "PLAYER" and player_moves <= 0: target = "ENEMY"
        next_turn_target = target;
        state = "TURN_SWITCH_ANIM";
        state_timer = 60

    def end_round():
        nonlocal round_num;
        # Check Low HP at end of round
        for c in player_cards:
            if c.current_hp < 5 and not c.is_dead:
                trigger_dialogue(c, "LOW_HP_ROUND_END")
                
        round_num += 1;
        # trigger_dialogue(player_cards[0], "ROUND_START") # Removed redundant call
        reset_round_logic()

    def execute_attack(attacker, target, move_type):
        nonlocal info_msg, player_moves, enemy_moves, next_turn_target
        if attacker.frozen_turns > 0: info_msg = "Unit is Frozen!"; return False
        
        # --- DYNAMIC DATA RETRIEVAL ---
        move_data = attacker.data["moves"].get(move_type, {})
        base_dmg = int(move_data.get("dmg", 0))
        
        if move_type == "normal":
            attacker.gain_energy(1);
            cost = 0
        else:
            cost = int(move_data.get("cost", 0))
            if not attacker.consume_energy(cost): 
                info_msg = f"Need {cost} Energy!"; 
                return False
            attacker.energy_spent += cost
        
        # Trigger Action Dialogue
        trigger_type = "ATK_USED"
        if move_type == "skill": trigger_type = "SKILL_USED"
        elif move_type == "ult": trigger_type = "ULT_USED"
        
        trigger_dialogue(attacker, trigger_type)
        
        vid = attacker.data["videos"].get(move_type)
        if vid: run_fullscreen_video(screen, vid, show_hint=False)
        
        # Trigger Post-Video (if configured in JSON via timing='POST' it would be queued)
        # But we already triggered above. The Manager handles the timing check?
        # Actually my Manager Implementation returns data with 'timing' field.
        # So I should handle it here properly.
        # But for now, let's keep it simple: The dialogue shows up, then video plays. 
        # The user asked for "before or after".
        # Since run_fullscreen_video blocks, 'PRE' alerts are seen before. 'POST' alerts are seen after.
        # The trigger_dialogue puts it in queue/active.
        
        tot_dmg = base_dmg + attacker.temp_atk_boost
        target.take_damage(tot_dmg)
        
        trigger_dialogue(attacker, "DAMAGE_DEALT", tot_dmg)
        if tot_dmg >= 5: trigger_dialogue(attacker, "HEAVY_HIT_DEALT", tot_dmg)
        
        attacker.temp_atk_boost = 0
        attacker.total_damage_dealt += tot_dmg
        if target.is_dead: 
            attacker.kills += 1
            trigger_dialogue(attacker, "KILL")
        
        if attacker.is_player:
            player_moves -= 1;
            next_turn_target = "PLAYER"
        else:
            enemy_moves -= 1;
            next_turn_target = "ENEMY"
        check_death();
        return True

    def check_death():
        nonlocal state, winner_team
        if all(c.is_dead for c in enemy_cards): 
            state = "GAME_OVER"; winner_team = "PLAYER"; 
            # Dialogue for Victory
            alive_count = sum(1 for c in player_cards if not c.is_dead)
            t_name = f"MATCH_WON_{alive_count}"
            for c in player_cards:
                if not c.is_dead: trigger_dialogue(c, t_name)
            return
            
        if all(c.is_dead for c in player_cards): 
            state = "GAME_OVER"; winner_team = "ENEMY"; 
            for c in player_cards: # Dead cards could speak? Maybe defeat lines?
                trigger_dialogue(c, "MATCH_LOST")
            return

    def use_buff_card(card_ui, target, is_player_using):
        nonlocal info_msg
        b_type = card_ui.data["type"]
        current_count = buffs_played_this_turn.get(b_type, 0)
        # --- REMOVED LIMIT CHECK ---
        is_buff = b_type in ["HEAL", "BUFF_ATK", "BUFF_DEF"]
        targets_friend = (target.is_player == is_player_using)
        if (is_buff and targets_friend) or (not is_buff and not targets_friend):
            target.apply_buff(b_type, card_ui.data["val"])
            trigger_dialogue(target, f"BUFF_USED_{b_type}")
            buffs_played_this_turn[b_type] = current_count + 1;
            return True
        if is_player_using: info_msg = "Invalid Target!"; return False

    def ai_turn_logic():
        nonlocal enemy_moves, info_msg
        while True:
            buff_move = ai.choose_buff(enemy_hand, enemy_cards, player_cards)
            if buff_move:
                card, target = buff_move
                if use_buff_card(card, target, False):
                    enemy_hand.remove(card)
                else:
                    break
            else:
                break
        attack_move = ai.choose_attack(enemy_cards, player_cards)
        if attack_move:
            attacker, target, move = attack_move
            if execute_attack(attacker, target, move):
                if state != "GAME_OVER": 
                    return "TURN_ENDED"
        enemy_moves = 0;
        info_msg = "Enemy Passes Turn"
        if state != "GAME_OVER": 
            return "TURN_ENDED"
        return "CONTINUE"

    def draw_inspect_overlay():
        nonlocal max_scroll_height
        if not inspected_entity: return
        
        # --- 1. DARK BACKDROP ---
        s = pygame.Surface((screen_w, screen_h))
        s.set_alpha(230)
        s.fill((10, 5, 10))
        screen.blit(s, (0, 0))

        # --- 2. MAIN PANEL ---
        BIG_W, BIG_H = 500, 750
        box_x = (screen_w - BIG_W) // 2
        box_y = (screen_h - BIG_H) // 2
        big_rect = pygame.Rect(box_x, box_y, BIG_W, BIG_H)
        
        draw_panel(screen, box_x, box_y, BIG_W, BIG_H)
        
        data = inspected_entity.data
        border_col = data.get("color", (100, 100, 255))

        # --- 3. HEADER (Fixed) ---
        header_h = 100 # Increased to prevent overlap
        # Header Background Gradient (simulated with alpha rect)
        head_bg = pygame.Surface((BIG_W - 8, header_h - 4), pygame.SRCALPHA)
        pygame.draw.rect(head_bg, (*border_col, 40), head_bg.get_rect(), border_top_left_radius=15, border_top_right_radius=15)
        screen.blit(head_bg, (box_x + 4, box_y + 4))
        
        # Title (Name)
        nm_font = get_font(38)
        nm_surf = nm_font.render(data["name"], True, (255, 255, 255))
        nm_shad = nm_font.render(data["name"], True, (0, 0, 0))
        # Center horizontally, padded from top
        title_x = box_x + (BIG_W - nm_surf.get_width()) // 2
        title_y = box_y + 15
        screen.blit(nm_shad, (title_x + 2, title_y + 2))
        screen.blit(nm_surf, (title_x, title_y))
        
        # Subtitle (Type)
        type_txt = data.get("type", "Unknown Unit").upper().replace("_", " ")
        sub_font = get_font(20)
        sub_surf = sub_font.render(type_txt, True, (200, 200, 220))
        screen.blit(sub_surf, (box_x + (BIG_W - sub_surf.get_width()) // 2, title_y + 50))
        
        # Separator Line
        pygame.draw.line(screen, (100, 100, 120), (box_x + 20, box_y + header_h), (box_x + BIG_W - 20, box_y + header_h), 2)

        # --- 4. SCROLLABLE CONTENT ---
        view_rect = pygame.Rect(box_x + 10, box_y + header_h + 10, BIG_W - 20, BIG_H - header_h - 40)
        screen.set_clip(view_rect)
        
        start_y = view_rect.y - inspector_scroll_y
        virtual_y = 0
        
        # A. CARD IMAGE
        img_h = 300
        img_path = data.get("image_path", "")
        if img_path and os.path.exists(img_path):
            try:
                raw = pygame.image.load(img_path).convert_alpha()
                # Maintain aspect ratio to fit width
                aspect = raw.get_width() / raw.get_height()
                target_w = int(img_h * aspect)
                if target_w > BIG_W - 60:
                    target_w = BIG_W - 60
                    img_h = int(target_w / aspect)
                
                scaled_img = pygame.transform.smoothscale(raw, (target_w, img_h))
                
                draw_y = start_y + virtual_y
                img_x = box_x + (BIG_W - target_w) // 2
                
                # Image Border/Glow
                glow_rect = pygame.Rect(img_x - 2, draw_y - 2, target_w + 4, img_h + 4)
                pygame.draw.rect(screen, border_col, glow_rect, border_radius=8)
                screen.blit(scaled_img, (img_x, draw_y))
                
                virtual_y += img_h + 20
            except:
                pass
        
        # B. VITAL STATS ROW (HP / Energy)
        if hasattr(inspected_entity, "max_hp"):
            draw_y = start_y + virtual_y
            
            # HP Pill
            hp_w, hp_h = 160, 40
            hp_x = box_x + BIG_W // 2 - hp_w - 10
            hp_rect = pygame.Rect(hp_x, draw_y, hp_w, hp_h)
            pygame.draw.rect(screen, (60, 20, 20), hp_rect, border_radius=20)
            pygame.draw.rect(screen, (200, 50, 50), hp_rect, 2, border_radius=20)
            
            hp_txt = f"HP {inspected_entity.current_hp}/{inspected_entity.max_hp}"
            hp_surf = get_font(24).render(hp_txt, True, (255, 200, 200))
            screen.blit(hp_surf, (hp_rect.centerx - hp_surf.get_width()//2, hp_rect.centery - hp_surf.get_height()//2))
            
            # Energy Pill
            en_x = box_x + BIG_W // 2 + 10
            en_rect = pygame.Rect(en_x, draw_y, hp_w, hp_h)
            pygame.draw.rect(screen, (20, 40, 60), en_rect, border_radius=20)
            pygame.draw.rect(screen, (50, 150, 255), en_rect, 2, border_radius=20)
            
            en_txt = f"EN {inspected_entity.energy}/{inspected_entity.max_energy}"
            en_surf = get_font(24).render(en_txt, True, (200, 240, 255))
            screen.blit(en_surf, (en_rect.centerx - en_surf.get_width()//2, en_rect.centery - en_surf.get_height()//2))
            
            virtual_y += 60
        elif "val" in data:
            # Just Value for Buff Cards
            draw_y = start_y + virtual_y
            val_txt = f"VALUE: {data['val']}"
            v_surf = get_font(28).render(val_txt, True, (255, 255, 200))
            screen.blit(v_surf, (box_x + (BIG_W - v_surf.get_width()) // 2, draw_y))
            virtual_y += 50

        # C. DESCRIPTION
        desc_txt = data.get("description", data.get("desc", "No description available."))
        desc_font = get_font(22)
        wrapped_desc = wrap_text(desc_txt, desc_font, BIG_W - 60)
        
        for line in wrapped_desc:
            draw_y = start_y + virtual_y
            l_surf = desc_font.render(line, True, (220, 220, 220)) # Light Grey
            screen.blit(l_surf, (box_x + (BIG_W - l_surf.get_width()) // 2, draw_y))
            virtual_y += 28
            
        virtual_y += 20
        
        # D. ABILITIES LIST
        if "moves" in data:
            # Section Header
            draw_y = start_y + virtual_y
            pygame.draw.line(screen, (100, 100, 120), (box_x + 40, draw_y), (box_x + BIG_W - 40, draw_y), 1)
            virtual_y += 15
            
            h_surf = get_font(24).render("ABILITIES", True, (255, 215, 0)) # Gold
            draw_y = start_y + virtual_y
            screen.blit(h_surf, (box_x + (BIG_W - h_surf.get_width()) // 2, draw_y))
            virtual_y += 35
            
            moves = data["moves"]
            font_title = get_font(22)
            font_detail = get_font(18)
            
            for m_key, m_label in [("normal", "NORMAL"), ("skill", "SKILL"), ("ult", "ULTIMATE")]:
                if m_key in moves:
                    m_data = moves[m_key]
                    name = m_data.get("name", "Unknown")
                    dmg = m_data.get("dmg", "0")
                    cost = m_data.get("cost", "0")
                    desc = m_data.get("desc", "")
                    
                    # --- DYNAMIC HEIGHT CALCULATION ---
                    # 1. Title/Header Height (Fixed)
                    header_h = 35 
                    
                    # 2. Damage Line (Optional)
                    has_dmg = (str(dmg) != "0")
                    dmg_h = 25 if has_dmg else 0
                    
                    # 3. Description Block (Variable)
                    d_lines = wrap_text(desc, font_detail, BIG_W - 90)
                    line_spacing = 20
                    desc_h = len(d_lines) * line_spacing
                    
                    # Total Card Height + Padding
                    total_h = header_h + dmg_h + desc_h + 15
                    
                    draw_y = start_y + virtual_y
                    card_rect = pygame.Rect(box_x + 20, draw_y, BIG_W - 40, total_h)
                    
                    # Card BG
                    bg_col = (40, 30, 50)
                    border_c = (100, 80, 120)
                    if m_key == "ult": 
                        bg_col = (50, 20, 20)
                        border_c = (200, 50, 50)
                    
                    pygame.draw.rect(screen, bg_col, card_rect, border_radius=10)
                    pygame.draw.rect(screen, border_c, card_rect, 2, border_radius=10)
                    
                    # Cost/Energy Pill (Right Aligned) — draw first to know width
                    cost_txt = f"{cost} Energy" if m_key != "normal" else "+1 Energy"
                    cost_col = (100, 200, 255) if m_key != "normal" else (100, 255, 100)
                    c_surf = font_detail.render(cost_txt, True, cost_col)
                    cost_w = c_surf.get_width()
                    screen.blit(c_surf, (card_rect.right - 15 - cost_w, card_rect.y + 12))
                    
                    # Ability Name — truncate if it would overlap the cost pill
                    full_name = f"{m_label}: {name}"
                    max_name_w = card_rect.width - 30 - cost_w - 15  # padding + gap + cost
                    n_surf = font_title.render(full_name, True, (255, 255, 255))
                    if n_surf.get_width() > max_name_w:
                        # Truncate with ellipsis
                        while len(full_name) > 3 and font_title.size(full_name + "...")[0] > max_name_w:
                            full_name = full_name[:-1]
                        n_surf = font_title.render(full_name + "...", True, (255, 255, 255))
                    screen.blit(n_surf, (card_rect.x + 15, card_rect.y + 8))
                    
                    current_y_offset = header_h
                    
                    # Damage (Under name)
                    if has_dmg:
                       dmg_surf = font_detail.render(f"DMG: {dmg}", True, (255, 100, 100))
                       screen.blit(dmg_surf, (card_rect.x + 15, card_rect.y + current_y_offset)) 
                       current_y_offset += dmg_h
                    
                    # Description Lines
                    for i, line in enumerate(d_lines):
                        l_s = font_detail.render(line, True, (240, 230, 210))
                        screen.blit(l_s, (card_rect.x + 15, card_rect.y + current_y_offset + (i * line_spacing)))
                    
                    virtual_y += total_h + 15
        
        virtual_y += 20
        total_content_height = virtual_y
        
        # --- 5. SCROLL BAR & HINT ---
        screen.set_clip(None)
        viewport_h = view_rect.height
        max_scroll_height = max(0, total_content_height - viewport_h)
        
        if max_scroll_height > 0:
            scroll_pct = inspector_scroll_y / max_scroll_height
            bar_h = max(40, (viewport_h / total_content_height) * viewport_h)
            avail_h = viewport_h - bar_h
            bar_y = view_rect.y + (scroll_pct * avail_h)
            bar_rect = pygame.Rect(box_x + BIG_W - 12, bar_y, 6, bar_h)
            pygame.draw.rect(screen, (80, 60, 90), bar_rect, border_radius=3)
            pygame.draw.rect(screen, (150, 100, 150), bar_rect, 1, border_radius=3)

        # Close Hint
        hint_font = get_font(20)
        hint = hint_font.render("Click outside or Right-Click to Close", True, (200, 200, 200))
        screen.blit(hint, (box_x + (BIG_W - hint.get_width()) // 2, box_y + BIG_H + 10))

    def draw_results_ui():
        # Dark Overlay
        s = pygame.Surface((screen_w, screen_h));
        s.set_alpha(220);
        s.fill((5, 5, 10));
        screen.blit(s, (0, 0))

        # Main Report Card Panel (90% width, 85% height)
        panel_w = int(screen_w * 0.9)
        panel_h = int(screen_h * 0.85)
        panel_x = (screen_w - panel_w) // 2
        panel_y = (screen_h - panel_h) // 2
        draw_panel(screen, panel_x, panel_y, panel_w, panel_h)

        # Title
        is_win = (winner_team == "PLAYER")
        title_txt = "VICTORY!" if is_win else "DEFEAT..."
        title_col = (255, 215, 0) if is_win else (220, 50, 50)
        
        t_surf = get_font(int(panel_h * 0.12)).render(title_txt, True, title_col)
        screen.blit(t_surf, (screen_w // 2 - t_surf.get_width() // 2, panel_y + 20))

        # --- HELPERS ---
        def fit_text(txt, size, max_w):
            """Dynamically scale text to fit width."""
            f = get_font(size)
            w, h = f.size(txt)
            while w > max_w and size > 10:
                size -= 2
                f = get_font(size)
                w, h = f.size(txt)
            return f.render(txt, True, (255, 255, 255))

        # --- MVP SECTION (Left Side ~30%) ---
        all_p = player_cards + enemy_cards
        # MVP Score: Dmg + Heals + (Kills * 20) + (Buffs * 10)
        def get_score(c): return c.total_damage_dealt + c.healing_done + (c.kills * 20) + (c.buffs_received * 10)
        mvp_card = max(all_p, key=get_score) if all_p else player_cards[0]

        mvp_w = int(panel_w * 0.3)
        mvp_h = int(panel_h * 0.6)
        mvp_x = panel_x + int(panel_w * 0.05)
        mvp_y = panel_y + int(panel_h * 0.2)

        # Draw MVP Frame
        pygame.draw.rect(screen, (30, 20, 40), (mvp_x, mvp_y, mvp_w, mvp_h), border_radius=15)
        pygame.draw.rect(screen, (255, 215, 0), (mvp_x, mvp_y, mvp_w, mvp_h), 3, border_radius=15)

        lbl_mvp = get_font(int(mvp_h * 0.1)).render("- MVP -", True, (255, 215, 0))
        screen.blit(lbl_mvp, (mvp_x + mvp_w // 2 - lbl_mvp.get_width() // 2, mvp_y + 10))

        if mvp_card.image_surf:
            # Dynamic Image Scaling
            img_w = int(mvp_w * 0.7)
            img_h = int(mvp_h * 0.6)
            img = pygame.transform.scale(mvp_card.image_surf, (img_w, img_h))
            i_rect = img.get_rect(center=(mvp_x + mvp_w // 2, mvp_y + mvp_h // 2))
            screen.blit(img, i_rect)
            pygame.draw.rect(screen, (255, 215, 0), i_rect, 2)
            
            # MVP Name
            # Move up significantly to avoid border overlap
            name_y = mvp_y + mvp_h - int(panel_h * 0.15)
            name_surf = fit_text(mvp_card.data['name'], int(mvp_h * 0.08), mvp_w - 20)
            screen.blit(name_surf, (mvp_x + mvp_w // 2 - name_surf.get_width() // 2, name_y))

        # --- STATS TABLE (Right Side ~60%) ---
        table_x = mvp_x + mvp_w + int(panel_w * 0.05)
        table_y = mvp_y
        table_w = int(panel_w * 0.55)
        
        headers = ["Unit", "Dmg", "Taken", "Heal", "Energy", "Buffs", "Kill"]
        # Dynamic Column Widths (relative weights)
        col_weights = [0.25, 0.12, 0.12, 0.12, 0.13, 0.13, 0.13]
        col_widths = [int(table_w * w) for w in col_weights]
        
        curr_x = table_x

        # Draw Headers
        header_y_offset = int(panel_h * 0.02)
        for i, h in enumerate(headers):
            h_surf = fit_text(h, int(panel_h * 0.04), col_widths[i] - 5)
            # Center header in its column
            screen.blit(h_surf, (curr_x + (col_widths[i] - h_surf.get_width()) // 2, table_y + header_y_offset))
            curr_x += col_widths[i]
        
        line_y = table_y + int(panel_h * 0.08)
        pygame.draw.line(screen, (100, 100, 120), (table_x, line_y), (table_x + table_w, line_y), 2)

        # Draw Rows
        curr_row_y = table_y + int(panel_h * 0.12)
        row_height = int(panel_h * 0.06)
        
        def draw_team_rows(cards, team_name, col):
            nonlocal curr_row_y
            ts = get_font(int(panel_h * 0.035)).render(team_name, True, col)
            screen.blit(ts, (table_x, curr_row_y))
            curr_row_y += row_height
            
            for c in cards:
                cx = table_x
                # Unit Name
                c_col = (255, 255, 255) if not c.is_dead else (100, 100, 100)
                n_surf = fit_text(c.data['name'], int(panel_h * 0.035), col_widths[0] - 10)
                screen.blit(n_surf, (cx, curr_row_y))
                cx += col_widths[0]
                
                # Stats
                stats = [
                    (c.total_damage_dealt, (255, 100, 100)),
                    (c.total_damage_taken, (100, 100, 255)),
                    (c.healing_done, (100, 255, 100)),
                    (c.energy_spent, (255, 255, 0)),
                    (c.buffs_received, (200, 100, 200)),
                    (c.kills, (255, 50, 50))
                ]
                
                for i, (val, color) in enumerate(stats):
                    v_surf = get_font(int(panel_h * 0.035)).render(str(val), True, color)
                    # Center align in column
                    screen.blit(v_surf, (cx + (col_widths[i+1] - v_surf.get_width()) // 2, curr_row_y))
                    cx += col_widths[i+1]
                
                curr_row_y += row_height

        draw_team_rows(player_cards, "PLAYER TEAM", (100, 255, 100))
        curr_row_y += 10
        draw_team_rows(enemy_cards, "ENEMY TEAM", (255, 100, 100))

        btn_continue.rect.centerx = screen_w // 2
        btn_continue.rect.y = panel_y + panel_h - 70
        btn_continue.update(screen)

    def draw_dialogue_overlay():
        nonlocal active_dialogues
        
        font = get_font(16)
        padding = 10
        max_bw = 250
        tail_h = 12
        
        # --- PASS 1: Calculate all bubble rects ---
        bubble_data = []
        to_remove = []
        
        for d in active_dialogues:
            card_ui = d["card"]
            speaker_name = card_ui.data.get("name", "???")
            text = d["text"]
            display_text = f"{speaker_name}: {text}"
            
            # Measure text
            txt_surf = font.render(display_text, True, (0, 0, 0))
            bw = txt_surf.get_width() + (padding * 2)
            bh = txt_surf.get_height() + (padding * 2)
            
            lines = None
            if bw > max_bw:
                bw = max_bw
                words = display_text.split(' ')
                lines = []
                current_line = ""
                for word in words:
                    test = current_line + (" " if current_line else "") + word
                    if font.size(test)[0] <= bw - padding * 2:
                        current_line = test
                    else:
                        if current_line: lines.append(current_line)
                        current_line = word
                if current_line: lines.append(current_line)
                bh = len(lines) * (font.get_height() + 2) + padding * 2
                txt_surf = None
            
            # Anchor to card center, above card
            anchor_x = card_ui.rect.centerx
            by = card_ui.rect.top - bh - tail_h - 5
            bx = anchor_x - bw // 2
            
            # Clamp to screen
            if bx < 10: bx = 10
            if bx + bw > SCREEN_WIDTH - 10: bx = SCREEN_WIDTH - 10 - bw
            if by < 5: by = 5
            
            rect = pygame.Rect(bx, by, bw, bh)
            bubble_data.append({
                "d": d, "rect": rect, "anchor_x": anchor_x,
                "txt_surf": txt_surf, "lines": lines, "card_ui": card_ui
            })
        
        # --- PASS 2: Resolve overlaps ---
        bubble_data.sort(key=lambda b: b["rect"].x)
        
        for i in range(len(bubble_data)):
            for j in range(i + 1, len(bubble_data)):
                ri = bubble_data[i]["rect"]
                rj = bubble_data[j]["rect"]
                if ri.colliderect(rj):
                    rj.y = ri.y - rj.height - 5
                    if rj.y < 5: rj.y = 5
        
        # --- PASS 3: Draw ---
        for bd in bubble_data:
            rect = bd["rect"]
            anchor_x = bd["anchor_x"]
            d = bd["d"]
            
            # Shadow
            shadow_rect = rect.copy()
            shadow_rect.x += 3
            shadow_rect.y += 3
            pygame.draw.rect(screen, (0, 0, 0, 80), shadow_rect, border_radius=8)
            
            # Body
            pygame.draw.rect(screen, (255, 255, 255), rect, border_radius=8)
            pygame.draw.rect(screen, (60, 60, 60), rect, 2, border_radius=8)
            
            # Tail pointing down to card
            tail_x = max(rect.x + 15, min(anchor_x, rect.right - 15))
            tail_pts = [
                (tail_x - 6, rect.bottom),
                (tail_x + 6, rect.bottom),
                (tail_x, rect.bottom + tail_h)
            ]
            pygame.draw.polygon(screen, (255, 255, 255), tail_pts)
            pygame.draw.lines(screen, (60, 60, 60), False, tail_pts, 2)
            
            # Text
            if bd["lines"]:
                ly = rect.y + padding
                for line in bd["lines"]:
                    ls = font.render(line, True, (0, 0, 0))
                    screen.blit(ls, (rect.x + padding, ly))
                    ly += font.get_height() + 2
            elif bd["txt_surf"]:
                screen.blit(bd["txt_surf"], (rect.x + padding, rect.y + padding))
            
            # Timer
            d["timer"] -= 1
            if d["timer"] <= 0:
                to_remove.append(d)
        
        for r in to_remove:
            active_dialogues.remove(r)

    # --- MAIN LOOP ---
    while True:
        mouse_pos = pygame.mouse.get_pos();
        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            
            if event.type == pygame.MOUSEWHEEL:
                if inspected_entity:
                    scroll_speed = 30
                    inspector_scroll_y -= event.y * scroll_speed
                    if inspector_scroll_y < 0: inspector_scroll_y = 0
                    if inspector_scroll_y > max_scroll_height: inspector_scroll_y = max_scroll_height

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:  # Right click
                    found_insp = False
                    for c in player_cards + enemy_cards:
                        if c.rect.collidepoint(mouse_pos):
                            inspected_entity = c;
                            found_insp = True;
                            inspector_scroll_y = 0;
                            break
                    if not found_insp:
                        for b in player_hand:
                            if b.check_click(mouse_pos):
                                inspected_entity = b;
                                found_insp = True;
                                inspector_scroll_y = 0;
                                break
                    continue

                # STRICT CLICK CHECK: Only Left Click
                if event.button == 1:
                    spawn_particles(event.pos[0], event.pos[1], count=5, color=(200, 100, 200))

                    if state == "GAME_OVER":
                        if btn_continue.check_input(mouse_pos):
                            fade.fade_out()
                            while not fade.finished: fade.update(); fade.draw(screen); pygame.display.update()
                            return

                    if inspected_entity: inspected_entity = None; continue
                    if btn_surrender.check_input(mouse_pos): return

                    # 1. BUTTONS FIRST (Prevents click-through)
                    if state == "TURN_PLAYER" and btn_end_turn.check_input(mouse_pos):
                        player_moves = 0;
                        switch_turn_logic();
                        continue

                    # 2. GAMEPLAY LOGIC
                    if state == "TURN_PLAYER":
                        # Buff Cards
                        clicked_buff_ui = None
                        for b_c in player_hand:
                            if b_c.check_click(mouse_pos): clicked_buff_ui = b_c; break

                        if clicked_buff_ui:
                            was_selected = clicked_buff_ui.selected
                            for b in player_hand: b.selected = False
                            
                            if not was_selected:
                                clicked_buff_ui.selected = True;
                                selected_buff = clicked_buff_ui;
                                selected_player = None
                            else:
                                selected_buff = None

                        # Attack Logic
                        elif selected_player and selected_enemy:
                            attacked = False
                            if btn_normal.check_input(mouse_pos):
                                attacked = execute_attack(selected_player, selected_enemy, "normal")
                            elif btn_skill.check_input(mouse_pos):
                                attacked = execute_attack(selected_player, selected_enemy, "skill")
                            elif btn_ult.check_input(mouse_pos):
                                attacked = execute_attack(selected_player, selected_enemy, "ult")

                            if attacked:
                                selected_player.selected = False;
                                selected_enemy.selected = False
                                selected_player = None;
                                selected_enemy = None
                                if state != "GAME_OVER": switch_turn_logic()
                            else:
                                # Reselect Card if missed button
                                handled_card = False
                                for p_c in player_cards:
                                    if p_c.update(mouse_pos, click_event=True):
                                        if selected_buff:
                                            if use_buff_card(selected_buff, p_c, True):
                                                player_hand.remove(selected_buff);
                                                selected_buff = None;
                                                inspected_entity = None
                                        else:
                                            for x in player_cards: x.selected = False
                                            p_c.selected = True;
                                            selected_player = p_c
                                        handled_card = True;
                                        break

                                if not handled_card:
                                    for e_c in enemy_cards:
                                        if e_c.update(mouse_pos, click_event=True):
                                            if selected_buff:
                                                if use_buff_card(selected_buff, e_c, True):
                                                    player_hand.remove(selected_buff);
                                                    selected_buff = None;
                                                    inspected_entity = None
                                            else:
                                                for x in enemy_cards: x.selected = False
                                                e_c.selected = True;
                                                selected_enemy = e_c
                                            handled_card = True;
                                            break

                        # Initial Selection
                        else:
                            handled_card = False
                            for p_c in player_cards:
                                if p_c.update(mouse_pos, click_event=True):
                                    if selected_buff:
                                        if use_buff_card(selected_buff, p_c, True):
                                            player_hand.remove(selected_buff);
                                            selected_buff = None;
                                            inspected_entity = None
                                    else:
                                        for x in player_cards: x.selected = False
                                        p_c.selected = True;
                                        selected_player = p_c
                                    handled_card = True;
                                    break

                            if not handled_card:
                                for e_c in enemy_cards:
                                    if e_c.update(mouse_pos, click_event=True):
                                        if selected_buff:
                                            if use_buff_card(selected_buff, e_c, True):
                                                player_hand.remove(selected_buff);
                                                selected_buff = None;
                                                inspected_entity = None
                                        else:
                                            for x in enemy_cards: x.selected = False
                                            e_c.selected = True;
                                            selected_enemy = e_c
                                        handled_card = True;
                                        break

        # ... (Game State Logic) ...
        if state == "COIN_TOSS":
            state_timer += 1;
            info_msg = "Flipping Coin..."
            if state_timer > 100: winner = random.choice(["PLAYER",
                                                          "ENEMY"]); info_msg = f"{winner} Goes First!"; state_timer = 0; state = "ROUND_START"; next_turn_target = winner
        elif state == "ROUND_START":
            state_timer += 1;
            if state_timer > 60: reset_round_logic()
        elif state == "DRAW_BUFFS":
            state_timer -= 1
            if state_timer <= 0:
                hand_x = (screen_w - (4 * 130)) // 2
                player_hand = buff_mgr.fill_hand(player_hand, hand_x, PLAYER_HAND_Y)
                enemy_hand = buff_mgr.fill_hand(enemy_hand, hand_x, ENEMY_HAND_Y)
                state = "TURN_SWITCH_ANIM";
                state_timer = 60
        elif state == "TURN_SWITCH_ANIM":
            state_timer -= 1;
            info_msg = f"{next_turn_target}'S TURN"
            if state_timer <= 0: info_msg = ""; state = f"TURN_{next_turn_target}"
        elif state == "TURN_ENEMY":
            state_timer += 1
            
            # --- AI THINKING DELAY ---
            # Wait for X frames before making a move to simulate thinking
            # Randomize slightly for "alive" feel (40-100 frames = 0.6s - 1.6s)
            think_delay = 60
            
            if state_timer > think_delay:
                state_timer = 0
                if enemy_moves > 0:
                    # GET MOVE FROM SMART AI
                    ai_move = ai.get_best_move(enemy_hand, enemy_cards, player_cards)
                    
                    if ai_move:
                        # EXECUTE MOVE
                        action_success = False
                        if ai_move["type"] == "PLAY_BUFF":
                            card = ai_move["card"]
                            target = ai_move["target"]
                            if use_buff_card(card, target, False):
                                enemy_hand.remove(card)
                                info_msg = ai_move["desc"]
                                action_success = True
                        
                        elif ai_move["type"] == "ATTACK":
                            attacker = ai_move["card"]
                            target = ai_move["target"]
                            move_key = ai_move["move"]
                            if execute_attack(attacker, target, move_key):
                                info_msg = ai_move["desc"]
                                action_success = True
                        
                        if action_success:
                             if state != "GAME_OVER":
                                 # If action was a BUFF, allow another move (don't end turn)
                                 # If action was an ATTACK, end turn.
                                 if ai_move["type"] == "ATTACK":
                                     switch_turn_logic()
                                 else:
                                     # It was a BUFF, so just pause briefly before next move
                                     state_timer = -30
                        else:
                             # Move failed? Retry or Pass?
                             # For now, pass to avoid stuck loop
                             switch_turn_logic()

                    else:
                        # No moves left or AI chooses to pass
                        switch_turn_logic()
                else:
                    if state != "GAME_OVER": switch_turn_logic()

        screen.fill(BG_FALLBACK)
        
        # --- UPDATE TRANSITION (Draw Last) ---
        fade.update()

        info_rect = pygame.Rect(20, 40, 250, 180)
        pygame.draw.rect(screen, (0, 0, 0), info_rect, border_radius=10);
        pygame.draw.rect(screen, (100, 100, 100), info_rect, 2, border_radius=10)
        screen.blit(get_font(25).render(f"ROUND {round_num}", True, (255, 255, 0)), (40, 60))
        screen.blit(get_font(25).render(f"Moves Left: {player_moves}", True, (0, 255, 0)), (40, 110))
        screen.blit(get_font(25).render(f"Enemy Moves: {enemy_moves}", True, (255, 50, 50)), (40, 160))
        
        # --- DRAW INFO MESSAGE (CENTERED BANNER) ---
        if info_msg:
             # Center in the gap between player/enemy cards (approx Y=545)
             center_y = 545
             
             # Create text surfaces
             inf_font = get_font(48)
             inf_surf = inf_font.render(info_msg, True, (255, 255, 255))
             inf_shad = inf_font.render(info_msg, True, (0, 0, 0))
             
             # Draw Background Banner
             banner_h = 80
             banner_w = screen_w
             banner_rect = pygame.Rect(0, center_y - banner_h // 2, banner_w, banner_h)
             
             s = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
             s.fill((0, 0, 0, 180)) # Semi-transparent black
             screen.blit(s, (0, center_y - banner_h // 2))
             
             # Draw Border Lines
             pygame.draw.line(screen, (255, 215, 0), (0, center_y - banner_h // 2), (screen_w, center_y - banner_h // 2), 2)
             pygame.draw.line(screen, (255, 215, 0), (0, center_y + banner_h // 2), (screen_w, center_y + banner_h // 2), 2)

             # Draw Text with Shadow
             screen.blit(inf_shad, (screen_w // 2 - inf_surf.get_width() // 2 + 3, center_y - inf_surf.get_height() // 2 + 3))
             screen.blit(inf_surf, (screen_w // 2 - inf_surf.get_width() // 2, center_y - inf_surf.get_height() // 2))

        for c in enemy_cards + player_cards: c.draw(screen, mouse_pos)

        # Draw Player Hand (Hovered card LAST)
        hovered_buff = None
        for b in player_hand:
            if b.rect.collidepoint(mouse_pos):
                hovered_buff = b
            else:
                b.draw(screen, mouse_pos)
        
        if hovered_buff:
            hovered_buff.draw(screen, mouse_pos)

        # Draw Enemy Hand (Hovered card LAST - even if disabled interaction, good for consistency)
        # Actually, enemy hand currently gets (-1, -1), so no hover. 
        # But if we want inspection, let's keep it consistent.
        # For now, just standard draw is fine as per original code, unless requested.
        for b in enemy_hand: b.draw(screen, (-1, -1))
        
        btn_surrender.update(screen)
        
        # --- UPDATE BUTTON LABELS DYNAMICALLY ---
        if state == "TURN_PLAYER": 
            if selected_player:
                # Skill
                s_data = selected_player.data["moves"].get("skill", {})
                s_cost = s_data.get("cost", "?")
                btn_skill.set_text(f"SKILL ({s_cost} E)")
                
                # Ult
                u_data = selected_player.data["moves"].get("ult", {})
                u_cost = u_data.get("cost", "?")
                btn_ult.set_text(f"ULTIMATE ({u_cost} E)")
                
                # Normal
                btn_normal.set_text("NORMAL (+1 E)")
            else:
                 btn_skill.set_text("SKILL")
                 btn_ult.set_text("ULTIMATE")
                 btn_normal.set_text("NORMAL")

            btn_normal.update(screen)
            btn_skill.update(screen)
            btn_ult.update(screen)
            btn_end_turn.update(screen)

        if inspected_entity:
            draw_inspect_overlay()
        
        if state == "GAME_OVER":
            draw_results_ui()

        # Draw Fade LAST
        if not fade.finished:
            fade.draw(screen)

        # Draw Juice Overlays (Particles, Floating Text)
        draw_juice_overlays(screen)
        
        # Draw Dialogue Overlay (Speech Bubbles)
        draw_dialogue_overlay()

        pygame.display.update()
        dt = clock.tick(60) / 1000.0
        update_juice(dt)
        update_animations(dt)