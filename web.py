import datetime
from flask import Flask, render_template, request, make_response, abort
from data import db_session
from data.users import User
from werkzeug.utils import redirect
from forms.user_mars import LoginForm, RegisterForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from forms.job import JobsForm
from data.jobs import Jobs


app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=365)
login_manager = LoginManager()
login_manager.init_app(app)


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
        jobs = db_sess.query(Jobs).all()
        users = db_sess.query(User)
        return render_template("index8.html", jobs=[], users=users, User=User)

    @app.route('/jobs', methods=['GET', 'POST'])
    @login_required
    def add_job():
        form = JobsForm()
        if form.validate_on_submit():
            db_sess = db_session.create_session()
            job = Jobs()
            job.job = form.title.data
            job.team_leader = form.teamleader_id.data
            job.work_size = int(form.work_size.data)
            job.collaborators = form.collaborators.data
            job.is_finished = int(form.is_finished.data)
            db_sess.add(job)
            db_sess.commit()
            return redirect('/')
        return render_template('job.html', title='Добавление новости',
                               form=form)

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

    app.run()


if __name__ == '__main__':
    main()