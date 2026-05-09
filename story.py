from core import *


# описывает класс story mixin
class StoryMixin:
    # открывает сюжет
    def open_story(self, pages, callback=None, ending=False, intro_mode=None):
        self.story_pages = pages
        self.story_index = 0
        self.story_callback = callback
        self.story_is_ending = ending
        self.story_transition = None
        self.story_choice_mode = False
        self.story_choice_index = 0
        self.story_hover_choice = None
        self.story_intro_mode = intro_mode
        self.story_intro_timer = 0.0
        self.reset_story_page_state()
        self.scene = "story"

    # выполняет текущий сюжет страницу
    def current_story_page(self):
        if not self.story_pages:
            return None
        return self.story_pages[min(self.story_index, len(self.story_pages) - 1)]

    # сбрасывает сюжет страницу состояние
    def reset_story_page_state(self):
        self.story_text_progress = 0.0
        self.story_prompt_timer = 0.0
        self.story_choice_mode = False
        self.story_choice_index = 0
        self.story_hover_choice = None

    # выполняет текущий сюжет текст
    def current_story_text(self):
        page = self.current_story_page()
        if not page:
            return ""
        return page.get("text", "")

    # выполняет сюжет текст is complete
    def story_text_is_complete(self):
        return self.story_text_progress >= len(self.current_story_text())

    # выполняет reveal сюжет текст
    def reveal_story_text(self):
        self.story_text_progress = float(len(self.current_story_text()))
        self.story_prompt_timer = 0.0

    # выполняет сюжет hint ready
    def story_hint_ready(self):
        return self.story_text_is_complete()

    # выполняет сюжет переход duration
    def story_transition_duration(self, kind):
        return {
            "white_flash": 1.0,
            "crossfade": 1.1,
            "dark_slide": 1.4,
            "fade": 0.8,
        }.get(kind, 0.8)

    # запускает сюжет переход
    def start_story_transition(self, kind, next_index):
        if kind == "white_flash":
            self.audio.play("Grom", 0.6)
        self.story_transition = {
            "type": kind,
            "timer": 0.0,
            "duration": self.story_transition_duration(kind),
            "from_index": self.story_index,
            "to_index": next_index,
        }

    # завершает сюжет
    def finish_story(self):
        callback = self.story_callback
        self.story_pages = []
        self.story_index = 0
        self.story_callback = None
        self.story_is_ending = False
        self.story_transition = None
        self.story_intro_mode = None
        self.story_intro_timer = 0.0
        self.story_choice_mode = False
        self.story_hover_choice = None
        if callback:
            callback()

    # обновляет сюжет
    def update_story(self, dt):
        if self.story_intro_mode:
            self.story_intro_timer += dt
            if self.story_intro_timer >= 1.15:
                self.story_intro_mode = None
                self.story_intro_timer = 0.0
            return

        if self.story_transition:
            self.story_transition["timer"] += dt
            if self.story_transition["timer"] >= self.story_transition["duration"]:
                self.story_index = self.story_transition["to_index"]
                self.story_transition = None
                self.reset_story_page_state()
            return

        if self.story_choice_mode:
            return

        text = self.current_story_text()
        if self.story_text_progress < len(text):
            chars_per_second = self.current_story_page().get("chars_per_second", 45)
            self.story_text_progress = min(len(text), self.story_text_progress + dt * chars_per_second)
            if self.story_text_is_complete():
                self.story_prompt_timer = 0.0
            return
        self.story_prompt_timer += dt

    # продвигает сюжет
    def advance_story(self):
        if self.story_intro_mode or self.story_transition:
            return
        page = self.current_story_page()
        if not page:
            return
        if self.story_choice_mode and page.get("choices"):
            self.choose_story_option(self.story_choice_index)
            return
        if not self.story_text_is_complete():
            self.reveal_story_text()
            return
        if not self.story_hint_ready():
            return
        if page.get("choices"):
            self.story_choice_mode = True
            self.story_hover_choice = None
            return
        next_index = self.story_index + 1
        if next_index >= len(self.story_pages):
            self.finish_story()
            return
        self.start_story_transition(page.get("transition", "fade"), next_index)

    # выбирает сюжет option
    def choose_story_option(self, index):
        page = self.current_story_page()
        if not page or not page.get("choices"):
            return
        choice = page["choices"][index]
        route = choice.get("route")
        if route:
            self.begin_route_story(route)
            return
        callback = choice.get("callback")
        if callable(callback):
            callback()

    # собирает prologue pages
    def build_prologue_pages(self):
        return [
            {
                "image": "1",
                "text": "Когда-то давно было место, тихое и спокойное. Стабильность там была верным гарантом безмятежного будущего. Казалось бы, это могло длиться вечно.",
                "transition": "white_flash",
            },
            {
                "image": "2",
                "text": "Но судьба часто играет злую шутку. Что-то страшное вырвалось в этот мир. То, что никто не мог предсказать. То, к чему никто не мог подготовиться. И то, что превратило недавний рай в сущий ад.",
                "transition": "crossfade",
            },
            {
                "image": "3",
                "text": "Два брата вырвались из пылающего дома в надежде на спасение. Ветер нёс пепел прямо в лицо, а за спиной рушилось всё, что когда-то было домом. Бежать, бежать — и куда подальше от языков пламени — вот всё, что было в их головах.",
                "transition": "dark_slide",
            },
            {
                "image": "4",
                "text": "Пламя уже пожирало крыши, когда братья бросились в сторону темнеющего леса, задыхаясь от дыма и страха. Один из них внезапно споткнулся, рухнул в пыль и закричал, протягивая руку вслед. Но второй, не обернувшись ни на мгновение, лишь ускорил бег, исчезая среди деревьев. Есть ли хоть единый шанс его догнать, или, раз судьба так распорядилась, возможно, стоит помочь таким же лишившимся крова?",
                "choices": [
                    {"text": "Остаться помочь", "route": "light"},
                    {"text": "Попытаться догнать", "route": "dark"},
                ],
            },
        ]

    # выполняет light route pages
    def light_route_pages(self):
        return [
            {
                "image": "5.1",
                "text": "Ты повернул назад и снова вошёл в пламя, будто один шаг мог отменить гибель дома. Ты смело указывал путь к спасению потерявшимся из-за дыма людям, но, не пожалев себя, в конце концов сам надышался ядом и потерял сознание.",
                "transition": "fade",
            },
            {
                "image": "6.1",
                "text": "Когда ты очнулся, уже оказался в странном светлом помещении. Оказывается, маги света пришли на помощь твоей деревне и, соответственно, спасли и тебя. Один мастер заинтересовался тобой и решил направлять тебя в изучении магии света.",
                "transition": "fade",
            },
            {
                "image": "7.1",
                "text": "Прошли годы дисциплины, молитв и ран. Ты просыпаешься уже не тем мальчишкой из леса. Теперь ты смелый рыцарь и защитник людей под знаменем Храма Солнца. Твоя задача — отправлять потусторонних существ обратно в тот мир, где им и место.",
            },
        ]

    # выполняет dark route pages
    def dark_route_pages(self):
        return [
            {
                "image": "5.2",
                "text": "Ты не оглянулся и ушёл глубже в чащу. Лес сомкнулся за спиной, как дверь. Брата нигде не видно и не слышно, будто он испарился. Где бы ты ни бродил, везде были лишь деревья, а выхода не находилось. Какой-то сладковатый запах ударил в нос, и ты, даже не сопротивляясь, провалился в сон.",
                "transition": "fade",
            },
            {
                "image": "6.2",
                "text": "Когда ты очнулся, вокруг был мягкий полумрак, наполненный запахом трав и сырой древесины. Ты лежал в хижине глубоко в лесу, и первой, кого ты увидел, была красивая ведьма с густыми белыми ресницами. Вместо утешений и молитв ты услышал шёпот о силе, что рождается в боли и страхе, и о том, что тьма — не враг, если научиться её понимать. Она решила оставить тебя у себя и направить, видя в тебе не жертву, а нечто большее.",
                "transition": "fade",
            },
            {
                "image": "7.2",
                "text": "Прошли годы, наполненные тайными знаниями, испытаниями и борьбой с самим собой. Ты больше не тот испуганный ребёнок — теперь ты охотник сумрака, идущий по грани между мирами, тот, кто подчиняет тьму и использует её против порождений разломов. Твоя задача — находить потусторонних существ и возвращать их обратно туда, откуда они пришли, сохраняя хрупкое равновесие.",
            },
        ]

    # выполняет begin route сюжет
    def begin_route_story(self, route):
        self.build_player_and_master(route)
        if route == "light":
            self.open_story(self.light_route_pages(), callback=self.prepare_intro_dialogue)
        else:
            self.open_story(self.dark_route_pages(), callback=self.prepare_intro_dialogue)

    # открывает диалог
    def open_dialogue(self, entries, callback=None, backdrop="world"):
        self.dialogue_entries = entries
        self.dialogue_index = 0
        self.dialogue_choice_index = 0
        self.dialogue_callback = callback
        self.dialogue_backdrop = backdrop
        self.dialogue_entry_timer = 0.0
        self.toast = ""
        self.toast_timer = 0.0
        self.wave_banner_timer = 0.0
        self.scene = "dialogue"

    # выполняет текущий диалог entry
    def current_dialogue_entry(self):
        if not self.dialogue_entries:
            return None
        return self.dialogue_entries[min(self.dialogue_index, len(self.dialogue_entries) - 1)]

    # продвигает диалог
    def advance_dialogue(self):
        entry = self.current_dialogue_entry()
        if not entry:
            return
        if entry.get("choices"):
            return
        self.dialogue_index += 1
        self.dialogue_entry_timer = 0.0
        if self.dialogue_index >= len(self.dialogue_entries):
            callback = self.dialogue_callback
            self.dialogue_entries = []
            self.dialogue_index = 0
            self.dialogue_choice_index = 0
            self.dialogue_callback = None
            self.dialogue_backdrop = "world"
            self.dialogue_entry_timer = 0.0
            self.scene = "gameplay"
            if callback:
                callback()

    # выбирает диалог option
    def choose_dialogue_option(self, index):
        entry = self.current_dialogue_entry()
        if not entry or not entry.get("choices"):
            return
        choice = entry["choices"][index]
        hero_entry = {
            "speaker": "Ты",
            "portrait": "hero",
            "left_portrait": entry.get("left_portrait"),
            "right_portrait": entry.get("right_portrait", "hero"),
            "text": choice["text"],
        }
        if "next_entries" in choice:
            self.dialogue_entries = self.dialogue_entries[: self.dialogue_index] + [hero_entry] + choice.get("next_entries", [])
        else:
            followup = choice.get("followup", [])
            self.dialogue_entries = self.dialogue_entries[: self.dialogue_index + 1] + followup + self.dialogue_entries[self.dialogue_index + 1 :]
            self.dialogue_entries[self.dialogue_index] = hero_entry
        self.dialogue_choice_index = 0
        self.advance_dialogue()

    # запускает new game
    def start_new_game(self):
        self.scene = "story"
        self.stats_overlay = False
        self.open_story(self.build_prologue_pages(), intro_mode="menu_pan")

    # применяет касту выбор
    def apply_caste_choice(self, caste, skip_story=False):
        self.stats_overlay = False
        self.build_player_and_master(caste)
        if caste == "light":
            pages = self.light_route_pages()
        else:
            pages = self.dark_route_pages()
        if skip_story:
            self.setup_assault_room(skip_save=True)
        else:
            self.open_story(pages, callback=self.prepare_intro_dialogue)

    # выполняет prepare intro диалог
    def prepare_intro_dialogue(self):
        self.setup_assault_room(skip_save=True)
        if self.player.caste == "light":
            self.open_light_route_dialogue()
        else:
            self.open_dark_route_dialogue()

    # завершает intro диалог
    def finish_intro_dialogue(self):
        spawn = self.assault_spawn_point.copy() if self.assault_spawn_point is not None else pygame.Vector2(8.4 * TILE_SIZE, 9.8 * TILE_SIZE)
        self.player.pos = spawn
        self.master.pos = spawn + pygame.Vector2(74, -42)
        self.camera.update(self.player.pos, self.world_size.x, self.world_size.y)
        self.save_checkpoint("assault")
        self.show_toast("Житель указал путь. Переходи мост, когда будешь готов поднять первую волну.")

    # запускает жителя intro
    def start_resident_intro(self):
        self.scene = "resident_intro"
        self.toast = ""
        self.toast_timer = 0.0
        self.wave_banner_timer = 0.0
        self.stats_overlay = False
        self.resident_intro_phase = 0
        self.resident_intro_timer = 0.0
        spawn = self.assault_spawn_point.copy() if self.assault_spawn_point is not None else pygame.Vector2(8.4 * TILE_SIZE, 9.8 * TILE_SIZE)
        self.player.pos = spawn + pygame.Vector2(-230, 0)
        self.master.pos = spawn + pygame.Vector2(160, -78)
        self.resident_intro_hero_target = spawn
        self.resident_intro_resident_target = spawn + pygame.Vector2(74, -42)
        self.player.facing = pygame.Vector2(1, 0)
        self.player.move_vector = pygame.Vector2(1, 0)
        self.camera.update((self.player.pos + self.master.pos) * 0.5, self.world_size.x, self.world_size.y)

    # завершает жителя intro
    def finish_resident_intro(self):
        self.player.pos = self.resident_intro_hero_target.copy()
        self.master.pos = self.resident_intro_resident_target.copy()
        self.player.tick(0.0, moving=False, move_vector=pygame.Vector2())
        self.master.tick(0.0, moving=False)
        self.open_resident_dialogue()

    # обновляет жителя intro
    def update_resident_intro(self, dt):
        # перемещает actor towards
        def move_actor_towards(actor, target, speed):
            delta = target - actor.pos
            if delta.length_squared() == 0:
                actor.pos = pygame.Vector2(target)
                return True
            distance = speed * dt
            length = delta.length()
            if length <= distance:
                actor.pos = pygame.Vector2(target)
                return True
            actor.pos += delta.normalize() * distance
            return False

        if self.resident_intro_phase == 0:
            finished = move_actor_towards(self.player, self.resident_intro_hero_target, 145.0)
            self.player.tick(dt, moving=True, move_vector=pygame.Vector2(1, 0))
            self.master.tick(dt, moving=False)
            if finished:
                self.resident_intro_phase = 1
                self.resident_intro_timer = 0.0
                self.player.move_vector = pygame.Vector2()
        elif self.resident_intro_phase == 1:
            self.resident_intro_timer += dt
            self.player.tick(dt, moving=False, move_vector=pygame.Vector2())
            self.master.tick(dt, moving=False)
            if self.resident_intro_timer >= 1.0:
                self.resident_intro_phase = 2
                self.resident_intro_timer = 0.0
        elif self.resident_intro_phase == 2:
            finished = move_actor_towards(self.master, self.resident_intro_resident_target, 165.0)
            self.player.tick(dt, moving=False, move_vector=pygame.Vector2())
            self.master.tick(dt, moving=True)
            if finished:
                self.resident_intro_phase = 3
                self.resident_intro_timer = 0.0
        else:
            self.resident_intro_timer += dt
            self.player.tick(dt, moving=False, move_vector=pygame.Vector2())
            self.master.tick(dt, moving=False)
            if self.resident_intro_timer >= 0.65:
                self.finish_resident_intro()
                return

        self.camera.update((self.player.pos + self.master.pos) * 0.5, self.world_size.x, self.world_size.y)

    # открывает light route диалог
    def open_light_route_dialogue(self):
        entries = [
            {
                "speaker": "Мастер",
                "portrait": "master",
                "left_portrait": "master",
                "right_portrait": "hero",
                "text": "Ты слышал последние новости, мальчик мой?",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "master",
                "right_portrait": "hero",
                "text": "В храме всегда есть вести, учитель. Какие из них важны на этот раз?",
            },
            {
                "speaker": "Мастер",
                "portrait": "master",
                "left_portrait": "master",
                "right_portrait": "hero",
                "text": "У руин одной деревни… снова видели дракона.",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "master",
                "right_portrait": "hero",
                "text": "Снова?",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "master",
                "right_portrait": "hero",
                "style": "shiver_letters",
                "style_duration": 2.0,
                "text": "Это тот самый дракон?",
            },
            {
                "speaker": "Мастер",
                "portrait": "master",
                "left_portrait": "master",
                "right_portrait": "hero",
                "text": "Мы не знаем, но свидетели говорят: тень огромная, чешуя тёмная, как уголь после бури. Очень похоже.",
            },
            {
                "speaker": "Мастер",
                "portrait": "master",
                "left_portrait": "master",
                "right_portrait": "hero",
                "text": "Судя по всему, его тянет к разлому. Те руины как раз рядом.",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "master",
                "right_portrait": "hero",
                "text": "Вы отправляете меня?",
            },
            {
                "speaker": "Мастер",
                "portrait": "master",
                "left_portrait": "master",
                "right_portrait": "hero",
                "text": "Верно. Я верю, ты единственный, кто сможет его одолеть... кто сможет вернуть рай в этот мир. Возможно, надежд мало, но своего брата ты сможешь тоже найти. По крайней мере, я за это помолюсь.",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "master",
                "right_portrait": "hero",
                "text": "...",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "master",
                "right_portrait": "hero",
                "text": "Я всё понял. Выдвигаюсь.",
            },
            {
                "speaker": "Мастер",
                "portrait": "master",
                "left_portrait": "master",
                "right_portrait": "hero",
                "text": "Желаю удачи тебе, сын мой. И напомню тебе: свет — это не только сила. Это ещё и выбор.",
            },
        ]
        self.open_dialogue(entries, callback=self.start_resident_intro, backdrop="black")

    # открывает dark route диалог
    def open_dark_route_dialogue(self):
        entries = [
            {
                "speaker": "Ведьма",
                "portrait": "witch",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Ты стал лучше чувствовать тьму. Даже сейчас — скажи, что ты ощущаешь?",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Что-то неспокойное. Как будто лес пытается что-то скрыть.",
            },
            {
                "speaker": "Ведьма",
                "portrait": "witch",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Или предупредить.",
            },
            {
                "speaker": "Ведьма",
                "portrait": "witch",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Лес принёс весть — у руин деревни снова видели дракона.",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "У тех самых руин? Значит, это не слухи.",
            },
            {
                "speaker": "Ведьма",
                "portrait": "witch",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Слишком много теней шевелится там, где давно должно быть тихо.",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "style": "shiver_letters",
                "style_duration": 2.0,
                "text": "Это он? Тот, кто сжёг всё?",
            },
            {
                "speaker": "Ведьма",
                "portrait": "witch",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Возможно. Или нечто, что идёт по его следу. Разломы не забывают такие места.",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Мне не важно, кто это. Если он там — я найду его.",
            },
            {
                "speaker": "Ведьма",
                "portrait": "witch",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Забавно. Слепая ярость делает тебя добычей, а не охотником.",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Я не тот ребёнок, которого ты нашла.",
            },
            {
                "speaker": "Ведьма",
                "portrait": "witch",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Я это знаю. Поэтому и говорю с тобой, а не удерживаю.",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Тогда скажи прямо — ты отправляешь меня?",
            },
            {
                "speaker": "Ведьма",
                "portrait": "witch",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Да.",
            },
            {
                "speaker": "Ведьма",
                "portrait": "witch",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Найди дракона. Узнай, зачем он вернулся.",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Я разберусь.",
            },
            {
                "speaker": "Ведьма",
                "portrait": "witch",
                "left_portrait": "witch",
                "right_portrait": "hero",
                "text": "Иди. И не забывай — тьма слушается только тех, кто контролирует себя.",
            },
        ]
        self.open_dialogue(entries, callback=self.start_resident_intro, backdrop="black")

    # открывает жителя диалог
    def open_resident_dialogue(self):
        resident_lines = [
            {
                "speaker": "",
                "portrait": "gonec",
                "left_portrait": "gonec",
                "right_portrait": "hero",
                "text": "Там, за мостом! Кое-как сбежал, ей-богу!",
            },
            {
                "speaker": "",
                "portrait": "gonec",
                "left_portrait": "gonec",
                "right_portrait": "hero",
                "text": "Прошу, умоляю тебя.... сразу видно, ты сильный парень.",
            },
            {
                "speaker": "",
                "portrait": "gonec",
                "left_portrait": "gonec",
                "right_portrait": "hero",
                "text": "Избавь мой дом от этих тварей!!!!",
            },
        ]
        entries = [
            {
                "speaker": "",
                "portrait": "gonec",
                "left_portrait": "gonec",
                "right_portrait": "hero",
                "text": "Господь меня услышал!!!! БОЖЕ СПАСИБО! Наконец-то хоть кто-то пришёл спасти нас!!!",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "gonec",
                "right_portrait": "hero",
                "text": "В чём дело?",
            },
            {
                "speaker": "",
                "portrait": "gonec",
                "left_portrait": "gonec",
                "right_portrait": "hero",
                "text": "Трупы восстали из мёртвых!!! Я кое-как растил капусту во дворе, а эти гниляки.....",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "gonec",
                "right_portrait": "hero",
                "text": "...",
            },
            {
                "speaker": "Ты",
                "portrait": "hero",
                "left_portrait": "gonec",
                "right_portrait": "hero",
                "choices": [
                    {
                        "text": "Где они?",
                        "next_entries": resident_lines,
                    },
                    {
                        "text": "Я устал это слушать...",
                        "next_entries": [],
                    },
                ],
            },
        ]
        self.open_dialogue(entries, callback=self.finish_intro_dialogue, backdrop="world")

    # открывает усиление выбор
    def open_upgrade_choice(self):
        self.scene = "upgrade"
        self.upgrade_focus = 0

    # применяет усиление
    def apply_upgrade(self, choice):
        if choice == "health":
            self.player.max_hp += 40
            self.player.hp = min(self.player.max_hp, self.player.hp + 40)
            self.show_toast("Печать крови усилила твою стойкость.")
        elif choice == "mana":
            self.player.max_mana += 50
            self.player.mana = min(self.player.max_mana, self.player.mana + 50)
            self.show_toast("Печать бездны расширила запас маны.")
        else:
            self.player.attack_power += 8
            self.show_toast("Печать клинка наполнила удары новой силой.")
        self.setup_tunnel()

    # открывает концовку выбор
    def open_ending_choice(self):
        self.scene = "ending_choice"
        self.ending_focus = 0

    # завершает game
    def finish_game(self, choice):
        if choice == "kill":
            ending_pages = [
                {
                    "image": "12.1",
                    "title": "Концовка I: Пепельный Наследник",
                    "text": "Ты добиваешь брата, и две сферы гаснут у него в ладонях. Разлом захлопывается рывком, будто кто-то закрыл бездну ценой последней крови этой семьи.",
                },
                {
                    "image": "13.1",
                    "title": "Эпилог",
                    "text": "Деревня получает шанс возродиться, но для тебя огонь так и не заканчивается. Люди называют тебя спасителем, а лес отвечает другим именем: тем, кто пережил Разлом, но уже никогда не вернулся домой.",
                },
            ]
        else:
            ending_pages = [
                {
                    "image": "12.2",
                    "title": "Концовка II: Два Стража",
                    "text": "Ты опускаешь оружие и не даёшь ненависти завершить путь за тебя. Брат падает на колени, а Свет и Тьма впервые не рвут друг друга, а сплетаются в печать, затягивающую Разлом без новой смерти.",
                },
                {
                    "image": "13.2",
                    "title": "Эпилог",
                    "text": "Деревня отстраивается на пепле, а двое братьев становятся молчаливыми стражами границы между двумя силами. Шрам той ночи остаётся навсегда, но вместе с ним остаётся и редкое чудо: не всё, что расколото, обязано быть уничтожено.",
                },
            ]
        self.open_story(ending_pages, callback=self.clear_save_after_ending, ending=True)

    # очищает сохранение after концовку
    def clear_save_after_ending(self):
        if SAVE_PATH.exists():
            try:
                SAVE_PATH.unlink()
            except OSError:
                pass
        self.scene = "menu"
        self.chapter = ""
        self.stats_overlay = False

