from flask_restful import reqparse, abort, Api, Resource
from flask import jsonify
import json


class GetPos(Resource):
    def get(self):
        with open('pos.txt', mode='rt') as file:
            return jsonify(json.load(file))
