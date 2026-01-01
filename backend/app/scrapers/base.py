from abc import ABC, abstractmethod
from typing import Dict, List, Any
from datetime import datetime


class BaseScraper(ABC):
    """Base class for all scrapers"""

    @abstractmethod
    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """Scrape data from source"""
        pass

    @abstractmethod
    def parse(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse raw data into structured format"""
        pass

    async def run(self, **kwargs) -> List[Dict[str, Any]]:
        """Execute scrape and parse pipeline"""
        raw = await self.scrape(**kwargs)
        return self.parse(raw)
