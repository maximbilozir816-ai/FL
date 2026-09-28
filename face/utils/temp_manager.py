# face/utils/temp_manager.py
"""
Temporary file management with automatic cleanup.
Ensures no orphan files remain after processing.
"""

import os
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class UserTempDirectory:
    """Manages a user-scoped temporary directory with automatic cleanup."""

    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.base_dir = tempfile.mkdtemp(prefix=f"face_bot_{chat_id}_")
        logger.debug(f"Created temp directory for user {chat_id}: {self.base_dir}")

    def get_path(self, filename: str = "") -> str:
        """Get a path within the user's temp directory."""
        if filename:
            return os.path.join(self.base_dir, filename)
        return self.base_dir

    def cleanup(self):
        """Recursively delete the temp directory and all contents."""
        try:
            import shutil
            if os.path.exists(self.base_dir):
                shutil.rmtree(self.base_dir)
                logger.debug(f"Cleaned up temp directory for user {self.chat_id}: {self.base_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temp directory: {e}", exc_info=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


class TempFileManager:
    """Manages temporary files for all users."""

    def __init__(self):
        self._user_temps = {}

    def get_or_create(self, chat_id: int) -> UserTempDirectory:
        """Get or create temp directory for user."""
        if chat_id not in self._user_temps:
            self._user_temps[chat_id] = UserTempDirectory(chat_id)
        return self._user_temps[chat_id]

    def cleanup_user(self, chat_id: int):
        """Cleanup temp directory for a specific user."""
        if chat_id in self._user_temps:
            self._user_temps[chat_id].cleanup()
            del self._user_temps[chat_id]


# Global singleton
_temp_manager: Optional[TempFileManager] = None


def get_temp_manager() -> TempFileManager:
    """Get or create the global temp file manager."""
    global _temp_manager
    if _temp_manager is None:
        _temp_manager = TempFileManager()
    return _temp_manager