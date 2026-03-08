from abc import ABC, abstractmethod

class BaseHost(ABC):
    def __init__(self, url: str):
        self.url = url

    @abstractmethod
    def get_contests(self, relative_url: str):
        pass
