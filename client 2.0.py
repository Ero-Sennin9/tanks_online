import socket
import sys
import math, random
import pygame
import os
import json
import pygame as pg


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.connect(('localhost', 10000))

all_sprites = pg.sprite.Group()  # создание групп спрайтов для каждого типа объектов
players = pg.sprite.Group()
rocks = pg.sprite.Group()
grasses = pg.sprite.Group()
patrons = pg.sprite.Group()
boom = pg.sprite.Group()
health = pg.sprite.Group()
fires = pg.sprite.Group()


  # настройки pygame
x = 100
y = 45
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (x, y)
os.environ['SDL_VIDEO_CENTERED'] = '0'
pg.init()
GRASS_STONES = (80, 80)
SIZE = WIDTH, HEIGHT = 1500, 700
screen = pg.display.set_mode(SIZE)
clock = pg.time.Clock()
fire = False  # наличие огня
running = True
players_inf = {}  # спрайты других игроков
time = 0  # время, чтобы замедлять анимацию из-за высокого FPS
reload = False

boom_sound1 = pygame.mixer.Sound('sounds/boom.mp3')  # звуки
boom_sound2 = pygame.mixer.Sound('sounds/probitie1.mp3')
boom_sound3 = pygame.mixer.Sound('sounds/probitie-2.mp3')
rik_sound1 = pygame.mixer.Sound('sounds/rikoshet.mp3')
rik_sound2 = pygame.mixer.Sound('sounds/rikoshet1.mp3')
game_over = pygame.mixer.Sound('sounds/tank-unichtozhen.mp3')
pojar = pygame.mixer.Sound('sounds/pojar.mp3')
# boom_sounds = list(
#     [pygame.mixer.Channel(1), pygame.mixer.Channel(2)])  # списки для хранения каналов для воспроизведения
# rik_sounds = list([pygame.mixer.Channel(3), pygame.mixer.Channel(4)])
pojar_channel = pygame.mixer.Channel(0)


def load_image(name, colorkey=None):  # загрузка изображения для спрайта
    fullname = os.path.join('data', name)
    # если файла не существует, то выходим
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pg.image.load(fullname)
    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


class Stone(pg.sprite.Sprite):  # класс камня
    stone = pg.transform.scale(load_image('stone.png'), GRASS_STONES)  # открытие картинки с камнем

    def __init__(self, pos):
        super().__init__(rocks)  # добавление спрайта в группу камней
        self.image = self.stone
        self.rect = self.image.get_rect()
        self.rect.center = pos
        self.mask = pygame.mask.from_surface(self.image)  # создание маски для камня


class Grass(pg.sprite.Sprite):  # класс куста
    grass = pg.transform.scale(load_image('grass.png'), GRASS_STONES)  # открытие картинки с кустом

    def __init__(self, pos):
        super().__init__(grasses)
        self.image = self.grass
        self.rect = self.image.get_rect()
        self.rect.center = pos


def angle_p(vec):  # рассчет угла поворота исходя из вектора скорости
    x, y = vec
    result = None
    if x == 0 or y == 0:
        if x == 0:
            if y < 0:
                result = 0
            elif y > 0:
                result = 180
        elif y == 0:
            if x < 0:
                result = 270
            elif x > 0:
                result = 90
    else:
        angle1 = math.degrees(math.atan(abs(y) / abs(x)))
        if x < 0 and y < 0:
            result = 270 + angle1
        elif x > 0 and y > 0:
            result = 90 + angle1
        elif x > 0 and y < 0:
            result = 90 - angle1
        elif x < 0 and y > 0:
            result = 270 - angle1
    return result


class AnimatedSprite(pygame.sprite.Sprite):  # анимация спрайтов
    def __init__(self, x, y, sheet, columns, rows, count_frames=None,
                 paddings=(0, 0, 0, 0)):
        super().__init__(all_sprites)
        self.frames = []
        if count_frames is not None:
            self.count_frames = count_frames
        else:
            self.count_frames = columns * rows
        self.cut_sheet(sheet, columns, rows, paddings)
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.rect.center = x, y

    def cut_sheet(self, sheet, columns, rows, paddings):  # нарезка кадров для анимации
        self.rect = pygame.Rect(
            0, 0, (sheet.get_width() - paddings[1] - paddings[3]) // columns,
                  (sheet.get_height() - paddings[0] - paddings[2]) // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (
                    paddings[3] + self.rect.w * i,
                    paddings[0] + self.rect.h * j
                )
                self.frames.append(sheet.subsurface(pygame.Rect(
                    frame_location, self.rect.size)))
                if self.count_frames == len(self.frames):
                    return

    def update(self):  # сама анимация
        self.cur_frame = self.cur_frame + 1
        self.image = self.frames[self.cur_frame]


