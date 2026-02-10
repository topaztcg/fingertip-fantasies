import pygame
import os

pygame.font.init()

# --- THE SOFT GIRL PALETTE (UPDATED) ---
BG_FALLBACK = (45, 25, 50)
BUTTON_BASE = (255, 160, 200)   # Hot Pastel Pink
BUTTON_HOVER = (255, 200, 230)  # Light Pink
BUTTON_BORDER = (255, 240, 250) # Near White Pink
TEXT_COLOR = (255, 245, 255)    # Soft White with Pink tint
INPUT_BG = (255, 250, 255)
COLOR_ACTIVE = (255, 105, 180)  # Hot Pink
COLOR_PASSIVE = (200, 150, 200) # Soft Lilac
PROFILE_BG = (70, 40, 80)       # Keep dark for contrast
TEXT_SHADOW = (100, 40, 80)     # Deep Plum for text shadows

UI_PATH = "assets/ui"
FONT_NAME = "Cvcielo-Regular.ttf"

assets = {
    "panel": None,
    "btn": None,
    "btn_hover": None
}
panel_patch = None


def load_ui_image(filename):
    if pygame.display.get_surface() is None:
        return None
    path = os.path.join(UI_PATH, filename)
    if os.path.exists(path):
        try:
            return pygame.image.load(path).convert_alpha()
        except:
            return None
    return None


def init_ui():
    global panel_patch
    assets["panel"] = load_ui_image("panel.png")
    assets["btn"] = load_ui_image("button.png")
    assets["btn_hover"] = load_ui_image("button_hover.png")

    if assets["panel"]:
        panel_patch = NinePatch(assets["panel"])


FONT_CACHE = {}

def get_font(size):
    global FONT_CACHE
    if size in FONT_CACHE:
        return FONT_CACHE[size]

    font_path = os.path.join(UI_PATH, FONT_NAME)
    if os.path.exists(font_path):
        try:
            font = pygame.font.Font(font_path, size)
            FONT_CACHE[size] = font
            return font
        except:
            pass
    
    font_name = pygame.font.match_font('segoeprint')
    if not font_name: font_name = pygame.font.match_font('arial')
    try:
        font = pygame.font.Font(font_name, size)
        FONT_CACHE[size] = font
        return font
    except:
        return pygame.font.Font(None, size)


class NinePatch:
    def __init__(self, image, corner_size=12):
        self.source = image
        self.w, self.h = image.get_size()
        self.c = corner_size
        self.valid = False
        if self.w < (2 * self.c) or self.h < (2 * self.c):
            self.valid = False
            return
        try:
            self.tl = image.subsurface((0, 0, self.c, self.c))
            self.tm = image.subsurface((self.c, 0, self.w - 2 * self.c, self.c))
            self.tr = image.subsurface((self.w - self.c, 0, self.c, self.c))
            self.ml = image.subsurface((0, self.c, self.c, self.h - 2 * self.c))
            self.mm = image.subsurface((self.c, self.c, self.w - 2 * self.c, self.h - 2 * self.c))
            self.mr = image.subsurface((self.w - self.c, self.c, self.c, self.h - 2 * self.c))
            self.bl = image.subsurface((0, self.h - self.c, self.c, self.c))
            self.bm = image.subsurface((self.c, self.h - self.c, self.w - 2 * self.c, self.c))
            self.br = image.subsurface((self.w - self.c, self.h - self.c, self.c, self.c))
            self.valid = True
        except:
            self.valid = False

    def draw(self, surf, rect):
        if not self.valid:
            return
        x, y, w, h = rect
        # Draw corners
        surf.blit(self.tl, (x, y))
        surf.blit(self.tr, (x + w - self.c, y))
        surf.blit(self.bl, (x, y + h - self.c))
        surf.blit(self.br, (x + w - self.c, y + h - self.c))
        
        # Draw edges
        # Top
        top_w = w - 2 * self.c
        if top_w > 0:
            surf.blit(pygame.transform.scale(self.tm, (top_w, self.c)), (x + self.c, y))
            # Bottom
            surf.blit(pygame.transform.scale(self.bm, (top_w, self.c)), (x + self.c, y + h - self.c))
        
        # Sides
        side_h = h - 2 * self.c
        if side_h > 0:
            surf.blit(pygame.transform.scale(self.ml, (self.c, side_h)), (x, y + self.c))
            surf.blit(pygame.transform.scale(self.mr, (self.c, side_h)), (x + w - self.c, y + self.c))
        
        # Middle
        if top_w > 0 and side_h > 0:
            surf.blit(pygame.transform.scale(self.mm, (top_w, side_h)), (x + self.c, y + self.c))

