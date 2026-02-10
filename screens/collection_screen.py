import pygame
import sys
import os
from ui_components import Button, BG_FALLBACK, BUTTON_BORDER, TEXT_COLOR, get_font
from card_manager import CardManager
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

        self.final_surf = None
        if os.path.exists(card_data["image_path"]):
            try:
                raw = pygame.image.load(card_data["image_path"]).convert_alpha()
                scaled_img = pygame.transform.scale(raw, (w, h))
                self.final_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                pygame.draw.rect(self.final_surf, (255, 255, 255), (0, 0, w, h), border_radius=15)
                self.final_surf.blit(scaled_img, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            except Exception as e:
                print(f"Error loading card img: {e}")

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, screen):
        if self.hovered:
            scale_factor = 1.1
            current_w = int(self.base_rect.width * scale_factor)
            current_h = int(self.base_rect.height * scale_factor)
            current_x = self.base_rect.centerx - (current_w // 2)
            current_y = self.base_rect.centery - (current_h // 2)
        else:
            current_w, current_h = self.base_rect.width, self.base_rect.height
            current_x, current_y = self.base_rect.x, self.base_rect.y

        draw_rect = pygame.Rect(current_x, current_y, current_w, current_h)

        shadow_rect = draw_rect.copy()
        shadow_rect.y += 5
        pygame.draw.rect(screen, (20, 20, 20), shadow_rect, border_radius=15)

        if self.final_surf:
            if self.hovered:
                scaled_res = pygame.transform.smoothscale(self.final_surf, (current_w, current_h))
                screen.blit(scaled_res, (current_x, current_y))
            else:
                screen.blit(self.final_surf, (current_x, current_y))
        else:
            pygame.draw.rect(screen, (50, 50, 50), draw_rect, border_radius=15)

        border_col = (138, 43, 226) if self.data.get("unlocked", False) else (100, 100, 100)
        pygame.draw.rect(screen, border_col, draw_rect, 3, border_radius=15)

        font = get_font(25)
        name_surf = font.render(self.data["name"], True, TEXT_COLOR)

        text_bg = pygame.Surface((draw_rect.width, 40), pygame.SRCALPHA)
        text_bg.fill((0, 0, 0, 180))
        screen.blit(text_bg, (draw_rect.x, draw_rect.bottom - 40))

        text_rect = name_surf.get_rect(center=(draw_rect.centerx, draw_rect.bottom - 20))
        screen.blit(name_surf, text_rect)


def show_collection_screen(screen):
    clock = pygame.time.Clock()
    mgr = CardManager()
    all_cards = mgr.get_all_cards()

    start_x, start_y = 150, 150
    card_w, card_h = 180, 250
    gap_x, gap_y = 40, 40
    cols = 5

    preview_objs = []

    for i, data in enumerate(all_cards):
        row = i // cols
        col = i % cols
        x = start_x + (col * (card_w + gap_x))
        y = start_y + (row * (card_h + gap_y))
        preview_objs.append(CardPreview(data, x, y, card_w, card_h))

    btn_back = Button("BACK", 50, 50, 150, 50, font_size=30)

    while True:
        mouse_pos = pygame.mouse.get_pos()
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # LEFT CLICK ONLY
                    if btn_back.check_input(mouse_pos):
                        return "BACK"

                    for card in preview_objs:
                        if card.hovered:
                            run_inspector_modal(screen, card.data)

        screen.fill(BG_FALLBACK)

        title = get_font(60).render("CARD COLLECTION", True, TEXT_COLOR)
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 50))

        for card in preview_objs:
            card.update(mouse_pos)
            card.draw(screen)

        btn_back.change_color(mouse_pos)
        btn_back.update(screen)

        pygame.display.update()
        clock.tick(60)