class Boom(AnimatedSprite):  # анимация взрыва
    sheet = load_image('boom.png')

    def __init__(self, x, y):
        super().__init__(x, y, self.sheet, 8, 4)
        boom.add(self)  # добавление спрайта в группу взрывов

    def update(self):  # анимация взрыва
        self.cur_frame = self.cur_frame + 1
        if self.cur_frame == self.count_frames - 1:  # уничтожение спрайта, если анимация окончена
            self.kill()
        self.image = self.frames[self.cur_frame]


class Fire(AnimatedSprite):  # анимация пожара
    sheet = load_image('fire.png')

    def __init__(self, player, time):
        super().__init__(player.rect.centerx, player.rect.centery - 40, self.sheet, 4, 4)
        fires.add(self)  # добавление спрайта в группу пожара
        self.time = time  # время действия пожара
        self.player = player  # игрок с этим эффектом

    def update(self):  # анимация взрыва
        global fire
        self.rect.center = self.player.rect.centerx, self.player.rect.centery - 40
        self.cur_frame = self.cur_frame + 1
        self.cur_frame %= self.count_frames
        self.time -= 1
        if self.time <= 0:  # уничтожение спрайта, если эффект окончен
            self.kill()
            fire = False
            pojar_channel.pause()  # остановка пожара
        self.image = self.frames[self.cur_frame]
        self.player.damage(0.089)  # урон от пожара


class HealthBar(pg.sprite.Sprite):  # класс полоски здоровья
    def __init__(self, size, pos, height):
        super().__init__(health)
        bar = pygame.Surface(size)  # рисование полоски
        bar.fill(pygame.Color("green"))
        pygame.draw.rect(bar, pygame.Color("black"), (0, 0, *size), 3)
        self.image = bar
        self.rect = self.image.get_rect()
        self.rect.center = pos  # позиция полоски
        self.size = size
        self.height = height  # высота полоски над центром спрайта игрока

    def update(self, player):  # обновление состояние полоски
        self.image.fill(pygame.Color("white"))
        pygame.draw.rect(self.image, pygame.Color("Green"), (2, 0, (self.size[0] - 3) * player.hp / 100, self.size[1]),
                         0)
        pygame.draw.rect(self.image, pygame.Color("black"), (0, 0, *self.size), 3)
        self.image = self.image.convert()  # делаем прозрачной полоску в месте белого цвета
        self.image.set_colorkey(pygame.Color("white"))
        self.image = self.image.convert_alpha()
        self.rect.center = player.rect.centerx, player.rect.centery - self.height  # рисование полоски с учетом высоты


