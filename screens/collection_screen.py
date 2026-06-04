import pygame
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui_components import Button, BG_FALLBACK, BUTTON_BORDER, TEXT_COLOR, get_font, update_animations, draw_panel, spawn_particles, update_juice, draw_juice_overlays, TEXT_SHADOW, PROFILE_BG, AnimationManager
from card_manager import CardManager
import pytweening
from video_player import VideoWrapper, run_fullscreen_video


# --- HELPER- TEXT WRAPPING ---
def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        w, h = font.size(test_line)
        if w < max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    return lines


class CardPreview:
    def __init__(self, card_data, x, y, w, h):
        self.data = card_data
        self.rect = pygame.Rect(x, y, w, h)
        self.base_rect = pygame.Rect(x, y, w, h)
        self.hovered = False
        self.is_hovered = False
        self.scale = 1.0

        self.final_surf = None
        if os.path.exists(card_data["image_path"]):
            try:
                raw = pygame.image.load(card_data["image_path"]).convert_alpha()
                # Maintain aspect ratio for crop
                # We want to fill the card width/height
                img_ratio = raw.get_width() / raw.get_height()
                tgt_ratio = w / h
                
                if img_ratio > tgt_ratio:
                    # Image is wider -> scale by height, crop width
                    scale_h = h
                    scale_w = int(h * img_ratio)
                else:
                    # Image is taller -> scale by width, crop height
                    scale_w = w
                    scale_h = int(w / img_ratio)
                
                scaled = pygame.transform.smoothscale(raw, (scale_w, scale_h))
                # Center crop
                crop_x = (scale_w - w) // 2
                crop_y = (scale_h - h) // 2
                
                self.final_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                
                # Create mask for rounded corners
                mask = pygame.Surface((w, h), pygame.SRCALPHA)
                pygame.draw.rect(mask, (255, 255, 255), (0, 0, w, h), border_radius=12)
                
                # Blit image to surface
                self.final_surf.blit(scaled, (0, 0), (crop_x, crop_y, w, h))
                
                # Apply mask (simplified approach: just draw border over it later or use special flags if needed)
                # For now simply blitting rect is fine, masking in pygame is expensive without special blending
                
            except Exception as e:
                print(f"Error loading card img: {e}")

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)
        
        if self.hovered and not self.is_hovered:
            self.is_hovered = True
            AnimationManager.get().start_tween(self, "scale", 1.08, 0.2, pytweening.easeOutBack)
        elif not self.hovered and self.is_hovered:
            self.is_hovered = False
            AnimationManager.get().start_tween(self, "scale", 1.0, 0.2, pytweening.easeOutQuad)

    def draw(self, screen):
        # Hover Scale Effect
        scale_factor = self.scale
        current_w = int(self.base_rect.width * scale_factor)
        current_h = int(self.base_rect.height * scale_factor)
        current_x = self.base_rect.centerx - (current_w // 2)
        current_y = self.base_rect.centery - (current_h // 2)

        draw_rect = pygame.Rect(current_x, current_y, current_w, current_h)
        
        # Draw Shadow
        shadow_rect = draw_rect.copy()
        shadow_rect.y += 6
        shadow_rect.x += 4
        shadow_surf = pygame.Surface((current_w, current_h), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (50, 20, 50, 100), shadow_surf.get_rect(), border_radius=12)
        screen.blit(shadow_surf, (shadow_rect.x, shadow_rect.y))

        # Draw Base/Image
        if self.final_surf:
            if self.hovered:
                scaled_res = pygame.transform.smoothscale(self.final_surf, (current_w, current_h))
                screen.blit(scaled_res, (current_x, current_y))
            else:
                screen.blit(self.final_surf, (current_x, current_y))
        else:
            pygame.draw.rect(screen, PROFILE_BG, draw_rect, border_radius=12)

        # Gradient Overlay at bottom for text readability
        grad_h = 80
        grad_surf = pygame.Surface((current_w, grad_h), pygame.SRCALPHA)
        for i in range(grad_h):
            alpha = int(200 * (i / grad_h))
            pygame.draw.line(grad_surf, (20, 10, 30, alpha), (0, i), (current_w, i))
        screen.blit(grad_surf, (current_x, current_y + current_h - grad_h))

        # Border
        border_col = (138, 43, 226) if self.data.get("unlocked", False) else (100, 100, 100)
        if self.hovered: border_col = (200, 100, 255)
        pygame.draw.rect(screen, border_col, draw_rect, 2, border_radius=12)

        # Name with dynamic sizing
        name_font_size = 22
        font = get_font(name_font_size)
        name_txt = self.data["name"]
        
        # Check if text fits
        max_txt_w = current_w - 20
        while font.size(name_txt)[0] > max_txt_w and name_font_size > 14:
            name_font_size -= 2
            font = get_font(name_font_size)
        
        name_surf = font.render(name_txt, True, (255, 255, 255))
        name_shad = font.render(name_txt, True, (0, 0, 0))
        
        # Consistent text positioning (centered horizontally, padded from bottom)
        # Move up slightly to account for descenders (p, g, y)
        txt_center_x = current_x + current_w // 2
        txt_y = current_y + current_h - 45 
        
        # Subtler shadow offset
        screen.blit(name_shad, (txt_center_x - name_surf.get_width() // 2 + 1, txt_y + 1))
        screen.blit(name_surf, (txt_center_x - name_surf.get_width() // 2, txt_y))


def show_collection_screen(screen):
    clock = pygame.time.Clock()
    mgr = CardManager()
    all_cards = mgr.get_all_cards()

    # Dynamic Grid Layout Logic
    max_cols = 5
    card_w, card_h = 180, 250
    gap_x, gap_y = 60, 60
    
    # Calculate effective columns to center properly if few cards exist
    num_cards = len(all_cards)
    effective_cols = min(num_cards, max_cols) if num_cards > 0 else 1
    
    # Total Grid Width based on effective columns
    total_grid_w = (effective_cols * card_w) + ((effective_cols - 1) * gap_x)
    start_x = (screen.get_width() - total_grid_w) // 2
    start_y = 220 # Push down to make room for header

    preview_objs = []

    for i, data in enumerate(all_cards):
        row = i // max_cols
        col = i % max_cols
        
        # Logic for centering cards on subsequent rows if needed? 
        # Standard grid: left aligned within the centered container.
        # But if total cards < max_cols, container shrinks, so they are effectively centered.
        
        x = start_x + (col * (card_w + gap_x))
        y = start_y + (row * (card_h + gap_y))
        preview_objs.append(CardPreview(data, x, y, card_w, card_h))

    btn_back = Button("BACK", 50, 40, 150, 60, font_size=28)

    while True:
        dt = clock.tick(60) / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # LEFT CLICK ONLY
                    spawn_particles(event.pos[0], event.pos[1], count=5, color=(200, 100, 200))

                    if btn_back.check_input(mouse_pos):
                        return "BACK"

                    for card in preview_objs:
                        if card.hovered:
                            run_inspector_modal(screen, card.data)

        # Draw Background (Dark Gradients)
        screen.fill(BG_FALLBACK)
        
        # Header (Centered)
        t_font = get_font(60)
        title_txt = "CARD COLLECTION"
        title = t_font.render(title_txt, True, (255, 255, 255))
        t_shad = t_font.render(title_txt, True, TEXT_SHADOW)
        
        title_x = (screen.get_width() - title.get_width()) // 2
        # Tighter shadow
        screen.blit(t_shad, (title_x + 2, 52)) 
        screen.blit(title, (title_x, 50))
        
        # Divider Line - MOVED DOWN to avoid overlap
        line_y = 170
        line_w = screen.get_width() * 0.8
        line_start_x = (screen.get_width() - line_w) // 2
        pygame.draw.line(screen, BUTTON_BORDER, (line_start_x, line_y), (line_start_x + line_w, line_y), 2)

        for card in preview_objs:
            card.update(mouse_pos)
            card.draw(screen)

        btn_back.change_color(mouse_pos)
        btn_back.update(screen)

        update_animations(dt)
        update_juice(dt)
        draw_juice_overlays(screen)
        pygame.display.update()


def run_inspector_modal(screen, data):
    clock = pygame.time.Clock()

    w, h = 1400, 900
    x = (screen.get_width() - w) // 2
    y = (screen.get_height() - h) // 2
    window_rect = pygame.Rect(x, y, w, h)

    btn_close = Button("X", x + w - 60, y + 10, 50, 50, font_size=30)

    font_h = get_font(50)
    font_b = get_font(30)
    font_s = get_font(22)

    full_art_surf = None
    img_area_w = int(w * 0.4)
    if os.path.exists(data["image_path"]):
        try:
            raw = pygame.image.load(data["image_path"]).convert_alpha()
            # Crop/Scale to fill left panel
            # We want to maintain aspect ratio but cover the area
            ir = raw.get_width() / raw.get_height()
            tr = img_area_w / h
            
            if ir > tr:
                # Wider image -> Scale by height, center horizontally
                sh = h
                sw = int(h * ir)
                scaled = pygame.transform.smoothscale(raw, (sw, sh))
                full_art_surf = pygame.Surface((img_area_w, h), pygame.SRCALPHA)
                offset_x = (sw - img_area_w) // 2
                full_art_surf.blit(scaled, (-offset_x, 0))
            else:
                # Taller or equal -> Scale by width
                sw = img_area_w
                sh = int(sw / ir)
                scaled = pygame.transform.smoothscale(raw, (sw, sh))
                full_art_surf = pygame.Surface((img_area_w, h), pygame.SRCALPHA)
                offset_y = (sh - h) // 2
                full_art_surf.blit(scaled, (0, -offset_y))
                
        except:
            pass

    # Initialize Videos
    vid_w, vid_h = 320, 180 # Slightly larger video
    videos = {}
    v_paths = data.get("videos", {})

    # Only load videos if path exists
    if v_paths.get("normal") and os.path.exists(v_paths["normal"]):
        videos["normal"] = VideoWrapper(v_paths["normal"], (vid_w, vid_h), muted=True, loop=True)
    if v_paths.get("skill") and os.path.exists(v_paths["skill"]):
        videos["skill"] = VideoWrapper(v_paths["skill"], (vid_w, vid_h), muted=True, loop=True)
    if v_paths.get("ult") and os.path.exists(v_paths["ult"]):
        videos["ult"] = VideoWrapper(v_paths["ult"], (vid_w, vid_h), muted=True, loop=True)

    scroll_y = 0
    right_panel_w = w - img_area_w - 60
    
    # Pre-wrap text for layout
    moves = data.get("moves", {})
    # Modernized Move Keys
    move_order = [("NORMAL ATTACK", "normal", (200, 200, 255)),
                  ("SKILL", "skill", (150, 255, 150)),
                  ("ULTIMATE", "ult", (255, 100, 100))]

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        update_animations(dt)
        
        mouse_pos = pygame.mouse.get_pos()
        events = pygame.event.get()

        # Update Videos
        current_frames = {}
        for k, v in videos.items():
            frame, val = v.update()
            current_frames[k] = frame

        # --- CALCULATE LAYOUT DYNAMICALLY ---
        layout_items = []
        cursor_y = 0

        # 1. Header (Name + Type)
        layout_items.append(("header", data["name"], (0, cursor_y)))
        cursor_y += 60
        
        type_txt = data.get("type", "Unknown Unit").upper().replace("_", " ")
        layout_items.append(("type", type_txt, (0, cursor_y)))
        cursor_y += 50
        
        # 2. Stats Row (HP / Energy)
        # We'll draw these as "Pills" manually in the draw loop, just marking position here
        layout_items.append(("stats_row", data, (0, cursor_y)))
        cursor_y += 80 
        
        # Separator
        layout_items.append(("line", None, (0, cursor_y)))
        cursor_y += 30

        # 3. Abilities List
        for title, key, color in move_order:
            if key not in moves: continue
            m_data = moves[key]
            
            # Ability Block Background needs total height
            block_start_y = cursor_y
            
            # Title
            layout_items.append(("move_title", (title, color), (0, cursor_y)))
            cursor_y += 35
            
            # Info (Name + Dmg + Cost)
            name_str = f"{m_data.get('name', 'Unknown')}"
            dmg_str = f"DMG: {m_data.get('dmg', 0)}"
            cost_str = ""
            if 'cost' in m_data and m_data['cost']: cost_str = f"Cost: {m_data['cost']}"
            
            layout_items.append(("move_info", (name_str, dmg_str, cost_str), (0, cursor_y)))
            cursor_y += 30
            
            # Description
            desc_lines = wrap_text(m_data.get('desc', ''), font_s, right_panel_w - 20)
            for line in desc_lines:
                layout_items.append(("desc_text", line, (0, cursor_y)))
                cursor_y += 25
            
            cursor_y += 15
            
            # Video (if exists)
            if key in videos:
                vid_rect = pygame.Rect(0, cursor_y, vid_w, vid_h)
                layout_items.append(("video", key, vid_rect))
                cursor_y += vid_h + 20
            
            cursor_y += 30 # Spacing between abilities

        total_content_height = cursor_y + 50
        viewport_h = h - 60
        max_scroll = max(0, total_content_height - viewport_h)

        # --- EVENT HANDLING ---
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEWHEEL:
                scroll_y -= event.y * 30
                scroll_y = max(0, min(scroll_y, max_scroll))

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: 
                    spawn_particles(event.pos[0], event.pos[1], count=5, color=(200, 100, 200))

                    if btn_close.check_input(mouse_pos):
                        running = False
                    elif not window_rect.collidepoint(mouse_pos):
                        running = False

                    # Video Fullscreen Click
                    base_x = x + img_area_w + 40
                    base_y = y + 30
                    view_rect = pygame.Rect(base_x, base_y, right_panel_w - 20, viewport_h)
                    
                    if view_rect.collidepoint(mouse_pos):
                        for item_type, content, pos_data in layout_items:
                            if item_type == "video":
                                screen_rect = pygame.Rect(
                                    base_x + pos_data.x,
                                    base_y + pos_data.y - scroll_y,
                                    pos_data.width,
                                    pos_data.height
                                )
                                if screen_rect.collidepoint(mouse_pos):
                                    run_fullscreen_video(screen, v_paths[content])

        # --- DRAWING ---
        screen.fill(BG_FALLBACK) # Background behind modal
        
        # Draw Main Panel (Glass Style)
        draw_panel(screen, x, y, w, h)
        
        # Left Panel (Art)
        if full_art_surf:
            screen.blit(full_art_surf, (x, y))
            # Gradient fade on right edge of image to blend
            fade = pygame.Surface((50, h), pygame.SRCALPHA)
            for i in range(50):
                alpha = int(255 * (i/49))
                pygame.draw.line(fade, (0, 0, 0, alpha), (i, 0), (i, h))
            # Actually we are using a panel over it? No, art is on top. 
            # Let's draw a border line between art and content
            pygame.draw.line(screen, BUTTON_BORDER, (x + img_area_w, y), (x + img_area_w, y + h), 2)

        # SCROLL AREA
        base_x = x + img_area_w + 40
        base_y = y + 30
        view_rect = pygame.Rect(base_x, base_y, right_panel_w - 20, viewport_h)

        screen.set_clip(view_rect)

        for item_type, content, pos_data in layout_items:
            # Check visibility
            if item_type == "video":
                 item_y = pos_data.y
                 item_h = pos_data.height
            else:
                 item_y = pos_data[1]
                 item_h = 30 # approx
            
            draw_y = base_y + item_y - scroll_y
            
            # Optimization: Skip if off screen
            if draw_y + item_h < 0 or draw_y > screen.get_height():
                continue

            if item_type == "header":
                # Name with shadow
                t_surf = font_h.render(content, True, (255, 255, 255))
                t_shad = font_h.render(content, True, TEXT_SHADOW)
                screen.blit(t_shad, (base_x + 2, draw_y + 2))
                screen.blit(t_surf, (base_x, draw_y))
            
            elif item_type == "type":
                t_surf = font_b.render(content, True, (200, 200, 220))
                screen.blit(t_surf, (base_x, draw_y))
            
            elif item_type == "stats_row":
                # Draw Pills
                hp = content.get('hp', 10)
                en = content.get('energy_max', 3)
                
                # HP Pill
                hp_rect = pygame.Rect(base_x, draw_y, 140, 40)
                pygame.draw.rect(screen, PROFILE_BG, hp_rect, border_radius=20)
                pygame.draw.rect(screen, (255, 100, 150), hp_rect, 2, border_radius=20)
                hp_s = font_s.render(f"HP: {hp}", True, (255, 200, 200))
                screen.blit(hp_s, (hp_rect.centerx - hp_s.get_width()//2, hp_rect.centery - hp_s.get_height()//2))

                # Energy Pill
                en_rect = pygame.Rect(base_x + 160, draw_y, 140, 40)
                pygame.draw.rect(screen, PROFILE_BG, en_rect, border_radius=20)
                pygame.draw.rect(screen, (50, 150, 255), en_rect, 2, border_radius=20)
                en_s = font_s.render(f"EN: {en}", True, (200, 240, 255))
                screen.blit(en_s, (en_rect.centerx - en_s.get_width()//2, en_rect.centery - en_s.get_height()//2))

            elif item_type == "line":
                pygame.draw.line(screen, BUTTON_BORDER, (base_x, draw_y), (base_x + right_panel_w - 60, draw_y), 2)
            
            elif item_type == "move_title":
                title, col = content
                s = font_b.render(title, True, col)
                screen.blit(s, (base_x, draw_y))
            
            elif item_type == "move_info":
                name, dmg, cost = content
                n_s = font_s.render(name, True, (255, 255, 255))
                screen.blit(n_s, (base_x, draw_y))
                
                # Draw badged info next to it
                offset_x = n_s.get_width() + 20
                if dmg:
                    d_s = font_s.render(dmg, True, (255, 100, 100))
                    screen.blit(d_s, (base_x + offset_x, draw_y))
                    offset_x += d_s.get_width() + 20
                if cost:
                    c_s = font_s.render(cost, True, (100, 200, 255))
                    screen.blit(c_s, (base_x + offset_x, draw_y))

            elif item_type == "desc_text":
                s = font_s.render(content, True, (200, 200, 200))
                screen.blit(s, (base_x, draw_y))
            
            elif item_type == "video":
                # Draw Video
                draw_rect = pygame.Rect(base_x + pos_data.x, draw_y, pos_data.width, pos_data.height)
                
                vid_key = content
                if vid_key in current_frames and current_frames[vid_key]:
                    screen.blit(current_frames[vid_key], draw_rect)
                    pygame.draw.rect(screen, (255, 255, 255), draw_rect, 2)
                else:
                    pygame.draw.rect(screen, (0, 0, 0), draw_rect)
                    pygame.draw.rect(screen, (50, 50, 50), draw_rect, 2)
                    no_vid = font_s.render("NO VIDEO", True, (100, 100, 100))
                    screen.blit(no_vid, (draw_rect.centerx - no_vid.get_width() // 2, draw_rect.centery))

        screen.set_clip(None)
        
        # ScrollBar
        if max_scroll > 0:
            scroll_pct = scroll_y / max_scroll
            bar_h = max(30, (viewport_h / total_content_height) * viewport_h)
            avail_h = viewport_h - bar_h
            bar_y = view_rect.y + (scroll_pct * avail_h)
            bar_rect = pygame.Rect(base_x + right_panel_w - 15, bar_y, 6, bar_h)
            pygame.draw.rect(screen, BUTTON_BORDER, bar_rect, border_radius=3)

        btn_close.change_color(mouse_pos)
        btn_close.update(screen)

        update_juice(dt)
        draw_juice_overlays(screen)
        pygame.display.update()
        clock.tick(60)

    for v in videos.values():
        v.close()