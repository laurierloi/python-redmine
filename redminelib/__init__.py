"""
Provides public API.
"""

import os
import io
import inspect
import warnings
import datetime
import contextlib

from . import managers, exceptions, engines, utilities, resources
from .version import __version__


class Redmine:
    """
    Entry point for all requests.
    """
    def __init__(self, url, **kwargs):
        """
        :param string url: (required). Redmine location.
        :param string key: (optional). API key used for authentication.
        :param string version: (optional). Redmine version.
        :param string username: (optional). Username used for authentication.
        :param string password: (optional). Password used for authentication.
        :param dict requests: (optional). Connection options.
        :param string impersonate: (optional). Username to impersonate.
        :param string date_format: (optional). Formatting directives for date format.
        :param string datetime_format: (optional). Formatting directives for datetime format.
        :param raise_attr_exception: (optional). Control over resource attribute access exception raising.
        :type raise_attr_exception: bool or tuple
        :param timezone: (optional). Whether to convert a naive datetime to a specific timezone aware one.
        :type timezone: str or cls
        :param EngineConfig engine_config: (optional). Configuration object.
        :param cls engine: (optional). Engine that will be used to make requests to Redmine.
        """
        self.url = url.rstrip('/')
        self.ver = kwargs.pop('version', None)

        if self.ver is not None:
            self.ver = utilities.versiontuple(self.ver)

        self.timezone = kwargs.pop('timezone', None)

        if self.timezone is not None and not isinstance(self.timezone, datetime.tzinfo):
            try:
                self.timezone = datetime.datetime.strptime(self.timezone, '%z').tzinfo
            except (TypeError, ValueError):
                raise exceptions.TimezoneError

        self.date_format = kwargs.pop('date_format', '%Y-%m-%d')
        self.datetime_format = kwargs.pop('datetime_format', '%Y-%m-%dT%H:%M:%SZ')
        self.raise_attr_exception = kwargs.pop('raise_attr_exception', True)

        self.engine_config = kwargs.pop('engine_config', engines.EngineConfig())
        engine_arg = kwargs.pop('engine', None)
        if engine_arg is None:
            engine_arg = self.engine_config.engine

        if isinstance(engine_arg, str):
            engine = engines.EngineType[engine_arg].get()
        else:
            engine = engine_arg

        if not inspect.isclass(engine) or not issubclass(engine, engines.BaseEngine):
            raise exceptions.EngineClassError

        self.engine = engine(**kwargs, config=self.engine_config)

    def __getattr__(self, resource_name):
        """
        Returns a ResourceManager object for the requested resource.

        :param string resource_name: (required). Resource name.
        """
        if resource_name.startswith('_'):
            raise AttributeError

        resource_name = ''.join(word[0].upper() + word[1:] for word in str(resource_name).split('_'))

        try:
            resource_class = resources.registry[resource_name]['class']
        except KeyError:
            raise exceptions.ResourceError

        if self.ver is not None and self.ver < resource_class.redmine_version:
            raise exceptions.ResourceVersionMismatchError

        return resource_class.manager_class(self, resource_class)

    @contextlib.contextmanager
    def session(self, **options):
        """
        Initiates a temporary session with a copy of the current engine but with new options.

        :param dict options: (optional). Engine's options for a session.
        """
        engine = self.engine
        self.engine = engine.__class__(
            requests=utilities.merge_dicts(engine.requests, options.pop('requests', {})), **options)

        try:
            yield self
        except exceptions.BaseRedmineError as e:
            raise e
        finally:
            self.engine = engine

    def upload(self, f, filename=None):
        """
        Uploads file from file path / file stream to Redmine and returns an assigned token.

        :param f: (required). File path / stream that will be uploaded.
        :type f: string or file-like object
        :param filename: (optional). Filename for the file that will be uploaded.
        """
        if self.ver is not None and self.ver < (1, 4, 0):
            raise exceptions.VersionMismatchError('File uploading')

        # There are myriads of file-like object implementations here and there and some of them don't have
        # a "read" method, which is wrong, but that's what we have, on the other hand it looks like all of
        # them implement a "close" method, that's why we check for it here. Also, we don't want to close the
        # stream ourselves as we have no idea of what the client is going to do with it afterwards, so we
        # leave the closing part to the client or to the garbage collector
        if hasattr(f, 'close'):
            try:
                c = f.read(0)
            except (AttributeError, TypeError):
                raise exceptions.FileObjectError

            # We need to send bytes over the socket, so in case a file-like object contains a unicode
            # object underneath, we need to convert it to bytes, otherwise we'll get an exception
            if isinstance(c, str):
                warnings.warn('File-like object contains unicode, hence an additional step is performed to convert '
                              'its content to bytes, please consider switching to bytes to eliminate this warning',
                              exceptions.PerformanceWarning)
                f = io.BytesIO(f.read().encode('utf-8'))

            stream = f
            close = False
        else:
            if not os.path.isfile(f) or os.path.getsize(f) == 0:
                raise exceptions.NoFileError

            if not filename:
                filename = os.path.basename(f)

            stream = open(f, 'rb')
            close = True

        url = f'{self.url}/uploads.json'
        headers = {'Content-Type': 'application/octet-stream'}
        params = {'filename': filename or ''}

        response = self.engine.request('post', url, params=params, data=stream, headers=headers)

        if close:
            stream.close()

        return response['upload']

    def download(self, url, savepath=None, filename=None, params=None):
        """
        Downloads file from Redmine and saves it to savepath or returns a response directly
        for maximum control over file processing.

        :param string url: (required). URL of the file that will be downloaded.
        :param string savepath: (optional). Path where to save the file.
        :param string filename: (optional). Name that will be used for the file.
        :param dict params: (optional). Params to send in the query string.
        """
        with self.session(requests={'stream': True}, return_raw_response=True):
            response = self.engine.request('get', url, params=params or {})

        # If a savepath wasn't provided we return a response directly
        # so a user can have maximum control over response data
        if savepath is None:
            return response

        from urllib.parse import urlsplit

        if filename is None:
            filename = urlsplit(url)[2].split('/')[-1]

            if not filename:
                raise exceptions.FileUrlError

        savepath = os.path.join(savepath, filename)

        with open(savepath, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        return savepath

    def auth(self):
        """
        Shortcut for the case if we just want to check if user provided valid auth credentials.
        """
        return self.user.get('current')

    def search(self, query, **options):
        """
        Interface to Redmine Search API

        :param string query: (required). What to search.
        :param dict options: (optional). Dictionary of search options.
        """
        if self.ver is not None and self.ver < (3, 0, 0):
            raise exceptions.VersionMismatchError('Search functionality')

        container_map, manager_map, results = {}, {}, {'unknown': {}}

        for resource in options.pop('resources', []):
            options[resource] = True

        options['q'] = query

        for name, details in resources.registry.items():
            if details['class'].search_hints is not None:
                container = details['class'].container_all or details['class'].container_filter

                for hint in details['class'].search_hints:
                    container_map[hint] = container

                manager_map[container] = getattr(self, name)

        raw_resources, _ = self.engine.bulk_request('get', f'{self.url}/search.json', 'results', **options)

        for resource in raw_resources:
            if resource['type'] in container_map:
                container = container_map[resource['type']]

                if container not in results:
                    results[container] = []

                results[container].append(resource)
            else:
                if resource['type'] not in results['unknown']:
                    results['unknown'][resource['type']] = []

                results['unknown'][resource['type']].append(resource)

            del resource['type']  # all resources are already sorted by type, so we don't need it

        if not results['unknown']:
            del results['unknown']

        for container in results:
            if container in manager_map:
                results[container] = manager_map[container].to_resource_set(results[container])

        return results or None