class Tank(pg.sprite.Sprite):  # класс танка
    pictures = [pygame.transform.scale(load_image('tank1.png'), (40, 55)),
            pygame.transform.scale(load_image('tank2.png'), (40, 55)),
            pygame.transform.scale(load_image('tank1.png'), (40, 55)),
            pygame.transform.scale(load_image('tank2.png'), (40, 55))]  # загрузка изображений двух игроков

    def __init__(self, pos, rotation, player, control, time, shoot_button):
        super().__init__(players)
        self.first_position = pos
        self.pos = pos
        self.shoot_button = shoot_button
        self.player = player  # номер игрока
        self.control = control  # клавиши для управления танком
        self.image = pygame.transform.rotate(self.pictures[player - 1],
                                             360 - rotation)  # картинки для спрайтов исходя из номера игрока
        self.image2 = self.pictures[player - 1]  # а также поворот картинки
        self.mask = pygame.mask.from_surface(self.image)  # создание маски
        self.rect = self.image.get_rect()
        self.rect.center = pos
        self.angle = rotation  # переменная дл хранения изменяющегося угла танка
        self.rotation = rotation  # хранения поворота при спавне
        self.velocity = [0, 0]  # изначальный вектор скорости
        self.data = [False, False, False, False]  # возможность ускорений танка по всем направлениям
        self.slowing = 1  # замедление танка
        self.hp = 100  # здоровье танка
        self.health_bar = HealthBar([100, 18], (self.pos[0], self.pos[1] - 50), 50)  # задание полоски здоровья
        self.reload_center = (75, 38)  # центр значка перезарядки относительно центра танка
        self.time = time
        self.colision = False
        self.boom_sounds = pygame.mixer.Channel(1)
        self.rik_sounds = pygame.mixer.Channel(2)
        self.player_inf = {'pos': self.first_position, # информация, идущая на сервер
                           'shoot': [None, None]}

    def change_id(self, id_player):
        self.player = id_player
        self.image = pygame.transform.rotate(self.pictures[(self.player - 1) % 4],
                                             360 - self.rotation)  # картинки для спрайтов исходя из номера игрока
        self.image2 = self.pictures[(self.player - 1) % 4]  # а также поворот картинки

    def kill(self):
        self.health_bar.kill()
        super(Tank, self).kill()

    def move(self, events):  # управление танком
        for i in events:
            if i.type == pg.KEYDOWN or i.type == pg.KEYUP:  # при удерживании кнопки управления танком значение передвижения в данном направлении становится True
                if i.key == self.control[0]:
                    self.data[0] = not self.data[0]
                if i.key == self.control[1]:
                    self.data[1] = not self.data[1]
                if i.key == self.control[2]:
                    self.data[2] = not self.data[2]
                if i.key == self.control[3]:
                    self.data[3] = not self.data[3]
        self.velocity = [round(self.velocity[0], 1), round(self.velocity[1],
                                                           1)]  # округление скоростей, так как почему-то в процессе прибавления и убавления они изменяются
        if self.data[0] and self.velocity[1] > -SPEED_TANK:  # ускорение танка в соответсвии с удерживаемыми кнопками
            self.velocity[1] -= TANK_A
        elif self.velocity[1] < 0:
            self.velocity[1] += TANK_A
        if self.data[1] and self.velocity[0] < SPEED_TANK:
            self.velocity[0] += TANK_A
        elif self.velocity[0] > 0:
            self.velocity[0] -= TANK_A
        if self.data[2] and self.velocity[1] < SPEED_TANK:  # и, следовательно, замедление в случае отпускания кнопок
            self.velocity[1] += TANK_A
        elif self.velocity[1] > 0:
            self.velocity[1] -= TANK_A
        if self.data[3] and self.velocity[0] > -SPEED_TANK:
            self.velocity[0] -= TANK_A
        elif self.velocity[0] < 0:
            self.velocity[0] += TANK_A


        if angle_p(self.velocity) != None and any(self.data):  # поворот танка исходя из вектора скорости
            self.rotate(angle_p(self.velocity))

        if self.rect.centerx >= WIDTH - 20 and self.velocity[0] > 0:  # танк не может уйти за границы карты
            self.velocity[0] = 0
        elif self.rect.centery >= HEIGHT - 20 and self.velocity[1] > 0:
            self.velocity[1] = 0
        if self.rect.centerx <= 20 and self.velocity[0] < 0:
            self.velocity[0] = 0
        elif self.rect.centery <= 20 and self.velocity[1] < 0:
            self.velocity[1] = 0

        self.rect.move_ip(self.velocity[0] / self.slowing,
                          self.velocity[1] / self.slowing)  # передвижение танка с учетом замедления
        self.mask = pg.mask.from_surface(self.image)  # обновление маски, так как он все время поворачивается
        self.slowing = 1
        if pg.sprite.spritecollide(self, rocks, dokill=False,
                                   collided=pg.sprite.collide_mask):  # при столкновении с камнем снижается скорость и наносится урон
            self.slowing = SLOWING
            self.damage(0.02)

    def rotate(self, angle):  # поворот танка
        self.image = pg.transform.rotate(self.image2, 360 - angle)
        center = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = center  # сохранение центра необходимо для корректного вылета пули
        self.angle = angle

    def shoot(self):  # выстрел
        self.player_inf['shoot'][0] = True
        a, b = math.sin(math.radians(self.angle)) * SPEED_PATRON, -math.cos(
            math.radians(self.angle)) * SPEED_PATRON  # рассчет вектора скорости пули исходя из угла поворота танка
        self.player_inf['shoot'][1] = (a, b), self.rect.center, self.angle, self.player

    def update(self):  # обновление состояние танка
        self.time += 1
        self.health_bar.update(self)  # обновление полоски со здоровьем
        angle = (self.time / (RELOAD * FPS)) * 2 * math.pi
        pygame.draw.arc(screen, pygame.Color('blue'), (self.rect.centerx + self.reload_center[0] - 20,
                                                       self.rect.centery - self.reload_center[1] - 20, 20, 20),
                        0, angle, 5)  # состояние перезарядки

    def damage(self, dam):  # нанесение урона танку
        self.hp -= dam

    def return_tank(self):  # возвращение танка в начальную позицию
        self.hp = 100
        self.velocity = [0, 0]
        self.angle = self.rotation
        self.data = [False, False, False, False]
        self.image = pg.transform.rotate(self.image2, 360 - self.rotation)
        self.rect.center = self.first_position
        self.time = RELOAD * FPS


