def _get_gender(g):
    if g == 'female':
        return 1
    elif g == 'male':
        return 0
    else:
        return -1


class User(dict):
    def __init__(self, user_info_json):
        self['user_id'] = user_info_json['user']['id']
        self['name'] = user_info_json['user']['name']
        self['account'] = user_info_json['user']['account']
        self['gender'] = _get_gender(user_info_json['profile']['gender'])
        self['total_illusts'] = user_info_json['profile']['total_illusts']
        self['total_manga'] = user_info_json['profile']['total_manga']
        self['total_novels'] = user_info_json['profile']['total_novels']
        self['is_followed'] = user_info_json['user']['is_followed']
        self['country_code'] = user_info_json['profile']['country_code']
        print(self)

    def __getattr__(self, attr):
        return self[attr]


class Works(dict):
    pass