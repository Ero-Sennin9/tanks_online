import json
import socket
import sys
import time
import pygame as pg
import random
import pygame.sprite
import math

from data.users import User

from data import db_session
from settings import SERVER_HOST, SERVER_PORT
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"  # на сервере нет дисплея

main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # настройка сервера
main_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
main_socket.bind((SERVER_HOST, int(SERVER_PORT)))
main_socket.setblocking(0)
main_socket.listen(5)

db_session.global_init("db/tanks.db")
db_sess = db_session.create_session()


id_players = 1   # id одключающихся игроков


FPS = 120  # настройки pygame
x = 100
y = 45
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (x, y)
os.environ['SDL_VIDEO_CENTERED'] = '0'
pg.init()
SIZE = WIDTH, HEIGHT = 3000, 3000
screen = pg.display.set_mode(SIZE)
clock = pg.time.Clock()
SPEED_TANK = 4.2  # максимальная скорость танка
SPEED_PATRON = 14  # скорость патрона
TANK_A0 = 0.16
FIRE_RAND = 10
TANK_A = round(TANK_A0, 1)  # ускорение танка при нажатии на кнопки движения
GRASS_STONES = (80, 80)  # размер камней и травы
RELOAD = 4  # время перезарядки
SLOWING = 4
TIME_FOR_REL = 4 * FPS
fire = False  # наличие огня
ERRORS = 750
MAX_PLAYERS = 15

all_sprites = pg.sprite.Group()  # создание групп спрайтов для каждого типа объектов
players = pg.sprite.Group()
rocks = pg.sprite.Group()
grasses = pg.sprite.Group()
patrons = pg.sprite.Group()
boom = pg.sprite.Group()
health = pg.sprite.Group()
fires = pg.sprite.Group()


players_inf = {}  # хранение спрайтов игроков с ключом по id
pole_info = {'players': {}}   # информация о состоянии игры для отправки


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


def load_image(name, colorkey=None):  # загрузка изображения для спрайта
    fullname = os.path.join('pictures', name)
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


class Fire(AnimatedSprite):  # анимация пожара
    sheet = load_image('fire.png')

    def __init__(self, player, time, player_id):
        super().__init__(player.rect.centerx, player.rect.centery - 40, self.sheet, 4, 4)
        fires.add(self)  # добавление спрайта в группу пожара
        self.time = time  # время действия пожара
        self.player = player  # игрок с этим эффектом
        self.player_id = player_id

    def update(self):  # анимация взрыва
        global fire
        self.rect.center = self.player.rect.centerx, self.player.rect.centery - 40
        self.cur_frame = self.cur_frame + 1
        self.cur_frame %= self.count_frames
        self.time -= 1
        self.image = self.frames[self.cur_frame]
        self.player.damage(0.089, self.player_id)  # урон от пожара
        if self.time <= 0 or self.player.hp <= 0:  # уничтожение спрайта, если эффект окончен
            fire = False
            self.kill()


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


