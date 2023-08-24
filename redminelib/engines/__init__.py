"""
Defines engines for processing requests/responses to/from Redmine.
"""

from .base import BaseEngine
from .sync import SyncEngine
from .gevent import GeventEngine

DefaultEngine = GeventEngine
