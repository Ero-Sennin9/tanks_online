from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, TextAreaField, SubmitField, BooleanField, EmailField, IntegerField
# from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Email, NumberRange, Length, ValidationError
import email_validator


class LoginForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired('Введите почту')])
    password = PasswordField('Пароль', validators=[DataRequired('Введите пароль')])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class RegisterForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired('Введите почту'), Email('Некорректная почта')])
    password = PasswordField('Пароль', validators=[DataRequired('Введите пароль')])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    name = StringField('Имя пользователя', validators=[DataRequired('Введите почту')])
    surname = StringField('Фамилия пользователя')
    nickname = StringField('Nickname', validators=[DataRequired('Введите nickname'), Length(min=3, max=20,
                                                                                            message="Nickname должен быть от 4 до 20 символов")])
    age = IntegerField('Возраст', validators=[DataRequired('Введите возраст')])
    submit = SubmitField('Войти')

