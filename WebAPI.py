from pathlib import Path

from flask import Flask, request, send_from_directory
from flask_restful import Api, Resource

import PixivConfig
import PixivModel as PM

PixivConfig.cd_script_dir()
pcfg = PixivConfig.PixivConfig('config.json')

app = Flask('PixivWebAPI')
api = Api(app)
db = PM.PixivDB(pcfg.database_uri)


class GetWorksCaption(Resource):
    def get(self, works_id: int):
        session = db.sessionmaker()
        r = session.query(PM.WorksCaption).filter(
            PM.WorksCaption.works_id == works_id).one_or_none()
        if r:
            return r.caption_text


api.add_resource(GetWorksCaption, '/api/getCaption/<int:works_id>')


@app.route('/image/<path:path>')
def send_stored_img(path):
    return send_from_directory('./Test/stable/storage/works', path)


def run():
    app.run(debug=True)


if __name__ == "__main__":
    run()
