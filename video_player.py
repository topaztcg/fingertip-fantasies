import pygame
import time
import sys
import os
from ffpyplayer.player import MediaPlayer


class VideoWrapper:
    def __init__(self, path, size=(320, 180), muted=False, loop=False):
        self.path = path
        self.target_size = size
        self.video_size = size # fallback
        self.player = None
        self.current_frame = None
        self.muted = muted
        self.loop = loop
        self.is_finished = False
        self.val = 0
        self.last_frame_time = time.time()

        # Save opts for reload
        self.ff_opts = {'out_fmt': 'rgb24', 'sn': 1} 
        if muted: 
            self.ff_opts['an'] = 1
            self.ff_opts['sync'] = 'video' 
        else:
            self.ff_opts['sync'] = 'audio' 
        
        # NOTE: We do NOT set 'loop' internally. We handle it manually.

        try:
            self.player = MediaPlayer(path, ff_opts=self.ff_opts)
            if not muted:
                self.player.set_volume(1.0)
            else:
                self.player.set_volume(0.0)
                
        except Exception as e:
            print(f"[Video] Error loading {path}: {e}")
            self.is_finished = True
            self.player = None

    def update(self):
        if not self.player:
            return None, 0

        # Sync Logic
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        
        # Buffer check
        if self.val > 0.005 and elapsed < self.val:
             return self.current_frame, 0

        # Get frame
        frame, val = self.player.get_frame()

        # --- EOF HANDLING ---
        if val == 'eof':
            if self.loop:
                # HARD RELOAD LOOP
                # Seeking proved unreliable. We re-initialize the player.
                try:
                    self.player = MediaPlayer(self.path, ff_opts=self.ff_opts)
                    if not self.muted:
                        self.player.set_volume(1.0)
                    else:
                        self.player.set_volume(0.0)
                    
                    self.val = 0
                    self.last_frame_time = time.time()
                except Exception as e:
                    print(f"[Video DEBUG] Reload failed: {e}")
                    self.is_finished = True
                return self.current_frame, 0
            else:
                # END OF VIDEO
                self.is_finished = True
                try: 
                    self.player.set_volume(0.0)
                    self.player.set_pause(True) 
                except: pass
                return self.current_frame, 0

        # --- FRAME HANDLING ---
        if frame:
             if val > 0: self.val = val
             self.last_frame_time = time.time()
             
             img, t = frame
             w, h = img.get_size()
             self.video_size = (w, h)
             
             try:
                 # Fast conversion
                 raw_surf = pygame.image.frombuffer(img.to_bytearray()[0], (w, h), "RGB")
                 if self.target_size != (w, h):
                    self.current_frame = pygame.transform.scale(raw_surf, self.target_size)
                 else:
                    self.current_frame = raw_surf
             except:
                 pass
        else:
             # Wait command from player
             if val > 0: self.val = val

        return self.current_frame, 0
        frame, val = self.player.get_frame()

        if val == 'eof':
            if self.loop:
                self.player.seek(0, relative=False)
                # Reset timings to avoid fast-forwarding after seek
                self.last_frame_time = time.time()
                self.val = 0.05 # Add small buffer delay for seek
                return self.current_frame, 0
            else:
                self.is_finished = True
                return self.current_frame, 0 

        if frame:
             # We got a frame!
             if val > 0: self.val = val
             self.last_frame_time = time.time()
             
             img, t = frame
             w, h = img.get_size()
             try:
                 raw_surf = pygame.image.frombuffer(img.to_bytearray()[0], (w, h), "RGB")
                 self.current_frame = pygame.transform.scale(raw_surf, self.target_size)
             except:
                 pass
        else:
            # No frame returned (val tells us to wait)
            # ffpyplayer often returns frame=None, val=remaining_wait
            # We trust val here.
            if val > 0: self.val = val
        
        return self.current_frame, 0

    def close(self):
        if self.player:
            try:
                # ffpyplayer specific close method if exists, otherwise assume garbage collection handles it
                if hasattr(self.player, 'close_player'):
                    self.player.close_player()
            except:
                pass
            self.player = None


def run_fullscreen_video(screen, video_path, speed=1.0, show_hint=False):
    if not video_path: return

    w, h = screen.get_width(), screen.get_height()
    player = VideoWrapper(video_path, (w, h), muted=False, loop=False)

    if player.is_finished: return  # Exit if load failed

    font = pygame.font.SysFont("arial", 30)
    clock = pygame.time.Clock()
    running = True
    start_time = time.time()

    while running:
        # Get frame AND delay
        frame, delay = player.update()

        if player.is_finished:
            running = False
            break 

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Debounce click
                if time.time() - start_time > 0.5:
                    running = False

        screen.fill((0, 0, 0))
        if frame:
            fw, fh = frame.get_size()
            dx = (w - fw) // 2
            dy = (h - fh) // 2
            screen.blit(frame, (dx, dy))

        if show_hint:
            hint_surf = font.render("Click to Skip", True, (200, 200, 200))
            screen.blit(hint_surf, (w // 2 - hint_surf.get_width() // 2, h - 60))

        clock.tick(60)
        pygame.display.update()

    player.close()
