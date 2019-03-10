from flask_restful import Resource, Api
from flask import Flask, send_from_directory

app = Flask('PixivWebAPI')
api = Api(app)


class Test(Resource):
    def get(self):
        return {'faq': 'faqq'}


api.add_resource(Test, '/api')


@app.route('/image/<path:path>')
def send_stored_img(path):
    return send_from_directory('./Test/stable/storage/works', path)


app.run(debug=True)
