"""
Defines engines for processing requests/responses to/from Redmine.
"""

from .base import BaseEngine
from .gevent import GeventEngine
from .sync import SyncEngine

DefaultEngine = GeventEngine
