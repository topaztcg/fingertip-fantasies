import pygame
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui_components import Button, BG_FALLBACK, BUTTON_BORDER, TEXT_COLOR, get_font, update_animations, spawn_particles, update_juice, draw_juice_overlays, PROFILE_BG, COLOR_ACTIVE, BUTTON_BASE, BUTTON_HOVER

def show_leaderboard_screen(screen, username, initial_league=None):
    clock = pygame.time.Clock()
    
    from leaderboard_manager import LeaderboardManager
    from user_manager import UserManager
    lb_mgr = LeaderboardManager()
    u_mgr = UserManager()
    
    seasons = lb_mgr.get_all_seasons()
    active_season = lb_mgr.data.get("current_season", "")
    
    leagues = lb_mgr.leagues
    active_league = initial_league if initial_league else (leagues[0]["id"] if leagues else None)
    
    screen_w, screen_h = screen.get_size()
    
    btn_back = Button("BACK", 40, 40, 120, 50, font_size=20)
    
    # Layout Params
    sidebar_w = 250
    sidebar_x = 40
    sidebar_y = 150
    sidebar_h = screen_h - 190
    
    main_x = sidebar_x + sidebar_w + 30
    main_y = 150
    main_w = screen_w - main_x - 40
    main_h = screen_h - 190
    
    # Pre-load pfps
    pfps = {}
    def get_pfp(path, is_bot, name):
        if not path and not is_bot:
            # Fallback to UserManager
            raw_pfp = u_mgr.get_avatar_image(name)
            if raw_pfp:
                return pygame.transform.smoothscale(raw_pfp, (45, 45))
            return None
            
        if not path: return None
        if path in pfps: return pfps[path]
        if os.path.exists(path):
            try:
                raw = pygame.image.load(path).convert_alpha()
                pfps[path] = pygame.transform.smoothscale(raw, (45, 45))
                return pfps[path]
            except: pass
        return None

    scroll_y = 0
    target_scroll_y = 0
    dragging_scrollbar = False
    drag_offset_y = 0
    
    row_h = 75
    header_h = 50
    
    def get_rank_color(rank):
        if rank == 1: return (255, 215, 0)
        if rank == 2: return (192, 192, 192)
        if rank == 3: return (205, 127, 50)
        return TEXT_COLOR

    while True:
        dt = clock.tick(60) / 1000.0
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()
        
        board_data = lb_mgr.get_leaderboard(season_id=active_season, league_id=active_league)
        content_h = len(board_data) * row_h
        max_scroll = max(0, content_h - (main_h - header_h - 20))
        
        # Smooth scroll
        scroll_y += (target_scroll_y - scroll_y) * 15 * dt
        if abs(target_scroll_y - scroll_y) < 0.5: scroll_y = target_scroll_y
        
        # Calculate dynamic positions for League Tabs
        tab_w = 160
        tab_h = 45
        tab_start_x = main_x
        tab_y = main_y - 60
        
        # Determine hovered elements
        hovered_season = None
        hovered_league = None
        
        for i, s in enumerate(seasons):
            r = pygame.Rect(sidebar_x + 20, sidebar_y + 60 + i * 55, sidebar_w - 40, 45)
            if r.collidepoint(mouse_pos): hovered_season = s
            
        for i, lg in enumerate(leagues):
            r = pygame.Rect(tab_start_x + i * (tab_w + 10), tab_y, tab_w, tab_h)
            if r.collidepoint(mouse_pos): hovered_league = lg["id"]
            
        list_rect = pygame.Rect(main_x, main_y + header_h, main_w, main_h - header_h)

        for event in events:
            if event.type == pygame.QUIT:
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    spawn_particles(event.pos[0], event.pos[1], count=5, color=(200, 100, 200))
                    
                    if btn_back.check_input(mouse_pos):
                        return "BACK"
                        
                    if hovered_season:
                        active_season = hovered_season
                        target_scroll_y = 0
                        
                    if hovered_league:
                        active_league = hovered_league
                        target_scroll_y = 0
                        
                    # Row click
                    if list_rect.collidepoint(mouse_pos):
                        sb_x = main_x + main_w - 20
                        sb_y = main_y + header_h + 10
                        sb_h = main_h - header_h - 20
                        
                        thumb_h = max(30, (sb_h / content_h) * sb_h) if content_h > 0 else sb_h
                        thumb_y = sb_y + (scroll_y / max_scroll) * (sb_h - thumb_h) if max_scroll > 0 else sb_y
                        thumb_rect = pygame.Rect(sb_x - 5, thumb_y, 16, thumb_h)
                        track_rect = pygame.Rect(sb_x - 5, sb_y, 16, sb_h)
                        
                        if max_scroll > 0 and thumb_rect.collidepoint(mouse_pos):
                            dragging_scrollbar = True
                            drag_offset_y = mouse_pos[1] - thumb_rect.y
                        elif max_scroll > 0 and track_rect.collidepoint(mouse_pos):
                            pass # Clicking on scrollbar track
                        else:
                            click_y = mouse_pos[1] - list_rect.y + scroll_y
                            idx = int(click_y // row_h)
                            if 0 <= idx < len(board_data):
                                return ("OPEN_PROFILE", board_data[idx]["id"], board_data[idx]["is_bot"])
                                
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_scrollbar = False
                
            if event.type == pygame.MOUSEMOTION:
                if dragging_scrollbar and max_scroll > 0:
                    sb_y = main_y + header_h + 10
                    sb_h = main_h - header_h - 20
                    thumb_h = max(30, (sb_h / content_h) * sb_h) if content_h > 0 else sb_h
                    
                    new_thumb_y = mouse_pos[1] - drag_offset_y
                    fraction = (new_thumb_y - sb_y) / (sb_h - thumb_h) if sb_h > thumb_h else 0
                    target_scroll_y = max(0, min(fraction * max_scroll, max_scroll))
                    scroll_y = target_scroll_y
                            
            if event.type == pygame.MOUSEWHEEL:
                if list_rect.collidepoint(mouse_pos) or True: # Global scroll is fine if no other scrollable area
                    target_scroll_y -= event.y * 50
                    target_scroll_y = max(0, min(target_scroll_y, max_scroll))
                    
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    target_scroll_y -= 100
                    target_scroll_y = max(0, min(target_scroll_y, max_scroll))
                elif event.key == pygame.K_DOWN:
                    target_scroll_y += 100
                    target_scroll_y = max(0, min(target_scroll_y, max_scroll))
                elif event.key == pygame.K_PAGEUP:
                    target_scroll_y -= main_h
                    target_scroll_y = max(0, min(target_scroll_y, max_scroll))
                elif event.key == pygame.K_PAGEDOWN:
                    target_scroll_y += main_h
                    target_scroll_y = max(0, min(target_scroll_y, max_scroll))

        # --- DRAW ---
        screen.fill((10, 10, 15)) # Deep dark bg
        
        # Ambient Glow
        glow = pygame.Surface((400, 400), pygame.SRCALPHA)
        pygame.draw.circle(glow, (COLOR_ACTIVE[0], COLOR_ACTIVE[1], COLOR_ACTIVE[2], 15), (200, 200), 200)
        screen.blit(glow, (main_x - 100, main_y - 100))
        
        # Title
        screen.blit(get_font(40).render("LEADERBOARD", True, TEXT_COLOR), (main_x, 30))
        
        # --- SIDEBAR (SEASONS) ---
        pygame.draw.rect(screen, PROFILE_BG, (sidebar_x, sidebar_y, sidebar_w, sidebar_h), border_radius=15)
        pygame.draw.rect(screen, BUTTON_BORDER, (sidebar_x, sidebar_y, sidebar_w, sidebar_h), 1, border_radius=15)
        
        s_title = get_font(22).render("SEASONS", True, (200, 150, 200))
        screen.blit(s_title, (sidebar_x + sidebar_w//2 - s_title.get_width()//2, sidebar_y + 20))
        pygame.draw.line(screen, BUTTON_BORDER, (sidebar_x + 20, sidebar_y + 50), (sidebar_x + sidebar_w - 20, sidebar_y + 50), 1)
        
        for i, s in enumerate(seasons):
            r = pygame.Rect(sidebar_x + 20, sidebar_y + 60 + i * 55, sidebar_w - 40, 45)
            is_act = (s == active_season)
            
            if is_act:
                pygame.draw.rect(screen, COLOR_ACTIVE, r, border_radius=8)
            elif s == hovered_season:
                pygame.draw.rect(screen, (80, 50, 80), r, border_radius=8)
                
            txt_col = (255, 255, 255) if is_act else (200, 200, 200)
            txt = get_font(20).render(s, True, txt_col)
            screen.blit(txt, (r.x + r.width//2 - txt.get_width()//2, r.y + r.height//2 - txt.get_height()//2))

        # --- MAIN TABS (LEAGUES) ---
        for i, lg in enumerate(leagues):
            r = pygame.Rect(tab_start_x + i * (tab_w + 10), tab_y, tab_w, tab_h)
            is_act = (lg["id"] == active_league)
            
            if is_act:
                pygame.draw.rect(screen, COLOR_ACTIVE, r, border_radius=8)
                txt_col = (255, 255, 255)
            else:
                if lg["id"] == hovered_league:
                    pygame.draw.rect(screen, (80, 50, 80, 150), r, border_radius=8)
                pygame.draw.rect(screen, BUTTON_BORDER, r, 1, border_radius=8)
                txt_col = (150, 150, 150)
                
            txt = get_font(18).render(lg["name"].upper(), True, txt_col)
            screen.blit(txt, (r.x + r.width//2 - txt.get_width()//2, r.y + r.height//2 - txt.get_height()//2))

        # --- LEADERBOARD PANEL ---
        pygame.draw.rect(screen, PROFILE_BG, (main_x, main_y, main_w, main_h), border_radius=15)
        pygame.draw.rect(screen, BUTTON_BORDER, (main_x, main_y, main_w, main_h), 1, border_radius=15)
        
        # Headers
        hx = main_x + 30
        hy = main_y + 15
        screen.blit(get_font(18).render("RANK", True, (150, 150, 150)), (hx, hy))
        screen.blit(get_font(18).render("PLAYER", True, (150, 150, 150)), (hx + 120, hy))
        screen.blit(get_font(18).render("POINTS", True, (150, 150, 150)), (hx + 500, hy))
        screen.blit(get_font(18).render("DAMAGE", True, (150, 150, 150)), (hx + 650, hy))
        
        pygame.draw.line(screen, BUTTON_BORDER, (main_x, main_y + header_h), (main_x + main_w, main_y + header_h), 1)

        # Rows Clipping
        screen.set_clip(list_rect)
        
        draw_y = main_y + header_h + 10 - scroll_y
        
        for p in board_data:
            if draw_y + row_h < list_rect.y or draw_y > list_rect.bottom:
                draw_y += row_h
                continue
                
            r = pygame.Rect(main_x + 15, draw_y, main_w - 30, row_h - 10)
            
            is_me = (p["name"] == username and not p["is_bot"])
            is_hovered = r.collidepoint(mouse_pos)
            
            # Row BG
            bg_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            if is_me:
                col = (100, 70, 100, 180) if is_hovered else (80, 50, 80, 150)
                pygame.draw.rect(bg_surf, col, bg_surf.get_rect(), border_radius=8)
                pygame.draw.rect(bg_surf, COLOR_ACTIVE, bg_surf.get_rect(), 1, border_radius=8)
            else:
                if is_hovered:
                    pygame.draw.rect(bg_surf, (255, 255, 255, 20), bg_surf.get_rect(), border_radius=8)
                elif p["rank"] % 2 == 0:
                    pygame.draw.rect(bg_surf, (0, 0, 0, 40), bg_surf.get_rect(), border_radius=8)
                    
            screen.blit(bg_surf, r.topleft)
            
            # Rank
            rk_col = get_rank_color(p["rank"])
            rk_txt = get_font(26).render(f"#{p['rank']}", True, rk_col)
            screen.blit(rk_txt, (r.x + 15, r.y + r.height//2 - rk_txt.get_height()//2))
            
            # PFP
            pfp_surf = get_pfp(p.get("pfp_path"), p["is_bot"], p["name"])
            pfp_x, pfp_y = r.x + 90, r.y + r.height//2 - 22
            if pfp_surf:
                screen.blit(pfp_surf, (pfp_x, pfp_y))
                pygame.draw.rect(screen, BUTTON_BORDER, (pfp_x, pfp_y, 45, 45), 1, border_radius=5)
            else:
                pygame.draw.rect(screen, (50, 40, 50), (pfp_x, pfp_y, 45, 45), border_radius=5)
                
            # Name
            n_col = COLOR_ACTIVE if is_me else TEXT_COLOR
            n_txt = get_font(24).render(p["name"], True, n_col)
            screen.blit(n_txt, (r.x + 150, r.y + r.height//2 - n_txt.get_height()//2 - (8 if p["is_bot"] else 0)))
            
            if p["is_bot"]:
                bot_txt = get_font(12).render("BOT", True, (150, 150, 150))
                screen.blit(bot_txt, (r.x + 150, r.y + r.height//2 + 8))
                
            # Points
            pts_txt = get_font(24).render(f"{p['points']:,}", True, (100, 255, 100))
            screen.blit(pts_txt, (r.x + 485, r.y + r.height//2 - pts_txt.get_height()//2))
            
            # Damage
            dmg_txt = get_font(20).render(f"{p['total_damage']:,}", True, (255, 150, 150))
            screen.blit(dmg_txt, (r.x + 635, r.y + r.height//2 - dmg_txt.get_height()//2))
            
            draw_y += row_h
            
        screen.set_clip(None)
        
        # Scrollbar
        if max_scroll > 0:
            sb_x = main_x + main_w - 15
            sb_y = main_y + header_h + 10
            sb_h = main_h - header_h - 20
            
            # Track
            pygame.draw.rect(screen, (30, 30, 40), (sb_x, sb_y, 6, sb_h), border_radius=3)
            
            # Thumb
            thumb_h = max(30, (sb_h / content_h) * sb_h)
            thumb_y = sb_y + (scroll_y / max_scroll) * (sb_h - thumb_h)
            pygame.draw.rect(screen, (150, 100, 150), (sb_x, thumb_y, 6, thumb_h), border_radius=3)

        btn_back.change_color(mouse_pos)
        btn_back.update(screen)
        
        update_animations(dt)
        update_juice(dt)
        draw_juice_overlays(screen)
        pygame.display.update()
