from core import *
from data import CONTROL_ROWS


# описывает класс ui mixin
class UIMixin:
    # отрисовывает текущую сцену
    def draw(self):
        self.screen.fill(BACKGROUND)
        if self.scene == "menu":
            self.draw_menu()
        elif self.scene == "settings":
            self.draw_settings()
        elif self.scene == "story":
            self.draw_story_clean()
        elif self.scene == "dialogue":
            self.draw_dialogue_clean()
        elif self.scene == "resident_intro":
            self.draw_resident_intro()
        elif self.scene == "caste_choice":
            self.draw_caste_choice()
        elif self.scene == "gameplay":
            self.draw_gameplay()
        elif self.scene == "upgrade":
            self.draw_gameplay()
            self.draw_upgrade_choice()
        elif self.scene == "tunnel":
            self.draw_tunnel()
        elif self.scene == "ending_choice":
            self.draw_gameplay()
            self.draw_ending_choice()
        elif self.scene == "death":
            self.draw_gameplay()
            self.draw_death_overlay()
        if self.wave_banner_timer > 0:
            self.draw_wave_banner()
        if self.toast_timer > 0 and not (self.scene == "gameplay" and self.stats_overlay):
            self.draw_toast()
        view_rect = self.logical_view_rect()
        final_frame = pygame.transform.scale(self.screen, view_rect.size)
        self.window.fill((0, 0, 0))
        self.window.blit(final_frame, view_rect.topleft)
        pygame.display.flip()

    # отрисовывает меню
    def draw_menu(self):
        if self.menu_art is not None:
            self.screen.blit(self.menu_art, (0, 0))
        else:
            self.screen.fill((0, 0, 0))

        veil = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for x in range(WINDOW_WIDTH):
            t = x / max(1, WINDOW_WIDTH - 1)
            alpha = int(lerp(228, 22, smoothstep(0.05, 0.88, t)))
            pygame.draw.line(veil, (10, 9, 12, alpha), (x, 0), (x, WINDOW_HEIGHT))
        self.screen.blit(veil, (0, 0))

        panel_rect = pygame.Rect(70, 130, 780, 780)
        draw_pixel_panel(self.screen, panel_rect, fill=(11, 11, 14), border=(190, 182, 165), padding=5)
        draw_text(self.screen, self.title_font, "Blood Rift", (241, 229, 210), (110, 184))

        save_exists = self.has_compatible_save()
        x = 112
        y = 360
        for index, item in enumerate(self.menu_items):
            rect = pygame.Rect(x, y + index * 82, 676, 64)
            disabled = index == 1 and not save_exists
            draw_pixel_button(self.screen, rect, selected=index == self.menu_index and not disabled, disabled=disabled)
            text_color = (242, 236, 228) if index == self.menu_index and not disabled else (214, 206, 193)
            if disabled:
                text_color = (118, 118, 124)
            label = self.menu_font.render(item, True, text_color)
            self.screen.blit(label, label.get_rect(midleft=(rect.x + 26, rect.centery)))

    # отрисовывает настройки
    def draw_settings(self):
        self.draw_background_mist()
        draw_centered_text(self.screen, self.title_font, "Настройки", TEXT, (WINDOW_WIDTH // 2, 104))
        for index, line in enumerate(wrap_text(self.small_font, self.settings_notice, 1180)):
            notice = self.small_font.render(line, False, SUBTLE)
            self.screen.blit(notice, notice.get_rect(center=(WINDOW_WIDTH // 2, 154 + index * 24)))

        panel_rect = pygame.Rect(250, 180, 1420, 840)
        draw_pixel_panel(self.screen, panel_rect, fill=(12, 12, 16), border=(196, 184, 154), padding=6)

        draw_text(self.screen, self.menu_font, "Экран", TEXT, (360, 224), shadow=False)
        dropdown_rect = self.settings_resolution_dropdown_rect()
        draw_pixel_button(self.screen, dropdown_rect, selected=self.settings_resolution_dropdown_open)
        selected_label = self.settings_resolution_option_label(self.settings_resolution_selected_option_index())
        label = self.small_font.render(selected_label, True, TEXT)
        self.screen.blit(label, label.get_rect(midleft=(dropdown_rect.x + 28, dropdown_rect.centery)))
        arrow = self.small_font.render("v", True, TEXT)
        self.screen.blit(arrow, arrow.get_rect(center=(dropdown_rect.right - 26, dropdown_rect.centery + 2)))

        draw_text(self.screen, self.menu_font, "Звук", TEXT, (360, 300), shadow=False)
        self.draw_settings_slider("Музыка", "music_volume", 520, 346)
        self.draw_settings_slider("Эффекты", "sfx_volume", 520, 424)

        table_rect = pygame.Rect(360, 510, 1200, 288)
        draw_pixel_panel(self.screen, table_rect, fill=(14, 14, 18), border=(196, 184, 154), padding=4)
        pygame.draw.rect(self.screen, (26, 26, 30), (378, 528, 1164, 34))
        header_action = self.small_font.render("Действие", True, (226, 210, 184))
        header_key = self.small_font.render("Клавиши", True, (226, 210, 184))
        header_note = self.small_font.render("Описание", True, (226, 210, 184))
        self.screen.blit(header_action, (394, 540))
        self.screen.blit(header_key, (760, 540))
        self.screen.blit(header_note, (1020, 540))

        for index, (action, key, note) in enumerate(CONTROL_ROWS):
            y = 586 + index * 34
            if index % 2 == 0:
                pygame.draw.rect(self.screen, (22, 22, 28), (378, y - 10, 1164, 30))
            self.screen.blit(self.small_font.render(action, False, TEXT), (394, y))
            self.screen.blit(self.small_font.render(key, False, GOLD), (760, y))
            self.screen.blit(self.small_font.render(note, False, (226, 226, 232)), (1020, y))

        apply_rect = pygame.Rect(WINDOW_WIDTH // 2 - 236, WINDOW_HEIGHT - 144, 220, 62)
        save_rect = pygame.Rect(WINDOW_WIDTH // 2 + 16, WINDOW_HEIGHT - 144, 220, 62)
        for rect, label in ((apply_rect, "Применить"), (save_rect, "Сохранить")):
            draw_pixel_panel(self.screen, rect, fill=(10, 10, 12), border=(240, 240, 244), padding=4)
            draw_centered_text(self.screen, self.menu_font, label, TEXT, rect.center, shadow=False)

        footer = "Esc - назад" if not self.first_launch_setup else "Сначала выбери окно и сохрани настройки"
        hint = self.small_font.render(footer, True, SUBTLE)
        self.screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50)))

        if self.settings_resolution_dropdown_open:
            option_count = self.settings_resolution_option_count()
            selected_index = self.settings_resolution_selected_option_index()
            dropdown_panel = pygame.Rect(dropdown_rect.x, dropdown_rect.bottom + 10, dropdown_rect.width, 12 + option_count * 52)
            draw_pixel_panel(self.screen, dropdown_panel, fill=(16, 18, 24), border=(240, 240, 244), padding=4)
            for index in range(option_count):
                option_rect = self.settings_resolution_option_rect(index)
                draw_pixel_button(self.screen, option_rect, selected=index == selected_index)
                option_label = self.small_font.render(self.settings_resolution_option_label(index), True, TEXT)
                self.screen.blit(option_label, option_label.get_rect(midleft=(option_rect.x + 24, option_rect.centery)))
                if index == selected_index:
                    marker = self.small_font.render(">", True, TEXT)
                    self.screen.blit(marker, marker.get_rect(center=(option_rect.right - 24, option_rect.centery)))

    # отрисовывает фон дымку
    def draw_background_mist(self, alpha=255):
        self.screen.fill((9, 8, 12))
        mist = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for y in range(0, WINDOW_HEIGHT, 2):
            t = y / max(1, WINDOW_HEIGHT)
            color = (
                int(lerp(22, 10, t)),
                int(lerp(14, 8, t)),
                int(lerp(18, 12, t)),
                alpha,
            )
            pygame.draw.line(mist, color, (0, y), (WINDOW_WIDTH, y))
        time_t = pygame.time.get_ticks() / 1000.0
        for index in range(10):
            cx = int(120 + index * 180 + math.sin(time_t * 0.6 + index * 0.8) * 70)
            cy = int(80 + index * 82)
            radius = 110 + (index % 3) * 28
            pygame.draw.circle(mist, (86, 44, 52, 18), (cx, cy), radius)
        self.screen.blit(mist, (0, 0))

    # отрисовывает настройки ползунок
    def draw_settings_slider(self, label, key, x, y):
        draw_text(self.screen, self.small_font, label, TEXT, (360, y - 4), shadow=False)
        minus_rect = pygame.Rect(x - 60, y - 6, 42, 42)
        plus_rect = pygame.Rect(x + 898, y - 6, 42, 42)
        for rect, sign in ((minus_rect, "-"), (plus_rect, "+")):
            draw_pixel_button(self.screen, rect)
            draw_centered_text(self.screen, self.menu_font, sign, TEXT, rect.center, shadow=False)
        bar_rect = pygame.Rect(x, y, 880, 28)
        draw_pixel_bar(self.screen, bar_rect, self.pending_config[key], (201, 185, 141), border=(188, 181, 162), track=(86, 90, 94))
        value = self.small_font.render(f"{int(self.pending_config[key] * 100)}%", True, TEXT)
        self.screen.blit(value, value.get_rect(midleft=(plus_rect.right + 22, bar_rect.centery)))

    # отрисовывает сюжет clean
    def draw_story_clean(self):
        page = self.current_story_page()
        if not page:
            return

        image_box = pygame.Rect(120, 56, 1680, 620)
        text_box = pygame.Rect(140, 720, 1640, 300)

        # выполняет страницу image
        def page_image(page_data):
            image_key = page_data.get("image")
            if not image_key:
                return None
            return self.story_images.get(str(image_key))

        # отрисовывает страницу
        def draw_page(target, page_data, char_count=None, show_text=True, image_dy=0, alpha=255, highlight=None):
            layer = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            layer.fill((0, 0, 0))
            image = page_image(page_data)
            if image is not None:
                image_rect = image.get_rect(midtop=(WINDOW_WIDTH // 2, image_box.y + int(image_dy)))
                layer.blit(image, image_rect)
            elif page_data.get("title"):
                draw_centered_text(layer, self.title_font, page_data["title"], (255, 255, 255), (WINDOW_WIDTH // 2, 170))

            if show_text:
                title = page_data.get("title", "")
                text_top = text_box.y + 10
                if title:
                    title_surf = self.menu_font.render(title, False, (255, 255, 255))
                    layer.blit(title_surf, title_surf.get_rect(center=(WINDOW_WIDTH // 2, text_top + 22)))
                    text_top += 50
                visible_text = page_data.get("text", "")
                if char_count is not None:
                    visible_text = visible_text[: int(char_count)]
                for index, line in enumerate(wrap_text(self.body_font, visible_text, text_box.width)):
                    surf = self.body_font.render(line, False, (255, 255, 255))
                    layer.blit(surf, surf.get_rect(center=(WINDOW_WIDTH // 2, text_top + index * 40)))
            if alpha < 255:
                layer.set_alpha(alpha)
            target.blit(layer, (0, 0))

        if self.story_intro_mode == "menu_pan":
            progress = clamp(self.story_intro_timer / 1.15, 0.0, 1.0)
            intro_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            if self.menu_art is not None:
                intro_surface.blit(self.menu_art, (0, 0))
            else:
                intro_surface.fill((0, 0, 0))
            veil = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            for x in range(WINDOW_WIDTH):
                t = x / max(1, WINDOW_WIDTH - 1)
                veil_alpha = int(lerp(228, 22, smoothstep(0.05, 0.88, t)))
                pygame.draw.line(veil, (10, 9, 12, veil_alpha), (x, 0), (x, WINDOW_HEIGHT))
            intro_surface.blit(veil, (0, 0))
            panel_rect = pygame.Rect(70, 130, 780, 780)
            draw_pixel_panel(intro_surface, panel_rect, fill=(11, 11, 14), border=(190, 182, 165), padding=5)
            draw_text(intro_surface, self.title_font, "Blood Rift", (241, 229, 210), (110, 184))
            x = 112
            y = 360
            save_exists = self.has_compatible_save()
            for index, item in enumerate(self.menu_items):
                rect = pygame.Rect(x, y + index * 82, 676, 64)
                disabled = index == 1 and not save_exists
                draw_pixel_button(intro_surface, rect, selected=index == self.menu_index and not disabled, disabled=disabled)
                text_color = (242, 236, 228) if index == self.menu_index and not disabled else (214, 206, 193)
                if disabled:
                    text_color = (118, 118, 124)
                label = self.menu_font.render(item, True, text_color)
                intro_surface.blit(label, label.get_rect(midleft=(rect.x + 26, rect.centery)))
            intro_surface.set_alpha(int(255 * (1.0 - smoothstep(0.55, 1.0, progress))))
            self.screen.blit(intro_surface, (0, int(progress * 260)))
            fade = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            fade.fill((0, 0, 0, int(170 * smoothstep(0.2, 0.85, progress))))
            self.screen.blit(fade, (0, 0))
            return

        if self.story_transition:
            t = clamp(self.story_transition["timer"] / max(0.001, self.story_transition["duration"]), 0.0, 1.0)
            from_page = self.story_pages[self.story_transition["from_index"]]
            to_page = self.story_pages[self.story_transition["to_index"]]
            kind = self.story_transition["type"]
            if kind == "white_flash":
                if t < 0.5:
                    draw_page(self.screen, from_page, show_text=False)
                    flash_alpha = int(255 * smoothstep(0.0, 1.0, t / 0.5))
                else:
                    draw_page(self.screen, to_page, show_text=False)
                    flash_alpha = int(255 * (1.0 - smoothstep(0.0, 1.0, (t - 0.5) / 0.5)))
                flash = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                flash.fill((255, 255, 255, flash_alpha))
                self.screen.blit(flash, (0, 0))
                return
            if kind == "crossfade":
                draw_page(self.screen, from_page, show_text=False, alpha=int(255 * (1.0 - t)))
                draw_page(self.screen, to_page, show_text=False, alpha=int(255 * t))
                return
            if kind == "dark_slide":
                if t < 0.5:
                    draw_page(self.screen, from_page, show_text=False)
                    dark = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                    dark.fill((0, 0, 0, int(255 * smoothstep(0.0, 1.0, t / 0.5))))
                    self.screen.blit(dark, (0, 0))
                else:
                    self.screen.fill((0, 0, 0))
                    slide_t = smoothstep(0.0, 1.0, (t - 0.5) / 0.5)
                    image_shift = lerp(-760, 0, slide_t)
                    draw_page(self.screen, to_page, show_text=False, image_dy=image_shift)
                    dark = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                    dark.fill((0, 0, 0, int(140 * (1.0 - slide_t))))
                    self.screen.blit(dark, (0, 0))
                return
            draw_page(self.screen, from_page, show_text=False, alpha=int(255 * (1.0 - t)))
            draw_page(self.screen, to_page, show_text=False, alpha=int(255 * t))
            return

        draw_page(
            self.screen,
            page,
            char_count=self.story_text_progress if not self.story_choice_mode else len(page.get("text", "")),
            show_text=not self.story_choice_mode,
            highlight=None,
        )

        if self.story_choice_mode and page.get("choices"):
            for index, (rect, choice) in enumerate(zip(self.story_choice_rects(), page["choices"])):
                draw_pixel_button(self.screen, rect, selected=index == self.story_choice_index)
                label = self.menu_font.render(choice["text"], False, TEXT)
                self.screen.blit(label, label.get_rect(center=rect.center))
            return

        if self.story_text_is_complete() and self.story_hint_ready():
            if self.story_is_ending:
                footer = "Enter / ЛКМ — дальше" if self.story_index < len(self.story_pages) - 1 else "Enter / ЛКМ — в меню"
            elif page.get("choices"):
                footer = "Enter / ЛКМ — к выбору"
            else:
                footer = "Enter / ЛКМ — дальше"
            hint = self.small_font.render(footer, True, SUBTLE)
            self.screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 36)))

    # отрисовывает gameplay сцену
    def draw_gameplay_scene(self, include_hud=True, show_names=True):
        self.draw_world()
        for attack in self.player_arcs:
            attack.draw(self.screen, self.camera)
        for projectile in self.player_projectiles:
            projectile.draw(self.screen, self.camera)
        for beam in self.player_beams:
            beam.draw(self.screen, self.camera)
        for projectile in self.enemy_projectiles:
            projectile.draw(self.screen, self.camera)
        for beam in self.enemy_beams:
            beam.draw(self.screen, self.camera)
        for zone in self.enemy_zones:
            zone.draw(self.screen, self.camera)
        for sweep in self.enemy_sweeps:
            sweep.draw(self.screen, self.camera)
        for ring in self.enemy_rings:
            ring.draw(self.screen, self.camera)
        for orb in self.gravity_orbs:
            orb.draw(self.screen, self.camera)
        for pickup in self.pickups:
            self.draw_pickup(pickup)

        entities = []
        if self.master and self.chapter == "assault":
            entities.append(self.master)
        entities.extend(self.dummies)
        entities.extend(self.crystals)
        entities.extend(self.enemies)
        entities.extend(self.town_npcs)
        if self.brother:
            entities.append(self.brother)
        if self.player:
            entities.append(self.player)
        entities = [entity for entity in entities if entity]

        for entity in sorted(entities, key=lambda actor: actor.pos.y):
            entity.draw(self.screen, self.camera)
            if show_names and entity.name:
                pos = self.camera.apply(entity.pos)
                label = self.small_font.render(entity.name, True, TEXT)
                self.screen.blit(label, label.get_rect(center=(pos.x, pos.y - entity.radius - 26)))

        self.draw_world_overlay()

        for floater in self.floaters:
            self.draw_floater(floater)

        if self.dragon:
            self.draw_dragon_overlay()
        for effect in self.relic_effects:
            effect.draw(self.screen)

        if include_hud:
            self.draw_hud()
            self.draw_boss_bar()
            if self.stats_overlay:
                self.draw_stats_overlay()

    # отрисовывает alert marker
    def draw_alert_marker(self, actor):
        pos = self.camera.apply(actor.pos)
        center = (int(pos.x), int(pos.y - actor.radius - 78))
        sign = self.sprite_bank.get("alert_sign")
        if sign is not None:
            self.screen.blit(sign, sign.get_rect(center=center))
            return
        shadow = self.title_font.render("!", False, (52, 8, 10))
        glyph = self.title_font.render("!", False, (164, 28, 36))
        self.screen.blit(shadow, shadow.get_rect(center=(center[0] + 2, center[1] + 3)))
        self.screen.blit(glyph, glyph.get_rect(center=center))

    # отрисовывает жителя intro
    def draw_resident_intro(self):
        self.screen.fill((0, 0, 0))
        self.draw_gameplay_scene(include_hud=False, show_names=False)
        if self.resident_intro_phase >= 1:
            self.draw_alert_marker(self.player)
            self.draw_alert_marker(self.master)
        frame = self.screen.copy()
        zoom = 1.18
        scaled_size = (int(WINDOW_WIDTH * zoom), int(WINDOW_HEIGHT * zoom))
        scaled = pygame.transform.scale(frame, scaled_size)
        self.screen.fill((0, 0, 0))
        self.screen.blit(scaled, ((WINDOW_WIDTH - scaled_size[0]) // 2, (WINDOW_HEIGHT - scaled_size[1]) // 2))

    # отрисовывает диалог clean
    def draw_dialogue_clean(self):
        if self.dialogue_backdrop == "world":
            self.draw_gameplay_scene(include_hud=False, show_names=False)
            dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 138))
            self.screen.blit(dim, (0, 0))
        else:
            self.screen.fill((0, 0, 0))

        entry = self.current_dialogue_entry()
        if not entry:
            return

        left_key = entry.get("left_portrait", "mentor")
        right_key = entry.get("right_portrait", "hero")
        active_key = entry.get("portrait")

        # определяет portrait
        def resolve_portrait(key):
            portrait = self.vn_portraits.get(key)
            if portrait is not None:
                return portrait
            if key == "hero":
                return pygame.transform.smoothscale(
                    self.sprite_bank["hero_light" if self.player.caste == "light" else "hero_dark"][0], (360, 360)
                )
            if key in ("mentor", "master"):
                return pygame.transform.smoothscale(
                    self.sprite_bank["mentor_light" if self.player.caste == "light" else "mentor_dark"][0], (320, 320)
                )
            return pygame.transform.smoothscale(self.sprite_bank["messenger"][0], (320, 320))

        left_portrait = fit_surface_to_box(resolve_portrait(left_key), (520, 720), anchor="midbottom", allow_upscale=False)
        right_portrait = fit_surface_to_box(resolve_portrait(right_key), (560, 760), anchor="midbottom", allow_upscale=False)

        portrait_specs = [
            (left_portrait, pygame.Rect(78, 170, 520, 730), active_key == left_key),
            (right_portrait, pygame.Rect(WINDOW_WIDTH - 638, 130, 560, 770), active_key == right_key),
        ]
        for portrait, frame_rect, active in portrait_specs:
            portrait_rect = portrait.get_rect(midbottom=(frame_rect.width // 2, frame_rect.height - 12))
            silhouette = portrait.copy()
            silhouette.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
            layer = pygame.Surface(frame_rect.size, pygame.SRCALPHA)
            for offset in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                layer.blit(silhouette, portrait_rect.move(*offset))
            portrait_surface = portrait if active else portrait.copy()
            if not active:
                portrait_surface.fill((0, 0, 0, 138), special_flags=pygame.BLEND_RGBA_SUB)
            layer.blit(portrait_surface, portrait_rect)
            self.screen.blit(layer, frame_rect)

        if entry.get("choices"):
            response_panel = pygame.Rect(34, WINDOW_HEIGHT - 268, WINDOW_WIDTH - 68, 214)
            draw_pixel_panel(self.screen, response_panel, fill=(10, 10, 12), border=(236, 236, 240), padding=5)
            inner = response_panel.inflate(-16, -16)
            pygame.draw.rect(self.screen, (18, 18, 24), inner)
            pygame.draw.rect(self.screen, (0, 0, 0), inner, 2)
            title_rect = pygame.Rect(WINDOW_WIDTH // 2 - 250, response_panel.y + 18, 500, 56)
            draw_pixel_panel(self.screen, title_rect, fill=(8, 8, 10), border=(236, 236, 240), padding=4)
            draw_centered_text(self.screen, self.menu_font, "Твой ответ", TEXT, title_rect.center, shadow=False)
            count = len(entry["choices"])
            total_width = count * 440 + max(0, count - 1) * 28
            start_x = WINDOW_WIDTH // 2 - total_width // 2
            for index, choice in enumerate(entry["choices"]):
                rect = pygame.Rect(start_x + index * 468, response_panel.y + 108, 440, 74)
                draw_pixel_button(self.screen, rect, selected=index == self.dialogue_choice_index)
                lines = wrap_text(self.small_font, choice["text"], 384)
                for line_index, line in enumerate(lines[:2]):
                    label = self.small_font.render(line, False, TEXT)
                    self.screen.blit(label, label.get_rect(center=(rect.centerx, rect.y + 18 + line_index * 24)))
            return

        box_rect = pygame.Rect(90, 752, WINDOW_WIDTH - 180, 238)
        draw_pixel_panel(self.screen, box_rect, fill=(6, 6, 8), border=(236, 236, 240), padding=5)
        inner = box_rect.inflate(-16, -16)
        pygame.draw.rect(self.screen, (0, 0, 0), inner)
        pygame.draw.rect(self.screen, (255, 255, 255), inner, 3)
        speaker_text = entry.get("speaker", "")
        if speaker_text:
            speaker = self.menu_font.render(speaker_text, False, (255, 255, 255))
            self.screen.blit(speaker, (inner.x + 20, inner.y + 14))

        text_style = entry.get("style")
        text_font = self.small_font if text_style == "shiver" else self.body_font
        base_y = inner.y + (54 if speaker_text else 24)
        line_step = 30 if text_style == "shiver" else 34
        wrap_width = inner.width - 40
        lines = wrap_text(text_font, entry.get("text", ""), wrap_width)
        if text_style == "shiver_letters" and self.dialogue_entry_timer < entry.get("style_duration", 2.0):
            tick = pygame.time.get_ticks() * 0.035
            for index, line in enumerate(lines):
                x = inner.x + 20
                y = base_y + index * line_step
                for letter_index, ch in enumerate(line):
                    glyph = text_font.render(ch, False, (255, 255, 255))
                    if ch.strip():
                        dx = int(math.sin(tick + index * 0.63 + letter_index * 0.37) * 2)
                        dy = int(math.cos(tick * 0.92 + letter_index * 0.41) * 2)
                    else:
                        dx = 0
                        dy = 0
                    self.screen.blit(glyph, (x + dx, y + dy))
                    x += glyph.get_width()
        else:
            for index, line in enumerate(lines):
                surf = text_font.render(line, False, (255, 255, 255))
                x = inner.x + 20
                if text_style == "shiver":
                    x += int(math.sin(pygame.time.get_ticks() * 0.02 + index * 0.8) * 3)
                self.screen.blit(surf, (x, base_y + index * line_step))

        hint = self.small_font.render("Enter — дальше", False, (232, 232, 236))
        self.screen.blit(hint, hint.get_rect(bottomright=(inner.right - 18, inner.bottom - 12)))

    # отрисовывает касту выбор
    def draw_caste_choice(self):
        self.draw_background_mist()
        draw_centered_text(self.screen, self.title_font, "Выбор Пути", TEXT, (WINDOW_WIDTH // 2, 150))
        cards = [
            (
                "1. Вернуться к матери",
                "Огонь зовёт назад",
                "Ты бросаешься обратно к деревне, туда, где в пламени ещё может ждать родной голос.",
                GOLD,
            ),
            (
                "2. Бежать своей дорогой",
                "Лес шепчет вперёд",
                "Ты рвёшься глубже в чащу, прочь от крика и жара, надеясь выжить любой ценой.",
                VIOLET,
            ),
        ]
        card_width = 460
        card_height = 410
        gap = 36
        total_width = card_width * 2 + gap
        start_x = WINDOW_WIDTH // 2 - total_width // 2
        for index, (title, subtitle, body, accent) in enumerate(cards):
            rect = pygame.Rect(start_x + index * (card_width + gap), 300, card_width, card_height)
            selected = index == self.choice_focus
            panel = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (22, 18, 23, 225), panel.get_rect(), border_radius=24)
            pygame.draw.rect(panel, accent if selected else (104, 83, 86), panel.get_rect(), 3, border_radius=24)
            self.screen.blit(panel, rect)
            emblem_center = (rect.centerx, rect.y + 82)
            pygame.draw.circle(self.screen, (240, 232, 216), emblem_center, 44, 3)
            if index == 0:
                pygame.draw.circle(self.screen, accent, emblem_center, 20)
                for ray in range(8):
                    direction = pygame.Vector2(0, -1).rotate(ray * 45)
                    start = pygame.Vector2(emblem_center) + direction * 34
                    end = pygame.Vector2(emblem_center) + direction * 56
                    pygame.draw.line(self.screen, accent, start, end, 4)
            else:
                pygame.draw.circle(self.screen, accent, (emblem_center[0] + 10, emblem_center[1]), 22)
                pygame.draw.circle(self.screen, (22, 18, 23), (emblem_center[0] - 6, emblem_center[1]), 22)
                pygame.draw.circle(self.screen, accent, emblem_center, 44, 3)
            title_lines = wrap_text(self.menu_font, title, rect.width - 64)
            for line_index, line in enumerate(title_lines[:2]):
                draw_centered_text(
                    self.screen,
                    self.menu_font,
                    line,
                    TEXT,
                    (rect.centerx, rect.y + 158 + line_index * 30),
                    shadow=False,
                )
            subtitle_image = self.body_font.render(subtitle, True, accent)
            self.screen.blit(subtitle_image, subtitle_image.get_rect(center=(rect.centerx, rect.y + 236)))
            for line_index, line in enumerate(wrap_text(self.small_font, body, 360)):
                text = self.small_font.render(line, True, (222, 214, 208))
                self.screen.blit(text, text.get_rect(center=(rect.centerx, rect.y + 296 + line_index * 26)))
        hint = self.small_font.render("1/2 или Enter. Последствия выбора раскроются только после пропущенных лет.", True, SUBTLE)
        self.screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 90)))

    # отрисовывает усиление выбор
    def draw_upgrade_choice(self):
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        self.screen.blit(dim, (0, 0))
        draw_centered_text(self.screen, self.title_font, "Печати Усиления", TEXT, (WINDOW_WIDTH // 2, 160))
        cards = [
            ("1. Жизнь", "Увеличить максимум HP и частично восстановить здоровье.", GREEN),
            ("2. Мана", "Увеличить максимум маны и пополнить запас силы.", BLUE),
            ("3. Сила", "Повысить урон ближней и усиленной атаки.", (208, 126, 74)),
        ]
        total_width = 1128
        start_x = WINDOW_WIDTH // 2 - total_width // 2
        for index, (title, body, accent) in enumerate(cards):
            rect = pygame.Rect(start_x + index * 384, 360, 360, 250)
            selected = index == self.upgrade_focus
            panel = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (18, 15, 20, 235), panel.get_rect(), border_radius=24)
            pygame.draw.rect(panel, accent if selected else (111, 95, 92), panel.get_rect(), 3, border_radius=24)
            self.screen.blit(panel, rect)
            draw_centered_text(self.screen, self.menu_font, title, TEXT, (rect.centerx, rect.y + 60), shadow=False)
            for line_index, line in enumerate(wrap_text(self.small_font, body, 280)):
                text = self.small_font.render(line, True, (222, 214, 208))
                self.screen.blit(text, text.get_rect(center=(rect.centerx, rect.y + 138 + line_index * 28)))
        hint = self.small_font.render("Выбери одно усиление. Остальные печати погаснут.", True, SUBTLE)
        self.screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 110)))

    # отрисовывает концовку выбор
    def draw_ending_choice(self):
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        self.screen.blit(dim, (0, 0))
        draw_centered_text(self.screen, self.title_font, "Последнее Решение", TEXT, (WINDOW_WIDTH // 2, 160))
        cards = [
            ("1. Добить", "Оборвать жизнь брата и захлопнуть историю силой.", RED),
            ("2. Оставить в живых", "Разорвать круг мести и попробовать спасти остаток семьи.", GREEN),
        ]
        start_x = WINDOW_WIDTH // 2 - 372
        for index, (title, body, accent) in enumerate(cards):
            rect = pygame.Rect(start_x + index * 384, 360, 360, 270)
            selected = index == self.ending_focus
            panel = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (18, 15, 20, 235), panel.get_rect(), border_radius=24)
            pygame.draw.rect(panel, accent if selected else (111, 95, 92), panel.get_rect(), 3, border_radius=24)
            self.screen.blit(panel, rect)
            draw_centered_text(self.screen, self.menu_font, title, TEXT, (rect.centerx, rect.y + 72), shadow=False)
            for line_index, line in enumerate(wrap_text(self.small_font, body, 286)):
                text = self.small_font.render(line, True, (222, 214, 208))
                self.screen.blit(text, text.get_rect(center=(rect.centerx, rect.y + 156 + line_index * 28)))

    # отрисовывает gameplay
    def draw_gameplay(self):
        self.draw_world()
        for attack in self.player_arcs:
            attack.draw(self.screen, self.camera)
        for projectile in self.player_projectiles:
            projectile.draw(self.screen, self.camera)
        for beam in self.player_beams:
            beam.draw(self.screen, self.camera)
        for projectile in self.enemy_projectiles:
            projectile.draw(self.screen, self.camera)
        for beam in self.enemy_beams:
            beam.draw(self.screen, self.camera)
        for zone in self.enemy_zones:
            zone.draw(self.screen, self.camera)
        for sweep in self.enemy_sweeps:
            sweep.draw(self.screen, self.camera)
        for ring in self.enemy_rings:
            ring.draw(self.screen, self.camera)
        for orb in self.gravity_orbs:
            orb.draw(self.screen, self.camera)
        for pickup in self.pickups:
            self.draw_pickup(pickup)

        entities = []
        if self.master and self.chapter == "assault":
            entities.append(self.master)
        entities.extend(self.dummies)
        entities.extend(self.crystals)
        entities.extend(self.enemies)
        entities.extend(self.town_npcs)
        if self.brother:
            entities.append(self.brother)
        entities.append(self.player)
        entities = [entity for entity in entities if entity]

        for entity in sorted(entities, key=lambda actor: actor.pos.y):
            entity.draw(self.screen, self.camera)
            if entity.name:
                pos = self.camera.apply(entity.pos)
                label = self.small_font.render(entity.name, True, TEXT)
                self.screen.blit(label, label.get_rect(center=(pos.x, pos.y - entity.radius - 26)))

        self.draw_world_overlay()

        for floater in self.floaters:
            self.draw_floater(floater)

        if self.dragon:
            self.draw_dragon_overlay()
        for effect in self.relic_effects:
            effect.draw(self.screen)

        self.draw_hud()
        self.draw_boss_bar()
        if self.stats_overlay:
            self.draw_stats_overlay()

    # отрисовывает дракона оверлей
    def draw_dragon_overlay(self):
        dragon = self.dragon
        if not dragon:
            return

        center_x = WINDOW_WIDTH // 2
        base_y = 144
        angry = dragon.mode in {"bullet", "beam_prepare", "beam"}
        head = self.sprite_bank.get("dragon_angry_face" if angry else "dragon_face")
        if head is not None and dragon.mode not in {"tail_windup", "tail_sweep"}:
            head_y = base_y
            if dragon.mode == "stunned":
                head = head.copy()
                head.fill((54, 54, 66, 128), special_flags=pygame.BLEND_RGBA_SUB)
            head_rect = head.get_rect(center=(center_x, head_y))
            self.screen.blit(head, head_rect)
        elif head is not None and dragon.mode == "tail_windup":
            progress = smoothstep(0.0, 1.0, 1.0 - clamp(dragon.tail_state_timer / 3.0, 0.0, 1.0))
            head_y = int(lerp(base_y, -220, progress))
            head_rect = head.get_rect(center=(center_x, head_y))
            if head_rect.bottom > -20:
                self.screen.blit(head, head_rect)

        if dragon.mode == "tail_sweep":
            return

        if dragon.shield > 0 and dragon.eyes_glowing:
            for eye in self.dragon_eye_centers():
                outer = pygame.Surface((92, 92), pygame.SRCALPHA)
                pygame.draw.circle(outer, (255, 236, 182, 46), (46, 46), 28)
                self.screen.blit(outer, outer.get_rect(center=(int(eye.x), int(eye.y))))
                pygame.draw.circle(self.screen, (255, 246, 214), (int(eye.x), int(eye.y)), 22, 3)
                pygame.draw.circle(self.screen, (255, 210, 138), (int(eye.x), int(eye.y)), 12, 2)

    # отрисовывает тайл layer group
    def draw_tile_layer_group(self, layers, start_tx, end_tx, start_ty, end_ty, clip_rect=None):
        for layer in layers:
            opacity = float(layer.opacity)
            for tx, ty, tile in layer.iter_tiles(self.map_gid_surfaces, start_tx, end_tx, start_ty, end_ty):
                draw_pos = self.camera.apply((tx * TILE_SIZE, ty * TILE_SIZE))
                draw_rect = pygame.Rect(int(draw_pos[0]), int(draw_pos[1]), tile.get_width(), tile.get_height())
                dest_pos = draw_rect.topleft
                area_rect = None
                if clip_rect is not None:
                    visible = draw_rect.clip(clip_rect)
                    if visible.width <= 0 or visible.height <= 0:
                        continue
                    area_rect = pygame.Rect(visible.x - draw_rect.x, visible.y - draw_rect.y, visible.width, visible.height)
                    dest_pos = visible.topleft
                if opacity >= 0.99:
                    self.screen.blit(tile, dest_pos, area_rect)
                else:
                    faded = tile.copy()
                    faded.set_alpha(int(255 * clamp(opacity, 0.0, 1.0)))
                    self.screen.blit(faded, dest_pos, area_rect)

    # отрисовывает мир
    def draw_world(self):
        start_tx = max(0, int(self.camera.x // TILE_SIZE) - 1)
        end_tx = min(self.world_tiles[0], int((self.camera.x + WINDOW_WIDTH) // TILE_SIZE) + 2)
        start_ty = max(0, int(self.camera.y // TILE_SIZE) - 1)
        end_ty = min(self.world_tiles[1], int((self.camera.y + WINDOW_HEIGHT) // TILE_SIZE) + 2)
        if self.chapter == "dragon":
            self.screen.fill((8, 5, 7))
        if self.chapter in ("assault", "dragon", "tunnel", "brother") and self.map_base_layers and self.map_gid_surfaces:
            self.draw_tile_layer_group(self.map_base_layers, start_tx, end_tx, start_ty, end_ty)
            for spike in self.rock_spikes:
                spike.draw(self.screen, self.camera)
            return

        if self.chapter == "assault" and self.ground_tiles:
            fallback = self.tile_bank.get("grass_0")
            for ty in range(start_ty, end_ty):
                for tx in range(start_tx, end_tx):
                    draw_pos = self.camera.apply((tx * TILE_SIZE, ty * TILE_SIZE))
                    ground_key = self.ground_tiles[ty][tx]
                    ground = self.tile_bank.get(ground_key, fallback)
                    self.screen.blit(ground, draw_pos)
                    detail_key = self.detail_tiles[ty][tx] if self.detail_tiles else None
                    if detail_key:
                        detail = self.tile_bank.get(detail_key)
                        if detail:
                            self.screen.blit(detail, draw_pos)
            for spike in self.rock_spikes:
                spike.draw(self.screen, self.camera)
            return

        for ty in range(start_ty, end_ty):
            for tx in range(start_tx, end_tx):
                rect = pygame.Rect(*self.camera.apply((tx * TILE_SIZE, ty * TILE_SIZE)), TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(self.screen, self.tile_color(tx, ty), rect)
                pygame.draw.rect(self.screen, (26, 21, 24), rect, 1)

        for deco_type, position in self.decor:
            screen_pos = self.camera.apply(position)
            if deco_type == "brazer":
                pygame.draw.circle(self.screen, (77, 48, 30), screen_pos, 18)
                pygame.draw.circle(self.screen, (230, 160, 74), screen_pos, 11)
                pygame.draw.circle(self.screen, (255, 223, 155), (screen_pos.x, screen_pos.y - 4), 6)
            elif deco_type == "embers":
                for index in range(6):
                    offset = pygame.Vector2(math.sin(index) * 14, math.cos(index * 1.7) * 9)
                    pygame.draw.circle(self.screen, (255, 128, 61), screen_pos + offset, 3)
            elif deco_type == "bones":
                pygame.draw.line(self.screen, (202, 193, 181), screen_pos + (-18, 0), screen_pos + (18, 0), 5)
                pygame.draw.line(self.screen, (202, 193, 181), screen_pos + (0, -18), screen_pos + (0, 18), 5)
            elif deco_type == "ash":
                pygame.draw.circle(self.screen, (114, 106, 98), screen_pos, 26)

        for wall in self.walls:
            rect = pygame.Rect(*self.camera.apply((wall.x, wall.y)), wall.width, wall.height)
            pygame.draw.rect(self.screen, (51, 43, 48), rect, border_radius=10)
            pygame.draw.rect(self.screen, (74, 63, 69), rect, 2, border_radius=10)
        for spike in self.rock_spikes:
            spike.draw(self.screen, self.camera)

    # отрисовывает мир оверлей
    def draw_world_overlay(self):
        start_tx = max(0, int(self.camera.x // TILE_SIZE) - 1)
        end_tx = min(self.world_tiles[0], int((self.camera.x + WINDOW_WIDTH) // TILE_SIZE) + 2)
        start_ty = max(0, int(self.camera.y // TILE_SIZE) - 1)
        end_ty = min(self.world_tiles[1], int((self.camera.y + WINDOW_HEIGHT) // TILE_SIZE) + 2)
        if self.chapter in ("assault", "dragon", "tunnel", "brother") and self.map_overlay_layers and self.map_gid_surfaces:
            self.draw_tile_layer_group(self.map_overlay_layers, start_tx, end_tx, start_ty, end_ty)
            return
        if self.chapter == "assault" and self.overlay_tiles:
            for ty in range(start_ty, end_ty):
                for tx in range(start_tx, end_tx):
                    overlay_key = self.overlay_tiles[ty][tx]
                    if not overlay_key:
                        continue
                    overlay = self.tile_bank.get(overlay_key)
                    if overlay:
                        self.screen.blit(overlay, self.camera.apply((tx * TILE_SIZE, ty * TILE_SIZE)))

    # отрисовывает предмет
    def draw_pickup(self, pickup):
        pos = self.camera.apply(pickup.pos)
        if pickup.kind == "dragon_relic":
            image = self.sprite_bank.get("pickup_artefact")
            if image is not None:
                pulse = 0.5 + 0.5 * math.sin(pickup.pulse)
                glow = pygame.Surface((96, 96), pygame.SRCALPHA)
                pygame.draw.circle(glow, (246, 232, 180, int(44 + pulse * 38)), (48, 48), 24)
                self.screen.blit(glow, glow.get_rect(center=(int(pos.x), int(pos.y))))
                self.screen.blit(image, image.get_rect(center=(int(pos.x), int(pos.y))))
                return
            pulse = 0.5 + 0.5 * math.sin(pickup.pulse)
            glow = pygame.Surface((94, 94), pygame.SRCALPHA)
            pygame.draw.circle(glow, (246, 232, 180, int(48 + pulse * 42)), (47, 47), 28)
            self.screen.blit(glow, glow.get_rect(center=(int(pos.x), int(pos.y))))
            points = [
                (pos.x, pos.y - 20),
                (pos.x + 18, pos.y - 4),
                (pos.x + 10, pos.y + 20),
                (pos.x - 10, pos.y + 20),
                (pos.x - 18, pos.y - 4),
            ]
            pygame.draw.polygon(self.screen, (234, 224, 198), points)
            pygame.draw.polygon(self.screen, (20, 20, 22), points, 2)
            pygame.draw.circle(self.screen, (255, 176, 92), (int(pos.x), int(pos.y + 2)), 6)
            return
        heal_image = self.sprite_bank.get("pickup_heal")
        if heal_image is not None:
            self.screen.blit(heal_image, heal_image.get_rect(center=(int(pos.x), int(pos.y))))
            return
        pygame.draw.circle(self.screen, (230, 233, 225), pos, 16)
        pygame.draw.rect(self.screen, (184, 54, 58), (pos.x - 5, pos.y - 10, 10, 20), border_radius=2)
        pygame.draw.rect(self.screen, (184, 54, 58), (pos.x - 10, pos.y - 5, 20, 10), border_radius=2)

    # отрисовывает floater
    def draw_floater(self, floater):
        alpha = int(255 * clamp(floater.ttl / 0.8, 0.0, 1.0))
        image = self.small_font.render(floater.text, True, floater.color)
        image.set_alpha(alpha)
        pos = self.camera.apply(floater.pos)
        self.screen.blit(image, image.get_rect(center=(pos.x, pos.y)))

    # отрисовывает hud
    def draw_hud(self):
        panel_height = 142 if not (self.chapter == "dragon" and self.dragon_relic_armed) else 114
        panel_rect = pygame.Rect(20, 18, 612, panel_height)
        draw_pixel_panel(self.screen, panel_rect, fill=(10, 10, 12), border=(190, 182, 165), padding=4)

        hp_ratio = self.player_hp_display / max(1, self.player.max_hp)
        self.draw_bar((44, 44), 320, 26, hp_ratio, (176, 40, 40), "HP", int(self.player.hp))
        if not (self.chapter == "dragon" and self.dragon_relic_armed):
            mana_ratio = self.player_mana_display / max(1, self.player.max_mana)
            self.draw_bar((44, 82), 320, 22, mana_ratio, (238, 238, 242), "MP", int(self.player.mana))
        else:
            relic_rect = pygame.Rect(44, 82, 320, 22)
            draw_pixel_bar(
                self.screen,
                relic_rect,
                1.0,
                (220, 186, 106),
                border=(236, 236, 240),
                track=(48, 48, 52),
            )
            label_text = self.hud_font.render("ПЕЧАТЬ", False, TEXT)
            self.screen.blit(label_text, (relic_rect.x + 4, relic_rect.y - 18))
        caste_name = "СВЕТ" if self.player.caste == "light" else "ТЬМА"
        caste_color = GOLD if self.player.caste == "light" else VIOLET
        caste_text = self.small_font.render(f"КАСТА: {caste_name}", False, caste_color)
        self.screen.blit(caste_text, (392, 42))
        stats = self.small_font.render(
            f"ATK {self.player.attack_power}   УКЛ {self.player.dash_charges}/2",
            False,
            (214, 206, 199),
        )
        self.screen.blit(stats, (392, 78))
        chapter = self.small_font.render(self.chapter_name().upper(), False, (214, 206, 199))
        self.screen.blit(chapter, (392, 112))

    # отрисовывает bar
    def draw_bar(self, pos, width, height, ratio, color, label, value):
        back = pygame.Rect(pos[0], pos[1], width, height)
        draw_pixel_bar(self.screen, back, ratio, color, border=(188, 181, 162), track=(58, 58, 64))
        label_text = self.hud_font.render(f"{label} {value}", False, TEXT)
        self.screen.blit(label_text, (pos[0] + 4, pos[1] - 18))

    # выполняет chapter name
    def chapter_name(self):
        return {
            "tutorial": "Обучение",
            "assault": "Пепельная Опушка",
            "dragon": "Логово Дракона",
            "tunnel": "Горящий Лес",
            "brother": "Сердце Разлома",
        }.get(self.chapter, "")

    # выполняет текущий objective
    def current_objective(self):
        if self.chapter == "assault":
            speaker = self.master.name if self.master else "Житель"
            if not self.assault_started:
                return speaker, "Перейди мост и зайди в зону тревоги, чтобы началась первая волна."
            if self.enemies:
                return speaker, f"Очисти опушку от тварей. Волна {min(self.assault_wave_index, len(self.assault_waves))}/{len(self.assault_waves)}."
            if self.assault_ready_to_advance:
                return speaker, "Путь к дракону открыт. Иди по тропе дальше."
            return speaker, "Лес шевелится. Следующая волна уже собирается."
        if self.chapter == "dragon":
            return "Инстинкт", "Ломай щит через глаза и переживи луч, землю и шквал."
        if self.chapter == "tunnel":
            return "Инстинкт", "Держись светлой тропы и не заходи в огонь."
        if self.chapter == "brother":
            return "Разлом", "Переживи световой луч, тёмный удар и сферу притяжения."
        return "", ""

    # отрисовывает objective
    def draw_objective(self):
        speaker, objective = self.current_objective()
        if not objective:
            return
        box = pygame.Surface((820, 108), pygame.SRCALPHA)
        pygame.draw.rect(box, (12, 13, 17, 190), box.get_rect(), border_radius=22)
        pygame.draw.rect(box, (86, 73, 66), box.get_rect(), 2, border_radius=22)
        self.screen.blit(box, (WINDOW_WIDTH - 860, 18))
        name = self.small_font.render(speaker, True, (226, 210, 184))
        self.screen.blit(name, (WINDOW_WIDTH - 830, 36))
        for index, line in enumerate(wrap_text(self.small_font, objective, 750)):
            text = self.small_font.render(line, True, TEXT)
            self.screen.blit(text, (WINDOW_WIDTH - 830, 64 + index * 24))

    # отрисовывает босса bar
    def draw_boss_bar(self):
        boss = None
        name = ""
        if self.dragon:
            boss = self.dragon
            name = "ПЕПЕЛЬНЫЙ ДРАКОН"
        elif self.brother:
            boss = self.brother
            name = "БРАТ РАЗЛОМА"
        if not boss:
            return
        panel_rect = pygame.Rect(WINDOW_WIDTH // 2 - 390, 18, 780, 86 if self.dragon else 64)
        draw_pixel_panel(self.screen, panel_rect, fill=(10, 10, 12), border=(190, 182, 165), padding=4)
        ratio = boss.hp / max(1, boss.max_hp)
        back = pygame.Rect(WINDOW_WIDTH // 2 - 340, 48, 680, 18)
        draw_pixel_bar(self.screen, back, ratio, (182, 63, 62), border=(188, 181, 162), track=(54, 24, 24))
        label = self.boss_font.render(name, False, TEXT)
        self.screen.blit(label, label.get_rect(center=(WINDOW_WIDTH // 2, 32)))
        if self.dragon:
            shield_label = self.small_font.render("ЩИТ", False, (226, 210, 184))
            self.screen.blit(shield_label, (WINDOW_WIDTH // 2 - 338, 72))
            for index in range(4):
                rect = pygame.Rect(WINDOW_WIDTH // 2 - 274 + index * 32, 70, 22, 12)
                active = index < self.dragon.shield
                draw_pixel_bar(
                    self.screen,
                    rect,
                    1.0 if active else 0.0,
                    (216, 198, 112),
                    border=(188, 181, 162),
                    track=(42, 42, 46),
                )
            if self.dragon.mode == "stunned":
                stun_text = self.small_font.render(
                    f"ОГЛУШЕН {int(math.ceil(self.dragon.stun_timer))}",
                    False,
                    (236, 236, 244),
                )
                self.screen.blit(stun_text, (WINDOW_WIDTH // 2 + 54, 70))

    # выполняет stats оверлей rect
    def stats_overlay_rect(self):
        return pygame.Rect(WINDOW_WIDTH // 2 - 560, WINDOW_HEIGHT // 2 - 290, 1120, 580)

    # выполняет stats оверлей button rects
    def stats_overlay_button_rects(self):
        panel = self.stats_overlay_rect()
        button_w = 220
        button_h = 54
        gap = 28
        total_w = button_w * 2 + gap
        start_x = panel.centerx - total_w // 2
        y = panel.bottom - 92
        return {
            "settings": pygame.Rect(start_x, y, button_w, button_h),
            "menu": pygame.Rect(start_x + button_w + gap, y, button_w, button_h),
        }

    # выполняет stats оверлей action at
    def stats_overlay_action_at(self, pos):
        for action, rect in self.stats_overlay_button_rects().items():
            if rect.collidepoint(pos):
                return action
        return None

    # отрисовывает stats оверлей
    def draw_stats_overlay(self):
        panel = self.stats_overlay_rect()
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 144))
        self.screen.blit(overlay, (0, 0))
        draw_pixel_panel(self.screen, panel, fill=(14, 14, 18), border=(130, 112, 102), padding=4)
        title_y = panel.y + 48
        draw_centered_text(self.screen, self.title_font, "Свод Героя", TEXT, (panel.centerx, title_y), shadow=False)

        left_x = panel.x + 100
        value_x = panel.x + 350
        right_x = panel.x + 660
        row_y = panel.y + 150
        line_gap = 62
        value_color = GOLD if self.player.caste == "light" else VIOLET

        rows = [
            ("Каста", "Свет" if self.player.caste == "light" else "Тьма"),
            ("Глава", self.chapter_name()),
            ("HP", f"{int(self.player.hp)} / {self.player.max_hp}"),
            ("Мана", f"{int(self.player.mana)} / {self.player.max_mana}"),
            ("Рывки", f"{self.player.dash_charges} / 2"),
        ]
        for index, (label, value) in enumerate(rows):
            y = row_y + index * line_gap
            label_surface = self.menu_font.render(label, False, (220, 214, 206))
            value_surface = self.menu_font.render(value, False, value_color if index == 0 else TEXT)
            self.screen.blit(label_surface, (left_x, y))
            self.screen.blit(value_surface, (value_x, y))

        hints = [
            "ЛКМ: ближняя атака",
            "ПКМ: усиленная атака",
            "Shift: два рывка подряд",
            "E или Esc: закрыть паузу",
        ]
        hint_font = self.small_font
        for index, line in enumerate(hints):
            text = hint_font.render(line, False, TEXT)
            self.screen.blit(text, (right_x, row_y + 18 + index * 52))

        for action, rect in self.stats_overlay_button_rects().items():
            hovered = self.stats_overlay_action_at(self.current_mouse_pos()) == action
            border = (236, 236, 244) if hovered else (188, 181, 162)
            fill = (24, 24, 30)
            draw_pixel_panel(self.screen, rect, fill=fill, border=border, padding=3)
            label = "Настройки" if action == "settings" else "В меню"
            text = self.menu_font.render(label, False, TEXT)
            self.screen.blit(text, text.get_rect(center=rect.center))

    # отрисовывает сообщение
    def draw_toast(self):
        lines = wrap_text(self.small_font, self.toast, 380)
        width = 420
        height = 34 + len(lines) * 24
        rect = pygame.Rect(WINDOW_WIDTH - width - 28, WINDOW_HEIGHT - height - 28, width, height)
        draw_pixel_panel(self.screen, rect, fill=(236, 232, 222), border=(24, 24, 26), padding=4)
        inner = rect.inflate(-12, -12)
        pygame.draw.rect(self.screen, (255, 255, 255), inner)
        pygame.draw.rect(self.screen, (0, 0, 0), inner, 2)
        for index, line in enumerate(lines):
            surf = self.small_font.render(line, False, (24, 24, 26))
            self.screen.blit(surf, (inner.x + 12, inner.y + 10 + index * 22))

    # отрисовывает волну баннер
    def draw_wave_banner(self):
        alpha = clamp(self.wave_banner_timer / 2.1, 0.0, 1.0)
        title = self.title_font.render(self.wave_banner_title, True, (190, 38, 38))
        title.set_alpha(int(255 * alpha))
        self.screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 124)))
        if self.wave_banner_subtitle:
            subtitle = self.small_font.render(self.wave_banner_subtitle, False, (236, 226, 216))
            subtitle.set_alpha(int(255 * alpha))
            self.screen.blit(subtitle, subtitle.get_rect(center=(WINDOW_WIDTH // 2, 174)))

    # отрисовывает туннель
    def draw_tunnel(self):
        self.screen.fill((6, 7, 10))
        path_glow = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        path_fill = (116, 146, 154)
        path_core = (184, 204, 210)
        path_outline = (28, 32, 38)
        for rect in self.tunnel_rects:
            glow_rect = rect.inflate(18, 18)
            pygame.draw.rect(path_glow, (170, 194, 202, 26), glow_rect)
            pygame.draw.rect(self.screen, path_fill, rect)
            inner = rect.inflate(-18, -18)
            if inner.width > 0 and inner.height > 0:
                pygame.draw.rect(self.screen, path_core, inner)
                center_line = inner.inflate(-max(20, inner.width // 3), -max(20, inner.height // 3))
                if center_line.width > 0 and center_line.height > 0:
                    pygame.draw.rect(self.screen, (228, 236, 238), center_line)
            pygame.draw.rect(self.screen, path_outline, rect, 6)
        self.screen.blit(path_glow, (0, 0))
        start_rect = self.tunnel_rects[0].inflate(-34, -34)
        goal_rect = self.tunnel_rects[-1].inflate(-34, -34)
        pygame.draw.rect(self.screen, (98, 136, 102), start_rect)
        pygame.draw.rect(self.screen, (212, 226, 214), start_rect, 4)
        pygame.draw.rect(self.screen, (98, 136, 102), goal_rect)
        pygame.draw.rect(self.screen, (212, 226, 214), goal_rect, 4)
        pygame.draw.circle(self.screen, (212, 226, 214), self.tunnel_goal, 18, 3)
        pygame.draw.circle(self.screen, (98, 136, 102), self.tunnel_goal, 7)
        hero_frames = self.sprite_bank["hero_light" if self.player.caste == "light" else "hero_dark"]
        hero = hero_frames[int(pygame.time.get_ticks() / 150) % len(hero_frames)]
        hero = pygame.transform.smoothscale(hero, (44, 44))
        self.screen.blit(hero, hero.get_rect(center=self.tunnel_player))
        draw_centered_text(self.screen, self.title_font, "Горящий Лес", TEXT, (WINDOW_WIDTH // 2, 96))
        for index, line in enumerate(wrap_text(self.body_font, self.tunnel_message, 1400)):
            hint = self.body_font.render(line, True, TEXT)
            self.screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, 150 + index * 34)))

    # отрисовывает туннель flames
    def draw_tunnel_flames(self):
        for index in range(len(self.tunnel_points) - 1):
            start = pygame.Vector2(self.tunnel_points[index])
            end = pygame.Vector2(self.tunnel_points[index + 1])
            direction = end - start
            if direction.length_squared() == 0:
                continue
            direction = direction.normalize()
            normal = pygame.Vector2(-direction.y, direction.x)
            width = self.tunnel_widths[index] if index < len(self.tunnel_widths) else 120
            for step in range(0, int(start.distance_to(end)), 34):
                point = start + direction * step
                left = point + normal * (width * 0.6)
                right = point - normal * (width * 0.6)
                flame_height = 18 + (step + index * 17) % 24
                pygame.draw.polygon(
                    self.screen,
                    (255, 101, 45),
                    [(left.x, left.y), (left.x - 9, left.y + flame_height), (left.x + 9, left.y + flame_height)],
                )
                pygame.draw.polygon(
                    self.screen,
                    (255, 140, 62),
                    [(right.x, right.y), (right.x - 9, right.y + flame_height), (right.x + 9, right.y + flame_height)],
                )

    # отрисовывает смерть оверлей
    def draw_death_overlay(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(190 + self.defeat_flash * 40)))
        self.screen.blit(overlay, (0, 0))
        draw_centered_text(self.screen, self.title_font, "Ты Пал", (255, 223, 223), (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 60))
        hint = self.body_font.render("Enter — загрузить последнее сохранение, Esc — меню", True, TEXT)
        self.screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30)))
