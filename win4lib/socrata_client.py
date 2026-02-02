"""
Socrata API client for fetching WIN4 lottery data.
Includes chunked fetching, retries, and progress callbacks.
"""
import time
import requests
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime

from .config import config


class SocrataError(Exception):
    """Custom exception for Socrata API errors."""
    pass


class SocrataClient:
    """Client for interacting with Socrata Open Data API."""

    def __init__(
        self,
        domain: Optional[str] = None,
        dataset_id: Optional[str] = None,
        app_token: Optional[str] = None
    ):
        """
        Initialize Socrata client.

        Args:
            domain: Socrata domain (default from config)
            dataset_id: Dataset identifier (default from config)
            app_token: Optional app token for higher rate limits
        """
        self.domain = domain or config.api.domain
        self.dataset_id = dataset_id or config.api.dataset_id
        self.app_token = app_token
        self.base_url = f"https://{self.domain}/resource/{self.dataset_id}.json"
        self.metadata_url = f"https://{self.domain}/api/views/{self.dataset_id}.json"

    def _get_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {"Accept": "application/json"}
        if self.app_token:
            headers["X-App-Token"] = self.app_token
        return headers

    def get_metadata(self) -> Dict[str, Any]:
        """
        Fetch dataset metadata including row count and update timestamps.

        Returns:
            Dict with metadata including rowCount, dataUpdatedAt, etc.
        """
        try:
            response = requests.get(
                self.metadata_url,
                headers=self._get_headers(),
                timeout=config.api.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise SocrataError(f"Failed to fetch metadata: {e}")

    def get_estimated_count(self) -> int:
        """
        Get approximate record count from metadata.

        Returns:
            Estimated row count (fallback to 50000 if unavailable)
        """
        try:
            metadata = self.get_metadata()
            return metadata.get("rowCount", 50000)
        except Exception:
            return 50000  # Fallback estimate

    def get_freshness(self) -> Dict[str, str]:
        """
        Get dataset freshness information.

        Returns:
            Dict with dataUpdatedAt and rowsUpdatedAt timestamps
        """
        try:
            metadata = self.get_metadata()
            return {
                "data_updated": metadata.get("dataUpdatedAt", "Unknown"),
                "rows_updated": metadata.get("rowsUpdatedAt", "Unknown"),
                "metadata_updated": metadata.get("viewLastModified", "Unknown")
            }
        except Exception:
            return {
                "data_updated": "Unknown",
                "rows_updated": "Unknown",
                "metadata_updated": "Unknown"
            }

    def _fetch_chunk(
        self,
        offset: int,
        limit: int,
        order_by: str = "draw_date DESC"
    ) -> List[Dict[str, Any]]:
        """
        Fetch a single chunk of data with retry logic.

        Args:
            offset: Starting record offset
            limit: Maximum records to fetch
            order_by: Sort order

        Returns:
            List of records
        """
        params = {
            "$limit": limit,
            "$offset": offset,
            "$order": order_by
        }

        last_error = None
        for attempt in range(config.api.max_retries):
            try:
                response = requests.get(
                    self.base_url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=config.api.timeout
                )
                response.raise_for_status()
                return response.json()

            except requests.RequestException as e:
                last_error = e
                if attempt < config.api.max_retries - 1:
                    # Exponential backoff
                    sleep_time = config.api.retry_delay * (2 ** attempt)
                    time.sleep(sleep_time)

        raise SocrataError(f"Failed after {config.api.max_retries} attempts: {last_error}")

    def fetch_all(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        chunk_size: Optional[int] = None,
        order_by: str = "draw_date DESC"
    ) -> List[Dict[str, Any]]:
        """
        Fetch all records with optional progress callback.

        Args:
            progress_callback: Function(current_count, estimated_total) for progress updates
            chunk_size: Records per request (default from config)
            order_by: Sort order for results

        Returns:
            List of all records
        """
        chunk_size = chunk_size or config.api.chunk_size
        all_records = []
        offset = 0
        estimated_total = self.get_estimated_count()

        while True:
            chunk = self._fetch_chunk(offset, chunk_size, order_by)

            if not chunk:
                break

            all_records.extend(chunk)
            offset += len(chunk)

            if progress_callback:
                progress_callback(len(all_records), estimated_total)

            # If we got fewer records than requested, we've reached the end
            if len(chunk) < chunk_size:
                break

        return all_records

    def fetch_recent(
        self,
        days: int = 30,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch only recent records (more efficient for quick loads).

        Args:
            days: Number of days of data to fetch
            progress_callback: Optional progress callback

        Returns:
            List of recent records
        """
        from datetime import datetime, timedelta

        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        all_records = []
        offset = 0
        chunk_size = config.api.chunk_size

        # Estimate based on ~2 draws per day
        estimated_total = days * 2

        while True:
            params = {
                "$limit": chunk_size,
                "$offset": offset,
                "$order": "draw_date DESC",
                "$where": f"draw_date >= '{cutoff_date}'"
            }

            try:
                response = requests.get(
                    self.base_url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=config.api.timeout
                )
                response.raise_for_status()
                chunk = response.json()
            except requests.RequestException as e:
                raise SocrataError(f"Failed to fetch recent data: {e}")

            if not chunk:
                break

            all_records.extend(chunk)
            offset += len(chunk)

            if progress_callback:
                progress_callback(len(all_records), estimated_total)

            if len(chunk) < chunk_size:
                break

        return all_records