def run_inspector_modal(screen, data):
    clock = pygame.time.Clock()

    w, h = 1400, 900
    x = (screen.get_width() - w) // 2
    y = (screen.get_height() - h) // 2
    window_rect = pygame.Rect(x, y, w, h)

    btn_close = Button("X", x + w - 60, y + 10, 50, 50, font_size=30)

    font_h = get_font(80)
    font_b = get_font(40)
    font_s = get_font(30)

    full_art_surf = None
    img_area_w = int(w * 0.4)
    if os.path.exists(data["image_path"]):
        try:
            raw = pygame.image.load(data["image_path"]).convert_alpha()
            full_art_surf = pygame.transform.scale(raw, (img_area_w, h))
        except:
            pass

    # Initialize Videos
    vid_w, vid_h = 240, 135
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

    # --- COLORS ---
    BG_MODAL = (60, 20, 80)
    TITLE_COLOR = (255, 182, 193)
    SUB_COLOR = (200, 100, 255)
    TEXT_DESC = (255, 220, 255)

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        events = pygame.event.get()

        # --- FIX: UNPACK TUPLE FROM VIDEO UPDATE ---
        current_frames = {}
        for k, v in videos.items():
            frame, val = v.update()  # <--- FIXED HERE
            current_frames[k] = frame

        # --- CALCULATE LAYOUT ---
        layout_items = []
        cursor_y = 0

        # Header
        layout_items.append(("header", data["name"], (0, cursor_y)))
        cursor_y += 100

        stats_line = f"Max HP: {data.get('hp', 10)}   |   Max Energy: {data.get('energy_max', 3)}"
        layout_items.append(("sub_header", stats_line, (0, cursor_y)))
        cursor_y += 100

        moves = data.get("moves", {})
        move_order = [("NORMAL ATTACK", "normal", (150, 150, 255)),
                      ("ELEMENTAL SKILL", "skill", (150, 255, 150)),
                      ("ELEMENTAL BURST", "ult", (255, 150, 150))]

        for title, key, color in move_order:
            if key not in moves: continue

            m_data = moves[key]

            # Title
            layout_items.append(("move_title", (title, color), (0, cursor_y)))
            cursor_y += 40

            # Info Line
            info_txt = f"{m_data.get('name', 'Unknown')} (Dmg: {m_data.get('dmg', 0)})"
            if 'cost' in m_data and m_data['cost']: info_txt += f" [Cost: {m_data['cost']}]"
            layout_items.append(("text", info_txt, (0, cursor_y)))
            cursor_y += 35

            # Description (Wrapped)
            desc_lines = wrap_text(m_data.get('desc', ''), font_s, right_panel_w)
            for line in desc_lines:
                layout_items.append(("desc_text", line, (0, cursor_y)))
                cursor_y += 30

            cursor_y += 50

            # Video
            if key in videos:
                vid_rect = pygame.Rect(0, cursor_y, vid_w, vid_h)
                layout_items.append(("video", key, vid_rect))
                cursor_y += vid_h

            cursor_y += 50

        total_content_height = cursor_y + 100
        viewport_h = h - 40
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
                if event.button == 1:  # ONLY LEFT CLICK
                    if btn_close.check_input(mouse_pos):
                        running = False
                    elif not window_rect.collidepoint(mouse_pos):
                        running = False

                    # Scroll Click Logic
                    base_x = x + img_area_w + 30
                    base_y = y + 20
                    view_rect = pygame.Rect(base_x, base_y, right_panel_w, h - 40)

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
                                    vid_key = content
                                    run_fullscreen_video(screen, v_paths[vid_key])

        # --- DRAWING ---
        screen.fill((20, 20, 20))

        pygame.draw.rect(screen, BG_MODAL, window_rect, border_radius=20)
        pygame.draw.rect(screen, BUTTON_BORDER, window_rect, 4, border_radius=20)

        if full_art_surf:
            screen.blit(full_art_surf, (x, y))
            pygame.draw.rect(screen, BUTTON_BORDER, (x, y, img_area_w, h), 4)

        # SCROLL AREA
        base_x = x + img_area_w + 30
        base_y = y + 20
        view_rect = pygame.Rect(base_x, base_y, right_panel_w, h - 40)

        screen.set_clip(view_rect)

        for item_type, content, pos_data in layout_items:

            if item_type == "video":
                draw_y = base_y + pos_data.y - scroll_y
                draw_rect = pygame.Rect(base_x + pos_data.x, draw_y, pos_data.width, pos_data.height)

                if draw_rect.bottom > 0 and draw_rect.top < screen.get_height():
                    vid_key = content
                    if vid_key in current_frames and current_frames[vid_key]:
                        screen.blit(current_frames[vid_key], draw_rect)
                        pygame.draw.rect(screen, (255, 255, 255), draw_rect, 2)
                    else:
                        pygame.draw.rect(screen, (0, 0, 0), draw_rect)
                        pygame.draw.rect(screen, (50, 50, 50), draw_rect, 2)
                        no_vid = font_s.render("NO VIDEO", True, (100, 100, 100))
                        screen.blit(no_vid, (draw_rect.centerx - no_vid.get_width() // 2, draw_rect.centery))

            else:
                draw_y = base_y + pos_data[1] - scroll_y

                if draw_y > -50 and draw_y < screen.get_height():
                    if item_type == "header":
                        screen.blit(font_h.render(content, True, TITLE_COLOR), (base_x, draw_y))
                    elif item_type == "sub_header":
                        screen.blit(font_b.render(content, True, SUB_COLOR), (base_x, draw_y))
                    elif item_type == "move_title":
                        title, col = content
                        screen.blit(font_b.render(title, True, col), (base_x, draw_y))
                    elif item_type == "text":
                        screen.blit(font_s.render(content, True, TEXT_COLOR), (base_x, draw_y))
                    elif item_type == "desc_text":
                        screen.blit(font_s.render(content, True, TEXT_DESC), (base_x, draw_y))

        screen.set_clip(None)

        btn_close.change_color(mouse_pos)
        btn_close.update(screen)

        pygame.display.update()
        clock.tick(60)

    for v in videos.values():
        v.close()