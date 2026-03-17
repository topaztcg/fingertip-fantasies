import pygame
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui_components import Button, BG_FALLBACK, BUTTON_BASE, BUTTON_BORDER, TEXT_COLOR, get_font, FadeLayer, TEXT_SHADOW, PROFILE_BG, COLOR_ACTIVE, COLOR_PASSIVE, update_animations, spawn_particles, update_juice, draw_juice_overlays

# Keep your absolute path if that's where your assets are
# --- ASSETS ---
ASSET_PATH = "assets/main_menu/menu_background_image.png"


def show_main_menu(screen, current_user, avatar_surf=None):
    clock = pygame.time.Clock()

    # --- SETUP TRANSITION ---
    fade_layer = FadeLayer(screen.get_width(), screen.get_height(), speed=12)
    next_action = None # Used to delay return until fade out finishes

    background_surf = None
    if os.path.exists(ASSET_PATH):
        try:
            raw_image = pygame.image.load(ASSET_PATH).convert()
            background_surf = pygame.transform.scale(raw_image, (screen.get_width(), screen.get_height()))
        except Exception as e:
            print(f"Error loading background: {e}")

    btn_width, btn_height, gap = 350, 75, 25
    center_x = screen.get_width() // 2 - (btn_width // 2)

    # Calculate total height to center the block of buttons
    # 6 buttons * height + 5 gaps
    total_height = (6 * btn_height) + (5 * gap)
    
    # Center vertically but offset slightly down to accommodate Title
    start_y = (screen.get_height() // 2) - (total_height // 2) + 60

    # Renamed "REPLAYS" to "ACHIEVEMENTS" here
    button_labels = ["PLAY", "CARD DECKS", "COLLECTION", "ACHIEVEMENTS", "SETTINGS", "QUIT"]
    menu_buttons = []

    for i, label in enumerate(button_labels):
        y_pos = start_y + (i * (btn_height + gap))
        menu_buttons.append(Button(label, center_x, y_pos, btn_width, btn_height, font_size=35))

    si_width, si_height = 250, 60
    signin_btn = Button("SIGN IN" if current_user == "Guest" else "SIGN OUT",
                        screen.get_width() - si_width - 30,
                        screen.get_height() - si_height - 30,
                        si_width, si_height, font_size=28)

    # Dynamic Profile Tag Sizing
    # Calculate required width based on text
    p_font = get_font(30) # Slightly smaller font for cleaner look
    p_text = f"User: {current_user}"
    p_text_w, p_text_h = p_font.size(p_text)
    
    # Avatar Size + Paddings
    # Height = 110. Avatar = 90 (110-20). Padding Left=10. Gap=20. Padding Right=30.
    p_height = 110
    avatar_s = p_height - 20
    p_width = 10 + avatar_s + 20 + p_text_w + 30
    
    # Move to Bottom Left (Height - RectHeight - Padding)
    profile_rect = pygame.Rect(20, screen.get_height() - p_height - 20, p_width, p_height)

    # Pre-render Title
    t_size = 100
    title_font = get_font(t_size)
    title_text = "FINGERTIP FANTASIES"
    
    # Colors (Updated to "Soft Girl" Palette)
    c_main = TEXT_COLOR      # Soft Pink-White
    c_outline = COLOR_ACTIVE # Hot Pink Pop
    c_shadow = TEXT_SHADOW   # Deep Plum
    
    # Render Surfaces
    t_surf_main = title_font.render(title_text, True, c_main)
    t_surf_outline = title_font.render(title_text, True, c_outline)
    t_surf_shadow = title_font.render(title_text, True, c_shadow)
    
    # Position
    title_center_x, title_center_y = screen.get_width() // 2, 80
    title_rect = t_surf_main.get_rect(center=(title_center_x, title_center_y))

    while True:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # DISABLE CLICKS IF FADING OUT
            if event.type == pygame.MOUSEBUTTONDOWN and next_action is None:
                # FIXED: STRICT CLICK CHECK (Only Left Click)
                if event.button == 1:
                    spawn_particles(event.pos[0], event.pos[1], count=5, color=(200, 100, 200))

                    # Check main menu buttons
                    for btn in menu_buttons:
                        if btn.check_input(mouse_pos):
                            next_action = btn.text_input
                            fade_layer.fade_out()

                    # Check Sign In/Out
                    if signin_btn.check_input(mouse_pos):
                        next_action = "LOGIN_ACTION"
                        fade_layer.fade_out()

                    # Check Profile Click
                    if current_user != "Guest" and profile_rect.collidepoint(mouse_pos):
                        next_action = "OPEN_PROFILE"
                        fade_layer.fade_out()

        # Draw Background
        if background_surf:
            screen.blit(background_surf, (0, 0))
        else:
            screen.fill(BG_FALLBACK)

        # Draw Title - Shadow
        screen.blit(t_surf_shadow, (title_rect.x + 4, title_rect.y + 4))
        
        # Draw Title - Outline (8-way offset for thickness)
        for ox in range(-2, 3):
            for oy in range(-2, 3):
                if ox == 0 and oy == 0: continue
                screen.blit(t_surf_outline, (title_rect.x + ox, title_rect.y + oy))
        
        # Draw Title - Main
        screen.blit(t_surf_main, title_rect)

        # Draw Buttons
        for btn in menu_buttons:
            btn.change_color(mouse_pos)
            btn.update(screen)

        signin_btn.change_color(mouse_pos)
        signin_btn.update(screen)

        # Draw Profile Tag
        if current_user != "Guest":
            draw_profile_tag(screen, current_user, avatar_surf, profile_rect, p_text, p_font)

        # --- UPDATE & DRAW TRANSITION & JUICE ---
        fade_layer.update()
        fade_layer.draw(screen)

        if next_action and fade_layer.finished:
            return next_action

        dt = clock.tick(60) / 1000.0
        update_animations(dt)
        update_juice(dt)
        draw_juice_overlays(screen)
        pygame.display.update()


def draw_profile_tag(screen, username, avatar, bg_rect, text_str, font_obj):
    # Draw Panel Background
    s = pygame.Surface((bg_rect.width, bg_rect.height))
    s.set_alpha(200) # Slightly more opaque
    s.fill(PROFILE_BG) # Use Constant
    screen.blit(s, (bg_rect.x, bg_rect.y))
    
    # Border
    pygame.draw.rect(screen, BUTTON_BORDER, bg_rect, 2, border_radius=15)

    # Dynamic Avatar Size
    avatar_size = bg_rect.height - 20
    final_avatar = avatar

    # Draw Default Avatar if None
    if final_avatar is None:
        final_avatar = pygame.Surface((avatar_size, avatar_size))
        final_avatar.fill(COLOR_PASSIVE) # Soft Lilac default

        font = get_font(int(avatar_size * 0.6))
        text = font.render("?", True, (200, 200, 200))
        text_rect = text.get_rect(center=(avatar_size // 2, avatar_size // 2))
        final_avatar.blit(text, text_rect)
    else:
        # Scale if existing avatar doesn't match
        if final_avatar.get_height() != avatar_size:
            final_avatar = pygame.transform.smoothscale(final_avatar, (avatar_size, avatar_size))

    # Blit Avatar
    av_x = bg_rect.x + 10
    av_y = bg_rect.y + 10
    screen.blit(final_avatar, (av_x, av_y))
    pygame.draw.rect(screen, (255, 255, 255), (av_x, av_y, avatar_size, avatar_size), 2)

    # Draw Username
    text_surf = font_obj.render(text_str, True, TEXT_COLOR)
    
    # Center text vertically in the remaining space
    text_x = av_x + avatar_size + 20
    text_rect = text_surf.get_rect(midleft=(text_x, bg_rect.centery))
    screen.blit(text_surf, text_rect)
