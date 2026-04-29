"""
game.py
-------
Gesture Space Shooter – Main entry point.
Run with:  python game.py
Controls:
  Hand gestures (webcam) OR keyboard fallback (← → SPACE P)
"""

import sys
import math
import random
import pygame

from gesture_engine import GestureEngine, Gesture
from particles     import ParticleSystem, StarField, Nebula
from entities      import (PlayerShip, Bullet, MegaBlast,
                           Scout, Cruiser, Boss, EnemyBullet, PowerUp)
from hud           import HUD, MenuScreen, OverlayScreen


# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────

SCREEN_W   = 1280
SCREEN_H   = 720
FPS        = 60
TITLE      = "Gesture Space Shooter"

# Wave configuration: list of (scout_count, cruiser_count, has_boss)
WAVES = [
    (6,  0, False),
    (10, 1, False),
    (12, 2, False),
    (14, 3, False),
    (8,  2, True ),   # wave 5 – first boss
    (16, 4, False),
    (18, 5, False),
    (20, 6, False),
    (16, 6, True ),   # wave 9 – second boss
    (25, 8, True ),   # wave 10 – final boss
]

SHOOT_CD_DEFAULT = 0.22   # seconds between normal shots
MEGA_COOLDOWN    = 8.0    # seconds to recharge mega blast

# Gesture → action debounce
GESTURE_DEBOUNCE = 0.12   # min seconds gesture must hold before acting

BG_COLOR = (4, 4, 20)


# ─────────────────────────────────────────────
#  Game States
# ─────────────────────────────────────────────

class State:
    MENU     = "menu"
    PLAYING  = "playing"
    PAUSED   = "paused"
    GAMEOVER = "gameover"
    VICTORY  = "victory"


