import pygame
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui_components import Button, InputBox, BG_FALLBACK, BUTTON_BORDER, TEXT_COLOR, get_font, update_animations, spawn_particles, update_juice, draw_juice_overlays, PROFILE_BG, COLOR_ACTIVE, BUTTON_BASE, BUTTON_HOVER
from card_manager import CardManager
from user_manager import UserManager


# -- SCROLLABLE CARD LIST WIDGET --
class CardListWidget:
    def __init__(self, rect, card_list, is_grid=True):
        self.rect = rect
        self.cards = card_list
        self.is_grid = is_grid
        self.scroll_y = 0

        self.thumbnails = {}
        for card in self.cards:
            path = card.get("image_path")
            if path and os.path.exists(path):
                try:
                    raw = pygame.image.load(path).convert_alpha()
                    size = (100, 140) if is_grid else (60, 60)
                    self.thumbnails[card["id"]] = pygame.transform.scale(raw, size)
                except:
                    pass

    def handle_scroll(self, event):
        if self.rect.collidepoint(pygame.mouse.get_pos()):
            content_h = self.get_content_height()
            max_scroll = max(0, content_h - self.rect.height)
            self.scroll_y -= event.y * 30
            self.scroll_y = max(0, min(self.scroll_y, max_scroll))

    def get_content_height(self):
        if self.is_grid:
            cards_per_row = max(1, (self.rect.width - 40) // 120)
            rows = (len(self.cards) + cards_per_row - 1) // cards_per_row
            return rows * 160 + 20
        else:
            return len(self.cards) * 80 + 20

    def get_clicked_card(self, mouse_pos):
        if not self.rect.collidepoint(mouse_pos): return None
        rel_y = mouse_pos[1] - self.rect.y + self.scroll_y
        rel_x = mouse_pos[0] - self.rect.x - 20

        if self.is_grid:
            cards_per_row = max(1, (self.rect.width - 40) // 120)
            col = int(rel_x // 120)
            row = int(rel_y // 160)
            if 0 <= col < cards_per_row:
                idx = row * cards_per_row + col
                if 0 <= idx < len(self.cards):
                    return self.cards[idx]
        else:
            idx = int(rel_y // 80)
            if 0 <= idx < len(self.cards):
                return self.cards[idx]
        return None

    def draw(self, screen):
        # Draw Container Border/Background
        pygame.draw.rect(screen, PROFILE_BG, self.rect, border_radius=15)
        pygame.draw.rect(screen, BUTTON_BORDER, self.rect, 1, border_radius=15)

        screen.set_clip(self.rect)
        start_y = self.rect.y - self.scroll_y
        font = get_font(20)
        
        cards_per_row = max(1, (self.rect.width - 40) // 120) if self.is_grid else 1

        for i, card in enumerate(self.cards):
            if self.is_grid:
                # GRID VIEW (Library)
                row = i // cards_per_row
                col = i % cards_per_row
                x = self.rect.x + (col * 120) + 25
                y = start_y + (row * 160) + 20

                if y + 160 < 0 or y > screen.get_height(): continue

                c_rect = pygame.Rect(x, y, 100, 140)
                thumb = self.thumbnails.get(card["id"])

                if thumb:
                    screen.blit(thumb, c_rect)
                else:
                    pygame.draw.rect(screen, BG_FALLBACK, c_rect)

                pygame.draw.rect(screen, BUTTON_BORDER, c_rect, 1)

                # Name
                name_surf = font.render(card["name"][:12], True, TEXT_COLOR)
                screen.blit(name_surf, (x, y + 142))
            else:
                pass # List view removed/not used

        screen.set_clip(None)


def show_deck_screen(screen, username):
    clock = pygame.time.Clock()
    user_mgr = UserManager()
    card_mgr = CardManager()

    all_cards = card_mgr.get_all_cards()
    library_cards = [c for c in all_cards if c.get("unlocked", True)]

    # Initial Load
    user_decks = user_mgr.get_user_decks(username)
    active_deck_name = user_mgr.get_active_deck_name(username)

    # State
    state = "SELECT"
    current_deck_name = ""
    current_deck_ids = []
    status_msg = ""
    status_timer = 0
    deck_grid_scroll = 0

    # UI Elements (Select Screen)
    btn_back = Button("BACK", 50, 40, 150, 60, font_size=28)

    # UI Elements (Edit Screen)
    btn_save = Button("SAVE DECK", screen.get_width() - 250, 40, 200, 60, font_size=25)
    btn_delete = Button("DELETE", screen.get_width() - 480, 40, 200, 60, font_size=25)

    # Input
    name_input = InputBox(screen.get_width() // 2 - 150, screen.get_height() // 2, 300, 50)
    btn_confirm_name = Button("CONFIRM", screen.get_width() // 2 - 100, screen.get_height() // 2 + 70, 200, 50, font_size=25)

    # Layout Rects
    lib_rect = pygame.Rect(50, 120, screen.get_width() - 100, screen.get_height() - 350)
    hotbar_rect = pygame.Rect(50, screen.get_height() - 200, screen.get_width() - 100, 180)
    
    deck_grid_rect = pygame.Rect(50, 120, screen.get_width() - 100, screen.get_height() - 150)

    library_widget = None

    def refresh_editor_widgets():
        return CardListWidget(lib_rect, library_cards, is_grid=True)

    # Load large thumbs for deck boxes
    # We load standard sizes and then we'll slice them
    deck_thumbnails = {} # {deck_name: [surf, surf, surf]}

    def load_deck_thumbs():
        deck_thumbnails.clear()
        for d_name, d_ids in user_decks.items():
            thumbs = []
            for cid in d_ids[:3]:
                c_data = next((c for c in all_cards if c["id"] == cid), None)
                if c_data:
                     path = c_data.get("image_path")
                     if path and os.path.exists(path):
                         try:
                             raw = pygame.image.load(path).convert_alpha()
                             # Scale to slice size: We want deck box to be 240x300, so slice is 80x200
                             # Actually just load raw, scale height to 200, width auto
                             h = 200
                             w = int((raw.get_width() / raw.get_height()) * h)
                             thumbs.append(pygame.transform.smoothscale(raw, (w, h)))
                         except: pass
            deck_thumbnails[d_name] = thumbs

    load_deck_thumbs()

    # Pre-render Hotbar slot backgrounds for performance
    slot_bg = pygame.Surface((110, 150), pygame.SRCALPHA)
    pygame.draw.rect(slot_bg, (0, 0, 0, 80), slot_bg.get_rect(), border_radius=12)
    pygame.draw.rect(slot_bg, BUTTON_BORDER, slot_bg.get_rect(), 1, border_radius=12)

    while True:
        dt = clock.tick(60) / 1000.0
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()

        if status_timer > 0:
            status_timer -= 1
        else:
            status_msg = ""

        active_deck_name = user_mgr.get_active_deck_name(username)

        for event in events:
            if event.type == pygame.QUIT:
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                spawn_particles(event.pos[0], event.pos[1], count=5, color=(200, 100, 200))

            if state == "NAME_INPUT":
                name_input.handle_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_back.check_input(mouse_pos):
                        state = "SELECT"
                    if btn_confirm_name.check_input(mouse_pos):
                        name = name_input.get_text().strip()
                        if name:
                            current_deck_name = name
                            current_deck_ids = []
                            state = "EDIT"
                            library_widget = refresh_editor_widgets()

            elif state == "SELECT":
                if event.type == pygame.MOUSEWHEEL:
                    content_h = ((len(user_decks) + 1) // 3 + 1) * 340
                    max_scr = max(0, content_h - deck_grid_rect.height)
                    deck_grid_scroll -= event.y * 30
                    deck_grid_scroll = max(0, min(deck_grid_scroll, max_scr))

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_back.check_input(mouse_pos):
                        return "BACK"

                    if deck_grid_rect.collidepoint(mouse_pos):
                        start_draw_y = deck_grid_rect.y - deck_grid_scroll
                        cards_per_row = max(1, (deck_grid_rect.width - 40) // 280)
                        
                        # Build list of decks + "NEW"
                        deck_list = list(user_decks.keys())
                        deck_list.append("NEW_DECK_BTN")
                        
                        for i, d_name in enumerate(deck_list):
                            row = i // cards_per_row
                            col = i % cards_per_row
                            x = deck_grid_rect.x + 20 + (col * 280)
                            y = start_draw_y + 20 + (row * 340)
                            
                            box_rect = pygame.Rect(x, y, 240, 300)
                            
                            if box_rect.collidepoint(mouse_pos):
                                if d_name == "NEW_DECK_BTN":
                                    state = "NAME_INPUT"
                                    name_input.text = ""
                                    name_input.txt_surface = name_input.font.render("", True, name_input.color)
                                else:
                                    # Inside Deck Box, check if they clicked EDIT or EQUIP
                                    edit_rect = pygame.Rect(x + 130, y + 245, 90, 35)
                                    if edit_rect.collidepoint(mouse_pos):
                                        current_deck_name = d_name
                                        current_deck_ids = list(user_decks[d_name])
                                        state = "EDIT"
                                        library_widget = refresh_editor_widgets()
                                    else:
                                        # EQUIP
                                        user_mgr.set_active_deck(username, d_name)
                                        spawn_particles(mouse_pos[0], mouse_pos[1], 15, COLOR_ACTIVE)

            elif state == "EDIT":
                if event.type == pygame.MOUSEWHEEL:
                    library_widget.handle_scroll(event)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_back.check_input(mouse_pos):
                        state = "SELECT"
                        user_decks = user_mgr.get_user_decks(username)
                        load_deck_thumbs()

                    if btn_save.check_input(mouse_pos):
                        user_mgr.save_deck(username, current_deck_name, current_deck_ids)
                        state = "SELECT"
                        user_decks = user_mgr.get_user_decks(username)
                        load_deck_thumbs()

                    if btn_delete.check_input(mouse_pos):
                        user_mgr.delete_deck(username, current_deck_name)
                        state = "SELECT"
                        user_decks = user_mgr.get_user_decks(username)
                        load_deck_thumbs()

                    # 1. Add Card (Library)
                    clicked_lib = library_widget.get_clicked_card(mouse_pos)
                    if clicked_lib:
                        if len(current_deck_ids) >= 3:
                            status_msg = "Deck Full (Max 3 Cards)!"
                            status_timer = 120
                        elif clicked_lib["id"] in current_deck_ids:
                            status_msg = "Card already in deck!"
                            status_timer = 120
                        else:
                            current_deck_ids.append(clicked_lib["id"])

                    # 2. Remove Card (Hotbar)
                    if hotbar_rect.collidepoint(mouse_pos):
                        slot_w, slot_h = 110, 150
                        gap = 40
                        total_w = (slot_w * 3) + (gap * 2)
                        start_x = hotbar_rect.x + (hotbar_rect.width - total_w) // 2
                        start_y = hotbar_rect.y + (hotbar_rect.height - slot_h) // 2
                        
                        for i in range(len(current_deck_ids)):
                            r = pygame.Rect(start_x + (i * (slot_w + gap)), start_y, slot_w, slot_h)
                            if r.collidepoint(mouse_pos):
                                current_deck_ids.pop(i)
                                break


        # --- DRAWING ---
        screen.fill(BG_FALLBACK)

        if state == "SELECT":
            screen.blit(get_font(40).render("MY DECKS", True, TEXT_COLOR), (220, 50))
            
            # Draw Deck Grid
            screen.set_clip(deck_grid_rect)
            start_draw_y = deck_grid_rect.y - deck_grid_scroll
            cards_per_row = max(1, (deck_grid_rect.width - 40) // 280)
            
            deck_list = list(user_decks.keys())
            deck_list.append("NEW_DECK_BTN")
            
            for i, d_name in enumerate(deck_list):
                row = i // cards_per_row
                col = i % cards_per_row
                x = deck_grid_rect.x + 20 + (col * 280)
                y = start_draw_y + 20 + (row * 340)
                
                if y + 300 < deck_grid_rect.y or y > deck_grid_rect.bottom: continue
                
                box_rect = pygame.Rect(x, y, 240, 300)
                is_hover = box_rect.collidepoint(mouse_pos) and deck_grid_rect.collidepoint(mouse_pos)
                
                if d_name == "NEW_DECK_BTN":
                    # Render Create New Button Box
                    bg_col = (55, 35, 55) if is_hover else PROFILE_BG
                    pygame.draw.rect(screen, bg_col, box_rect, border_radius=20)
                    # Dashed border simulation
                    pygame.draw.rect(screen, BUTTON_BORDER, box_rect, 1, border_radius=20)
                    plus = get_font(80).render("+", True, BUTTON_BORDER)
                    screen.blit(plus, (x + 120 - plus.get_width()//2, y + 150 - plus.get_height()//2))
                    txt = get_font(20).render("CREATE NEW", True, BUTTON_BORDER)
                    screen.blit(txt, (x + 120 - txt.get_width()//2, y + 210))
                else:
                    is_active = (d_name == active_deck_name)
                    bg_col = PROFILE_BG
                    
                    pygame.draw.rect(screen, bg_col, box_rect, border_radius=20)
                    
                    # Draw Blended Art
                    art_rect = pygame.Rect(x, y, 240, 200)
                    screen.set_clip(art_rect.clip(deck_grid_rect))
                    thumbs = deck_thumbnails.get(d_name, [])
                    if thumbs:
                        slice_w = 240 // max(1, len(thumbs))
                        for idx, img in enumerate(thumbs):
                            sx = x + (idx * slice_w)
                            # Center image horizontally in its slice
                            ix = sx + (slice_w - img.get_width()) // 2
                            iy = y + (200 - img.get_height()) // 2
                            screen.blit(img, (ix, iy))
                    else:
                        pygame.draw.rect(screen, (30, 20, 30), art_rect)
                        
                    screen.set_clip(deck_grid_rect)
                    
                    # Dark Gradient at bottom of art to blend into card body
                    fade = pygame.Surface((240, 50), pygame.SRCALPHA)
                    for i in range(50):
                        alpha = int(255 * (i/49))
                        pygame.draw.line(fade, (*PROFILE_BG, alpha), (0, i), (240, i))
                    screen.blit(fade, (x, y + 150))
                    
                    # Text Data
                    n_surf = get_font(28).render(d_name, True, TEXT_COLOR)
                    screen.blit(n_surf, (x + 20, y + 215))
                    
                    c_surf = get_font(18).render(f"{len(user_decks[d_name])} / 3 Cards", True, (200, 180, 200))
                    screen.blit(c_surf, (x + 20, y + 260))
                    
                    # Buttons & Borders
                    edit_rect = pygame.Rect(x + 140, y + 250, 80, 32)
                    edit_hover = edit_rect.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, BUTTON_HOVER if edit_hover else PROFILE_BG, edit_rect, border_radius=12)
                    pygame.draw.rect(screen, BUTTON_BORDER, edit_rect, 1, border_radius=12)
                    e_txt = get_font(16).render("EDIT", True, TEXT_COLOR)
                    screen.blit(e_txt, (edit_rect.centerx - e_txt.get_width()//2, edit_rect.centery - e_txt.get_height()//2))
                    
                    if is_active:
                        pygame.draw.rect(screen, COLOR_ACTIVE, box_rect, 2, border_radius=20)
                        
                        eq = get_font(18).render("EQUIPPED", True, COLOR_ACTIVE)
                        eq_rect = eq.get_rect(topright=(x + 240 - 15, y + 15))
                        
                        pill = eq_rect.inflate(16, 10)
                        p_surf = pygame.Surface((pill.width, pill.height), pygame.SRCALPHA)
                        pygame.draw.rect(p_surf, (0, 0, 0, 180), p_surf.get_rect(), border_radius=12)
                        screen.blit(p_surf, pill.topleft)
                        screen.blit(eq, eq_rect)
                    else:
                        pygame.draw.rect(screen, BUTTON_BORDER, box_rect, 1 if not is_hover else 2, border_radius=20)

            screen.set_clip(None)

        elif state == "NAME_INPUT":
            title = get_font(50).render("NAME YOUR DECK", True, TEXT_COLOR)
            screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 300))

            name_input.update()
            name_input.draw(screen)

            btn_confirm_name.change_color(mouse_pos)
            btn_confirm_name.update(screen)

        elif state == "EDIT":
            # Header
            head = get_font(40).render(f"EDITING: {current_deck_name}", True, TEXT_COLOR)
            screen.blit(head, (250, 40))

            # Draw Library
            library_widget.draw(screen)

            # Draw Hotbar Base
            pygame.draw.rect(screen, PROFILE_BG, hotbar_rect, border_radius=20)
            pygame.draw.rect(screen, BUTTON_BORDER, hotbar_rect, 1, border_radius=20)
            
            # Hotbar Info
            hb_title = get_font(25).render("CURRENT DECK", True, TEXT_COLOR)
            screen.blit(hb_title, (hotbar_rect.x + 30, hotbar_rect.y + 20))
            
            cnt_col = COLOR_ACTIVE if len(current_deck_ids) == 3 else (200, 200, 200)
            cnt = get_font(20).render(f"{len(current_deck_ids)}/3 CARDS", True, cnt_col)
            screen.blit(cnt, (hotbar_rect.x + 30, hotbar_rect.y + 55))

            # Draw Slots
            slot_w, slot_h = 110, 150
            gap = 40
            total_w = (slot_w * 3) + (gap * 2)
            start_x = hotbar_rect.x + (hotbar_rect.width - total_w) // 2
            start_y = hotbar_rect.y + (hotbar_rect.height - slot_h) // 2

            for i in range(3):
                sx = start_x + (i * (slot_w + gap))
                sy = start_y + 15
                screen.blit(slot_bg, (sx, sy))
                
                if i < len(current_deck_ids):
                    cid = current_deck_ids[i]
                    c_data = next((c for c in all_cards if c["id"] == cid), None)
                    if c_data and "image_path" in c_data and os.path.exists(c_data["image_path"]):
                        try:
                            raw = pygame.image.load(c_data["image_path"]).convert_alpha()
                            scaled = pygame.transform.smoothscale(raw, (slot_w, slot_h))
                            screen.blit(scaled, (sx, sy))
                            pygame.draw.rect(screen, BUTTON_BORDER, (sx, sy, slot_w, slot_h), 1, border_radius=12)
                        except: pass

            # Error Message
            if status_msg:
                err = get_font(30).render(status_msg, True, COLOR_ACTIVE)
                screen.blit(err, (screen.get_width() // 2 - err.get_width() // 2, hotbar_rect.y - 40))

            btn_save.change_color(mouse_pos)
            btn_save.update(screen)

            btn_delete.change_color(mouse_pos)
            btn_delete.update(screen)

        btn_back.change_color(mouse_pos)
        btn_back.update(screen)

        update_animations(dt)
        update_juice(dt)
        draw_juice_overlays(screen)
        pygame.display.update()