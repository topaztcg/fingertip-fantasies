import pygame
import tkinter as tk
import sys
import os
import time
import math
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

def draw_glass_panel(screen, rect, alpha=150):
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, (30, 25, 40, alpha), s.get_rect(), border_radius=15)
    pygame.draw.rect(s, (255, 105, 180, 80), s.get_rect(), 2, border_radius=15) # Girly pink border
    screen.blit(s, rect.topleft)

def _show_fullscreen_image(screen, img_surf, clock):
    w, h = screen.get_size()
    
    # Scale image to fit within the screen while maintaining aspect ratio
    iw, ih = img_surf.get_size()
    scale = min(w / iw, h / ih)
    new_w, new_h = int(iw * scale), int(ih * scale)
    scaled_img = pygame.transform.scale(img_surf, (new_w, new_h))
    
    img_x = w // 2 - new_w // 2
    img_y = h // 2 - new_h // 2
    
    # Draw dark overlay once
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 230))
    screen.blit(overlay, (0, 0))
    screen.blit(scaled_img, (img_x, img_y))
    pygame.display.update()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                running = False
                
        clock.tick(60)

def show_profile_screen(screen, player_id, is_own_profile=True):
    clock = pygame.time.Clock()
    user_mgr = UserManager()
    from leaderboard_manager import LeaderboardManager
    lb_mgr = LeaderboardManager()
    from card_manager import CardManager
    cm = CardManager()
    
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
    stats["points"] = p_data.get("points", 0)
    
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

    match_history = p_data.get("match_history", [])

    # Playstyle Algorithm
    playstyle = {
        "Aggression": 0.5,
        "Vitality": 0.5,
        "Execution": 0.5,
        "Burst": 0.5,
        "Efficiency": 0.5
    }

    if match_history:
        # Execution = Win Rate of last 20 matches
        recent_20 = match_history[-20:]
        wins = sum(1 for m in recent_20 if m.get("win"))
        playstyle["Execution"] = min(1.0, max(0.1, wins / max(1, len(recent_20))))
        
        # Analyze MVP cards
        mvp_ids = [m.get("mvp_card") for m in recent_20 if m.get("mvp_card")]
        if mvp_ids:
            avg_hp = 0
            avg_norm_dmg = 0
            avg_ult_dmg = 0
            avg_ult_cost = 0
            valid_cards = 0
            
            for cid in mvp_ids:
                cdata = cm.get_card(cid)
                if cdata:
                    valid_cards += 1
                    avg_hp += cdata.get("max_hp", 100)
                    avg_norm_dmg += int(cdata.get("moves", {}).get("normal", {}).get("dmg", 0))
                    avg_ult_dmg += int(cdata.get("moves", {}).get("ult", {}).get("dmg", 0))
                    avg_ult_cost += int(cdata.get("moves", {}).get("ult", {}).get("cost", 5))
                    
            if valid_cards > 0:
                avg_hp /= valid_cards
                avg_norm_dmg /= valid_cards
                avg_ult_dmg /= valid_cards
                avg_ult_cost /= valid_cards
                
                playstyle["Vitality"] = min(1.0, max(0.1, avg_hp / 15.0))
                playstyle["Aggression"] = min(1.0, max(0.1, avg_norm_dmg / 2.0))
                playstyle["Burst"] = min(1.0, max(0.1, avg_ult_dmg / 9.0))
                playstyle["Efficiency"] = min(1.0, max(0.1, 1.0 - (avg_ult_cost / 7.0)))
    
    # Calculate favorite card from last 10 matches
    recent_10 = match_history[-10:]
    fav_card_id = None
    if recent_10:
        freqs = {}
        for m in recent_10:
            cid = m.get("mvp_card")
            if cid:
                freqs[cid] = freqs.get(cid, 0) + 1
        if freqs:
            fav_card_id = max(freqs.items(), key=lambda x: x[1])[0]
            
    fav_card_data = cm.get_card(fav_card_id) if fav_card_id else None

    editing_mode = False
    temp_avatar_surf = None
    input_name = InputBox(0, 0, 300, 50, text=original_username)

    def get_display_avatar(raw, temp):
        source = temp if temp else raw
        if source:
            return pygame.transform.scale(source, (300, 300))
        s = pygame.Surface((300, 300))
        s.fill(COLOR_PASSIVE)
        return s

    screen_w, screen_h = screen.get_size()
    pad = 40
    main_w = screen_w - pad*2
    main_h = screen_h - pad*2 - 80
    main_x = pad
    main_y = pad + 80
    
    left_w = 400
    right_w = main_w - left_w - 30
    
    left_rect = pygame.Rect(main_x, main_y, left_w, main_h)
    
    top_right_h = 350
    mid_right_h = 160
    bot_right_h = main_h - top_right_h - mid_right_h - 40
    
    graph_rect = pygame.Rect(main_x + left_w + 30, main_y, right_w, top_right_h)
    fav_rect = pygame.Rect(graph_rect.x, graph_rect.bottom + 20, right_w, mid_right_h)
    hist_rect = pygame.Rect(graph_rect.x, fav_rect.bottom + 20, right_w, bot_right_h)

    avatar_rect = pygame.Rect(left_rect.centerx - 150, left_rect.y + 40, 300, 300)
    
    btn_back = Button("BACK", 40, 30, 150, 50, font_size=30)
    btn_edit = Button("EDIT", left_rect.right - 120, left_rect.y + 15, 100, 40, font_size=20)
    btn_save = Button("SAVE", left_rect.centerx - 110, left_rect.bottom - 70, 100, 40, font_size=20)
    btn_cancel = Button("CANCEL", left_rect.centerx + 10, left_rect.bottom - 70, 100, 40, font_size=20)

    btn_toggle_graph = Button("SWITCH GRAPH", graph_rect.right - 150, graph_rect.y + 10, 130, 35, font_size=16)

    font_name = get_font(40)
    font_stats = get_font(28)
    font_small = get_font(20)

    status_msg = ""
    hist_scroll = 0
    graph_mode = "RADAR"

    while True:
        dt = clock.tick(60) / 1000.0
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()

        for event in events:
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None

            if editing_mode:
                input_name.handle_event(event)
                
            if event.type == pygame.MOUSEWHEEL:
                if hist_rect.collidepoint(mouse_pos):
                    hist_max_scroll = max(0, len(match_history) * 60 - (hist_rect.height - 60))
                    hist_scroll = max(0, min(hist_max_scroll, hist_scroll - event.y * 30))

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    spawn_particles(event.pos[0], event.pos[1], count=5, color=(255, 105, 180))

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
                            
                        if avatar_rect.collidepoint(mouse_pos) and raw_avatar:
                            _show_fullscreen_image(screen, raw_avatar, clock)
                            
                    if btn_toggle_graph.check_input(mouse_pos):
                        graph_mode = "LINE" if graph_mode == "RADAR" else "RADAR"

        screen.fill((15, 10, 20)) # Dark girly aesthetic background
        
        # Soft glowing orbs
        glow1 = pygame.Surface((800, 800), pygame.SRCALPHA)
        pygame.draw.circle(glow1, (255, 20, 147, 10), (400, 400), 400)
        screen.blit(glow1, (-200, -200))
        
        glow2 = pygame.Surface((800, 800), pygame.SRCALPHA)
        pygame.draw.circle(glow2, (138, 43, 226, 10), (400, 400), 400)
        screen.blit(glow2, (screen_w - 600, screen_h - 600))
        
        title = get_font(50).render("PLAYER PROFILE", True, (255, 255, 255))
        screen.blit(title, (main_x + 150, 30))
        
        # --- LEFT PANEL (IDENTITY) ---
        draw_glass_panel(screen, left_rect)
        
        disp_avatar = get_display_avatar(raw_avatar, temp_avatar_surf)
        screen.blit(disp_avatar, avatar_rect)
        border_col = (100, 255, 100) if editing_mode else (255, 105, 180)
        pygame.draw.rect(screen, border_col, avatar_rect, 3, border_radius=5)

        name_y = avatar_rect.bottom + 20
        if editing_mode:
            input_name.rect.x = left_rect.centerx - 150
            input_name.rect.y = name_y
            input_name.rect.w = 300
            input_name.update()
            input_name.draw(screen)

            upload_band = pygame.Surface((300, 50))
            upload_band.set_alpha(200)
            upload_band.fill((0, 0, 0))
            screen.blit(upload_band, (avatar_rect.x, avatar_rect.bottom - 50))
            hint = font_small.render("CLICK TO UPLOAD", True, (255, 255, 255))
            screen.blit(hint, (avatar_rect.centerx - hint.get_width() // 2, avatar_rect.bottom - 38))
        else:
            name_surf = font_name.render(original_username, True, (255, 255, 255))
            name_pos = (left_rect.centerx - name_surf.get_width()//2, name_y)
            screen.blit(name_surf, name_pos)

        # Stats
        stats_y = name_y + 60
        stats_list = [
            ("League", f"{stats.get('league_name', 'N/A')}"),
            ("Global Rank", f"#{stats.get('global_rank', 'N/A')}"),
            ("League Rank", f"#{stats.get('league_rank', 'N/A')}"),
            ("Wins / Losses", f"{stats.get('wins', 0)} / {stats.get('losses', 0)}"),
            ("Win Rate", f"{int(stats.get('wins',0)/(max(1, stats.get('games_played', 1))) * 100)}%"),
            ("Total Points", str(stats.get('points', 0)))
        ]
        
        for i, (lbl, val) in enumerate(stats_list):
            ly = stats_y + i * 40
            lsurf = font_small.render(lbl, True, (255, 180, 220))
            vsurf = font_small.render(val, True, (255, 255, 255))
            screen.blit(lsurf, (left_rect.x + 30, ly))
            screen.blit(vsurf, (left_rect.right - 30 - vsurf.get_width(), ly))
            
        if status_msg:
            msg = font_small.render(status_msg, True, (255, 100, 100))
            screen.blit(msg, (left_rect.centerx - msg.get_width()//2, left_rect.bottom - 110))

        if editing_mode:
            btn_save.change_color(mouse_pos)
            btn_save.update(screen)
            btn_cancel.change_color(mouse_pos)
            btn_cancel.update(screen)
        elif is_own_profile:
            btn_edit.change_color(mouse_pos)
            btn_edit.update(screen)
            
            
        # --- TOP RIGHT PANEL (PERFORMANCE / PLAYSTYLE) ---
        draw_glass_panel(screen, graph_rect)
        if graph_mode == "RADAR":
            screen.blit(font_stats.render("PLAYSTYLE (RADAR)", True, (255, 180, 220)), (graph_rect.x + 20, graph_rect.y + 15))
            btn_toggle_graph.set_text("VIEW LINE GRAPH")
            btn_toggle_graph.change_color(mouse_pos)
            btn_toggle_graph.update(screen)
            
            # Draw Radar Chart
            cx, cy = graph_rect.centerx, graph_rect.centery + 10
            radius = min(graph_rect.width, graph_rect.height) / 2 - 35
            
            labels = ["Aggression", "Vitality", "Execution", "Burst", "Efficiency"]
            angles = [math.radians(-90 + i * 72) for i in range(5)]
            
            # Grid
            for r_ratio in [0.33, 0.66, 1.0]:
                r = radius * r_ratio
                pts = [(cx + math.cos(a)*r, cy + math.sin(a)*r) for a in angles]
                pygame.draw.polygon(screen, (255, 255, 255, 40), pts, 1)
                
            # Axes and Labels
            for i, a in enumerate(angles):
                end_x = cx + math.cos(a) * radius
                end_y = cy + math.sin(a) * radius
                pygame.draw.line(screen, (255, 255, 255, 40), (cx, cy), (end_x, end_y), 1)
                
                lbl_surf = font_small.render(labels[i], True, (255, 180, 220))
                lx = cx + math.cos(a) * (radius + 20) - lbl_surf.get_width()//2
                ly = cy + math.sin(a) * (radius + 20) - lbl_surf.get_height()//2
                screen.blit(lbl_surf, (lx, ly))
                
            # Data Polygon
            data_pts = []
            for i, a in enumerate(angles):
                val = playstyle[labels[i]]
                r = radius * val
                data_pts.append((cx + math.cos(a)*r, cy + math.sin(a)*r))
                
            if data_pts:
                poly_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
                pygame.draw.polygon(poly_surf, (255, 20, 147, 60), data_pts)
                screen.blit(poly_surf, (0,0))
                
                pygame.draw.polygon(screen, (255, 105, 180), data_pts, 3)
                for px, py in data_pts:
                    pygame.draw.circle(screen, (255, 255, 255), (int(px), int(py)), 4)
                    pygame.draw.circle(screen, (255, 20, 147), (int(px), int(py)), 6, 2)
                    
        else:
            screen.blit(font_stats.render("SEASON PERFORMANCE (LINE)", True, (255, 180, 220)), (graph_rect.x + 20, graph_rect.y + 15))
            btn_toggle_graph.set_text("VIEW RADAR")
            btn_toggle_graph.change_color(mouse_pos)
            btn_toggle_graph.update(screen)
            
            # Calculate Graph Data
            points_series = []
            curr_pts = stats.get('points', 0)
            points_series.append(curr_pts)
            for m in reversed(match_history):
                curr_pts -= m.get("points_change", 0)
                points_series.append(curr_pts)
            points_series.reverse()
            
            if len(points_series) < 2:
                points_series = [curr_pts] * 5 # Flat line if not enough data
                
            # Draw Graph
            gx = graph_rect.x + 60
            gw = graph_rect.width - 90
            gy = graph_rect.y + 80
            gh = graph_rect.height - 120
            
            # Axes
            pygame.draw.line(screen, (255, 255, 255, 50), (gx, gy), (gx, gy + gh), 2)
            pygame.draw.line(screen, (255, 255, 255, 50), (gx, gy + gh), (gx + gw, gy + gh), 2)
            
            min_p = min(points_series)
            max_p = max(points_series)
            p_range = max_p - min_p if max_p != min_p else 100
            min_p -= p_range * 0.1
            max_p += p_range * 0.1
            actual_range = max_p - min_p
            
            points_coords = []
            for i, pt in enumerate(points_series):
                x = gx + (i / (len(points_series) - 1)) * gw
                y = gy + gh - ((pt - min_p) / actual_range) * gh
                points_coords.append((x, y))
                
            # Gradient Fill under graph
            if len(points_coords) >= 2:
                fill_coords = [(gx, gy + gh)] + points_coords + [(points_coords[-1][0], gy + gh)]
                fill_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
                pygame.draw.polygon(fill_surf, (255, 20, 147, 40), fill_coords)
                screen.blit(fill_surf, (0, 0))
                
                # Pink Glowing Line
                pygame.draw.lines(screen, (255, 105, 180), False, points_coords, 4)
                for px, py in points_coords:
                    pygame.draw.circle(screen, (255, 255, 255), (int(px), int(py)), 5)
                    pygame.draw.circle(screen, (255, 20, 147), (int(px), int(py)), 7, 2)
                    
            # Axis labels
            screen.blit(font_small.render(str(int(max_p)), True, (150, 150, 150)), (gx - 50, gy - 10))
            screen.blit(font_small.render(str(int(min_p)), True, (150, 150, 150)), (gx - 50, gy + gh - 10))
            
        # --- MID RIGHT PANEL (FAVORITE CARD) ---
        draw_glass_panel(screen, fav_rect)
        screen.blit(font_stats.render("CURRENT FAVORITE CARD", True, (255, 180, 220)), (fav_rect.x + 20, fav_rect.y + 15))
        
        if fav_card_data:
            cimg = cm.get_card_image(fav_card_data["id"])
            if cimg:
                cimg = pygame.transform.scale(cimg, (100, 100))
                screen.blit(cimg, (fav_rect.x + 30, fav_rect.y + 45))
                pygame.draw.rect(screen, (255, 105, 180), (fav_rect.x + 30, fav_rect.y + 45, 100, 100), 2, border_radius=5)
            
            cname = get_font(30).render(fav_card_data["name"], True, (255, 255, 255))
            screen.blit(cname, (fav_rect.x + 150, fav_rect.y + 55))
            csub = font_small.render(f"Based on last 10 matches", True, (150, 150, 150))
            screen.blit(csub, (fav_rect.x + 150, fav_rect.y + 100))
        else:
            screen.blit(font_small.render("Not enough match data to determine favorite card.", True, (150, 150, 150)), (fav_rect.x + 30, fav_rect.y + 70))
        
        
        # --- BOTTOM RIGHT PANEL (MATCH HISTORY) ---
        draw_glass_panel(screen, hist_rect)
        screen.blit(font_stats.render("RECENT MATCHES", True, (255, 180, 220)), (hist_rect.x + 20, hist_rect.y + 15))
        
        screen.set_clip(hist_rect)
        my = hist_rect.y + 60 - hist_scroll
        if not match_history:
            screen.blit(font_small.render("No matches played yet.", True, (150, 150, 150)), (hist_rect.x + 20, hist_rect.y + 60))
        else:
            for m in reversed(match_history):
                if my > hist_rect.y and my < hist_rect.bottom:
                    r = pygame.Rect(hist_rect.x + 20, my, hist_rect.width - 40, 50)
                    pygame.draw.rect(screen, (0, 0, 0, 80), r, border_radius=8)
                    
                    win = m.get('win', False)
                    col = (100, 255, 100) if win else (255, 100, 100)
                    res_txt = font_small.render("VICTORY" if win else "DEFEAT", True, col)
                    screen.blit(res_txt, (r.x + 15, r.y + 15))
                    
                    vs_txt = font_small.render(f"vs {m.get('opponent', 'Unknown')}", True, (255, 255, 255))
                    screen.blit(vs_txt, (r.x + 150, r.y + 15))
                    
                    pts = m.get('points_change', 0)
                    pts_txt = font_small.render(f"{'+' if pts>=0 else ''}{pts} PTS", True, col)
                    screen.blit(pts_txt, (r.right - pts_txt.get_width() - 15, r.y + 15))
                    
                    ts = m.get('timestamp', 0)
                    if ts:
                        ts_str = time.strftime("%b %d, %H:%M", time.localtime(ts))
                        ts_txt = font_small.render(ts_str, True, (150, 150, 150))
                        ts_x = r.right - pts_txt.get_width() - 30 - ts_txt.get_width()
                        screen.blit(ts_txt, (ts_x, r.y + 15))
                    
                my += 60
        screen.set_clip(None)

        btn_back.change_color(mouse_pos)
        btn_back.update(screen)

        update_animations(dt)
        update_juice(dt)
        draw_juice_overlays(screen)
        pygame.display.update()