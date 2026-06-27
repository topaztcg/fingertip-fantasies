import pygame
import sys
import os
import re
import shutil
import hashlib
import tkinter as tk
from tkinter import filedialog
import cv2

# Make sure we can import from the main project
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ui_components import Button, BG_FALLBACK, BUTTON_BORDER, TEXT_COLOR, get_font, update_animations, spawn_particles, update_juice, draw_juice_overlays, PROFILE_BG, COLOR_ACTIVE, BUTTON_BASE, BUTTON_HOVER

pygame.init()
pygame.display.set_caption("Antigravity Asset Manager")

# Fullscreen Setup
info = pygame.display.Info()
screen_w, screen_h = info.current_w, info.current_h
screen = pygame.display.set_mode((screen_w, screen_h), pygame.FULLSCREEN)
clock = pygame.time.Clock()

def draw_glass_panel(surface, rect):
    # Sleek frosted glass look
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel, (25, 15, 35, 200), panel.get_rect(), border_radius=15)
    # Highlight top edge slightly for 3D effect
    pygame.draw.rect(panel, (255, 255, 255, 40), panel.get_rect(), 1, border_radius=15)
    surface.blit(panel, rect.topleft)

BASE_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

def get_directories():
    dirs = [""] # root assets folder
    if not os.path.exists(BASE_ASSETS_DIR):
        return dirs
    for root, d_names, f_names in os.walk(BASE_ASSETS_DIR):
        for d in d_names:
            rel_path = os.path.relpath(os.path.join(root, d), BASE_ASSETS_DIR)
            dirs.append(rel_path.replace("\\", "/"))
    return dirs

def get_asset_groups(directory_path):
    groups = {}
    pattern = re.compile(r"^(.*)_old_(\d+)(\.[a-zA-Z0-9]+)$")
    
    if not os.path.exists(directory_path):
        return groups
        
    for filename in os.listdir(directory_path):
        if not os.path.isfile(os.path.join(directory_path, filename)):
            continue
            
        match = pattern.match(filename)
        if match:
            base_name = match.group(1) + match.group(3)
            is_old = True
            version = int(match.group(2))
        else:
            base_name = filename
            is_old = False
            version = 0
            
        if base_name not in groups:
            groups[base_name] = {"main": None, "old": []}
            
        if is_old:
            groups[base_name]["old"].append({"filename": filename, "version": version})
        else:
            groups[base_name]["main"] = filename
            
    final_groups = {}
    for base, data in groups.items():
        data["old"].sort(key=lambda x: x["version"], reverse=True)
        final_groups[base] = data
        
    return final_groups

def get_file_hash(filepath):
    if not os.path.exists(filepath):
        return None
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except:
        return None

def backup_main_if_unique(directory_path, base_name):
    main_path = os.path.join(directory_path, base_name)
    if not os.path.exists(main_path):
        return
        
    main_hash = get_file_hash(main_path)
    if not main_hash:
        return
        
    pattern = re.compile(r"^" + re.escape(os.path.splitext(base_name)[0]) + r"_old_(\d+)" + re.escape(os.path.splitext(base_name)[1]) + r"$")
    
    max_ver = 0
    for f in os.listdir(directory_path):
        m = pattern.match(f)
        if m:
            ver = int(m.group(1))
            max_ver = max(max_ver, ver)
            old_path = os.path.join(directory_path, f)
            if get_file_hash(old_path) == main_hash:
                # Already backed up! No need to save a new _old_XX
                os.remove(main_path)
                return
                
    # Not backed up, save as new version
    next_ver = max_ver + 1
    new_old_name = f"{os.path.splitext(base_name)[0]}_old_{next_ver:02d}{os.path.splitext(base_name)[1]}"
    os.rename(main_path, os.path.join(directory_path, new_old_name))

def import_new_replacement(directory_path, base_name):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title=f"Select Replacement for {base_name}")
    root.destroy()
    
    if not file_path: return False
    
    main_path = os.path.join(directory_path, base_name)
    backup_main_if_unique(directory_path, base_name)
        
    shutil.copy2(file_path, main_path)
    return True

def delete_history_entry(directory_path, filename):
    filepath = os.path.join(directory_path, filename)
    if os.path.exists(filepath):
        os.remove(filepath)

def set_as_main(directory_path, base_name, selected_old_filename):
    main_path = os.path.join(directory_path, base_name)
    old_path = os.path.join(directory_path, selected_old_filename)
    
    if not os.path.exists(old_path): return False
    
    # If restoring an old file that is exactly the same as current main, do nothing
    if os.path.exists(main_path) and get_file_hash(main_path) == get_file_hash(old_path):
        return True
    
    backup_main_if_unique(directory_path, base_name)
        
    shutil.copy2(old_path, main_path)
    return True

