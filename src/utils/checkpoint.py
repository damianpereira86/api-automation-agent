import inspect
import os
import shelve
from functools import wraps
from typing import Dict, Any, Optional

from src.utils.logger import Logger


class Checkpoint:
    DB_NAME = "checkpoints"

    def __init__(self, obj=None, tag: str = None, namespace: str = None):
        self.obj = obj
        self.tag = tag or (obj.__class__.__name__ if obj else "global")
        self.namespace = namespace or "default"
        self.logger = Logger.get_logger(__name__)

    def _get_checkpoint_key(self, tag=None):
        """Consistently generate the same key for the given object or tag."""
        return f"{self.namespace}_{tag or self.tag}"

    def save_last_namespace(self):
        """Save the last namespace in the shelve database."""
        with shelve.open(self.DB_NAME, writeback=True) as db:
            db["last_namespace"] = self.namespace

    def restore_last_namespace(self):
        """Restore the last used namespace from the database."""
        with shelve.open(self.DB_NAME) as db:
            self.namespace = db.get("last_namespace", "default")
            self.logger.info(f"🔄 Restored last namespace: {self.namespace}")

    def get_last_namespace(self):
        """Retrieve the last saved namespace."""
        with shelve.open(self.DB_NAME) as db:
            return db.get("last_namespace", "default")

    def save(self, tag: str = None, state: Any = None, skip_object=False):
        """Save function state and optionally object state."""
        frame = inspect.currentframe().f_back
        local_vars = frame.f_locals
        state = state or {var: local_vars[var] for var in local_vars if var != "self"}

        if not skip_object and self.obj:
            state["self"] = {attr: getattr(self.obj, attr) for attr in vars(self.obj)}

        key = self._get_checkpoint_key(tag)

        with shelve.open(self.DB_NAME, writeback=True) as db:
            db[key] = state
            db.sync()

        self.logger.info(f"✅ Checkpoint '{key}' saved.")

    def restore(self, tag=None, restore_object=False) -> Optional[Dict[str, Any]]:
        """Restore function and optionally object state."""
        if not os.path.exists(f"{self.DB_NAME}.db"):
            return None

        tag = tag or self.tag
        key = self._get_checkpoint_key(tag)

        with shelve.open(self.DB_NAME) as db:
            saved_data = db.get(key, None)
            if not saved_data:
                return None

            obj_state = saved_data.get("self", {})
            if restore_object and self.obj:
                for key, value in obj_state.items():
                    setattr(self.obj, key, value)
                self.logger.info(f"🔄 Restored object state: {obj_state}")

            function_state = {
                var: saved_data[var] for var in saved_data if var != "self"
            }
            return function_state

    @staticmethod
    def clear():
        """Clear all stored checkpoints."""
        if os.path.exists(f"{Checkpoint.DB_NAME}"):
            os.remove(f"{Checkpoint.DB_NAME}")
            Logger.get_logger(__name__).info("🗑️ Checkpoints cleared.")

    @staticmethod
    def checkpoint(tag=None):
        """Decorator to automatically checkpoint function results."""

        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                checkpoint_tag = tag or func.__name__
                checkpoint = self.checkpoint
                last_state = checkpoint.restore(tag=checkpoint_tag)
                if last_state and "result" in last_state:
                    self.logger.info(f"✅ Skipping {func.__name__}, already processed.")
                    return last_state["result"]

                try:
                    result = func(self, *args, **kwargs)
                    checkpoint.save(
                        tag=checkpoint_tag, state={"result": result}, skip_object=True
                    )
                    return result
                except Exception as e:
                    self.save_state()
                    Logger.get_logger(__name__).warning(
                        f"⚠️ Exception occurred: {e}, state saved."
                    )
                    raise

            return wrapper

        return decorator
