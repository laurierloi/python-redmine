from dataclasses import dataclass

@dataclass
class EngineConfig:
    engine: str = 'gevent'
    retries: int = 3
    backoff_factor: float = 1
    pool_block: bool = True
    pool_connections: int = 30
    pool_maxsize: int = 10
    group_size: int = 4

    def __post_init__(self):
        self.retries = int(self.retries)
        self.backoff_factor = float(self.backoff_factor)
        self.pool_block = bool(self.pool_block)
        self.pool_connections = int(self.pool_connections)
        self.pool_maxsize = int(self.pool_maxsize)
        self.group_size = int(self.group_size)

    def retry_args(self):
        return {
            'total': self.retries,
            'backoff_factor': self.backoff_factor,
            'status_forcelist': [500, 502, 503, 504],
            'raise_on_redirect': True,
            'raise_on_status': True,
        }


    def adapter_args(self):
        return {
            'pool_block': self.pool_block,
            'pool_connections': self.pool_connections,
            'pool_maxsize': self.pool_maxsize
        }

    def grequests_map_args(self):
        return {
            'size': self.group_size
        }
