import pygame
import os
import pytweening
import time
import math
import random

pygame.font.init()

# --- THE SOFT GIRL PALETTE (UPDATED) ---
BG_FALLBACK = (28, 15, 28)      # Deep Violet-Plum
BUTTON_BASE = (230, 110, 150)   # Seductive Rose Pink
BUTTON_HOVER = (245, 140, 180)  # Lighter Rose
BUTTON_BORDER = (255, 180, 210) # Soft Rose-Gold line
TEXT_COLOR = (255, 245, 255)    # Soft White with Pink tint
INPUT_BG = (20, 10, 20)         # Fallback bg
COLOR_ACTIVE = (255, 105, 180)  # Hot Pink
COLOR_PASSIVE = (200, 150, 180) # Muted Mauve
PROFILE_BG = (45, 25, 45)       # Sleek Glass Panel
TEXT_SHADOW = (40, 15, 40)      # Deep Plum for crisp text shadows

# --- ANIMATION ENGINE ---
class Tween:
    def __init__(self, target, attr, end_val, duration, easing=pytweening.linear, on_complete=None):
        self.target = target
        self.attr = attr
        self.start_val = getattr(target, attr)
        self.end_val = end_val
        self.duration = duration
        self.easing = easing
        self.on_complete = on_complete
        self.elapsed = 0
        self.active = True
        self.is_color = isinstance(self.start_val, (tuple, list)) and len(self.start_val) in (3, 4)

    def update(self, dt):
        if not self.active: return False
        self.elapsed += dt
        t = min(1.0, self.elapsed / self.duration)
        eased_t = self.easing(t)

        if self.is_color:
            current = []
            for i in range(len(self.start_val)):
                s = self.start_val[i]
                e = self.end_val[i]
                current.append(s + (e - s) * eased_t)
            setattr(self.target, self.attr, tuple(current))
        else:
            val = self.start_val + (self.end_val - self.start_val) * eased_t
            setattr(self.target, self.attr, val)

        if t >= 1.0:
            self.active = False
            if self.on_complete: self.on_complete()
            return False
        return True

class AnimationManager:
    _instance = None
    def __init__(self):
        self.tweens = []
    
    @classmethod
    def get(cls):
        if not cls._instance: cls._instance = cls()
        return cls._instance

    def start_tween(self, target, attr, end_val, duration, easing=pytweening.easeOutQuad, on_complete=None):
        # Cancel existing tweens on same property
        self.tweens = [t for t in self.tweens if not (t.target == target and t.attr == attr)]
        new_tween = Tween(target, attr, end_val, duration, easing, on_complete)
        self.tweens.append(new_tween)
        return new_tween

    def update(self, dt):
        # dt in seconds
        active_tweens = []
        for t in self.tweens:
            if t.update(dt):
                active_tweens.append(t)
        self.tweens = active_tweens

# Global accessor
def animate(target, attr, end_val, duration, easing=pytweening.easeOutQuad, on_complete=None):
    return AnimationManager.get().start_tween(target, attr, end_val, duration, easing, on_complete)

def update_animations(dt):
    AnimationManager.get().update(dt)

# --- JUICE & EFFECTS ---
class ScreenShake:
    _instance = None
    def __init__(self):
        self.duration = 0
        self.intensity = 0
        self.offset = [0, 0]
    
    @classmethod
    def get(cls):
        if not cls._instance: cls._instance = cls()
        return cls._instance

    def shake(self, intensity=5, duration=0.5):
        self.intensity = intensity
        self.duration = duration

    def update(self, dt):
        if self.duration > 0:
            self.duration -= dt
            if self.duration <= 0:
                self.offset = [0, 0]
            else:
                import random
                self.offset = [
                    random.uniform(-self.intensity, self.intensity),
                    random.uniform(-self.intensity, self.intensity)
                ]
        return self.offset

class Particle:
    def __init__(self, x, y, color, vel, life):
        self.x = x
        self.y = y
        self.color = color
        self.vel = vel
        self.life = life
        self.max_life = life
        self.size = random.randint(3, 8) if 'random' in globals() else 5

    def update(self, dt):
        self.x += self.vel[0] * dt * 60
        self.y += self.vel[1] * dt * 60
        self.life -= dt
        return self.life > 0

    def draw(self, screen):
        alpha = int((self.life / self.max_life) * 255)
        scale = (self.life / self.max_life) * self.size
        # Draw a soft circle or sparkle
        surf = pygame.Surface((int(scale*2), int(scale*2)), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (int(scale), int(scale)), int(scale))
        screen.blit(surf, (int(self.x - scale), int(self.y - scale)))

class ParticleSystem:
    _instance = None
    def __init__(self):
        self.particles = []

    @classmethod
    def get(cls):
        if not cls._instance: cls._instance = cls()
        return cls._instance

    def emit(self, x, y, count=10, color=(255, 105, 180)):
        import random
        for _ in range(count):
            angle = random.uniform(0, 6.28)
            speed = random.uniform(1, 4)
            vel = [math.cos(angle) * speed, math.sin(angle) * speed]
            self.particles.append(Particle(x, y, color, vel, random.uniform(0.5, 1.0)))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)

