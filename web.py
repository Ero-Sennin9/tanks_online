import datetime
from flask import Flask, render_template, request, make_response, abort
from data import db_session
from data.users import User
from werkzeug.utils import redirect
from forms.user_tanks import LoginForm, RegisterForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from settings import SERVER_HOST, SERVER_PORT, SERVER_PORT_WEB
from turbo_flask import Turbo
from time import sleep
import threading
import json
import socket
app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(
    days=365
)
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
        db_sess = db_session.create_session()
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
            db_sess = db_session.create_session()
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
        return render_template("index9.html")

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
            user.set_password(form.password.data)
            db_sess.add(user)
            db_sess.commit()
            return redirect('/login')
        return render_template('register.html', title='Регистрация', form=form)

    app.run()


if __name__ == '__main__':
    main()