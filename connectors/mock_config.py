from .base import config_Source

class mock_config_source(config_Source):
    """A mock connector for testing. Initialized with a dict of resource_id -> blob bytes"""
    
    def __init__(self, samples: dict[str, bytes]):
        self.samples = samples
        
    def list_resources(self)-> list[str]:
        return list(self.samples.keys())
    
    def fetch_config(self, resource_id):
        return self.samples.get(resource_id, b"")