# ─────────────────────────────────────────────
#  Main Game Class
# ─────────────────────────────────────────────

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock  = pygame.time.Clock()

        # Camera / gesture
        self.engine     = GestureEngine(camera_index=0)
        self.no_camera  = not self.engine.available
        self._last_gesture = Gesture.NONE
        self._gesture_hold = 0.0

        # Sub-systems
        self.particles  = ParticleSystem()
        self.stars      = StarField(SCREEN_W, SCREEN_H, count=260)
        self.nebula     = Nebula(SCREEN_W, SCREEN_H)

        # UI
        self.hud        = HUD(SCREEN_W, SCREEN_H)
        self.menu_ui    = MenuScreen(SCREEN_W, SCREEN_H)
        self.over_ui    = OverlayScreen(SCREEN_W, SCREEN_H)

        # Pre-render background to a surface (nebula is static)
        self.bg_surf = pygame.Surface((SCREEN_W, SCREEN_H))
        self.bg_surf.fill(BG_COLOR)
        self.nebula.draw(self.bg_surf)

        self.state = State.MENU
        self._init_game()

        # Pause surface
        self._pause_overlay = None

    # ── Game init / reset ─────────────────────

    def _init_game(self):
        self.player      = PlayerShip(SCREEN_W // 2, SCREEN_H - 90)
        self.bullets:    list[Bullet]    = []
        self.mega_shots: list[MegaBlast] = []
        self.enemies:    list           = []
        self.powerups:   list[PowerUp]  = []

        self.score       = 0
        self.combo       = 1
        self.combo_timer = 0.0

        self.wave        = 0
        self.wave_timer  = 0.0   # cooldown between waves
        self.wave_active = False
        self.enemies_to_spawn: list = []
        self.spawn_timer = 0.0
        self.spawn_interval = 1.2

        self.shoot_cd    = 0.0
        self.mega_cd     = 0.0

        self.particles   = ParticleSystem()
        self._start_next_wave()

    def _start_next_wave(self):
        self.wave += 1
        if self.wave > len(WAVES):
            self.state = State.VICTORY
            return

        cfg = WAVES[self.wave - 1]
        scouts, cruisers, has_boss = cfg

        queue = []
        for _ in range(scouts):
            queue.append("scout")
        for _ in range(cruisers):
            queue.append("cruiser")
        if has_boss:
            queue.append("boss")
        random.shuffle(queue[:scouts+cruisers])  # shuffle non-boss

        self.enemies_to_spawn = queue
        self.wave_active      = True
        self.spawn_timer      = 0.0
        self.spawn_interval   = max(0.3, 1.4 - self.wave * 0.05)

    def _spawn_enemy(self, kind):
        x = random.randint(80, SCREEN_W - 80)
        y = -60
        cls = {"scout": Scout, "cruiser": Cruiser, "boss": Boss}[kind]
        self.enemies.append(cls(x, y, SCREEN_W, SCREEN_H))

    # ── Main loop ─────────────────────────────

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)   # cap to avoid spiral of death

            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                self._handle_event(event)

            # Gesture update (each frame)
            self.engine.update()
            gesture  = self.engine.gesture
            wrist_x  = self.engine.wrist_x
            cam_surf = self.engine.get_pygame_surface(180, 120)

            self._process_gesture(gesture, wrist_x, dt)

            # State update
            if self.state == State.PLAYING:
                self._update(dt, gesture, wrist_x)

            # Draw
            self._draw(cam_surf, gesture)

            pygame.display.flip()

        self.engine.release()
        pygame.quit()
        sys.exit(0)

    # ── Event Handler ─────────────────────────

    def _handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state in (State.PLAYING, State.PAUSED):
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                else:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))

            elif event.key == pygame.K_SPACE:
                if self.state == State.MENU:
                    self.state = State.PLAYING
                elif self.state in (State.GAMEOVER, State.VICTORY):
                    self._init_game()
                    self.state = State.PLAYING
                elif self.state == State.PLAYING:
                    self._fire_bullet()
                elif self.state == State.PAUSED:
                    self.state = State.PLAYING

            elif event.key == pygame.K_p:
                if self.state == State.PLAYING:
                    self.state = State.PAUSED
                elif self.state == State.PAUSED:
                    self.state = State.PLAYING

    # ── Gesture → Action ──────────────────────

    def _process_gesture(self, gesture: Gesture, wrist_x: float, dt: float):
        """Map current gesture to game actions."""
        # Debounce: must hold same gesture for GESTURE_DEBOUNCE seconds
        if gesture == self._last_gesture:
            self._gesture_hold += dt
        else:
            self._gesture_hold = 0.0
            self._last_gesture = gesture

        held = self._gesture_hold >= GESTURE_DEBOUNCE

        if gesture == Gesture.OPEN_PALM:
            if self.state == State.PLAYING:
                self.player.set_target_x(wrist_x, SCREEN_W)

        elif gesture == Gesture.FIST and held:
            if self.state == State.MENU:
                self.state = State.PLAYING
            elif self.state in (State.GAMEOVER, State.VICTORY):
                self._init_game()
                self.state = State.PLAYING

        elif gesture == Gesture.PEACE and held:
            if self.state == State.PLAYING:
                self.player.activate_shield()
                self.particles.shield_ripple(
                    int(self.player.x), int(self.player.y))

        elif gesture == Gesture.PINCH and held:
            if self.state == State.PLAYING and self.mega_cd <= 0:
                self._fire_mega()

        elif gesture == Gesture.THUMBS_UP and held:
            if self.state == State.PLAYING:
                self.state = State.PAUSED
            elif self.state == State.PAUSED:
                self.state = State.PLAYING

        # Keyboard fallback (always active)
        keys = pygame.key.get_pressed()
        if self.state == State.PLAYING:
            speed = 400
            if self.no_camera:
                # Move with arrow keys
                if keys[pygame.K_LEFT]:
                    self.player.target_x = max(40, self.player.target_x - speed * dt)
                if keys[pygame.K_RIGHT]:
                    self.player.target_x = min(SCREEN_W-40, self.player.target_x + speed * dt)

    # ── Shooting ──────────────────────────────

    def _fire_bullet(self):
        self.bullets.append(Bullet(self.player.x, self.player.y - 28))

    def _fire_mega(self):
        self.mega_shots.append(MegaBlast(self.player.x, self.player.y - 28))
        self.mega_cd = MEGA_COOLDOWN
        self.particles.mega_blast(
            int(self.player.x), int(self.player.y), SCREEN_W, SCREEN_H)

    # ── Update ────────────────────────────────

    def _update(self, dt, gesture, wrist_x):
        # Auto-shoot on fist gesture (hold to rapid-fire)
        if gesture == Gesture.FIST and self._gesture_hold >= GESTURE_DEBOUNCE:
            self.shoot_cd -= dt
            if self.shoot_cd <= 0:
                self._fire_bullet()
                self.shoot_cd = SHOOT_CD_DEFAULT
        else:
            self.shoot_cd = max(0, self.shoot_cd - dt)

        # Keyboard shooting
        keys = pygame.key.get_pressed()
        if self.no_camera and keys[pygame.K_SPACE]:
            self.shoot_cd -= dt
            if self.shoot_cd <= 0:
                self._fire_bullet()
                self.shoot_cd = SHOOT_CD_DEFAULT

        # Mega cooldown
        self.mega_cd = max(0, self.mega_cd - dt)

        # Player
        self.player.update(dt)
        self.particles.thruster(int(self.player.x), int(self.player.y) + 28)

        # Bullets
        for b in self.bullets:
            b.update(dt)
        self.bullets = [b for b in self.bullets if not b.dead]

        # Mega blasts
        for m in self.mega_shots:
            m.update(dt)
        self.mega_shots = [m for m in self.mega_shots if not m.dead]

        # Enemy spawning
        if self.wave_active and self.enemies_to_spawn:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                kind = self.enemies_to_spawn.pop(0)
                self._spawn_enemy(kind)
                self.spawn_timer = self.spawn_interval

        # Check wave complete
        if self.wave_active and not self.enemies_to_spawn and not self.enemies:
            self.wave_active = False
            self.wave_timer  = 3.0   # pause between waves

        if not self.wave_active and not self.wave_active:
            self.wave_timer -= dt
            if self.wave_timer <= 0 and self.state == State.PLAYING:
                self._start_next_wave()

        # Enemy update
        for e in self.enemies:
            e.update(dt)
        self.enemies = [e for e in self.enemies if not e.dead]

        # PowerUp update
        for p in self.powerups:
            p.update(dt)
        self.powerups = [p for p in self.powerups if not p.dead]

        # Particle update
        self.particles.update(dt)

        # Star update
        self.stars.update(dt)

        # Combo timer
        if self.combo > 1:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 1

        # ── Collisions ────────────────────────

        player_rect = self.player.get_rect()

        # Bullet vs Enemy
        for bullet in self.bullets[:]:
            b_rect = bullet.get_rect()
            for enemy in self.enemies[:]:
                if b_rect.colliderect(enemy.get_rect()):
                    bullet.dead = True
                    killed = enemy.take_hit(1)
                    self.particles.hit_spark(int(enemy.x), int(enemy.y))
                    if killed:
                        self._on_enemy_killed(enemy)
                    break

        # Mega vs Enemy
        for mega in self.mega_shots[:]:
            m_rect = mega.get_rect()
            for enemy in self.enemies[:]:
                if m_rect.colliderect(enemy.get_rect()):
                    killed = enemy.take_hit(5)
                    self.particles.hit_spark(int(enemy.x), int(enemy.y))
                    if killed:
                        self._on_enemy_killed(enemy)

        # Enemy vs Player
        for enemy in self.enemies[:]:
            if player_rect.colliderect(enemy.get_rect()):
                if hasattr(enemy, 'hp') and enemy.hp > 0:
                    hit = self.player.take_hit()
                    if hit:
                        self.particles.explode(int(self.player.x), int(self.player.y),
                                               color=(80, 200, 255), count=20)
                        self.combo = 1
                    enemy.take_hit(99)   # destroy enemy
                    self._on_enemy_killed(enemy)

        # Boss bullets vs Player
        for enemy in self.enemies:
            if isinstance(enemy, Boss):
                for eb in enemy.bullets[:]:
                    if player_rect.colliderect(eb.get_rect()):
                        eb.dead = True
                        hit = self.player.take_hit()
                        if hit:
                            self.particles.explode(int(self.player.x), int(self.player.y),
                                                   color=(80, 200, 255), count=20)
                            self.combo = 1

        # PowerUp vs Player
        for pu in self.powerups[:]:
            if player_rect.colliderect(pu.get_rect()):
                pu.dead = True
                self.particles.pickup_sparkle(int(pu.x), int(pu.y), pu.COLOR)
                self._apply_powerup(pu.kind)

        # Death check
        if self.player.health <= 0:
            self.particles.explode(int(self.player.x), int(self.player.y),
                                   color=(80, 200, 255), count=100, speed=300)
            self.state = State.GAMEOVER

    def _on_enemy_killed(self, enemy):
        pts = enemy.__class__.VALUE * self.combo
        self.score += pts
        self.combo  = min(self.combo + 1, 8)
        self.combo_timer = 3.0
        self.particles.explode(int(enemy.x), int(enemy.y))

        # 30% chance to drop powerup
        if random.random() < 0.30:
            self.powerups.append(PowerUp(enemy.x, enemy.y))

    def _apply_powerup(self, kind):
        if kind == "health":
            self.player.health = min(self.player.health + 1, self.player.max_health)
        elif kind == "shield":
            self.player.activate_shield()
            self.particles.shield_ripple(int(self.player.x), int(self.player.y))
        elif kind == "mega":
            self.mega_cd = 0   # instant recharge

    # ── Draw ──────────────────────────────────

    def _draw(self, cam_surf, gesture):
        # Background
        self.screen.blit(self.bg_surf, (0, 0))
        self.stars.draw(self.screen)

        if self.state == State.MENU:
            self.menu_ui.draw(self.screen, no_camera=self.no_camera)
            return

        if self.state == State.PAUSED:
            self._draw_game_world(cam_surf, gesture)
            self._draw_pause_overlay()
            return

        if self.state in (State.GAMEOVER, State.VICTORY):
            self._draw_game_world(cam_surf, gesture)
            msg      = "VICTORY!" if self.state == State.VICTORY else "GAME OVER"
            victory  = self.state == State.VICTORY
            self.over_ui.draw(self.screen, msg, self.score, self.wave, victory=victory)
            return

        # Normal playing state
        self._draw_game_world(cam_surf, gesture)

    def _draw_game_world(self, cam_surf, gesture):
        # Entities
        for pu in self.powerups:
            pu.draw(self.screen)
        for e in self.enemies:
            e.draw(self.screen)
        for b in self.bullets:
            b.draw(self.screen)
        for m in self.mega_shots:
            m.draw(self.screen)

        self.particles.draw(self.screen)
        self.player.draw(self.screen)

        # Wave announcement banner
        if not self.wave_active and self.wave_timer > 1.5:
            self._draw_wave_banner()

        # HUD
        self.hud.draw(
            surf         = self.screen,
            score        = self.score,
            lives        = self.player.health,
            max_lives    = self.player.max_health,
            wave         = self.wave,
            gesture_name = gesture.name.replace("_", " "),
            cam_surf     = cam_surf,
            combo        = self.combo,
            mega_ready   = self.mega_cd <= 0,
            shield_timer = self.player.shield_timer,
            shield_dur   = self.player.shield_dur,
        )

    def _draw_wave_banner(self):
        """Full-width wave announcement."""
        t = pygame.time.get_ticks() / 400
        pulse = abs(math.sin(t))
        font  = pygame.font.SysFont("Consolas", 64, bold=True)
        is_boss = self.wave <= len(WAVES) and WAVES[self.wave-1][2]
        text  = f"⚡ BOSS INCOMING!" if is_boss else f"— WAVE {self.wave} —"
        col   = (255, int(80+120*pulse), int(40*pulse)) if is_boss else (int(120+100*pulse), 200, 255)
        t_surf = font.render(text, True, col)
        # Glow bg
        pad    = 30
        glow   = pygame.Surface((t_surf.get_width()+pad*2, t_surf.get_height()+pad), pygame.SRCALPHA)
        glow.fill((0, 0, 0, 140))
        x = SCREEN_W//2 - t_surf.get_width()//2 - pad
        y = SCREEN_H//2 - t_surf.get_height()//2 - pad//2
        self.screen.blit(glow, (x, y))
        self.screen.blit(t_surf, (SCREEN_W//2 - t_surf.get_width()//2, SCREEN_H//2 - t_surf.get_height()//2))

    def _draw_pause_overlay(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 30, 160))
        self.screen.blit(overlay, (0, 0))

        font  = pygame.font.SysFont("Consolas", 72, bold=True)
        small = pygame.font.SysFont("Consolas", 24)
        t     = pygame.time.get_ticks() / 600
        pulse = abs(math.sin(t))
        col   = (int(100+120*pulse), 180, 255)

        txt  = font.render("PAUSED", True, col)
        hint = small.render("👍 Thumbs Up or P to resume  |  ESC to quit", True, (180, 200, 255))
        self.screen.blit(txt,  txt.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 40)))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_W//2, SCREEN_H//2 + 40)))


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    game = Game()
    game.run()
