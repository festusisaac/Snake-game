import random
import sys
import pygame
import math

class PygameSnake:
    def __init__(self, grid_size=20, cols=30, rows=30, start_speed=8):
        pygame.init()
        self.grid_size = grid_size
        self.cols = cols
        self.rows = rows
        self.width = cols * grid_size
        self.height = rows * grid_size
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption('Snake (pygame)')
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont(None, 28)
        self.big_font = pygame.font.SysFont(None, 48)

        self.start_speed = start_speed
        self.reset()
        # prepare a head sprite (will be scaled to grid_size)
        self.head_sprite = self.create_head_sprite(self.grid_size)

    def reset(self):
        mid_x = self.cols // 2
        mid_y = self.rows // 2
        self.snake = [(mid_x, mid_y), (mid_x - 1, mid_y), (mid_x - 2, mid_y)]
        self.direction = (1, 0)
        self.spawn_food()
        self.score = 0
        self.game_over = False
        self.paused = False
        self.speed = self.start_speed
        self.move_timer = 0
        # particles are small circles shown when eating food
        self.particles = []
        # segment pixel positions for smooth interpolation
        self.segment_positions = [((x * self.grid_size + self.grid_size // 2), (y * self.grid_size + self.grid_size // 2)) for x, y in self.snake]

    def spawn_food(self):
        empties = [(x, y) for x in range(self.cols) for y in range(self.rows) if (x, y) not in self.snake]
        self.food = random.choice(empties) if empties else None

    def draw_cell(self, pos, color):
        # deprecated: use pixel-based drawing via draw_segment
        x, y = pos
        rect = pygame.Rect(x * self.grid_size, y * self.grid_size, self.grid_size, self.grid_size)
        pygame.draw.rect(self.screen, color, rect)

    def draw(self):
        # subtle vertical gradient background
        for i in range(self.height):
            t = i / self.height
            # dark to slightly lighter
            c = int(12 + 40 * t)
            pygame.draw.line(self.screen, (c, c, c), (0, i), (self.width, i))

        # optional faint grid for a retro look
        grid_col = (18, 18, 18)
        if self.grid_size >= 8:
            for gx in range(0, self.width, self.grid_size):
                pygame.draw.line(self.screen, grid_col, (gx, 0), (gx, self.height))
            for gy in range(0, self.height, self.grid_size):
                pygame.draw.line(self.screen, grid_col, (0, gy), (self.width, gy))

        # draw food with glow
        if self.food:
            fx, fy = self.food
            self.draw_food_glow((fx, fy))

        # snake (draw using interpolated pixel positions)
        for i, seg in enumerate(self.snake):
            px, py = self.segment_positions[i]
            if i == 0:
                # head: rotate sprite
                dx, dy = self.direction
                angle = math.degrees(math.atan2(-dy, dx))
                head_surf = pygame.transform.rotozoom(self.head_sprite, angle, self.grid_size / self.head_sprite.get_width())
                hw, hh = head_surf.get_size()
                self.screen.blit(head_surf, (px - hw // 2, py - hh // 2))
            else:
                color = (30, 160, 30)
                # draw a circle for each body segment
                pygame.draw.circle(self.screen, color, (int(px), int(py)), max(3, self.grid_size // 2 - 1))

        # draw and update particles
        for p in list(self.particles):
            alpha = max(0, min(255, int(255 * (p['life'] / p['max_life']))))
            surf = pygame.Surface((p['r'] * 2, p['r'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p['color'], alpha), (p['r'], p['r']), p['r'])
            self.screen.blit(surf, (p['x'] - p['r'], p['y'] - p['r']))

        # score
        score_surf = self.font.render(f"Score: {self.score}", True, (220, 220, 220))
        self.screen.blit(score_surf, (8, 8))

        if self.paused:
            pause_surf = self.big_font.render("PAUSED", True, (255, 200, 0))
            r = pause_surf.get_rect(center=(self.width // 2, self.height // 2))
            self.screen.blit(pause_surf, r)

        if self.game_over:
            go_surf = self.big_font.render("GAME OVER", True, (220, 50, 50))
            r = go_surf.get_rect(center=(self.width // 2, self.height // 2 - 30))
            self.screen.blit(go_surf, r)
            hint = self.font.render("Space to restart  Esc/Q to quit", True, (200, 200, 200))
            r2 = hint.get_rect(center=(self.width // 2, self.height // 2 + 20))
            self.screen.blit(hint, r2)

        pygame.display.flip()

    def draw_food_glow(self, grid_pos):
        fx, fy = grid_pos
        cx = fx * self.grid_size + self.grid_size // 2
        cy = fy * self.grid_size + self.grid_size // 2
        glow_radius = int(self.grid_size * 1.6)
        surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        for i in range(glow_radius, 0, -1):
            a = int(40 * (i / glow_radius))
            color = (220, 60, 60, a)
            pygame.draw.circle(surf, color, (glow_radius, glow_radius), i)
        self.screen.blit(surf, (cx - glow_radius, cy - glow_radius), special_flags=0)
        # solid food center
        pygame.draw.circle(self.screen, (255, 80, 80), (cx, cy), max(3, self.grid_size // 3))

    def update_particles(self, dt):
        # dt in ms
        for p in list(self.particles):
            p['life'] -= dt
            if p['life'] <= 0:
                self.particles.remove(p)
                continue
            p['x'] += p['vx'] * (dt / 1000.0)
            p['y'] += p['vy'] * (dt / 1000.0)

    def update_segments(self, dt, ms_per_move):
        # compute target pixel positions (cell centers)
        targets = [(x * self.grid_size + self.grid_size // 2, y * self.grid_size + self.grid_size // 2) for x, y in self.snake]

        # keep segment_positions in sync lengthwise
        if len(self.segment_positions) < len(targets):
            # append a copy of last position to avoid pop-in
            if self.segment_positions:
                self.segment_positions.append(self.segment_positions[-1])
            else:
                self.segment_positions = list(targets)
        while len(self.segment_positions) > len(targets):
            self.segment_positions.pop()

        # smoothing factor relative to move interval
        if ms_per_move <= 0:
            alpha = 1.0
        else:
            alpha = min(1.0, (dt / ms_per_move) * 0.9)

        # lerp each segment towards its target
        for i in range(len(targets)):
            tx, ty = targets[i]
            px, py = self.segment_positions[i]
            nx = px + (tx - px) * alpha
            ny = py + (ty - py) * alpha
            self.segment_positions[i] = (nx, ny)

    def step(self):
        if self.game_over or self.paused:
            return

        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        # wall collision
        x, y = new_head
        if x < 0 or x >= self.cols or y < 0 or y >= self.rows:
            self.game_over = True
            return

        # self collision: allow moving into the tail cell because the tail
        # will move away in this step unless we're growing.
        body_to_check = self.snake[:-1] if (not (self.food and new_head == self.food)) else self.snake
        if new_head in body_to_check:
            self.game_over = True
            return

        self.snake.insert(0, new_head)

        if self.food and new_head == self.food:
            self.score += 1
            # speed up gradually
            self.speed = min(25, self.speed + 0.5)
            eaten_pos = self.food
            self.spawn_food()
            self.spawn_eat_particles(eaten_pos)
        else:
            self.snake.pop()
            # keep pixel positions in sync when tail removed
            if len(self.segment_positions) > len(self.snake):
                self.segment_positions.pop()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k in (pygame.K_UP, pygame.K_w):
                if self.direction != (0, 1):
                    self.direction = (0, -1)
            elif k in (pygame.K_DOWN, pygame.K_s):
                if self.direction != (0, -1):
                    self.direction = (0, 1)
            elif k in (pygame.K_LEFT, pygame.K_a):
                if self.direction != (1, 0):
                    self.direction = (-1, 0)
            elif k in (pygame.K_RIGHT, pygame.K_d):
                if self.direction != (-1, 0):
                    self.direction = (1, 0)
            elif k == pygame.K_p:
                self.paused = not self.paused
            elif k in (pygame.K_ESCAPE, pygame.K_q):
                pygame.quit()
                sys.exit()
            elif k == pygame.K_SPACE and self.game_over:
                self.reset()

    def spawn_eat_particles(self, grid_pos):
        # create burst of particles at center of grid cell
        fx, fy = grid_pos
        cx = fx * self.grid_size + self.grid_size // 2
        cy = fy * self.grid_size + self.grid_size // 2
        for i in range(12):
            angle = random.random() * math.tau
            speed = random.uniform(60, 240)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particles.append({
                'x': cx,
                'y': cy,
                'vx': vx,
                'vy': vy,
                'life': random.uniform(300, 800),
                'max_life': random.uniform(300, 800),
                'r': random.randint(2, 6),
                'color': (255, 190, 60)
            })

    def create_head_sprite(self, size):
        # create a simple circular head sprite with eyes
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        r = size // 2
        # head base
        pygame.draw.circle(s, (100, 230, 100), (r, r), r)
        # darker rim
        pygame.draw.circle(s, (30, 160, 30), (r, r), r, max(1, size // 12))
        # eyes
        eye_w = max(2, size // 8)
        eye_h = max(2, size // 12)
        ex = r + size // 6
        ey = r - size // 8
        pygame.draw.rect(s, (30, 30, 30), (ex - eye_w // 2, ey - eye_h // 2, eye_w, eye_h))
        pygame.draw.rect(s, (30, 30, 30), (size - ex - eye_w // 2, ey - eye_h // 2, eye_w, eye_h))
        return s

    def run(self):
        while True:
            dt = self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.handle_event(event)

            # move based on speed (moves per second)
            self.move_timer += dt
            ms_per_move = 1000 / self.speed if self.speed > 0 else 1000
            if self.move_timer >= ms_per_move:
                self.move_timer -= ms_per_move
                self.step()

            # update particles
            self.update_particles(dt)

            # update interpolated segment positions so the snake visually moves
            self.update_segments(dt, ms_per_move)

            self.draw()


def main():
    game = PygameSnake(grid_size=20, cols=30, rows=30, start_speed=8)
    game.run()


if __name__ == '__main__':
    main()
