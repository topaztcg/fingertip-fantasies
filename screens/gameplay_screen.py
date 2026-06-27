import pygame
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import random
import time
import pytweening
from ui_components import Button, BG_FALLBACK, BUTTON_BORDER, TEXT_COLOR, get_font, update_animations, draw_panel, spawn_particles, update_juice, draw_juice_overlays, spawn_floating_text, shake_screen, AnimationManager, FadeLayer, TEXT_SHADOW, PROFILE_BG
from game_ai import SmartAI
from video_player import VideoWrapper, run_fullscreen_video
from buff_manager import BuffManager, BuffCardUI
from dialogue_manager import DialogueManager
from leaderboard_manager import LeaderboardManager
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


def show_gameplay_screen(screen, player_deck_data, current_user, opp=None):
    clock = pygame.time.Clock()
    buff_mgr = BuffManager()
    ai = SmartAI()
    lb_mgr = LeaderboardManager()
    
    # --- LOAD HUD AVATARS ---
    from user_manager import UserManager
    from screens.profile_screen import show_profile_screen
    u_mgr = UserManager()
    player_pfp = u_mgr.get_avatar_image(current_user)
    if player_pfp: player_pfp = pygame.transform.scale(player_pfp, (100, 100))
    
    enemy_id = opp["id"] if opp else "bot_ai"
    enemy_name = opp["name"] if opp else "ENEMY"
    enemy_league = opp["league"] if opp else "unranked"
    enemy_pfp = None
    if opp and opp.get("pfp_path") and os.path.exists(opp["pfp_path"]):
        try: enemy_pfp = pygame.transform.scale(pygame.image.load(opp["pfp_path"]).convert_alpha(), (100, 100))
        except: pass
    
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

    btn_w, btn_h = 280, 65;
    ui_x = screen_w - btn_w - 30;
    ui_y_start = screen_h - 450
    btn_normal = Button("NORMAL (+1 E)", ui_x, ui_y_start, btn_w, btn_h, font_size=22)
    btn_skill = Button("SKILL (2 E)", ui_x, ui_y_start + 80, btn_w, btn_h, font_size=22)
    btn_ult = Button("ULTIMATE (4 E)", ui_x, ui_y_start + 160, btn_w, btn_h, font_size=22)
    btn_end_turn = Button("END ROUND", ui_x, ui_y_start + 250, btn_w, btn_h, font_size=26)
    btn_surrender = Button("SURRENDER", screen_w - 220, 30, 200, 50, font_size=22)
    btn_continue = Button("RETURN TO MENU", screen_w - 350, screen_h - 100, 320, 70, font_size=32)

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
    ai_action_queue = None
    results_view_mode = "SUMMARY" # or "STATS"
    btn_toggle_results = Button("VIEW COMBAT STATS", screen_w // 2 - 150, 100, 300, 50, font_size=20)
    match_recorded = False

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
        attacker.total_damage_dealt += tot_dmg
        
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
        s.fill(BG_FALLBACK)
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
        nm_shad = nm_font.render(data["name"], True, TEXT_SHADOW)
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
        pygame.draw.line(screen, BUTTON_BORDER, (box_x + 20, box_y + header_h), (box_x + BIG_W - 20, box_y + header_h), 2)

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
            pygame.draw.rect(screen, PROFILE_BG, hp_rect, border_radius=20)
            pygame.draw.rect(screen, (255, 100, 150), hp_rect, 2, border_radius=20)
            
            hp_txt = f"HP {inspected_entity.current_hp}/{inspected_entity.max_hp}"
            hp_surf = get_font(24).render(hp_txt, True, (255, 200, 200))
            screen.blit(hp_surf, (hp_rect.centerx - hp_surf.get_width()//2, hp_rect.centery - hp_surf.get_height()//2))
            
            # Energy Pill
            en_x = box_x + BIG_W // 2 + 10
            en_rect = pygame.Rect(en_x, draw_y, hp_w, hp_h)
            pygame.draw.rect(screen, PROFILE_BG, en_rect, border_radius=20)
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
            pygame.draw.line(screen, BUTTON_BORDER, (box_x + 40, draw_y), (box_x + BIG_W - 40, draw_y), 1)
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
                    bg_col = PROFILE_BG
                    border_c = BUTTON_BORDER
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
            pygame.draw.rect(screen, BUTTON_BORDER, bar_rect, border_radius=3)
            pygame.draw.rect(screen, (150, 100, 150), bar_rect, 1, border_radius=3)

        # Close Hint
        hint_font = get_font(20)
        hint = hint_font.render("Click outside or Right-Click to Close", True, (200, 200, 200))
        screen.blit(hint, (box_x + (BIG_W - hint.get_width()) // 2, box_y + BIG_H + 10))

    def draw_results_ui():
        nonlocal results_view_mode
        # Dark Overlay
        s = pygame.Surface((screen_w, screen_h));
        s.set_alpha(240);
        s.fill((5, 5, 10));
        screen.blit(s, (0, 0))

        # Main Report Card Panel (92% width, 92% height)
        panel_w = int(screen_w * 0.92)
        panel_h = int(screen_h * 0.92)
        panel_x = (screen_w - panel_w) // 2
        panel_y = (screen_h - panel_h) // 2
        draw_panel(screen, panel_x, panel_y, panel_w, panel_h)

        # Title
        is_win = (winner_team == "PLAYER")
        title_txt = "VICTORY!" if is_win else "DEFEAT..."
        title_col = (255, 215, 0) if is_win else (220, 50, 50)
        
        # Reduce font size to prevent overlapping
        t_surf = get_font(60).render(title_txt, True, title_col)
        # Add a subtle shadow to title
        t_shad = get_font(60).render(title_txt, True, TEXT_SHADOW)
        
        tx = screen_w // 2 - t_surf.get_width() // 2
        ty = panel_y + 25
        screen.blit(t_shad, (tx + 3, ty + 3))
        screen.blit(t_surf, (tx, ty))

        # Toggle Button
        btn_toggle_results.rect.centerx = screen_w // 2
        btn_toggle_results.rect.y = panel_y + 115
        btn_toggle_results.update(screen)
        
        if btn_toggle_results.check_input(mouse_pos):
            if pygame.mouse.get_pressed()[0]:
                results_view_mode = "STATS" if results_view_mode == "SUMMARY" else "SUMMARY"
                btn_toggle_results.set_text(f"VIEW {'SUMMARY' if results_view_mode == 'STATS' else 'COMBAT STATS'}")
                pygame.time.delay(200) # Simple debounce

        # --- HELPERS ---
        def fit_text(txt, size, max_w):
            f = get_font(size)
            w, h = f.size(txt)
            while w > max_w and size > 10:
                size -= 2
                f = get_font(size)
                w, h = f.size(txt)
            return f.render(txt, True, (255, 255, 255))

        if results_view_mode == "SUMMARY":
            # --- SUMMARY VIEW (BIG PFPS & POINTS) ---
            cy = panel_y + 370
            p1_x = panel_x + panel_w // 4
            p2_x = panel_x + (panel_w // 4) * 3
            
            p_pts = "+25 PTS" if is_win else "-15 PTS"
            e_pts = "-15 PTS" if is_win else "+25 PTS"
            p_col = (100, 255, 100) if is_win else (255, 100, 100)
            e_col = (255, 100, 100) if is_win else (100, 255, 100)
            
            # Draw Player Summary
            if player_pfp:
                big_p = pygame.transform.scale(player_pfp, (200, 200))
                pr = big_p.get_rect(center=(p1_x, cy - 80))
                pygame.draw.rect(screen, BUTTON_BORDER, pr.inflate(6, 6), border_radius=10)
                screen.blit(big_p, pr)
            
            p_n = get_font(30).render(current_user, True, (255, 255, 255))
            p_data = lb_mgr.get_player_data(current_user)
            p_l = get_font(20).render(f"LEAGUE: {p_data['league'].upper()}", True, (200, 200, 255))
            p_r = get_font(20).render(f"RANK: #{lb_mgr.get_player_rank(current_user)}", True, (255, 200, 100))
            p_pt = get_font(40).render(p_pts, True, p_col)
            
            screen.blit(p_n, p_n.get_rect(center=(p1_x, cy + 50)))
            screen.blit(p_l, p_l.get_rect(center=(p1_x, cy + 90)))
            screen.blit(p_r, p_r.get_rect(center=(p1_x, cy + 115)))
            screen.blit(p_pt, p_pt.get_rect(center=(p1_x, cy + 160)))
            
            # Draw Enemy Summary
            if enemy_pfp:
                big_e = pygame.transform.scale(enemy_pfp, (200, 200))
                er = big_e.get_rect(center=(p2_x, cy - 80))
                pygame.draw.rect(screen, BUTTON_BORDER, er.inflate(6, 6), border_radius=10)
                screen.blit(big_e, er)
                
            e_n = get_font(30).render(enemy_name, True, (255, 255, 255))
            e_l = get_font(20).render(f"LEAGUE: {enemy_league.upper()}", True, (200, 200, 255))
            e_r = get_font(20).render(f"RANK: #{lb_mgr.get_player_rank(enemy_name)}", True, (255, 200, 100))
            e_pt = get_font(40).render(e_pts, True, e_col)
            
            screen.blit(e_n, e_n.get_rect(center=(p2_x, cy + 50)))
            screen.blit(e_l, e_l.get_rect(center=(p2_x, cy + 90)))
            screen.blit(e_r, e_r.get_rect(center=(p2_x, cy + 115)))
            screen.blit(e_pt, e_pt.get_rect(center=(p2_x, cy + 160)))
            
            # VS Text
            vs = get_font(60).render("VS", True, (150, 150, 150))
            screen.blit(vs, vs.get_rect(center=(panel_x + panel_w // 2, cy - 50)))

        else:
            # --- COMBAT STATS VIEW (MVP box + Table) ---
            # MVP Left Box (approx 350px width)
            mvp_w = 350
            mvp_rect = pygame.Rect(panel_x + 30, panel_y + 180, mvp_w, panel_h - 260)
            pygame.draw.rect(screen, (30, 30, 40), mvp_rect, border_radius=10)
            pygame.draw.rect(screen, BUTTON_BORDER, mvp_rect, 2, border_radius=10)
            
            mvp_title = get_font(30).render("MATCH MVP", True, (255, 215, 0))
            screen.blit(mvp_title, (mvp_rect.centerx - mvp_title.get_width()//2, mvp_rect.top + 10))
            
            # Find MVP (highest dmg)
            all_c = player_cards + enemy_cards
            mvp = max(all_c, key=lambda c: c.total_damage_dealt)
            
            mvp_img_path = mvp.data.get("image_path")
            
            mvp_owner = current_user if mvp in player_cards else enemy_name
            mvp_owner_col = (100, 255, 100) if mvp in player_cards else (255, 100, 100)
            
            if mvp_img_path and os.path.exists(mvp_img_path):
                try:
                    m_img = pygame.transform.scale(pygame.image.load(mvp_img_path).convert_alpha(), (150, 225))
                    img_rect = m_img.get_rect(center=(mvp_rect.centerx, mvp_rect.top + 175))
                    
                    pygame.draw.rect(screen, BUTTON_BORDER, img_rect.inflate(6, 6), border_radius=8)
                    screen.blit(m_img, img_rect)
                    
                    m_name = get_font(28).render(mvp.data["name"], True, (255, 255, 255))
                    screen.blit(m_name, (mvp_rect.centerx - m_name.get_width()//2, img_rect.bottom + 10))
                    
                    m_owner = get_font(20).render(f"Team: {mvp_owner}", True, mvp_owner_col)
                    screen.blit(m_owner, (mvp_rect.centerx - m_owner.get_width()//2, img_rect.bottom + 40))
                    
                    m_dmg = get_font(24).render(f"Damage: {mvp.total_damage_dealt}", True, (255, 100, 100))
                    screen.blit(m_dmg, (mvp_rect.centerx - m_dmg.get_width()//2, img_rect.bottom + 65))
                except:
                    pass
            
            # STATS TABLE (Takes rest of the space)
            table_x = panel_x + 30 + mvp_w + 30
            table_y = panel_y + 180
            table_w = panel_w - (30 + mvp_w + 30) - 30
            
            headers = ["Unit", "Dmg", "Taken", "Heal", "Energy", "Buffs", "Kill"]
            col_weights = [0.25, 0.12, 0.12, 0.12, 0.13, 0.13, 0.13]
            col_widths = [int(table_w * w) for w in col_weights]
            
            curr_x = table_x
            
            # Header Background Bar
            hdr_bg = pygame.Surface((table_w, 40), pygame.SRCALPHA)
            pygame.draw.rect(hdr_bg, (40, 40, 60, 200), hdr_bg.get_rect(), border_radius=5)
            screen.blit(hdr_bg, (table_x, table_y))

            # Draw Headers
            header_y_offset = 8
            for i, h in enumerate(headers):
                h_surf = fit_text(h, 22, col_widths[i] - 5)
                # Render in gold for a premium feel
                h_surf = get_font(22).render(h, True, (255, 215, 0))
                screen.blit(h_surf, (curr_x + (col_widths[i] - h_surf.get_width()) // 2, table_y + header_y_offset))
                curr_x += col_widths[i]
            
            line_y = table_y + 45
            pygame.draw.line(screen, BUTTON_BORDER, (table_x, line_y), (table_x + table_w, line_y), 2)

            # Draw Rows
            curr_row_y = line_y + 10
            row_height = 40
            
            row_idx = 0
            def draw_team_rows(cards, team_name, col):
                nonlocal curr_row_y, row_idx
                
                # Team Header Pill
                t_surf = pygame.Surface((table_w, row_height), pygame.SRCALPHA)
                pygame.draw.rect(t_surf, (*col, 40), t_surf.get_rect(), border_radius=8)
                pygame.draw.rect(t_surf, (*col, 150), t_surf.get_rect(), 1, border_radius=8)
                screen.blit(t_surf, (table_x, curr_row_y))
                
                ts = get_font(25).render(team_name, True, col)
                screen.blit(ts, (table_x + 10, curr_row_y + (row_height - ts.get_height()) // 2))
                curr_row_y += row_height + 8
                
                for c in cards:
                    if row_idx % 2 == 0:
                        z_surf = pygame.Surface((table_w, row_height), pygame.SRCALPHA)
                        pygame.draw.rect(z_surf, (0, 0, 0, 60), z_surf.get_rect(), border_radius=4)
                        screen.blit(z_surf, (table_x, curr_row_y))
                    
                    cx = table_x
                    c_col = TEXT_COLOR if not c.is_dead else (150, 120, 150)
                    n_surf = get_font(22).render(c.data['name'][:10], True, c_col)
                    screen.blit(n_surf, (cx + 5, curr_row_y + (row_height - n_surf.get_height()) // 2))
                    cx += col_widths[0]
                    
                    stats = [
                        (c.total_damage_dealt, (255, 180, 180)),
                        (c.total_damage_taken, (180, 180, 255)),
                        (c.healing_done, (180, 255, 180)),
                        (c.energy_spent, (255, 255, 180)),
                        (c.buffs_received, (220, 180, 220)),
                        (c.kills, (255, 100, 100))
                    ]
                    
                    for i, (val, color) in enumerate(stats):
                        if c.is_dead: color = (120, 100, 120)
                        v_surf = get_font(22).render(str(val), True, color)
                        screen.blit(v_surf, (cx + (col_widths[i+1] - v_surf.get_width()) // 2, curr_row_y + (row_height - v_surf.get_height()) // 2))
                        cx += col_widths[i+1]
                    
                    curr_row_y += row_height + 4
                    row_idx += 1

            draw_team_rows(player_cards, "PLAYER TEAM", (100, 255, 100))
            curr_row_y += 15
            draw_team_rows(enemy_cards, "ENEMY TEAM", (255, 100, 100))

        btn_continue.rect.centerx = screen_w // 2
        btn_continue.rect.y = panel_y + panel_h - 60
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
        if state == "GAME_OVER" and not match_recorded:
            total_dmg = sum(c.total_damage_dealt for c in player_cards)
            is_win = (winner_team == "PLAYER")
            
            p_mvp = max(player_cards, key=lambda c: c.total_damage_dealt) if player_cards else None
            p_mvp_id = p_mvp.data["id"] if p_mvp else None
            opp_name = opp["name"] if opp else "Unknown"
            
            lb_mgr.record_match(current_user, is_win, total_dmg, opp_name, p_mvp_id)
            
            # Record Enemy Match
            if opp and opp.get("is_bot"):
                enemy_dmg = sum(c.total_damage_dealt for c in enemy_cards)
                e_mvp = max(enemy_cards, key=lambda c: c.total_damage_dealt) if enemy_cards else None
                e_mvp_id = e_mvp.data["id"] if e_mvp else None
                
                lb_mgr.record_match(opp["id"], not is_win, enemy_dmg, current_user, e_mvp_id)
                
            match_recorded = True
            
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
                            
                        # Handle PFP Clicks in Results Screen (Summary Mode)
                        if results_view_mode == "SUMMARY":
                            panel_w = int(screen_w * 0.9)
                            panel_h = int(screen_h * 0.85)
                            panel_x = (screen_w - panel_w) // 2
                            panel_y = (screen_h - panel_h) // 2
                            cy = panel_y + 350
                            
                            p1_x = panel_x + panel_w // 4
                            p1_rect = pygame.Rect(0, 0, 200, 200)
                            p1_rect.center = (p1_x, cy - 80)
                            
                            p2_x = panel_x + (panel_w // 4) * 3
                            p2_rect = pygame.Rect(0, 0, 200, 200)
                            p2_rect.center = (p2_x, cy - 80)
                            
                            if p1_rect.collidepoint(mouse_pos):
                                show_profile_screen(screen, current_user)
                                continue
                            if p2_rect.collidepoint(mouse_pos):
                                enemy_id = opp["id"] if opp else None
                                if enemy_id:
                                    show_profile_screen(screen, enemy_id)
                                continue

                    if inspected_entity: inspected_entity = None; continue
                    if btn_surrender.check_input(mouse_pos): return
                    
                    # Handle PFP Clicks in HUD (During Match)
                    p_hud_rect = pygame.Rect(18, PLAYER_CARD_Y - 2, 104, 104)
                    e_hud_rect = pygame.Rect(screen_w - 132, ENEMY_CARD_Y - 2, 104, 104)
                    if p_hud_rect.collidepoint(mouse_pos):
                        show_profile_screen(screen, current_user)
                        continue
                    if e_hud_rect.collidepoint(mouse_pos):
                        show_profile_screen(screen, enemy_id)
                        continue

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
                    # CALCULATE FULL SEQUENCE IF NEEDED
                    if ai_action_queue is None:
                        ai_action_queue = ai.get_turn_actions(enemy_hand, enemy_cards, player_cards)
                    
                    if ai_action_queue:
                        # POP AND EXECUTE NEXT ACTION
                        action = ai_action_queue.pop(0)
                        action_success = False
                        
                        if action[0] == "BUFF":
                            _, card, target = action
                            if use_buff_card(card, target, False):
                                enemy_hand.remove(card)
                                info_msg = f"Enemy used {card.data.get('name', 'Buff')}!"
                                action_success = True
                        
                        elif action[0] == "ATTACK":
                            _, attacker, target, move_key = action
                            if execute_attack(attacker, target, move_key):
                                info_msg = f"Enemy used {move_key.upper()}!"
                                action_success = True
                        
                        if action_success:
                             if state != "GAME_OVER":
                                 # If action was a BUFF, allow another move (don't end turn)
                                 # If action was an ATTACK, end turn.
                                 if action[0] == "ATTACK":
                                     ai_action_queue = None
                                     switch_turn_logic()
                                 else:
                                     # It was a BUFF, so just pause briefly before next move
                                     state_timer = -30
                        else:
                             # Move failed? Clear queue to avoid stuck loop
                             ai_action_queue = None
                             switch_turn_logic()

                    else:
                        # No moves left or AI chooses to pass
                        ai_action_queue = None
                        switch_turn_logic()
                else:
                    ai_action_queue = None
                    if state != "GAME_OVER": switch_turn_logic()

        screen.fill(BG_FALLBACK)
        
        # --- UPDATE TRANSITION (Draw Last) ---
        fade.update()
        
        # --- DRAW HUD PFPS & NAMES ---
        hud_font = get_font(28)
        
        # Player (Left Side, near player cards)
        p_hud_y = PLAYER_CARD_Y
        if player_pfp:
            pygame.draw.rect(screen, BUTTON_BORDER, (18, p_hud_y - 2, 104, 104), border_radius=8)
            screen.blit(player_pfp, (20, p_hud_y))
        ps = hud_font.render(current_user, True, (100, 255, 100))
        screen.blit(ps, (20, p_hud_y + 110))
        
        # Enemy (Right Side, near enemy cards)
        e_hud_y = ENEMY_CARD_Y
        e_hud_x = screen_w - 130
        if enemy_pfp:
            pygame.draw.rect(screen, BUTTON_BORDER, (e_hud_x - 2, e_hud_y - 2, 104, 104), border_radius=8)
            screen.blit(enemy_pfp, (e_hud_x, e_hud_y))
        es = hud_font.render(enemy_name, True, (255, 100, 100))
        screen.blit(es, (e_hud_x, e_hud_y + 110))

        info_rect = pygame.Rect(20, 40, 250, 180)
        pygame.draw.rect(screen, PROFILE_BG, info_rect, border_radius=10);
        pygame.draw.rect(screen, BUTTON_BORDER, info_rect, 2, border_radius=10)
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
             inf_shad = inf_font.render(info_msg, True, TEXT_SHADOW)
             
             # Draw Background Banner
             banner_h = 80
             banner_w = screen_w
             banner_rect = pygame.Rect(0, center_y - banner_h // 2, banner_w, banner_h)
             
             s = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
             s.fill((PROFILE_BG[0], PROFILE_BG[1], PROFILE_BG[2], 180)) # Semi-transparent theme bg
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