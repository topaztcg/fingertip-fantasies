import pygame
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui_components import Button, InputBox, BG_FALLBACK, BUTTON_BORDER, TEXT_COLOR, get_font, update_animations, spawn_particles, update_juice, draw_juice_overlays
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
            self.scroll_y -= event.y * 20
            self.scroll_y = max(0, min(self.scroll_y, max_scroll))

    def get_content_height(self):
        if self.is_grid:
            rows = (len(self.cards) + 2) // 3
            return rows * 160 + 20
        else:
            return len(self.cards) * 80 + 20

    def get_clicked_card(self, mouse_pos):
        if not self.rect.collidepoint(mouse_pos): return None

        rel_y = mouse_pos[1] - self.rect.y + self.scroll_y
        rel_x = mouse_pos[0] - self.rect.x

        if self.is_grid:
            col = int(rel_x // 110)
            row = int(rel_y // 160)
            idx = row * 3 + col
            if 0 <= idx < len(self.cards):
                return self.cards[idx]
        else:
            idx = int(rel_y // 80)
            if 0 <= idx < len(self.cards):
                return self.cards[idx]
        return None

    def draw(self, screen):
        # Draw Container Border/Background
        pygame.draw.rect(screen, (30, 20, 40), self.rect, border_radius=10)
        pygame.draw.rect(screen, BUTTON_BORDER, self.rect, 2, border_radius=10)

        screen.set_clip(self.rect)

        start_y = self.rect.y - self.scroll_y
        font = get_font(20)

        for i, card in enumerate(self.cards):
            if self.is_grid:
                # GRID VIEW (Library)
                row = i // 3
                col = i % 3
                x = self.rect.x + (col * 110) + 20  # Extra padding
                y = start_y + (row * 160) + 20

                if y + 160 < 0 or y > screen.get_height(): continue

                c_rect = pygame.Rect(x, y, 100, 140)
                thumb = self.thumbnails.get(card["id"])

                if thumb:
                    screen.blit(thumb, c_rect)
                else:
                    pygame.draw.rect(screen, (50, 50, 50), c_rect)

                pygame.draw.rect(screen, BUTTON_BORDER, c_rect, 2)

                # Name
                name_surf = font.render(card["name"][:12], True, TEXT_COLOR)
                screen.blit(name_surf, (x, y + 142))

            else:
                # LIST VIEW (Deck)
                x = self.rect.x + 10
                y = start_y + (i * 80) + 10  # Increased gap

                if y + 80 < 0 or y > screen.get_height(): continue

                row_rect = pygame.Rect(x, y, self.rect.width - 20, 70)
                pygame.draw.rect(screen, (60, 30, 80), row_rect, border_radius=10)

                thumb = self.thumbnails.get(card["id"])
                if thumb:
                    screen.blit(thumb, (x + 5, y + 5))

                # Name
                name_surf = get_font(25).render(card["name"], True, TEXT_COLOR)
                screen.blit(name_surf, (x + 80, y + 10))

                # Remove Hint
                rem_surf = get_font(18).render("(Click to remove)", True, (200, 150, 150))
                screen.blit(rem_surf, (x + 80, y + 40))

        screen.set_clip(None)

        # Redraw border on top to hide clipped elements
        pygame.draw.rect(screen, BUTTON_BORDER, self.rect, 3, border_radius=10)


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

    # UI Elements (Select Screen)
    btn_back = Button("BACK", 50, 50, 150, 50, font_size=30)
    btn_new_deck = Button("CREATE NEW DECK", 50, 180, 300, 60, font_size=25)

    # UI Elements (Edit Screen)
    btn_save = Button("SAVE DECK", screen.get_width() - 250, 50, 200, 50, font_size=25)
    btn_delete = Button("DELETE", screen.get_width() - 500, 50, 200, 50, font_size=25)

    # Input
    name_input = InputBox(screen.get_width() // 2 - 150, screen.get_height() // 2, 300, 50)
    btn_confirm_name = Button("CONFIRM", screen.get_width() // 2 - 100, screen.get_height() // 2 + 70, 200, 50,
                              font_size=25)

    # Deck Scroll Area (Select Screen)
    # Give it more horizontal space to avoid overlap with left panel
    deck_list_rect = pygame.Rect(450, 150, screen.get_width() - 500, screen.get_height() - 200)
    deck_list_scroll = 0

    # Widgets
    library_widget = None
    deck_widget = None

    def refresh_editor_widgets(current_ids):
        # Push Y down to 200 to give text space
        lib_rect = pygame.Rect(50, 200, 400, screen.get_height() - 250)
        deck_rect = pygame.Rect(500, 200, 400, screen.get_height() - 250)

        deck_cards_obj = []
        for cid in current_ids:
            found = next((c for c in all_cards if c["id"] == cid), None)
            if found: deck_cards_obj.append(found)

        return CardListWidget(lib_rect, library_cards, is_grid=True), \
            CardListWidget(deck_rect, deck_cards_obj, is_grid=False)

    # Load thumbnails for deck preview
    deck_thumbnails = {} # {deck_name: [surf, surf, surf]}

    def load_deck_thumbs():
        deck_thumbnails.clear()
        for d_name, d_ids in user_decks.items():
            thumbs = []
            for cid in d_ids[:3]: # Take up to 3
                c_data = next((c for c in all_cards if c["id"] == cid), None)
                if c_data:
                     path = c_data.get("image_path")
                     if path and os.path.exists(path):
                         try:
                             raw = pygame.image.load(path).convert_alpha()
                             thumbs.append(pygame.transform.smoothscale(raw, (60, 84)))
                         except: pass
            deck_thumbnails[d_name] = thumbs

    load_deck_thumbs()

    while True:
        dt = clock.tick(60) / 1000.0
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()

        # Status Message Timer
        if status_timer > 0:
            status_timer -= 1
        else:
            status_msg = ""

        # Update Active Deck (in case logic changes it)
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
                            library_widget, deck_widget = refresh_editor_widgets(current_deck_ids)

            elif state == "SELECT":
                if event.type == pygame.MOUSEWHEEL:
                    # Scroll deck list
                    content_h = len(user_decks) * 160 # Taller items now
                    max_scr = max(0, content_h - deck_list_rect.height)
                    deck_list_scroll -= event.y * 20
                    deck_list_scroll = max(0, min(deck_list_scroll, max_scr))

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_back.check_input(mouse_pos):
                        return "BACK"

                    if btn_new_deck.check_input(mouse_pos):
                        state = "NAME_INPUT"
                        name_input.text = ""
                        name_input.txt_surface = name_input.font.render("", True, name_input.color)

                    # Check clicks in Deck List
                    if deck_list_rect.collidepoint(mouse_pos):
                        start_draw_y = deck_list_rect.y - deck_list_scroll
                        for d_name in user_decks.keys():
                            # Item Area
                            r = pygame.Rect(deck_list_rect.x + 10, start_draw_y, deck_list_rect.width - 40, 140)
                            
                            # Equip Button Area (Inside Item)
                            equip_btn_rect = pygame.Rect(r.right - 130, r.centery - 20, 110, 40)
                            
                            if r.collidepoint(mouse_pos):
                                if equip_btn_rect.collidepoint(mouse_pos):
                                    # EQUIP ACTION
                                    user_mgr.set_active_deck(username, d_name)
                                    spawn_particles(mouse_pos[0], mouse_pos[1], 15, (50, 255, 50))
                                else:
                                    # EDIT ACTION
                                    current_deck_name = d_name
                                    current_deck_ids = list(user_decks[d_name])
                                    state = "EDIT"
                                    library_widget, deck_widget = refresh_editor_widgets(current_deck_ids)
                            
                            start_draw_y += 160

            elif state == "EDIT":
                if event.type == pygame.MOUSEWHEEL:
                    library_widget.handle_scroll(event)
                    deck_widget.handle_scroll(event)

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

                    # 1. Add Card (With Limits)
                    clicked_lib = library_widget.get_clicked_card(mouse_pos)
                    if clicked_lib:
                        if len(current_deck_ids) >= 3:
                            status_msg = "Deck Full (Max 3 Cards)!"
                            status_timer = 120  # 2 seconds
                        elif clicked_lib["id"] in current_deck_ids:
                            status_msg = "Card already in deck!"
                            status_timer = 120
                        else:
                            current_deck_ids.append(clicked_lib["id"])
                            library_widget, deck_widget = refresh_editor_widgets(current_deck_ids)

                    # 2. Remove Card
                    clicked_deck = deck_widget.get_clicked_card(mouse_pos)
                    if clicked_deck:
                        current_deck_ids.remove(clicked_deck["id"])
                        library_widget, deck_widget = refresh_editor_widgets(current_deck_ids)

        # --- DRAWING ---
        screen.fill(BG_FALLBACK)

        if state == "SELECT":
            # Left Side
            screen.blit(get_font(40).render("DECK SELECTION", True, TEXT_COLOR), (50, 130)) # Pushed down
            
            btn_new_deck = Button("CREATE NEW DECK", 50, 190, 300, 60, font_size=25)
            btn_new_deck.change_color(mouse_pos)
            btn_new_deck.update(screen)
            
            # Info Panel (Slightly narrower and pushed down)
            info_rect = pygame.Rect(50, 270, 350, 300)
            pygame.draw.rect(screen, (30, 20, 50), info_rect, border_radius=15)
            pygame.draw.rect(screen, BUTTON_BORDER, info_rect, 2, border_radius=15)
            
            txt1 = get_font(25).render("Active Deck:", True, (200, 200, 200))
            screen.blit(txt1, (70, 280))
            
            act_col = (100, 255, 100) if active_deck_name else (150, 150, 150)
            txt2 = get_font(35).render(active_deck_name or "None", True, act_col)
            screen.blit(txt2, (70, 320))
            
            txt3 = get_font(20).render("Select a deck to Edit", True, (150, 150, 150))
            screen.blit(txt3, (70, 510))
            txt4 = get_font(20).render("Click 'EQUIP' to use", True, (150, 150, 150))
            screen.blit(txt4, (70, 540))

            # Right Side: Deck List
            pygame.draw.rect(screen, (20, 10, 30), deck_list_rect, border_radius=20)
            pygame.draw.rect(screen, BUTTON_BORDER, deck_list_rect, 3, border_radius=20)

            screen.set_clip(deck_list_rect)
            draw_y = deck_list_rect.y - deck_list_scroll

            if not user_decks:
                empty = get_font(30).render("No Decks Found", True, (150, 150, 150))
                screen.blit(empty, (deck_list_rect.centerx - empty.get_width() // 2, deck_list_rect.centery))

            for d_name, d_cards in user_decks.items():
                r = pygame.Rect(deck_list_rect.x + 20, draw_y, deck_list_rect.width - 40, 140)
                
                # Highlight Active Deck
                is_active = (d_name == active_deck_name)
                
                is_hover = r.collidepoint(mouse_pos) and deck_list_rect.collidepoint(mouse_pos)
                col = (60, 80, 60) if is_active else ((80, 40, 100) if is_hover else (50, 30, 60))
                
                pygame.draw.rect(screen, col, r, border_radius=15)
                border_col = (100, 255, 100) if is_active else BUTTON_BORDER
                pygame.draw.rect(screen, border_col, r, 2 if not is_active else 4, border_radius=15)

                # Thumbnails
                thumbs = deck_thumbnails.get(d_name, [])
                tx = r.x + 20
                for img in thumbs:
                    screen.blit(img, (tx, r.y + 28)) # Centered roughly vertically
                    pygame.draw.rect(screen, (0, 0, 0), (tx, r.y + 28, 60, 84), 1)
                    tx += 50 # Overlap slightly
                
                # Text Info
                text_x = r.x + 180
                t1 = get_font(35).render(d_name, True, TEXT_COLOR)
                screen.blit(t1, (text_x, r.y + 20))
                
                t2 = get_font(25).render(f"{len(d_cards)} Cards", True, (200, 200, 200))
                screen.blit(t2, (text_x, r.y + 60))
                
                if is_active:
                    t3 = get_font(25).render("EQUIPPED", True, (100, 255, 100))
                    screen.blit(t3, (text_x, r.y + 90))
                
                # Equip Button (Only show if not active)
                if not is_active:
                    btn_rect = pygame.Rect(r.right - 130, r.centery - 20, 110, 40)
                    btn_hover = btn_rect.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (100, 200, 100) if btn_hover else (50, 100, 50), btn_rect, border_radius=8)
                    pygame.draw.rect(screen, (255, 255, 255), btn_rect, 2, border_radius=8)
                    
                    bt = get_font(20).render("EQUIP", True, (255, 255, 255))
                    screen.blit(bt, (btn_rect.centerx - bt.get_width()//2, btn_rect.centery - bt.get_height()//2))

                draw_y += 160

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

            # Library Label
            screen.blit(get_font(35).render("LIBRARY", True, TEXT_COLOR), (50, 150))

            # Deck Label & Count
            screen.blit(get_font(35).render("CURRENT DECK", True, TEXT_COLOR), (500, 150))

            cnt_col = (100, 255, 100) if len(current_deck_ids) == 3 else (255, 255, 255)
            cnt = get_font(30).render(f"Count: {len(current_deck_ids)}/3", True, cnt_col)
            # Position count to the right of "CURRENT DECK" with gap
            screen.blit(cnt, (780, 155))

            library_widget.draw(screen)
            deck_widget.draw(screen)

            # Error Message
            if status_msg:
                err = get_font(30).render(status_msg, True, (255, 100, 100))
                # Center bottom
                screen.blit(err, (screen.get_width() // 2 - err.get_width() // 2, screen.get_height() - 100))

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