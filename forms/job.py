from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms import BooleanField, SubmitField
from wtforms.validators import DataRequired


class JobsForm(FlaskForm):
    title = StringField('Job Title', validators=[DataRequired()])
    teamleader_id = StringField("Team Leader id")
    work_size = StringField("Work Size")
    collaborators = StringField("Collaborators")
    is_finished = BooleanField("Is job finished?")
    submit = SubmitField('Добавить')