def draw_panel(surf, x, y, w, h):
    r = pygame.Rect(x, y, w, h)
    if panel_patch and panel_patch.valid:
        panel_patch.draw(surf, (x, y, w, h))
    else:
        # Fallback
        pygame.draw.rect(surf, (40, 20, 60), r)
        pygame.draw.rect(surf, (100, 50, 100), r, 3)




class FadeLayer:
    def __init__(self, w, h, speed=10):
        self.surf = pygame.Surface((w, h))
        self.surf.fill((0, 0, 0))
        self.alpha = 255
        self.speed = speed
        self.state = "FADE_IN"
        self.finished = False

    def fade_out(self):
        self.state = "FADE_OUT";
        self.finished = False

    def update(self):
        if self.state == "FADE_IN":
            if self.alpha > 0:
                self.alpha -= self.speed
            else:
                self.alpha = 0; self.finished = True
        elif self.state == "FADE_OUT":
            if self.alpha < 255:
                self.alpha += self.speed
            else:
                self.alpha = 255; self.finished = True
        self.surf.set_alpha(self.alpha)

    def draw(self, screen):
        if self.alpha > 0: screen.blit(self.surf, (0, 0))


# --- BUTTON CLASS (UPDATED FOR DYNAMIC TEXT) ---
class Button:
    def __init__(self, text, x, y, width, height, font_size=35):
        self.text = text
        self.text_input = text
        self.rect = pygame.Rect(x, y, width, height)
        self.base_font_size = font_size
        self.cur_col = BUTTON_BASE
        self.tgt_col = BUTTON_BASE
        self.hovered = False

        # Calculate fitting font immediately
        self.font = self.recalculate_font()

    def recalculate_font(self):
        """Reduces font size until text fits inside the button width."""
        current_size = self.base_font_size
        padding = 30  # Pixel buffer on sides

        while current_size > 10:  # Don't go smaller than 10px
            temp_font = get_font(current_size)
            w, h = temp_font.size(self.text)
            if w < (self.rect.width - padding):
                return temp_font
            current_size -= 2  # Shrink and retry

        return get_font(10)  # Minimal fallback

    def check_input(self, pos):
        return self.rect.collidepoint(pos)

    def change_color(self, pos):
        if self.rect.collidepoint(pos):
            self.tgt_col = BUTTON_HOVER;
            self.hovered = True
        else:
            self.tgt_col = BUTTON_BASE;
            self.hovered = False

    def set_text(self, t):
        self.text = t;
        self.text_input = t
        self.font = self.recalculate_font()  # Recalculate if text changes

    def update(self, screen):
        if assets["btn"] and assets["btn_hover"]:
            img = assets["btn_hover"] if self.hovered else assets["btn"]
            scaled = pygame.transform.scale(img, (self.rect.width, self.rect.height))
            screen.blit(scaled, self.rect)
        else:
            if self.cur_col != self.tgt_col:
                self.cur_col = lerp_color(self.cur_col, self.tgt_col, 0.2)
            pygame.draw.rect(screen, self.cur_col, self.rect, border_radius=15)
            pygame.draw.rect(screen, BUTTON_BORDER, self.rect, 3, border_radius=15)

        shadow = self.font.render(self.text, True, (80, 40, 80))
        txt = self.font.render(self.text, True, TEXT_COLOR)
        shadow_rect = shadow.get_rect(center=(self.rect.centerx + 2, self.rect.centery + 2))
        txt_rect = txt.get_rect(center=self.rect.center)
        screen.blit(shadow, shadow_rect)
        screen.blit(txt, txt_rect)


class InputBox:
    def __init__(self, x, y, w, h, text='', is_password=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = COLOR_PASSIVE
        self.text = text
        self.font = get_font(32)
        self.txt_surface = self.font.render(text, True, self.color)
        self.active = False
        self.is_password = is_password

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = COLOR_ACTIVE if self.active else COLOR_PASSIVE

        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    return self.text
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    if len(self.text) < 15: self.text += event.unicode
                display_text = "*" * len(self.text) if self.is_password else self.text
                self.txt_surface = self.font.render(display_text, True, COLOR_PASSIVE)
        return None

    def update(self):
        width = max(200, self.txt_surface.get_width() + 10)
        self.rect.w = width

    def draw(self, screen):
        if panel_patch:
            panel_patch.draw(screen, self.rect)
        else:
            pygame.draw.rect(screen, INPUT_BG, self.rect, border_radius=10)
        pygame.draw.rect(screen, self.color, self.rect, 2, border_radius=10)
        screen.blit(self.txt_surface, (self.rect.x + 10, self.rect.y + 5))

    def get_text(self):
        return self.text





def lerp_color(start, end, t):
    return (
        int(start[0] + (end[0] - start[0]) * t),
        int(start[1] + (end[1] - start[1]) * t),
        int(start[2] + (end[2] - start[2]) * t)
    )