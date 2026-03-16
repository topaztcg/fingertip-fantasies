import random
import pygame
import json
import os
import pytweening
from ui_components import get_font, AnimationManager, Tween

# Standard size for buffs in hand
HAND_BUFF_W, HAND_BUFF_H = 120, 160


class BuffCardUI:
    def __init__(self, data, x, y):
        self.data = data
        self.id = data["id"]
        # Logical Hitbox (stays static for consistent mouse detection)
        self.rect = pygame.Rect(x, y, HAND_BUFF_W, HAND_BUFF_H)

        self.selected = False
        self.image_surf = None

        # Animation State
        self.hover_scale = 1.0
        self.target_scale = 1.0

        # Load and scale image
        img_path = data.get("image_path", "")
        if img_path and os.path.exists(img_path):
            try:
                raw = pygame.image.load(img_path).convert_alpha()
                # Scale to fit nicely inside the card border
                self.image_surf = pygame.transform.scale(raw, (HAND_BUFF_W - 10, HAND_BUFF_H - 40))
            except:
                pass
        
        # ENTRY ANIMATION using Tween
        target_y = y
        self.rect.y = y + 150 # Start lower
        AnimationManager.get().start_tween(self.rect, "y", target_y, 0.6, pytweening.easeOutBack)

    def draw(self, screen, mouse_pos):
        # 1. Hover Logic
        is_hovered = self.rect.collidepoint(mouse_pos)
        self.target_scale = 1.15 if is_hovered else 1.0
        # Smooth Interpolation (Lerp)
        self.hover_scale += (self.target_scale - self.hover_scale) * 0.2

        # 2. Setup Surface
        surf_w, surf_h = HAND_BUFF_W, HAND_BUFF_H
        temp_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        
        # Consistent Card Base Rect (with padding for glow/shadow)
        padding = 4
        card_rect = pygame.Rect(padding, padding, surf_w - (padding*2), surf_h - (padding*2))
        
        # 3. Dynamic Styles
        # Dark semi-transparent background
        base_col = (30, 25, 35, 230)
        border_col = self.data.get("color", (100, 100, 100))
        
        if self.selected:
            border_col = (255, 255, 150) # Bright selection color
            # Outer Glow
            glow_rect = card_rect.inflate(6, 6)
            pygame.draw.rect(temp_surf, (255, 255, 100, 80), glow_rect, border_radius=12)
        elif is_hovered:
            # Highlight border on hover
            border_col = tuple(min(255, c + 50) for c in border_col)

        # 4. Draw Card Body
        pygame.draw.rect(temp_surf, base_col, card_rect, border_radius=12)
        
        # 5. Draw Image
        if self.image_surf:
            img_rect = self.image_surf.get_rect(center=(surf_w // 2, surf_h // 2 + 5))
            temp_surf.blit(self.image_surf, img_rect)

        # 6. Header (Glassy Top)
        header_h = 28
        header_rect = pygame.Rect(card_rect.x, card_rect.y, card_rect.width, header_h)
        
        # Header Background (Semi-transparent with rounded top corners)
        head_s = pygame.Surface((header_rect.width, header_rect.height), pygame.SRCALPHA)
        head_col = (*border_col[:3], 180) # Add alpha
        pygame.draw.rect(head_s, head_col, head_s.get_rect(), border_top_left_radius=12, border_top_right_radius=12)
        temp_surf.blit(head_s, header_rect)

        # 7. Border Overlay
        pygame.draw.rect(temp_surf, border_col, card_rect, 2, border_radius=12)

        # 8. Text Helper
        def draw_text_shadow(txt, font, col, center_pos):
            shad = font.render(txt, True, (0,0,0, 180))
            face = font.render(txt, True, col)
            temp_surf.blit(shad, (center_pos[0] - shad.get_width()//2 + 1, center_pos[1] - shad.get_height()//2 + 1))
            temp_surf.blit(face, (center_pos[0] - face.get_width()//2, center_pos[1] - face.get_height()//2))

        # Title
        font_nm = get_font(16)
        draw_text_shadow(self.data["name"], font_nm, (255, 255, 255), (surf_w//2, card_rect.y + 14))

        # Footer Value/Type
        val_txt = f"{self.data['type']} {self.data['val']}"
        v_font = get_font(14)
        draw_text_shadow(val_txt, v_font, border_col, (surf_w//2, card_rect.bottom - 12))

        # 9. Final Blit with Scale
        if abs(self.hover_scale - 1.0) > 0.01:
            scaled_w = int(surf_w * self.hover_scale)
            scaled_h = int(surf_h * self.hover_scale)
            scaled_surf = pygame.transform.smoothscale(temp_surf, (scaled_w, scaled_h))
            
            # Center the scaled surface on the original rect
            draw_rect = scaled_surf.get_rect(center=self.rect.center)
            screen.blit(scaled_surf, draw_rect)
        else:
            screen.blit(temp_surf, self.rect)

    def check_click(self, pos):
        return self.rect.collidepoint(pos)


class BuffManager:
    def __init__(self):
        self.buff_db = []
        self.load_buffs()

        if not self.buff_db:
            print("Notice: No buffs loaded (buffs.json missing or empty).")

    def load_buffs(self):
        path = "assets/buffs.json"
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    self.buff_db = json.load(f)
            except:
                pass

    def fill_hand(self, current_hand_list, x_start, y_pos):
        if not self.buff_db:
            return current_hand_list

        needed = 4 - len(current_hand_list)
        if needed <= 0: return current_hand_list

        new_hand = list(current_hand_list)
        type_counts = {}

        # Count types in existing hand
        for card in new_hand:
            t = card.data["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        attempts = 0
        while len(new_hand) < 4 and attempts < 100:
            attempts += 1
            candidate_data = random.choice(self.buff_db)
            c_type = candidate_data["type"]

            # Rule: Max 2 of same type removed for total randomness
            new_hand.append(BuffCardUI(candidate_data, 0, y_pos))
            type_counts[c_type] = type_counts.get(c_type, 0) + 1

        # Layout
        for i, card in enumerate(new_hand):
            card.rect.x = x_start + (i * (HAND_BUFF_W + 10))
            card.rect.y = y_pos

        return new_hand