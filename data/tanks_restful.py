from flask import jsonify
from flask_restful import reqparse, abort, Api, Resource
from data import db_session
from data.users import User
import socket
from settings import SERVER_HOST, SERVER_PORT
import json
from time import sleep
from data.parser import parser


def abort_if_user_not_found(user_id):
    session = db_session.create_session()
    jobs = session.query(User).get(user_id)
    if not jobs:
        abort(404, message=f"User {user_id} not found")


class TanksSessionInfo(Resource):
    def get(self):
        try:
            with open('stat.txt', mode='rt') as file:
                return jsonify(json.load(file))
        except Exception:
            return jsonify({'error': 'Ошибка перевода в json'})


    # def post(self):
    #     args = parser.parse_args()
    #     with open('stat.txt', mode='wt') as file:
    #         json.dump(json.loads(args['stat']), file)
    #     return jsonify({'success': 'OK'})



    # def delete(self, user_id):
    #     abort_if_user_not_found(user_id)
    #     session = db_session.create_session()
    #     job = session.query(User).get(user_id)
    #     session.delete(job)
    #     session.commit()
    #     return jsonify({'success': 'OK'})


# class UsersListResource(Resource):
#     def get(self):
#         session = db_session.create_session()
#         users = session.query(User).all()
#         return jsonify({'users': [item.to_dict(
#             only=('id', 'name', 'surname', 'age', 'position', 'speciality', 'address', 'email')) for item in users]})
#
#     def post(self):
#         args = parser.parse_args()
#         session = db_session.create_session()
#         user = User(
#             surname=args['surname'],
#             name=args['name'],
#             age=args['surname'],
#             position=args['position'],
#             speciality=args['speciality'],
#             address=args['address'],
#             email=args['email']
#         )
#         session.add(user)
#         session.commit()
#         return jsonify({'success': 'OK'})