class Patron(pg.sprite.Sprite):
    pat = pg.transform.scale(pg.transform.rotate(load_image('patron.png', (255, 255, 255)), 90),
                             (10, 40))  # открытие избражения с пулей и ее сжатие

    def __init__(self, speed, pos, rotation, player_id, dam, angle_rik):
        super().__init__(patrons)
        self.speed = speed
        self.image = pg.transform.rotate(self.pat,
                                         360 - rotation)  # поворот ее на соответствующий градус исходя из поворота танка
        self.mask = pygame.mask.from_surface(self.image)  # создание маски для пули
        self.rect = self.image.get_rect()
        self.rect.center = pos
        self.player_id = player_id
        self.collide_with_tank = True  # возможность столкновения с танком
        self.dam = dam
        self.angle_rik = angle_rik

    def update(self):
        global fire, index
        for elem in players:
            if elem.player != self.player_id:
                if not pg.sprite.collide_mask(self,
                                              elem):  # если не сталкивается с другим игроком, то продолжает движение
                    self.rect.move_ip(*self.speed)
                else:
                    if self.collide_with_tank:
                        elem.damage(self.dam)  # нанесение урона при обратном
                        if self.dam >= 20:  # попадание по танку
                            sound = boom_sound2 if random.randint(1, 2) == 2 else boom_sound3
                            elem.boom_sounds.queue(boom_sound1), elem.boom_sounds.queue(
                                sound)  # звук взрыва
                            Boom(*self.rect.center)  # взрыв пули
                            self.kill()  # уничтожение пули
                            # if random.randint(1, 10) == 1:  # c небольшой вероятностью вызывается пожар
                            #     Fire(elem, random.randint(5 * FPS, 20 * FPS))
                            #     fire = True
                        else:  # если произошел рикошет - меняем направление пули
                            elem.rik_sounds.queue(rik_sound1), elem.rik_sounds.queue(
                                rik_sound2)  # звук рикошета
                            angle = self.angle_rik
                            self.speed = (math.sin(math.radians(angle)) * SPEED_PATRON,
                                          -math.cos(math.radians(angle)) * SPEED_PATRON)
                            self.image = pg.transform.rotate(self.pat, 360 - angle)
                            self.mask = pygame.mask.from_surface(self.image)
                        self.collide_with_tank = False
            else:
                self.rect.move_ip(*self.speed)

        if pg.sprite.spritecollide(self, rocks, dokill=False,
                                   collided=pygame.sprite.collide_mask):  # столкновение с камнем
            pygame.mixer.Sound('sounds/rock_boom.mp3').play()
            Boom(*self.rect.center)  # взрыв пули
            self.kill()  # уничтожение пули
        if self.rect.centerx >= WIDTH + self.rect.width or self.rect.centerx <= -self.rect.width:  # уничтожение пули при вылете за границы для оптимизации игры
            self.kill()  # уничтожение пули
        if self.rect.centery >= HEIGHT + self.rect.width or self.rect.centery <= -self.rect.width:
            self.kill()  # уничтожение пули


player_id = 1
player_pos = (60, HEIGHT / 2)

pole = load_image('pole.jpg')  # загрузка изображения игрового поля
game = True  # статус игры
font, font2 = pg.font.Font(None, 50), pg.font.Font(None, 36)  # шрифты для текста
try:
    info = json.loads(sock.recv(2 ** 20).decode())
    if 'generation' in info:
        rocks_pos, grasses_pos = info['generation'][0], info['generation'][1]
        for pos1 in rocks_pos:
            all_sprites.add(Stone(pos1))
        for pos2 in grasses_pos:
            all_sprites.add(Grass(pos2))
    if 'id' in info:
        player_id = info['id'] % 4
    if 'pos' in info:
        player_pos = info['pos']
    if 'settings' in info:
        FPS = info['settings']['fps']
        SPEED_TANK = info['settings']['speed_tank']
        SPEED_PATRON = info['settings']['speed_patron']
        TANK_A0 = info['settings']['tank_a0']
        GRASS_STONES = info['settings']['grass_stones']
        RELOAD = info['settings']['reload']
        SLOWING = info['settings']['slowing']
        TANK_A = round(TANK_A0, 1)
