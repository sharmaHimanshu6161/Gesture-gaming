"""
hud.py
------
Heads-Up Display: score, lives, wave, gesture indicator, combo, webcam thumbnail.
"""

import pygame
import math


# ─────────────────────────────────────────────
#  Colour tokens
# ─────────────────────────────────────────────

C_WHITE   = (255, 255, 255)
C_SCORE   = (120, 255, 120)
C_HEALTH  = (255, 80,  80)
C_HEALTH_OK = (60, 255, 120)
C_BLUE    = (80,  180, 255)
C_GOLD    = (255, 210, 50)
C_GREY    = (150, 150, 170)


def _load_font(size, bold=False):
    try:
        return pygame.font.SysFont("Consolas", size, bold=bold)
    except Exception:
        return pygame.font.SysFont("monospace", size, bold=bold)


class HUD:
    def __init__(self, screen_w, screen_h):
        self.sw = screen_w
        self.sh = screen_h

        self.font_large  = _load_font(36, bold=True)
        self.font_medium = _load_font(22, bold=True)
        self.font_small  = _load_font(16, bold=False)

        self._score_anim  = 0
        self._combo_alpha = 0
        self._wave_pop    = 0.0

    # ── Public draw call ──────────────────────

    def draw(self, surf, score, lives, max_lives, wave,
             gesture_name, cam_surf=None, combo=1, mega_ready=False,
             shield_timer=0.0, shield_dur=3.0):

        self._draw_score(surf, score)
        self._draw_lives(surf, lives, max_lives)
        self._draw_wave(surf, wave)
        self._draw_gesture(surf, gesture_name, mega_ready, shield_timer, shield_dur)
        if combo > 1:
            self._draw_combo(surf, combo)
        if cam_surf:
            self._draw_cam_thumbnail(surf, cam_surf)

    # ── Private renderers ─────────────────────

    def _draw_score(self, surf, score):
        label = self.font_small.render("SCORE", True, C_GREY)
        value = self.font_large.render(f"{score:,}", True, C_SCORE)
        surf.blit(label, (20, 12))
        surf.blit(value, (20, 30))

    def _draw_lives(self, surf, lives, max_lives):
        # Draw heart icons
        label = self.font_small.render("LIVES", True, C_GREY)
        surf.blit(label, (20, 76))
        for i in range(max_lives):
            x = 22 + i * 28
            y = 96
            col = C_HEALTH_OK if i < lives else (60, 60, 80)
            self._draw_heart(surf, x, y, 10, col)

    def _draw_heart(self, surf, cx, cy, r, color):
        """Draw a simple heart shape."""
        heart_surf = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
        # Two circles + triangle
        pygame.draw.circle(heart_surf, (*color, 220), (r,   r), r)
        pygame.draw.circle(heart_surf, (*color, 220), (r*3, r), r)
        pts = [(0, r), (r*4, r), (r*2, r*4-2)]
        pygame.draw.polygon(heart_surf, (*color, 220), pts)
        surf.blit(heart_surf, (cx - r*2, cy - r))

    def _draw_wave(self, surf, wave):
        label = self.font_small.render("WAVE", True, C_GREY)
        value = self.font_medium.render(str(wave), True, C_GOLD)
        surf.blit(label, (self.sw//2 - 20, 12))
        surf.blit(value, (self.sw//2 - value.get_width()//2, 30))

    def _draw_gesture(self, surf, gesture_name, mega_ready, shield_timer, shield_dur):
        panel_w = 220
        panel_h = 110
        px      = self.sw - panel_w - 10
        py      = 10

        # Panel background
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (10, 10, 30, 180), (0, 0, panel_w, panel_h), border_radius=12)
        pygame.draw.rect(panel, (60, 80, 140, 120), (0, 0, panel_w, panel_h), 1, border_radius=12)
        surf.blit(panel, (px, py))

        # Gesture emoji/text
        emoji_map = {
            "OPEN PALM": "🖐  MOVE",
            "FIST":      "✊  SHOOT",
            "PEACE":     "✌  SHIELD",
            "PINCH":     "🤌  MEGA BLAST",
            "THUMBS UP": "👍  PAUSE",
            "NONE":      "—  NO GESTURE",
        }
        g_text = emoji_map.get(gesture_name, gesture_name)
        label  = self.font_small.render("GESTURE", True, C_GREY)
        text   = self.font_medium.render(g_text if len(g_text) < 18 else g_text[:17], True, C_WHITE)
        surf.blit(label, (px+12, py+10))
        surf.blit(text,  (px+12, py+30))

        # Mega ready indicator
        if mega_ready:
            t = pygame.time.get_ticks() / 500
            col = (255, int(80 + 60*abs(math.sin(t))), 200)
            mega_lbl = self.font_small.render("⚡ MEGA READY", True, col)
            surf.blit(mega_lbl, (px+12, py+60))

        # Shield cooldown bar
        if shield_timer > 0:
            ratio = shield_timer / shield_dur
            bx = px + 12
            by = py + 88
            bw = panel_w - 24
            pygame.draw.rect(surf, (30,30,60), (bx, by, bw, 10), border_radius=4)
            pygame.draw.rect(surf, (80,160,255), (bx, by, int(bw*ratio), 10), border_radius=4)
            s_lbl = self.font_small.render("SHIELD", True, C_BLUE)
            surf.blit(s_lbl, (bx, by - 14))

    def _draw_combo(self, surf, combo):
        t = pygame.time.get_ticks() / 300
        scale = 1.0 + 0.08 * abs(math.sin(t))
        base_size = 40
        font = _load_font(int(base_size * scale), bold=True)
        col  = (255, int(180 + 60 * abs(math.sin(t))), 40)
        txt  = font.render(f"x{combo} COMBO!", True, col)
        surf.blit(txt, txt.get_rect(center=(self.sw//2, self.sh - 60)))

    def _draw_cam_thumbnail(self, surf, cam_surf):
        """Render a small webcam preview in the bottom-right corner."""
        thumb_w, thumb_h = 180, 120
        thumb = pygame.transform.scale(cam_surf, (thumb_w, thumb_h))
        tx = self.sw - thumb_w - 10
        ty = self.sh - thumb_h - 10
        # Border
        border = pygame.Surface((thumb_w+4, thumb_h+4), pygame.SRCALPHA)
        pygame.draw.rect(border, (80, 120, 200, 200), (0, 0, thumb_w+4, thumb_h+4), 2, border_radius=6)
        surf.blit(border, (tx-2, ty-2))
        surf.blit(thumb, (tx, ty))
        lbl = self.font_small.render("CAMERA", True, C_GREY)
        surf.blit(lbl, (tx, ty - 18))


# ─────────────────────────────────────────────
#  Menu Screen
# ─────────────────────────────────────────────

class MenuScreen:
    def __init__(self, screen_w, screen_h):
        self.sw = screen_w
        self.sh = screen_h
        self.font_title  = _load_font(72, bold=True)
        self.font_sub    = _load_font(28)
        self.font_small  = _load_font(18)
        self.t = 0.0

    def draw(self, surf, no_camera=False):
        self.t += 0.016

        # Title
        pulse = abs(math.sin(self.t * 1.5))
        col_title = (
            int(80 + 160*pulse),
            int(180 + 60*pulse),
            255,
        )
        title = self.font_title.render("GESTURE SHOOTER", True, col_title)
        surf.blit(title, title.get_rect(center=(self.sw//2, self.sh//2 - 120)))

        # Subtitle
        sub = self.font_sub.render("Control your ship with hand gestures!", True, (180, 200, 255))
        surf.blit(sub, sub.get_rect(center=(self.sw//2, self.sh//2 - 40)))

        # Controls
        controls = [
            ("🖐  Open Palm", "→ Move ship"),
            ("✊  Fist",      "→ Shoot"),
            ("✌  Peace",     "→ Shield"),
            ("🤌  Pinch",    "→ Mega Blast"),
            ("👍  Thumbs Up","→ Pause"),
        ]
        for i, (gesture, action) in enumerate(controls):
            y = self.sh//2 + 20 + i*30
            g_surf = self.font_small.render(gesture, True, (120, 220, 255))
            a_surf = self.font_small.render(action,  True, (220, 220, 255))
            surf.blit(g_surf, g_surf.get_rect(right=self.sw//2 - 10, centery=y))
            surf.blit(a_surf, a_surf.get_rect(left=self.sw//2 + 10,  centery=y))

        # Start prompt
        blink = int(abs(math.sin(self.t * 3)) * 255)
        start = self.font_sub.render("✊  MAKE A FIST — OR PRESS SPACE TO START", True, (255, 255, blink))
        surf.blit(start, start.get_rect(center=(self.sw//2, self.sh - 60)))

        if no_camera:
            warn = self.font_small.render("⚠ No camera detected – keyboard fallback active (← → Space)", True, (255, 200, 60))
            surf.blit(warn, warn.get_rect(center=(self.sw//2, self.sh - 28)))


# ─────────────────────────────────────────────
#  Game-Over / Victory Screen
# ─────────────────────────────────────────────

class OverlayScreen:
    def __init__(self, screen_w, screen_h):
        self.sw = screen_w
        self.sh = screen_h
        self.font_big   = _load_font(80, bold=True)
        self.font_med   = _load_font(30)
        self.font_small = _load_font(20)
        self.t = 0.0

    def draw(self, surf, message, score, wave, victory=False):
        self.t += 0.016

        # Dark overlay
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 20, 170))
        surf.blit(overlay, (0, 0))

        pulse = abs(math.sin(self.t * 2))
        col = (int(80*pulse+120), 255, int(80*pulse+100)) if victory else (255, int(60+80*pulse), 60)

        title = self.font_big.render(message, True, col)
        surf.blit(title, title.get_rect(center=(self.sw//2, self.sh//2 - 80)))

        score_txt = self.font_med.render(f"Score: {score:,}   |   Wave: {wave}", True, (220, 220, 255))
        surf.blit(score_txt, score_txt.get_rect(center=(self.sw//2, self.sh//2)))

        restart = self.font_small.render("✊ Fist or SPACE to restart  |  ESC to quit", True, (180, 180, 220))
        surf.blit(restart, restart.get_rect(center=(self.sw//2, self.sh//2 + 60)))
