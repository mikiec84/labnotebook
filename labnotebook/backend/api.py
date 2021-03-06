from flask import Flask, jsonify
from flask_restful import Resource, Api, reqparse
from flask_cors import CORS, cross_origin
import labnotebook
from collections import defaultdict
from sqlalchemy.sql import func
import argparse

"""
API definititions
"""

def start_backend():
    parser = argparse.ArgumentParser()
    parser.add_argument("database_url")
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    app = Flask(__name__)
    # this is for the ability to run everything from different servers.
    cors = CORS(app)
    api = Api(app)

    xp,ts, mp = labnotebook.initialize(args.database_url)

    def flip_dict(dict_list):
        """
        helper function to flip list of dicts to dict of lists
        """
        result = defaultdict(list)

        for dic in dict_list:
            for k, v in dic.items():
                result[k].append(v)
        
        return result

    class Steps(Resource):
        def get(self, run_id):
            parser = reqparse.RequestParser()
            parser.add_argument('start_timestep', type=int, default=0)
            start_timestep = parser.parse_args()['start_timestep']

            query = labnotebook.session.query(ts.step_id,
            ts.timestep,
            ts.run_id,
            ts.trainacc,
            ts.valacc,
            ts.trainloss).filter(ts.run_id == run_id).filter(
                ts.timestep>start_timestep).all()
            result = labnotebook.runs_schema.dump(query)[0]

            return jsonify(flip_dict(result))

    class Experiments(Resource):
        def get(self):
            query = labnotebook.session.query(xp.run_id,
            xp.dt,
            xp.gpu,
            xp.completed,
            xp.final_trainacc,
            xp.final_trainloss,
            xp.final_valacc,
            xp.model_desc
            ).order_by(xp.run_id.desc()).all()
            result = labnotebook.xps_schema.dump(query)[0]

            return jsonify(result)

    class CustomFieldNames(Resource):
        def get(self, run_id):
            # FIRST CHECK IF THERE ARE CUSTOM FIELDS
            query = labnotebook.session.query(ts.custom_fields).filter(
                ts.run_id == run_id).filter(
                ts.timestep == 1).all()

            if query[0][0] is not None:
                query = labnotebook.session.query(
                    func.jsonb_object_keys(ts.custom_fields)).filter(
                    ts.run_id == run_id).filter(
                    ts.timestep == 1).all()

                query = [q[0] for q in query]

                return jsonify(query)

            return []

    class CustomFields(Resource):
        def get(self, run_id):
            parser = reqparse.RequestParser()
            parser.add_argument('fieldname', type=str)
            parser.add_argument('start_timestep', type=int, default=0)

            fieldname = parser.parse_args()['fieldname']
            start_timestep = parser.parse_args()['start_timestep']

            query = labnotebook.session.query(
                ts.timestep, ts.custom_fields[fieldname].label('cf')).filter(
                    ts.run_id == run_id).filter(
                    ts.timestep>start_timestep).all()

            result = labnotebook.cfs_schema.dump(query)[0]


            return jsonify(flip_dict(result))


    # our api:
    api.add_resource(Steps, '/steps/<string:run_id>')
    api.add_resource(CustomFields, '/customfields/<string:run_id>')
    api.add_resource(CustomFieldNames, '/customfieldnames/<string:run_id>')
    api.add_resource(Experiments, '/experiments')

    app.run(debug=True, host=args.host, port=3000)