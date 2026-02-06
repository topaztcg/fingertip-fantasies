import pygame
import sys
import tkinter as tk
from tkinter import filedialog
from ui_components import Button, InputBox, BG_FALLBACK, TEXT_COLOR, get_font
from user_manager import UserManager


def get_image_from_pc():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Avatar Image",
        filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")]
    )
    root.destroy()
    return file_path


def show_login_screen(screen):
    clock = pygame.time.Clock()
    user_mgr = UserManager()

    mode = "LOGIN"
    status_msg = ""

    # --- LAYOUT CONFIG ---
    center_x = screen.get_width() // 2

    # MOVED UP: Give some more space for the form
    start_y = 180
    row_gap = 100

    label_x = center_x - 400  # Labels further left
    input_x = center_x - 50  # Inputs near center

    user_box = InputBox(input_x, start_y, 300, 50)
    pass_box = InputBox(input_x, start_y + row_gap, 300, 50, is_password=True)

    # --- BUTTONS ---
    # These Y positions are now much lower to avoid overlap
    btn_submit = Button("LOGIN", center_x - 150, 680, 300, 60, font_size=30)
    btn_switch = Button("CREATE NEW USER", center_x - 200, 760, 400, 60, font_size=28)

    btn_back = Button("BACK", 50, 50, 150, 50, font_size=30)

    # Avatar Upload (Register Mode) - Placed below Password
    # Y approx 380 + 90 = 470
    btn_avatar = Button("UPLOAD AVATAR", center_x - 150, start_y + (row_gap * 2), 300, 50, font_size=30)

    font_title = get_font(80)
    font_label = get_font(40)
    font_msg = get_font(30)

    uploaded_avatar_surf = None

    while True:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            user_box.handle_event(event)
            pass_box.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                if btn_back.check_input(mouse_pos):
                    return ("BACK", None)

                if btn_switch.check_input(mouse_pos):
                    status_msg = ""
                    uploaded_avatar_surf = None
                    if mode == "LOGIN":
                        mode = "REGISTER"
                        btn_submit.set_text("CREATE ACCOUNT")
                        btn_switch.set_text("BACK TO LOGIN")
                    else:
                        mode = "LOGIN"
                        btn_submit.set_text("LOGIN")
                        btn_switch.set_text("CREATE NEW USER")

                if mode == "REGISTER" and btn_avatar.check_input(mouse_pos):
                    path = get_image_from_pc()
                    if path:
                        try:
                            raw_img = pygame.image.load(path).convert_alpha()
                            uploaded_avatar_surf = pygame.transform.scale(raw_img, (800, 800))
                            status_msg = "Avatar Loaded!"
                        except Exception as e:
                            status_msg = "Error loading image"
                            print(e)

                if btn_submit.check_input(mouse_pos):
                    u_val = user_box.get_text().strip()
                    p_val = pass_box.get_text().strip()

                    if not u_val or not p_val:
                        status_msg = "Fields cannot be empty!"
                    else:
                        if mode == "LOGIN":
                            if user_mgr.validate_login(u_val, p_val):
                                return ("LOGIN_SUCCESS", u_val)
                            else:
                                status_msg = "Invalid Credentials"
                        else:
                            final_avatar = uploaded_avatar_surf
                            if final_avatar is None:
                                final_avatar = pygame.Surface((800, 800))
                                final_avatar.fill((180, 150, 180))  # Soft purple placeholder

                            success, msg = user_mgr.create_user(u_val, p_val, final_avatar)
                            status_msg = msg
                            if success:
                                mode = "LOGIN"
                                btn_submit.set_text("LOGIN")
                                btn_switch.set_text("CREATE NEW USER")

        screen.fill(BG_FALLBACK)

        # Title
        title_text = "LOGIN" if mode == "LOGIN" else "REGISTER"
        title_surf = font_title.render(title_text, True, TEXT_COLOR)
        screen.blit(title_surf, (center_x - title_surf.get_width() // 2, 80))

        # Labels
        u_y_center = start_y + 25 - (font_label.get_height() // 2)
        screen.blit(font_label.render("Username:", True, TEXT_COLOR), (label_x, u_y_center))

        p_y_center = (start_y + row_gap) + 25 - (font_label.get_height() // 2)
        screen.blit(font_label.render("Password:", True, TEXT_COLOR), (label_x, p_y_center))

        user_box.update()
        pass_box.update()
        user_box.draw(screen)
        pass_box.draw(screen)

        if mode == "REGISTER":
            # Draw Upload Button
            btn_avatar.change_color(pygame.mouse.get_pos())
            btn_avatar.update(screen)

            # Preview Box (Centered below upload button)
            # Button is at start_y + 200 (approx 380)
            # Box starts at 450
            preview_box = pygame.Rect(center_x - 75, start_y + (row_gap * 2) + 70, 150, 150)
            pygame.draw.rect(screen, (60, 40, 70), preview_box)  # Darker soft purple

            if uploaded_avatar_surf:
                preview_img = pygame.transform.scale(uploaded_avatar_surf, (150, 150))
                screen.blit(preview_img, preview_box)
            else:
                no_img = font_msg.render("No Img", True, (200, 180, 210))
                screen.blit(no_img, (preview_box.x + 35, preview_box.y + 65))

            pygame.draw.rect(screen, (255, 200, 220), preview_box, 3)

        if status_msg:
            # Shift error msg down to bottom
            col = (255, 100, 100) if "Error" in status_msg or "Invalid" in status_msg else (150, 255, 150)
            msg_surf = font_msg.render(status_msg, True, col)
            screen.blit(msg_surf, (center_x - msg_surf.get_width() // 2, 850))

        btn_submit.change_color(pygame.mouse.get_pos())
        btn_submit.update(screen)
        btn_switch.change_color(pygame.mouse.get_pos())
        btn_switch.update(screen)
        btn_back.change_color(pygame.mouse.get_pos())
        btn_back.update(screen)

        pygame.display.update()
        clock.tick(60)