class Tank(pg.sprite.Sprite):  # класс танка
    pictures = [pygame.transform.scale(load_image('tank1.png'), (40, 55)),
            pygame.transform.scale(load_image('tank2.png'), (40, 55)),
            pygame.transform.scale(load_image('tank1.png'), (40, 55)),
            pygame.transform.scale(load_image('tank2.png'), (40, 55))]  # загрузка изображений игроков

    def __init__(self, pos, rotation, player, control, time, shoot_button, mail, nickname):
        super().__init__(players)
        self.mail = mail
        self.nickname = nickname
        self.is_rock_colision = False
        self.stat = {'kills': 0,
                     'deaths': 0,
                     'hits': 0,
                     'rik': 0,
                     'damage': 0,
                     'fires': 0}
        self.first_position = pos
        self.pos = pos
        self.shoot_button = shoot_button
        self.player = player  # id игрока
        self.control = control  # клавиши для управления танком
        self.image = pygame.transform.rotate(self.pictures[player % 4],
                                             360 - rotation)  # картинки для спрайтов исходя из номера игрока
        self.fire = [False, None]  # информация об анимации пожара для передачи
        self.image2 = self.pictures[player % 4]  # а также поворот картинки
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
        self.player_inf = {'pos': self.first_position,# информация, идущая на сервер
                           'shoot': [None, None]}
        self.time_delete_patrons = 0
        self.time_delete_fire = 0

    def rotate(self, angle):  # поворот танка
        self.image = pg.transform.rotate(self.image2, 360 - angle)
        center = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = center  # сохранение центра необходимо для корректного вылета пули
        self.angle = angle

    def kill(self):
        self.health_bar.kill()
        super(Tank, self).kill()

    # def shoot(self):  # выстрел
    #     a, b = math.sin(math.radians(self.angle)) * SPEED_PATRON, -math.cos(
    #         math.radians(self.angle)) * SPEED_PATRON  # рассчет вектора скорости пули исходя из угла поворота танка
    #     Patron((a, b), self.rect.center, self.angle, self.player)  # создание пули

    def update(self):  # обновление состояние танка
        self.time += 1
        self.time_delete_patrons += 1
        self.time_delete_fire += 1
        if self.time_delete_fire % 4 == 0:
            self.fire[0] = False
        if self.time_delete_patrons % 4 == 0:
            pole_info['players'][self.player]['patrons'] = pole_info['players'][self.player]['patrons'][1:]
        self.health_bar.update(self)  # обновление полоски со здоровьем
        angle = (self.time / (RELOAD * FPS)) * 2 * math.pi
        pygame.draw.arc(screen, pygame.Color('blue'), (self.rect.centerx + self.reload_center[0] - 20,
                                                       self.rect.centery - self.reload_center[1] - 20, 20, 20),
                        0, angle, 5)  # состояние перезарядки

    def damage(self, dam, sender_id):  # нанесение урона танку
        if sender_id != None:
            players_inf[sender_id].stat['damage'] += dam
        if self.hp > 0:
            self.hp -= dam
            if self.hp <= 0:
                if sender_id != None:
                    players_inf[sender_id].stat['kills'] += 1
                self.stat['deaths'] += 1

    def return_tank(self):  # возвращение танка в начальную позицию
        self.hp = 100
        self.velocity = [0, 0]
        self.angle = self.rotation
        self.data = [False, False, False, False]
        self.image = pg.transform.rotate(self.image2, 360 - self.rotation)
        self.rect.center = self.first_position
        self.time = RELOAD * FPS

    def rock_colision(self):
        if pg.sprite.spritecollide(self, rocks, dokill=False,
                                   collided=pg.sprite.collide_mask):  # при столкновении с камнем снижается скорость и наносится урон
            if not self.is_rock_colision:
                self.is_rock_colision = True
                speed = (self.velocity[0] ** 2 + self.velocity[1] ** 2) ** 0.5
                damage = (speed / (2 * (SPEED_TANK * 2) ** 2) ** 0.5) * 100
                self.damage(random.choice([damage / 4, damage / 3, damage / 2, damage]), None)

            self.slowing = 4
            self.damage(0.02, None)
        else:
            self.is_rock_colision = False

    def shoot_data(self, data):
        self.time = 0
        Patron(*data)  # создание пули


