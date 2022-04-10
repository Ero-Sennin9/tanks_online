import datetime
from flask import Flask, render_template, request, make_response, abort
from data import db_session
from data.users import User
from werkzeug.utils import redirect
from forms.user_tanks import LoginForm, RegisterForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from settings import SERVER_HOST, SERVER_PORT, SERVER_PORT_WEB
from flask_restful import reqparse, abort, Api, Resource
from turbo_flask import Turbo
from time import sleep
import threading
import json
import socket
from data.stats import Stats
from data.api import GetPos
app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(
    days=365
)
api = Api(app)
api.add_resource(GetPos, '/api/getpos')
login_manager = LoginManager()
login_manager.init_app(app)
turbo = Turbo(app)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.connect((SERVER_HOST, int(SERVER_PORT)))


def main():
    db_session.global_init("db/tanks.db")
    db_sess = db_session.create_session()

    @app.before_first_request
    def before_first_request():
        threading.Thread(target=update_load).start()

    def inject_load():
        try:
            sock.send(json.dumps({'info': None}).encode())
            info = json.loads(sock.recv(2 ** 20).decode())
            for i in range(len(info)):
                deaths = 1 if info[i][2]['deaths'] == 0 else info[i][2]['deaths']
                info[i][2]['KD'] = round(info[i][2]['kills'] / deaths, 2)
                info[i][2]['damage'] = round(info[i][2]['damage'], 2)
                user = db_sess.query(User).filter(User.email == info[i][0]).first()
                info[i].append(user.id)
        except Exception:
            info = []
        return info

    def update_load():
        with app.app_context():
            while True:
                # inject_load()
                turbo.push(turbo.replace(render_template('loadvg.html', info=inject_load()), 'load'))
                sleep(0.4)

    @login_manager.user_loader
    def load_user(user_id):
        return db_sess.query(User).get(user_id)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect("/login")

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = db_sess.query(User).filter(User.email == form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect("/")
            return render_template('login2.html',
                                   message="Неправильный логин или пароль",
                                   form=form)
        return render_template('login2.html', title='Авторизация', form=form)

    @app.route("/")
    def index():
        return render_template("players.html")

    @app.route("/info")
    def info():
        return render_template("information.html")

    @app.route("/player/<int:id>")
    def player(id):
        user = db_sess.query(User).filter(User.id == id).first()

        stat = db_sess.query(Stats).filter(Stats.player_mail == user.email).first()
        deaths = 1 if stat.deaths == 0 else stat.deaths
        kd = round(stat.kills / deaths, 2)
        return render_template("player.html", stat=stat, kd=kd, user=user)

    @app.route('/register', methods=['GET', 'POST'])
    def reqister():
        form = RegisterForm()
        if form.validate_on_submit():
            if form.password.data != form.password_again.data:
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Пароли не совпадают")
            if db_sess.query(User).filter(User.email == form.email.data).first():
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Такой пользователь уже есть")
            if db_sess.query(User).filter(User.nickname == form.nickname.data).first():
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Никнейм уже занят")
            user = User(
                name=form.name.data,
                surname=form.surname.data,
                age=int(form.age.data),
                email=form.email.data,
                nickname=form.nickname.data)
            stat = Stats(player_mail=form.email.data, kills=0, deaths=0, damage=0, hits=0, rik=0, fires=0)
            user.set_password(form.password.data)
            db_sess.add(user)
            db_sess.add(stat)
            db_sess.commit()
            return redirect('/login')
        return render_template('register.html', title='Регистрация', form=form)

    app.run(host=SERVER_HOST, port=int(SERVER_PORT_WEB))


if __name__ == '__main__':
    main()