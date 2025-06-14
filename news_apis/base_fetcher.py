# news_apis/base_fetcher.py

class BaseNewsFetcher:
    def fetch(self, ticker, date):
        """
        Returns: List[dict] — each dict: {'headline': ..., 'date': ..., 'url': ..., 'source': ...}
        """
        raise NotImplementedError

    def get_remaining_quota(self):
        """Returns integer for available queries today."""
        raise NotImplementedError

    def log_query(self):
        """Call in each fetch to increment internal quota counter."""
        raise NotImplementedError

    def get_name(self):
        return self.__class__.__name__