except Exception:
    data = sock.recv(2 ** 20).decode()


player_main = Tank(player_pos, 90, player_id, [pg.K_w, pg.K_d, pg.K_s, pg.K_a], RELOAD * FPS, pg.MOUSEBUTTONDOWN)  # создание игроков

all_sprites.add(player_main)  # добавление их в группу всех спрайтов для отслеживания столкновений при генерации карты


while running:
    time += 1
    player_main.player_inf['shoot'][0] = False
    if fire:
        if pojar_channel.get_queue():  # звук пожара
            pojar_channel.unpause()
        else:
            pojar_channel.queue(pojar)
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False
        if event.type == player_main.shoot_button and game and player_main.time >= RELOAD * FPS and player_main.hp > 0:
            player_main.time = 0
            player_main.shoot()
    if reload:  # перезагрузка игры
        pojar_channel.pause()  # остановка пожара
        game = True
        for fire in fires:  # уничтожение пожаров
            fire.kill()
        fire = False
        for player in players:
            player.return_tank()  # восстановление здоровья у игроков
        reload = False

    if game and player_main.hp > 0:
        player_main.move(events)  # передвижение игроков
    else:
        player_main.data = [False, False, False, False]
    if True:
        for player1 in players:
            data = pygame.sprite.spritecollide(player1, players, dokill=False, collided=pygame.sprite.collide_mask)
            if len(data) > 1:
                for player2 in data:
                    if player2 != player1:
                        player1.slowing, player2.slowing = SLOWING, SLOWING
            else:
                player1.colision = False
    player_main.player_inf['velocity'] = player_main.velocity
    player_main.player_inf['hp'] = player_main.hp
    player_main.player_inf['angle'] = player_main.angle
    player_main.player_inf['pos'] = player_main.rect.center
    sock.send(json.dumps(player_main.player_inf).encode())
    screen.blit(pole, (0, 0)), rocks.draw(screen), players.draw(screen)  # отрисовка кадра
    patrons.draw(screen), fires.draw(screen), grasses.draw(screen), health.draw(screen), boom.draw(screen)
    if not game:  # если игра окончена, выводится сообщение с результатом
        text = font.render(f'Игра окончена', True, pygame.Color('red'))  # рендер текста
        text2 = font2.render('Нажмите p для перезапуска', True, pygame.Color('yellow'))
        text_x = WIDTH // 2 - text.get_width() // 2  # размещение текста в центре экрана
        text_y = HEIGHT // 2 - text.get_height() // 2
        screen.blit(text, (text_x, text_y))  # отображение текста
        screen.blit(text2, (text_x, text_y + 50))
    else:
        result = []
    # text = font.render(f'{score[0]} : {score[1]}', True, pygame.Color('green'))  # рендер текста
    # text_x, text_y = text.get_width() // 2, text.get_height() // 2  # размещение текста в верхнем левом углу
    # screen.blit(text, (text_x, text_y))  # отображение текста
    players.update(), patrons.update()  # обновление спрайтов(анимация, движение, взрывы, обновление полоски здоровья)
    if time % 3 == 1:
        boom.update()
        fires.update()
    clock.tick(FPS)
    pg.display.flip()  # обновление дисплея
    try:
        info = json.loads(sock.recv(2 ** 20).decode())
        if 'patrons' in info:
            for el in info['patrons']:
                Patron(*el)

        if 'players' in info:
            data_players = info['players']
            for id0 in data_players.keys():
                player_info = data_players[id0]
                if int(id0) != player_main.player:
                    if id0 not in players_inf:
                        players_inf[id0] = Tank(player_info['pos'], 90, int(id0), [pg.K_w, pg.K_d, pg.K_s, pg.K_a],
                                               RELOAD * FPS, pg.KEYDOWN)
                    players_inf[id0].hp = player_info['hp']
                    players_inf[id0].rotate(player_info['angle'])
                    players_inf[id0].rect.center = player_info['pos']
                    players_inf[id0].velocity = player_info['velocity']
                    if player_info['fire'][0]:
                        Fire(players_inf[id0], player_info['fire'][1])
                else:
                    player_main.hp = player_info['hp']

            for key_id in players_inf.keys():
                if key_id not in data_players.keys():
                    players_inf[key_id].kill()
                    del players_inf[key_id]
        if 'fire_sound' in info:
            fire = info['fire_sound']
        if 'reload' in info:
            reload = info['reload']

    except Exception:
        # info = sock.recv(2 ** 20).decode()
        pass
