from abc import ABC, abstractmethod
from typing import List
from models import Contest, UserPerformance, ProblemTag

class BaseNotifier(ABC):
    @abstractmethod
    def send_upcoming_contests(self, contests: List[Contest]):
        """Send notification about upcoming contests."""
        pass
        
    @abstractmethod
    def send_performance_report(self, performances: List[UserPerformance], tags: List[ProblemTag]):
        """Send notification about user performance."""
        pass
