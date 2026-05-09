import json
import os
import math
import random
import sys
import heapq
import ctypes
from dataclasses import dataclass, field
from pathlib import Path

import pygame


WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
FPS = 60
TILE_SIZE = 64

ROOT_DIR = Path(__file__).resolve().parent
# находит asset dir
def discover_asset_dir():
    local_assets = ROOT_DIR / "assets"
    required_new_dirs = ("player", "enemies", "map", "npc")
    if local_assets.exists() and all((local_assets / name).exists() for name in required_new_dirs):
        return local_assets
    external_assets = Path(r"D:\VS projects\blood_rift\assets")
    if external_assets.exists() and all((external_assets / name).exists() for name in required_new_dirs):
        return external_assets
    return local_assets


ASSET_DIR = discover_asset_dir()
# хранит корневые папки ассетов по типам
SPRITE_DIR = ASSET_DIR / "characters"
UI_DIR = ASSET_DIR / "ui"
AUDIO_DIR = ASSET_DIR / "audio"
MUSIC_DIR = ASSET_DIR / "music"
SOUND_DIR = ASSET_DIR / "sounds"
PORTRAIT_DIR = ASSET_DIR / "portraits"
ANIMATION_DIR = ASSET_DIR / "animations"
CUTSCENE_DIR = ASSET_DIR / "cutscenes"
PROLOGUE_CUTSCENE_DIR = CUTSCENE_DIR / "prologue"
PLAYER_DIR = ASSET_DIR / "player"
LIGHT_PLAYER_DIR = PLAYER_DIR / "light"
DARK_PLAYER_DIR = PLAYER_DIR / "dark"
ENEMY_DIR = ASSET_DIR / "enemies"
BOSS_DIR = ENEMY_DIR / "bosses"
DRAGON_DIR = BOSS_DIR / "dragon"
BROTHER_DIR = BOSS_DIR / "brother"
MOB_DIR = ENEMY_DIR / "mobi"
SKELETON_DIR = MOB_DIR / "skeleton"
SVET_DIR = MOB_DIR / "svet"
TMA_DIR = MOB_DIR / "tma"
NPC_DIR = ASSET_DIR / "npc"
RESIDENT_DIR = NPC_DIR / "zhitel"
MAP_DIR = ASSET_DIR / "map"
MAP_LEVEL1_DIR = MAP_DIR / "1loc"
MAP_LEVEL2_DIR = MAP_DIR / "2loc"
MAP_LEVEL3_DIR = MAP_DIR / "3loc"
MAP_LEVEL4_DIR = MAP_DIR / "4loc"
MAP_TILELIST_DIR = MAP_DIR / "tilelists"
ITEM_DIR = ASSET_DIR / "items"
MENU_ART_PATH = UI_DIR / "menu_art.png"
HERO_SWALKING_SHEET_PATH = SPRITE_DIR / "hero_swalking.png"
SHERO_ATTACK_SHEET_PATH = SPRITE_DIR / "shero_attack.png"
THERO_ATTACK_SHEET_PATH = SPRITE_DIR / "thero_attack.png"
HERO_VN_PORTRAIT_PATH = PORTRAIT_DIR / "hero_vn.png"
MENTOR_VN_PORTRAIT_PATH = PORTRAIT_DIR / "mentor_vn.png"
MASTER_VN_PORTRAIT_PATH = PORTRAIT_DIR / "master.png"
WITCH_VN_PORTRAIT_PATH = PORTRAIT_DIR / "witch.png"
GONEC_VN_PORTRAIT_PATH = PORTRAIT_DIR / "gonec.png"
ROCK_ANIMATION_PATH = ANIMATION_DIR / "rock_animation.png"
ALERT_SIGN_PATH = ITEM_DIR / "znak.png"
HEAL_ITEM_PATH = ITEM_DIR / "heal.png"
ARTEFACT_ITEM_PATH = ITEM_DIR / "artefact.png"


# выполняет first existing path
def first_existing_path(*paths):
    for path in paths:
        if path.exists():
            return path
    return paths[0]


