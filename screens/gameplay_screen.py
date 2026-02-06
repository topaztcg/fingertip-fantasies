import pygame
import sys
import os
import random
import time
from ui_components import Button, BG_FALLBACK, get_font, FadeLayer, draw_panel
from game_ai import GameAI
from video_player import run_fullscreen_video
from buff_manager import BuffManager

# --- CONSTANTS ---
CARD_W, CARD_H = 180, 270
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
        self.max_energy = int(card_data.get("energy_max", 5))
        self.is_player = is_player
        self.selected = False
        self.is_dead = False

        self.total_damage_dealt = 0
        self.total_damage_taken = 0
        self.kills = 0

        self.temp_atk_boost = 0
        self.temp_def_boost = 0
        self.frozen_turns = 0
        self.dot_turns = 0
        self.dot_val = 0

        self.rect = pygame.Rect(x, y, CARD_W, CARD_H)
        self.hover_scale = 1.0

        self.image_surf = None
        if os.path.exists(card_data["image_path"]):
            try:
                raw = pygame.image.load(card_data["image_path"]).convert_alpha()
                self.image_surf = pygame.transform.scale(raw, (CARD_W, CARD_H))
            except:
                pass

    def reset_round_stats(self):
        self.temp_atk_boost = 0
        self.temp_def_boost = 0
        if self.frozen_turns > 0: self.frozen_turns -= 1
        if self.dot_turns > 0:
            self.take_damage(self.dot_val)
            self.dot_turns -= 1

    def apply_buff(self, buff_type, val):
        if buff_type == "HEAL":
            self.current_hp += val
            if self.current_hp > self.max_hp: self.current_hp = self.max_hp
        elif buff_type == "BUFF_ATK":
            self.temp_atk_boost += val
        elif buff_type == "BUFF_DEF":
            self.temp_def_boost += val
        elif buff_type == "DEBUFF_FREEZE":
            self.frozen_turns += val
        elif buff_type == "DEBUFF_DOT":
            self.dot_turns = 2;
            self.dot_val = val

    def take_damage(self, amount):
        if self.is_dead: return
        actual_dmg = max(0, amount - self.temp_def_boost)
        self.current_hp -= actual_dmg
        self.total_damage_taken += actual_dmg
        if self.current_hp <= 0:
            self.current_hp = 0;
            self.is_dead = True;
            self.selected = False;
            self.frozen_turns = 0;
            self.dot_turns = 0

    def consume_energy(self, cost):
        if self.energy >= cost:
            self.energy -= cost;
            return True
        return False

    def gain_energy(self, amount=1):
        self.energy += amount
        if self.energy > self.max_energy: self.energy = self.max_energy

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
    ai = GameAI()

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
        round_num += 1;
        reset_round_logic()

    def execute_attack(attacker, target, move_type):
        nonlocal info_msg, player_moves, enemy_moves, next_turn_target
        if attacker.frozen_turns > 0: info_msg = "Unit is Frozen!"; return False
        if move_type == "normal":
            attacker.gain_energy(1);
            dmg = 2
        else:
            cost = 2 if move_type == "skill" else 4
            if not attacker.consume_energy(cost): info_msg = "Not Enough Energy!"; return False
            dmg = 4 if move_type == "skill" else 8
        vid = attacker.data["videos"].get(move_type)
        if vid: run_fullscreen_video(screen, vid, show_hint=False)
        tot_dmg = dmg + attacker.temp_atk_boost
        target.take_damage(tot_dmg)
        attacker.temp_atk_boost = 0
        attacker.total_damage_dealt += tot_dmg
        if target.is_dead: attacker.kills += 1
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
        if all(c.is_dead for c in enemy_cards): state = "GAME_OVER"; winner_team = "PLAYER"; return
        if all(c.is_dead for c in player_cards): state = "GAME_OVER"; winner_team = "ENEMY"; return

    def use_buff_card(card_ui, target, is_player_using):
        nonlocal info_msg
        b_type = card_ui.data["type"]
        current_count = buffs_played_this_turn.get(b_type, 0)
        if current_count >= 2:
            if is_player_using: info_msg = f"Limit: 2 {b_type} cards per turn!"
            return False
        is_buff = b_type in ["HEAL", "BUFF_ATK", "BUFF_DEF"]
        targets_friend = (target.is_player == is_player_using)
        if (is_buff and targets_friend) or (not is_buff and not targets_friend):
            target.apply_buff(b_type, card_ui.data["val"])
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
                if state != "GAME_OVER": switch_turn_logic(); return
        enemy_moves = 0;
        info_msg = "Enemy Passes Turn"
        if state != "GAME_OVER": switch_turn_logic()

    def draw_inspect_overlay():
        nonlocal max_scroll_height
        if not inspected_entity: return
        s = pygame.Surface((screen_w, screen_h));
        s.set_alpha(200);
        s.fill((0, 0, 0));
        screen.blit(s, (0, 0))
        BIG_W, BIG_H = 400, 650
        box_x = (screen_w - BIG_W) // 2;
        box_y = (screen_h - BIG_H) // 2
        big_rect = pygame.Rect(box_x, box_y, BIG_W, BIG_H)
        draw_panel(screen, big_rect)
        data = inspected_entity.data
        border_col = data.get("color", (100, 100, 255))
        header_height = 60
        header_surf = pygame.Surface((BIG_W - 10, header_height), pygame.SRCALPHA)
        header_surf.fill((*border_col, 100))
        screen.blit(header_surf, (box_x + 5, box_y + 5))

        # FIXED: White Text for Header
        nm_surf = get_font(30).render(data["name"], True, (255, 255, 255))
        nm_shad = get_font(30).render(data["name"], True, (0, 0, 0))
        screen.blit(nm_shad, (big_rect.centerx - nm_surf.get_width() // 2 + 2, box_y + 17))
        screen.blit(nm_surf, (big_rect.centerx - nm_surf.get_width() // 2, box_y + 15))

        view_rect = pygame.Rect(box_x + 10, box_y + header_height + 10, BIG_W - 20, BIG_H - header_height - 20)
        screen.set_clip(view_rect)
        start_y_pos = view_rect.y;
        virtual_y = 0

        img_path = data.get("image_path", "")
        if img_path and os.path.exists(img_path):
            try:
                raw = pygame.image.load(img_path).convert_alpha()
                img_h = 240
                big_img = pygame.transform.scale(raw, (BIG_W - 60, img_h))
                draw_y = start_y_pos + virtual_y - inspector_scroll_y
                pygame.draw.rect(screen, (20, 20, 30),
                                 (big_rect.centerx - (BIG_W - 56) // 2, draw_y - 2, BIG_W - 56, img_h + 4))
                img_rect = big_img.get_rect(center=(big_rect.centerx, draw_y + img_h // 2))
                screen.blit(big_img, img_rect)
                virtual_y += img_h + 20
            except:
                virtual_y += 200

        if hasattr(inspected_entity, "max_hp"):
            draw_y = start_y_pos + virtual_y - inspector_scroll_y
            stats_y = draw_y;
            icon_radius = 22
            hp_center = (big_rect.left + 80, stats_y + 20)
            pygame.draw.circle(screen, (180, 0, 0), hp_center, icon_radius);
            pygame.draw.circle(screen, (255, 255, 255), hp_center, icon_radius, 2)
            # FIXED: White Text for Stats
            hp_str = f"{inspected_entity.current_hp}/{inspected_entity.max_hp}"
            hp_surf = get_font(26).render(hp_str, True, (255, 255, 255))
            screen.blit(hp_surf, (hp_center[0] + 35, hp_center[1] - 15))

            en_center = (big_rect.right - 100, stats_y + 20)
            pygame.draw.circle(screen, (0, 100, 200), en_center, icon_radius);
            pygame.draw.circle(screen, (255, 255, 255), en_center, icon_radius, 2)
            en_str = f"{inspected_entity.energy}/{inspected_entity.max_energy}"
            en_surf = get_font(26).render(en_str, True, (255, 255, 255))
            screen.blit(en_surf, (en_center[0] + 35, en_center[1] - 15))
            virtual_y += 60
        elif "type" in data:
            draw_y = start_y_pos + virtual_y - inspector_scroll_y
            type_str = f"TYPE: {data['type']} | VAL: {data['val']}"
            # FIXED: White Text
            t_surf = get_font(22).render(type_str, True, (220, 220, 220))
            screen.blit(t_surf, (big_rect.centerx - t_surf.get_width() // 2, draw_y + 10))
            virtual_y += 50

        virtual_y += 10
        desc_txt = data.get("description", data.get("desc", "No description"))
        font_desc = get_font(20)
        wrapped_lines = wrap_text(desc_txt, font_desc, BIG_W - 60)
        for line in wrapped_lines:
            draw_y = start_y_pos + virtual_y - inspector_scroll_y
            # FIXED: White Text for Description
            line_surf = font_desc.render(line, True, (255, 255, 255))
            screen.blit(line_surf, (big_rect.centerx - line_surf.get_width() // 2, draw_y))
            virtual_y += 25

        if "moves" in data:
            virtual_y += 25
            draw_y = start_y_pos + virtual_y - inspector_scroll_y
            pygame.draw.line(screen, (180, 180, 200), (big_rect.left + 30, draw_y), (big_rect.right - 30, draw_y), 2)
            virtual_y += 15
            draw_y = start_y_pos + virtual_y - inspector_scroll_y
            moves = data["moves"]
            font_skill = get_font(18);
            font_header = get_font(22)
            h_surf = font_header.render("ABILITIES", True, (255, 255, 100))
            screen.blit(h_surf, (big_rect.centerx - h_surf.get_width() // 2, draw_y))
            virtual_y += 35
            for m_key, m_label in [("normal", "NORMAL"), ("skill", "SKILL"), ("ult", "ULTIMATE")]:
                if m_key in moves:
                    draw_y = start_y_pos + virtual_y - inspector_scroll_y
                    m_data = moves[m_key]
                    name = m_data.get("name", "Unknown");
                    dmg = m_data.get("dmg", "0");
                    cost = m_data.get("cost", "0") if m_key != "normal" else "+1"

                    # FIXED: White Text for Ability Names
                    n_surf = font_skill.render(f"{m_label}: {name}", True, (240, 240, 240));
                    screen.blit(n_surf, (big_rect.left + 30, draw_y))
                    virtual_y += 22;
                    draw_y = start_y_pos + virtual_y - inspector_scroll_y
                    stats_x = big_rect.left + 30
                    d_surf = font_skill.render(f"DMG: {dmg}", True, (255, 100, 100));
                    screen.blit(d_surf, (stats_x, draw_y))
                    if m_key == "normal":
                        c_surf = font_skill.render(f" (Generates {cost} Energy)", True, (100, 255, 100))
                    else:
                        c_surf = font_skill.render(f" | COST: {cost}", True, (100, 200, 255))
                    screen.blit(c_surf, (stats_x + d_surf.get_width() + 5, draw_y))
                    virtual_y += 22;
                    s_desc = m_data.get("desc", "");
                    s_lines = wrap_text(s_desc, font_skill, BIG_W - 60)
                    for sl in s_lines:
                        draw_y = start_y_pos + virtual_y - inspector_scroll_y
                        # FIXED: Light Grey for Skill Desc
                        sl_surf = font_skill.render(sl, True, (200, 200, 200))
                        screen.blit(sl_surf, (stats_x, draw_y));
                        virtual_y += 20
                    virtual_y += 25
        virtual_y += 20
        total_content_height = virtual_y;
        viewport_h = view_rect.height;
        max_scroll_height = max(0, total_content_height - viewport_h)
        screen.set_clip(None)
        if max_scroll_height > 0:
            scroll_pct = inspector_scroll_y / max_scroll_height
            bar_h = max(30, (viewport_h / total_content_height) * viewport_h)
            avail_h = viewport_h - bar_h
            bar_y = view_rect.y + (scroll_pct * avail_h)
            bar_rect = pygame.Rect(big_rect.right - 15, bar_y, 8, bar_h)
            pygame.draw.rect(screen, (150, 100, 150), bar_rect, border_radius=4)
        hint = get_font(18).render("Scroll for more | Click to Close", True, (255, 255, 255))
        hint_s = get_font(18).render("Scroll for more | Click to Close", True, (0, 0, 0))
        screen.blit(hint_s, (big_rect.centerx - hint.get_width() // 2 + 1, big_rect.bottom + 11))
        screen.blit(hint, (big_rect.centerx - hint.get_width() // 2, big_rect.bottom + 10))

    def draw_results_ui():
        s = pygame.Surface((screen_w, screen_h));
        s.set_alpha(245);
        s.fill((10, 5, 20));
        screen.blit(s, (0, 0))
        txt = "VICTORY!" if winner_team == "PLAYER" else "DEFEAT..."
        col = (255, 215, 0) if winner_team == "PLAYER" else (200, 50, 50)
        t_surf = get_font(90).render(txt, True, col);
        screen.blit(t_surf, (screen_w // 2 - t_surf.get_width() // 2, 30))
        all_p = player_cards + enemy_cards
        mvp_card = max(all_p, key=lambda c: c.total_damage_dealt) if all_p else player_cards[0]
        if mvp_card.image_surf:
            big_img = pygame.transform.scale(mvp_card.image_surf, (220, 330));
            mvp_rect = big_img.get_rect(topleft=(150, 200))
            screen.blit(big_img, mvp_rect);
            pygame.draw.rect(screen, (255, 215, 0), mvp_rect, 5)
            lbl = get_font(40).render("MVP", True, (255, 215, 0));
            screen.blit(lbl, (mvp_rect.centerx - lbl.get_width() // 2, 150))
            name = get_font(30).render(mvp_card.data['name'], True, (255, 255, 255));
            screen.blit(name, (mvp_rect.centerx - name.get_width() // 2, mvp_rect.bottom + 10))
            d_txt = get_font(24).render(f"Dmg: {mvp_card.total_damage_dealt}", True, (255, 100, 100));
            screen.blit(d_txt, (mvp_rect.centerx - d_txt.get_width() // 2, mvp_rect.bottom + 45))
        tx, ty = 650, 200;
        headers = ["Unit", "Dmg Dealt", "Taken", "Kills", "Status"];
        off_x = [0, 220, 420, 550, 680]
        for i, h in enumerate(headers): screen.blit(get_font(26).render(h, True, (200, 200, 255)), (tx + off_x[i], ty))
        pygame.draw.line(screen, (100, 100, 100), (tx, ty + 40), (tx + 850, ty + 40), 2)
        curr_y = ty + 60;
        screen.blit(get_font(25).render("PLAYER", True, (100, 255, 100)), (tx - 120, curr_y))
        for c in player_cards:
            screen.blit(get_font(24).render(c.data['name'], True, (255, 255, 255)), (tx, curr_y))
            screen.blit(get_font(24).render(str(c.total_damage_dealt), True, (255, 100, 100)), (tx + 250, curr_y))
            screen.blit(get_font(24).render(str(c.total_damage_taken), True, (100, 100, 255)), (tx + 440, curr_y))
            screen.blit(get_font(24).render(str(c.kills), True, (255, 255, 0)), (tx + 570, curr_y))
            status = "Alive" if not c.is_dead else "Dead";
            col_s = (100, 255, 100) if not c.is_dead else (100, 100, 100)
            screen.blit(get_font(24).render(status, True, col_s), (tx + 680, curr_y));
            curr_y += 40
        curr_y += 30;
        screen.blit(get_font(25).render("ENEMY", True, (255, 100, 100)), (tx - 120, curr_y))
        for c in enemy_cards:
            screen.blit(get_font(24).render(c.data['name'], True, (255, 255, 255)), (tx, curr_y))
            screen.blit(get_font(24).render(str(c.total_damage_dealt), True, (255, 100, 100)), (tx + 250, curr_y))
            screen.blit(get_font(24).render(str(c.total_damage_taken), True, (100, 100, 255)), (tx + 440, curr_y))
            screen.blit(get_font(24).render(str(c.kills), True, (255, 255, 0)), (tx + 570, curr_y))
            status = "Alive" if not c.is_dead else "Dead";
            col_s = (100, 255, 100) if not c.is_dead else (100, 100, 100)
            screen.blit(get_font(24).render(status, True, col_s), (tx + 680, curr_y));
            curr_y += 40
        btn_continue.update(screen)

    while True:
        mouse_pos = pygame.mouse.get_pos();
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT: sys.exit()

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
                            for b in player_hand: b.selected = False
                            clicked_buff_ui.selected = True;
                            selected_buff = clicked_buff_ui;
                            selected_player = None

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
                hand_x = (screen_w - (5 * 130)) // 2
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
            if state_timer > 40:
                state_timer = 0
                if enemy_moves > 0:
                    ai_turn_logic()
                else:
                    if state != "GAME_OVER": switch_turn_logic()

        screen.fill(BG_FALLBACK)
        info_rect = pygame.Rect(20, 40, 250, 180)
        pygame.draw.rect(screen, (0, 0, 0), info_rect, border_radius=10);
        pygame.draw.rect(screen, (100, 100, 100), info_rect, 2, border_radius=10)
        screen.blit(get_font(25).render(f"ROUND {round_num}", True, (255, 255, 0)), (40, 60))
        screen.blit(get_font(25).render(f"Moves Left: {player_moves}", True, (0, 255, 0)), (40, 110))
        screen.blit(get_font(25).render(f"Enemy Moves: {enemy_moves}", True, (255, 50, 50)), (40, 160))

        for c in enemy_cards + player_cards: c.draw(screen, mouse_pos)
        for b in player_hand: b.draw(screen, mouse_pos)
        for b in enemy_hand: b.draw(screen, (-1, -1))
        btn_surrender.update(screen)
        if state == "TURN_PLAYER": btn_normal.update(screen); btn_skill.update(screen); btn_ult.update(
            screen); btn_end_turn.update(screen)

        if state == "TURN_SWITCH_ANIM":
            s = pygame.Surface((screen_w, 150));
            s.set_alpha(180);
            s.fill((0, 0, 0));
            screen.blit(s, (0, screen_h // 2 - 75))
            col = (100, 255, 100) if next_turn_target == "PLAYER" else (255, 100, 100)
            txt = get_font(80).render(f"{next_turn_target}'S TURN", True, col);
            screen.blit(txt, (screen_w // 2 - txt.get_width() // 2, screen_h // 2 - 40))
        elif info_msg and not inspected_entity:
            msg = get_font(40).render(info_msg, True, (255, 255, 255));
            bg = msg.get_rect(center=(screen_w // 2, screen_h // 2)).inflate(40, 20)
            pygame.draw.rect(screen, (0, 0, 0, 180), bg, border_radius=15);
            screen.blit(msg, msg.get_rect(center=bg.center))

        if state == "GAME_OVER": draw_results_ui(); btn_continue.change_color(mouse_pos)
        draw_inspect_overlay()
        fade.update();
        fade.draw(screen)
        pygame.display.update();
        clock.tick(60)