class FloatingText:
    def __init__(self, x, y, text, color, size=40):
        self.x = x
        self.y = y
        self.text = str(text)
        self.color = color
        self.size = size
        self.life = 1.0 # Seconds
        self.y_offset = 0
        self.scale = 0.5
        
        # Pop in animation
        AnimationManager.get().start_tween(self, "scale", 1.2, 0.3, pytweening.easeOutElastic)
        AnimationManager.get().start_tween(self, "y_offset", -50, 1.0, pytweening.easeOutExpo)

    def update(self, dt):
        self.life -= dt
        return self.life > 0

    def draw(self, screen):
        alpha = int(min(255, self.life * 500)) if self.life < 0.5 else 255
        
        font = get_font(int(self.size * self.scale))
        surf = font.render(self.text, True, self.color)
        surf.set_alpha(alpha)
        
        # Stroke/Shadow
        shadow_surf = font.render(self.text, True, (50, 20, 50))
        shadow_surf.set_alpha(alpha)
        
        draw_pos = (self.x - surf.get_width()//2, self.y + self.y_offset - surf.get_height()//2)
        screen.blit(shadow_surf, (draw_pos[0]+2, draw_pos[1]+2))
        screen.blit(surf, draw_pos)

class FloatingTextManager:
    _instance = None
    def __init__(self):
        self.texts = []

    @classmethod
    def get(cls):
        if not cls._instance: cls._instance = cls()
        return cls._instance

    def add(self, x, y, text, color):
        self.texts.append(FloatingText(x, y, text, color))

    def update(self, dt):
        self.texts = [t for t in self.texts if t.update(dt)]

    def draw(self, screen):
        for t in self.texts:
            t.draw(screen)

def spawn_floating_text(x, y, text, color=(255, 255, 255)):
    FloatingTextManager.get().add(x, y, text, color)

def draw_floating_text(screen):
    FloatingTextManager.get().draw(screen)

def shake_screen(intensity=5, duration=0.5):
    ScreenShake.get().shake(intensity, duration)

def spawn_particles(x, y, count=10, color=(255, 105, 180)):
    ParticleSystem.get().emit(x, y, count, color)

def update_juice(dt):
    offset = ScreenShake.get().update(dt)
    ParticleSystem.get().update(dt)
    FloatingTextManager.get().update(dt)
    return offset

def draw_particles(screen):
    ParticleSystem.get().draw(screen)

def draw_juice_overlays(screen):
    ParticleSystem.get().draw(screen)
    FloatingTextManager.get().draw(screen)
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
        # Sleek, flat panel with thin border
        pygame.draw.rect(surf, PROFILE_BG, r, border_radius=18)
        pygame.draw.rect(surf, BUTTON_BORDER, r, 1, border_radius=18)




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


# --- BUTTON CLASS (UPDATED FOR SOFT GIRL AESTHETIC) ---
class Button:
    def __init__(self, text, x, y, width, height, font_size=35):
        self.text = text
        self.text_input = text
        self.rect = pygame.Rect(x, y, width, height)
        self.base_font_size = font_size
        self.cur_col = BUTTON_BASE
        self.tgt_col = BUTTON_BASE
        self.hovered = False
        self.is_hovered = False
        self.scale = 1.0

        # Calculate fitting font immediately
        self.font = self.recalculate_font()

    def recalculate_font(self):
        """Reduces font size until text fits inside the button width, but respects a minimum size."""
        current_size = self.base_font_size
        padding = 40  # 20px buffer on each side
        min_font_size = max(18, int(self.base_font_size * 0.6)) # Don't shrink below 60% of base or 18px

        while current_size > min_font_size:
            temp_font = get_font(current_size)
            w, h = temp_font.size(self.text)
            if w < (self.rect.width - padding):
                return temp_font
            current_size -= 2

        # If it still doesn't fit, expand the rect!
        final_font = get_font(current_size)
        w, h = final_font.size(self.text)
        if w > (self.rect.width - padding):
            # Center-aligned expansion (expand both sides)
            diff = w - (self.rect.width - padding)
            self.rect.width += diff
            self.rect.x -= diff // 2
            
        return final_font

    def check_input(self, pos):
        return self.rect.collidepoint(pos)

    def change_color(self, pos):
        # Update hover state
        hovering = self.rect.collidepoint(pos)
        
        if hovering and not self.is_hovered:
            self.is_hovered = True
            self.tgt_col = BUTTON_HOVER
            AnimationManager.get().start_tween(self, "scale", 1.05, 0.15, pytweening.easeOutBack)
        elif not hovering and self.is_hovered:
            self.is_hovered = False
            self.tgt_col = BUTTON_BASE
            AnimationManager.get().start_tween(self, "scale", 1.0, 0.15, pytweening.easeOutQuad)

    def set_text(self, t):
        self.text = t;
        self.text_input = t
        self.font = self.recalculate_font()

    def update(self, screen):
        # Color Interpolation
        if self.cur_col != self.tgt_col:
            # Simple lerp for color if no tween active
            c1 = pygame.Color(*self.cur_col)
            c2 = pygame.Color(*self.tgt_col)
            self.cur_col = c1.lerp(c2, 0.2)
        
        # Calculate Scaled Rect
        center = self.rect.center
        w = int(self.rect.width * self.scale)
        h = int(self.rect.height * self.scale)
        draw_rect = pygame.Rect(0, 0, w, h)
        draw_rect.center = center

        if assets["btn"] and assets["btn_hover"]:
            img = assets["btn_hover"] if self.is_hovered else assets["btn"]
            scaled = pygame.transform.scale(img, (w, h))
            screen.blit(scaled, draw_rect)
        else:
            # Subtle Drop shadow instead of retro box shadow
            shadow_rect = draw_rect.copy()
            shadow_rect.y += 4
            s_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(s_surf, (0, 0, 0, 40), s_surf.get_rect(), border_radius=25)
            screen.blit(s_surf, (shadow_rect.x, shadow_rect.y))
            
            # Base button - sleek and flat
            pygame.draw.rect(screen, self.cur_col, draw_rect, border_radius=25)
            
            # Subtle 1px Border (Glass style)
            pygame.draw.rect(screen, BUTTON_BORDER, draw_rect, 1, border_radius=25)

        # Draw Text (Centered)
        # Crisp, single drop shadow instead of messy 5-way blur
        shadow = self.font.render(self.text, True, TEXT_SHADOW)
        s_rect = shadow.get_rect(center=(center[0], center[1] + 2))
        screen.blit(shadow, s_rect)
        
        # Main Text
        txt = self.font.render(self.text, True, TEXT_COLOR)
        txt_rect = txt.get_rect(center=center)
        screen.blit(txt, txt_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.rect.collidepoint(event.pos):
                    if hasattr(self, 'on_click') and self.on_click:
                        self.on_click()
                    return True
        return False


class InputBox:
    def __init__(self, x, y, w, h, text='', placeholder='', is_password=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = COLOR_PASSIVE
        self.text = text
        self.placeholder = placeholder
        self.is_password = is_password
        self.active = False
        
        self.font = get_font(28)
        self.txt_surface = None
        self.re_render()

        # Animation state
        self.glow_alpha = 0
        self.target_glow = 0

    def re_render(self):
        # Decide what to show
        if not self.text and not self.active and self.placeholder:
            # Show Placeholder
            self.txt_surface = self.font.render(self.placeholder, True, COLOR_PASSIVE)
        else:
            # Show Actual Text (or stars)
            to_show = "*" * len(self.text) if self.is_password else self.text
            self.txt_surface = self.font.render(to_show, True, TEXT_COLOR) # Light text for dark BG

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = COLOR_ACTIVE if self.active else COLOR_PASSIVE
            self.re_render()

        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    return self.text
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    # Limit length
                    if len(self.text) < 20: self.text += event.unicode
                self.re_render()
        return None

    def update(self):
        # We KEEP fixed width now for better layout control
        # width = max(200, self.txt_surface.get_width() + 10)
        # self.rect.w = width
        
        # Glow Animation
        self.target_glow = 150 if self.active else 0
        self.glow_alpha += (self.target_glow - self.glow_alpha) * 0.2

    def draw(self, screen):
        # 1. Glow (if active)
        if self.glow_alpha > 1:
            glow_surf = pygame.Surface((self.rect.width + 10, self.rect.height + 10), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*COLOR_ACTIVE, int(self.glow_alpha * 0.4)), glow_surf.get_rect(), border_radius=15)
            screen.blit(glow_surf, (self.rect.x - 5, self.rect.y - 5))

        # 2. Dark Glass Background
        bg_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, (0, 0, 0, 120), bg_surf.get_rect(), border_radius=12)
        screen.blit(bg_surf, (self.rect.x, self.rect.y))
        
        # 3. Delicate Border
        border_c = COLOR_ACTIVE if self.active else COLOR_PASSIVE
        pygame.draw.rect(screen, border_c, self.rect, 1 if not self.active else 2, border_radius=12)
        
        # 4. Text
        # Center vertically
        text_y = self.rect.y + (self.rect.height - self.txt_surface.get_height()) // 2
        screen.blit(self.txt_surface, (self.rect.x + 15, text_y))

    def get_text(self):
        return self.text





def lerp_color(start, end, t):
    return (
        int(start[0] + (end[0] - start[0]) * t),
        int(start[1] + (end[1] - start[1]) * t),
        int(start[2] + (end[2] - start[2]) * t)
    )