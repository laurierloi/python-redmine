"""
Defines engines for processing requests/responses to/from Redmine.
"""

from .config import EngineConfig
from .base import BaseEngine
from enum import Enum

class EngineType(Enum):
    sync = 'sync'
    gevent = 'gevent'
    default = 'sync'

    def get(self):
        if self.value == 'gevent':
            from .gevent import GeventEngine
            return GeventEngine
        elif self.value == 'sync':
            from .sync import SyncEngine
            return SyncEngine
        raise NotImplementedError(f'Engine {self.name} is not yet implemented')
