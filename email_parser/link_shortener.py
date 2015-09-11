import requests


class NullShortener(object):
    name = 'null'

    def __init__(self, config):
        pass

    def shorten(self, link):
        return link


class KsShortener(object):
    name = 'keepsafe'
    url = 'http://4uon.ly/url/'

    def __init__(self, config):
        pass

    def shorten(self, link):
        # TODO needs auth
        # TODO needs perm links
        res = requests.post(self.url, data={'url': link})
        return res.text


def shortener(config):
    return NullShortener(config)
