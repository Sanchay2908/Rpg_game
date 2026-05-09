from core import *
from attacks import BeamAttack, MiasmaZoneAttack, Projectile, RingAttack, SlashArc, ZoneAttack

# описывает класс camera
class Camera:
    # инициализирует объект
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.x = 0.0
        self.y = 0.0
        self.pad_x = 0.0
        self.pad_y = 0.0

    # обновляет состояние
    def update(self, target, world_width, world_height):
        if world_width <= self.width:
            self.x = 0.0
            self.pad_x = (self.width - world_width) / 2
        else:
            self.x = clamp(target.x - self.width / 2, 0.0, world_width - self.width)
            self.pad_x = 0.0
        if world_height <= self.height:
            self.y = 0.0
            self.pad_y = (self.height - world_height) / 2
        else:
            self.y = clamp(target.y - self.height / 2, 0.0, world_height - self.height)
            self.pad_y = 0.0

    # применяет
    def apply(self, value):
        if isinstance(value, pygame.Vector2):
            return pygame.Vector2(value.x - self.x + self.pad_x, value.y - self.y + self.pad_y)
        return value[0] - self.x + self.pad_x, value[1] - self.y + self.pad_y

    # выполняет unapply
    def unapply(self, value):
        return pygame.Vector2(value[0] + self.x - self.pad_x, value[1] + self.y - self.pad_y)


# описывает класс floating text
@dataclass

class FloatingText:
    text: str
    pos: pygame.Vector2
    color: tuple
    ttl: float = 0.8
    velocity: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, -34))

    # обновляет состояние
    def update(self, dt):
        self.ttl -= dt
        self.pos += self.velocity * dt

    # проверяет активен ли объект
    @property
    def alive(self):
        return self.ttl > 0


# описывает класс pickup
@dataclass

class Pickup:
    pos: pygame.Vector2
    heal: int = 28
    kind: str = "medkit"
    pulse: float = 0.0

# описывает класс sprite actor
class SpriteActor:
    # инициализирует объект
    def __init__(self, pos, frames, radius, hp, speed, name="", draw_anchor="center"):
        self.pos = pygame.Vector2(pos)
        self.frames = frames or []
        if not self.frames:
            fallback = pygame.Surface((max(4, radius * 2), max(4, radius * 2)), pygame.SRCALPHA)
            pygame.draw.circle(fallback, (255, 0, 255), fallback.get_rect().center, max(2, radius))
            self.frames = [fallback]
        self.anim = Animation(self.frames, fps=8)
        self.radius = radius
        self.max_hp = hp
        self.hp = hp
        self.speed = speed
        self.name = name
        self.dead = False
        self.iframes = 0.0
        self.hit_flash = 0.0
        self.draw_anchor = draw_anchor
        self.facing_x = 1
        self.mirror_when_left = False
        self.mirror_when_right = False

    # обновляет состояние объекта
    def tick(self, dt, moving=False):
        self.anim.update(dt, moving)
        self.iframes = max(0.0, self.iframes - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)

    # возвращает текущий кадр
    def current_frame(self):
        return self.apply_hit_flash(self.anim.image())

    # применяет hit flash
    def apply_hit_flash(self, image):
        if self.hit_flash > 0 and int(self.hit_flash * 30) % 2 == 0:
            flashed = image.copy()
            flashed.fill((255, 255, 255, 90), special_flags=pygame.BLEND_RGBA_ADD)
            return flashed
        return image

    # обрабатывает получение урона
    def take_damage(self, amount):
        if self.dead or self.iframes > 0:
            return False
        self.hp -= int(amount)
        self.iframes = 0.12
        self.hit_flash = 0.18
        if self.hp <= 0:
            self.dead = True
        return True

    # отрисовывает rect
    def draw_rect(self, image, pos):
        if self.draw_anchor == "midbottom":
            return image.get_rect(midbottom=(int(pos.x), int(pos.y + self.radius)))
        return image.get_rect(center=(int(pos.x), int(pos.y)))

    # выполняет мир draw rect
    def world_draw_rect(self, image=None, pos=None):
        image = image or self.current_frame()
        position = pygame.Vector2(pos) if pos is not None else self.pos
        if self.draw_anchor == "midbottom":
            return image.get_rect(midbottom=(int(position.x), int(position.y + self.radius)))
        return image.get_rect(center=(int(position.x), int(position.y)))

    # выполняет combat rect
    def combat_rect(self):
        return self.world_draw_rect(self.current_frame(), self.pos)

    # выполняет combat center
    def combat_center(self):
        return pygame.Vector2(self.combat_rect().center)

    # выполняет combat radius
    def combat_radius(self):
        rect = self.combat_rect()
        return max(self.radius, int(max(rect.width, rect.height) * 0.42))

    # отрисовывает текущую сцену
    def draw(self, surface, camera):
        image = self.current_frame()
        if self.mirror_when_left and self.facing_x < 0:
            image = pygame.transform.flip(image, True, False)
        elif self.mirror_when_right and self.facing_x > 0:
            image = pygame.transform.flip(image, True, False)
        pos = camera.apply(self.pos)
        rect = self.draw_rect(image, pos)
        surface.blit(image, rect)

