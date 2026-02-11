import io
import math
import os
import random
import struct
import sys
import time
import wave

import pygame

try:
    from .ai import Player, AIPlayer
    from .scores import ScoreManager
    from .ui import (
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        FPS,
        MARGIN,
        GAP,
        TOP,
        BOARD_SIZE,
        GRID_SIZE,
        CELL_SIZE,
        WHITE,
        BLACK,
        LIGHT_GRAY,
        DARK,
        GRAY,
        BLUE,
        RED,
        GREEN,
        SHIP_GREEN,
        BG_LEFT,
        BG_RIGHT,
        BG_DIVIDER,
        RECORDS_FILE,
        Button,
    )
except ImportError:
    # Allow running this file directly: python game/core.py
    this_dir = os.path.dirname(__file__)
    if this_dir not in sys.path:
        sys.path.insert(0, this_dir)

    from ai import Player, AIPlayer
    from scores import ScoreManager
    from ui import (
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        FPS,
        MARGIN,
        GAP,
        TOP,
        BOARD_SIZE,
        GRID_SIZE,
        CELL_SIZE,
        WHITE,
        BLACK,
        LIGHT_GRAY,
        DARK,
        GRAY,
        BLUE,
        RED,
        GREEN,
        SHIP_GREEN,
        BG_LEFT,
        BG_RIGHT,
        BG_DIVIDER,
        RECORDS_FILE,
        Button,
    )