vid_cap = None
preview_is_video = False

def load_preview(path):
    global vid_cap, preview_is_video
    if vid_cap is not None:
        vid_cap.release()
        vid_cap = None
    preview_is_video = False
    
    if not path: return None
    ext = path.lower()
    
    if ext.endswith(('.png', '.jpg', '.jpeg', '.bmp')):
        try:
            return pygame.image.load(path).convert_alpha()
        except: pass
    elif ext.endswith(('.mp4', '.avi', '.mov', '.mkv')):
        try:
            vid_cap = cv2.VideoCapture(path)
            preview_is_video = True
            return None
        except: pass
    return None

def main():
    dirs = get_directories()
    active_dir = dirs[0] if dirs else ""
    
    asset_groups = get_asset_groups(os.path.join(BASE_ASSETS_DIR, active_dir))
    active_asset = None
    
    dir_scroll = 0
    asset_scroll = 0
    history_scroll = 0
    
    preview_img = None
    
    btn_import = Button("IMPORT NEW", 1000, 480, 200, 50, font_size=20)
    
    # State tracking
    dragging_scroll = None
    drag_offset = 0
    video_frame_timer = 0
    
    def refresh_data():
        nonlocal asset_groups, active_asset, preview_img, video_frame_timer
        asset_groups = get_asset_groups(os.path.join(BASE_ASSETS_DIR, active_dir))
        if active_asset and active_asset not in asset_groups:
            active_asset = None
            preview_img = None
        if active_asset:
            main_file = asset_groups[active_asset]["main"]
            if main_file:
                preview_img = load_preview(os.path.join(BASE_ASSETS_DIR, active_dir, main_file))
                video_frame_timer = 0
            else:
                preview_img = load_preview(None)

    while True:
        dt = clock.tick(60) / 1000.0
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()
        
        # Dynamic Fullscreen Layout
        dir_rect = pygame.Rect(40, 150, 400, screen_h - 200)
        asset_rect = pygame.Rect(480, 150, 500, screen_h - 200)
        
        right_panel_x = 1020
        right_panel_w = screen_w - right_panel_x - 40
        preview_rect = pygame.Rect(right_panel_x, 150, right_panel_w, screen_h // 2 - 50)
        hist_rect = pygame.Rect(right_panel_x, preview_rect.bottom + 40, right_panel_w, screen_h - preview_rect.bottom - 80)
        
        # Calculate heights for scrolling
        dir_h = len(dirs) * 50
        dir_max_scroll = max(0, dir_h - (dir_rect.height - 60))
        
        asset_keys = list(asset_groups.keys())
        asset_h = len(asset_keys) * 60
        asset_max_scroll = max(0, asset_h - (asset_rect.height - 60))
        
        hist_h = len(asset_groups[active_asset]["old"]) * 65 if active_asset else 0
        hist_max_scroll = max(0, hist_h - (hist_rect.height - 60))
        
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                spawn_particles(mouse_pos[0], mouse_pos[1], 3)
                
                # Directory clicks
                if dir_rect.collidepoint(mouse_pos):
                    idx = int((mouse_pos[1] - (dir_rect.y + 55) + dir_scroll) // 45)
                    if 0 <= idx < len(dirs):
                        active_dir = dirs[idx]
                        active_asset = None
                        preview_img = load_preview(None)
                        refresh_data()
                        asset_scroll = 0
                        
                # Asset clicks
                elif asset_rect.collidepoint(mouse_pos):
                    idx = int((mouse_pos[1] - (asset_rect.y + 55) + asset_scroll) // 55)
                    if 0 <= idx < len(asset_keys):
                        active_asset = asset_keys[idx]
                        history_scroll = 0
                        refresh_data()
                        
                # History Action Clicks
                elif hist_rect.collidepoint(mouse_pos) and active_asset:
                    idx = int((mouse_pos[1] - (hist_rect.y + 55) + history_scroll) // 65)
                    old_list = asset_groups[active_asset]["old"]
                    if 0 <= idx < len(old_list):
                        # Detect RESTORE vs DELETE
                        r = pygame.Rect(hist_rect.x + 10, hist_rect.y + 55 - history_scroll + idx * 65, hist_rect.width - 20, 55)
                        r_restore = pygame.Rect(r.right - 270, r.y + 10, 130, 35)
                        r_delete = pygame.Rect(r.right - 130, r.y + 10, 110, 35)
                        
                        if r_restore.collidepoint(mouse_pos):
                            set_as_main(os.path.join(BASE_ASSETS_DIR, active_dir), active_asset, old_list[idx]["filename"])
                            refresh_data()
                        elif r_delete.collidepoint(mouse_pos):
                            delete_history_entry(os.path.join(BASE_ASSETS_DIR, active_dir), old_list[idx]["filename"])
                            refresh_data()
                        
                if active_asset and btn_import.check_input(mouse_pos):
                    if import_new_replacement(os.path.join(BASE_ASSETS_DIR, active_dir), active_asset):
                        refresh_data()
                        
            if event.type == pygame.MOUSEWHEEL:
                if dir_rect.collidepoint(mouse_pos):
                    dir_scroll = max(0, min(dir_max_scroll, dir_scroll - event.y * 30))
                elif asset_rect.collidepoint(mouse_pos):
                    asset_scroll = max(0, min(asset_max_scroll, asset_scroll - event.y * 30))
                elif hist_rect.collidepoint(mouse_pos):
                    history_scroll = max(0, min(hist_max_scroll, history_scroll - event.y * 30))

        # Video Frame Update
        global vid_cap, preview_is_video
        if active_asset and preview_is_video and vid_cap:
            v_fps = vid_cap.get(cv2.CAP_PROP_FPS) or 30
            video_frame_timer += dt
            if video_frame_timer >= 1.0 / v_fps:
                video_frame_timer = 0
                ret, frame = vid_cap.read()
                if not ret:
                    vid_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = vid_cap.read()
                if ret:
                    # Convert BGR (OpenCV) to RGB (Pygame)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = frame.swapaxes(0, 1)
                    preview_img = pygame.surfarray.make_surface(frame)

        # Refresh keys to prevent KeyError after event loop updates
        asset_keys = list(asset_groups.keys())
        asset_h = len(asset_keys) * 60
        asset_max_scroll = max(0, asset_h - (asset_rect.height - 60))
        
        # Background
        screen.fill((10, 8, 14))
        
        # Aesthetic background glows
        glow_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (150, 50, 150, 20), (400, 200), 600)
        pygame.draw.circle(glow_surf, (50, 100, 200, 15), (screen_w - 300, screen_h - 200), 800)
        screen.blit(glow_surf, (0, 0))
        
        # Header
        title = get_font(50).render("ASSET MANAGER", True, (255, 255, 255))
        screen.blit(title, (40, 30))
        subtitle = get_font(22).render("HOT SWAP & VERSION CONTROL", True, COLOR_ACTIVE)
        screen.blit(subtitle, (40, 90))
        
        # Directories Panel
        draw_glass_panel(screen, dir_rect)
        screen.blit(get_font(20).render("FOLDERS", True, (150, 150, 150)), (dir_rect.x + 20, dir_rect.y + 15))
        pygame.draw.line(screen, (255, 255, 255, 40), (dir_rect.x + 20, dir_rect.y + 45), (dir_rect.right - 20, dir_rect.y + 45), 1)
        
        screen.set_clip(dir_rect)
        dy = dir_rect.y + 55 - dir_scroll
        for d in dirs:
            disp_name = d if d != "" else "assets (root)"
            col = (255, 255, 255) if d == active_dir else (180, 180, 180)
            if dy > dir_rect.y and dy < dir_rect.bottom:
                txt = get_font(18).render(disp_name, True, col)
                screen.blit(txt, (dir_rect.x + 25, dy))
                if d == active_dir:
                    pygame.draw.rect(screen, COLOR_ACTIVE, (dir_rect.x + 5, dy, 4, 22), border_radius=2)
            dy += 45
        screen.set_clip(None)
        
        # Assets Panel
        draw_glass_panel(screen, asset_rect)
        screen.blit(get_font(20).render(f"FILES IN /{(active_dir or 'assets').upper()}", True, (150, 150, 150)), (asset_rect.x + 20, asset_rect.y + 15))
        pygame.draw.line(screen, (255, 255, 255, 40), (asset_rect.x + 20, asset_rect.y + 45), (asset_rect.right - 20, asset_rect.y + 45), 1)
        
        screen.set_clip(asset_rect)
        ay = asset_rect.y + 55 - asset_scroll
        for a in asset_keys:
            col = (255, 255, 255) if a == active_asset else (180, 180, 180)
            if ay > asset_rect.y and ay < asset_rect.bottom:
                txt = get_font(18).render(a, True, col)
                screen.blit(txt, (asset_rect.x + 25, ay + 15))
                versions = len(asset_groups[a]["old"])
                badge = get_font(14).render(f"{versions} version{'s' if versions!=1 else ''}", True, (120, 120, 180))
                screen.blit(badge, (asset_rect.right - badge.get_width() - 20, ay + 18))
                
                if a == active_asset:
                    pygame.draw.rect(screen, COLOR_ACTIVE, (asset_rect.x + 5, ay+15, 4, 22), border_radius=2)
                pygame.draw.line(screen, (255, 255, 255, 10), (asset_rect.x + 15, ay + 50), (asset_rect.right - 15, ay + 50), 1)
            ay += 55
        screen.set_clip(None)
        
        # Right Panel
        draw_glass_panel(screen, preview_rect)

        
        if active_asset:
            title_txt = get_font(25).render(active_asset, True, (255, 255, 255))
            screen.blit(title_txt, (preview_rect.x + 20, preview_rect.y + 20))
            
            # Draw preview
            if preview_img:
                # scale to fit inside preview rect
                pw, ph = preview_img.get_size()
                max_w = preview_rect.width - 40
                max_h = preview_rect.height - 140
                scale = min(max_w / pw, max_h / ph)
                nw, nh = int(pw * scale), int(ph * scale)
                scaled_img = pygame.transform.smoothscale(preview_img, (nw, nh))
                px = preview_rect.x + 20 + (max_w - nw) // 2
                py = preview_rect.y + 60 + (max_h - nh) // 2
                screen.blit(scaled_img, (px, py))
                pygame.draw.rect(screen, (255, 255, 255, 30), (px-1, py-1, nw+2, nh+2), 1, border_radius=5)
            else:
                txt = get_font(18).render("No Image/Video Preview Available", True, (120, 120, 120))
                screen.blit(txt, (preview_rect.centerx - txt.get_width()//2, preview_rect.centery - 20))
                
            btn_import.rect.centerx = preview_rect.centerx
            btn_import.rect.y = preview_rect.bottom - 70
            btn_import.change_color(mouse_pos)
            btn_import.update(screen)
            
            # History
            draw_glass_panel(screen, hist_rect)
            screen.blit(get_font(20).render("VERSION HISTORY", True, (150, 150, 150)), (hist_rect.x + 20, hist_rect.y + 15))
            pygame.draw.line(screen, (255, 255, 255, 40), (hist_rect.x + 20, hist_rect.y + 45), (hist_rect.right - 20, hist_rect.y + 45), 1)
            
            screen.set_clip(hist_rect)
            hy = hist_rect.y + 55 - history_scroll
            old_list = asset_groups[active_asset]["old"]
            if not old_list:
                screen.blit(get_font(16).render("No previous versions found.", True, (100, 100, 100)), (hist_rect.x + 20, hist_rect.y + 70))
            for old in old_list:
                if hy > hist_rect.y and hy < hist_rect.bottom:
                    r = pygame.Rect(hist_rect.x + 10, hy, hist_rect.width - 20, 55)
                    hov = r.collidepoint(mouse_pos)
                    
                    bg_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
                    if hov:
                        pygame.draw.rect(bg_surf, (80, 50, 100, 180), bg_surf.get_rect(), border_radius=8)
                        pygame.draw.rect(bg_surf, COLOR_ACTIVE, bg_surf.get_rect(), 1, border_radius=8)
                    else:
                        pygame.draw.rect(bg_surf, (0, 0, 0, 60), bg_surf.get_rect(), border_radius=8)
                        
                    # Hover Actions
                    r_restore = pygame.Rect(r.width - 270, 10, 130, 35)
                    r_delete = pygame.Rect(r.width - 130, 10, 110, 35)
                    if hov:
                        rest_hov = r_restore.collidepoint(mouse_pos[0] - r.x, mouse_pos[1] - r.y)
                        del_hov = r_delete.collidepoint(mouse_pos[0] - r.x, mouse_pos[1] - r.y)
                        
                        pygame.draw.rect(bg_surf, (50, 150, 50) if rest_hov else (30, 100, 30), r_restore, border_radius=5)
                        tr = get_font(14).render("RESTORE", True, (255, 255, 255))
                        bg_surf.blit(tr, (r_restore.x + (r_restore.width - tr.get_width())//2, r_restore.y + 10))
                        
                        pygame.draw.rect(bg_surf, (150, 50, 50) if del_hov else (100, 30, 30), r_delete, border_radius=5)
                        td = get_font(14).render("DELETE", True, (255, 255, 255))
                        bg_surf.blit(td, (r_delete.x + (r_delete.width - td.get_width())//2, r_delete.y + 10))
                        
                    screen.blit(bg_surf, r.topleft)
                    
                    txt = get_font(20).render(f"Version {old['version']:02d}", True, (255, 255, 255))
                    screen.blit(txt, (r.x + 15, hy + 16))
                    
                    sub = get_font(14).render(old['filename'], True, (150, 150, 150))
                    screen.blit(sub, (r.x + 15 + txt.get_width() + 15, hy + 20))
                    
                hy += 65
            screen.set_clip(None)
        else:
            txt = get_font(25).render("Select an asset to view details", True, (100, 100, 100))
            screen.blit(txt, (preview_rect.centerx - txt.get_width()//2, preview_rect.centery))

        update_animations(dt)
        update_juice(dt)
        draw_juice_overlays(screen)
        pygame.display.flip()

if __name__ == "__main__":
    main()