# хранит основные файлы карт и сохранений
ASSAULT_MAP_JSON_PATH = first_existing_path(
    MAP_LEVEL1_DIR / "1level.json",
    MAP_TILELIST_DIR / "1level.json",
    MAP_DIR / "1level.json",
)
DRAGON_MAP_JSON_PATH = first_existing_path(
    MAP_LEVEL2_DIR / "dragon_arena.json",
    MAP_LEVEL2_DIR / "dragon_arena.tmj",
)
DRAGON_BACKGROUND_DIR = MAP_LEVEL2_DIR / "background (dragon)"
TUNNEL_MAP_JSON_PATH = first_existing_path(
    MAP_LEVEL3_DIR / "maze.json",
)
BROTHER_MAP_JSON_PATH = first_existing_path(
    MAP_LEVEL4_DIR / "brat.json",
)
SAVE_PATH = ROOT_DIR / "blood_rift_save.json"
CONFIG_PATH = ROOT_DIR / "blood_rift_config.json"
SAVE_VERSION = 2
CONFIG_VERSION = 1
DEFAULT_WINDOW_SIZE = (1280, 720)
WINDOW_PRESETS = [(1280, 720), (1600, 900), (1920, 1080)]

BACKGROUND = (12, 10, 15)
TEXT = (237, 230, 220)
SUBTLE = (177, 167, 161)
GREEN = (84, 190, 112)
BLUE = (90, 133, 225)
GOLD = (228, 210, 140)
VIOLET = (149, 118, 234)
RED = (196, 74, 82)
PANEL = (14, 14, 18)


# ограничивает
def clamp(value, low, high):
    return max(low, min(high, value))


# выполняет lerp
def lerp(a, b, t):
    return a + (b - a) * t


