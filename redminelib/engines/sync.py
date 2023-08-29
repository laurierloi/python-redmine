"""
Synchronous blocking engine that processes requests one by one.
"""

import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from . import BaseEngine


class SyncEngine(BaseEngine):
    @staticmethod
    def create_session(**params):
        config = params['config']
        session = requests.Session()
        retry = Retry(**config.retry_args())
        session.mount('http://', HTTPAdapter(max_retries=retry, **config.adapter_args()))
        session.mount('https://', HTTPAdapter(max_retries=retry, **config.adapter_args()))

        for param in params:
            if param in ['config']:
                continue
            setattr(session, param, params[param])

        return session


    def process_bulk_request(self, method, url, container, bulk_params):
        return [resource for params in bulk_params for resource in self.request(method, url, params=params)[container]]