# описывает класс player
class Player(SpriteActor):
    # инициализирует объект
    def __init__(
        self,
        pos,
        frames,
        caste,
        down_frames=None,
        attack_frames_right=None,
        attack_frames_left=None,
        walk_frames=None,
        run_frames=None,
        special_frames_right=None,
        special_frames_left=None,
        charge_frames=None,
        special_effect_frames=None,
        projectile_frames=None,
    ):
        super().__init__(pos, frames, radius=22, hp=100, speed=260, draw_anchor="midbottom")
        self.caste = caste
        self.max_mana = 100
        self.mana = 100
        self.attack_power = 18
        self.facing = pygame.Vector2(1, 0)
        self.dash_charges = 2
        self.dash_recharge = 0.0
        self.dash_time = 0.0
        self.dash_direction = pygame.Vector2(1, 0)
        self.melee_cooldown = 0.0
        self.special_cooldown = 0.0
        self.move_vector = pygame.Vector2()
        self.is_moving = False
        self.idle_frames = frames or []
        self.walk_frames = walk_frames or down_frames or frames or []
        self.run_frames = run_frames or self.walk_frames or self.idle_frames
        self.walk_anim = Animation(self.walk_frames or self.idle_frames, fps=9)
        self.run_anim = Animation(self.run_frames or self.walk_frames or self.idle_frames, fps=12)
        self.attack_frames_right = attack_frames_right or []
        self.attack_frames_left = attack_frames_left or self.flip_like(self.attack_frames_right)
        self.special_frames_right = special_frames_right or []
        self.special_frames_left = special_frames_left or self.flip_like(self.special_frames_right)
        self.charge_frames = charge_frames or []
        self.special_effect_frames = special_effect_frames or []
        self.projectile_frames = projectile_frames or []
        self.attack_duration = 0.28
        self.attack_timer = 0.0
        self.special_duration = 0.38
        self.special_timer = 0.0
        self.attack_side = 1
        self.last_horizontal = 1
        self.slow_timer = 0.0

    # выполняет combat rect
    def combat_rect(self):
        width = max(18, int(self.radius * 1.0))
        height = max(26, int(self.radius * 1.45))
        rect = pygame.Rect(0, 0, width, height)
        rect.centerx = int(self.pos.x)
        rect.centery = int(self.pos.y + self.radius * 0.08)
        return rect

    # выполняет combat radius
    def combat_radius(self):
        return max(10, self.radius // 2)

    # выполняет snapshot
    def snapshot(self):
        return {
            "max_hp": self.max_hp,
            "hp": self.hp,
            "max_mana": self.max_mana,
            "mana": self.mana,
            "attack_power": self.attack_power,
            "caste": self.caste,
        }

    # загружает stats
    def load_stats(self, stats):
        self.max_hp = int(stats.get("max_hp", self.max_hp))
        self.hp = clamp(int(stats.get("hp", self.hp)), 1, self.max_hp)
        self.max_mana = int(stats.get("max_mana", self.max_mana))
        self.mana = clamp(float(stats.get("mana", self.mana)), 0, self.max_mana)
        self.attack_power = int(stats.get("attack_power", self.attack_power))

    # выполняет movement vector
    def movement_vector(self, keys):
        move = pygame.Vector2(
            (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
            (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        if move.length_squared() > 0:
            move = move.normalize()
        return move

    # обновляет aim
    def update_aim(self, mouse_pos, camera):
        world_mouse = camera.unapply(mouse_pos)
        direction = world_mouse - self.pos
        if direction.length_squared() > 0:
            self.facing = direction.normalize()

    # выполняет remember horizontal
    def remember_horizontal(self, direction):
        if direction.x > 0.24:
            self.last_horizontal = 1
        elif direction.x < -0.24:
            self.last_horizontal = -1

    # возвращает текущий кадр
    def current_frame(self):
        if self.special_timer > 0 and self.special_frames_right:
            frames = self.special_frames_right if self.attack_side >= 0 else self.special_frames_left
            progress = clamp(1.0 - self.special_timer / max(0.001, self.special_duration), 0.0, 0.9999)
            index = min(len(frames) - 1, int(progress * len(frames)))
            return self.apply_hit_flash(frames[index])
        if self.attack_timer > 0 and self.attack_frames_right:
            frames = self.attack_frames_right if self.attack_side >= 0 else self.attack_frames_left
            progress = clamp(1.0 - self.attack_timer / self.attack_duration, 0.0, 0.9999)
            index = min(len(frames) - 1, int(progress * len(frames)))
            return self.apply_hit_flash(frames[index])
        if self.dash_time > 0 and self.run_frames:
            return self.apply_hit_flash(self.run_anim.image())
        if self.is_moving and self.walk_frames:
            return self.apply_hit_flash(self.walk_anim.image())
        return super().current_frame()

    # обновляет состояние объекта
    def tick(self, dt, moving=False, move_vector=None):
        if move_vector is not None:
            self.move_vector = pygame.Vector2(move_vector)
            self.remember_horizontal(self.move_vector)
            self.facing_x = self.last_horizontal
        self.is_moving = moving or self.dash_time > 0
        self.walk_anim.update(dt, self.is_moving and self.attack_timer <= 0 and self.special_timer <= 0 and self.dash_time <= 0)
        self.run_anim.update(dt, self.dash_time > 0)
        super().tick(dt, not self.is_moving and self.attack_timer <= 0 and self.special_timer <= 0)
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.special_timer = max(0.0, self.special_timer - dt)
        self.melee_cooldown = max(0.0, self.melee_cooldown - dt)
        self.special_cooldown = max(0.0, self.special_cooldown - dt)
        self.dash_time = max(0.0, self.dash_time - dt)
        self.dash_recharge = max(0.0, self.dash_recharge - dt)
        self.slow_timer = max(0.0, self.slow_timer - dt)
        if self.dash_charges < 2 and self.dash_recharge <= 0:
            self.dash_charges = 2
        self.mana = min(self.max_mana, self.mana + 14.0 * dt)

    # выполняет текущий move speed
    def current_move_speed(self):
        return self.speed * (0.6 if self.slow_timer > 0 else 1.0)

    # применяет slow
    def apply_slow(self, duration):
        self.slow_timer = max(self.slow_timer, duration)

    # выполняет dash velocity
    def dash_velocity(self):
        if self.dash_time > 0:
            return self.dash_direction * self.speed * 4.8
        return pygame.Vector2()

    # выполняет attempt dash
    def attempt_dash(self, move_vector):
        if self.dash_charges <= 0 or self.dash_time > 0:
            return False
        dash_direction = pygame.Vector2(move_vector) if move_vector.length_squared() > 0 else pygame.Vector2(self.facing)
        if dash_direction.length_squared() == 0:
            dash_direction = pygame.Vector2(1, 0)
        self.dash_direction = dash_direction.normalize()
        self.dash_time = 0.14
        self.dash_charges -= 1
        self.dash_recharge = 2.0
        self.iframes = max(self.iframes, 0.24)
        return True

    # выполняет attempt ближнюю
    def attempt_melee(self):
        if self.melee_cooldown > 0:
            return None
        self.melee_cooldown = 0.34
        self.sync_attack_side()
        self.attack_timer = self.attack_duration
        color = (248, 228, 160) if self.caste == "light" else (170, 132, 255)
        return SlashArc(self.pos.copy(), self.facing, self.attack_power, 112, 122, 0.18, color)

    # выполняет attempt усиленную
    def attempt_special(self):
        if self.special_cooldown > 0:
            return None
        mana_ratio = self.mana / max(1.0, self.max_mana)
        self.sync_attack_side()
        self.special_timer = self.special_duration
        if self.caste == "light":
            cost = 35
            if self.mana < cost:
                self.special_timer = 0.0
                return None
            self.mana -= cost
            self.special_cooldown = 0.78
            damage = int(self.attack_power * (1.7 + mana_ratio * 0.9))
            direction = self.facing if self.facing.length_squared() else pygame.Vector2(1, 0)
            return Projectile(
                self.pos + direction * 24,
                direction.normalize() * 620,
                damage,
                20,
                (242, 226, 172),
                ttl=1.5,
                pierce=999,
                explosive_radius=0,
                friendly=True,
                frames=self.projectile_frames,
                fps=14,
                face_velocity=True,
            )
        cost = 45
        if self.mana < cost:
            self.special_timer = 0.0
            return None
        self.mana -= cost
        self.special_cooldown = 0.95
        damage = int(self.attack_power * (2.1 + mana_ratio))
        direction = self.facing if self.facing.length_squared() else pygame.Vector2(1, 0)
        return Projectile(
            self.pos + direction * 24,
            direction.normalize() * 560,
            damage,
            18,
            (154, 111, 255),
            ttl=1.5,
            pierce=999,
            explosive_radius=0,
            friendly=True,
            frames=self.projectile_frames,
            fps=14,
            face_velocity=True,
        )

    # обрабатывает получение урона
    def take_damage(self, amount):
        if self.iframes > 0:
            return False
        self.hp -= int(amount)
        self.iframes = 0.3
        self.hit_flash = 0.22
        return True

    # синхронизирует атаку side
    def sync_attack_side(self):
        if self.facing.x > 0.24:
            self.attack_side = 1
        elif self.facing.x < -0.24:
            self.attack_side = -1
        else:
            self.attack_side = self.last_horizontal

    # выполняет flip like
    def flip_like(self, frames):
        return [pygame.transform.flip(frame, True, False) for frame in frames]

    # выполняет текущий charge кадр
    def current_charge_frame(self):
        if self.special_timer <= 0 or not self.charge_frames:
            return None
        progress = clamp(1.0 - self.special_timer / max(0.001, self.special_duration), 0.0, 0.9999)
        return self.charge_frames[min(len(self.charge_frames) - 1, int(progress * len(self.charge_frames)))]

    # выполняет текущий усиленную fx кадр
    def current_special_fx_frame(self):
        if self.special_timer <= 0 or not self.special_effect_frames:
            return None
        progress = clamp(1.0 - self.special_timer / max(0.001, self.special_duration), 0.0, 0.9999)
        frame = self.special_effect_frames[min(len(self.special_effect_frames) - 1, int(progress * len(self.special_effect_frames)))]
        if self.attack_side < 0:
            return pygame.transform.flip(frame, True, False)
        return frame

    # отрисовывает текущую сцену
    def draw(self, surface, camera):
        pos = camera.apply(self.pos)
        fx = self.current_special_fx_frame()
        if fx is not None:
            direction = self.facing if self.facing.length_squared() > 0 else pygame.Vector2(self.attack_side, 0)
            fx_pos = pygame.Vector2(pos) + direction.normalize() * 72
            surface.blit(fx, fx.get_rect(center=(int(fx_pos.x), int(fx_pos.y))))
        charge = self.current_charge_frame()
        if charge is not None:
            surface.blit(charge, charge.get_rect(center=(int(pos.x), int(pos.y))))
        image = self.current_frame()
        if self.last_horizontal < 0 and self.attack_timer <= 0 and self.special_timer <= 0:
            image = pygame.transform.flip(image, True, False)
        surface.blit(image, self.draw_rect(image, pos))

# описывает класс npc
class NPC(SpriteActor):
    # инициализирует объект
    def __init__(self, pos, frames, name, run_frames=None):
        super().__init__(pos, frames, radius=22, hp=1, speed=0, name=name, draw_anchor="midbottom")
        self.idle_frames = frames or []
        self.run_frames = run_frames or frames or []
        self.run_anim = Animation(self.run_frames or self.idle_frames, fps=8)
        self.visual_moving = False

    # обновляет состояние объекта
    def tick(self, dt, moving=False):
        self.visual_moving = moving
        self.run_anim.update(dt, moving)
        super().tick(dt, not moving)

    # возвращает текущий кадр
    def current_frame(self):
        if self.visual_moving and self.run_frames:
            return self.apply_hit_flash(self.run_anim.image())
        return super().current_frame()

# описывает класс wander npc
class WanderNPC(SpriteActor):
    # инициализирует объект
    def __init__(self, pos, up_frames, right_frames, down_frames, left_frames=None, name=""):
        idle_frames = down_frames or right_frames or up_frames or left_frames or []
        super().__init__(pos, idle_frames, radius=18, hp=1, speed=54, name=name, draw_anchor="midbottom")
        self.up_frames = up_frames or idle_frames
        self.right_frames = right_frames or idle_frames
        self.down_frames = down_frames or idle_frames
        self.left_frames = left_frames or [pygame.transform.flip(frame, True, False) for frame in self.right_frames]
        self.up_anim = Animation(self.up_frames or idle_frames, fps=7)
        self.right_anim = Animation(self.right_frames or idle_frames, fps=7)
        self.down_anim = Animation(self.down_frames or idle_frames, fps=7)
        self.left_anim = Animation(self.left_frames or idle_frames, fps=7)
        self.home = pygame.Vector2(pos)
        self.wander_target = pygame.Vector2(pos)
        self.pause_timer = random.uniform(0.5, 1.6)
        self.visual_moving = False
        self.move_vector = pygame.Vector2()

    # выбирает new target
    def choose_new_target(self, game):
        for _ in range(20):
            offset = pygame.Vector2(random.uniform(-150, 150), random.uniform(-150, 150))
            target = self.home + offset
            bounds = game.actor_bounds(self, target)
            if any(game.bounds_hit_wall(bounds, wall) for wall in game.active_walls()):
                continue
            self.wander_target = target
            return
        self.wander_target = pygame.Vector2(self.home)

    # обновляет wander
    def update_wander(self, dt, game):
        if self.pause_timer > 0:
            self.pause_timer = max(0.0, self.pause_timer - dt)
            self.visual_moving = False
            self.move_vector.update(0, 0)
            return pygame.Vector2()
        delta = self.wander_target - self.pos
        if delta.length_squared() <= 36:
            self.pause_timer = random.uniform(0.4, 1.4)
            self.choose_new_target(game)
            self.visual_moving = False
            self.move_vector.update(0, 0)
            return pygame.Vector2()
        velocity = delta.normalize() * self.speed
        self.visual_moving = True
        self.move_vector = velocity.normalize()
        return velocity

    # обновляет состояние объекта
    def tick(self, dt, moving=False):
        self.visual_moving = moving
        self.iframes = max(0.0, self.iframes - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)
        if moving:
            if abs(self.move_vector.x) > abs(self.move_vector.y):
                if self.move_vector.x >= 0:
                    self.right_anim.update(dt, True)
                else:
                    self.left_anim.update(dt, True)
            elif self.move_vector.y < 0:
                self.up_anim.update(dt, True)
            else:
                self.down_anim.update(dt, True)
        else:
            self.anim.update(dt, True)

    # возвращает текущий кадр
    def current_frame(self):
        if self.visual_moving:
            if abs(self.move_vector.x) > abs(self.move_vector.y):
                if self.move_vector.x >= 0:
                    return self.apply_hit_flash(self.right_anim.image())
                return self.apply_hit_flash(self.left_anim.image())
            if self.move_vector.y < 0:
                return self.apply_hit_flash(self.up_anim.image())
            return self.apply_hit_flash(self.down_anim.image())
        if self.move_vector.y < -0.2:
            return self.apply_hit_flash(self.up_frames[0] if self.up_frames else super().current_frame())
        if self.move_vector.x > 0.2:
            return self.apply_hit_flash(self.right_frames[0] if self.right_frames else super().current_frame())
        if self.move_vector.x < -0.2:
            return self.apply_hit_flash(self.left_frames[0] if self.left_frames else super().current_frame())
        return self.apply_hit_flash(self.down_frames[0] if self.down_frames else super().current_frame())

# описывает класс training dummy
class TrainingDummy(SpriteActor):
    # инициализирует объект
    def __init__(self, pos, frames):
        super().__init__(pos, frames, radius=20, hp=56, speed=0)

# описывает класс rune crystal
class RuneCrystal(SpriteActor):
    # инициализирует объект
    def __init__(self, pos, frames):
        super().__init__(pos, frames, radius=22, hp=70, speed=0)

    # отрисовывает текущую сцену
    def draw(self, surface, camera):
        pos = camera.apply(self.pos)
        glow = pygame.Surface((120, 120), pygame.SRCALPHA)
        pygame.draw.circle(glow, (152, 122, 255, 45), (60, 60), 40)
        surface.blit(glow, (pos.x - 60, pos.y - 60))
        image = self.current_frame().copy()
        image.fill((72, 42, 120, 100), special_flags=pygame.BLEND_RGBA_ADD)
        rect = image.get_rect(center=(int(pos.x), int(pos.y)))
        surface.blit(image, rect)

# описывает класс ghoul
class Ghoul(SpriteActor):
    # инициализирует объект
    def __init__(
        self,
        pos,
        frames,
        summoned=False,
        walk_frames=None,
        attack_variants=None,
        hurt_frames=None,
        death_frames=None,
    ):
        hp = 38 if not summoned else 24
        speed = 152 if not summoned else 190
        super().__init__(pos, frames, radius=20, hp=hp, speed=speed, draw_anchor="midbottom")
        self.mirror_when_left = True
        self.variant = "ghoul"
        self.summoned = summoned
        self.idle_frames = frames or []
        self.walk_frames = walk_frames or frames or []
        self.walk_anim = Animation(self.walk_frames or self.idle_frames, fps=8)
        self.attack_variants = [variant for variant in (attack_variants or []) if variant]
        self.attack_frames = self.attack_variants[0] if self.attack_variants else []
        self.attack_anim = Animation(self.attack_frames or self.walk_frames or self.idle_frames, fps=11)
        self.attack_timer = 0.0
        self.attack_duration = 0.42
        self.cast_frames = []
        self.cast_anim = Animation(self.walk_frames or self.idle_frames, fps=9)
        self.cast_timer = 0.0
        self.cast_duration = 0.0
        self.hurt_frames = hurt_frames or []
        self.death_frames = death_frames or []
        self.death_anim = Animation(self.death_frames or self.walk_frames or self.idle_frames, fps=9)
        self.visual_moving = False
        self.attack_cooldown = random.uniform(0.35, 0.9)
        self.attack_damage = 10 if not summoned else 7
        self.attack_reach = 34 if not summoned else 26
        self.attack_interval = 0.9 if not summoned else 0.65
        self.loot_rolled = False
        self.path_nodes = []
        self.path_index = 0
        self.repath_timer = random.uniform(0.05, 0.22)
        self.path_goal_cell = None
        self.buff_timer = 0.0
        self.buff_speed_mult = 1.0
        self.buff_damage_mult = 1.0

    # обновляет состояние объекта
    def tick(self, dt, moving=False):
        self.visual_moving = moving
        self.iframes = max(0.0, self.iframes - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)
        if self.dead:
            self.death_anim.update(dt, True)
            self.attack_timer = 0.0
            self.cast_timer = 0.0
            return
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.cast_timer = max(0.0, self.cast_timer - dt)
        if self.cast_timer > 0 and self.cast_frames:
            self.cast_anim.update(dt, True)
        elif self.attack_timer > 0 and self.attack_frames:
            self.attack_anim.update(dt, True)
        elif moving and self.walk_frames:
            self.walk_anim.update(dt, True)
        else:
            self.anim.update(dt, True)

    # возвращает текущий кадр
    def current_frame(self):
        if self.dead and self.death_frames:
            return self.death_anim.image()
        if self.cast_timer > 0 and self.cast_frames:
            return self.cast_anim.image()
        if self.attack_timer > 0 and self.attack_frames:
            return self.attack_anim.image()
        if self.visual_moving and self.walk_frames:
            return self.walk_anim.image()
        return super().current_frame()

    # выполняет engage distance
    def engage_distance(self, player):
        return self.radius + player.radius + self.attack_reach

    # применяет buff
    def apply_buff(self, duration=5.0, speed_mult=1.2, damage_mult=1.25):
        self.buff_timer = max(self.buff_timer, duration)
        self.buff_speed_mult = max(self.buff_speed_mult, speed_mult)
        self.buff_damage_mult = max(self.buff_damage_mult, damage_mult)

    # выполняет текущий speed
    def current_speed(self):
        return self.speed * self.buff_speed_mult

    # выполняет ближнюю damage
    def melee_damage(self):
        return int(round(self.attack_damage * self.buff_damage_mult))

    # выполняет ближнюю cooldown duration
    def melee_cooldown_duration(self):
        return self.attack_interval

    # обновляет status
    def update_status(self, dt):
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        self.repath_timer = max(0.0, self.repath_timer - dt)
        self.buff_timer = max(0.0, self.buff_timer - dt)
        if self.buff_timer <= 0:
            self.buff_speed_mult = 1.0
            self.buff_damage_mult = 1.0

    # пытается применить усиленную атаку
    def try_special_attack(self, dt, player, game):
        return

    # обновляет ai
    def update_ai(self, dt, player, game):
        self.update_status(dt)
        self.try_special_attack(dt, player, game)
        direction = player.pos - self.pos
        if direction.length_squared() == 0:
            self.tick(dt, moving=False)
            return pygame.Vector2()
        stop_distance = max(24.0, self.engage_distance(player) - 6.0)
        speed = self.current_speed()
        if direction.length() > stop_distance:
            self.tick(dt, moving=True)
            if not line_blocked(self.pos, player.pos, game.cover):
                self.facing_x = -1 if direction.x < 0 else 1
                return direction.normalize() * speed
            goal_cell = game.world_to_cell(player.pos)
            if self.repath_timer <= 0 or not self.path_nodes or self.path_goal_cell != goal_cell:
                self.path_nodes = game.find_path(self.pos, player.pos)
                self.path_index = 0
                self.path_goal_cell = goal_cell
                self.repath_timer = random.uniform(0.28, 0.46)
            if self.path_nodes:
                while self.path_index < len(self.path_nodes):
                    node = self.path_nodes[self.path_index]
                    if self.pos.distance_to(node) <= 14:
                        self.path_index += 1
                    else:
                        break
                if self.path_index < len(self.path_nodes):
                    target = self.path_nodes[self.path_index]
                    path_direction = target - self.pos
                    if path_direction.length_squared() > 0:
                        self.facing_x = -1 if path_direction.x < 0 else 1
                        return path_direction.normalize() * speed
            self.facing_x = -1 if direction.x < 0 else 1
            return direction.normalize() * speed
        self.tick(dt, moving=False)
        return pygame.Vector2()

    # выполняет begin атаку animation
    def begin_attack_animation(self, duration=None, variant_index=None):
        if self.attack_variants:
            if variant_index is None:
                frames = random.choice(self.attack_variants)
            else:
                frames = self.attack_variants[variant_index % len(self.attack_variants)]
            if frames:
                self.attack_frames = frames
                self.attack_anim = Animation(frames, fps=12)
        self.attack_timer = duration if duration is not None else self.attack_duration

    # выполняет begin cast animation
    def begin_cast_animation(self, frames=None, duration=0.7, fps=10):
        if frames:
            self.cast_frames = frames
            self.cast_anim = Animation(frames, fps=fps)
        self.cast_timer = duration
        self.cast_duration = duration

    # отрисовывает текущую сцену
    def draw(self, surface, camera):
        super().draw(surface, camera)

# описывает класс light priest
class LightPriest(Ghoul):
    # инициализирует объект
    def __init__(self, pos, frames, walk_frames=None, attack_frames=None, hurt_frames=None, death_frames=None):
        super().__init__(
            pos,
            frames,
            summoned=False,
            walk_frames=walk_frames,
            attack_variants=[attack_frames] if attack_frames else None,
            hurt_frames=hurt_frames,
            death_frames=death_frames,
        )
        self.variant = "light"
        self.max_hp = 50
        self.hp = 50
        self.speed = 85
        self.radius = 32
        self.attack_damage = 12
        self.attack_reach = 32
        self.attack_interval = 1.15
        self.spell_cooldown = random.uniform(6.0, 11.0)

    # пытается применить усиленную атаку
    def try_special_attack(self, dt, player, game):
        self.spell_cooldown = max(0.0, self.spell_cooldown - dt)
        if self.spell_cooldown > 0:
            return
        self.spell_cooldown = 15.0
        self.begin_cast_animation(self.attack_frames, duration=0.7, fps=11)
        damage = max(10, int(round(self.melee_damage() * 2.0)))
        size = 104
        if random.random() < 0.5:
            offsets = [pygame.Vector2(0, 0), pygame.Vector2(112, -64), pygame.Vector2(-104, 56)]
            for offset in offsets:
                center = player.pos + offset
                rect = pygame.Rect(int(center.x - size / 2), int(center.y - size / 2), size, size)
                game.enemy_zones.append(
                    ZoneAttack(
                        rect,
                        damage,
                        0.9,
                        0.28,
                        (246, 236, 196),
                        warning_color=(255, 242, 214),
                        style="light_pillar",
                        frames=game.sprite_bank.get("light_priest_beam"),
                        fps=14,
                    )
                )
        else:
            center = player.pos.copy()
            rect = pygame.Rect(int(center.x - size / 2), int(center.y - size / 2), size, size)
            game.enemy_zones.append(
                ZoneAttack(
                    rect,
                    damage,
                    0.72,
                    0.3,
                    (246, 236, 196),
                    warning_color=(255, 242, 214),
                    style="light_pillar",
                    frames=game.sprite_bank.get("light_priest_beam"),
                    fps=14,
                )
            )

# описывает класс dark alchemist
class DarkAlchemist(Ghoul):
    # инициализирует объект
    def __init__(self, pos, frames, walk_frames=None, attack_frames=None, cast_frames=None, spell_frames=None, hurt_frames=None, death_frames=None):
        super().__init__(
            pos,
            frames,
            summoned=False,
            walk_frames=walk_frames,
            attack_variants=[attack_frames] if attack_frames else None,
            hurt_frames=hurt_frames,
            death_frames=death_frames,
        )
        self.variant = "dark"
        self.max_hp = 80
        self.hp = 80
        self.speed = 40
        self.radius = 24
        self.attack_damage = 12
        self.attack_reach = 28
        self.attack_interval = 1.2
        self.shot_cooldown = random.uniform(1.4, 2.6)
        self.potion_cooldown = random.uniform(7.0, 10.0)
        self.cast_frames = cast_frames or []
        self.spell_frames = spell_frames or []
        self.mirror_when_left = False
        self.mirror_when_right = True

    # пытается применить усиленную атаку
    def try_special_attack(self, dt, player, game):
        self.shot_cooldown = max(0.0, self.shot_cooldown - dt)
        self.potion_cooldown = max(0.0, self.potion_cooldown - dt)
        if self.shot_cooldown <= 0:
            direction = player.pos - self.pos
            if direction.length_squared() > 0:
                self.begin_attack_animation(duration=0.42, variant_index=0)
                velocity = direction.normalize() * 330
                damage = max(12, int(round(self.melee_damage() * 1.5)))
                game.enemy_projectiles.append(
                    Projectile(
                        self.pos + velocity.normalize() * 26,
                        velocity,
                        damage,
                        14,
                        (112, 88, 198),
                        ttl=2.2,
                        friendly=False,
                        frames=self.spell_frames,
                        fps=14,
                        face_velocity=True,
                    )
                )
                self.shot_cooldown = 2.4
        if self.potion_cooldown <= 0:
            self.potion_cooldown = 10.0
            if random.random() < 0.2:
                self.begin_cast_animation(self.cast_frames, duration=0.72, fps=11)
                center = player.pos.copy()
                rect = pygame.Rect(int(center.x - 82), int(center.y - 82), 164, 164)
                game.enemy_zones.append(
                    MiasmaZoneAttack(
                        rect,
                        max(3, int(round(self.melee_damage() * 0.3))),
                        0.75,
                        5.0,
                        (102, 78, 160),
                        frames=self.spell_frames,
                        fps=12,
                    )
                )
                for enemy in game.enemies:
                    if enemy is self:
                        continue
                    if enemy.pos.distance_to(self.pos) <= 180:
                        enemy.apply_buff(5.0, speed_mult=1.18, damage_mult=1.25)

