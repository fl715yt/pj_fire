# news_apis/base_fetcher.py

class BaseNewsFetcher:
    def fetch(self, ticker, date):
        """
        Abstract method to fetch news headlines for the given ticker and date.
        Returns: List[dict] — each dict: {'headline': ..., 'date': ..., 'url': ..., 'source': ...}
        """
        raise NotImplementedError

    def get_remaining_quota(self):
        """Returns the number of queries this fetcher can perform today."""
        raise NotImplementedError

    def log_query(self):
        """Should increment internal quota counter when a query is made."""
        raise NotImplementedError

    def get_name(self):
        """Returns the class/fetcher name (used for logging and tagging)."""
        return self.__class__.__name__
