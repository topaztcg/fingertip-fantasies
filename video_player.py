import pygame
import time
import sys
import os
from ffpyplayer.player import MediaPlayer


class VideoWrapper:
    def __init__(self, path, size=(320, 180), muted=False):
        self.path = path
        self.target_size = size
        self.player = None
        self.current_frame = None
        self.muted = muted
        self.is_finished = False
        self.last_pts = -1

        try:
            # Attempt to load video
            # loop=0 is critical
            ff_opts = {'out_fmt': 'rgb24', 'loop': 0}
            if muted: ff_opts['an'] = 1

            self.player = MediaPlayer(path, ff_opts=ff_opts)
            if not muted:
                self.player.set_volume(1.0)
            else:
                self.player.set_volume(0.0)
        except Exception as e:
            print(f"[Video] Error loading {path}: {e}")
            self.is_finished = True
            self.player = None

    def update(self):
        if not self.player or self.is_finished:
            return None, 0

        # Get frame and delay (val)
        frame, val = self.player.get_frame()

        if val == 'eof':
            self.is_finished = True
            return None, 0

        if frame:
            img, t = frame

            # Anti-Loop: Timestamp Check
            if self.last_pts > 0 and t < (self.last_pts - 0.5):
                self.is_finished = True
                return None, 0

            self.last_pts = t

            w, h = img.get_size()
            try:
                raw_surf = pygame.image.frombuffer(img.to_bytearray()[0], (w, h), "RGB")
                self.current_frame = pygame.transform.scale(raw_surf, self.target_size)
            except:
                pass

        return self.current_frame, val

    def close(self):
        if self.player:
            try:
                self.player.close_player()
            except:
                pass
            self.player = None


def run_fullscreen_video(screen, video_path, speed=1.0, show_hint=False):
    if not video_path: return

    w, h = screen.get_width(), screen.get_height()
    player = VideoWrapper(video_path, (w, h), muted=False)

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

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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

        pygame.display.update()

        # --- SYNC FIX ---
        if delay > 0:
            # Wait exactly as long as the video needs
            time.sleep(delay)
        else:
            # Fallback if no specific delay is requested
            clock.tick(60)

    player.close()