class Patron(pg.sprite.Sprite):
    pat = pg.transform.scale(pg.transform.rotate(load_image('patron.png', (255, 255, 255)), 90),
                             (10, 40))  # открытие избражения с пулей и ее сжатие

    def __init__(self, speed, pos, rotation, player_id, dam, angle_rik):
        super().__init__(patrons)
        self.number1 = 0
        self.number2 = 0
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
                        dam = self.dam[self.number1 % 4]
                        elem.damage(dam, self.player_id)  # нанесение урона при обратном
                        self.number1 += 1
                        if dam >= 20:  # попадание по танку
                            players_inf[self.player_id].stat['hits'] += 1
                            Boom(*self.rect.center)  # взрыв пули
                            self.kill()  # уничтожение пули
                            if random.randint(1, FIRE_RAND) == 1:  # c небольшой вероятностью вызывается пожар
                                time_fire = random.randint(5 * FPS, 20 * FPS)
                                Fire(elem, time_fire, self.player_id)
                                fire = True
                                elem.fire = [True, time_fire]
                                elem.time_delete_fire = 0
                                players_inf[self.player_id].stat['fires'] += 1

                        else:  # если произошел рикошет - меняем направление пули
                            players_inf[self.player_id].stat['rik'] += 1
                            angle = self.angle_rik[self.number2 % 4]
                            self.number2 += 1
                            self.speed = (math.sin(math.radians(angle)) * SPEED_PATRON,
                                          -math.cos(math.radians(angle)) * SPEED_PATRON)
                            self.image = pg.transform.rotate(self.pat, 360 - angle)
                            self.mask = pygame.mask.from_surface(self.image)
                        self.collide_with_tank = False
            else:
                self.rect.move_ip(*self.speed)

        if pg.sprite.spritecollide(self, rocks, dokill=False,
                                   collided=pygame.sprite.collide_mask):  # столкновение с камнем
            Boom(*self.rect.center)  # взрыв пули
            self.kill()  # уничтожение пули
        if self.rect.centerx >= WIDTH + self.rect.width or self.rect.centerx <= -self.rect.width:  # уничтожение пули при вылете за границы для оптимизации игры
            self.kill()  # уничтожение пули
        if self.rect.centery >= HEIGHT + self.rect.width or self.rect.centery <= -self.rect.width:
            self.kill()  # уничтожение пули


class Tank2(Tank):  # класс танка для задания позиций игроков в начале игры
    def __init__(self, pos, rotation):
        super().__init__(pos, rotation, 1, [pg.K_w, pg.K_d, pg.K_s, pg.K_a], RELOAD * FPS, pg.KEYDOWN, 'gen', 'gen')


def generate_level(value_of_grass, value_of_stones):  # генерация уровня
    for i in range(value_of_grass):
        while True:
            el = Grass((random.randint(GRASS_STONES[0] / 2 + 1, WIDTH - (GRASS_STONES[0] / 2 + 1)),  # создание травы
                        random.randint(GRASS_STONES[0] / 2 + 1, HEIGHT - (GRASS_STONES[0] / 2 + 1))))
            if not pg.sprite.spritecollide(el, all_sprites, dokill=False,
                                           collided=pygame.sprite.collide_circle):  # проверка на столкновение с другими объектам
                all_sprites.add(el)
                break
            else:
                el.kill()
    for j in range(value_of_stones):
        while True:
            el = Stone((random.randint(GRASS_STONES[0] / 2 + 1, WIDTH - (GRASS_STONES[0] / 2 + 1)),  # создание камней
                        random.randint(GRASS_STONES[0] / 2 + 1, HEIGHT - (GRASS_STONES[0] / 2 + 1))))
            if not pg.sprite.spritecollide(el, all_sprites, dokill=False,
                                           collided=pygame.sprite.collide_circle):  # проверка на столкновение с другими объектами
                all_sprites.add(el)
                break
            else:
                el.kill()


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


positions = []
angles = []
running = True
generate_level(100, 130)
data_rocks_grass = [[rock.rect.center for rock in rocks], [grass.rect.center for grass in grasses]]  # иинформация о расположении травы и камней
print(data_rocks_grass)

while len(positions) != MAX_PLAYERS:  # позиции для расположения игроков
    el = Tank2((random.randint(100, WIDTH - 100), random.randint(100, HEIGHT - 100)), random.randint(0, 360))
    if not pg.sprite.spritecollide(el, all_sprites, dokill=False,
                                   collided=pygame.sprite.collide_circle):  # проверка на столкновение с другими объектам
        positions.append(el.pos)
        angles.append(el.angle)
        all_sprites.add(el)
    else:
        el.kill()
for player in players:
    player.kill()

print(positions)
players_information = []
pole = load_image('pole.jpg')  # загрузка изображения игрового поля
game = True  # статус игры
font, font2 = pg.font.Font(None, 50), pg.font.Font(None, 36)  # шрифты для текста


def get_all_id(players):
    return [player.player for player in players]


def get_all_hp(players):
    return list(filter(lambda s: s > 0, [player.hp for player in players]))


def get_all_logins(players):
    return [el.mail for el in players]


