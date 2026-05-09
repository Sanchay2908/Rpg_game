from core import *
from attacks import *
from bosses import *
from entities import *


# описывает класс world mixin
class WorldMixin:
    # собирает assault волны
    def build_assault_waves(self):
        # выполняет p
        def p(tx, ty):
            return pygame.Vector2((tx + 0.5) * TILE_SIZE, (ty + 0.5) * TILE_SIZE)

        return [
            [
                (p(38, 13), "ghoul", False),
                (p(41, 10), "light", False),
                (p(42, 12), "ghoul", False),
                (p(38, 18), "dark", False),
                (p(37, 24), "ghoul", False),
                (p(31, 30), "ghoul", False),
            ],
            [
                (p(29, 9), "ghoul", False),
                (p(41, 8), "dark", False),
                (p(42, 14), "ghoul", False),
                (p(38, 22), "light", False),
                (p(40, 29), "ghoul", False),
                (p(29, 35), "dark", False),
                (p(26, 39), "ghoul", True),
                (p(25, 38), "ghoul", True),
                (p(29, 24), "ghoul", True),
                (p(35, 18), "ghoul", True),
            ],
            [
                (p(29, 8), "light", False),
                (p(38, 8), "dark", False),
                (p(42, 10), "ghoul", False),
                (p(42, 16), "light", False),
                (p(38, 23), "ghoul", False),
                (p(40, 31), "dark", False),
                (p(29, 36), "ghoul", False),
                (p(26, 39), "ghoul", False),
                (p(25, 39), "ghoul", True),
                (p(22, 35), "ghoul", True),
                (p(28, 32), "dark", False),
                (p(34, 27), "ghoul", True),
                (p(38, 20), "light", False),
                (p(30, 15), "ghoul", True),
            ],
        ]

    # выполняет point from карту object
    def point_from_map_object(self, obj, fallback=None):
        if not obj:
            return pygame.Vector2(fallback or (0, 0))
        return obj.center

    # выполняет rect from карту object
    def rect_from_map_object(self, obj, fallback=None):
        if not obj:
            return fallback.copy() if fallback else None
        return obj.rect

    # подготавливает общее состояние перед загрузкой комнаты
    def prepare_room_scene(self, chapter):
        self.scene = "gameplay"
        self.chapter = chapter
        self.stats_overlay = False
        self.ground_tiles = []
        self.detail_tiles = []
        self.overlay_tiles = []
        self.assault_started = False
        self.assault_stream_rects = []
        self.assault_forest_rects = []

    # применяет загруженный шаблон tiled карты к состоянию мира
    def apply_map_template(self, template):
        # хранит текущую обёртку карты для чтения слоёв и объектов
        self.current_map = template
        # хранит путь к активной карте для отладки и повторной загрузки
        self.current_map_path = template.path
        # хранит размер карты в тайлах и пикселях игрового мира
        self.world_tiles = (template.width, template.height)
        self.world_size = pygame.Vector2(template.width * template.tile_width, template.height * template.tile_height)
        # хранит слои тайлов, набор тайлсетов и объекты tiled
        self.map_layers = template.layers
        self.map_base_layers = template.base_layers
        self.map_overlay_layers = template.overlay_layers
        self.map_gid_surfaces = template.gid_surfaces
        self.map_tilesets = template.tilesets
        self.map_object_layers = template.object_layers

    # собирает прямоугольники коллизии из объектов tiled
    def collision_rects_from_objects(self, objects):
        return [obj.rect for obj in objects if obj.width > 0 and obj.height > 0]

    # выполняет карту objects matching
    def map_objects_matching(self, *aliases):
        return self.current_map.objects_matching(*aliases) if self.current_map else []

    # собирает assault town spawns
    def build_assault_town_spawns(self):
        spawns = []
        for obj in self.map_objects_matching("npc"):
            label = obj.label()
            npc_kind = "npc2" if "2" in label else "npc1"
            spawns.append({"kind": npc_kind, "pos": self.point_from_map_object(obj)})
        return spawns

    # создает assault civilians
    def spawn_assault_civilians(self):
        if self.assault_civilians_spawned:
            return
        self.assault_civilians_spawned = True
        self.town_npcs = []
        for spawn in self.town_npc_spawns:
            kind = spawn["kind"]
            npc = WanderNPC(
                spawn["pos"],
                self.sprite_bank.get(f"{kind}_up"),
                self.sprite_bank.get(f"{kind}_right"),
                self.sprite_bank.get(f"{kind}_down"),
                left_frames=self.sprite_bank.get(f"{kind}_left"),
                name="",
            )
            self.town_npcs.append(npc)
        if self.town_npcs:
            self.show_toast("Жители выбираются из укрытий. Тропа к дракону теперь открыта.")

    # обновляет assault civilians
    def update_assault_civilians(self, dt):
        for npc in self.town_npcs:
            velocity = npc.update_wander(dt, self)
            self.move_actor(npc, velocity * dt)
            npc.tick(dt, moving=velocity.length_squared() > 0)

    # создает next assault волну
    def spawn_next_assault_wave(self):
        if self.assault_wave_index >= len(self.assault_waves):
            return False
        specs = self.assault_waves[self.assault_wave_index]
        enemies = []
        for pos, kind, summoned in specs:
            if kind == "light":
                enemies.append(
                    LightPriest(
                        pos,
                        self.sprite_bank["light_priest_idle"],
                        walk_frames=self.sprite_bank.get("light_priest_walk"),
                        attack_frames=self.sprite_bank.get("light_priest_attack"),
                        hurt_frames=self.sprite_bank.get("light_priest_hurt"),
                        death_frames=self.sprite_bank.get("light_priest_death"),
                    )
                )
            elif kind == "dark":
                enemies.append(
                    DarkAlchemist(
                        pos,
                        self.sprite_bank["dark_alchemist_idle"],
                        walk_frames=self.sprite_bank.get("dark_alchemist_walk"),
                        attack_frames=self.sprite_bank.get("dark_alchemist_attack"),
                        cast_frames=self.sprite_bank.get("dark_alchemist_cast"),
                        spell_frames=self.sprite_bank.get("dark_alchemist_spell"),
                        hurt_frames=self.sprite_bank.get("dark_alchemist_hurt"),
                        death_frames=self.sprite_bank.get("dark_alchemist_death"),
                    )
                )
            else:
                enemies.append(
                    Ghoul(
                        pos,
                        self.sprite_bank["ghoul"],
                        summoned=summoned,
                        walk_frames=self.sprite_bank.get("ghoul_walk"),
                        attack_variants=self.sprite_bank.get("ghoul_attacks"),
                        death_frames=self.sprite_bank.get("ghoul_death"),
                    )
                )
        self.enemies = enemies
        self.assault_wave_index += 1
        self.assault_wave_delay = 0.0
        remaining = max(0, len(self.assault_waves) - self.assault_wave_index)
        self.show_wave_banner(f"{self.assault_wave_index} ВОЛНА", f"Осталось волн: {remaining}")
        self.show_toast(f"Волна {self.assault_wave_index}/{len(self.assault_waves)} выходит из леса.")
        return True

    # настраивает assault room
    def setup_assault_room(self, skip_save=False):
        self.prepare_room_scene("assault")
        self.clear_combat_state()
        self.decor = []
        if self.assault_map_template:
            template = self.assault_map_template
            self.apply_map_template(template)
            self.walls = template.collision_rects("collision")
            default_spawn = pygame.Vector2(7.5 * TILE_SIZE, 10.4 * TILE_SIZE)
            default_trigger = pygame.Rect(19 * TILE_SIZE, 8 * TILE_SIZE, 5 * TILE_SIZE, 6 * TILE_SIZE)
            default_exit = pygame.Rect(int(self.world_size.x - 5 * TILE_SIZE), 0, 5 * TILE_SIZE, 4 * TILE_SIZE)
            self.assault_spawn_point = template.first_center("spawn", fallback=default_spawn)
            self.assault_wave_trigger = template.first_rect("trigger wave", "wave trigger", "trigger", fallback=default_trigger)
            self.assault_teleport_rect = template.first_rect("teleport to dragon", "teleport", fallback=default_exit)
            self.town_npc_spawns = self.build_assault_town_spawns()
        else:
            self.current_map = None
            self.current_map_path = None
            self.world_tiles = (50, 50)
            self.world_size = pygame.Vector2(self.world_tiles[0] * TILE_SIZE, self.world_tiles[1] * TILE_SIZE)
            self.map_layers = []
            self.map_base_layers = []
            self.map_overlay_layers = []
            self.map_gid_surfaces = {}
            self.map_tilesets = []
            self.map_object_layers = {}
            self.assault_spawn_point = pygame.Vector2(7.5 * TILE_SIZE, 10.4 * TILE_SIZE)
            self.assault_wave_trigger = pygame.Rect(19 * TILE_SIZE, 8 * TILE_SIZE, 5 * TILE_SIZE, 6 * TILE_SIZE)
            self.assault_teleport_rect = pygame.Rect(int(self.world_size.x - 5 * TILE_SIZE), 0, 5 * TILE_SIZE, 4 * TILE_SIZE)
            self.town_npc_spawns = []
            self.assault_stream_rects = [
                pygame.Rect(13 * TILE_SIZE, 0, 3 * TILE_SIZE, 10 * TILE_SIZE),
                pygame.Rect(13 * TILE_SIZE, 12 * TILE_SIZE, 3 * TILE_SIZE, 38 * TILE_SIZE),
            ]
            self.assault_forest_rects = [
                pygame.Rect(0, 0, 4 * TILE_SIZE, 50 * TILE_SIZE),
                pygame.Rect(0, 0, 13 * TILE_SIZE, 5 * TILE_SIZE),
                pygame.Rect(18 * TILE_SIZE, 0, 17 * TILE_SIZE, 5 * TILE_SIZE),
                pygame.Rect(43 * TILE_SIZE, 0, 7 * TILE_SIZE, 50 * TILE_SIZE),
                pygame.Rect(0, 44 * TILE_SIZE, 50 * TILE_SIZE, 6 * TILE_SIZE),
                pygame.Rect(30 * TILE_SIZE, 6 * TILE_SIZE, 8 * TILE_SIZE, 7 * TILE_SIZE),
                pygame.Rect(39 * TILE_SIZE, 18 * TILE_SIZE, 5 * TILE_SIZE, 8 * TILE_SIZE),
                pygame.Rect(30 * TILE_SIZE, 31 * TILE_SIZE, 10 * TILE_SIZE, 8 * TILE_SIZE),
                pygame.Rect(15 * TILE_SIZE, 37 * TILE_SIZE, 10 * TILE_SIZE, 7 * TILE_SIZE),
            ]
            self.walls = self.build_world_bounds()
            self.walls.extend(self.assault_stream_rects)
            self.walls.extend(self.assault_forest_rects)
            width, height = self.world_tiles
            self.ground_tiles = [[f"grass_{(tx * 7 + ty * 11) % 3}" for tx in range(width)] for ty in range(height)]
            self.detail_tiles = [[None for _ in range(width)] for _ in range(height)]
            self.overlay_tiles = [[None for _ in range(width)] for _ in range(height)]

        self.refresh_cover()
        self.rebuild_navigation()
        self.player.pos = self.assault_spawn_point.copy()
        self.player.hp = self.player.max_hp
        self.player.mana = self.player.max_mana
        self.master.pos = self.assault_spawn_point + pygame.Vector2(108, -36)
        self.assault_waves = self.build_assault_waves()
        self.assault_wave_index = 0
        self.assault_tutorial_step = 0
        self.assault_tutorial_move = False
        self.assault_tutorial_melee = False
        self.assault_tutorial_special = False
        self.assault_tutorial_dodge = False
        self.camera.update(self.player.pos, self.world_size.x, self.world_size.y)
        if not skip_save:
            self.save_checkpoint("assault")
        self.show_toast("Тихая опушка ещё держится. Перейди мост, когда будешь готов.")

    # настраивает дракона room
    def setup_dragon_room(self, skip_save=False):
        self.prepare_room_scene("dragon")
        if self.dragon_map_template:
            template = self.dragon_map_template
            self.apply_map_template(template)
            self.walls = template.collision_rects("collision")
            self.dragon_spawn_point = template.first_center("spawn", "player spawn", fallback=pygame.Vector2(
                self.world_size.x * 0.5, self.world_size.y - 2.2 * TILE_SIZE
            ))
        else:
            self.current_map = None
            self.current_map_path = None
            self.world_tiles = (30, 20)
            self.world_size = pygame.Vector2(self.world_tiles[0] * TILE_SIZE, self.world_tiles[1] * TILE_SIZE)
            self.map_layers = []
            self.map_base_layers = []
            self.map_overlay_layers = []
            self.map_gid_surfaces = {}
            self.map_tilesets = []
            self.map_object_layers = {}
            self.walls = self.build_world_bounds()
            self.dragon_spawn_point = pygame.Vector2(15 * TILE_SIZE, 17.2 * TILE_SIZE)
        self.refresh_cover()
        self.rebuild_navigation()
        self.decor = []
        self.clear_combat_state()
        self.refresh_cover()
        self.player.pos = self.dragon_spawn_point.copy()
        self.dragon = DragonBoss((self.world_size.x * 0.5, 4.6 * TILE_SIZE), self.sprite_bank["dragon"])
        self.begin_dragon_idle_window(5.2)
        self.camera.update(self.player.pos, self.world_size.x, self.world_size.y)
        if not skip_save:
            self.save_checkpoint("dragon")
        self.show_toast("Пепельный дракон держит зал пустым. Перед лучом сама земля даст тебе укрытия.")

    # собирает туннель mask
    def build_tunnel_mask(self):
        surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        surface.fill((0, 0, 0))
        if not self.tunnel_rects:
            return surface
        for rect in self.tunnel_rects:
            pygame.draw.rect(surface, (255, 255, 255), rect)
        return surface

    # настраивает туннель
    def setup_tunnel(self, skip_save=False):
        if self.tunnel_map_template:
            self.prepare_room_scene("tunnel")
            self.clear_combat_state()
            template = self.tunnel_map_template
            self.apply_map_template(template)
            wall_objects = template.objects_in_layer("walls") or template.objects_in_layer("collision")
            self.walls = self.collision_rects_from_objects(wall_objects)
            self.tunnel_fire_rects = template.collision_rects("fire")
            self.tunnel_spawn_point = template.first_center("spawn", fallback=pygame.Vector2(
                self.world_size.x * 0.5, self.world_size.y - 2.2 * TILE_SIZE
            ))
            self.tunnel_exit_rect = pygame.Rect(0, 0, int(self.world_size.x), TILE_SIZE)
            self.player.pos = self.tunnel_spawn_point.copy()
            self.refresh_cover()
            self.rebuild_navigation()
            self.camera.update(self.player.pos, self.world_size.x, self.world_size.y)
            if not skip_save:
                self.save_checkpoint("tunnel")
            self.show_toast("Лабиринт пылает. Ступишь в огонь — погибнешь сразу.")
            return

        self.prepare_room_scene("tunnel")
        self.tunnel_rects = [
            pygame.Rect(76, 800, 156, 156),
            pygame.Rect(190, 838, 430, 80),
            pygame.Rect(542, 620, 80, 298),
            pygame.Rect(264, 620, 358, 80),
            pygame.Rect(264, 346, 80, 354),
            pygame.Rect(264, 346, 1086, 80),
            pygame.Rect(1270, 170, 80, 256),
            pygame.Rect(1216, 82, 188, 142),
        ]
        self.tunnel_points = [(rect.centerx, rect.centery) for rect in self.tunnel_rects]
        self.tunnel_widths = [min(rect.width, rect.height) for rect in self.tunnel_rects[:-1]]
        self.tunnel_start = pygame.Vector2(154, 878)
        self.tunnel_goal = pygame.Vector2(1310, 152)
        self.tunnel_mask = self.build_tunnel_mask()
        self.tunnel_player = pygame.Vector2(self.tunnel_start)
        self.tunnel_message = "Держись цельного коридора. Дальше будут узкие шейки и жёсткие повороты."
        if not skip_save:
            self.save_checkpoint("tunnel")
        self.show_toast("Перед тобой прямой лабиринт. Иди только по мягкой светлой полосе и не цепляй пустоту.")

    # настраивает брата room
    def setup_brother_room(self, skip_save=False):
        self.prepare_room_scene("brother")
        self.clear_combat_state()
        if self.brother_map_template:
            template = self.brother_map_template
            self.apply_map_template(template)
            collision_objects = template.objects_in_layer("collision") or template.objects_in_layer("walls")
            self.walls = self.collision_rects_from_objects(collision_objects)
            self.brother_spawn_point = template.first_center("spawn", fallback=pygame.Vector2(
                self.world_size.x * 0.5, self.world_size.y - 2.0 * TILE_SIZE
            ))
        else:
            self.current_map = None
            self.current_map_path = None
            self.world_tiles = (30, 16)
            self.world_size = pygame.Vector2(self.world_tiles[0] * TILE_SIZE, self.world_tiles[1] * TILE_SIZE)
            self.map_layers = []
            self.map_base_layers = []
            self.map_overlay_layers = []
            self.map_gid_surfaces = {}
            self.map_tilesets = []
            self.map_object_layers = {}
            self.walls = self.build_world_bounds()
            self.brother_spawn_point = pygame.Vector2(15 * TILE_SIZE, 12.5 * TILE_SIZE)
        self.refresh_cover()
        self.rebuild_navigation()
        self.decor = [("ash", pygame.Vector2(8 * TILE_SIZE, 8 * TILE_SIZE)), ("ash", pygame.Vector2(22 * TILE_SIZE, 8 * TILE_SIZE))]
        self.player.pos = self.brother_spawn_point.copy()
        self.brother = BrotherBoss(
            (15 * TILE_SIZE, 4.5 * TILE_SIZE),
            self.sprite_bank["brother_idle"],
            self.player.speed,
            run_frames=self.sprite_bank.get("brother_run"),
            attack_1_frames=self.sprite_bank.get("brother_attack_1"),
            attack_2_frames=self.sprite_bank.get("brother_attack_2"),
            jump_frames=self.sprite_bank.get("brother_jump"),
            fall_frames=self.sprite_bank.get("brother_fall"),
            hit_frames=self.sprite_bank.get("brother_hit"),
            death_frames=self.sprite_bank.get("brother_death"),
        )
        self.camera.update(self.player.pos, self.world_size.x, self.world_size.y)
        if not skip_save:
            self.save_checkpoint("brother")
        self.show_toast("В сердце Разлома тебя ждёт брат, вобравший обе силы.")

    # собирает мир bounds
    def build_world_bounds(self):
        return []

    # выполняет active walls
    def active_walls(self):
        walls = list(self.walls)
        for spike in self.rock_spikes:
            if spike.is_blocking:
                walls.append(spike.collision_rect())
        return walls

    # выполняет refresh cover
    def refresh_cover(self):
        self.cover = self.active_walls()

    # выполняет actor bounds
    def actor_bounds(self, actor, pos=None):
        position = pos or actor.pos
        return (
            position.x - actor.radius,
            position.y - actor.radius,
            position.x + actor.radius,
            position.y + actor.radius,
        )

    # выполняет bounds hit wall
    def bounds_hit_wall(self, bounds, wall):
        left, top, right, bottom = bounds
        return left < wall.right and right > wall.left and top < wall.bottom and bottom > wall.top

    # выполняет мир to cell
    def world_to_cell(self, pos):
        return (
            clamp(int(pos.x // TILE_SIZE), 0, self.world_tiles[0] - 1),
            clamp(int(pos.y // TILE_SIZE), 0, self.world_tiles[1] - 1),
        )

    # выполняет cell center
    def cell_center(self, cell):
        return pygame.Vector2(cell[0] * TILE_SIZE + TILE_SIZE / 2, cell[1] * TILE_SIZE + TILE_SIZE / 2)

    # выполняет rebuild navigation
    def rebuild_navigation(self):
        blocked = set()
        probe_radius = 18
        walls = self.active_walls()
        for ty in range(self.world_tiles[1]):
            for tx in range(self.world_tiles[0]):
                center = self.cell_center((tx, ty))
                if (
                    center.x - probe_radius < 0
                    or center.y - probe_radius < 0
                    or center.x + probe_radius > self.world_size.x
                    or center.y + probe_radius > self.world_size.y
                ):
                    blocked.add((tx, ty))
                    continue
                if any(circle_rect_collision(center, probe_radius, wall) for wall in walls):
                    blocked.add((tx, ty))
        self.navigation_blocked = blocked

    # выполняет nearest open cell
    def nearest_open_cell(self, cell):
        if cell not in self.navigation_blocked:
            return cell
        visited = {cell}
        queue = [cell]
        while queue:
            current = queue.pop(0)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (current[0] + dx, current[1] + dy)
                if not (0 <= nxt[0] < self.world_tiles[0] and 0 <= nxt[1] < self.world_tiles[1]):
                    continue
                if nxt in visited:
                    continue
                if nxt not in self.navigation_blocked:
                    return nxt
                visited.add(nxt)
                queue.append(nxt)
        return cell

    # находит path
    def find_path(self, start_pos, end_pos):
        if not self.navigation_blocked:
            return []
        start = self.nearest_open_cell(self.world_to_cell(start_pos))
        goal = self.nearest_open_cell(self.world_to_cell(end_pos))
        if start == goal:
            return []

        frontier = [(0, start)]
        came_from = {start: None}
        cost_so_far = {start: 0}

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (current[0] + dx, current[1] + dy)
                if not (0 <= nxt[0] < self.world_tiles[0] and 0 <= nxt[1] < self.world_tiles[1]):
                    continue
                if nxt in self.navigation_blocked:
                    continue
                new_cost = cost_so_far[current] + 1
                if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                    cost_so_far[nxt] = new_cost
                    priority = new_cost + abs(goal[0] - nxt[0]) + abs(goal[1] - nxt[1])
                    heapq.heappush(frontier, (priority, nxt))
                    came_from[nxt] = current

        if goal not in came_from:
            return []

        path = []
        current = goal
        while current is not None and current != start:
            path.append(self.cell_center(current))
            current = came_from[current]
        path.reverse()
        return path

    # обновляет pickups
    def update_pickups(self, dt):
        for pickup in list(self.pickups):
            pickup.pulse += 4.5 * dt
            if self.player.pos.distance_to(pickup.pos) <= 28:
                self.pickups.remove(pickup)
                if pickup.kind == "dragon_relic":
                    self.dragon_relic_armed = True
                    self.show_toast("Осколок печати у тебя. Жми ПКМ прямо по горящему глазу дракона.")
                    continue
                self.player.hp = min(self.player.max_hp, self.player.hp + pickup.heal)
                self.floaters.append(FloatingText(f"+{pickup.heal}", pickup.pos.copy(), GREEN))
                self.audio.play("heal", 0.42)

    # обновляет assault room
    def update_assault_room(self, dt):
        if not self.assault_started:
            if self.assault_wave_trigger and self.assault_wave_trigger.collidepoint(self.player.pos):
                self.assault_started = True
                self.assault_wave_index = 0
                self.assault_wave_delay = 0.0
                self.spawn_next_assault_wave()
                self.save_checkpoint("assault")
                self.show_toast("Лес проснулся. Держи поляну и не подпускай тварей вплотную.")
            return

        self.update_assault_tutorial()
        if not self.enemies and self.assault_wave_index < len(self.assault_waves):
            if self.assault_wave_delay <= 0:
                self.assault_wave_delay = 1.6
                self.show_toast("В ветвях снова хруст. Следующая волна уже выходит из леса.")
            else:
                self.assault_wave_delay = max(0.0, self.assault_wave_delay - dt)
                if self.assault_wave_delay <= 0:
                    self.spawn_next_assault_wave()
        elif not self.enemies and self.assault_wave_index >= len(self.assault_waves):
            self.assault_ready_to_advance = True
            self.spawn_assault_civilians()
            self.update_assault_civilians(dt)
            if self.assault_teleport_rect and self.assault_teleport_rect.collidepoint(self.player.pos):
                self.setup_dragon_room()
            elif self.assault_wave_index < len(self.assault_waves) + 100:
                self.show_toast("Опушка очищена. Поднимайся по северо-восточной тропе к логову дракона.")
                self.assault_wave_index = len(self.assault_waves) + 100

    # обновляет assault tutorial
    def update_assault_tutorial(self):
        if not self.assault_started:
            return
        if self.assault_tutorial_step == 0 and self.assault_tutorial_move:
            self.assault_tutorial_step = 1
            self.show_toast("ЛКМ — быстрый клинок. Бей, как только тварь подойдёт вплотную.")
        elif self.assault_tutorial_step == 1 and self.assault_tutorial_melee:
            self.assault_tutorial_step = 2
            self.show_toast("ПКМ — усиленная атака. Она тратит ману, зато быстро ломает плотную цель.")
        elif self.assault_tutorial_step == 2 and self.assault_tutorial_special:
            self.assault_tutorial_step = 3
            self.show_toast("Shift — уклонение. Два коротких рывка подряд дают неуязвимость и спасают от удара.")
        elif self.assault_tutorial_step == 3 and self.assault_tutorial_dodge:
            self.assault_tutorial_step = 4
            self.show_toast("Хорошо. Теперь удержи опушку и переживи все три волны.")

    # обновляет ghouls
    def update_ghouls(self, dt):
        for enemy in list(self.enemies):
            velocity = enemy.update_ai(dt, self.player, self)
            self.move_actor(enemy, velocity * dt)
            if enemy.pos.distance_to(self.player.pos) <= enemy.engage_distance(self.player) and enemy.attack_cooldown <= 0:
                enemy.begin_attack_animation()
                enemy.attack_cooldown = enemy.melee_cooldown_duration()
                self.damage_player(enemy.melee_damage())
        self.enemies = [enemy for enemy in self.enemies if not enemy.dead]

    # выполняет дракона оверлей screen anchor
    def dragon_overlay_screen_anchor(self):
        return pygame.Vector2(WINDOW_WIDTH // 2, 144)

    # выполняет дракона оверлей мир anchor
    def dragon_overlay_world_anchor(self):
        return pygame.Vector2(
            self.camera.x + WINDOW_WIDTH / 2 - self.camera.pad_x,
            self.camera.y + 144 - self.camera.pad_y,
        )

    # выполняет дракона eye centers
    def dragon_eye_centers(self):
        center = self.dragon_overlay_screen_anchor()
        return [center + pygame.Vector2(-74, 8), center + pygame.Vector2(74, 8)]

    # выполняет дракона hit circles
    def dragon_hit_circles(self):
        if not self.dragon:
            return []
        anchor = self.dragon_overlay_world_anchor()
        return [
            (anchor, 158),
            (anchor + pygame.Vector2(0, 126), 134),
            (anchor + pygame.Vector2(-214, 58), 94),
            (anchor + pygame.Vector2(214, 58), 94),
        ]

    # выполняет ближнюю hits дракона
    def melee_hits_dragon(self, attack):
        for center, radius in self.dragon_hit_circles():
            delta = center - attack.origin
            distance = delta.length()
            if distance > attack.radius + radius:
                continue
            if delta.length_squared() and abs(attack.direction.angle_to(delta)) > attack.arc_degrees / 2:
                continue
            if line_blocked(attack.origin, center, self.cover):
                continue
            return True
        return False

    # выполняет луч hits дракона
    def beam_hits_dragon(self, beam):
        for center, radius in self.dragon_hit_circles():
            if distance_to_segment(center, beam.start, beam.end) <= beam.width / 2 + radius:
                return True
        return False

    # выполняет снаряд hits дракона
    def projectile_hits_dragon(self, projectile):
        for center, radius in self.dragon_hit_circles():
            if projectile.pos.distance_to(center) <= projectile.radius + radius:
                return True
        return False

    # выполняет explosion hits дракона
    def explosion_hits_dragon(self, epicenter, radius):
        for center, hit_radius in self.dragon_hit_circles():
            if center.distance_to(epicenter) <= radius + hit_radius and not line_blocked(epicenter, center, self.cover):
                return True
        return False

    # выполняет дракона can lose shield
    def dragon_can_lose_shield(self):
        dragon = self.dragon
        return bool(
            dragon
            and dragon.shield > 0
            and self.dragon_relic_armed
            and dragon.mode == "idle"
            and dragon.attack_cooldown > 0
            and dragon.eyes_glowing
            and not dragon.eye_hit_this_window
        )

    # очищает дракона relic pickups
    def clear_dragon_relic_pickups(self):
        self.pickups = [pickup for pickup in self.pickups if pickup.kind != "dragon_relic"]

    # создает дракона relic
    def spawn_dragon_relic(self):
        if not self.dragon or self.dragon.shield <= 0 or self.dragon_relic_armed:
            return
        if any(pickup.kind == "dragon_relic" for pickup in self.pickups):
            return
        positions = [
            pygame.Vector2(5 * TILE_SIZE, 11.8 * TILE_SIZE),
            pygame.Vector2(9 * TILE_SIZE, 12.2 * TILE_SIZE),
            pygame.Vector2(14.5 * TILE_SIZE, 11.3 * TILE_SIZE),
            pygame.Vector2(20 * TILE_SIZE, 12.0 * TILE_SIZE),
            pygame.Vector2(24.5 * TILE_SIZE, 11.6 * TILE_SIZE),
        ]
        self.pickups.append(Pickup(random.choice(positions), kind="dragon_relic"))

    # выполняет stun дракона
    def stun_dragon(self):
        dragon = self.dragon
        if not dragon:
            return
        dragon.mode = "stunned"
        dragon.stun_timer = 20.0
        dragon.attack_cooldown = 0.0
        dragon.recover_timer = 0.0
        dragon.eyes_glowing = False
        dragon.eye_hint_sent = False
        self.dragon_relic_charge = False
        self.dragon_relic_armed = False
        self.clear_dragon_relic_pickups()
        self.fade_cover_spikes()
        self.fade_earth_spikes()
        self.show_toast("Щит пал. Дракон оглушён на 20 секунд и получает усиленный урон.")

    # восстанавливает дракона shield
    def restore_dragon_shield(self):
        dragon = self.dragon
        if not dragon:
            return
        dragon.shield = 4
        dragon.eye_hit_this_window = False
        dragon.eyes_glowing = False
        dragon.mode = "recover"
        dragon.recover_timer = 1.1
        dragon.attack_cooldown = 0.0
        self.dragon_relic_armed = False
        self.dragon_relic_charge = False
        self.clear_dragon_relic_pickups()
        self.show_toast("Дракон пришёл в себя и восстановил щит. Придётся ломать его заново.")

    # выполняет fire дракона relic
    def fire_dragon_relic(self, logical_pos):
        if not self.dragon_relic_armed:
            return
        origin = self.camera.apply(self.player.pos)
        point = pygame.Vector2(logical_pos)
        hit = any(eye.distance_to(point) <= 40 for eye in self.dragon_eye_centers())
        self.relic_effects.append(RelicShotEffect(origin, point, hit))
        self.audio.play("Atak_sun" if self.player.caste == "light" else "Atak_tma", 0.44)
        can_break_shield = self.dragon_can_lose_shield()
        self.dragon_relic_armed = False
        if not can_break_shield:
            self.show_toast("Дракон уже закрыл глаза. Этот выстрел ушёл в пепел.")
            return
        for eye in self.dragon_eye_centers():
            if eye.distance_to(point) <= 40:
                self.dragon.shield = max(0, self.dragon.shield - 1)
                self.dragon.eye_hit_this_window = True
                self.dragon.eyes_glowing = False
                self.audio.play("Atak_sun" if self.player.caste == "light" else "Atak_tma", 0.5, cooldown=0.05)
                if self.dragon.shield > 0:
                    self.show_toast(f"Щит дракона треснул. Осталось {self.dragon.shield} деления.")
                else:
                    self.stun_dragon()
                return
        self.show_toast("Печать ушла мимо глаза. Дракон успел отдёрнуть голову.")

    # создает cover spikes
    def spawn_cover_spikes(self):
        self.audio.play("Kamen_dragon", 0.42, cooldown=0.12)
        candidates = [
            (5, 11.8),
            (8, 9.0),
            (11, 12.2),
            (14, 8.8),
            (17, 11.7),
            (20, 8.6),
            (23, 12.0),
            (26, 9.4),
        ]
        for tx, ty in random.sample(candidates, 5):
            self.rock_spikes.append(
                RockSpike(
                    pygame.Vector2(tx * TILE_SIZE, ty * TILE_SIZE),
                    self.sprite_bank["rock_spike"],
                    blocks_movement=True,
                    damage=0,
                    telegraph=0.65,
                    active_time=4.8,
                    fade_time=0.55,
                    kind="cover",
                )
            )

    # затухает cover spikes
    def fade_cover_spikes(self):
        for spike in self.rock_spikes:
            if spike.kind == "cover":
                spike.begin_fade()

    # затухает earth spikes
    def fade_earth_spikes(self):
        for spike in self.rock_spikes:
            if spike.kind == "earth":
                spike.begin_fade()

    # создает earth spike
    def spawn_earth_spike(self, pos):
        self.audio.play("Kamen_dragon", 0.4, cooldown=0.12)
        earth_spikes = [spike for spike in self.rock_spikes if spike.kind == "earth" and spike.alive]
        if len(earth_spikes) >= 3:
            earth_spikes[0].begin_fade()
        self.rock_spikes.append(
            RockSpike(
                pygame.Vector2(pos),
                self.sprite_bank["rock_spike"],
                blocks_movement=False,
                damage=18,
                telegraph=1.0,
                active_time=3.0,
                fade_time=0.45,
                kind="earth",
            )
        )

    # обновляет rock spikes
    def update_rock_spikes(self, dt):
        if not self.rock_spikes:
            return
        for spike in self.rock_spikes:
            spike.update(dt)
            if spike.just_activated and spike.damage > 0 and self.player.pos.distance_to(spike.pos) <= 60:
                self.damage_player(spike.damage)
        self.rock_spikes = [spike for spike in self.rock_spikes if spike.alive]

    # выполняет begin дракона idle window
    def begin_dragon_idle_window(self, cooldown=5.2):
        dragon = self.dragon
        if not dragon:
            return
        dragon.mode = "idle"
        dragon.attack_cooldown = cooldown
        dragon.eye_hit_this_window = False
        dragon.eyes_glowing = dragon.shield > 0
        dragon.eye_hint_sent = False
        self.clear_dragon_relic_pickups()
        if dragon.shield > 0:
            self.spawn_dragon_relic()

    # запускает next дракона атаку
    def start_next_dragon_attack(self):
        dragon = self.dragon
        if not dragon:
            return
        attack = dragon.attack_cycle[dragon.attack_index]
        dragon.attack_index = (dragon.attack_index + 1) % len(dragon.attack_cycle)
        dragon.last_attack = attack
        dragon.eyes_glowing = False
        dragon.eye_hint_sent = False
        self.clear_dragon_relic_pickups()
        self.dragon_relic_armed = False
        self.dragon_relic_charge = False
        if attack == "tail":
            dragon.mode = "tail_windup"
            dragon.tail_state_timer = 3.0
            dragon.tail_sweep_progress = 0.0
            self.show_toast("Дракон втягивает морду и готовит широкий удар хвостом по самому верху арены.")
        elif attack == "beam":
            self.fade_cover_spikes()
            self.spawn_cover_spikes()
            dragon.mode = "beam_prepare"
            dragon.recover_timer = 2.8
            self.show_toast("Перед лучом из пола поднимаются пики-укрытия. Луч вспыхнет только после короткой паузы.")
        elif attack == "earth":
            dragon.mode = "earth"
            dragon.earth_timer = 10.0
            dragon.earth_spawn_timer = 0.55
            self.show_toast("Земля под ногами трещит. Через миг на отмеченном месте вырастет пик.")
        else:
            dragon.mode = "bullet"
            dragon.bullet_timer = 0.0
            dragon.bullet_bursts = 44
            dragon.bullet_angle = random.uniform(0.0, 360.0)
            self.audio.play("Kamen_dragon", 0.44, cooldown=0.12)
            self.show_toast("Дракон распахивает пасть и выпускает спираль стихийных капель.")

    # обновляет дракона
    def update_dragon(self, dt):
        dragon = self.dragon
        if dragon is None:
            return
        dragon.tick(dt, moving=True)
        dragon.attack_cooldown = max(0.0, dragon.attack_cooldown - dt)
        dragon.recover_timer = max(0.0, dragon.recover_timer - dt)
        dragon.bullet_timer = max(0.0, dragon.bullet_timer - dt)
        dragon.stun_timer = max(0.0, dragon.stun_timer - dt)
        dragon.hover_phase += dt * 1.6
        dragon.anchor.x = self.world_size.x / 2 + math.sin(dragon.hover_phase) * 160
        dragon.anchor.y = 2.0 * TILE_SIZE + math.cos(dragon.hover_phase * 0.8) * 18
        dragon.pos.update(dragon.anchor.x, dragon.anchor.y + 42)

        if dragon.hp <= 0:
            self.audio.play("Dragon_die", 0.62, cooldown=0.4)
            self.clear_dragon_relic_pickups()
            self.fade_cover_spikes()
            self.fade_earth_spikes()
            self.dragon = None
            self.open_story(
                [
                    {
                        "title": "После битвы",
                        "image": "8",
                        "text": "Когда чудовище рушится в пепел, на его шее ты замечаешь обгоревшую карту. На ней отмечен путь к сердцу Разлома, скрытый за горящим лесом.",
                    },
                    {
                        "title": "Печати силы",
                        "image": "9",
                        "text": "Три печати вспыхивают над трупом дракона. Ты успеваешь схватить только одну, прежде чем подземный ветер гасит зал багровой тьмой.",
                    },
                ],
                callback=self.open_upgrade_choice,
            )
            self.show_toast("Пепельный дракон пал.")
            return

        if dragon.mode in {"tail_windup", "tail_sweep"}:
            dragon.mode = "recover"
            dragon.recover_timer = 0.35
            dragon.tail_state_timer = 0.0
            dragon.tail_sweep_progress = 0.0

        if dragon.mode == "stunned":
            if dragon.stun_timer <= 0 and dragon.hp > 0:
                self.restore_dragon_shield()
            return

        if dragon.mode == "idle" and dragon.eyes_glowing and not dragon.eye_hint_sent:
            self.show_toast("Глаза дракона открыты. Подбери осколок и жми ПКМ прямо по глазу, пока он не атакует.")
            dragon.eye_hint_sent = True

        if dragon.mode == "tail_windup":
            dragon.tail_state_timer = max(0.0, dragon.tail_state_timer - dt)
            if dragon.tail_state_timer <= 0:
                zone_height = int(self.world_size.y * 0.52)
                self.enemy_zones.append(
                    ZoneAttack(
                        pygame.Rect(0, 0, int(self.world_size.x), zone_height),
                        28,
                        0.0,
                        0.62,
                        (0, 0, 0),
                        style="invisible",
                    )
                )
                dragon.mode = "tail_sweep"
                dragon.tail_state_timer = 0.52
                dragon.tail_sweep_progress = 0.0
        elif dragon.mode == "tail_sweep":
            dragon.tail_state_timer = max(0.0, dragon.tail_state_timer - dt)
            dragon.tail_sweep_progress = 1.0 - clamp(dragon.tail_state_timer / 0.52, 0.0, 1.0)
            if dragon.tail_state_timer <= 0:
                dragon.tail_sweep_progress = 0.0
                dragon.mode = "recover"
                dragon.recover_timer = 1.1
        elif dragon.mode == "bullet":
            if dragon.bullet_timer <= 0 and dragon.bullet_bursts > 0:
                center = dragon.anchor + pygame.Vector2(0, 42)
                colors = [(246, 138, 78), (118, 182, 246), (225, 239, 248), (176, 124, 88)]
                for index, color in enumerate(colors):
                    for arm in range(2):
                        angle = dragon.bullet_angle + index * 90 + arm * 18
                        direction = pygame.Vector2(1, 0).rotate(angle)
                        speed = 300 + index * 24 + arm * 18
                        self.enemy_projectiles.append(
                            Projectile(
                                center + direction * 54,
                                direction * speed,
                                12,
                                15,
                                color,
                                ttl=4.2,
                                friendly=False,
                                blocked_by_cover=True,
                                shape="drop",
                            )
                        )
                dragon.bullet_bursts -= 1
                dragon.bullet_angle += 15
                dragon.bullet_timer = 0.09
            if dragon.bullet_bursts <= 0:
                dragon.mode = "recover"
                dragon.recover_timer = 0.9
        elif dragon.mode == "earth":
            dragon.earth_timer = max(0.0, dragon.earth_timer - dt)
            dragon.earth_spawn_timer = max(0.0, dragon.earth_spawn_timer - dt)
            if dragon.earth_spawn_timer <= 0:
                self.spawn_earth_spike(self.player.pos.copy())
                dragon.earth_spawn_timer = 1.2
            if dragon.earth_timer <= 0:
                self.fade_earth_spikes()
                dragon.mode = "recover"
                dragon.recover_timer = 1.1
        elif dragon.mode == "beam_prepare":
            if dragon.recover_timer <= 0:
                self.cast_dragon_cataclysm(dragon)
                dragon.mode = "beam"
                dragon.recover_timer = 2.8
        elif dragon.mode == "beam":
            if dragon.recover_timer <= 0:
                self.begin_dragon_idle_window()
        elif dragon.mode == "recover":
            if dragon.recover_timer <= 0:
                self.begin_dragon_idle_window()
        elif dragon.mode == "idle" and dragon.attack_cooldown <= 0:
            self.start_next_dragon_attack()

    # выполняет cast дракона cataclysm
    def cast_dragon_cataclysm(self, dragon):
        origin = self.dragon_overlay_world_anchor()
        sweep = SweepingBeamAttack(
            origin,
            135,
            45,
            self.world_size.y + 640,
            68,
            22,
            0.0,
            2.4,
            (255, 132, 78),
        )
        sweep.lock_to_screen = True
        sweep.screen_anchor_y = 144
        self.enemy_sweeps.append(sweep)
        self.show_toast("Дракон тянет один тяжёлый огненный луч слева направо. Прячься за выросшими пиками.")

    # определяет игрока attacks
    def resolve_player_attacks(self):
        targets = list(self.enemies) + list(self.dummies) + list(self.crystals)
        if self.brother:
            targets.append(self.brother)

        for attack in self.player_arcs:
            if self.dragon and id(self.dragon) not in attack.hit_ids and self.melee_hits_dragon(attack):
                attack.hit_ids.add(id(self.dragon))
                self.apply_damage_to_target(self.dragon, random.randint(max(6, attack.damage - 3), attack.damage + 3))
            for target in list(targets):
                target_center = target.combat_center() if hasattr(target, "combat_center") else target.pos
                if attack.can_hit(target) and not line_blocked(attack.origin, target_center, self.cover):
                    attack.hit_ids.add(id(target))
                    self.apply_damage_to_target(target, random.randint(max(6, attack.damage - 3), attack.damage + 3))

        for beam in self.player_beams:
            if not beam.is_active:
                continue
            if self.dragon and id(self.dragon) not in beam.hit_ids and self.beam_hits_dragon(beam):
                beam.hit_ids.add(id(self.dragon))
                self.apply_damage_to_target(self.dragon, beam.damage)
            for target in list(targets):
                if id(target) in beam.hit_ids:
                    continue
                if beam.can_hit(target):
                    beam.hit_ids.add(id(target))
                    self.apply_damage_to_target(target, beam.damage)

        for projectile in list(self.player_projectiles):
            if self.dragon and id(self.dragon) not in projectile.hit_ids and self.projectile_hits_dragon(projectile):
                projectile.hit_ids.add(id(self.dragon))
                self.apply_damage_to_target(self.dragon, projectile.damage)
                if projectile.explosive_radius > 0:
                    self.explode_projectile(projectile, targets + [self.dragon], self.dragon)
                if projectile.pierce > 0:
                    projectile.pierce -= 1
                else:
                    projectile.ttl = 0
                continue
            for target in list(targets):
                if id(target) in projectile.hit_ids:
                    continue
                target_rect = target.combat_rect() if hasattr(target, "combat_rect") else pygame.Rect(
                    int(target.pos.x - target.radius),
                    int(target.pos.y - target.radius),
                    target.radius * 2,
                    target.radius * 2,
                )
                if circle_rect_collision(projectile.pos, projectile.radius, target_rect):
                    projectile.hit_ids.add(id(target))
                    self.apply_damage_to_target(target, projectile.damage)
                    if projectile.explosive_radius > 0:
                        self.explode_projectile(projectile, targets, target)
                    if projectile.pierce > 0:
                        projectile.pierce -= 1
                    else:
                        projectile.ttl = 0
                    if not projectile.alive:
                        break

    # определяет enemy attacks
    def resolve_enemy_attacks(self):
        for projectile in self.enemy_projectiles:
            if circle_rect_collision(projectile.pos, projectile.radius, self.player.combat_rect()):
                projectile.ttl = 0
                self.damage_player(projectile.damage)

        for beam in self.enemy_beams:
            if beam.can_hit(self.player) and beam.tick_timer <= 0:
                beam.tick_timer = 0.18
                self.damage_player(beam.damage)

        for zone in self.enemy_zones:
            if isinstance(zone, MiasmaZoneAttack):
                if zone.is_active and zone.can_hit(self.player):
                    self.player.apply_slow(1.2)
                    if zone.tick_timer <= 0:
                        zone.tick_timer = zone.tick_interval
                        self.damage_player(zone.damage)
                continue
            if zone.is_active and not zone.hit_player and zone.can_hit(self.player):
                zone.hit_player = True
                self.damage_player(zone.damage)

        for sweep in self.enemy_sweeps:
            if sweep.can_hit(self.player) and sweep.tick_timer <= 0:
                sweep.tick_timer = 0.16
                self.damage_player(sweep.damage)

        for ring in self.enemy_rings:
            if ring.is_active and not ring.hit_player and ring.can_hit(self.player):
                ring.hit_player = True
                self.damage_player(ring.damage)

    # выполняет explode снаряд
    def explode_projectile(self, projectile, targets, primary_target):
        epicenter = projectile.pos.copy()
        for target in targets:
            if target is primary_target:
                continue
            if isinstance(target, DragonBoss):
                if self.explosion_hits_dragon(epicenter, projectile.explosive_radius):
                    self.apply_damage_to_target(target, int(projectile.damage * 0.65))
                continue
            if (
                circle_rect_collision(epicenter, projectile.explosive_radius, target.combat_rect() if hasattr(target, "combat_rect") else pygame.Rect(int(target.pos.x - target.radius), int(target.pos.y - target.radius), target.radius * 2, target.radius * 2))
                and not line_blocked(epicenter, target.combat_center() if hasattr(target, "combat_center") else target.pos, self.cover)
            ):
                self.apply_damage_to_target(target, int(projectile.damage * 0.65))
        self.floaters.append(FloatingText("Тьма", epicenter, VIOLET))

    # применяет damage to target
    def apply_damage_to_target(self, target, damage):
        if isinstance(target, DragonBoss) and target.shield > 0:
            return
        if isinstance(target, DragonBoss) and target.mode == "stunned":
            damage = int(round(damage * 1.75))
        if target.take_damage(damage):
            color = GOLD if self.player.caste == "light" else VIOLET
            self.floaters.append(FloatingText(str(int(damage)), target.pos.copy(), color))
            if isinstance(target, Ghoul) and target.dead and not target.loot_rolled:
                target.loot_rolled = True
                if random.random() < 0.5:
                    self.pickups.append(Pickup(target.pos.copy()))
            if isinstance(target, RuneCrystal) and target.dead:
                self.floaters.append(FloatingText("Руна лопнула", target.pos.copy(), (193, 152, 255)))

    # выполняет damage игрока
    def damage_player(self, amount):
        if self.player.take_damage(amount):
            self.floaters.append(FloatingText(f"-{int(amount)}", self.player.pos.copy(), (255, 110, 110)))
            self.audio.play("Uron_igrok", 0.46, cooldown=0.06)

    # перемещает actor
    def move_actor(self, actor, delta):
        if delta.length_squared() == 0:
            return
        if delta.x != 0:
            self.resolve_actor_axis(actor, "x", delta.x)
        if delta.y != 0:
            self.resolve_actor_axis(actor, "y", delta.y)
        self.clamp_actor_to_world(actor)

    # ограничивает actor to мир
    def clamp_actor_to_world(self, actor):
        actor.pos.x = clamp(actor.pos.x, actor.radius, self.world_size.x - actor.radius)
        actor.pos.y = clamp(actor.pos.y, actor.radius, self.world_size.y - actor.radius)

    # выполняет actor коллизию targets
    def actor_collision_targets(self, actor):
        targets = []
        if actor in self.enemies:
            targets.extend(enemy for enemy in self.enemies if enemy is not actor and not enemy.dead)
        elif actor in self.town_npcs:
            targets.extend(npc for npc in self.town_npcs if npc is not actor)
        return targets

    # определяет actor entity overlap
    def resolve_actor_entity_overlap(self, actor, axis, amount):
        skin = 0.01
        if axis == "x":
            resolved = actor.pos.x
            for other in self.actor_collision_targets(actor):
                vertical_gap = abs(actor.pos.y - other.pos.y)
                min_distance = actor.radius + other.radius
                if vertical_gap >= min_distance:
                    continue
                horizontal_gap = abs(resolved - other.pos.x)
                if horizontal_gap >= min_distance:
                    continue
                if amount > 0:
                    resolved = min(resolved, other.pos.x - min_distance - skin)
                else:
                    resolved = max(resolved, other.pos.x + min_distance + skin)
            actor.pos.x = resolved
        else:
            resolved = actor.pos.y
            for other in self.actor_collision_targets(actor):
                horizontal_gap = abs(actor.pos.x - other.pos.x)
                min_distance = actor.radius + other.radius
                if horizontal_gap >= min_distance:
                    continue
                vertical_gap = abs(resolved - other.pos.y)
                if vertical_gap >= min_distance:
                    continue
                if amount > 0:
                    resolved = min(resolved, other.pos.y - min_distance - skin)
                else:
                    resolved = max(resolved, other.pos.y + min_distance + skin)
            actor.pos.y = resolved

    # определяет actor axis
    def resolve_actor_axis(self, actor, axis, amount):
        skin = 0.01
        new_pos = actor.pos.copy()
        if axis == "x":
            new_pos.x += amount
        else:
            new_pos.y += amount

        new_pos.x = clamp(new_pos.x, actor.radius, self.world_size.x - actor.radius)
        new_pos.y = clamp(new_pos.y, actor.radius, self.world_size.y - actor.radius)

        bounds = self.actor_bounds(actor, new_pos)
        collisions = [wall for wall in self.active_walls() if self.bounds_hit_wall(bounds, wall)]
        if not collisions:
            actor.pos = new_pos
            self.resolve_actor_entity_overlap(actor, axis, amount)
            return

        if axis == "x":
            resolved_x = new_pos.x
            if amount > 0:
                for wall in collisions:
                    resolved_x = min(resolved_x, wall.left - actor.radius - skin)
            else:
                for wall in collisions:
                    resolved_x = max(resolved_x, wall.right + actor.radius + skin)
            actor.pos.x = resolved_x
        else:
            resolved_y = new_pos.y
            if amount > 0:
                for wall in collisions:
                    resolved_y = min(resolved_y, wall.top - actor.radius - skin)
            else:
                for wall in collisions:
                    resolved_y = max(resolved_y, wall.bottom + actor.radius + skin)
            actor.pos.y = resolved_y
        self.resolve_actor_entity_overlap(actor, axis, amount)

    # обновляет туннель
    def update_tunnel(self, dt):
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(
            (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
            (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        if move.length_squared() > 0:
            move = move.normalize()
            self.tunnel_player += move * 182 * dt
        self.tunnel_player.x = clamp(self.tunnel_player.x, 40, WINDOW_WIDTH - 40)
        self.tunnel_player.y = clamp(self.tunnel_player.y, 40, WINDOW_HEIGHT - 40)

        if not self.tunnel_passable(self.tunnel_player):
            self.tunnel_player = pygame.Vector2(self.tunnel_start)
            self.show_toast("Пламя лизнуло ноги. Придётся начать проход заново.")

        if self.tunnel_player.distance_to(self.tunnel_goal) < 42:
            self.open_story(
                [
                    {
                        "title": "У края Разлома",
                        "image": "10",
                        "text": "Тропа выводит тебя в мёртвый зал, где свет и тьма сплетены в один узел. Там стоит твой брат. Над его ладонями вращаются белая и чёрная сферы.",
                    },
                    {
                        "title": "Истина",
                        "image": "11",
                        "text": "Он пережил ту ночь и, пытаясь обрести силу спасти всё сразу, вобрал обе касты. Разлом сделал его сосудом. Теперь в нём живут и Свет, и Тьма, а человеческое держится на остатке воли.",
                    },
                ],
                callback=self.setup_brother_room,
            )

    # обновляет туннель room
    def update_tunnel_room(self, dt):
        if self.tunnel_map_template and self.map_base_layers:
            for fire_rect in self.tunnel_fire_rects:
                if fire_rect.colliderect(self.player.combat_rect()):
                    self.damage_player(max(self.player.max_hp, 9999))
                    self.show_toast("Пламя дотянулось до тебя. Один шаг мимо — и путь начнётся заново.")
                    return
            exit_rect = getattr(self, "tunnel_exit_rect", None)
            if exit_rect and exit_rect.colliderect(self.player.combat_rect()):
                self.open_story(
                    [
                        {
                            "title": "У края Разлома",
                            "image": "10",
                            "text": "Тропа выводит тебя в мёртвый зал, где свет и тьма сплетены в один узел. Там стоит твой брат. Над его ладонями вращаются белая и чёрная сферы.",
                        },
                        {
                            "title": "Истина",
                            "image": "11",
                            "text": "Он пережил ту ночь и, пытаясь обрести силу спасти всё сразу, вобрал обе касты. Разлом сделал его сосудом. Теперь в нём живут и Свет, и Тьма, а человеческое держится на остатке воли.",
                        },
                    ],
                    callback=self.setup_brother_room,
                )
            return
        self.update_tunnel(dt)

    # выполняет туннель passable
    def tunnel_passable(self, position):
        samples = [
            (int(position.x), int(position.y)),
            (int(position.x + 6), int(position.y)),
            (int(position.x - 6), int(position.y)),
            (int(position.x), int(position.y + 6)),
            (int(position.x), int(position.y - 6)),
        ]
        for x, y in samples:
            if self.tunnel_mask.get_at((x, y))[0] < 200:
                return False
        return True

    # обновляет брата
    def update_brother(self, dt):
        boss = self.brother
        if boss is None:
            return
        if boss.hp <= 0:
            self.brother = None
            self.open_ending_choice()
            return

        moving = boss.dash_time > 0 or not boss.summon_phase
        boss.tick(dt, moving=moving)
        boss.light_beam_cooldown = max(0.0, boss.light_beam_cooldown - dt)
        boss.dark_slam_cooldown = max(0.0, boss.dark_slam_cooldown - dt)
        boss.dash_cooldown = max(0.0, boss.dash_cooldown - dt)
        boss.super_cooldown = max(0.0, boss.super_cooldown - dt)

        if boss.dash_time > 0:
            boss.dash_time -= dt
            if boss.dash_direction.x != 0:
                boss.facing_x = -1 if boss.dash_direction.x < 0 else 1
            self.move_actor(boss, boss.dash_direction * boss.speed * 6.5 * dt)
            boss.iframes = max(boss.iframes, boss.dash_time)
            return

        if boss.summon_phase:
            self.update_ghouls(dt)
            if not self.enemies:
                boss.summon_phase = False
                self.show_toast("Брат вновь поднимает сферы и идёт в бой.")
            return

        to_player = self.player.pos - boss.pos
        distance = max(1.0, to_player.length())
        direction = to_player / distance
        if direction.x != 0:
            boss.facing_x = -1 if direction.x < 0 else 1
        self.move_actor(boss, direction * boss.speed * dt)

        if not boss.summon_triggered and self.player.hp < 25:
            boss.summon_triggered = True
            boss.summon_phase = True
            boss.begin_summon()
            self.enemies = [
                Ghoul((8 * TILE_SIZE, 4 * TILE_SIZE), self.sprite_bank["ghoul"], summoned=True, walk_frames=self.sprite_bank.get("ghoul_walk"), attack_variants=self.sprite_bank.get("ghoul_attacks"), death_frames=self.sprite_bank.get("ghoul_death")),
                Ghoul((12 * TILE_SIZE, 8 * TILE_SIZE), self.sprite_bank["ghoul"], summoned=True, walk_frames=self.sprite_bank.get("ghoul_walk"), attack_variants=self.sprite_bank.get("ghoul_attacks"), death_frames=self.sprite_bank.get("ghoul_death")),
                Ghoul((18 * TILE_SIZE, 8 * TILE_SIZE), self.sprite_bank["ghoul"], summoned=True, walk_frames=self.sprite_bank.get("ghoul_walk"), attack_variants=self.sprite_bank.get("ghoul_attacks"), death_frames=self.sprite_bank.get("ghoul_death")),
                Ghoul((22 * TILE_SIZE, 4 * TILE_SIZE), self.sprite_bank["ghoul"], summoned=True, walk_frames=self.sprite_bank.get("ghoul_walk"), attack_variants=self.sprite_bank.get("ghoul_attacks"), death_frames=self.sprite_bank.get("ghoul_death")),
            ]
            self.show_toast("Брат останавливается и зовёт слабых тварей. Сейчас он не атакует.")
            return

        if boss.dash_cooldown <= 0:
            boss.dash_direction = direction if direction.length_squared() else pygame.Vector2(0, 1)
            boss.dash_time = 0.34
            boss.iframes = 0.34
            boss.dash_cooldown = random.uniform(6.0, 7.0)
            return

        if boss.super_cooldown <= 0:
            center = self.player.pos.lerp(boss.pos, 0.35)
            self.gravity_orbs.append(GravityOrb(center))
            self.audio.play("Black_dura", 0.54)
            boss.super_cooldown = 30.0
            self.show_toast("Чёрно-белая сфера выворачивает воздух и тянет тебя к себе.")

        if distance < 150 and boss.dark_slam_cooldown <= 0:
            boss.begin_attack("attack_2", duration=0.56)
            self.enemy_rings.append(RingAttack(boss.pos.copy(), 18, 140, 20, 0.28, 0.24, (100, 72, 205)))
            boss.dark_slam_cooldown = 2.6
        elif boss.light_beam_cooldown <= 0:
            boss.begin_attack("attack_1", duration=0.56)
            end = clip_line_by_blockers(boss.pos, boss.pos + direction * 1700, self.cover)
            self.enemy_beams.append(BeamAttack(boss.pos.copy(), end, 20, 18, 0.62, 0.42, (246, 242, 203), friendly=False))
            boss.light_beam_cooldown = 3.0

