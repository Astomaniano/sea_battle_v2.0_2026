import json
import os
import random
import time

import pygame

from .ai import Player, AIPlayer
from .board import Board
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


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Морской бой")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.SysFont("arial", 18)
        self.title_font = pygame.font.SysFont("arial", 40, bold=True)
        self.timer_font = pygame.font.SysFont("arial", 28, bold=True)

        self.score_manager = ScoreManager(RECORDS_FILE)
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

        self.ai_next_action = 0
        self.player_won = False
        self.shot_anim = None
        self.anim_duration = 0.35
        self.ai_think_delay = 1.0

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
        self.ai_next_action = 0
        self.player_won = False
        self.shot_anim = None

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

    # ------------- State Handlers -------------
    def handle_menu(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.menu_buttons():
                if btn.is_clicked(event):
                    if btn.text == "Новая игра":
                        self.reset_game()
                        self.state = "coin"
                    elif btn.text == "Рекорды":
                        self.state = "scores"
                    elif btn.text == "Выход":
                        return False
        return True

    def handle_coin(self, event):
        if self.coin_result is None:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in self.coin_buttons():
                    if btn.is_clicked(event):
                        self.coin_result = random.choice(["player", "ai"])
                        self.current_turn = self.coin_result
                        self.coin_time = time.time()
        return True

    def update_coin(self):
        if self.coin_result is not None:
            if time.time() - self.coin_time > 1.2:
                self.state = "play"
                if self.start_time is None:
                    self.start_time = time.time()

    def handle_play(self, event):
        if self.current_turn != "player":
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            target = self.cell_from_click(event.pos, enemy=True)
            if target:
                x, y = target
                result = self.ai.board.shoot(x, y)
                self.start_shot_anim("ai", x, y, result)
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

        now = time.time()
        if now < self.ai_next_action:
            return

        shot = self.ai.choose_shot(self.player.board)
        if shot is None:
            self.current_turn = "player"
            return
        x, y = shot
        result = self.player.board.shoot(x, y)
        self.start_shot_anim("player", x, y, result)
        if result in ["hit", "sunk"]:
            self.ai.process_result((x, y), result, self.player.board)
            if self.player.board.all_sunk():
                self.game_over(player_won=False)
                return
            self.ai_next_action = time.time() + self.ai_think_delay
        else:
            self.current_turn = "player"

    def handle_scores(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.scores_buttons():
                if btn.is_clicked(event):
                    if btn.text == "Назад":
                        self.state = "menu"
        return True

    def handle_gameover(self, event):
        if event.type == pygame.KEYDOWN and self.player_won:
            if event.key == pygame.K_BACKSPACE:
                self.name_input = self.name_input[:-1]
            elif event.key == pygame.K_RETURN:
                self.save_result()
            else:
                if len(self.name_input) < 12 and event.unicode.isprintable() and event.unicode != "\t":
                    self.name_input += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.gameover_buttons():
                if btn.is_clicked(event):
                    if btn.text == "Сохранить результат":
                        self.save_result()
                    elif btn.text == "Начать сначала":
                        self.reset_game()
                        self.state = "coin"
                    elif btn.text == "Рекорды":
                        self.state = "scores"
                    elif btn.text == "Главное меню":
                        self.state = "menu"
                    elif btn.text == "Выход":
                        return False
        return True

    # ------------- Actions -------------
    def game_over(self, player_won):
        self.player_won = player_won
        self.end_time = time.time()
        self.state = "gameover"

    def save_result(self):
        if not self.player_won or self.saved:
            return
        name = self.name_input.strip()
        if not name:
            return
        elapsed = int(self.end_time - self.start_time)
        self.score_manager.add_record(name, elapsed)
        self.saved = True

    # ------------- Drawing -------------
    def draw(self, mouse_pos):
        self.draw_background()

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

    def draw_background(self):
        self.screen.fill(BG_RIGHT)

        left_width = SCREEN_WIDTH // 2
        pygame.draw.rect(self.screen, BG_LEFT, (0, 0, left_width, SCREEN_HEIGHT))

        divider_x = left_width
        pygame.draw.line(self.screen, BG_DIVIDER, (divider_x, 0), (divider_x, SCREEN_HEIGHT), 2)
        pygame.draw.line(self.screen, (24, 25, 29), (divider_x - 2, 0), (divider_x - 2, SCREEN_HEIGHT), 1)
        pygame.draw.line(self.screen, (14, 15, 18), (divider_x + 2, 0), (divider_x + 2, SCREEN_HEIGHT), 1)
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
        minutes = elapsed // 60
        seconds = elapsed % 60
        timer_title = self.timer_font.render(f"{minutes:02d}:{seconds:02d}", True, BLACK)
        self.screen.blit(timer_title, timer_title.get_rect(center=(SCREEN_WIDTH // 2, 40)))

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
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 40)))

        y = 120
        if not self.score_manager.records:
            text = self.font.render("Пока нет рекордов", True, BLACK)
            self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, y)))
            y += 40
        else:
            for idx, record in enumerate(self.score_manager.records, 1):
                line = f"{idx}. {record['name']} — {record['time']} c"
                text = self.font.render(line, True, BLACK)
                self.screen.blit(text, (SCREEN_WIDTH // 2 - 180, y))
                y += 30

        for btn in self.scores_buttons():
            btn.draw(self.screen, mouse_pos)

    def draw_gameover(self, mouse_pos):
        result = "WINNER" if self.player_won else "LOSER"
        color = GREEN if self.player_won else RED
        title = self.title_font.render(result, True, color)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 40)))

        if self.player_won:
            prompt = self.font.render("Введите имя:", True, BLACK)
            self.screen.blit(prompt, (SCREEN_WIDTH // 2 - 120, 110))
            input_rect = pygame.Rect(SCREEN_WIDTH // 2 - 120, 140, 240, 36)
            pygame.draw.rect(self.screen, WHITE, input_rect)
            pygame.draw.rect(self.screen, BLACK, input_rect, 2)
            name_surf = self.font.render(self.name_input, True, BLACK)
            self.screen.blit(name_surf, (input_rect.x + 8, input_rect.y + 6))
            if self.saved:
                saved_text = self.font.render("Сохранено", True, GREEN)
                self.screen.blit(saved_text, (SCREEN_WIDTH // 2 - 60, 185))

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
        start_x = offset_x
        row_index = 0

        for size in sizes:
            if counts[size] <= 0:
                continue
            row_y = y + row_index * row_h
            row_index += 1
            rect = pygame.Rect(start_x, row_y, cell * size, cell)
            pygame.draw.rect(self.screen, SHIP_GREEN, rect)
            pygame.draw.rect(self.screen, DARK, rect, 1)
            for i in range(1, size):
                divider_x = start_x + i * cell
                pygame.draw.line(self.screen, DARK, (divider_x, row_y), (divider_x, row_y + cell), 1)

            count_text = self.small_font.render(f"={counts[size]}", True, BLACK)
            self.screen.blit(count_text, (start_x + cell * size + 8, row_y + 1))

    # ------------- UI Helpers -------------
    def menu_buttons(self):
        return [
            Button((SCREEN_WIDTH // 2 - 120, 140, 240, 50), "Новая игра", self.font),
            Button((SCREEN_WIDTH // 2 - 120, 210, 240, 50), "Рекорды", self.font),
            Button((SCREEN_WIDTH // 2 - 120, 280, 240, 50), "Выход", self.font),
        ]

    def coin_buttons(self):
        return [Button((SCREEN_WIDTH // 2 - 140, 140, 280, 50), "Бросить монетку", self.font)]

    def scores_buttons(self):
        return [Button((SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT - 90, 240, 50), "Назад", self.font)]

    def gameover_buttons(self):
        buttons = []
        if self.player_won:
            buttons.append(Button((SCREEN_WIDTH // 2 - 160, 220, 320, 50), "Сохранить результат", self.font))
        buttons.append(Button((SCREEN_WIDTH // 2 - 140, 300, 280, 50), "Начать сначала", self.font))
        buttons.append(Button((SCREEN_WIDTH // 2 - 140, 370, 280, 50), "Рекорды", self.font))
        buttons.append(Button((SCREEN_WIDTH // 2 - 140, 440, 280, 50), "Главное меню", self.font))
        buttons.append(Button((SCREEN_WIDTH // 2 - 140, 510, 280, 50), "Выход", self.font))
        return buttons

    def cell_from_click(self, pos, enemy):
        offset_x = MARGIN + BOARD_SIZE + GAP if enemy else MARGIN
        offset_y = TOP
        x, y = pos
        if not (offset_x <= x < offset_x + BOARD_SIZE and offset_y <= y < offset_y + BOARD_SIZE):
            return None
        grid_x = (x - offset_x) // CELL_SIZE
        grid_y = (y - offset_y) // CELL_SIZE
        return int(grid_x), int(grid_y)



