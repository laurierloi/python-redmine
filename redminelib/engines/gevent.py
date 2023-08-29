"""
Synchronous blocking engine that processes requests one by one.
"""

import grequests
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from . import BaseEngine


class GeventEngine(BaseEngine):
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
        if method.lower() == 'get': # Getting, we can use grequests
            unsent_requests = [grequests.get(url, params=params, session=self.session) for params in bulk_params]
            print(f'number of requests {len(unsent_requests)}') # TODO: remove is only debug

            responses = grequests.map(unsent_requests, **self.config.grequests_map_args())
            try:
                processed_responses = (self.process_response(response)[container] for response in responses if response is not None)
            except Exception as exc:
                print(f'Exception: {exc}')
                import pdb; pdb.set_trace()
                raise exc
            return [resource for response in processed_responses for resource in response]
        else:
            return [resource for params in bulk_params for resource in self.request(method, url, params=params)[container]]
