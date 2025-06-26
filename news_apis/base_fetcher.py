# news_apis/base_fetcher.py

class BaseNewsFetcher:
    def fetch(self, ticker, date):
        """
        Abstract method to fetch news headlines for the given ticker and date.
        Returns: List[dict] — each dict: {'headline': ..., 'date': ..., 'url': ..., 'source': ...}
        """
        raise NotImplementedError

    def get_name(self):
        """
        Returns the class/fetcher name (used for logging and tagging).
        """
        return self.__class__.__name__