class SimpleSounds:
    def __init__(self):
        self.enabled = False
        self.sfx = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(44100, -16, 1, 512)
            self.enabled = True
            self.sfx = {
                "click": self._tone(720, 0.04, 0.18),
                "coin": self._tone(960, 0.10, 0.20),
                "miss": self._tone(260, 0.12, 0.20),
                "hit": self._tone(820, 0.10, 0.24),
                "sunk": self._sweep(700, 1020, 0.18, 0.26),
                "win": self._sweep(420, 1120, 0.32, 0.26),
                "lose": self._sweep(580, 180, 0.35, 0.24),
                "save": self._tone(520, 0.08, 0.22),
            }
        except pygame.error:
            self.enabled = False
            self.sfx = {}

    def play(self, name):
        if not self.enabled:
            return
        snd = self.sfx.get(name)
        if snd is not None:
            snd.play()

    def _tone(self, freq, duration, volume):
        return self._build_sound(duration, volume, lambda t, _: math.sin(2.0 * math.pi * freq * t))

    def _sweep(self, f0, f1, duration, volume):
        def wave_fn(t, ratio):
            cur = f0 + (f1 - f0) * ratio
            return math.sin(2.0 * math.pi * cur * t)

        return self._build_sound(duration, volume, wave_fn)

    def _build_sound(self, duration, volume, wave_fn):
        sample_rate = 44100
        samples = max(1, int(sample_rate * duration))
        attack = max(1, int(samples * 0.08))
        release = max(1, int(samples * 0.12))

        frames = bytearray()
        for i in range(samples):
            t = i / sample_rate
            ratio = i / samples
            amp = wave_fn(t, ratio)
            env = 1.0
            if i < attack:
                env = i / attack
            elif i > samples - release:
                env = max(0.0, (samples - i) / release)
            val = int(32767 * volume * env * amp)
            frames.extend(struct.pack("<h", val))

        with io.BytesIO() as buff:
            with wave.open(buff, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(frames)
            buff.seek(0)
            return pygame.mixer.Sound(file=buff)


class Game:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Морской бой")
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.SysFont("arial", 18)
        self.title_font = pygame.font.SysFont("arial", 40, bold=True)
        self.timer_font = pygame.font.SysFont("arial", 28, bold=True)

        self.score_manager = ScoreManager(RECORDS_FILE)
        self.sounds = SimpleSounds()

        self.state = "menu"
        self.player = Player()
        self.ai = AIPlayer()

        self.current_turn = "player"
        self.coin_result = None
        self.coin_time = None

        self.start_time = None
        self.end_time = None
        self.name_input = ""
        self.saved = False

        self.ai_next_action = 0.0
        self.player_won = False

        self.shot_anim = None
        self.anim_duration = 0.35
        self.ai_think_delay = 1.0

        self.scores_scroll = 0
        self.max_name_len = 20
        self.name_limit_warning_until = 0.0

    def reset_game(self):
        self.player = Player()
        self.ai = AIPlayer()
        self.player.board.place_ships_auto()
        self.ai.board.place_ships_auto()

        self.current_turn = "player"
        self.coin_result = None
        self.coin_time = None

        self.start_time = None
        self.end_time = None
        self.name_input = ""
        self.saved = False

        self.ai_next_action = 0.0
        self.player_won = False
        self.shot_anim = None

        self.scores_scroll = 0
        self.name_limit_warning_until = 0.0

    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if self.state == "menu":
                    running = self.handle_menu(event)
                elif self.state == "coin":
                    self.handle_coin(event)
                elif self.state == "play":
                    self.handle_play(event)
                elif self.state == "scores":
                    self.handle_scores(event)
                elif self.state == "gameover":
                    running = self.handle_gameover(event)

            if self.state == "coin":
                self.update_coin()
            if self.state == "play":
                self.update_play()

            self.draw(mouse_pos)
            pygame.display.flip()

        pygame.quit()

    # ---------- State handlers ----------
    def handle_menu(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.menu_buttons():
                if btn.is_clicked(event):
                    self.sounds.play("click")
                    if btn.text == "Новая игра":
                        self.reset_game()
                        self.state = "coin"
                    elif btn.text == "Рекорды":
                        self.scores_scroll = 0
                        self.state = "scores"
                    elif btn.text == "Выход":
                        return False
        return True

    def handle_coin(self, event):
        if self.coin_result is None and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.coin_buttons():
                if btn.is_clicked(event):
                    self.sounds.play("coin")
                    self.coin_result = random.choice(["player", "ai"])
                    self.current_turn = self.coin_result
                    self.coin_time = time.time()
        return True

    def update_coin(self):
        if self.coin_result is not None and time.time() - self.coin_time > 1.2:
            self.state = "play"
            if self.start_time is None:
                self.start_time = time.time()

    def handle_play(self, event):
        if self.current_turn != "player":
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            target = self.cell_from_click(event.pos, enemy=True)
            if target is None:
                return True
            x, y = target
            result = self.ai.board.shoot(x, y)
            self.start_shot_anim("ai", x, y, result)
            self.play_shot_sound(result)

            if result in ["hit", "sunk"]:
                if self.ai.board.all_sunk():
                    self.game_over(player_won=True)
            elif result == "miss":
                self.current_turn = "ai"
                self.ai_next_action = time.time() + self.ai_think_delay
        return True

    def update_play(self):
        if self.current_turn != "ai":
            return

        if time.time() < self.ai_next_action:
            return

        shot = self.ai.choose_shot(self.player.board)
        if shot is None:
            self.current_turn = "player"
            return

        x, y = shot
        result = self.player.board.shoot(x, y)
        self.start_shot_anim("player", x, y, result)
        self.play_shot_sound(result)

        if result in ["hit", "sunk"]:
            self.ai.process_result((x, y), result, self.player.board)
            if self.player.board.all_sunk():
                self.game_over(player_won=False)
                return
            self.ai_next_action = time.time() + self.ai_think_delay
        else:
            self.current_turn = "player"

    def handle_scores(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self.scores_scroll -= event.y

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                self.scores_scroll -= 1
            elif event.button == 5:
                self.scores_scroll += 1
            elif event.button == 1:
                for btn in self.scores_buttons():
                    if btn.is_clicked(event):
                        self.sounds.play("click")
                        if btn.text == "Назад":
                            self.state = "menu"

        records = self.score_manager.records
        row_h = 32
        list_top = 132
        list_bottom = SCREEN_HEIGHT - 130
        visible = max(1, (list_bottom - list_top) // row_h)
        max_scroll = max(0, len(records) - visible)
        self.scores_scroll = max(0, min(self.scores_scroll, max_scroll))
        return True

    def handle_gameover(self, event):
        if event.type == pygame.KEYDOWN and self.player_won:
            if event.key == pygame.K_BACKSPACE:
                self.name_input = self.name_input[:-1]
            elif event.key == pygame.K_RETURN:
                self.sounds.play("click")
                self.save_result()
            else:
                if event.unicode.isprintable() and event.unicode != "\t":
                    if len(self.name_input) < self.max_name_len:
                        self.name_input += event.unicode
                    else:
                        self.name_limit_warning_until = time.time() + 1.6

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.player_won and self.gameover_ok_button().is_clicked(event):
                self.sounds.play("click")
                self.save_result()
                return True

            for btn in self.gameover_buttons():
                if btn.is_clicked(event):
                    self.sounds.play("click")
                    if btn.text == "Начать сначала":
                        self.reset_game()
                        self.state = "coin"
                    elif btn.text == "Рекорды":
                        self.scores_scroll = 0
                        self.state = "scores"
                    elif btn.text == "Главное меню":
                        self.state = "menu"
                    elif btn.text == "Выход":
                        return False
        return True

    # ---------- Actions ----------
    def game_over(self, player_won):
        self.player_won = player_won
        self.end_time = time.time()
        self.state = "gameover"
        self.sounds.play("win" if player_won else "lose")

    def play_shot_sound(self, result):
        if result == "miss":
            self.sounds.play("miss")
        elif result == "hit":
            self.sounds.play("hit")
        elif result == "sunk":
            self.sounds.play("sunk")

    def save_result(self):
        if not self.player_won or self.saved:
            return
        name = self.name_input.strip()
        if not name:
            return
        elapsed = int(self.end_time - self.start_time)
        self.score_manager.add_record(name, elapsed)
        self.saved = True
        self.sounds.play("save")

    # ---------- Drawing ----------
    def draw(self, mouse_pos):
        self.draw_background(play_state=self.state == "play")

        if self.state == "menu":
            self.draw_menu(mouse_pos)
        elif self.state == "coin":
            self.draw_coin(mouse_pos)
        elif self.state == "play":
            self.draw_play(mouse_pos)
        elif self.state == "scores":
            self.draw_scores(mouse_pos)
        elif self.state == "gameover":
            self.draw_gameover(mouse_pos)

    def draw_background(self, play_state=False):
        if play_state:
            self.screen.fill(BG_RIGHT)
            left_width = SCREEN_WIDTH // 2
            pygame.draw.rect(self.screen, BG_LEFT, (0, 0, left_width, SCREEN_HEIGHT))
            divider_x = left_width
            pygame.draw.line(self.screen, BG_DIVIDER, (divider_x, 0), (divider_x, SCREEN_HEIGHT), 2)
            pygame.draw.line(self.screen, (24, 25, 29), (divider_x - 2, 0), (divider_x - 2, SCREEN_HEIGHT), 1)
            pygame.draw.line(self.screen, (14, 15, 18), (divider_x + 2, 0), (divider_x + 2, SCREEN_HEIGHT), 1)
            return

        side_width = SCREEN_WIDTH // 4
        center_width = SCREEN_WIDTH // 2
        self.screen.fill(BG_LEFT)
        pygame.draw.rect(self.screen, BG_RIGHT, (side_width, 0, center_width, SCREEN_HEIGHT))

        left_edge = side_width
        right_edge = side_width + center_width
        pygame.draw.line(self.screen, BG_DIVIDER, (left_edge, 0), (left_edge, SCREEN_HEIGHT), 2)
        pygame.draw.line(self.screen, BG_DIVIDER, (right_edge, 0), (right_edge, SCREEN_HEIGHT), 2)
        pygame.draw.line(self.screen, (24, 25, 29), (left_edge - 2, 0), (left_edge - 2, SCREEN_HEIGHT), 1)
        pygame.draw.line(self.screen, (24, 25, 29), (right_edge + 2, 0), (right_edge + 2, SCREEN_HEIGHT), 1)

    def draw_menu(self, mouse_pos):
        title = self.title_font.render("Морской бой", True, BLACK)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 40)))
        for btn in self.menu_buttons():
            btn.draw(self.screen, mouse_pos)

    def draw_coin(self, mouse_pos):
        title = self.title_font.render("Бросок монетки", True, BLACK)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 40)))
        if self.coin_result is None:
            for btn in self.coin_buttons():
                btn.draw(self.screen, mouse_pos)
        else:
            result_text = "Орёл — первым ходит игрок" if self.coin_result == "player" else "Решка — первым ходит компьютер"
            text = self.font.render(result_text, True, BLACK)
            self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 140)))
            pygame.draw.circle(self.screen, BLUE, (SCREEN_WIDTH // 2, 220), 50)

    def draw_play(self, mouse_pos):
        elapsed = int((self.end_time or time.time()) - self.start_time) if self.start_time else 0
        timer = self.timer_font.render(f"{elapsed // 60:02d}:{elapsed % 60:02d}", True, BLACK)
        self.screen.blit(timer, timer.get_rect(center=(SCREEN_WIDTH // 2, 40)))

        self.draw_board(self.player.board, MARGIN, TOP, show_ships=True)
        self.draw_board(self.ai.board, MARGIN + BOARD_SIZE + GAP, TOP, show_ships=False)

        label_player = self.font.render("Игрок", True, BLACK)
        label_ai = self.font.render("Компьютер", True, BLACK)
        self.screen.blit(label_player, (MARGIN, TOP - 30))
        self.screen.blit(label_ai, (MARGIN + BOARD_SIZE + GAP, TOP - 30))

        status_y = TOP + BOARD_SIZE + 40
        self.draw_fleet_status(self.player.board, MARGIN, status_y, "Ваши корабли")
        self.draw_fleet_status(self.ai.board, MARGIN + BOARD_SIZE + GAP, status_y, "Корабли врага")

    def draw_scores(self, mouse_pos):
        title = self.title_font.render("Рекорды", True, BLACK)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 68)))

        center_left = SCREEN_WIDTH // 4
        center_width = SCREEN_WIDTH // 2
        table_x = center_left + 24
        table_w = center_width - 48

        col_num = table_x + 10
        col_time = table_x + 70
        col_name = table_x + 190

        list_top = 132
        list_bottom = SCREEN_HEIGHT - 130
        row_h = 32

        self.screen.blit(self.small_font.render("№", True, BLACK), (col_num, list_top - 30))
        self.screen.blit(self.small_font.render("Time", True, BLACK), (col_time, list_top - 30))
        self.screen.blit(self.small_font.render("Name", True, BLACK), (col_name, list_top - 30))
        pygame.draw.line(self.screen, DARK, (table_x, list_top - 8), (table_x + table_w, list_top - 8), 1)

        records = self.score_manager.records
        visible = max(1, (list_bottom - list_top) // row_h)
        max_scroll = max(0, len(records) - visible)
        self.scores_scroll = max(0, min(self.scores_scroll, max_scroll))

        if not records:
            text = self.font.render("Пока нет рекордов", True, BLACK)
            self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, list_top + 24)))
        else:
            start = self.scores_scroll
            end = min(len(records), start + visible)
            y = list_top
            for i in range(start, end):
                rec = records[i]
                time_val = rec.get("time") or self.score_manager.format_time(rec.get("seconds", 0))
                name_val = str(rec.get("name", ""))
                self.screen.blit(self.small_font.render(str(i + 1), True, BLACK), (col_num, y))
                self.screen.blit(self.small_font.render(time_val, True, BLACK), (col_time, y))
                self.screen.blit(self.small_font.render(name_val, True, BLACK), (col_name, y))
                y += row_h

            if max_scroll > 0:
                hint = self.small_font.render("Колесо мыши: прокрутка", True, DARK)
                self.screen.blit(hint, (table_x, SCREEN_HEIGHT - 124))

        for btn in self.scores_buttons():
            btn.draw(self.screen, mouse_pos)

    def draw_gameover(self, mouse_pos):
        result = "WINNER" if self.player_won else "LOSER"
        color = GREEN if self.player_won else RED
        title = self.title_font.render(result, True, color)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 68)))

        if self.player_won:
            input_rect = self.gameover_input_rect()
            prompt = self.font.render("Введите имя:", True, BLACK)
            self.screen.blit(prompt, (input_rect.x, 118))

            pygame.draw.rect(self.screen, WHITE, input_rect)
            pygame.draw.rect(self.screen, BLACK, input_rect, 2)
            name_surf = self.font.render(self.name_input, True, BLACK)
            self.screen.blit(name_surf, (input_rect.x + 8, input_rect.y + 6))

            ok_btn = self.gameover_ok_button()
            ok_btn.draw(self.screen, mouse_pos)

            if self.saved:
                saved = self.small_font.render("Результат записан", True, GREEN)
                self.screen.blit(saved, saved.get_rect(midtop=(SCREEN_WIDTH // 2, input_rect.bottom + 8)))

            if time.time() < self.name_limit_warning_until:
                warn = self.small_font.render(f"Лимит имени: {self.max_name_len} символов", True, RED)
                self.screen.blit(warn, warn.get_rect(midtop=(SCREEN_WIDTH // 2, input_rect.bottom + 32)))

        for btn in self.gameover_buttons():
            btn.draw(self.screen, mouse_pos)

    def draw_board(self, board, offset_x, offset_y, show_ships):
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                rect = pygame.Rect(offset_x + x * CELL_SIZE, offset_y + y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(self.screen, LIGHT_GRAY, rect)
                pygame.draw.rect(self.screen, DARK, rect, 1)

                if show_ships and board.grid[y][x] != -1:
                    pygame.draw.rect(self.screen, SHIP_GREEN, rect)

                handled = self.draw_shot_anim(board, x, y, rect)
                if board.shots[y][x] == 1:
                    pygame.draw.circle(self.screen, BLUE, rect.center, 4)
                elif board.shots[y][x] == 2 and not handled:
                    pygame.draw.rect(self.screen, RED, rect)

    def remaining_counts(self, board):
        counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for ship in board.ships:
            if not ship.is_sunk():
                size = len(ship.cells)
                if size in counts:
                    counts[size] += 1
        return counts

    def start_shot_anim(self, target, x, y, result):
        self.shot_anim = {
            "target": target,
            "x": x,
            "y": y,
            "result": result,
            "start": time.time(),
        }

    def draw_shot_anim(self, board, x, y, rect):
        if not self.shot_anim:
            return False

        target_board = self.player.board if self.shot_anim["target"] == "player" else self.ai.board
        if board is not target_board:
            return False
        if self.shot_anim["x"] != x or self.shot_anim["y"] != y:
            return False

        elapsed = time.time() - self.shot_anim["start"]
        if elapsed > self.anim_duration:
            self.shot_anim = None
            return False

        t = elapsed / self.anim_duration
        if self.shot_anim["result"] in ["hit", "sunk"]:
            radius = max(2, int((CELL_SIZE / 2 - 1) * t))
            pygame.draw.circle(self.screen, RED, rect.center, radius)
        else:
            radius = int(4 + (CELL_SIZE / 2 - 4) * (1 - t))
            pygame.draw.circle(self.screen, BLUE, rect.center, max(3, radius), 2)
        return True

    def draw_fleet_status(self, board, offset_x, y, label):
        label_surf = self.small_font.render(label, True, BLACK)
        self.screen.blit(label_surf, (offset_x, y - 22))

        counts = self.remaining_counts(board)
        sizes = [4, 3, 2, 1]
        cell = max(10, CELL_SIZE // 2)
        row_h = cell + 8

        row_index = 0
        for size in sizes:
            if counts[size] <= 0:
                continue
            row_y = y + row_index * row_h
            row_index += 1

            rect = pygame.Rect(offset_x, row_y, cell * size, cell)
            pygame.draw.rect(self.screen, SHIP_GREEN, rect)
            pygame.draw.rect(self.screen, DARK, rect, 1)
            for i in range(1, size):
                x = offset_x + i * cell
                pygame.draw.line(self.screen, DARK, (x, row_y), (x, row_y + cell), 1)

            count_text = self.small_font.render(f"={counts[size]}", True, BLACK)
            self.screen.blit(count_text, (offset_x + cell * size + 8, row_y + 1))

    # ---------- UI helpers ----------
    def _distributed_buttons(self, labels, y_start, y_end, width=280, height=50):
        if not labels:
            return []
        total_h = len(labels) * height
        free_h = max(0, y_end - y_start - total_h)
        gap = free_h // (len(labels) - 1) if len(labels) > 1 else 0

        x = SCREEN_WIDTH // 2 - width // 2
        out = []
        for i, label in enumerate(labels):
            y = y_start + i * (height + gap)
            out.append(Button((x, y, width, height), label, self.font))
        return out

    def menu_buttons(self):
        return self._distributed_buttons(["Новая игра", "Рекорды", "Выход"], y_start=170, y_end=430, width=280)

    def coin_buttons(self):
        return self._distributed_buttons(["Бросить монетку"], y_start=230, y_end=320, width=300)

    def scores_buttons(self):
        return self._distributed_buttons(["Назад"], y_start=470, y_end=530, width=240)

    def gameover_input_rect(self):
        center_left = SCREEN_WIDTH // 4
        center_right = center_left + SCREEN_WIDTH // 2

        input_w = 220
        ok_w = 52
        gap = 8
        total_w = input_w + gap + ok_w

        start_x = center_left + (center_right - center_left - total_w) // 2
        return pygame.Rect(start_x, 148, input_w, 42)

    def gameover_ok_button(self):
        r = self.gameover_input_rect()
        return Button((r.right + 8, r.y, 52, r.height), "OK", self.small_font, bg=SHIP_GREEN, fg=BG_RIGHT)

    def gameover_buttons(self):
        labels = ["Начать сначала", "Рекорды", "Главное меню", "Выход"]
        y_start = 250 if self.player_won else 190
        return self._distributed_buttons(labels, y_start=y_start, y_end=500, width=320)

    def cell_from_click(self, pos, enemy):
        offset_x = MARGIN + BOARD_SIZE + GAP if enemy else MARGIN
        offset_y = TOP
        x, y = pos
        if not (offset_x <= x < offset_x + BOARD_SIZE and offset_y <= y < offset_y + BOARD_SIZE):
            return None
        gx = (x - offset_x) // CELL_SIZE
        gy = (y - offset_y) // CELL_SIZE
        return int(gx), int(gy)


if __name__ == "__main__":
    Game().run()
