"""
particles.py
------------
GPU-friendly particle system using Pygame with additive blending.
Provides: StarField, ParticleSystem, Nebula
"""

import pygame
import random
import math
import numpy as np


# ─────────────────────────────────────────────
#  Colour helpers
# ─────────────────────────────────────────────

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))


# ─────────────────────────────────────────────
#  Individual Particle
# ─────────────────────────────────────────────

class Particle:
    __slots__ = ('x','y','vx','vy','life','max_life','size','color','glow','fade')

    def __init__(self, x, y, vx, vy, life, size, color, glow=True, fade=True):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.life = float(life)
        self.max_life = float(life)
        self.size = float(size)
        self.color = color
        self.glow = glow
        self.fade = fade

    def update(self, dt):
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        self.vy += 10 * dt   # slight gravity
        self.life -= dt
        return self.life > 0

    @property
    def alpha(self):
        ratio = self.life / self.max_life
        return clamp(ratio * 255) if self.fade else 255

    @property
    def radius(self):
        ratio = self.life / self.max_life
        return max(1, self.size * ratio)

    def draw(self, surf):
        r = int(self.radius)
        if r < 1:
            return
        a = self.alpha
        col = tuple(clamp(c) for c in self.color)

        # Glow: draw circle on a temp surface with per-pixel alpha
        if self.glow and r > 2:
            glow_surf = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
            for i in range(3, 0, -1):
                ga = clamp(a * (0.15 * i))
                gc = (*col, ga)
                pygame.draw.circle(glow_surf, gc, (r*2, r*2), r * i)
            surf.blit(glow_surf, (int(self.x) - r*2, int(self.y) - r*2),
                      special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surf, (*col, a), (int(self.x), int(self.y)), r)


# ─────────────────────────────────────────────
#  Particle System
# ─────────────────────────────────────────────

class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surf):
        for p in self.particles:
            p.draw(surf)

    # ── Emitters ──────────────────────────────

    def explode(self, x, y, color=(255, 120, 20), count=60, speed=220):
        """Enemy / object explosion."""
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            spd   = random.uniform(40, speed)
            vx    = math.cos(angle) * spd
            vy    = math.sin(angle) * spd
            col   = lerp_color(color, (255, 255, 200), random.random() * 0.5)
            self.particles.append(Particle(
                x, y, vx, vy,
                life=random.uniform(0.4, 1.0),
                size=random.uniform(2, 7),
                color=col, glow=True,
            ))

    def thruster(self, x, y, count=4):
        """Ship engine exhaust – emitted every frame."""
        for _ in range(count):
            vx = random.uniform(-25, 25)
            vy = random.uniform(60, 140)
            col = random.choice([
                (80, 180, 255), (120, 220, 255), (200, 240, 255),
            ])
            self.particles.append(Particle(
                x, y, vx, vy,
                life=random.uniform(0.15, 0.40),
                size=random.uniform(1.5, 4),
                color=col, glow=True, fade=True,
            ))

    def shield_ripple(self, x, y, radius=40, count=20, color=(80, 160, 255)):
        """Shield activation burst."""
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            spd   = random.uniform(radius * 0.6, radius * 1.2)
            vx    = math.cos(angle) * spd
            vy    = math.sin(angle) * spd
            self.particles.append(Particle(
                x, y, vx, vy,
                life=random.uniform(0.3, 0.7),
                size=random.uniform(2, 5),
                color=color, glow=True,
            ))

    def mega_blast(self, x, y, screen_w, screen_h, count=120):
        """Mega blast shockwave – radiate from ship outward."""
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            spd   = random.uniform(200, 500)
            vx    = math.cos(angle) * spd
            vy    = math.sin(angle) * spd
            col   = random.choice([
                (255, 60, 200), (160, 0, 255), (255, 200, 0),
            ])
            self.particles.append(Particle(
                x, y, vx, vy,
                life=random.uniform(0.5, 1.2),
                size=random.uniform(3, 10),
                color=col, glow=True,
            ))

    def pickup_sparkle(self, x, y, color=(0, 255, 180), count=15):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            spd   = random.uniform(30, 100)
            vx    = math.cos(angle) * spd
            vy    = math.sin(angle) * spd
            self.particles.append(Particle(
                x, y, vx, vy,
                life=random.uniform(0.3, 0.6),
                size=random.uniform(2, 5),
                color=color, glow=True,
            ))

    def hit_spark(self, x, y, count=12):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            spd   = random.uniform(60, 160)
            vx    = math.cos(angle) * spd
            vy    = math.sin(angle) * spd
            col   = random.choice([(255,255,100),(255,200,60),(255,100,30)])
            self.particles.append(Particle(
                x, y, vx, vy,
                life=random.uniform(0.1, 0.3),
                size=random.uniform(1, 3),
                color=col, glow=False,
            ))


# ─────────────────────────────────────────────
#  Parallax Star Field
# ─────────────────────────────────────────────

class StarField:
    """Three-layer parallax star background."""

    def __init__(self, width, height, count=200):
        self.width  = width
        self.height = height
        self.stars  = []
        self._generate(count)

    def _generate(self, count):
        for _ in range(count):
            layer  = random.randint(0, 2)          # 0=near,1=mid,2=far
            x      = random.uniform(0, self.width)
            y      = random.uniform(0, self.height)
            speed  = [80, 40, 15][layer]
            size   = [2.5, 1.5, 0.8][layer]
            bright = [220, 160, 100][layer]
            col    = (bright, bright, bright)
            self.stars.append([x, y, speed, size, col])

    def update(self, dt):
        for s in self.stars:
            s[1] += s[2] * dt
            if s[1] > self.height:
                s[1] = 0
                s[0] = random.uniform(0, self.width)

    def draw(self, surf):
        for s in self.stars:
            x, y, _, size, col = s
            r = max(1, int(size))
            if r <= 1:
                surf.set_at((int(x), int(y)), col)
            else:
                pygame.draw.circle(surf, col, (int(x), int(y)), r)


# ─────────────────────────────────────────────
#  Nebula Background (procedural)
# ─────────────────────────────────────────────

class Nebula:
    """Procedural colourful nebula blobs drawn once to a cached surface."""

    PALETTES = [
        [(80, 0, 120), (40, 0, 80)],
        [(0, 40, 100), (0, 20, 60)],
        [(100, 30, 0), (60, 10, 0)],
    ]

    def __init__(self, width, height):
        self.surf = pygame.Surface((width, height), pygame.SRCALPHA)
        self._generate(width, height)

    def _generate(self, w, h):
        palette = random.choice(self.PALETTES)
        for _ in range(8):
            x  = random.randint(0, w)
            y  = random.randint(0, h)
            rx = random.randint(80, 260)
            ry = random.randint(60, 200)
            col = random.choice(palette)
            blob = pygame.Surface((rx*2, ry*2), pygame.SRCALPHA)
            for step in range(6, 0, -1):
                alpha = int(18 * (7 - step))
                c = (*col, alpha)
                pygame.draw.ellipse(blob, c,
                    (rx - rx*step//6, ry - ry*step//6,
                     rx*2*step//6,    ry*2*step//6))
            self.surf.blit(blob, (x - rx, y - ry),
                           special_flags=pygame.BLEND_RGBA_ADD)

    def draw(self, surf):
        surf.blit(self.surf, (0, 0))
