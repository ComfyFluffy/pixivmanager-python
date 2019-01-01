import json


def _get_gender(g):
    if g == 'female':
        return 1
    elif g == 'male':
        return 0
    else:
        return -1


class User():
    def __init__(self, user_info, info_type):
        if info_type == 'json':
            user_info_json = json.loads(user_info)
            self.user_id = user_info_json['user']['id']
            self.name = user_info_json['user']['name']
            self.account = user_info_json['user']['account']
            self.gender = _get_gender(user_info_json['profile']['gender'])
            self.total_illusts = user_info_json['profile']['total_illusts']
            self.total_manga = user_info_json['profile']['total_manga']
            self.total_novels = user_info_json['profile']['total_novels']
            self.is_followed = user_info_json['user']['is_followed']
            self.country_code = user_info_json['profile']['country_code']
        else:
            info_type
        print(self)

    def __str__(self):
        return 'User: %s | %s' % (self.user_id, self.name)

    # def __getattr__(self, attr):
    #     return self[attr]


class Works(dict):
    pass