time_for_reload = 0
while running:
    ides = get_all_id(players)
    pole_info['game'] = game
    pole_info['fire_sound'] = fire
    pole_info['reload'] = False
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False
    if not game:
        time_for_reload += 1
        if time_for_reload >= TIME_FOR_REL:
            pole_info['reload'] = True
            game = True
            for player in players:
                player.hp = 100
            for fire0 in fires:
                fire0.kill()
                fire = False
            time_for_reload = 0
    if (len(get_all_hp(players)) <= 1 and len(players) > 1) or (len(get_all_hp(players)) == 0 and len(players) == 1):
        game = False
    try:
        new_socket, addr = main_socket.accept()  # подключение игрока и отправка ему данных об игре
        print('Подключился', addr)
        new_socket.setblocking(0)
        players_information.append([id_players, new_socket, 0, None, False, None, None])
        id_players += 1
    except Exception:
        pass

    for data1 in players_information:  # получение информации от пользователей и иx обработка
        id, new_socket, errors, data, autorization, login, nickname = data1
        try:
            info = data1[1].recv(2 ** 20)
            login_or_inform = json.loads(info.decode())
            if 'login' in login_or_inform:
                user = db_sess.query(User).filter(User.email == login_or_inform['login']).first()
                if user and user.check_password(login_or_inform['password']):
                    if login_or_inform['login'] not in get_all_logins(players):
                        if len(players_inf.values()) < MAX_PLAYERS:
                            data1[4] = True
                            data1[5] = login_or_inform['login']
                            data1[6] = user.nickname
                            json1 = {'id': id,
                                     'generation': data_rocks_grass,
                                     'pos': positions[id % MAX_PLAYERS],
                                     'settings': {'fps': FPS,
                                                  'speed_tank': SPEED_TANK,
                                                  'speed_patron': SPEED_PATRON,
                                                  'tank_a0': TANK_A0,
                                                  'grass_stones': GRASS_STONES,
                                                  'reload': RELOAD,
                                                  'slowing': SLOWING,
                                                  'size': SIZE},
                                     'angle': angles[id % MAX_PLAYERS]}
                            new_socket.send(json.dumps(json1).encode())
                            # time.sleep(3)
                        else:
                            new_socket.send(json.dumps({'error': 'Сервер заполнен'}).encode())
                    else:
                        new_socket.send(json.dumps({'error': 'Пользователь уже в игре'}).encode())
                else:
                    new_socket.send(json.dumps({'error': 'Неправильный логин или пароль'}).encode())
            if 'pos' in login_or_inform and autorization:
                data1[3] = login_or_inform
            if 'info' in login_or_inform:
                players_stat = [[player0.mail, player0.nickname, player0.stat] for player0 in players]
                new_socket.send(json.dumps(players_stat).encode())
            if 'exit' in login_or_inform:
                print(login_or_inform['exit'])
                user = db_sess.query(User).filter(User.email == login_or_inform['exit'][0]).first()
                if user and user.check_password(login_or_inform['exit'][1]):
                    data1[2] = ERRORS
                    print('вышел')

        except Exception:
            pass

    info_send = list(map(lambda s: [s[0], s[3], s[5], s[6]], players_information))
    for id, player_info, login, nickname in info_send:  # получение информации от пользователей и иx обработка
        if player_info != None:  # получение информации от пользователей и иx обработка
            if id not in players_inf:  # создание танка, если он отсутствует в списке
                players_inf[id] = Tank(player_info['pos'], 90, id, [pg.K_w, pg.K_d, pg.K_s, pg.K_a],
                                        RELOAD * FPS, pg.KEYDOWN, login, nickname)
            players_inf[id].velocity = player_info['velocity']  # иначе - применение переданных данных об игроке
            players_inf[id].rotate(player_info['angle'])
            players_inf[id].rect.center = player_info['pos']
            if id not in pole_info['players']:
                pole_info['players'][id] = {'patrons': []}
            pole_info['players'][id]['hp'] = players_inf[id].hp  # сбор информации для отправки
            pole_info['players'][id]['pos'] = player_info['pos']
            pole_info['players'][id]['angle'] = player_info['angle']
            pole_info['players'][id]['velocity'] = player_info['velocity']
            pole_info['players'][id]['fire'] = players_inf[id].fire
            pole_info['players'][id]['kills'] = players_inf[id].stat['kills']
            pole_info['players'][id]['mail'] = players_inf[id].mail
            pole_info['players'][id]['nickname'] = nickname
            if player_info['shoot'][0]:  # выстрел
                if players_inf[id].time >= RELOAD * FPS:
                    dam = [random.randint(4, 10) if random.randint(1, 3) == 2 else random.randint(22, 30) for i in range(4)]  # рикошет или не рикошет + расчет урона
                    angle = []
                    for i in range(4):
                        angle0 = (angle_p(player_info['shoot'][1][0]) + random.randint(-28, 28)) % 360
                        angle.append(360 - abs(angle0) if angle0 < 0 else angle0)
                    data_patron = player_info['shoot'][1] + [dam, angle]
                    players_inf[id].shoot_data(data_patron)
                    pole_info['players'][id]['patrons'].append(data_patron)  # передача информации о пуле
                    players_inf[id].time_delete_patrons = 0
    for player1 in players:  # обработка столкновений
        data = pygame.sprite.spritecollide(player1, players, dokill=False, collided=pygame.sprite.collide_mask)
        if len(data) > 1:
            for player2 in data:
                if player2 != player1:
                    player1.slowing, player2.slowing = 4, 4
                    if not player1.colision or not player2.colision:
                        speedx, speedy = abs(player1.velocity[0] - player2.velocity[0]), abs(
                            player1.velocity[1] - player2.velocity[1])
                        speed = (speedx ** 2 + speedy ** 2) ** 0.5
                        damage = (speed / (2 * (SPEED_TANK * 2) ** 2) ** 0.5) * 100
                        damage1 = random.choice([damage / 4, damage / 3, damage / 2, damage])
                        damage2 = random.choice([damage / 4, damage / 3, damage / 2, damage])
                        player1.damage(damage1, player2.player), player2.damage(damage2, player1.player)  # нанесение урона при аварии
                        if damage >= 30:
                            Boom(*player1.rect.center), Boom(*player2.rect.center)  # взрывы при аварии
                        player1.colision, player2.colision = True, True
                    player1.damage(0.03, player2.player), player2.damage(0.03, player1.player)  # урон при контакте
        else:
            player1.colision = False

    for data2 in players_information:  # отправление состояния игрового поля + отключение игрока
        sock = data2[1]
        id0 = data2[0]
        try:
            if data2[-1]:
                sock.send(json.dumps(pole_info).encode())
        except Exception:
            data2[2] += 1
        if data2[2] >= ERRORS:
            print(data2)
            try:
                players_inf[data2[0]].kill()
                del players_inf[data2[0]]
                del pole_info['players'][data2[0]]
            except Exception:
                pass
            players_information.remove(data2)
            sock.close()
            print('Отключился')
    # screen.blit(pole, (0, 0)), rocks.draw(screen), players.draw(screen)  # отрисовка кадра
    # patrons.draw(screen), fires.draw(screen), grasses.draw(screen), health.draw(screen), boom.draw(screen)
    # if not game:  # если игра окончена, выводится сообщение с результатом
    #     text = font.render(f'Игра окончена', True, pygame.Color('red'))  # рендер текста
    #     text2 = font2.render('Нажмите p для перезапуска', True, pygame.Color('yellow'))
    #     text_x = WIDTH // 2 - text.get_width() // 2  # размещение текста в центре экрана
    #     text_y = HEIGHT // 2 - text.get_height() // 2
    #     screen.blit(text, (text_x, text_y))  # отображение текста
    #     screen.blit(text2, (text_x, text_y + 50))
    # else:
    #     result = []
    # text = font.render(f'{score[0]} : {score[1]}', True, pygame.Color('green'))  # рендер текста
    # text_x, text_y = text.get_width() // 2, text.get_height() // 2  # размещение текста в верхнем левом углу
    # screen.blit(text, (text_x, text_y))  # отображение текста
    for player0 in players:
        player0.fire[0] = False
    players.update(), patrons.update(), boom.update(), fires.update()  # обновление спрайтов(анимация, движение, взрывы, обновление полоски здоровья)
    for player0 in players:
        player0.rock_colision()
    clock.tick(FPS)
    # pg.display.flip()

