import pygame
import tkinter as tk
from tkinter import filedialog
from ui_components import Button, InputBox, TEXT_COLOR, BG_FALLBACK, PROFILE_BG, BUTTON_BORDER, get_font
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


def show_profile_screen(screen, username):
    clock = pygame.time.Clock()
    user_mgr = UserManager()

    original_username = username
    raw_avatar = user_mgr.get_avatar_image(username)
    stats = user_mgr.get_user_stats(username)

    editing_mode = False
    viewing_fullscreen = False

    temp_avatar_surf = None
    # Input box now uses theme colors automatically from ui_components
    input_name = InputBox(0, 0, 300, 50, text=username)

    def get_display_avatar(raw, temp):
        source = temp if temp else raw
        if source:
            return pygame.transform.scale(source, (350, 350))
        s = pygame.Surface((350, 350))
        s.fill((60, 20, 80))  # Dark Purple placeholder
        return s

    def get_fullscreen_avatar(raw, temp):
        source = temp if temp else raw
        if source:
            return pygame.transform.scale(source, (900, 900))
        return None

    card_w, card_h = 800, 600
    card_rect = pygame.Rect((screen.get_width() - card_w) // 2, (screen.get_height() - card_h) // 2, card_w, card_h)

    avatar_rect = pygame.Rect(card_rect.x + 50, card_rect.y + 125, 350, 350)

    input_name.rect.x = card_rect.x + 50
    input_name.rect.y = card_rect.y + 40
    input_name.rect.w = 350

    btn_back = Button("BACK", 50, 50, 150, 50, font_size=30)
    btn_edit = Button("EDIT PROFILE", card_rect.right - 250, card_rect.y + 30, 200, 50, font_size=25)

    btn_save = Button("SAVE", card_rect.centerx - 210, card_rect.bottom - 80, 200, 50, font_size=30)
    btn_cancel = Button("CANCEL", card_rect.centerx + 10, card_rect.bottom - 80, 200, 50, font_size=30)

    font_name = get_font(70)
    font_stats = get_font(40)
    font_small = get_font(30)

    status_msg = ""

    while True:
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()

        for event in events:
            if event.type == pygame.QUIT:
                return None

            if editing_mode:
                input_name.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
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
                        if btn_edit.check_input(mouse_pos):
                            editing_mode = True
                            status_msg = ""

                        if avatar_rect.collidepoint(mouse_pos):
                            viewing_fullscreen = True

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
            overlay.fill((10, 5, 20))
            screen.blit(overlay, (0, 0))

            # Card BG
            pygame.draw.rect(screen, PROFILE_BG, card_rect, border_radius=20)
            pygame.draw.rect(screen, BUTTON_BORDER, card_rect, 4, border_radius=20)

            disp_avatar = get_display_avatar(raw_avatar, temp_avatar_surf)
            screen.blit(disp_avatar, avatar_rect)

            # Green border if editing, otherwise Pink
            border_col = (100, 255, 100) if editing_mode else BUTTON_BORDER
            pygame.draw.rect(screen, border_col, avatar_rect, 3)

            if editing_mode:
                input_name.update()
                input_name.draw(screen)

                # --- FIXED: Better visual cue for uploading ---
                # Draw a semi transparent band at bottom of avatar
                upload_band = pygame.Surface((350, 50))
                upload_band.set_alpha(200)
                upload_band.fill((0, 0, 0))
                screen.blit(upload_band, (avatar_rect.x, avatar_rect.bottom - 50))

                hint = font_small.render("CLICK TO UPLOAD", True, (255, 255, 255))
                screen.blit(hint, (avatar_rect.centerx - hint.get_width() // 2, avatar_rect.bottom - 38))
            else:
                name_surf = font_name.render(original_username, True, TEXT_COLOR)
                screen.blit(name_surf, (card_rect.x + 50, card_rect.y + 40))

            text_x = avatar_rect.right + 40
            start_text_y = avatar_rect.y + 20
            stats_list = [
                f"Rank: {stats.get('rank', 'N/A')}",
                f"Wins: {stats.get('wins', 0)}",
                f"Losses: {stats.get('losses', 0)}",
                f"Games: {stats.get('games_played', 0)}"
            ]
            for i, line in enumerate(stats_list):
                txt = font_stats.render(line, True, TEXT_COLOR)
                screen.blit(txt, (text_x, start_text_y + (i * 60)))

            if status_msg:
                msg = font_small.render(status_msg, True, (255, 100, 100))
                screen.blit(msg, (card_rect.x + 50, card_rect.bottom - 130))

            if editing_mode:
                btn_save.change_color(mouse_pos)
                btn_save.update(screen)
                btn_cancel.change_color(mouse_pos)
                btn_cancel.update(screen)
            else:
                btn_edit.change_color(mouse_pos)
                btn_edit.update(screen)

            btn_back.change_color(mouse_pos)
            btn_back.update(screen)

        pygame.display.update()
        clock.tick(60)