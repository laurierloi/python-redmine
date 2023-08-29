"""
Defines engines for processing requests/responses to/from Redmine.
"""

from .config import EngineConfig
from .base import BaseEngine
from .gevent import GeventEngine
from .sync import SyncEngine
from enum import Enum

class EngineType(Enum):
    sync = SyncEngine
    gevent = GeventEngine
    default = GeventEngine
