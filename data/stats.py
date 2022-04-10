import datetime
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Stats(SqlAlchemyBase):
    __tablename__ = 'statistics'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    player_mail = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey("users.email"), unique=True)

    kills = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    deaths = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    rik = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    hits = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    fires = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    damage = sqlalchemy.Column(sqlalchemy.Float, nullable=True)

    user = orm.relation('User')