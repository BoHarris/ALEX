from abc import ABC, abstractmethod

class config_Source(ABC):
    """ 
    Abstract interface for configuration sources.
    """
    @abstractmethod
    def list_resources(self) -> list[str]:
        """ Return a list of resources"""
        ...
        
    @abstractmethod
    def fetch_config(self, resource_id: str)-> bytes:
        """Fetch and return the raw configuration blob for a resource"""
        ...