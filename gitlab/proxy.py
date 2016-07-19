import requests as rq


class ProxyRequests(object):

    def __init__(self, proxies):
        self.proxies_arg = {'proxies': proxies}

    def get(self, url, params=None, **kwargs):
        kwargs.update(self.proxies_arg)
        return rq.get(url=url, params=params, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        kwargs.update(self.proxies_arg)
        return rq.post(url=url, data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs):
        kwargs.update(self.proxies_arg)
        return rq.put(url=url, data=data, **kwargs)

    def delete(self, url, **kwargs):
        kwargs.update(self.proxies_arg)
        return rq.delete(url=url, **kwargs)