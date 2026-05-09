import re
import xml.etree.ElementTree as ET

from core import *
from data import MENU_ITEMS
from entities import *
from story import StoryMixin
from world import WorldMixin
from ui import UIMixin


class BloodRiftGame(WorldMixin, StoryMixin, UIMixin):

    def __init__(self):
        pygame.init()

        self.first_launch_setup = not CONFIG_PATH.exists()
        self.desktop_size = self.detect_desktop_size()
        self.config = self.load_config_data()
        pygame.display.set_caption("Blood Rift")
        initial_size, initial_flags = self.display_mode_for_size(
            self.config["window_width"],
            self.config["window_height"],
            self.config.get("fullscreen", False),
        )
        self.window = pygame.display.set_mode(initial_size, initial_flags)
        self.screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)).convert()
        if initial_flags & pygame.NOFRAME:
            self.move_window(0, 0)
        else:
            self.center_window()
        self.clock = pygame.time.Clock()
        ensure_generated_assets()

        self.audio = AudioBus()
        self.audio.set_music_volume(self.config["music_volume"])
        self.audio.set_sfx_volume(self.config["sfx_volume"])
        self.pending_config = dict(self.config)

        self.init_fonts()
        self.init_assets()
        self.camera = Camera(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.init_scene_state()
        self.init_story_state()
        self.init_world_state()
        self.init_combat_state()
        self.init_special_scene_state()

    # собирает текст подсказки для экрана настроек
    def build_settings_notice(self):
        return (
            "Выбери размер окна и режим экрана, нажми Применить и затем Сохранить."
            if self.first_launch_setup
            else "Настрой звук, размер окна, полноэкранный режим и управление."
        )

    # ищет путь к пиксельному шрифту в системе
    def find_pixel_font_path(self):
        pixel_candidates = [
            Path(r"C:\Windows\Fonts\CascadiaMono.ttf"),
            Path(r"C:\Windows\Fonts\consola.ttf"),
            Path(r"C:\Windows\Fonts\lucon.ttf"),
        ]
        return next((str(path) for path in pixel_candidates if path.exists()), None)

    # инициализирует набор шрифтов интерфейса
    def init_fonts(self):
        pixel_path = self.find_pixel_font_path()
        self.title_font = PixelFont(pixel_path, 82)
        self.menu_font = PixelFont(pixel_path, 32)
        self.body_font = PixelFont(pixel_path, 36)
        self.small_font = PixelFont(pixel_path, 22)
        self.hud_font = PixelFont(pixel_path, 20)
        self.boss_font = PixelFont(pixel_path, 20)

    # инициализирует меню арт и игровые ассеты
    def init_assets(self):
        self.menu_art = None
        if MENU_ART_PATH.exists():
            try:
                self.menu_art = pygame.image.load(MENU_ART_PATH).convert()
                self.menu_art = pygame.transform.smoothscale(self.menu_art, (WINDOW_WIDTH, WINDOW_HEIGHT))
            except pygame.error:
                self.menu_art = None

        self.tile_bank = self.build_tile_bank()
        self.sprite_bank = self.load_sprite_bank()
        self.vn_portraits = self.load_vn_portraits()
        self.story_images = self.load_story_images()
        self.assault_map_template = self.load_assault_map_definition()
        self.dragon_map_template = self.load_dragon_map_definition()
        self.tunnel_map_template = self.load_tunnel_map_definition()
        self.brother_map_template = self.load_brother_map_definition()
        self.dragon_background_layers = self.load_dragon_background_layers()

    # инициализирует состояние меню и экранов выбора
    def init_scene_state(self):
        self.running = True
        self.scene = "settings" if self.first_launch_setup else "menu"
        self.chapter = ""
        self.menu_items = list(MENU_ITEMS)
        self.menu_index = 0
        self.settings_window_index = self.window_preset_index_from_size(
            self.pending_config["window_width"], self.pending_config["window_height"]
        )
        self.settings_resolution_dropdown_open = False
        self.settings_notice = self.build_settings_notice()
        self.settings_return_scene = "menu"
        self.settings_return_stats_overlay = False
        self.choice_focus = 0
        self.upgrade_focus = 0
        self.ending_focus = 0

    # инициализирует состояние пролога, катсцен и диалогов
    def init_story_state(self):
        self.story_pages = []
        self.story_index = 0
        self.story_callback = None
        self.story_is_ending = False
        self.story_text_progress = 0.0
        self.story_prompt_timer = 0.0
        self.story_choice_mode = False
        self.story_choice_index = 0
        self.story_hover_choice = None
        self.story_transition = None
        self.story_intro_mode = None
        self.story_intro_timer = 0.0
        self.dialogue_entries = []
        self.dialogue_index = 0
        self.dialogue_choice_index = 0
        self.dialogue_callback = None
        self.dialogue_backdrop = "world"
        self.dialogue_entry_timer = 0.0
        self.toast = ""
        self.toast_timer = 0.0
        self.wave_banner_title = ""
        self.wave_banner_subtitle = ""
        self.wave_banner_timer = 0.0
        self.defeat_flash = 0.0
        self.stats_overlay = False
        self.player_hp_display = 100.0
        self.player_mana_display = 100.0

    # инициализирует состояние карты, слоёв и навигации
    def init_world_state(self):
        self.world_tiles = (30, 16)
        self.world_size = pygame.Vector2(self.world_tiles[0] * TILE_SIZE, self.world_tiles[1] * TILE_SIZE)
        self.walls = []
        self.cover = []
        self.decor = []
        self.ground_tiles = []
        self.detail_tiles = []
        self.overlay_tiles = []
        self.map_layers = []
        self.map_base_layers = []
        self.map_overlay_layers = []
        self.map_tilesets = []
        self.map_gid_surfaces = {}
        self.map_object_layers = {}
        self.current_map = None
        self.current_map_path = None
        self.navigation_blocked = set()
        self.town_npcs = []
        self.town_npc_spawns = []
        self.assault_spawn_point = None
        self.assault_wave_trigger = None
        self.assault_teleport_rect = None
        self.assault_civilians_spawned = False
        self.tunnel_fire_rects = []

    # инициализирует сущности и боевые списки
    def init_combat_state(self):
        self.player = None
        self.master = None
        self.dragon = None
        self.brother = None
        self.enemies = []
        self.dummies = []
        self.crystals = []
        self.pickups = []
        self.rock_spikes = []
        self.player_arcs = []
        self.player_projectiles = []
        self.player_beams = []
        self.relic_effects = []
        self.enemy_projectiles = []
        self.enemy_beams = []
        self.enemy_zones = []
        self.enemy_sweeps = []
        self.enemy_rings = []
        self.gravity_orbs = []
        self.floaters = []
        self.assault_waves = []
        self.assault_wave_index = 0
        self.assault_wave_delay = 0.0
        self.assault_ready_to_advance = False
        self.assault_tutorial_step = 0
        self.assault_tutorial_move = False
        self.assault_tutorial_melee = False
        self.assault_tutorial_special = False
        self.assault_tutorial_dodge = False
        self.assault_started = False
        self.assault_stream_rects = []
        self.assault_forest_rects = []
        self.dragging_volume_key = None

    # инициализирует состояние реликта, катсцены жителя и лабиринта
    def init_special_scene_state(self):
        self.dragon_relic_armed = False
        self.dragon_relic_charge = False
        self.dragon_relic_charge_time = 0.0
        self.dragon_relic_pickup_id = 0
        self.resident_intro_phase = 0
        self.resident_intro_timer = 0.0
        self.resident_intro_hero_target = pygame.Vector2()
        self.resident_intro_resident_target = pygame.Vector2()
        self.player_step_timer = 0.0
        self.tunnel_points = []
        self.tunnel_widths = []
        self.tunnel_rects = []
        self.tunnel_mask = None
        self.tunnel_start = pygame.Vector2(180, 900)
        self.tunnel_goal = pygame.Vector2(1700, 170)
        self.tunnel_player = pygame.Vector2(self.tunnel_start)
        self.tunnel_message = "Держись в тропе. Стоит коснуться огня, и путь начнётся заново."

    # загружает конфиг data
    def load_config_data(self):
        config = default_config()
        if not CONFIG_PATH.exists():
            return config
        try:
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return config
        if loaded.get("version") != CONFIG_VERSION:
            return config
        width = int(loaded.get("window_width", config["window_width"]))
        height = int(loaded.get("window_height", config["window_height"]))
        fullscreen = loaded.get("fullscreen")
        if fullscreen is None:
            fullscreen = (width, height) == WINDOW_PRESETS[-1] or width >= self.desktop_size[0] or height >= self.desktop_size[1]
        config.update(
            {
                "window_width": width,
                "window_height": height,
                "fullscreen": bool(fullscreen),
                "music_volume": clamp(float(loaded.get("music_volume", config["music_volume"])), 0.0, 1.0),
                "sfx_volume": clamp(float(loaded.get("sfx_volume", config["sfx_volume"])), 0.0, 1.0),
            }
        )
        return config

    # сохраняет конфиг data
    def save_config_data(self):
        payload = dict(self.pending_config)
        payload["version"] = CONFIG_VERSION
        CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.config = dict(self.pending_config)
        self.first_launch_setup = False

    # открывает настройки
    def open_settings(self, return_scene=None, return_stats_overlay=None):
        self.pending_config = dict(self.config)
        self.settings_window_index = self.window_preset_index_from_size(
            self.pending_config["window_width"], self.pending_config["window_height"]
        )
        self.settings_resolution_dropdown_open = False
        self.audio.set_music_volume(self.pending_config["music_volume"])
        self.audio.set_sfx_volume(self.pending_config["sfx_volume"])
        self.settings_notice = self.build_settings_notice()
        if return_scene is None:
            return_scene = "gameplay" if self.scene == "gameplay" else "menu"
        if return_stats_overlay is None:
            return_stats_overlay = bool(self.scene == "gameplay" and self.stats_overlay)
        self.settings_return_scene = return_scene
        self.settings_return_stats_overlay = bool(return_stats_overlay)
        self.scene = "settings"

    # закрывает настройки
    def close_settings(self, restore_audio=False):
        if restore_audio:
            self.audio.set_music_volume(self.config["music_volume"])
            self.audio.set_sfx_volume(self.config["sfx_volume"])
        self.settings_resolution_dropdown_open = False
        self.scene = self.settings_return_scene
        self.stats_overlay = self.settings_return_stats_overlay if self.settings_return_scene == "gameplay" else False

    # определяет desktop size
    def detect_desktop_size(self):
        try:
            if sys.platform == "win32" and pygame.display.get_driver() != "dummy":
                user32 = ctypes.windll.user32
                try:
                    user32.SetProcessDPIAware()
                except Exception:
                    pass
                width = int(user32.GetSystemMetrics(0))
                height = int(user32.GetSystemMetrics(1))
                if width > 0 and height > 0:
                    return width, height
        except Exception:
            pass
        desktop_sizes = pygame.display.get_desktop_sizes()
        if desktop_sizes:
            width, height = desktop_sizes[0]
            return int(width), int(height)
        return WINDOW_WIDTH, WINDOW_HEIGHT

    # выполняет window preset index from size
    def window_preset_index_from_size(self, width, height):
        for index, preset in enumerate(WINDOW_PRESETS):
            if preset == (int(width), int(height)):
                return index
        return 0

    # выполняет display mode for size
    def display_mode_for_size(self, width, height, fullscreen=False):
        width = int(width)
        height = int(height)
        if fullscreen and pygame.display.get_driver() != "dummy":
            return self.desktop_size, pygame.NOFRAME
        max_width = max(640, self.desktop_size[0] - 32)
        max_height = max(480, self.desktop_size[1] - 72)
        width = clamp(width, 640, max_width)
        height = clamp(height, 480, max_height)
        return (int(width), int(height)), 0

    # перемещает window
    def move_window(self, x, y):
        try:
            if sys.platform != "win32":
                return
            if pygame.display.get_driver() == "dummy":
                return
            wm_info = pygame.display.get_wm_info()
            hwnd = wm_info.get("window")
            if not hwnd:
                return
            user32 = ctypes.windll.user32
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_SHOWWINDOW = 0x0040
            user32.SetWindowPos(hwnd, 0, int(x), int(y), 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_SHOWWINDOW)
        except Exception:
            pass

    # центрирует window
    def center_window(self):
        try:
            if sys.platform != "win32":
                return
            if pygame.display.get_driver() == "dummy":
                return
            wm_info = pygame.display.get_wm_info()
            hwnd = wm_info.get("window")
            if not hwnd:
                return
            desktop_w, desktop_h = self.desktop_size
            window_w, window_h = self.window.get_size()
            x = max(0, (desktop_w - window_w) // 2)
            y = max(0, (desktop_h - window_h) // 2)
            self.move_window(x, y)
        except Exception:
            pass

    # применяет pending настройки
    def apply_pending_settings(self):
        size, flags = self.display_mode_for_size(
            self.pending_config["window_width"],
            self.pending_config["window_height"],
            self.pending_config.get("fullscreen", False),
        )
        self.window = pygame.display.set_mode(size, flags)
        if flags & pygame.NOFRAME:
            self.move_window(0, 0)
        else:
            self.center_window()

    # выполняет window to logical
    def window_to_logical(self, pos):
        view_rect = self.logical_view_rect()
        if view_rect.width <= 0 or view_rect.height <= 0:
            return pos
        local_x = clamp(pos[0] - view_rect.x, 0, view_rect.width - 1)
        local_y = clamp(pos[1] - view_rect.y, 0, view_rect.height - 1)
        x = int(local_x * WINDOW_WIDTH / view_rect.width)
        y = int(local_y * WINDOW_HEIGHT / view_rect.height)
        return clamp(x, 0, WINDOW_WIDTH - 1), clamp(y, 0, WINDOW_HEIGHT - 1)

    # выполняет текущий mouse pos
    def current_mouse_pos(self):
        return self.window_to_logical(pygame.mouse.get_pos())

    # выполняет logical view rect
    def logical_view_rect(self):
        window_width, window_height = self.window.get_size()
        if window_width <= 0 or window_height <= 0:
            return pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        scale = min(window_width / WINDOW_WIDTH, window_height / WINDOW_HEIGHT)
        draw_width = max(1, int(WINDOW_WIDTH * scale))
        draw_height = max(1, int(WINDOW_HEIGHT * scale))
        offset_x = (window_width - draw_width) // 2
        offset_y = (window_height - draw_height) // 2
        return pygame.Rect(offset_x, offset_y, draw_width, draw_height)

    # собирает тайл bank
    def build_tile_bank(self):
        tile = TILE_SIZE

        # выполняет speckled тайл
        def speckled_tile(base, palette, seed, count=34):
            surface = pygame.Surface((tile, tile), pygame.SRCALPHA)
            surface.fill(base)
            rng = random.Random(seed)
            for y in range(0, tile, 4):
                shade = palette[(y // 4 + seed) % len(palette)]
                pygame.draw.rect(surface, shade, (0, y, tile, 4))
            for _ in range(count):
                color = palette[rng.randrange(len(palette))]
                x = rng.randrange(0, tile - 4, 2)
                y = rng.randrange(0, tile - 4, 2)
                w = rng.choice((2, 4, 4, 6))
                h = rng.choice((2, 4, 4, 6))
                pygame.draw.rect(surface, color, (x, y, w, h))
            return surface

        # выполняет grass тайл
        def grass_tile(seed, deep=False):
            if deep:
                base = (34, 51, 37)
                palette = [(28, 42, 31), (42, 63, 44), (55, 78, 51), (77, 102, 62)]
            else:
                base = (58, 80, 56)
                palette = [(46, 65, 45), (68, 92, 63), (82, 112, 71), (102, 132, 82)]
            surface = speckled_tile(base, palette, seed)
            for x in range(0, tile, 16):
                pygame.draw.line(surface, (20, 32, 20, 80), (x, 0), (x, tile), 1)
            return surface

        # выполняет dirt тайл
        def dirt_tile(seed):
            surface = speckled_tile(
                (112, 89, 63),
                [(90, 70, 48), (124, 99, 70), (142, 118, 82), (72, 54, 40)],
                seed,
                count=42,
            )
            rng = random.Random(seed * 11 + 7)
            for _ in range(10):
                x = rng.randrange(4, tile - 10)
                y = rng.randrange(4, tile - 10)
                pygame.draw.ellipse(surface, (76, 60, 44), (x, y, 6, 4))
            return surface

        # выполняет bank тайл
        def bank_tile(seed):
            surface = dirt_tile(seed)
            rng = random.Random(seed * 13 + 9)
            for _ in range(12):
                x = rng.randrange(4, tile - 8)
                y = rng.randrange(4, tile - 8)
                pygame.draw.rect(surface, (86, 114, 72), (x, y, 4, 4))
            return surface

        # выполняет water тайл
        def water_tile(seed):
            surface = pygame.Surface((tile, tile), pygame.SRCALPHA)
            surface.fill((34, 66, 88))
            rng = random.Random(seed * 17 + 3)
            for y in range(0, tile, 6):
                color = (28, 56 + (y % 12), 82 + (y % 18))
                pygame.draw.rect(surface, color, (0, y, tile, 4))
            for _ in range(10):
                x = rng.randrange(4, tile - 14)
                y = rng.randrange(4, tile - 8)
                w = rng.randrange(8, 18)
                pygame.draw.line(surface, (162, 205, 218), (x, y), (x + w, y), 2)
            return surface

        # выполняет bridge тайл
        def bridge_tile(seed):
            surface = pygame.Surface((tile, tile), pygame.SRCALPHA)
            surface.fill((80, 58, 39))
            for y in range(4, tile, 12):
                pygame.draw.rect(surface, (104, 74, 51), (0, y, tile, 8))
                pygame.draw.line(surface, (48, 34, 24), (0, y), (tile, y), 2)
            for x in (10, tile - 12):
                pygame.draw.rect(surface, (58, 40, 28), (x, 0, 4, tile))
            for x in range(12, tile - 12, 16):
                pygame.draw.circle(surface, (28, 22, 18), (x, 14), 2)
                pygame.draw.circle(surface, (28, 22, 18), (x, tile - 14), 2)
            return surface

        # выполняет flower тайл
        def flower_tile(seed):
            surface = pygame.Surface((tile, tile), pygame.SRCALPHA)
            rng = random.Random(seed * 19 + 11)
            for _ in range(14):
                x = rng.randrange(8, tile - 8)
                y = rng.randrange(10, tile - 8)
                pygame.draw.line(surface, (78, 114, 62), (x, y), (x, y + 5), 1)
                color = rng.choice(((232, 232, 236), (244, 206, 132), (196, 176, 228)))
                pygame.draw.circle(surface, color, (x, y), 2)
            return surface

        # выполняет tree тайл
        def tree_tile(seed):
            surface = pygame.Surface((tile, tile), pygame.SRCALPHA)
            rng = random.Random(seed * 23 + 5)
            pygame.draw.rect(surface, (74, 50, 31), (26, 34, 12, 22))
            canopy_colors = [(38, 60, 36), (48, 74, 43), (64, 92, 52)]
            for radius, offset in ((18, (-10, -2)), (20, (0, -10)), (18, (10, -1)), (15, (0, 8))):
                color = canopy_colors[rng.randrange(len(canopy_colors))]
                pygame.draw.circle(surface, color, (32 + offset[0], 28 + offset[1]), radius)
            for _ in range(6):
                x = rng.randrange(10, tile - 10)
                y = rng.randrange(8, 34)
                pygame.draw.circle(surface, (84, 114, 66, 180), (x, y), rng.randrange(2, 4))
            return surface

        return {
            "grass_0": grass_tile(1),
            "grass_1": grass_tile(2),
            "grass_2": grass_tile(3),
            "grass_deep": grass_tile(4, deep=True),
            "dirt": dirt_tile(5),
            "bank": bank_tile(6),
            "water": water_tile(7),
            "bridge": bridge_tile(8),
            "flowers": flower_tile(9),
            "tree_0": tree_tile(10),
            "tree_1": tree_tile(11),
        }

    # загружает спрайт bank
    def load_sprite_bank(self):
        hero_light_idle = self.load_horizontal_sheet(LIGHT_PLAYER_DIR / "Idle.png", frame_count=7, target_box=(186, 236))
        hero_light_walk = self.load_horizontal_sheet(LIGHT_PLAYER_DIR / "Walk.png", frame_count=6, target_box=(186, 236))
        hero_light_run = self.load_horizontal_sheet(LIGHT_PLAYER_DIR / "Run.png", frame_count=8, target_box=(194, 240))
        hero_light_melee_right = self.load_horizontal_sheet(
            LIGHT_PLAYER_DIR / "Flame_jet.png", frame_count=14, target_box=(248, 236), anchor="center"
        )
        hero_light_special_right = self.load_horizontal_sheet(
            LIGHT_PLAYER_DIR / "Fireball.png", frame_count=8, target_box=(250, 238), anchor="center"
        )
        hero_light_charge = []
        hero_light_special_fx = []
        hero_light_projectile = self.load_horizontal_sheet(
            LIGHT_PLAYER_DIR / "Charge.png", frame_count=12, target_box=(116, 116), anchor="center"
        )

        hero_dark_idle = self.load_horizontal_sheet(DARK_PLAYER_DIR / "Idle.png", frame_count=8, target_box=(186, 236))
        hero_dark_walk = self.load_horizontal_sheet(DARK_PLAYER_DIR / "Walk.png", frame_count=7, target_box=(186, 236))
        hero_dark_run = self.load_horizontal_sheet(DARK_PLAYER_DIR / "Run.png", frame_count=8, target_box=(194, 240))
        hero_dark_melee_right = self.load_horizontal_sheet(
            DARK_PLAYER_DIR / "Attack_1.png", frame_count=7, target_box=(252, 238), anchor="center"
        )
        hero_dark_special_right = self.load_horizontal_sheet(
            DARK_PLAYER_DIR / "Attack_2.png", frame_count=9, target_box=(254, 240), anchor="center"
        )
        hero_dark_charge = []
        hero_dark_special_fx = self.load_horizontal_sheet(
            DARK_PLAYER_DIR / "Charge_2.png", frame_count=6, target_box=(210, 210), anchor="center"
        )
        hero_dark_projectile = self.load_horizontal_sheet(
            DARK_PLAYER_DIR / "Charge_1.png", frame_count=9, target_box=(116, 116), anchor="center"
        )

        resident_idle = self.load_horizontal_sheet(NPC_DIR / "Zhitel_Idle.png", frame_count=8, target_box=(168, 210))
        if not resident_idle:
            resident_idle = self.load_horizontal_sheet(RESIDENT_DIR / "Idle.png", frame_count=8, target_box=(168, 210))
        resident_run = self.load_horizontal_sheet(NPC_DIR / "Zhitel_Run.png", frame_count=8, target_box=(168, 210))
        if not resident_run:
            resident_run = self.load_horizontal_sheet(RESIDENT_DIR / "Run.png", frame_count=8, target_box=(168, 210))
        npc1_up = self.load_sheet_column(NPC_DIR / "npc1.png", column_index=0, frame_count=5, target_box=(132, 182))
        npc1_right = self.load_sheet_column(NPC_DIR / "npc1.png", column_index=2, frame_count=5, target_box=(132, 182))
        npc1_down = self.load_sheet_column(NPC_DIR / "npc1.png", column_index=4, frame_count=5, target_box=(132, 182))
        npc2_up = self.load_sheet_column(NPC_DIR / "npc2.png", column_index=0, frame_count=5, target_box=(132, 182))
        npc2_right = self.load_sheet_column(NPC_DIR / "npc2.png", column_index=2, frame_count=5, target_box=(132, 182))
        npc2_down = self.load_sheet_column(NPC_DIR / "npc2.png", column_index=4, frame_count=5, target_box=(132, 182))

        skeleton_walk = self.load_horizontal_sheet(SKELETON_DIR / "Walk.png", frame_count=4, target_box=(248, 304))
        skeleton_attack_1 = self.load_horizontal_sheet(SKELETON_DIR / "Attack1.png", frame_count=8, target_box=(308, 340))
        skeleton_attack_2 = self.load_horizontal_sheet(SKELETON_DIR / "Attack2.png", frame_count=8, target_box=(308, 340))
        skeleton_attack_3 = self.load_horizontal_sheet(SKELETON_DIR / "Attack3.png", frame_count=6, target_box=(308, 340))
        skeleton_death = self.load_horizontal_sheet(SKELETON_DIR / "Death.png", frame_count=4, target_box=(308, 340))

        priest_idle = self.load_sequence_folder(SVET_DIR, "cultist_priest_idle_*.png", (136, 170))
        priest_walk = self.load_sequence_folder(SVET_DIR, "cultist_priest_walk_*.png", (136, 170))
        priest_attack = self.load_sequence_folder(SVET_DIR, "cultist_priest_attack_*.png", (160, 184))
        priest_hurt = self.load_sequence_folder(SVET_DIR, "cultist_priest_takehit_*.png", (136, 170))
        priest_death = self.load_sequence_folder(SVET_DIR, "cultist_priest_die_*.png", (160, 190))
        priest_beam = self.load_horizontal_sheet(SVET_DIR / "luch.png", frame_count=11, target_box=(136, 160), anchor="center")

        tma_idle = self.load_sequence_folder(TMA_DIR / "Idle", "*.png", (308, 368))
        tma_walk = self.load_sequence_folder(TMA_DIR / "Walk", "*.png", (308, 368))
        tma_attack = self.load_sequence_folder(TMA_DIR / "Attack", "*.png", (340, 380))
        tma_cast = self.load_sequence_folder(TMA_DIR / "Cast", "*.png", (340, 380))
        tma_spell = self.load_sequence_folder(TMA_DIR / "Spell", "*.png", (360, 360), anchor="center")
        tma_hurt = self.load_sequence_folder(TMA_DIR / "Hurt", "*.png", (308, 368))
        tma_death = self.load_sequence_folder(TMA_DIR / "Death", "*.png", (340, 396))

        brother_idle = self.load_horizontal_sheet(BROTHER_DIR / "Idle.png", frame_count=6, target_box=(188, 224))
        brother_run = self.load_horizontal_sheet(BROTHER_DIR / "Run.png", frame_count=8, target_box=(188, 224))
        brother_attack_1 = self.load_horizontal_sheet(BROTHER_DIR / "Attack1.png", frame_count=8, target_box=(214, 230))
        brother_attack_2 = self.load_horizontal_sheet(BROTHER_DIR / "Attack2.png", frame_count=8, target_box=(214, 230))
        brother_jump = self.load_horizontal_sheet(BROTHER_DIR / "Jump.png", frame_count=2, target_box=(188, 224))
        brother_fall = self.load_horizontal_sheet(BROTHER_DIR / "Fall.png", frame_count=2, target_box=(188, 224))
        brother_hit = self.load_horizontal_sheet(BROTHER_DIR / "Hit.png", frame_count=3, target_box=(188, 224))
        brother_death = self.load_horizontal_sheet(BROTHER_DIR / "Death.png", frame_count=6, target_box=(188, 224))

        dragon_face = self.load_single_image(DRAGON_DIR / "face.png", (620, 348), anchor="center")
        dragon_angry_face = self.load_single_image(DRAGON_DIR / "angry_face.png", (620, 348), anchor="center")
        dragon_tail = self.load_single_image(DRAGON_DIR / "tail.png", (1280, 620), anchor="center")
        rock_spike = self.load_grid_sheet(DRAGON_DIR / "rock_animation.png", 5, 1, (176, 192))
        alert_sign = self.load_single_image(ALERT_SIGN_PATH, (43, 43), anchor="center")
        pickup_heal = self.load_single_image(HEAL_ITEM_PATH, (46, 46), anchor="center")
        pickup_artefact = self.load_single_image(ARTEFACT_ITEM_PATH, (58, 58), anchor="center")

        neutral_hero = self.load_strip_from_surface(
            build_hero_sheet((58, 58, 72), (232, 223, 210), (132, 132, 150), (108, 110, 126)),
            92,
        )
        elder_surface = build_mentor_sheet((84, 68, 52), (236, 226, 210), (204, 182, 132))
        return {
            "hero_light": hero_light_idle or neutral_hero,
            "hero_light_walk": hero_light_walk or hero_light_idle or neutral_hero,
            "hero_light_run": hero_light_run or hero_light_walk or hero_light_idle or neutral_hero,
            "hero_light_special": hero_light_special_right,
            "hero_light_charge": hero_light_charge,
            "hero_light_special_fx": hero_light_special_fx,
            "hero_light_projectile": hero_light_projectile,
            "hero_dark": hero_dark_idle or neutral_hero,
            "hero_dark_walk": hero_dark_walk or hero_dark_idle or neutral_hero,
            "hero_dark_run": hero_dark_run or hero_dark_walk or hero_dark_idle or neutral_hero,
            "hero_dark_special": hero_dark_special_right,
            "hero_dark_charge": hero_dark_charge,
            "hero_dark_special_fx": hero_dark_special_fx,
            "hero_dark_projectile": hero_dark_projectile,
            "hero_down": hero_light_walk or hero_dark_walk,
            "shero_attack_right": hero_light_melee_right,
            "shero_attack_left": self.flip_frames(hero_light_melee_right),
            "thero_attack_right": hero_dark_melee_right,
            "thero_attack_left": self.flip_frames(hero_dark_melee_right),
            "mentor_light": self.load_strip_with_fallback(
                "mentor_lumen.png", 64, build_mentor_sheet((170, 147, 84), (238, 232, 215), (255, 239, 180))
            ),
            "mentor_dark": self.load_strip_with_fallback(
                "mentor_umbra.png", 64, build_mentor_sheet((68, 56, 112), (220, 210, 235), (177, 135, 255))
            ),
            "elder_map": self.load_strip_from_surface(elder_surface, 128),
            "messenger": resident_idle or self.load_strip_with_fallback("messenger.png", 64, build_messenger_sheet()),
            "resident_idle": resident_idle or self.load_strip_with_fallback("messenger.png", 64, build_messenger_sheet()),
            "resident_run": resident_run or resident_idle or self.load_strip_with_fallback("messenger.png", 64, build_messenger_sheet()),
            "npc1_up": npc1_up,
            "npc1_right": npc1_right,
            "npc1_down": npc1_down,
            "npc1_left": self.flip_frames(npc1_right),
            "npc2_up": npc2_up,
            "npc2_right": npc2_right,
            "npc2_down": npc2_down,
            "npc2_left": self.flip_frames(npc2_right),
            "ghoul": skeleton_walk or self.load_strip_with_fallback("ghoul.png", 64, build_ghoul_sheet()),
            "ghoul_walk": skeleton_walk or self.load_strip_with_fallback("ghoul.png", 64, build_ghoul_sheet()),
            "ghoul_attacks": [frames for frames in (skeleton_attack_1, skeleton_attack_2, skeleton_attack_3) if frames],
            "ghoul_death": skeleton_death,
            "light_priest_idle": priest_idle or skeleton_walk,
            "light_priest_walk": priest_walk or priest_idle or skeleton_walk,
            "light_priest_attack": priest_attack,
            "light_priest_hurt": priest_hurt,
            "light_priest_death": priest_death,
            "light_priest_beam": priest_beam,
            "dark_alchemist_idle": tma_idle or skeleton_walk,
            "dark_alchemist_walk": tma_walk or tma_idle or skeleton_walk,
            "dark_alchemist_attack": tma_attack,
            "dark_alchemist_cast": tma_cast,
            "dark_alchemist_spell": tma_spell,
            "dark_alchemist_hurt": tma_hurt,
            "dark_alchemist_death": tma_death,
            "dragon": [dragon_face] if dragon_face else self.load_strip_with_fallback("wyrm.png", 160, build_dragon_sheet()),
            "dragon_face": dragon_face,
            "dragon_angry_face": dragon_angry_face or dragon_face,
            "dragon_tail": dragon_tail,
            "alert_sign": alert_sign,
            "pickup_heal": pickup_heal,
            "pickup_artefact": pickup_artefact,
            "brother": brother_idle or self.load_strip_with_fallback("heir.png", 96, build_brother_sheet()),
            "brother_idle": brother_idle or self.load_strip_with_fallback("heir.png", 96, build_brother_sheet()),
            "brother_run": brother_run or brother_idle or self.load_strip_with_fallback("heir.png", 96, build_brother_sheet()),
            "brother_attack_1": brother_attack_1,
            "brother_attack_2": brother_attack_2,
            "brother_jump": brother_jump,
            "brother_fall": brother_fall,
            "brother_hit": brother_hit,
            "brother_death": brother_death,
            "rock_spike": rock_spike or self.load_grid_sheet(ROCK_ANIMATION_PATH, 5, 1, (176, 192)),
        }

    # загружает vn portraits
    def load_vn_portraits(self):
        portraits = {}
        portrait_paths = (
            ("hero", HERO_VN_PORTRAIT_PATH),
            ("mentor", MASTER_VN_PORTRAIT_PATH if MASTER_VN_PORTRAIT_PATH.exists() else MENTOR_VN_PORTRAIT_PATH),
            ("master", MASTER_VN_PORTRAIT_PATH if MASTER_VN_PORTRAIT_PATH.exists() else MENTOR_VN_PORTRAIT_PATH),
            ("witch", WITCH_VN_PORTRAIT_PATH),
            ("gonec", GONEC_VN_PORTRAIT_PATH),
        )
        for key, path in portrait_paths:
            if not path.exists():
                portraits[key] = None
                continue
            try:
                portraits[key] = pygame.image.load(path).convert_alpha()
            except pygame.error:
                portraits[key] = None
        return portraits

    # загружает сюжет images
    def load_story_images(self):
        images = {}
        if not CUTSCENE_DIR.exists():
            return images
        target_box = (1680, 620)
        for path in CUTSCENE_DIR.rglob("*.png"):
            try:
                source = pygame.image.load(path).convert()
                images[path.stem] = fit_surface_to_box(source, target_box, anchor="center")
            except pygame.error:
                continue
        return images

    # загружает strip
    def load_strip(self, filename, target_size):
        image = pygame.image.load(SPRITE_DIR / filename).convert_alpha()
        return self.load_strip_from_surface(image, target_size)

    # загружает strip with fallback
    def load_strip_with_fallback(self, filename, target_size, fallback_surface):
        path = SPRITE_DIR / filename
        if path.exists():
            image = pygame.image.load(path).convert_alpha()
            if self.is_valid_strip(image, 5):
                return self.load_strip_from_surface(image, target_size)
        return self.load_strip_from_surface(fallback_surface, target_size)

    # загружает strip from поверхность
    def load_strip_from_surface(self, image, target_size):
        frame_width = image.get_width() // 5
        frames = []
        for index in range(5):
            frame = pygame.Surface((frame_width, image.get_height()), pygame.SRCALPHA)
            frame.blit(image, (0, 0), pygame.Rect(index * frame_width, 0, frame_width, image.get_height()))
            if frame_width != target_size or image.get_height() != target_size:
                frame = pygame.transform.scale(frame, (target_size, target_size))
            frames.append(frame)
        return frames

    # проверяет является ли valid strip
    def is_valid_strip(self, image, columns):
        if image.get_width() % columns != 0:
            return False
        frame_width = image.get_width() // columns
        return image.get_height() <= int(frame_width * 1.5)

    # загружает grid sheet
    def load_grid_sheet(self, path, columns, rows, target_box, anchor="midbottom"):
        if not path.exists():
            return []
        image = pygame.image.load(path).convert_alpha()
        frame_width = image.get_width() // columns
        frame_height = image.get_height() // rows
        frames = []
        for row in range(rows):
            for column in range(columns):
                frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
                source_rect = pygame.Rect(column * frame_width, row * frame_height, frame_width, frame_height)
                frame.blit(image, (0, 0), source_rect)
                frames.append(fit_surface_to_box(frame, target_box, anchor=anchor))
        return frames

    # выполняет flip frames
    def flip_frames(self, frames):
        return [pygame.transform.flip(frame, True, False) for frame in frames]

    # выполняет repeat кадр
    def repeat_frame(self, frame, count):
        return [frame.copy() for _ in range(max(0, count))]

    # выполняет natural sort key
    def natural_sort_key(self, value):
        parts = re.split(r"(\d+)", str(value))
        return [int(part) if part.isdigit() else part.lower() for part in parts]

    # загружает single image
    def load_single_image(self, path, target_box, anchor="midbottom", allow_upscale=True):
        if not path.exists():
            return None
        try:
            image = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None
        return fit_surface_to_box(image, target_box, anchor=anchor, allow_upscale=allow_upscale)

    # загружает horizontal sheet
    def load_horizontal_sheet(self, path, frame_count, target_box, anchor="midbottom", allow_upscale=True):
        if not path.exists():
            return []
        try:
            image = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return []
        if frame_count <= 0 or image.get_width() % frame_count != 0:
            return []
        frame_width = image.get_width() // frame_count
        frames = []
        for index in range(frame_count):
            frame = pygame.Surface((frame_width, image.get_height()), pygame.SRCALPHA)
            frame.blit(image, (0, 0), pygame.Rect(index * frame_width, 0, frame_width, image.get_height()))
            frames.append(fit_surface_to_box(frame, target_box, anchor=anchor, allow_upscale=allow_upscale))
        return frames

    # загружает sequence folder
    def load_sequence_folder(self, folder, pattern, target_box, anchor="midbottom", allow_upscale=True):
        if not folder.exists():
            return []
        frames = []
        for path in sorted(folder.glob(pattern), key=lambda item: self.natural_sort_key(item.name)):
            try:
                image = pygame.image.load(path).convert_alpha()
            except pygame.error:
                continue
            frames.append(fit_surface_to_box(image, target_box, anchor=anchor, allow_upscale=allow_upscale))
        return frames

    # загружает sheet row
    def load_sheet_row(self, path, row_index, frame_count, target_box, anchor="midbottom", allow_upscale=True):
        if not path.exists():
            return []
        try:
            image = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return []
        if frame_count <= 0 or image.get_width() % frame_count != 0:
            return []
        frame_width = image.get_width() // frame_count
        if frame_width <= 0 or image.get_height() % frame_width != 0:
            return []
        rows = image.get_height() // frame_width
        if row_index < 0 or row_index >= rows:
            return []
        frames = []
        top = row_index * frame_width
        for index in range(frame_count):
            frame = pygame.Surface((frame_width, frame_width), pygame.SRCALPHA)
            frame.blit(image, (0, 0), pygame.Rect(index * frame_width, top, frame_width, frame_width))
            frames.append(fit_surface_to_box(frame, target_box, anchor=anchor, allow_upscale=allow_upscale))
        return frames

    # загружает sheet column
    def load_sheet_column(self, path, column_index, frame_count, target_box, anchor="midbottom", allow_upscale=True):
        if not path.exists():
            return []
        try:
            image = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return []
        if frame_count <= 0:
            return []
        frame_width = image.get_width() // 5
        if frame_width <= 0 or image.get_width() % 5 != 0 or image.get_height() % frame_width != 0:
            return []
        rows = image.get_height() // frame_width
        if column_index < 0 or column_index >= 5:
            return []
        frames = []
        left = column_index * frame_width
        limit = min(frame_count, rows)
        for index in range(limit):
            top = index * frame_width
            frame = pygame.Surface((frame_width, frame_width), pygame.SRCALPHA)
            frame.blit(image, (0, 0), pygame.Rect(left, top, frame_width, frame_width))
            frames.append(fit_surface_to_box(frame, target_box, anchor=anchor, allow_upscale=allow_upscale))
        return frames

    # определяет tileset image path
    def resolve_tileset_image_path(self, source, base_dir=None):
        source_path = Path(str(source))
        if base_dir is not None:
            source_path = (Path(base_dir) / source_path).resolve()
        source_name = source_path.name.lower()
        candidate_dirs = []
        if base_dir is not None:
            candidate_dirs.append(Path(base_dir))
        for folder in (MAP_LEVEL1_DIR, MAP_LEVEL2_DIR, MAP_LEVEL3_DIR, MAP_LEVEL4_DIR, MAP_TILELIST_DIR, MAP_DIR):
            if folder not in candidate_dirs:
                candidate_dirs.append(folder)
        if source_path.exists() and source_path.suffix.lower() == ".tsx":
            try:
                root = ET.fromstring(source_path.read_text(encoding="utf-8"))
                image_node = root.find("image")
                if image_node is not None and image_node.get("source"):
                    image_path = (source_path.parent / image_node.get("source")).resolve()
                    if image_path.exists():
                        return image_path
            except (OSError, ET.ParseError):
                pass
        if source_path.exists() and source_path.suffix.lower() == ".png":
            return source_path
        explicit_names = {
            "pescheri+les.tsx": "MainLev2.0.png",
            "river.tsx": "river.png",
            "river2.tsx": "river2.png",
            "river3.tsx": "river3.png",
            "river4.tsx": "river4.png",
            "elka.tsx": "elka.png",
            "elka2.tsx": "elka2.png",
            "house1.tsx": "house1.png",
        }
        if source_name in explicit_names:
            explicit_name = explicit_names[source_name]
            for folder in candidate_dirs:
                candidate = folder / explicit_name
                if candidate.exists():
                    return candidate
        direct_name = Path(source_name).stem + ".png"
        for folder in candidate_dirs:
            candidate = folder / direct_name
            if candidate.exists():
                return candidate
        return candidate_dirs[0] / direct_name

    # загружает карту definition
    def load_map_definition(self, map_json_path, overlay_tokens=None):
        if overlay_tokens is None:
            overlay_tokens = ("tops", "top", "roof", "кры", "верх")
        if not map_json_path.exists():
            return None
        try:
            data = json.loads(map_json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        base_dir = map_json_path.parent
        # хранит исходный размер тайла из json карты
        map_tile_width = int(data.get("tilewidth", TILE_SIZE))
        map_tile_height = int(data.get("tileheight", TILE_SIZE))
        # хранит масштаб до игрового тайла 64x64
        scale_x = TILE_SIZE / max(1, map_tile_width)
        scale_y = TILE_SIZE / max(1, map_tile_height)
        # хранит готовые поверхности тайлов по gid и метаданные tileset
        gid_surfaces = {}
        tileset_meta = []
        for tileset in data.get("tilesets", []):
            source = str(tileset.get("source", ""))
            source_path = (base_dir / source).resolve() if source else None
            image_path = self.resolve_tileset_image_path(source, base_dir=base_dir)
            if not image_path.exists():
                continue
            # хранит геометрию тайлсета для нарезки на отдельные плитки
            tile_width = map_tile_width
            tile_height = map_tile_height
            columns = 0
            total = 0
            spacing = 0
            margin = 0
            if source_path and source_path.exists() and source_path.suffix.lower() == ".tsx":
                try:
                    root = ET.fromstring(source_path.read_text(encoding="utf-8"))
                    tile_width = int(root.get("tilewidth", tile_width))
                    tile_height = int(root.get("tileheight", tile_height))
                    columns = int(root.get("columns", 0))
                    total = int(root.get("tilecount", 0))
                    spacing = int(root.get("spacing", 0))
                    margin = int(root.get("margin", 0))
                except (OSError, ET.ParseError, ValueError):
                    pass
            else:
                tile_width = int(tileset.get("tilewidth", tile_width))
                tile_height = int(tileset.get("tileheight", tile_height))
                columns = int(tileset.get("columns", 0))
                total = int(tileset.get("tilecount", 0))
                spacing = int(tileset.get("spacing", 0))
                margin = int(tileset.get("margin", 0))
            try:
                image = pygame.image.load(image_path).convert_alpha()
            except pygame.error:
                continue
            if columns <= 0:
                columns = max(1, (image.get_width() - margin * 2 + spacing) // max(1, tile_width + spacing))
            rows = max(1, (image.get_height() - margin * 2 + spacing) // max(1, tile_height + spacing))
            if total <= 0:
                total = columns * rows
            firstgid = int(tileset.get("firstgid", 1))
            for local_index in range(total):
                column = local_index % columns
                row = local_index // columns
                src_x = margin + column * (tile_width + spacing)
                src_y = margin + row * (tile_height + spacing)
                source_rect = pygame.Rect(src_x, src_y, tile_width, tile_height)
                if source_rect.right > image.get_width() or source_rect.bottom > image.get_height():
                    continue
                tile = pygame.Surface((tile_width, tile_height), pygame.SRCALPHA)
                tile.blit(image, (0, 0), source_rect)
                if tile_width != TILE_SIZE or tile_height != TILE_SIZE:
                    tile = pygame.transform.scale(tile, (TILE_SIZE, TILE_SIZE))
                gid_surfaces[firstgid + local_index] = tile
            tileset_meta.append(
                {
                    "firstgid": firstgid,
                    "image_path": image_path,
                    "columns": columns,
                    "rows": rows,
                    "source_tile_width": tile_width,
                    "source_tile_height": tile_height,
                }
            )

        # хранит нормализованные tile- и object-слои карты
        tile_layers = []
        base_layers = []
        overlay_layers = []
        object_layers = {}
        for layer in data.get("layers", []):
            if layer.get("type") == "tilelayer":
                if not layer.get("visible", True):
                    continue
                layer_info = TiledTileLayer(
                    name=str(layer.get("name", "")),
                    width=int(layer.get("width", data.get("width", 0))),
                    height=int(layer.get("height", data.get("height", 0))),
                    data=list(layer.get("data", [])),
                    opacity=float(layer.get("opacity", 1.0)),
                )
                tile_layers.append(layer_info)
                layer_name = layer_info.name.strip().lower()
                if any(token in layer_name for token in overlay_tokens):
                    overlay_layers.append(layer_info)
                else:
                    base_layers.append(layer_info)
            elif layer.get("type") == "objectgroup":
                scaled_objects = [TiledMapObject.from_tiled_dict(obj, scale_x, scale_y) for obj in layer.get("objects", [])]
                object_layers[layer.get("name", "")] = scaled_objects

        return LoadedTileMap(
            width=int(data.get("width", 0)),
            height=int(data.get("height", 0)),
            tile_width=TILE_SIZE,
            tile_height=TILE_SIZE,
            layers=tile_layers,
            base_layers=base_layers,
            overlay_layers=overlay_layers,
            gid_surfaces=gid_surfaces,
            object_layers=object_layers,
            tilesets=tileset_meta,
            path=map_json_path,
        )

    # загружает assault карту definition
    def load_assault_map_definition(self):
        return self.load_map_definition(ASSAULT_MAP_JSON_PATH)

    # загружает дракона карту definition
    def load_dragon_map_definition(self):
        return self.load_map_definition(DRAGON_MAP_JSON_PATH)

    # загружает туннель карту definition
    def load_tunnel_map_definition(self):
        return self.load_map_definition(TUNNEL_MAP_JSON_PATH)

    # загружает брата карту definition
    def load_brother_map_definition(self):
        return self.load_map_definition(BROTHER_MAP_JSON_PATH)

    # загружает дракона фон layers
    def load_dragon_background_layers(self):
        if not DRAGON_BACKGROUND_DIR.exists():
            return []
        presets = {
            "01": {"travel_x": 18, "travel_y": 14, "offset_x": 0, "offset_y": -24},
            "02": {"travel_x": 34, "travel_y": 18, "offset_x": 0, "offset_y": 18},
            "03": {"travel_x": 42, "travel_y": 26, "offset_x": 0, "offset_y": -34},
            "04": {"travel_x": 10, "travel_y": 8, "offset_x": 0, "offset_y": 0},
            "05": {"travel_x": 58, "travel_y": 34, "offset_x": 0, "offset_y": -62},
            "06": {"travel_x": 24, "travel_y": 12, "offset_x": 0, "offset_y": 10},
            "07": {"travel_x": 72, "travel_y": 44, "offset_x": 0, "offset_y": 48},
        }
        layers = []
        for path in sorted(DRAGON_BACKGROUND_DIR.glob("*.png")):
            try:
                image = pygame.image.load(path).convert_alpha()
            except pygame.error:
                continue
            spec = presets.get(path.stem, {})
            layers.append(
                {
                    "name": path.stem,
                    "surface": pygame.transform.scale(image, (WINDOW_WIDTH, WINDOW_HEIGHT)),
                    "travel_x": spec.get("travel_x", 0),
                    "travel_y": spec.get("travel_y", 0),
                    "offset_x": spec.get("offset_x", 0),
                    "offset_y": spec.get("offset_y", 0),
                }
            )
        return layers

    # запускает основной цикл
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

    # запускает self test
    def run_self_test(self):
        self.start_new_game()
        self.apply_caste_choice("dark", skip_story=True)
        for _ in range(12):
            self.update(1 / 60)
            self.draw()
        print("SELF_TEST_OK", flush=True)

    # проверяет есть ли compatible сохранение
    def has_compatible_save(self):
        if not SAVE_PATH.exists():
            return False
        try:
            data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        return data.get("version") == SAVE_VERSION

    # показывает сообщение
    def show_toast(self, text):
        self.toast = text
        self.toast_timer = 2.6

    # показывает волну баннер
    def show_wave_banner(self, title, subtitle=""):
        self.wave_banner_title = title
        self.wave_banner_subtitle = subtitle
        self.wave_banner_timer = 2.1

    # очищает combat состояние
    def clear_combat_state(self):
        self.enemies = []
        self.dummies = []
        self.crystals = []
        self.town_npcs = []
        self.town_npc_spawns = []
        self.pickups = []
        self.rock_spikes = []
        self.player_arcs = []
        self.player_projectiles = []
        self.player_beams = []
        self.relic_effects = []
        self.enemy_projectiles = []
        self.enemy_beams = []
        self.enemy_zones = []
        self.enemy_sweeps = []
        self.enemy_rings = []
        self.gravity_orbs = []
        self.floaters = []
        self.dragon = None
        self.brother = None
        self.assault_waves = []
        self.assault_wave_index = 0
        self.assault_wave_delay = 0.0
        self.assault_ready_to_advance = False
        self.dragon_relic_armed = False
        self.dragon_relic_charge = False
        self.dragon_relic_charge_time = 0.0
        self.assault_civilians_spawned = False
        self.tunnel_fire_rects = []
        self.refresh_cover()

    # собирает игрока and master
    def build_player_and_master(self, caste):
        if caste == "light":
            self.player = Player(
                (8 * TILE_SIZE, 9 * TILE_SIZE),
                self.sprite_bank["hero_light"],
                "light",
                walk_frames=self.sprite_bank.get("hero_light_walk"),
                run_frames=self.sprite_bank.get("hero_light_run"),
                attack_frames_right=self.sprite_bank.get("shero_attack_right"),
                attack_frames_left=self.sprite_bank.get("shero_attack_left"),
                special_frames_right=self.sprite_bank.get("hero_light_special"),
                special_frames_left=self.flip_frames(self.sprite_bank.get("hero_light_special", [])),
                charge_frames=self.sprite_bank.get("hero_light_charge"),
                special_effect_frames=self.sprite_bank.get("hero_light_special_fx"),
                projectile_frames=self.sprite_bank.get("hero_light_projectile"),
            )
        else:
            self.player = Player(
                (8 * TILE_SIZE, 9 * TILE_SIZE),
                self.sprite_bank["hero_dark"],
                "dark",
                walk_frames=self.sprite_bank.get("hero_dark_walk"),
                run_frames=self.sprite_bank.get("hero_dark_run"),
                attack_frames_right=self.sprite_bank.get("thero_attack_right"),
                attack_frames_left=self.sprite_bank.get("thero_attack_left"),
                special_frames_right=self.sprite_bank.get("hero_dark_special"),
                special_frames_left=self.flip_frames(self.sprite_bank.get("hero_dark_special", [])),
                charge_frames=self.sprite_bank.get("hero_dark_charge"),
                special_effect_frames=self.sprite_bank.get("hero_dark_special_fx"),
                projectile_frames=self.sprite_bank.get("hero_dark_projectile"),
            )
        self.master = NPC(
            (10 * TILE_SIZE, 9 * TILE_SIZE),
            self.sprite_bank["resident_idle"],
            "Житель",
            run_frames=self.sprite_bank.get("resident_run"),
        )

    # сохраняет checkpoint
    def save_checkpoint(self, chapter):
        if not self.player:
            return
        data = {
            "version": SAVE_VERSION,
            "chapter": chapter,
            "stats": self.player.snapshot(),
        }
        SAVE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # загружает last сохранение
    def load_last_save(self):
        if not self.has_compatible_save():
            self.show_toast("Сохранение отсутствует или относится к старой версии игры.")
            return
        try:
            data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.show_toast("Сохранение повреждено.")
            return
        stats = data.get("stats", {})
        chapter = data.get("chapter", "assault")
        caste = stats.get("caste", "light")
        self.build_player_and_master(caste)
        # хранит совместимость со старыми сохранениями tutorial
        loaders = {
            "tutorial": self.setup_assault_room,
            "assault": self.setup_assault_room,
            "dragon": self.setup_dragon_room,
            "tunnel": self.setup_tunnel,
            "brother": self.setup_brother_room,
        }
        loader = loaders.get(chapter)
        if loader is None:
            self.show_toast("Сохранение несовместимо с новой сборкой.")
            return
        loader(skip_save=True)
        self.player.load_stats(stats)
        self.player_hp_display = float(self.player.hp)
        self.player_mana_display = float(self.player.mana)
        self.show_toast("Сохранение загружено.")

    # обрабатывает events
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.scene == "menu":
                    self.handle_menu_input(event)
                elif self.scene == "settings":
                    self.handle_settings_input(event)
                elif self.scene == "story":
                    if self.story_choice_mode and self.current_story_page() and self.current_story_page().get("choices"):
                        if event.key in (pygame.K_LEFT, pygame.K_a):
                            self.story_choice_index = max(0, self.story_choice_index - 1)
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            self.story_choice_index = min(len(self.current_story_page()["choices"]) - 1, self.story_choice_index + 1)
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            self.choose_story_option(self.story_choice_index)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.advance_story()
                    elif event.key == pygame.K_ESCAPE and not self.story_is_ending:
                        self.scene = "menu"
                elif self.scene == "dialogue":
                    entry = self.current_dialogue_entry()
                    if entry and entry.get("choices"):
                        if event.key in (pygame.K_LEFT, pygame.K_a):
                            self.dialogue_choice_index = max(0, self.dialogue_choice_index - 1)
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            self.dialogue_choice_index = min(len(entry["choices"]) - 1, self.dialogue_choice_index + 1)
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            self.choose_dialogue_option(self.dialogue_choice_index)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.advance_dialogue()
                elif self.scene == "resident_intro":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.finish_resident_intro()
                elif self.scene == "caste_choice":
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        self.choice_focus = 0
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.choice_focus = 1
                    elif event.key == pygame.K_1:
                        self.apply_caste_choice("light")
                    elif event.key == pygame.K_2:
                        self.apply_caste_choice("dark")
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.apply_caste_choice("light" if self.choice_focus == 0 else "dark")
                elif self.scene == "gameplay":
                    if event.key == pygame.K_e:
                        self.stats_overlay = not self.stats_overlay
                    elif event.key == pygame.K_ESCAPE:
                        if self.stats_overlay:
                            self.stats_overlay = False
                        else:
                            self.scene = "menu"
                    elif self.stats_overlay:
                        continue
                    elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                        move = self.player.movement_vector(pygame.key.get_pressed())
                        if self.player.attempt_dash(move):
                            self.audio.play("Dash", 0.44)
                            if self.chapter == "assault" and self.assault_started:
                                self.assault_tutorial_dodge = True
                    elif event.key == pygame.K_RETURN and self.chapter == "assault" and self.assault_ready_to_advance:
                        if self.player.pos.y < 128:
                            self.setup_dragon_room()
                elif self.scene == "upgrade":
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        self.upgrade_focus = max(0, self.upgrade_focus - 1)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.upgrade_focus = min(2, self.upgrade_focus + 1)
                    elif event.key in (pygame.K_1, pygame.K_KP1):
                        self.apply_upgrade("health")
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        self.apply_upgrade("mana")
                    elif event.key in (pygame.K_3, pygame.K_KP3):
                        self.apply_upgrade("power")
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.apply_upgrade(("health", "mana", "power")[self.upgrade_focus])
                elif self.scene == "tunnel":
                    if event.key == pygame.K_ESCAPE:
                        self.scene = "menu"
                elif self.scene == "ending_choice":
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        self.ending_focus = 0
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.ending_focus = 1
                    elif event.key == pygame.K_1:
                        self.finish_game("kill")
                    elif event.key == pygame.K_2:
                        self.finish_game("spare")
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.finish_game("kill" if self.ending_focus == 0 else "spare")
                elif self.scene == "death":
                    if event.key == pygame.K_RETURN:
                        self.load_last_save()
                    elif event.key == pygame.K_ESCAPE:
                        self.scene = "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN:
                logical_pos = self.window_to_logical(event.pos)
                if self.scene == "menu" and event.button == 1:
                    self.handle_menu_click(logical_pos)
                elif self.scene == "settings" and event.button == 1:
                    self.handle_settings_click(logical_pos)
                elif self.scene == "story" and event.button == 1:
                    if self.story_choice_mode:
                        for index, rect in enumerate(self.story_choice_rects()):
                            if rect.collidepoint(logical_pos):
                                self.story_choice_index = index
                                self.choose_story_option(index)
                                break
                    else:
                        self.advance_story()
                elif self.scene == "gameplay" and self.stats_overlay and event.button == 1:
                    action = self.stats_overlay_action_at(logical_pos)
                    if action == "settings":
                        self.open_settings(return_scene="gameplay", return_stats_overlay=True)
                    elif action == "menu":
                        self.stats_overlay = False
                        self.scene = "menu"
                elif self.scene == "gameplay" and not self.stats_overlay:
                    self.player.update_aim(logical_pos, self.camera)
                    if event.button == 1:
                        attack = self.player.attempt_melee()
                        if attack:
                            self.player_arcs.append(attack)
                            self.audio.play("Udar_blizh", 0.52, cooldown=0.04)
                            if self.chapter == "assault" and self.assault_started:
                                self.assault_tutorial_melee = True
                    elif event.button == 3:
                        if self.chapter == "dragon" and self.dragon_relic_armed:
                            self.fire_dragon_relic(logical_pos)
                        else:
                            special = self.player.attempt_special()
                            if isinstance(special, BeamAttack):
                                special.end = clip_line_by_blockers(special.start, special.end, self.cover)
                                self.player_beams.append(special)
                                self.audio.play("Atak_sun" if self.player.caste == "light" else "Atak_tma", 0.52)
                                if self.chapter == "assault" and self.assault_started:
                                    self.assault_tutorial_special = True
                            elif isinstance(special, Projectile):
                                self.player_projectiles.append(special)
                                self.audio.play("Atak_sun" if self.player.caste == "light" else "Atak_tma", 0.52)
                                if self.chapter == "assault" and self.assault_started:
                                    self.assault_tutorial_special = True
                elif self.scene == "caste_choice" and event.button == 1:
                    choice = self.card_under_mouse(logical_pos, 2, 300, 460, 410)
                    if choice == 0:
                        self.apply_caste_choice("light")
                    elif choice == 1:
                        self.apply_caste_choice("dark")
                elif self.scene == "dialogue" and event.button == 1:
                    entry = self.current_dialogue_entry()
                    if entry and entry.get("choices"):
                        count = len(entry["choices"])
                        total_width = count * 420 + max(0, count - 1) * 24
                        start_x = WINDOW_WIDTH // 2 - total_width // 2
                        for index in range(count):
                            rect = pygame.Rect(start_x + index * 444, WINDOW_HEIGHT - 150, 420, 62)
                            if rect.collidepoint(logical_pos):
                                self.choose_dialogue_option(index)
                                break
                    else:
                        self.advance_dialogue()
                elif self.scene == "resident_intro" and event.button == 1:
                    self.finish_resident_intro()
                elif self.scene == "upgrade" and event.button == 1:
                    choice = self.card_under_mouse(logical_pos, 3, 360, 360, 250)
                    if choice is not None:
                        self.apply_upgrade(("health", "mana", "power")[choice])
                elif self.scene == "ending_choice" and event.button == 1:
                    choice = self.card_under_mouse(logical_pos, 2, 360, 360, 270)
                    if choice == 0:
                        self.finish_game("kill")
                    elif choice == 1:
                        self.finish_game("spare")
            elif event.type == pygame.MOUSEBUTTONUP:
                logical_pos = self.window_to_logical(event.pos)
                if self.scene == "settings" and event.button == 1:
                    self.dragging_volume_key = None
            elif event.type == pygame.MOUSEMOTION:
                if self.scene == "story" and self.story_choice_mode:
                    self.story_hover_choice = None
                    for index, rect in enumerate(self.story_choice_rects()):
                        if rect.collidepoint(self.window_to_logical(event.pos)):
                            self.story_hover_choice = index
                            self.story_choice_index = index
                            break
                if self.scene == "settings" and pygame.mouse.get_pressed()[0]:
                    self.handle_settings_drag(self.window_to_logical(event.pos))

    # обрабатывает меню ввод
    def handle_menu_input(self, event):
        if event.key in (pygame.K_UP, pygame.K_w):
            self.menu_index = (self.menu_index - 1) % len(self.menu_items)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.menu_index = (self.menu_index + 1) % len(self.menu_items)
        elif event.key == pygame.K_1:
            self.start_new_game()
        elif event.key == pygame.K_2:
            self.load_last_save()
        elif event.key == pygame.K_3:
            self.open_settings()
        elif event.key in (pygame.K_4, pygame.K_ESCAPE):
            self.running = False
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.menu_index == 0:
                self.start_new_game()
            elif self.menu_index == 1:
                self.load_last_save()
            elif self.menu_index == 2:
                self.open_settings()
            else:
                self.running = False

    # обрабатывает меню click
    def handle_menu_click(self, pos):
        x = 112
        y = 360
        for index in range(len(self.menu_items)):
            rect = pygame.Rect(x, y + index * 82, 676, 64)
            if rect.collidepoint(pos):
                self.menu_index = index
                if index == 0:
                    self.start_new_game()
                elif index == 1:
                    self.load_last_save()
                elif index == 2:
                    self.open_settings()
                else:
                    self.running = False
                break

    # выполняет change pending volume
    def change_pending_volume(self, key, delta):
        self.pending_config[key] = clamp(self.pending_config[key] + delta, 0.0, 1.0)
        if key == "music_volume":
            self.audio.set_music_volume(self.pending_config[key])
        else:
            self.audio.set_sfx_volume(self.pending_config[key])
            self.preview_sfx_volume()

    # предпросматривает sfx volume
    def preview_sfx_volume(self):
        self.audio.play("Udar_blizh", 0.52, cooldown=0.08)

    # выполняет текущий музыку track
    def current_music_track(self):
        if self.scene in {"menu", "settings"}:
            return "Menu"
        if self.scene in {"story", "dialogue", "resident_intro", "upgrade", "ending_choice"}:
            return "Prolog"
        if self.scene == "gameplay":
            if self.chapter == "assault":
                in_wave_fight = self.assault_started and (bool(self.enemies) or self.assault_wave_delay > 0)
                return "Mob_fight" if in_wave_fight else "Prolog"
            if self.chapter == "dragon":
                return "Dragon"
            if self.chapter == "brother":
                return "Boss_fight"
            if self.chapter == "tunnel":
                return None
            return "Prolog"
        if self.scene == "tunnel":
            return None
        return None

    # обновляет environment audio
    def update_environment_audio(self):
        self.audio.play_music(self.current_music_track())
        tunnel_active = (self.scene == "gameplay" and self.chapter == "tunnel") or self.scene == "tunnel"
        if tunnel_active:
            self.audio.ensure_loop("Fire", "ambient_fire", volume=0.34)
        else:
            self.audio.stop_loop("ambient_fire")

    # выполняет текущий step effect
    def current_step_effect(self):
        if self.chapter == "assault":
            return "Step_trava"
        if self.chapter == "dragon":
            return "Step_dragon"
        if self.chapter == "brother":
            return "Step_peshera"
        return None

    # обновляет игрока footsteps
    def update_player_footsteps(self, dt, move):
        effect_name = self.current_step_effect()
        moving = bool(
            effect_name
            and self.scene == "gameplay"
            and not self.stats_overlay
            and self.player
            and self.player.dash_time <= 0
            and move.length_squared() > 0
        )
        if not moving:
            self.player_step_timer = 0.0
            return
        self.player_step_timer -= dt
        if self.player_step_timer <= 0:
            self.audio.play(effect_name, 0.28, cooldown=0.04)
            speed_ratio = clamp(self.player.current_move_speed() / max(1.0, self.player.speed), 0.65, 1.5)
            self.player_step_timer = 0.34 / speed_ratio

    # выбирает window preset
    def select_window_preset(self, index):
        self.settings_window_index = clamp(index, 0, len(WINDOW_PRESETS) - 1)
        width, height = WINDOW_PRESETS[self.settings_window_index]
        self.pending_config["window_width"] = width
        self.pending_config["window_height"] = height
        self.pending_config["fullscreen"] = False
        self.settings_resolution_dropdown_open = False

    # переключает pending fullscreen
    def toggle_pending_fullscreen(self):
        self.pending_config["fullscreen"] = not bool(self.pending_config.get("fullscreen", False))

    # выполняет настройки resolution список rect
    def settings_resolution_dropdown_rect(self):
        return pygame.Rect(670, 218, 970, 56)

    # выполняет настройки resolution option rect
    def settings_resolution_option_rect(self, index):
        dropdown = self.settings_resolution_dropdown_rect()
        return pygame.Rect(dropdown.x, dropdown.bottom + 10 + index * 52, dropdown.width, 48)

    # выполняет настройки resolution option count
    def settings_resolution_option_count(self):
        return len(WINDOW_PRESETS) + 1

    # выполняет настройки resolution option label
    def settings_resolution_option_label(self, index):
        if index < len(WINDOW_PRESETS):
            width, height = WINDOW_PRESETS[index]
            return f"{width} x {height} | окно"
        return "Во весь экран"

    # выполняет настройки resolution selected option index
    def settings_resolution_selected_option_index(self):
        if self.pending_config.get("fullscreen", False):
            return len(WINDOW_PRESETS)
        return self.settings_window_index

    # выбирает resolution option
    def select_resolution_option(self, index):
        if index < len(WINDOW_PRESETS):
            self.select_window_preset(index)
        else:
            self.pending_config["fullscreen"] = True
            self.settings_resolution_dropdown_open = False

    # выполняет сюжет выбор rects
    def story_choice_rects(self):
        page = self.current_story_page()
        if not page or not page.get("choices"):
            return []
        count = len(page["choices"])
        width = 460
        gap = 34
        total_width = count * width + max(0, count - 1) * gap
        start_x = WINDOW_WIDTH // 2 - total_width // 2
        y = WINDOW_HEIGHT - 154
        return [pygame.Rect(start_x + index * (width + gap), y, width, 72) for index in range(count)]

    # обрабатывает настройки ввод
    def handle_settings_input(self, event):
        if event.key in (pygame.K_ESCAPE,):
            if not self.first_launch_setup:
                self.close_settings(restore_audio=True)
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self.select_window_preset(self.settings_window_index - 1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.select_window_preset(self.settings_window_index + 1)
        elif event.key == pygame.K_f:
            self.toggle_pending_fullscreen()
        elif event.key == pygame.K_q:
            self.change_pending_volume("music_volume", -0.05)
        elif event.key == pygame.K_e:
            self.change_pending_volume("music_volume", 0.05)
        elif event.key == pygame.K_z:
            self.change_pending_volume("sfx_volume", -0.05)
        elif event.key == pygame.K_c:
            self.change_pending_volume("sfx_volume", 0.05)
        elif event.key == pygame.K_RETURN:
            self.apply_pending_settings()
            self.show_toast("Настройки применены.")
        elif event.key == pygame.K_s:
            self.save_config_data()
            self.show_toast("Настройки сохранены.")
            self.close_settings(restore_audio=False)

    # обрабатывает настройки click
    def handle_settings_click(self, pos):
        dropdown_rect = self.settings_resolution_dropdown_rect()
        if dropdown_rect.collidepoint(pos):
            self.settings_resolution_dropdown_open = not self.settings_resolution_dropdown_open
            return

        if self.settings_resolution_dropdown_open:
            for index in range(self.settings_resolution_option_count()):
                if self.settings_resolution_option_rect(index).collidepoint(pos):
                    self.select_resolution_option(index)
                    return
            self.settings_resolution_dropdown_open = False

        music_minus = pygame.Rect(460, 340, 42, 42)
        music_plus = pygame.Rect(1418, 340, 42, 42)
        sfx_minus = pygame.Rect(460, 418, 42, 42)
        sfx_plus = pygame.Rect(1418, 418, 42, 42)
        if music_minus.collidepoint(pos):
            self.change_pending_volume("music_volume", -0.05)
            return
        if music_plus.collidepoint(pos):
            self.change_pending_volume("music_volume", 0.05)
            return
        if sfx_minus.collidepoint(pos):
            self.change_pending_volume("sfx_volume", -0.05)
            return
        if sfx_plus.collidepoint(pos):
            self.change_pending_volume("sfx_volume", 0.05)
            return

        bar_defs = [
            ("music_volume", pygame.Rect(520, 346, 880, 28)),
            ("sfx_volume", pygame.Rect(520, 424, 880, 28)),
        ]
        for key, rect in bar_defs:
            if rect.collidepoint(pos):
                ratio = clamp((pos[0] - rect.x) / rect.width, 0.0, 1.0)
                self.pending_config[key] = ratio
                if key == "music_volume":
                    self.audio.set_music_volume(ratio)
                else:
                    self.audio.set_sfx_volume(ratio)
                    self.preview_sfx_volume()
                return

        buttons = {
            "apply": pygame.Rect(WINDOW_WIDTH // 2 - 236, WINDOW_HEIGHT - 144, 220, 62),
            "save": pygame.Rect(WINDOW_WIDTH // 2 + 16, WINDOW_HEIGHT - 144, 220, 62),
        }
        if buttons["apply"].collidepoint(pos):
            self.apply_pending_settings()
            self.show_toast("Настройки применены.")
        elif buttons["save"].collidepoint(pos):
            self.save_config_data()
            self.show_toast("Настройки сохранены.")
            self.close_settings(restore_audio=False)

    # обрабатывает настройки drag
    def handle_settings_drag(self, pos):
        for key, rect in (
            ("music_volume", pygame.Rect(520, 346, 880, 28)),
            ("sfx_volume", pygame.Rect(520, 424, 880, 28)),
        ):
            expanded = rect.inflate(0, 24)
            if expanded.collidepoint(pos):
                ratio = clamp((pos[0] - rect.x) / rect.width, 0.0, 1.0)
                self.pending_config[key] = ratio
                if key == "music_volume":
                    self.audio.set_music_volume(ratio)
                else:
                    self.audio.set_sfx_volume(ratio)
                    self.preview_sfx_volume()
                return

    # выполняет card under mouse
    def card_under_mouse(self, pos, count, y, width, height):
        gap = 24
        total_width = count * width + (count - 1) * gap
        start_x = WINDOW_WIDTH // 2 - total_width // 2
        for index in range(count):
            rect = pygame.Rect(start_x + index * (width + gap), y, width, height)
            if rect.collidepoint(pos):
                return index
        return None

    # обновляет состояние
    def update(self, dt):
        self.toast_timer = max(0.0, self.toast_timer - dt)
        self.wave_banner_timer = max(0.0, self.wave_banner_timer - dt)
        self.update_environment_audio()
        if self.scene == "menu":
            pass
        elif self.scene == "settings":
            pass
        elif self.scene == "story":
            self.update_story(dt)
        elif self.scene == "dialogue":
            self.dialogue_entry_timer += dt
        elif self.scene == "resident_intro":
            self.update_resident_intro(dt)
        elif self.scene == "gameplay":
            self.update_gameplay(dt)
        elif self.scene == "tunnel":
            self.update_tunnel(dt)
        elif self.scene == "death":
            self.defeat_flash = min(1.0, self.defeat_flash + dt * 0.5)
        if self.player:
            self.player_hp_display = lerp(self.player_hp_display, self.player.hp, clamp(dt * 8, 0.0, 1.0))
            self.player_mana_display = lerp(self.player_mana_display, self.player.mana, clamp(dt * 8, 0.0, 1.0))

    # обновляет gameplay
    def update_gameplay(self, dt):
        if self.player.hp <= 0:
            self.scene = "death"
            self.defeat_flash = 0.0
            return
        if self.stats_overlay:
            return

        keys = pygame.key.get_pressed()
        move = self.player.movement_vector(keys)
        if self.chapter == "assault" and self.assault_started and move.length_squared() > 0:
            self.assault_tutorial_move = True
        self.player.tick(dt, moving=move.length_squared() > 0, move_vector=move)
        velocity = self.player.dash_velocity() if self.player.dash_time > 0 else move * self.player.current_move_speed()
        self.move_actor(self.player, velocity * dt)
        self.update_player_footsteps(dt, move)
        self.camera.update(self.player.pos, self.world_size.x, self.world_size.y)
        self.player.update_aim(self.current_mouse_pos(), self.camera)
        self.dragon_relic_charge = False
        self.dragon_relic_charge_time = 0.0

        if self.master and self.chapter == "assault":
            self.master.tick(dt, moving=False)
        for dummy in self.dummies:
            dummy.tick(dt, moving=False)
        for crystal in self.crystals:
            crystal.tick(dt, moving=True)

        for floater in self.floaters:
            floater.update(dt)
        self.floaters = [floater for floater in self.floaters if floater.alive]

        for attack in self.player_arcs:
            attack.update(dt)
        self.player_arcs = [attack for attack in self.player_arcs if attack.alive]

        for projectile in self.player_projectiles:
            projectile.update(dt, self.cover)
        self.player_projectiles = [projectile for projectile in self.player_projectiles if projectile.alive]

        for beam in self.player_beams:
            beam.update(dt)
        self.player_beams = [beam for beam in self.player_beams if beam.alive]

        for effect in self.relic_effects:
            effect.update(dt)
        self.relic_effects = [effect for effect in self.relic_effects if effect.alive]

        for projectile in self.enemy_projectiles:
            projectile.update(dt, self.cover)
        self.enemy_projectiles = [projectile for projectile in self.enemy_projectiles if projectile.alive]

        for beam in self.enemy_beams:
            beam.update(dt)
        self.enemy_beams = [beam for beam in self.enemy_beams if beam.alive]

        for zone in self.enemy_zones:
            zone.update(dt)
        self.enemy_zones = [zone for zone in self.enemy_zones if zone.alive]

        for sweep in self.enemy_sweeps:
            if getattr(sweep, "lock_to_screen", False):
                sweep.center.update(
                    self.camera.x + WINDOW_WIDTH / 2 - self.camera.pad_x,
                    self.camera.y + getattr(sweep, "screen_anchor_y", 144) - self.camera.pad_y,
                )
            sweep.update(dt, self.cover)
        self.enemy_sweeps = [sweep for sweep in self.enemy_sweeps if sweep.alive]

        for ring in self.enemy_rings:
            ring.update(dt)
        self.enemy_rings = [ring for ring in self.enemy_rings if ring.alive]

        for orb in self.gravity_orbs:
            damage = orb.update(dt, self.player)
            if damage:
                self.damage_player(damage)
        self.gravity_orbs = [orb for orb in self.gravity_orbs if orb.alive]

        self.resolve_player_attacks()
        self.resolve_enemy_attacks()
        self.update_pickups(dt)
        self.update_rock_spikes(dt)
        self.refresh_cover()

        if self.chapter == "assault":
            self.update_ghouls(dt)
            self.update_assault_room(dt)
        elif self.chapter == "dragon":
            self.update_dragon(dt)
        elif self.chapter == "tunnel":
            self.update_tunnel_room(dt)
        elif self.chapter == "brother":
            self.update_brother(dt)
        self.refresh_cover()


# запускает игру
def main(argv=None):
    argv = argv or sys.argv[1:]
    game = BloodRiftGame()
    if "--self-test" in argv:
        game.run_self_test()
        return
    game.run()


if __name__ == "__main__":
    main()
