import pygame
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui_components import Button, BG_FALLBACK, BUTTON_BORDER, TEXT_COLOR, get_font, update_animations, spawn_particles, update_juice, draw_juice_overlays, PROFILE_BG, COLOR_ACTIVE, BUTTON_BASE, BUTTON_HOVER
from leaderboard_manager import LeaderboardManager
from user_manager import UserManager

def show_leaderboard_screen(screen, username, initial_league=None):
    clock = pygame.time.Clock()
    lb_mgr = LeaderboardManager()
    u_mgr = UserManager()
    
    # State
    seasons = lb_mgr.get_all_seasons()
    active_season = lb_mgr.data.get("current_season", "")
    
    leagues = lb_mgr.leagues
    active_league = initial_league if initial_league else (leagues[0]["id"] if leagues else None)
    
    btn_back = Button("BACK", 50, 40, 150, 60, font_size=28)
    
    # Season Buttons
    season_btns = []
    sy = 150
    for s in seasons:
        sb = Button(s, 50, sy, 200, 50, font_size=20)
        season_btns.append({"id": s, "btn": sb})
        sy += 60
        
    # League Buttons (Horizontal Tabs)
    league_btns = []
    lx = 300
    for lg in leagues:
        lb = Button(lg["name"], lx, 150, 180, 50, font_size=20)
        league_btns.append({"id": lg["id"], "btn": lb})
        lx += 190
        
    scroll_y = 0
    lb_rect = pygame.Rect(300, 220, screen.get_width() - 350, screen.get_height() - 250)
    
    # Pre-load pfps
    pfps = {}
    
    def get_pfp(path):
        if not path: return None
        if path in pfps: return pfps[path]
        if os.path.exists(path):
            try:
                raw = pygame.image.load(path).convert_alpha()
                pfps[path] = pygame.transform.smoothscale(raw, (50, 50))
                return pfps[path]
            except: pass
        return None

    while True:
        dt = clock.tick(60) / 1000.0
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()
        
        # Get data
        board_data = lb_mgr.get_leaderboard(season_id=active_season, league_id=active_league)
        
        for event in events:
            if event.type == pygame.QUIT:
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                spawn_particles(event.pos[0], event.pos[1], count=5, color=(200, 100, 200))
                
                if btn_back.check_input(mouse_pos):
                    return "BACK"
                    
                for sb in season_btns:
                    if sb["btn"].check_input(mouse_pos):
                        active_season = sb["id"]
                        
                for lb in league_btns:
                    if lb["btn"].check_input(mouse_pos):
                        active_league = lb["id"]
                        scroll_y = 0
                        
                # Check Row Clicks
                if lb_rect.collidepoint(mouse_pos):
                    hy = lb_rect.y + 15
                    click_y = mouse_pos[1] - (hy + 40 - scroll_y)
                    idx = int(click_y // 75)
                    if 0 <= idx < len(board_data):
                        r_y = (hy + 40 - scroll_y) + idx * 75
                        if r_y <= mouse_pos[1] <= r_y + 65:
                            return ("OPEN_PROFILE", board_data[idx]["id"], board_data[idx]["is_bot"])
                        
            if event.type == pygame.MOUSEWHEEL:
                if lb_rect.collidepoint(mouse_pos):
                    content_h = len(board_data) * 80
                    max_scr = max(0, content_h - lb_rect.height)
                    scroll_y -= event.y * 30
                    scroll_y = max(0, min(scroll_y, max_scr))

        # DRAW
        screen.fill(BG_FALLBACK)
        
        # Header
        screen.blit(get_font(40).render("LEADERBOARD", True, TEXT_COLOR), (250, 50))
        
        # Season Sidebar
        screen.blit(get_font(25).render("SEASONS", True, (200, 150, 200)), (50, 120))
        for sb in season_btns:
            # Highlight active season
            if sb["id"] == active_season:
                pygame.draw.rect(screen, COLOR_ACTIVE, (sb["btn"].rect.x - 10, sb["btn"].rect.y, 5, sb["btn"].rect.height), border_radius=5)
            sb["btn"].change_color(mouse_pos)
            sb["btn"].update(screen)
            
        # League Tabs
        for lb in league_btns:
            if lb["id"] == active_league:
                pygame.draw.rect(screen, COLOR_ACTIVE, (lb["btn"].rect.x, lb["btn"].rect.bottom, lb["btn"].rect.width, 3))
            lb["btn"].change_color(mouse_pos)
            lb["btn"].update(screen)
            
        # Leaderboard Area
        pygame.draw.rect(screen, PROFILE_BG, lb_rect, border_radius=15)
        pygame.draw.rect(screen, BUTTON_BORDER, lb_rect, 1, border_radius=15)
        
        # Table Headers
        hx = lb_rect.x + 20
        hy = lb_rect.y + 15
        screen.blit(get_font(20).render("RANK", True, (200, 150, 200)), (hx, hy))
        screen.blit(get_font(20).render("PLAYER", True, (200, 150, 200)), (hx + 120, hy))
        screen.blit(get_font(20).render("POINTS", True, (200, 150, 200)), (hx + 400, hy))
        screen.blit(get_font(20).render("DAMAGE DEALT", True, (200, 150, 200)), (hx + 550, hy))
        
        pygame.draw.line(screen, BUTTON_BORDER, (lb_rect.x, hy + 30), (lb_rect.right, hy + 30), 1)
        
        screen.set_clip(pygame.Rect(lb_rect.x, hy + 31, lb_rect.width, lb_rect.height - 31))
        draw_y = hy + 40 - scroll_y
        
        for p in board_data:
            if draw_y + 70 < lb_rect.y or draw_y > lb_rect.bottom:
                draw_y += 75
                continue
                
            r = pygame.Rect(lb_rect.x + 10, draw_y, lb_rect.width - 20, 65)
            
            # Highlight the real user
            is_me = (p["name"] == username and not p["is_bot"])
            is_hovered = r.collidepoint(mouse_pos)
            
            # Draw row BG
            row_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            if is_me:
                col = (100, 70, 100, 180) if is_hovered else (80, 50, 80, 150)
                pygame.draw.rect(row_surf, col, row_surf.get_rect(), border_radius=10)
                pygame.draw.rect(row_surf, COLOR_ACTIVE, row_surf.get_rect(), 1, border_radius=10)
            else:
                if is_hovered:
                    pygame.draw.rect(row_surf, (255, 255, 255, 20), row_surf.get_rect(), border_radius=10)
                elif p["rank"] % 2 == 0:
                    pygame.draw.rect(row_surf, (0, 0, 0, 50), row_surf.get_rect(), border_radius=10)
                    
            screen.blit(row_surf, r.topleft)
            
            # Rank
            rank_col = (255, 215, 0) if p["rank"] == 1 else ((192, 192, 192) if p["rank"] == 2 else ((205, 127, 50) if p["rank"] == 3 else TEXT_COLOR))
            screen.blit(get_font(28).render(f"#{p['rank']}", True, rank_col), (r.x + 10, r.y + 15))
            
            # PFP
            pfp_surf = get_pfp(p.get("pfp_path"))
            
            # If not a bot and no pfp, try to get from UserManager
            if not pfp_surf and not p["is_bot"]:
                raw_pfp = u_mgr.get_avatar_image(p["name"])
                if raw_pfp:
                    pfp_surf = pygame.transform.smoothscale(raw_pfp, (50, 50))
            
            if pfp_surf:
                screen.blit(pfp_surf, (r.x + 90, r.y + 7))
                pygame.draw.rect(screen, BUTTON_BORDER, (r.x + 90, r.y + 7, 50, 50), 1)
            else:
                pygame.draw.rect(screen, (50, 40, 50), (r.x + 90, r.y + 7, 50, 50))
                
            # Name
            n_col = COLOR_ACTIVE if is_me else TEXT_COLOR
            screen.blit(get_font(25).render(p["name"], True, n_col), (r.x + 150, r.y + 18))
            
            # Bot badge
            if p["is_bot"]:
                screen.blit(get_font(14).render("BOT", True, (150, 150, 150)), (r.x + 150, r.y + 45))
                
            # Points
            screen.blit(get_font(25).render(str(p["points"]), True, (100, 255, 100)), (r.x + 390, r.y + 18))
            
            # Damage (Tie-breaker)
            screen.blit(get_font(20).render(str(p["total_damage"]), True, (255, 150, 150)), (r.x + 550, r.y + 22))
            
            draw_y += 75
            
        screen.set_clip(None)

        btn_back.change_color(mouse_pos)
        btn_back.update(screen)
        
        update_animations(dt)
        update_juice(dt)
        draw_juice_overlays(screen)
        pygame.display.update()
