import random

import cv2
import numpy as np
import pygame


WIDTH, HEIGHT = 1100, 700
BG = (18, 24, 38)
WHITE = (245, 247, 250)
MUTED = (165, 175, 192)
BLUE = (56, 155, 255)
RED = (255, 91, 91)
GREEN = (69, 205, 139)
YELLOW = (255, 208, 92)
DARK = (31, 40, 58)


class BoxingGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("AI BOXING - PVE / PVP")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("arial", 18)
        self.font = pygame.font.SysFont("arial", 24, bold=True)
        self.font_big = pygame.font.SysFont("arial", 42, bold=True)
        self.font_title = pygame.font.SysFont("arial", 56, bold=True)
        self.mode = None
        self.difficulty = "normal"
        self.reset()

    def reset(self):
        self.players = [
            {"name": "PLAYER 1", "color": BLUE, "health": 100,
             "attack_timer": 0.0, "hit_flash": 0.0, "cooldown": 0.0,
             "guard": False, "message": "", "message_timer": 0.0},
            {"name": "PLAYER 2", "color": RED, "health": 100,
             "attack_timer": 0.0, "hit_flash": 0.0, "cooldown": 0.0,
             "guard": False, "message": "", "message_timer": 0.0},
        ]
        if self.mode == "pve":
            self.players[1]["name"] = "BOXING BOT"
        self.round_seconds = 90.0
        self.game_over = False
        self.winner_text = ""
        self.bot_action_timer = 1.5
        self.bot_guard_timer = 0.0

    def start(self, mode, difficulty=None):
        self.mode = mode
        if difficulty:
            self.difficulty = difficulty
        self.reset()

    def back_to_menu(self):
        self.mode = None
        self.reset()

    def set_difficulty(self, difficulty):
        if difficulty in ("easy", "normal", "hard"):
            self.difficulty = difficulty

    def keyboard_punch(self, player_index):
        if self.mode is not None and not self.game_over and player_index in (0, 1):
            if self.mode == "pve" and player_index == 1:
                return
            self._apply_punch(player_index)

    def _apply_punch(self, attacker_index, base_damage=10):
        attacker = self.players[attacker_index]
        defender = self.players[1 - attacker_index]
        if attacker["cooldown"] > 0 or defender["health"] <= 0:
            return

        attacker["attack_timer"] = 0.26
        attacker["cooldown"] = 0.48
        damage = 2 if defender["guard"] else base_damage
        defender["health"] = max(0, defender["health"] - damage)
        defender["hit_flash"] = 0.22
        defender["message"] = "BLOCK!" if defender["guard"] else f"-{damage} HP"
        defender["message_timer"] = 0.55

    def _update_bot(self, dt):
        bot = self.players[1]
        bot["guard"] = self.bot_guard_timer > 0
        self.bot_guard_timer = max(0.0, self.bot_guard_timer - dt)
        self.bot_action_timer -= dt

        settings = {
            "easy":   {"interval": (2.8, 4.0), "damage": 6,  "guard": 0.18},
            "normal": {"interval": (1.8, 2.8), "damage": 9,  "guard": 0.35},
            "hard":   {"interval": (1.0, 1.8), "damage": 12, "guard": 0.52},
        }
        cfg = settings[self.difficulty]

        if self.bot_action_timer <= 0:
            if random.random() < cfg["guard"]:
                self.bot_guard_timer = random.uniform(0.65, 1.15)
                bot["guard"] = True
                bot["message"] = "GUARD!"
                bot["message_timer"] = 0.45
                self.bot_action_timer = random.uniform(0.8, 1.5)
            else:
                self._apply_punch(1, base_damage=cfg["damage"])
                self.bot_action_timer = random.uniform(*cfg["interval"])

    def update(self, dt, gestures):
        if self.mode is None or self.game_over:
            return

        self.round_seconds = max(0.0, self.round_seconds - dt)
        for player in self.players:
            player["attack_timer"] = max(0.0, player["attack_timer"] - dt)
            player["hit_flash"] = max(0.0, player["hit_flash"] - dt)
            player["cooldown"] = max(0.0, player["cooldown"] - dt)
            player["message_timer"] = max(0.0, player["message_timer"] - dt)

        self.players[0]["guard"] = bool(gestures[0].get("guard", False))
        if self.mode == "pvp":
            self.players[1]["guard"] = bool(gestures[1].get("guard", False))
        else:
            self._update_bot(dt)

        if gestures[0].get("punch", False):
            self._apply_punch(0)
        if self.mode == "pvp" and gestures[1].get("punch", False):
            self._apply_punch(1)

        if self.players[0]["health"] <= 0:
            self.game_over = True
            self.winner_text = "PLAYER 2 WINS!" if self.mode == "pvp" else "BOT WINS!"
        elif self.players[1]["health"] <= 0:
            self.game_over = True
            self.winner_text = "PLAYER 1 WINS!"
        elif self.round_seconds <= 0:
            hp1, hp2 = self.players[0]["health"], self.players[1]["health"]
            if hp1 > hp2:
                self.winner_text = "PLAYER 1 WINS!"
            elif hp2 > hp1:
                self.winner_text = "PLAYER 2 WINS!" if self.mode == "pvp" else "BOT WINS!"
            else:
                self.winner_text = "DRAW!"
            self.game_over = True

    def _text(self, text, x, y, font=None, color=WHITE, center=False):
        surface = (font or self.font).render(str(text), True, color)
        rect = surface.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(surface, rect)

    def _draw_health_bar(self, x, y, player, width=390):
        pygame.draw.rect(self.screen, (55, 64, 82), (x, y, width, 24), border_radius=8)
        fill_width = int(width * max(0, player["health"]) / 100)
        if fill_width:
            pygame.draw.rect(self.screen, player["color"], (x, y, fill_width, 24), border_radius=8)
        pygame.draw.rect(self.screen, WHITE, (x, y, width, 24), 2, border_radius=8)
        self._text(f'{player["health"]:3d} HP', x + width - 75, y + 29, self.font_small)

    def _draw_ring(self):
        pygame.draw.rect(self.screen, (42, 52, 73), (75, 300, 950, 315), border_radius=22)
        pygame.draw.rect(self.screen, (225, 230, 240), (95, 320, 910, 275), 5)
        for y, color in [(375, (220, 70, 80)), (430, (230, 230, 240)), (485, (65, 140, 235))]:
            pygame.draw.line(self.screen, color, (95, y), (1005, y), 7)
        pygame.draw.rect(self.screen, (30, 37, 53), (95, 510, 910, 85))
        pygame.draw.line(self.screen, (90, 105, 130), (550, 320), (550, 595), 2)

    def _draw_fighter(self, x, base_y, player, facing):
        color = YELLOW if player["hit_flash"] > 0 else player["color"]
        dark = tuple(max(0, c - 65) for c in color)
        pygame.draw.circle(self.screen, (232, 190, 153), (x, base_y - 174), 31)
        pygame.draw.arc(self.screen, (45, 35, 35), (x - 31, base_y - 205, 62, 48), 0.1, 3.0, 7)
        pygame.draw.polygon(self.screen, dark, [
            (x - 39, base_y - 143), (x + 39, base_y - 143),
            (x + 48, base_y - 65), (x - 48, base_y - 65)
        ])
        pygame.draw.polygon(self.screen, color, [
            (x - 30, base_y - 137), (x + 30, base_y - 137),
            (x + 34, base_y - 75), (x - 34, base_y - 75)
        ])
        pygame.draw.line(self.screen, (35, 40, 55), (x - 32, base_y - 70), (x - 48, base_y - 12), 17)
        pygame.draw.line(self.screen, (35, 40, 55), (x + 32, base_y - 70), (x + 48, base_y - 12), 17)

        direction = facing
        shoulder_front = (x + direction * 29, base_y - 130)
        shoulder_back = (x - direction * 29, base_y - 130)
        if player["attack_timer"] > 0:
            elbow_front = (x + direction * 80, base_y - 122)
            glove_front = (x + direction * 142, base_y - 119)
        else:
            elbow_front = (x + direction * 57, base_y - 105)
            glove_front = (x + direction * 38, base_y - 91)
        elbow_back = (x - direction * 52, base_y - 104)
        glove_back = (x - direction * 30, base_y - 91)

        for shoulder, elbow, glove in (
            (shoulder_front, elbow_front, glove_front),
            (shoulder_back, elbow_back, glove_back),
        ):
            pygame.draw.line(self.screen, (232, 190, 153), shoulder, elbow, 17)
            pygame.draw.line(self.screen, (232, 190, 153), elbow, glove, 15)
            pygame.draw.circle(self.screen, color, glove, 18)
            pygame.draw.circle(self.screen, WHITE, glove, 18, 2)

        pygame.draw.rect(self.screen, WHITE, (x - 42, base_y - 72, 84, 13), border_radius=4)
        if player["guard"]:
            self._text("GUARD", x, base_y - 238, self.font_small, GREEN, center=True)
        elif player["attack_timer"] > 0:
            self._text("PUNCH!", x, base_y - 238, self.font_small, YELLOW, center=True)
        if player["message_timer"] > 0:
            self._text(player["message"], x, base_y - 270, self.font, YELLOW, center=True)
        self._text(player["name"], x, base_y + 8, self.font_small, WHITE, center=True)

    def _draw_camera(self, camera_frame, people):
        x, y, w, h = WIDTH - 285, 95, 260, 195
        pygame.draw.rect(self.screen, (8, 12, 20), (x - 4, y - 4, w + 8, h + 8), border_radius=8)
        pygame.draw.rect(self.screen, WHITE, (x - 4, y - 4, w + 8, h + 8), 2, border_radius=8)
        if camera_frame is not None:
            small = cv2.resize(camera_frame, (w, h))
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            surface = pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))
            self.screen.blit(surface, (x, y))
        else:
            pygame.draw.rect(self.screen, DARK, (x, y, w, h))
            self._text("NO CAMERA", x + w // 2, y + h // 2, self.font_small, WHITE, center=True)
        count = sum(1 for p in people if p is not None)
        expected = 1 if self.mode == "pve" else 2
        self._text(f"POSE TRACKING: {count}/{expected}", x, y + h + 8, self.font_small,
                   GREEN if count == expected else YELLOW)

    def _draw_menu(self, camera_frame, people):
        self.screen.fill(BG)
        self._text("AI BOXING", WIDTH // 2, 115, self.font_title, WHITE, center=True)
        self._text("CHOOSE YOUR GAME MODE", WIDTH // 2, 180, self.font, MUTED, center=True)

        pygame.draw.rect(self.screen, (35, 75, 115), (145, 245, 365, 175), border_radius=18)
        pygame.draw.rect(self.screen, BLUE, (145, 245, 365, 175), 3, border_radius=18)
        self._text("1  -  PVE", 327, 295, self.font_big, WHITE, center=True)
        self._text("Fight against AI Bot", 327, 350, self.font, WHITE, center=True)

        pygame.draw.rect(self.screen, (105, 43, 53), (590, 245, 365, 175), border_radius=18)
        pygame.draw.rect(self.screen, RED, (590, 245, 365, 175), 3, border_radius=18)
        self._text("2  -  PVP", 772, 295, self.font_big, WHITE, center=True)
        self._text("Player versus Player", 772, 350, self.font, WHITE, center=True)

        self._text("BOT DIFFICULTY", WIDTH // 2, 480, self.font, MUTED, center=True)
        choices = [("E", "EASY"), ("N", "NORMAL"), ("H", "HARD")]
        start_x = WIDTH // 2 - 190
        for i, (key, label) in enumerate(choices):
            selected = self.difficulty == label.lower()
            self._text(f"{key}  {label}", start_x + i * 190, 530, self.font,
                       GREEN if selected else MUTED, center=True)

        self._text("ESC: quit  |  Difficulty applies to PVE mode", WIDTH // 2, 635,
                   self.font_small, MUTED, center=True)
        self._draw_camera(camera_frame, people)
        pygame.display.flip()

    def draw(self, camera_frame, people):
        if self.mode is None:
            self._draw_menu(camera_frame, people)
            return

        self.screen.fill(BG)
        self._text("AI BOXING", WIDTH // 2, 34, self.font_title, WHITE, center=True)
        mode_label = "PLAYER VS BOT" if self.mode == "pve" else "PLAYER VS PLAYER"
        suffix = self.difficulty.upper() if self.mode == "pve" else "LOCAL MATCH"
        self._text(f"{mode_label}  |  {suffix}", WIDTH // 2, 78,
                   self.font_small, MUTED, center=True)

        self._text(self.players[0]["name"], 75, 112, self.font, BLUE)
        self._draw_health_bar(75, 145, self.players[0], 390)
        self._text(self.players[1]["name"], 600, 112, self.font, RED)
        self._draw_health_bar(600, 145, self.players[1], 390)
        timer_text = f"{int(self.round_seconds // 60):02d}:{int(self.round_seconds % 60):02d}"
        self._text(timer_text, WIDTH // 2, 165, self.font_big, YELLOW, center=True)

        self._draw_ring()
        self._draw_fighter(340, 575, self.players[0], facing=1)
        self._draw_fighter(760, 575, self.players[1], facing=-1)
        self._draw_camera(camera_frame, people)

        controls = "P1: stand left  |  R: restart  |  M: menu  |  ESC: quit"
        if self.mode == "pvp":
            controls = "P1: left  |  P2: right  |  R: restart  |  M: menu  |  ESC: quit"
        self._text(controls, WIDTH // 2, 665, self.font_small, MUTED, center=True)

        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            self.screen.blit(overlay, (0, 0))
            self._text(self.winner_text, WIDTH // 2, HEIGHT // 2 - 25,
                       self.font_title, YELLOW, center=True)
            self._text("Press R to rematch  |  M for menu  |  ESC to exit",
                       WIDTH // 2, HEIGHT // 2 + 38, self.font, WHITE, center=True)
        pygame.display.flip()

    def close(self):
        pygame.quit()
