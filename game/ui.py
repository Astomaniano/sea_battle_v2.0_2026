import pygame

# ---------------------------
# Config
# ---------------------------
GRID_SIZE = 10
CELL_SIZE = 30
BOARD_SIZE = GRID_SIZE * CELL_SIZE
MARGIN = 20
GAP = 40
TOP = 80

SCREEN_WIDTH = MARGIN * 2 + BOARD_SIZE * 2 + GAP
SCREEN_HEIGHT = TOP + BOARD_SIZE + MARGIN + 140
FPS = 60

RECORDS_FILE = "records.json"

WHITE = (17, 18, 22)
BLACK = (228, 231, 236)
GRAY = (56, 59, 66)
LIGHT_GRAY = (44, 47, 54)
BLUE = (98, 150, 232)
RED = (208, 84, 84)
GREEN = (110, 196, 140)
SHIP_GREEN = (124, 188, 148)
DARK = (96, 102, 114)
BG_LEFT = (31, 32, 36)
BG_RIGHT = (19, 20, 24)
BG_DIVIDER = (44, 46, 52)


class Button:
    def __init__(self, rect, text, font, bg=GRAY, fg=BLACK):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.bg = bg
        self.fg = fg

    def draw(self, surface, mouse_pos):
        color = self.bg
        if self.rect.collidepoint(mouse_pos):
            color = LIGHT_GRAY
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, DARK, self.rect, 2, border_radius=8)
        text_surf = self.font.render(self.text, True, self.fg)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

