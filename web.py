import datetime
from flask import Flask, render_template, request, make_response, abort
from data import db_session
from data.users import User
from werkzeug.utils import redirect
from forms.user_mars import LoginForm, RegisterForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_restful import reqparse, abort, Api, Resource
from data import tanks_restful
from requests import get
import json
import threading
from turbo_flask import Turbo
from time import sleep
from settings import SERVER_HOST, SERVER_PORT, SERVER_PORT_WEB
import socket


app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=365)
turbo = Turbo(app)
login_manager = LoginManager()
login_manager.init_app(app)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.connect((SERVER_HOST, int(SERVER_PORT)))


def main():
    db_session.global_init("db/mars.db")
    db_sess = db_session.create_session()

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
        db_sess = db_session.create_session()
        users = db_sess.query(User)
        return render_template("index8.html", jobs=[], users=users, User=User)

    @app.route('/register', methods=['GET', 'POST'])
    def reqister():
        form = RegisterForm()
        if form.validate_on_submit():
            if form.password.data != form.password_again.data:
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Пароли не совпадают")
            db_sess = db_session.create_session()
            if db_sess.query(User).filter(User.email == form.email.data).first():
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Такой пользователь уже есть")
            user = User(
                name=form.name.data,
                surname=form.surname.data,
                age=int(form.age.data),
                position=form.position.data,
                speciality=form.speciality.data,
                address=form.address.data,
                email=form.email.data)
            user.set_password(form.password.data)
            db_sess.add(user)
            db_sess.commit()
            return redirect('/login')
        return render_template('register.html', title='Регистрация', form=form)

    @app.before_first_request
    def before_first_request():
        threading.Thread(target=update_load).start()

    def inject_load():
        try:
            sock.send(json.dumps({'info': None}).encode())
            info = json.loads(sock.recv(2**20).decode())
        except Exception:
            info = []
        return info

    def update_load():
        with app.app_context():
            while True:
                # inject_load()
                turbo.push(turbo.replace(render_template('loadvg.html', info=inject_load()), 'load'))
                sleep(0.2)

    app.run()


if __name__ == '__main__':
    main()