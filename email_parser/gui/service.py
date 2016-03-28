import asyncio
import aiohttp
import logging
import urllib.parse
import concurrent.futures
from functools import wraps

logger = logging.getLogger(__name__)

ENDPOINTS = {
    'push': {'method': 'PUT', 'url': '/templates/%s/%s'},
    'show': {'method': 'GET', 'url': '/templates/%s/%s'}
}

class TimeoutError(Exception):

    def __init__(self, message):
        super().__init__(message)


class ServiceError(Exception):

    def __init__(self, message, status, text):
        super().__init__(message)
        self.status = status
        self.text = text


class Client(object):

    def __init__(self, host, loop=None):
        self._host = host
        self._loop = loop or asyncio.get_event_loop()

    def request(self, path='', method='GET', timeout=5, **kwargs):
        url = urllib.parse.urljoin(self._host, path)
        req = aiohttp.request(method, url, loop=self._loop, **kwargs)
        try:
            res = yield from asyncio.wait_for(req, timeout, loop=self._loop)
        except concurrent.futures.TimeoutError:
            msg = 'service request timed out after %ss' % timeout
            raise TimeoutError(msg)
        if res.status != 200:
            text = yield from res.text()
            raise ServiceError('service returned error', res.status, text)
        return (yield from res.text())

    def push_template(self, locale, name, filepath):
        data = {'template': open(filepath, 'rb')}
        return self.request(ENDPOINTS['push']['url'] % (locale, name),
                            ENDPOINTS['push']['method'],
                            data=data
                            )


    def get_template(self, locale, name):
        return self.request(ENDPOINTS['show']['url'] % (locale, name),
                            ENDPOINTS['show']['method']
                            )