# выполняет smoothstep
def smoothstep(edge0, edge1, value):
    if edge0 == edge1:
        return 1.0
    x = clamp((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


# выполняет distance to segment
def distance_to_segment(point, start, end):
    segment = end - start
    if segment.length_squared() == 0:
        return point.distance_to(start)
    t = clamp((point - start).dot(segment) / segment.length_squared(), 0.0, 1.0)
    projection = start + segment * t
    return point.distance_to(projection)


# выполняет clip line by blockers
def clip_line_by_blockers(start, end, blockers):
    clipped_end = pygame.Vector2(end)
    best_distance = start.distance_to(clipped_end)
    for rect in blockers:
        clip = rect.clipline((int(start.x), int(start.y)), (int(end.x), int(end.y)))
        if clip:
            hit = pygame.Vector2(clip[0])
            distance = start.distance_to(hit)
            if 1.0 < distance < best_distance:
                best_distance = distance
                clipped_end = hit
    return clipped_end


# выполняет line blocked
def line_blocked(start, end, blockers):
    return clip_line_by_blockers(start, end, blockers).distance_to(end) > 1.0


# выполняет circle rect коллизию
def circle_rect_collision(pos, radius, rect):
    closest_x = clamp(pos.x, rect.left, rect.right)
    closest_y = clamp(pos.y, rect.top, rect.bottom)
    dx = pos.x - closest_x
    dy = pos.y - closest_y
    return dx * dx + dy * dy <= radius * radius


# разбивает текст
def wrap_text(font, text, width):
    words = text.split()
    lines = []
    current = []
    for word in words:
        candidate = " ".join(current + [word])
        if not current or font.size(candidate)[0] <= width:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


# находит font
def find_font(candidates):
    return pygame.font.match_font(",".join(candidates))


# отрисовывает centered текст
def draw_centered_text(surface, font, text, color, center, shadow=True):
    image = font.render(text, True, color)
    rect = image.get_rect(center=center)
    if shadow:
        shadow_image = font.render(text, True, (0, 0, 0))
        surface.blit(shadow_image, rect.move(2, 3))
    surface.blit(image, rect)
    return rect


# отрисовывает текст
def draw_text(surface, font, text, color, pos, shadow=True):
    image = font.render(text, True, color)
    rect = image.get_rect(topleft=pos)
    if shadow:
        shadow_image = font.render(text, True, (0, 0, 0))
        surface.blit(shadow_image, rect.move(2, 3))
    surface.blit(image, rect)
    return rect


# отрисовывает pixel panel
def draw_pixel_panel(surface, rect, fill=(18, 18, 20), border=(196, 184, 154), padding=4):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, border, rect)
    inner = rect.inflate(-padding * 2, -padding * 2)
    if inner.width > 0 and inner.height > 0:
        pygame.draw.rect(surface, fill, inner)
    return inner


# отрисовывает pixel button
def draw_pixel_button(surface, rect, selected=False, disabled=False):
    rect = pygame.Rect(rect)
    border = (230, 230, 234) if selected else (182, 170, 146)
    fill = (10, 10, 12)
    if disabled:
        border = (92, 92, 98)
        fill = (22, 22, 24)
    draw_pixel_panel(surface, rect, fill=fill, border=border, padding=3)
    if selected and not disabled:
        glow = rect.inflate(8, 8)
        pygame.draw.rect(surface, (255, 255, 255), glow, 1)


# отрисовывает pixel bar
def draw_pixel_bar(surface, rect, ratio, fill_color, border=(186, 176, 150), track=(78, 78, 86)):
    rect = pygame.Rect(rect)
    draw_pixel_panel(surface, rect, fill=(0, 0, 0), border=border, padding=3)
    track_rect = rect.inflate(-8, -8)
    pygame.draw.rect(surface, track, track_rect)
    fill_rect = track_rect.copy()
    fill_rect.width = int(track_rect.width * clamp(ratio, 0.0, 1.0))
    if fill_rect.width > 0:
        pygame.draw.rect(surface, fill_color, fill_rect)
    pygame.draw.rect(surface, (0, 0, 0), track_rect, 1)
    return track_rect


# выполняет fit поверхность to box
def fit_surface_to_box(surface, box_size, anchor="midbottom", allow_upscale=True):
    box_w, box_h = box_size
    width, height = surface.get_size()
    canvas = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    if width <= 0 or height <= 0:
        return canvas
    scale = min(box_w / width, box_h / height)
    if not allow_upscale:
        scale = min(1.0, scale)
    scaled_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    if scaled_size != (width, height):
        surface = pygame.transform.scale(surface, scaled_size)
    if anchor == "center":
        rect = surface.get_rect(center=(box_w // 2, box_h // 2))
    else:
        rect = surface.get_rect(midbottom=(box_w // 2, box_h - 2))
    canvas.blit(surface, rect)
    return canvas


# описывает класс animation
class Animation:
    # инициализирует объект
    def __init__(self, frames, fps=8):
        self.frames = frames or []
        self.fps = fps
        self.index = 0
        self.timer = 0.0

    # обновляет состояние
    def update(self, dt, moving=True):
        if not self.frames:
            return
        if not moving:
            self.index = 0
            self.timer = 0.0
            return
        self.timer += dt * self.fps
        while self.timer >= 1.0:
            self.timer -= 1.0
            self.index = (self.index + 1) % len(self.frames)

    # выполняет image
    def image(self):
        return self.frames[self.index] if self.frames else pygame.Surface((1, 1), pygame.SRCALPHA)


# описывает класс pixel font
class PixelFont:
    # инициализирует объект
    def __init__(self, path, target_size, scale=2):
        self.scale = max(1, int(scale))
        self.target_size = int(target_size)
        base_size = max(8, int(round(self.target_size / self.scale)))
        self.base_font = pygame.font.Font(path, base_size) if path else pygame.font.Font(None, base_size)

    # отрисовывает
    def render(self, text, antialias, color, background=None):
        image = self.base_font.render(text, False, color, background)
        if self.scale == 1:
            return image
        return pygame.transform.scale(image, (max(1, image.get_width() * self.scale), max(1, image.get_height() * self.scale)))

    # выполняет size
    def size(self, text):
        width, height = self.base_font.size(text)
        return width * self.scale, height * self.scale

    # возвращает height
    def get_height(self):
        return self.base_font.get_height() * self.scale

    # возвращает linesize
    def get_linesize(self):
        return self.base_font.get_linesize() * self.scale


# описывает объект карты из tiled
@dataclass
class TiledMapObject:
    # хранит имя, тип и геометрию объекта на карте
    name: str = ""
    type_name: str = ""
    class_name: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    raw: dict = field(default_factory=dict)

    # создает объект карты из словаря tiled
    @classmethod
    def from_tiled_dict(cls, data, scale_x=1.0, scale_y=1.0):
        # хранит масштабированные координаты и размеры объекта
        scaled = dict(data)
        for key, factor in (("x", scale_x), ("y", scale_y), ("width", scale_x), ("height", scale_y)):
            if key in scaled:
                scaled[key] = float(scaled.get(key, 0)) * factor
        return cls(
            name=str(scaled.get("name", "")),
            type_name=str(scaled.get("type", "")),
            class_name=str(scaled.get("class", "")),
            x=float(scaled.get("x", 0)),
            y=float(scaled.get("y", 0)),
            width=float(scaled.get("width", 0)),
            height=float(scaled.get("height", 0)),
            raw=scaled,
        )

    # возвращает объединенную подпись объекта для поиска
    def label(self):
        return " ".join(part for part in (self.name, self.class_name, self.type_name) if part).strip().lower()

    # проверяет подходит ли объект под один из алиасов
    def matches(self, *aliases):
        label = self.label()
        wanted = [alias.lower() for alias in aliases if alias]
        return any(alias in label for alias in wanted)

    # возвращает центр объекта как точку мира
    @property
    def center(self):
        return pygame.Vector2(self.x + self.width * 0.5, self.y + self.height * 0.5)

    # возвращает прямоугольник объекта
    @property
    def rect(self):
        return pygame.Rect(
            int(round(self.x)),
            int(round(self.y)),
            max(1, int(round(self.width))),
            max(1, int(round(self.height))),
        )


# описывает тайловый слой карты
@dataclass
class TiledTileLayer:
    # хранит имя слоя, размеры сетки и массив gid тайлов
    name: str
    width: int
    height: int
    data: list[int]
    opacity: float = 1.0

    # возвращает gid тайла по координатам сетки
    def gid_at(self, tx, ty):
        if not (0 <= tx < self.width and 0 <= ty < self.height):
            return 0
        return self.data[ty * self.width + tx]

    # итерирует готовые тайлы слоя в заданной области
    def iter_tiles(self, gid_surfaces, start_tx=0, end_tx=None, start_ty=0, end_ty=None):
        end_tx = self.width if end_tx is None else min(self.width, end_tx)
        end_ty = self.height if end_ty is None else min(self.height, end_ty)
        start_tx = max(0, start_tx)
        start_ty = max(0, start_ty)
        for ty in range(start_ty, end_ty):
            base_index = ty * self.width
            for tx in range(start_tx, end_tx):
                gid = self.data[base_index + tx]
                if gid <= 0:
                    continue
                tile = gid_surfaces.get(gid)
                if tile is not None:
                    yield tx, ty, tile


# описывает загруженную tiled карту
@dataclass
class LoadedTileMap:
    # хранит геометрию карты, слои, тайлы и объекты tiled
    width: int
    height: int
    tile_width: int
    tile_height: int
    layers: list[TiledTileLayer]
    base_layers: list[TiledTileLayer]
    overlay_layers: list[TiledTileLayer]
    gid_surfaces: dict[int, pygame.Surface]
    object_layers: dict[str, list[TiledMapObject]]
    tilesets: list[dict]
    path: Path

    # возвращает слой карты по имени
    def get_layer(self, name):
        wanted = str(name).strip().lower()
        for layer in self.layers:
            if layer.name.strip().lower() == wanted:
                return layer
        return None

    # возвращает объекты из слоя по имени слоя
    def objects_in_layer(self, layer_name):
        wanted = str(layer_name).strip().lower()
        for name, objects in self.object_layers.items():
            if str(name).strip().lower() == wanted:
                return list(objects)
        return []

    # возвращает объекты подходящие под алиасы
    def objects_matching(self, *aliases):
        wanted = [alias.lower() for alias in aliases if alias]
        found = []
        for layer_name, objects in self.object_layers.items():
            layer_label = str(layer_name).strip().lower()
            if any(alias in layer_label for alias in wanted):
                found.extend(objects)
                continue
            for obj in objects:
                if obj.matches(*wanted):
                    found.append(obj)
        return found

    # возвращает прямоугольники коллизии для выбранных объектов
    # возвращает первый объект подходящий под алиасы
    def first_object(self, *aliases):
        matches = self.objects_matching(*aliases)
        return matches[0] if matches else None

    # возвращает центр первого объекта или fallback
    def first_center(self, *aliases, fallback=None):
        obj = self.first_object(*aliases)
        if obj:
            return obj.center
        if fallback is None:
            return None
        return pygame.Vector2(fallback)

    # возвращает прямоугольник первого объекта или fallback
    def first_rect(self, *aliases, fallback=None):
        obj = self.first_object(*aliases)
        if obj:
            return obj.rect
        if hasattr(fallback, "copy"):
            return fallback.copy()
        return fallback

    def collision_rects(self, *aliases):
        objects = self.objects_matching(*aliases) if aliases else [
            obj for layer_objects in self.object_layers.values() for obj in layer_objects
        ]
        return [obj.rect for obj in objects if obj.width > 0 and obj.height > 0]


# выполняет default конфиг
def default_config():
    return {
        "version": CONFIG_VERSION,
        "window_width": DEFAULT_WINDOW_SIZE[0],
        "window_height": DEFAULT_WINDOW_SIZE[1],
        "fullscreen": False,
        "music_volume": 0.7,
        "sfx_volume": 0.85,
    }


# описывает класс audio bus
class AudioBus:
    # инициализирует объект
    def __init__(self):
        self.ready = False
        self.sound_cache = {}
        self.current_music = None
        self.music_volume = 0.7
        self.sfx_volume = 0.85
        self.last_play_times = {}
        self.loop_channels = {}
        self.loop_specs = {}
        try:
            pygame.mixer.init()
            self.ready = True
        except pygame.error:
            self.ready = False

    # задает музыку volume
    def set_music_volume(self, volume):
        self.music_volume = clamp(float(volume), 0.0, 1.0)
        if self.ready:
            pygame.mixer.music.set_volume(self.music_volume)

    # задает sfx volume
    def set_sfx_volume(self, volume):
        self.sfx_volume = clamp(float(volume), 0.0, 1.0)
        self.refresh_loop_volumes()

    # находит музыку path
    def find_music_path(self, track_name):
        if not track_name:
            return None
        search_roots = [MUSIC_DIR, AUDIO_DIR / "music"]
        extensions = (".ogg", ".mp3", ".wav")
        for root in search_roots:
            for extension in extensions:
                path = root / f"{track_name}{extension}"
                if path.exists():
                    return path
        needle = str(track_name).lower()
        for root in search_roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if path.is_file() and path.suffix.lower() in extensions and path.stem.lower() == needle:
                    return path
        fallback = []
        for root in search_roots:
            if root.exists():
                for extension in extensions:
                    fallback.extend(sorted(root.glob(f"*{extension}")))
        return fallback[0] if fallback else None

    # воспроизводит музыку
    def play_music(self, track_name):
        if not self.ready:
            return
        if not track_name:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            self.current_music = None
            return
        path = self.find_music_path(track_name)
        if path is None:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            self.current_music = None
            return
        if self.current_music == path:
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(self.music_volume)
            self.current_music = path
        except pygame.error:
            self.current_music = None

    # находит звук path
    def find_sound_path(self, effect_name):
        if not effect_name:
            return None
        search_roots = [SOUND_DIR, AUDIO_DIR / "sfx"]
        extensions = (".ogg", ".wav", ".mp3")
        for root in search_roots:
            for extension in extensions:
                candidate = root / f"{effect_name}{extension}"
                if candidate.exists():
                    return candidate
        needle = str(effect_name).lower()
        for root in search_roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if path.is_file() and path.suffix.lower() in extensions and path.stem.lower() == needle:
                    return path
        return None

    # загружает звук
    def load_sound(self, effect_name):
        if effect_name not in self.sound_cache:
            path = self.find_sound_path(effect_name)
            if path is None:
                self.sound_cache[effect_name] = None
            else:
                try:
                    self.sound_cache[effect_name] = pygame.mixer.Sound(path)
                except pygame.error:
                    self.sound_cache[effect_name] = None
        return self.sound_cache.get(effect_name)

    # воспроизводит
    def play(self, effect_name, volume=0.45, cooldown=0.0):
        if not self.ready:
            return None
        now = pygame.time.get_ticks() / 1000.0
        if cooldown > 0:
            last_time = self.last_play_times.get(effect_name, -9999.0)
            if now - last_time < cooldown:
                return None
            self.last_play_times[effect_name] = now
        sound = self.load_sound(effect_name)
        if sound is not None:
            sound.set_volume(clamp(volume, 0.0, 1.0) * self.sfx_volume)
            return sound.play()
        return None

    # проверяет и подготавливает loop
    def ensure_loop(self, effect_name, channel_key, volume=0.45):
        if not self.ready:
            return
        sound = self.load_sound(effect_name)
        if sound is None:
            self.stop_loop(channel_key)
            return
        existing = self.loop_channels.get(channel_key)
        spec = self.loop_specs.get(channel_key)
        target_volume = clamp(volume, 0.0, 1.0) * self.sfx_volume
        if existing is not None and existing.get_busy() and spec and spec.get("effect_name") == effect_name:
            existing.set_volume(target_volume)
            return
        self.stop_loop(channel_key)
        channel = pygame.mixer.find_channel(True)
        if channel is None:
            return
        channel.set_volume(target_volume)
        channel.play(sound, loops=-1)
        self.loop_channels[channel_key] = channel
        self.loop_specs[channel_key] = {"effect_name": effect_name, "volume": clamp(volume, 0.0, 1.0)}

    # останавливает loop
    def stop_loop(self, channel_key):
        channel = self.loop_channels.pop(channel_key, None)
        self.loop_specs.pop(channel_key, None)
        if channel is not None:
            channel.stop()

    # останавливает all loops
    def stop_all_loops(self):
        for channel_key in list(self.loop_channels):
            self.stop_loop(channel_key)

    # выполняет refresh loop volumes
    def refresh_loop_volumes(self):
        if not self.ready:
            return
        for channel_key, channel in list(self.loop_channels.items()):
            spec = self.loop_specs.get(channel_key)
            if spec is None:
                continue
            if channel.get_busy():
                channel.set_volume(spec["volume"] * self.sfx_volume)
            else:
                self.loop_channels.pop(channel_key, None)
                self.loop_specs.pop(channel_key, None)


# проверяет и подготавливает generated assets
def ensure_generated_assets():
    # The project now relies on hand-authored assets under the current asset root.
    return


# собирает hero sheet
def build_hero_sheet(cloak, skin, glow, steel):
    frame = 64
    sheet = pygame.Surface((frame * 5, frame), pygame.SRCALPHA)
    for index in range(5):
        surf = pygame.Surface((frame, frame), pygame.SRCALPHA)
        bob = int(math.sin(index / 5 * math.tau) * 2)
        sway = math.sin(index / 5 * math.tau)
        pygame.draw.ellipse(surf, (0, 0, 0, 80), (14, 49, 36, 10))
        pygame.draw.polygon(
            surf,
            cloak,
            [
                (18, 22 + bob),
                (45, 22 + bob),
                (50 + sway * 3, 52),
                (14 - sway * 3, 54),
            ],
        )
        pygame.draw.circle(surf, skin, (32, 17 + bob), 9)
        pygame.draw.circle(surf, (27, 23, 23), (29, 16 + bob), 1)
        pygame.draw.circle(surf, (27, 23, 23), (35, 16 + bob), 1)
        pygame.draw.line(surf, steel, (26, 48), (18 + sway * 4, 61), 4)
        pygame.draw.line(surf, steel, (38, 48), (44 - sway * 4, 61), 4)
        pygame.draw.line(surf, steel, (46, 30 + bob), (56, 39 + sway * 2), 4)
        pygame.draw.circle(surf, glow, (52, 27 + bob), 4)
        pygame.draw.circle(surf, (255, 255, 255, 120), (52, 27 + bob), 2)
        sheet.blit(surf, (index * frame, 0))
    return sheet


# собирает mentor sheet
def build_mentor_sheet(cloak, skin, glow):
    frame = 64
    sheet = pygame.Surface((frame * 5, frame), pygame.SRCALPHA)
    for index in range(5):
        surf = pygame.Surface((frame, frame), pygame.SRCALPHA)
        bob = int(math.sin(index / 5 * math.tau) * 1.5)
        sway = math.sin(index / 5 * math.tau)
        pygame.draw.ellipse(surf, (0, 0, 0, 84), (12, 50, 40, 9))
        pygame.draw.polygon(surf, cloak, [(16, 22 + bob), (47, 22 + bob), (53, 54), (10, 55)])
        pygame.draw.circle(surf, skin, (32, 17 + bob), 9)
        pygame.draw.line(surf, (225, 220, 208), (25, 24 + bob), (25, 40 + bob), 3)
        pygame.draw.line(surf, (225, 220, 208), (39, 24 + bob), (39, 40 + bob), 3)
        pygame.draw.line(surf, (111, 82, 55), (15, 25 + bob), (8, 58), 4)
        pygame.draw.circle(surf, glow, (8, 22 + bob), 5)
        pygame.draw.line(surf, (104, 86, 60), (28, 47), (24 + sway * 3, 61), 4)
        pygame.draw.line(surf, (104, 86, 60), (36, 47), (40 - sway * 3, 61), 4)
        sheet.blit(surf, (index * frame, 0))
    return sheet


# собирает messenger sheet
def build_messenger_sheet():
    frame = 64
    sheet = pygame.Surface((frame * 5, frame), pygame.SRCALPHA)
    for index in range(5):
        surf = pygame.Surface((frame, frame), pygame.SRCALPHA)
        bob = int(math.sin(index / 5 * math.tau) * 2)
        sway = math.sin(index / 5 * math.tau)
        pygame.draw.ellipse(surf, (0, 0, 0, 80), (14, 49, 36, 10))
        pygame.draw.polygon(surf, (108, 92, 70), [(18, 23 + bob), (45, 23 + bob), (49, 53), (13, 53)])
        pygame.draw.circle(surf, (235, 224, 214), (32, 17 + bob), 9)
        pygame.draw.line(surf, (225, 224, 228), (24, 18 + bob), (19, 31 + bob), 3)
        pygame.draw.line(surf, (225, 224, 228), (40, 18 + bob), (45, 30 + bob), 3)
        pygame.draw.line(surf, (149, 119, 80), (21, 28 + bob), (12 + sway * 2, 38 + bob), 4)
        pygame.draw.line(surf, (149, 119, 80), (43, 28 + bob), (52 - sway * 2, 39 + bob), 4)
        pygame.draw.line(surf, (149, 119, 80), (27, 48), (24 + sway * 2, 61), 4)
        pygame.draw.line(surf, (149, 119, 80), (37, 48), (40 - sway * 2, 61), 4)
        sheet.blit(surf, (index * frame, 0))
    return sheet


# собирает ghoul sheet
def build_ghoul_sheet():
    frame = 64
    sheet = pygame.Surface((frame * 5, frame), pygame.SRCALPHA)
    for index in range(5):
        surf = pygame.Surface((frame, frame), pygame.SRCALPHA)
        crouch = int(math.sin(index / 5 * math.tau) * 3)
        pygame.draw.ellipse(surf, (0, 0, 0, 90), (13, 50, 38, 8))
        pygame.draw.ellipse(surf, (78, 29, 33), (14, 17 + crouch, 36, 30))
        pygame.draw.circle(surf, (164, 57, 59), (32, 19 + crouch), 13)
        pygame.draw.circle(surf, (246, 233, 219), (26, 26 + crouch), 3)
        pygame.draw.circle(surf, (246, 233, 219), (38, 26 + crouch), 3)
        pygame.draw.line(surf, (28, 14, 18), (19, 29 + crouch), (10, 45 + crouch), 4)
        pygame.draw.line(surf, (28, 14, 18), (45, 29 + crouch), (54, 45 + crouch), 4)
        pygame.draw.line(surf, (31, 14, 17), (25, 45), (21, 61), 4)
        pygame.draw.line(surf, (31, 14, 17), (39, 45), (43, 61), 4)
        sheet.blit(surf, (index * frame, 0))
    return sheet


# собирает дракона sheet
def build_dragon_sheet():
    frame = 160
    sheet = pygame.Surface((frame * 5, frame), pygame.SRCALPHA)
    for index in range(5):
        surf = pygame.Surface((frame, frame), pygame.SRCALPHA)
        wing = math.sin(index / 5 * math.tau)
        neck = math.cos(index / 5 * math.tau) * 3
        pygame.draw.ellipse(surf, (0, 0, 0, 90), (24, 112, 112, 18))
        pygame.draw.ellipse(surf, (83, 31, 24), (28, 54, 94, 52))
        pygame.draw.polygon(surf, (132, 51, 36), [(42, 58), (22, 18 - wing * 8), (68, 50), (54, 72)])
        pygame.draw.polygon(surf, (132, 51, 36), [(92, 58), (126, 18 + wing * 8), (72, 50), (82, 72)])
        pygame.draw.polygon(
            surf,
            (176, 84, 42),
            [(74, 54), (80, 30 + neck), (95, 18 + neck), (112, 28 + neck), (106, 52), (88, 58)],
        )
        pygame.draw.circle(surf, (244, 218, 116), (110, 34 + int(neck)), 6)
        pygame.draw.line(surf, (41, 19, 17), (50, 87), (40 - wing * 7, 140), 8)
        pygame.draw.line(surf, (41, 19, 17), (96, 87), (106 + wing * 7, 140), 8)
        pygame.draw.polygon(surf, (170, 98, 52), [(18, 70), (0, 58), (10, 79), (0, 101), (20, 92)])
        pygame.draw.rect(surf, (128, 96, 38), (88, 50, 22, 10), border_radius=4)
        pygame.draw.circle(surf, (214, 186, 116), (107, 55), 4, 2)
        sheet.blit(surf, (index * frame, 0))
    return sheet


# собирает брата sheet
def build_brother_sheet():
    frame = 96
    sheet = pygame.Surface((frame * 5, frame), pygame.SRCALPHA)
    for index in range(5):
        surf = pygame.Surface((frame, frame), pygame.SRCALPHA)
        bob = int(math.sin(index / 5 * math.tau) * 2)
        sway = math.sin(index / 5 * math.tau)
        pygame.draw.ellipse(surf, (0, 0, 0, 90), (18, 77, 60, 12))
        pygame.draw.polygon(surf, (40, 39, 54), [(24, 28 + bob), (72, 28 + bob), (80, 76), (16, 76)])
        pygame.draw.polygon(surf, (222, 216, 193), [(45, 29 + bob), (51, 29 + bob), (55, 74), (41, 74)])
        pygame.draw.circle(surf, (235, 220, 205), (48, 21 + bob), 12)
        pygame.draw.circle(surf, (19, 19, 24), (44, 21 + bob), 2)
        pygame.draw.circle(surf, (19, 19, 24), (52, 21 + bob), 2)
        pygame.draw.circle(surf, (244, 240, 220), (18, 42), 8)
        pygame.draw.circle(surf, (135, 102, 255), (78, 42), 8)
        pygame.draw.line(surf, (122, 109, 90), (35, 75), (30 + sway * 2, 91), 4)
        pygame.draw.line(surf, (122, 109, 90), (61, 75), (66 - sway * 2, 91), 4)
        sheet.blit(surf, (index * frame, 0))
    return sheet


