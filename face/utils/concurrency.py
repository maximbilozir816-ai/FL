# face/utils/concurrency.py
"""
Concurrency management for high-load facial analysis bot.
Features:
  - Per-user asyncio.Lock to prevent concurrent photo processing
  - Media group deduplication to prevent processing the same album twice
  - Bounded PDF rendering via ThreadPoolExecutor (no pickling issues)
"""

import asyncio
import logging
from typing import Dict
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class UserProcessingState:
    """Track a user's processing status and media group history."""
    chat_id: int
    is_processing: bool = False
    current_message_id: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    recent_media_groups: Dict[str, datetime] = field(default_factory=dict)

    async def cleanup_old_media_groups(self, ttl_seconds: int = 30):
        """Remove media group IDs older than TTL."""
        now = datetime.utcnow()
        expired = [
            key for key, timestamp in self.recent_media_groups.items()
            if (now - timestamp).total_seconds() > ttl_seconds
        ]
        for key in expired:
            del self.recent_media_groups[key]


class UserConcurrencyManager:
    """
    Manages per-user processing state and media group deduplication.
    Prevents:
      1. Simultaneous photo processing for the same user
      2. Processing duplicate photos from the same media group
    """

    def __init__(self):
        self._user_states: Dict[int, UserProcessingState] = {}

    async def get_or_create_state(self, chat_id: int) -> UserProcessingState:
        """Get or create the processing state for a user."""
        if chat_id not in self._user_states:
            self._user_states[chat_id] = UserProcessingState(chat_id=chat_id)
        return self._user_states[chat_id]

    async def is_media_group_duplicate(
        self, chat_id: int, media_group_id: str
    ) -> bool:
        """
        Check if a media group ID has been recently processed.
        Returns True if duplicate, False if first occurrence.
        """
        state = await self.get_or_create_state(chat_id)
        await state.cleanup_old_media_groups(ttl_seconds=30)

        if media_group_id in state.recent_media_groups:
            return True

        state.recent_media_groups[media_group_id] = datetime.utcnow()
        return False

    async def acquire_user_lock(self, chat_id: int, wait_in_queue: bool = False):
        """Acquire the lock for a user."""
        state = await self.get_or_create_state(chat_id)
        return UserLockContext(state, wait_in_queue=wait_in_queue)

    async def cleanup_user_state(self, chat_id: int):
        """Manually cleanup a user's processing state (e.g., on error recovery)."""
        if chat_id in self._user_states:
            state = self._user_states[chat_id]
            state.is_processing = False
            logger.debug(f"Cleaned up processing state for user {chat_id}")


class UserLockContext:
    """Context manager for user lock acquisition with timeout or queueing."""

    def __init__(self, state: UserProcessingState, wait_in_queue: bool = False):
        self.state = state
        self.wait_in_queue = wait_in_queue
        self.acquired = False

    async def __aenter__(self):
        try:
            if self.wait_in_queue:
                await self.state.lock.acquire()
                self.acquired = True
                self.state.is_processing = True
                return True
            else:
                await asyncio.wait_for(self.state.lock.acquire(), timeout=1.0)
                self.acquired = True
                self.state.is_processing = True
                return True
        except asyncio.TimeoutError:
            logger.warning(f"Could not acquire lock for user {self.state.chat_id}")
            return False

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            self.state.is_processing = False
            self.state.lock.release()
        return False


class BoundedWeasyPrintExecutor:
    """
    Manages WeasyPrint PDF generation with a bounded thread pool.
    Uses ThreadPoolExecutor (not ProcessPoolExecutor) to avoid pickling issues.
    Prevents resource exhaustion from concurrent PDF renders.
    """

    def __init__(self, max_workers: int = 2):
        """
        Initialize the executor.
        Args:
            max_workers: Number of concurrent PDF generation workers (2-4 recommended).
        """
        self.max_workers = max(1, min(max_workers, 4))
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="weasyprint_")
        self._semaphore = asyncio.Semaphore(self.max_workers)
        logger.info(f"BoundedWeasyPrintExecutor initialized with {self.max_workers} workers (ThreadPoolExecutor)")

    async def render_pdf_async(self, render_func, *args, **kwargs) -> bytes:
        """
        Render PDF asynchronously with bounded concurrency.
        Args:
            render_func: Sync function that returns PDF bytes (e.g., PDFReportBuilder.build)
            *args, **kwargs: Arguments to pass to render_func
        Returns:
            PDF bytes
        """
        async with self._semaphore:
            loop = asyncio.get_event_loop()
            try:
                wrapped_func = partial(render_func, *args, **kwargs)
                pdf_bytes = await loop.run_in_executor(
                    self._executor, 
                    wrapped_func
                )
                logger.debug("PDF successfully rendered within bounded executor")
                return pdf_bytes
            except Exception as e:
                logger.error(f"PDF rendering failed: {e}", exc_info=True)
                raise

    def shutdown(self):
        """Gracefully shutdown the executor."""
        self._executor.shutdown(wait=True)
        logger.info("BoundedWeasyPrintExecutor shut down")


# Global singletons
_user_concurrency_manager: UserConcurrencyManager = None
_pdf_executor: BoundedWeasyPrintExecutor = None


def get_user_concurrency_manager() -> UserConcurrencyManager:
    """Get or create the global user concurrency manager."""
    global _user_concurrency_manager
    if _user_concurrency_manager is None:
        _user_concurrency_manager = UserConcurrencyManager()
    return _user_concurrency_manager


def get_pdf_executor() -> BoundedWeasyPrintExecutor:
    """Get or create the global PDF executor."""
    global _pdf_executor
    if _pdf_executor is None:
        _pdf_executor = BoundedWeasyPrintExecutor(max_workers=2)
    return _pdf_executor


def shutdown_executors():
    """Shutdown all executors (call on bot shutdown)."""
    global _pdf_executor
    if _pdf_executor:
        _pdf_executor.shutdown()