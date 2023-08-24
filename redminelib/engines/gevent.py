"""
Synchronous blocking engine that processes requests one by one.
"""

import grequests
import requests

from . import BaseEngine


class GeventEngine(BaseEngine):
    @staticmethod
    def create_session(**params):
        session = requests.Session()

        for param in params:
            setattr(session, param, params[param])

        return session

    def process_bulk_request(self, method, url, container, bulk_params):
        if method.lower() == 'get': # Getting, we can use grequests
            unsent_requests = (grequests.get(url, params=params, session=self.session) for params in bulk_params)
            responses = grequests.map(unsent_requests)

            processed_responses = (self.process_response(response)[container] for response in responses)
            return [resource for response in processed_responses for resource in response]
        else:
            return [resource for params in bulk_params for resource in self.request(method, url, params=params)[container]]
