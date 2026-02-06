import random
import pygame
import json
import os
from ui_components import get_font

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

    def draw(self, screen, mouse_pos):
        # 1. Check Hover Logic
        is_hovered = self.rect.collidepoint(mouse_pos)
        self.target_scale = 1.15 if is_hovered else 1.0

        # Smooth Interpolation (Lerp)
        self.hover_scale += (self.target_scale - self.hover_scale) * 0.2

        # 2. Draw Content to a Temporary Surface (at 1x scale)
        # We add padding to the surface so shadows/glows don't get cut off
        surf_w, surf_h = HAND_BUFF_W, HAND_BUFF_H
        temp_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

        # Glow if selected
        if self.selected:
            pygame.draw.rect(temp_surf, (255, 255, 100), (0, 0, surf_w, surf_h), border_radius=10)
            inner_rect = pygame.Rect(2, 2, surf_w - 4, surf_h - 4)
        else:
            inner_rect = pygame.Rect(0, 0, surf_w, surf_h)

        # Card Background & Image
        pygame.draw.rect(temp_surf, (30, 30, 40), inner_rect, border_radius=8)

        if self.image_surf:
            img_rect = self.image_surf.get_rect(center=(surf_w // 2, surf_h // 2 + 5))
            temp_surf.blit(self.image_surf, img_rect)

        # Header (Type Color)
        border_col = self.data.get("color", (100, 100, 100))
        header_rect = pygame.Rect(inner_rect.x, inner_rect.y, inner_rect.width, 30)
        pygame.draw.rect(temp_surf, border_col, header_rect, border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.rect(temp_surf, border_col, inner_rect, 2, border_radius=8)

        # Name Text
        font_nm = get_font(18)
        nm_surf = font_nm.render(self.data["name"], True, (255, 255, 255))
        temp_surf.blit(nm_surf, (surf_w // 2 - nm_surf.get_width() // 2, 4))

        # Value/Type indicator at bottom
        val_txt = f"{self.data['type']} {self.data['val']}"
        v_surf = get_font(16).render(val_txt, True, border_col)
        temp_surf.blit(v_surf, (surf_w // 2 - v_surf.get_width() // 2, surf_h - 22))

        # 3. Scale and Blit to Screen
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

        needed = 5 - len(current_hand_list)
        if needed <= 0: return current_hand_list

        new_hand = list(current_hand_list)
        type_counts = {}

        # Count types in existing hand
        for card in new_hand:
            t = card.data["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        attempts = 0
        while len(new_hand) < 5 and attempts < 100:
            attempts += 1
            candidate_data = random.choice(self.buff_db)
            c_type = candidate_data["type"]

            # Rule: Max 2 of same type
            if type_counts.get(c_type, 0) >= 2: continue

            new_hand.append(BuffCardUI(candidate_data, 0, 0))
            type_counts[c_type] = type_counts.get(c_type, 0) + 1

        # Layout
        for i, card in enumerate(new_hand):
            card.rect.x = x_start + (i * (HAND_BUFF_W + 10))
            card.rect.y = y_pos

        return new_hand