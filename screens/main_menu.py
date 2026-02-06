import pygame
import sys
import os
from ui_components import Button, BG_FALLBACK, BUTTON_BASE, BUTTON_BORDER, TEXT_COLOR, get_font, FadeLayer

# Keep your absolute path if that's where your assets are
ASSET_PATH = r"assets\main_menu\menu_background_image.png"


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
    start_y = (screen.get_height() // 2) - (total_height // 2) + 50

    # Renamed "REPLAYS" to "ACHIEVEMENTS" here
    button_labels = ["PLAY", "CARD DECKS", "COLLECTION", "ACHIEVEMENTS", "SETTINGS", "QUIT"]
    menu_buttons = []

    for i, label in enumerate(button_labels):
        y_pos = start_y + (i * (btn_height + gap))
        # Button class now uses get_font automatically from ui_components
        menu_buttons.append(Button(label, center_x, y_pos, btn_width, btn_height, font_size=35))

    si_width, si_height = 250, 60
    signin_btn = Button("SIGN IN" if current_user == "Guest" else "SIGN OUT",
                        screen.get_width() - si_width - 30,
                        screen.get_height() - si_height - 30,
                        si_width, si_height, font_size=28)

    profile_rect = pygame.Rect(20, 20, 450, 150)

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

        # Draw Buttons
        for btn in menu_buttons:
            btn.change_color(mouse_pos)
            btn.update(screen)

        signin_btn.change_color(mouse_pos)
        signin_btn.update(screen)

        # Draw Profile Tag
        if current_user != "Guest":
            draw_profile_tag(screen, current_user, avatar_surf, profile_rect)

        # --- UPDATE & DRAW TRANSITION ---
        fade_layer.update()
        fade_layer.draw(screen)

        # IF FADE OUT IS DONE, RETURN THE ACTION
        if next_action is not None and fade_layer.finished:
            return next_action

        pygame.display.update()
        clock.tick(60)


def draw_profile_tag(screen, username, avatar, bg_rect):
    s = pygame.Surface((bg_rect.width, bg_rect.height))
    s.set_alpha(180)
    s.fill(BUTTON_BASE)
    screen.blit(s, (bg_rect.x, bg_rect.y))
    pygame.draw.rect(screen, BUTTON_BORDER, bg_rect, 3, border_radius=15)

    avatar_size = 130
    final_avatar = avatar

    # Draw Default Avatar if None
    if final_avatar is None:
        final_avatar = pygame.Surface((avatar_size, avatar_size))
        final_avatar.fill((100, 80, 120))

        font = get_font(80)
        text = font.render("?", True, (200, 200, 200))
        text_rect = text.get_rect(center=(avatar_size // 2, avatar_size // 2))
        final_avatar.blit(text, text_rect)

    # Blit Avatar
    screen.blit(final_avatar, (bg_rect.x + 10, bg_rect.y + 10))
    pygame.draw.rect(screen, BUTTON_BORDER, (bg_rect.x + 10, bg_rect.y + 10, avatar_size, avatar_size), 2)

    # Draw Username
    font = get_font(35)
    text = font.render(f"User: {username}", True, TEXT_COLOR)

    text_x = bg_rect.x + 10 + avatar_size + 20
    text_rect = text.get_rect(midleft=(text_x, bg_rect.centery))
    screen.blit(text, text_rect)