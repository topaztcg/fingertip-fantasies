import pygame
import tkinter as tk
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tkinter import filedialog
from ui_components import Button, InputBox, TEXT_COLOR, BG_FALLBACK, PROFILE_BG, BUTTON_BORDER, get_font, update_animations, spawn_particles, update_juice, draw_juice_overlays, COLOR_PASSIVE, TEXT_SHADOW
from user_manager import UserManager


def get_image_from_pc():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select New Avatar",
        filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")]
    )
    root.destroy()
    return file_path


def show_profile_screen(screen, player_id, is_own_profile=True):
    clock = pygame.time.Clock()
    user_mgr = UserManager()
    
    from leaderboard_manager import LeaderboardManager
    lb_mgr = LeaderboardManager()
    
    # Get REAL stats from LeaderboardManager
    p_data = lb_mgr.get_player_data(player_id)
    is_bot = p_data.get("is_bot", False)
    display_name = p_data.get("name", player_id)
    
    original_username = display_name
            
    if is_bot:
        is_own_profile = False
        bot_config = lb_mgr.fake_players.get(player_id)
        raw_avatar = None
        if bot_config and bot_config.get("pfp_path") and os.path.exists(bot_config["pfp_path"]):
            raw_avatar = pygame.image.load(bot_config["pfp_path"]).convert_alpha()
        stats = {}
    else:
        raw_avatar = user_mgr.get_avatar_image(player_id)
        stats = user_mgr.get_user_stats(player_id)
        
    stats["wins"] = p_data.get("wins", stats.get("wins", 0))
    stats["losses"] = p_data.get("losses", stats.get("losses", 0))
    stats["games_played"] = p_data.get("games_played", stats.get("games_played", 0))
    
    global_rank = lb_mgr.get_player_rank(player_id)
    
    league_id = p_data.get("league", "unranked")
    league_name = league_id.upper()
    for l in lb_mgr.leagues:
        if l["id"] == league_id:
            league_name = l["name"]
            break
            
    league_rank = lb_mgr.get_player_league_rank(player_id, league_id)
    
    stats["global_rank"] = global_rank
    stats["league_id"] = league_id
    stats["league_name"] = league_name
    stats["league_rank"] = league_rank

    editing_mode = False
    viewing_fullscreen = False
    league_rect = pygame.Rect(-1000, -1000, 0, 0)

    temp_avatar_surf = None
    # Input box now uses theme colors automatically from ui_components
    input_name = InputBox(0, 0, 300, 50, text=original_username)

    def get_display_avatar(raw, temp):
        source = temp if temp else raw
        if source:
            return pygame.transform.scale(source, (350, 350))
        s = pygame.Surface((350, 350))
        s.fill(COLOR_PASSIVE)  # Soft Lilac placeholder
        return s

    def get_fullscreen_avatar(raw, temp):
        source = temp if temp else raw
        if source:
            return pygame.transform.scale(source, (900, 900))
        return None

    card_w, card_h = 1000, 700
    card_rect = pygame.Rect((screen.get_width() - card_w) // 2, (screen.get_height() - card_h) // 2, card_w, card_h)

    # Shift Avatar down to clear the name
    avatar_rect = pygame.Rect(card_rect.x + 80, card_rect.y + 160, 350, 350)
    
    input_name.rect.x = card_rect.x + 50
    input_name.rect.y = card_rect.y + 40
    input_name.rect.w = 350

    btn_back = Button("BACK", 50, 50, 150, 50, font_size=30)
    btn_edit = Button("EDIT PROFILE", card_rect.right - 250, card_rect.y + 40, 200, 50, font_size=25)

    btn_save = Button("SAVE", card_rect.centerx - 210, card_rect.bottom - 80, 200, 50, font_size=30)
    btn_cancel = Button("CANCEL", card_rect.centerx + 10, card_rect.bottom - 80, 200, 50, font_size=30)

    font_name = get_font(65) # Slightly reduced for fit
    font_stats = get_font(32) # Reduced for fitting long ranks
    font_small = get_font(28)

    status_msg = ""

    while True:
        dt = clock.tick(60) / 1000.0
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()

        for event in events:
            if event.type == pygame.QUIT:
                return None

            if editing_mode:
                input_name.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    spawn_particles(event.pos[0], event.pos[1], count=5, color=(200, 100, 200))

                if viewing_fullscreen:
                    viewing_fullscreen = False
                else:
                    if btn_back.check_input(mouse_pos):
                        return None

                    if editing_mode:
                        if btn_save.check_input(mouse_pos):
                            new_name = input_name.get_text().strip()
                            success, msg = user_mgr.update_user_profile(original_username, new_name, temp_avatar_surf)
                            if success:
                                return ("UPDATE_USER", new_name)
                            else:
                                status_msg = msg

                        if btn_cancel.check_input(mouse_pos):
                            editing_mode = False
                            temp_avatar_surf = None
                            input_name.text = original_username
                            input_name.txt_surface = input_name.font.render(original_username, True, input_name.color)
                            status_msg = ""

                        if avatar_rect.collidepoint(mouse_pos):
                            path = get_image_from_pc()
                            if path:
                                try:
                                    raw = pygame.image.load(path).convert_alpha()
                                    temp_avatar_surf = pygame.transform.scale(raw, (800, 800))
                                except:
                                    status_msg = "Error loading image"

                    else:
                        if is_own_profile and btn_edit.check_input(mouse_pos):
                            editing_mode = True
                            status_msg = ""

                        if avatar_rect.collidepoint(mouse_pos):
                            viewing_fullscreen = True
                            
                        # Check League click
                        if league_rect.collidepoint(mouse_pos):
                            return ("OPEN_LEADERBOARD", stats.get("league_id", "unranked"))

        if viewing_fullscreen:
            screen.fill((0, 0, 0))
            fs_img = get_fullscreen_avatar(raw_avatar, temp_avatar_surf)
            if fs_img:
                fs_x = (screen.get_width() - fs_img.get_width()) // 2
                fs_y = (screen.get_height() - fs_img.get_height()) // 2
                screen.blit(fs_img, (fs_x, fs_y))
                pygame.draw.rect(screen, BUTTON_BORDER, (fs_x, fs_y, fs_img.get_width(), fs_img.get_height()), 5)

            hint = font_stats.render("Click anywhere to close", True, TEXT_COLOR)
            screen.blit(hint, (screen.get_width() // 2 - hint.get_width() // 2, screen.get_height() - 50))

        else:
            # Dark overlay
            overlay = pygame.Surface((screen.get_width(), screen.get_height()))
            overlay.set_alpha(150)
            overlay.fill(BG_FALLBACK)
            screen.blit(overlay, (0, 0))

            # Card BG - Use Panel Style
            s = pygame.Surface((card_rect.width, card_rect.height))
            s.set_alpha(230)
            s.fill(PROFILE_BG)
            screen.blit(s, (card_rect.x, card_rect.y))
            
            # --- FIXED: Use Profile BG Panel ---
            pygame.draw.rect(screen, BUTTON_BORDER, card_rect, 4, border_radius=20)
            pygame.draw.rect(screen, (255, 255, 255), card_rect, 1, border_radius=20) # Inner white stroke for definition

            disp_avatar = get_display_avatar(raw_avatar, temp_avatar_surf)
            screen.blit(disp_avatar, avatar_rect)

            # Green border if editing, otherwise Pink
            border_col = (100, 255, 100) if editing_mode else BUTTON_BORDER
            pygame.draw.rect(screen, border_col, avatar_rect, 3)

            # Username Display
            name_y = card_rect.y + 40
            if editing_mode:
                input_name.rect.y = name_y
                input_name.update()
                input_name.draw(screen)

                # --- FIXED: Better visual cue for uploading ---
                # Draw a semi transparent band at bottom of avatar
                upload_band = pygame.Surface((350, 50))
                upload_band.set_alpha(200)
                upload_band.fill(PROFILE_BG)
                screen.blit(upload_band, (avatar_rect.x, avatar_rect.bottom - 50))

                hint = font_small.render("CLICK TO UPLOAD", True, (255, 255, 255))
                screen.blit(hint, (avatar_rect.centerx - hint.get_width() // 2, avatar_rect.bottom - 38))
            else:
                # Render Username with Shadow/Outline for pop
                name_surf = font_name.render(original_username, True, TEXT_COLOR)
                name_shad = font_name.render(original_username, True, TEXT_SHADOW)
                
                # Position
                name_pos = (card_rect.x + 50, name_y)
                screen.blit(name_shad, (name_pos[0] + 2, name_pos[1] + 2))
                screen.blit(name_surf, name_pos)

            # Stats Panel (Right Side)
            stats_x = avatar_rect.right + 80
            stats_y = avatar_rect.y
            stats_w = card_rect.right - stats_x - 40
            stats_h = avatar_rect.height
            
            # Semi-transparent stats background
            stats_bg = pygame.Surface((stats_w, stats_h))
            stats_bg.set_alpha(50)
            stats_bg.fill(COLOR_PASSIVE) # Soft Lilac tint
            screen.blit(stats_bg, (stats_x, stats_y))
            pygame.draw.rect(screen, BUTTON_BORDER, (stats_x, stats_y, stats_w, stats_h), 2, border_radius=10)

            stats_list = [
                ("Global Rank", f"#{stats.get('global_rank', 'N/A')}"),
                ("League", f"{stats.get('league_name', 'N/A')} (#{stats.get('league_rank', 'N/A')})"),
                ("Wins", str(stats.get('wins', 0))),
                ("Losses", str(stats.get('losses', 0))),
                ("Games", str(stats.get('games_played', 0)))
            ]
            
            for i, (label, val) in enumerate(stats_list):
                line_y = stats_y + 25 + (i * 55)
                
                # Label
                lbl_col = (255, 180, 220)
                if label == "League": lbl_col = (200, 200, 255) # distinguish it
                lbl_surf = font_stats.render(f"{label}:", True, lbl_col)
                screen.blit(lbl_surf, (stats_x + 20, line_y))
                
                # Value
                val_surf = font_stats.render(val, True, TEXT_COLOR)
                val_x = stats_x + 20 + lbl_surf.get_width() + 15
                screen.blit(val_surf, (val_x, line_y))
                
                if label == "League":
                    # Capture rect for clicking
                    league_rect = pygame.Rect(stats_x + 20, line_y, lbl_surf.get_width() + 15 + val_surf.get_width(), 40)
                    # Draw a subtle underline on hover
                    if league_rect.collidepoint(mouse_pos):
                        pygame.draw.line(screen, (200, 200, 255), (stats_x + 20, line_y + 35), (val_x + val_surf.get_width(), line_y + 35), 2)

            if status_msg:
                msg = font_small.render(status_msg, True, (255, 100, 100))
                screen.blit(msg, (card_rect.x + 50, card_rect.bottom - 130))

            if editing_mode:
                btn_save.change_color(mouse_pos)
                btn_save.update(screen)
                btn_cancel.change_color(mouse_pos)
                btn_cancel.update(screen)
            else:
                # Update Edit Button Position dynamically to align with Username
                # But keep it simple for now, fixed position top right is okay
                if is_own_profile:
                    btn_edit.change_color(mouse_pos)
                    btn_edit.update(screen)

            btn_back.change_color(mouse_pos)
            btn_back.update(screen)

        update_animations(dt)
        update_juice(dt)
        draw_juice_overlays(screen)
        pygame.display.update()