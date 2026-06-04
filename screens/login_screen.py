import pygame
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
from tkinter import filedialog
from ui_components import (
    Button, InputBox, BG_FALLBACK, TEXT_COLOR, get_font, 
    update_animations, draw_panel, spawn_particles, update_juice, draw_juice_overlays,
    TEXT_SHADOW, COLOR_PASSIVE, COLOR_ACTIVE
)
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
    status_timer = 0

    # Layout Config
    W, H = screen.get_width(), screen.get_height()
    PANEL_W, PANEL_H = 550, 700
    panel_x = (W - PANEL_W) // 2
    panel_y = (H - PANEL_H) // 2

    # Inputs (Centered in Panel)
    # Start inputs roughly 1/3 down the panel
    start_y_rel = 200
    input_w = 360
    input_h = 60
    input_x = panel_x + (PANEL_W - input_w) // 2
    
    user_box = InputBox(input_x, panel_y + start_y_rel, input_w, input_h, placeholder="Username")
    pass_box = InputBox(input_x, panel_y + start_y_rel + 120, input_w, input_h, placeholder="Password", is_password=True)

    # Buttons
    btn_w = 260
    btn_h = 60
    btn_submit = Button("LOGIN", panel_x + (PANEL_W - btn_w)//2, panel_y + 460, btn_w, btn_h, font_size=28)
    
    # Switch Mode Button (Link style at bottom)
    btn_switch = Button("Create Account", panel_x + (PANEL_W - 300)//2, panel_y + 560, 300, 45, font_size=22)
    # Style tweak for "link" look? For now standard button but smaller

    btn_back = Button("BACK", 30, 30, 120, 50, font_size=24)

    # Avatar (Register Mode)
    btn_avatar = Button("Upload Avatar", panel_x + (PANEL_W - 250)//2, panel_y + 300, 250, 45, font_size=24)

    font_title = get_font(60)
    font_msg = get_font(24)

    uploaded_avatar_surf = None

    # Spawn some initial particles
    spawn_particles(W//2, H//2, count=30, color=COLOR_ACTIVE)

    while True:
        dt = clock.tick(60) / 1000.0
        events = pygame.event.get()
        
        mouse_pos = pygame.mouse.get_pos()

        for event in events:
            if event.type == pygame.QUIT:
                sys.exit()

            user_box.handle_event(event)
            pass_box.handle_event(event)
            
            # Interactive Particles on click
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                spawn_particles(event.pos[0], event.pos[1], count=5, color=(200, 100, 200))

            if btn_back.handle_event(event):
                return ("BACK", None)

            if btn_switch.handle_event(event):
                status_msg = ""
                uploaded_avatar_surf = None
                if mode == "LOGIN":
                    mode = "REGISTER"
                    btn_submit.set_text("REGISTER")
                    btn_switch.set_text("Back to Login")
                    PANEL_H = 800 # Expand for avatar
                    pass_box.rect.y = panel_y + start_y_rel + 120 # Reset pos
                else:
                    mode = "LOGIN"
                    btn_submit.set_text("LOGIN")
                    btn_switch.set_text("Create Account")
                    PANEL_H = 700
                
                # Re-center panel Y
                panel_y = (H - PANEL_H) // 2
                # Re-calc relative positions
                user_box.rect.y = panel_y + start_y_rel
                pass_box.rect.y = panel_y + start_y_rel + 120
                btn_avatar.rect.y = panel_y + 380
                btn_submit.rect.y = panel_y + PANEL_H - 180
                btn_switch.rect.y = panel_y + PANEL_H - 80
                # Re-center X
                user_box.rect.x = panel_x + (PANEL_W - input_w) // 2
                pass_box.rect.x = panel_x + (PANEL_W - input_w) // 2
                btn_submit.rect.x = panel_x + (PANEL_W - btn_w) // 2
                btn_switch.rect.x = panel_x + (PANEL_W - 300) // 2
                btn_avatar.rect.x = panel_x + (PANEL_W - 250) // 2


            if mode == "REGISTER" and btn_avatar.handle_event(event):
                path = get_image_from_pc()
                if path:
                    try:
                        raw = pygame.image.load(path).convert_alpha()
                        uploaded_avatar_surf = pygame.transform.scale(raw, (800, 800)) # Store hi-res
                        status_msg = "Avatar Selected"
                        status_timer = 3.0
                    except:
                        status_msg = "Error loading image"
                        status_timer = 3.0

            if btn_submit.handle_event(event):
                u_val = user_box.get_text().strip()
                p_val = pass_box.get_text().strip()
                
                # Check empty
                if not u_val or not p_val:
                    status_msg = "Missing fields!"
                    status_timer = 2.0
                else:
                    # Logic
                    if mode == "LOGIN":
                        if user_mgr.validate_login(u_val, p_val):
                            return ("LOGIN_SUCCESS", u_val)
                        else:
                            status_msg = "Invalid Credentials"
                            status_timer = 2.0
                    else:
                        # Register
                        final_av = uploaded_avatar_surf
                        if not final_av:
                            final_av = pygame.Surface((800, 800))
                            final_av.fill(COLOR_PASSIVE)
                        
                        success, msg = user_mgr.create_user(u_val, p_val, final_av)
                        status_msg = msg
                        status_timer = 3.0
                        if success:
                            # Switch back to login
                            mode = "LOGIN"
                            btn_submit.set_text("LOGIN")
                            btn_switch.set_text("Create Account")
                            PANEL_H = 700
                            panel_y = (H - PANEL_H) // 2
                            # Reset pos... (Simpler to just copy paste re-calc or make function, but this works)
                            user_box.rect.y = panel_y + start_y_rel
                            pass_box.rect.y = panel_y + start_y_rel + 120
                            btn_submit.rect.y = panel_y + PANEL_H - 180
                            btn_switch.rect.y = panel_y + PANEL_H - 80

        # --- DRAWING ---
        screen.fill(BG_FALLBACK)
        
        # 1. Background Juice
        update_juice(dt)
        draw_juice_overlays(screen)

        # 2. Main Glass Panel
        draw_panel(screen, panel_x, panel_y, PANEL_W, PANEL_H)
        
        # 3. Title
        title_txt = "WELCOME" if mode == "LOGIN" else "JOIN US"
        t_surf = font_title.render(title_txt, True, (255, 255, 255))
        # Shadow
        t_shad = font_title.render(title_txt, True, TEXT_SHADOW)
        t_x = panel_x + (PANEL_W - t_surf.get_width())//2
        t_y = panel_y + 40
        screen.blit(t_shad, (t_x+2, t_y+2))
        screen.blit(t_surf, (t_x, t_y))
        
        # Subtitle
        sub_txt = "Login to continue" if mode == "LOGIN" else "Create your profile"
        s_surf = get_font(24).render(sub_txt, True, (200, 180, 220))
        screen.blit(s_surf, (panel_x + (PANEL_W - s_surf.get_width())//2, t_y + 70))

        # 4. Components
        user_box.update()
        pass_box.update()
        user_box.draw(screen)
        pass_box.draw(screen)

        btn_submit.change_color(mouse_pos)
        btn_submit.update(screen)
        
        btn_switch.change_color(mouse_pos)
        btn_switch.update(screen)
        
        btn_back.change_color(mouse_pos)
        btn_back.update(screen)
        
        if mode == "REGISTER":
            btn_avatar.change_color(mouse_pos)
            btn_avatar.update(screen)
            # Preview Avatar
            prev_x = btn_avatar.rect.right + 20
            prev_y = btn_avatar.rect.y
            prev_rect = pygame.Rect(panel_x + 40, btn_avatar.rect.y - 10, 60, 60) # Left side?
            # Actually let's put it next to the button or small icon
            
            if uploaded_avatar_surf:
                sc = pygame.transform.smoothscale(uploaded_avatar_surf, (50, 50))
                screen.blit(sc, (btn_avatar.rect.right + 10, btn_avatar.rect.y))
                pygame.draw.rect(screen, (100, 255, 100), (btn_avatar.rect.right + 10, btn_avatar.rect.y, 50, 50), 2)

        # 5. Status Message
        if status_msg:
            status_timer -= dt
            if status_timer <= 0: status_msg = ""
            
            col = (255, 100, 100) if "Error" in status_msg or "Invalid" in status_msg or "Missing" in status_msg else (100, 255, 100)
            m_surf = font_msg.render(status_msg, True, col)
            screen.blit(m_surf, (panel_x + (PANEL_W - m_surf.get_width())//2, panel_y + PANEL_H - 40))

        update_animations(dt)
        pygame.display.update()