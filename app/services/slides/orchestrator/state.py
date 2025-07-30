"""State management for slide generation orchestration."""

from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging
import asyncio
import json
from enum import Enum
from pathlib import Path
import pickle

logger = logging.getLogger(__name__)


class StateChangeType(Enum):
    """Types of state changes."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    RESTORED = "restored"


@dataclass
class StateSnapshot:
    """Represents a state snapshot."""
    id: str
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateChange:
    """Represents a state change event."""
    timestamp: datetime
    change_type: StateChangeType
    key: str
    old_value: Any = None
    new_value: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateManager:
    """Manages orchestration state with persistence and recovery."""
    
    def __init__(
        self,
        persistence_dir: Optional[Path] = None,
        enable_persistence: bool = True,
        snapshot_interval: int = 10  # Number of changes before snapshot
    ):
        """Initialize the state manager."""
        self.state: Dict[str, Any] = {}
        self.persistence_dir = persistence_dir
        self.enable_persistence = enable_persistence
        self.snapshot_interval = snapshot_interval
        self._change_history: List[StateChange] = []
        self._snapshots: Dict[str, StateSnapshot] = {}
        self._change_count = 0
        self._listeners: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()
        self._cache: Dict[str, Any] = {}
        self._cache_enabled = True
        
        if self.persistence_dir and self.enable_persistence:
            self.persistence_dir.mkdir(parents=True, exist_ok=True)
            
    async def initialize(self):
        """Initialize state manager and restore state if available."""
        if self.enable_persistence and self.persistence_dir:
            await self._restore_state()
            
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from state."""
        # Check cache first
        if self._cache_enabled and key in self._cache:
            return self._cache[key]
            
        async with self._lock:
            value = self._navigate_nested_key(self.state, key, default)
            
            # Update cache
            if self._cache_enabled:
                self._cache[key] = value
                
            return value
            
    async def set(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None):
        """Set a value in state."""
        async with self._lock:
            old_value = self._navigate_nested_key(self.state, key)
            self._set_nested_key(self.state, key, value)
            
            # Clear cache for this key
            if key in self._cache:
                del self._cache[key]
                
            # Record change
            change = StateChange(
                timestamp=datetime.utcnow(),
                change_type=StateChangeType.UPDATED if old_value is not None else StateChangeType.CREATED,
                key=key,
                old_value=old_value,
                new_value=value,
                metadata=metadata or {}
            )
            
            self._change_history.append(change)
            self._change_count += 1
            
            # Notify listeners
            await self._notify_listeners(key, change)
            
            # Check if snapshot needed
            if self._change_count >= self.snapshot_interval:
                await self._create_snapshot()
                
            # Persist change
            if self.enable_persistence:
                await self._persist_change(change)
                
    async def delete(self, key: str):
        """Delete a value from state."""
        async with self._lock:
            old_value = self._navigate_nested_key(self.state, key)
            
            if old_value is not None:
                self._delete_nested_key(self.state, key)
                
                # Clear cache
                if key in self._cache:
                    del self._cache[key]
                    
                # Record change
                change = StateChange(
                    timestamp=datetime.utcnow(),
                    change_type=StateChangeType.DELETED,
                    key=key,
                    old_value=old_value
                )
                
                self._change_history.append(change)
                await self._notify_listeners(key, change)
                
    async def update(self, updates: Dict[str, Any]):
        """Batch update multiple values."""
        for key, value in updates.items():
            await self.set(key, value)
            
    async def get_all(self, prefix: Optional[str] = None) -> Dict[str, Any]:
        """Get all state values, optionally filtered by prefix."""
        async with self._lock:
            if not prefix:
                return self.state.copy()
                
            filtered = {}
            for key, value in self._flatten_dict(self.state).items():
                if key.startswith(prefix):
                    filtered[key] = value
                    
            return filtered
            
    def subscribe(self, pattern: str, callback: Callable):
        """Subscribe to state changes matching a pattern."""
        if pattern not in self._listeners:
            self._listeners[pattern] = []
            
        self._listeners[pattern].append(callback)
        
    def unsubscribe(self, pattern: str, callback: Callable):
        """Unsubscribe from state changes."""
        if pattern in self._listeners:
            self._listeners[pattern].remove(callback)
            
    async def create_snapshot(self, snapshot_id: Optional[str] = None) -> str:
        """Create a state snapshot."""
        async with self._lock:
            return await self._create_snapshot(snapshot_id)
            
    async def restore_snapshot(self, snapshot_id: str):
        """Restore state from a snapshot."""
        async with self._lock:
            if snapshot_id not in self._snapshots:
                raise ValueError(f"Snapshot {snapshot_id} not found")
                
            snapshot = self._snapshots[snapshot_id]
            self.state = snapshot.data.copy()
            
            # Clear cache
            self._cache.clear()
            
            # Record restoration
            change = StateChange(
                timestamp=datetime.utcnow(),
                change_type=StateChangeType.RESTORED,
                key="*",
                new_value=snapshot_id,
                metadata={"snapshot_timestamp": snapshot.timestamp.isoformat()}
            )
            
            self._change_history.append(change)
            
            # Notify all listeners
            await self._notify_listeners("*", change)
            
            logger.info(f"Restored state from snapshot {snapshot_id}")
            
    async def get_history(
        self,
        key: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[StateChange]:
        """Get state change history."""
        history = self._change_history
        
        if key:
            history = [c for c in history if c.key == key or c.key.startswith(f"{key}.")]
            
        if limit:
            history = history[-limit:]
            
        return history
        
    async def clear_cache(self):
        """Clear the state cache."""
        self._cache.clear()
        logger.info("State cache cleared")
        
    def enable_cache(self, enabled: bool = True):
        """Enable or disable caching."""
        self._cache_enabled = enabled
        if not enabled:
            self._cache.clear()
            
    async def export_state(self) -> Dict[str, Any]:
        """Export complete state for backup."""
        async with self._lock:
            return {
                "state": self.state.copy(),
                "metadata": {
                    "exported_at": datetime.utcnow().isoformat(),
                    "change_count": len(self._change_history),
                    "snapshot_count": len(self._snapshots)
                }
            }
            
    async def import_state(self, state_data: Dict[str, Any]):
        """Import state from backup."""
        async with self._lock:
            self.state = state_data.get("state", {}).copy()
            self._cache.clear()
            
            # Record import
            change = StateChange(
                timestamp=datetime.utcnow(),
                change_type=StateChangeType.RESTORED,
                key="*",
                metadata=state_data.get("metadata", {})
            )
            
            self._change_history.append(change)
            
    def _navigate_nested_key(self, data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Navigate nested dictionary using dot notation."""
        parts = key.split(".")
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
                
        return current
        
    def _set_nested_key(self, data: Dict[str, Any], key: str, value: Any):
        """Set value in nested dictionary using dot notation."""
        parts = key.split(".")
        current = data
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
            
        current[parts[-1]] = value
        
    def _delete_nested_key(self, data: Dict[str, Any], key: str):
        """Delete value from nested dictionary using dot notation."""
        parts = key.split(".")
        current = data
        
        for part in parts[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return
                
        if isinstance(current, dict) and parts[-1] in current:
            del current[parts[-1]]
            
    def _flatten_dict(self, data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested dictionary to dot notation keys."""
        flattened = {}
        
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                flattened.update(self._flatten_dict(value, full_key))
            else:
                flattened[full_key] = value
                
        return flattened
        
    async def _create_snapshot(self, snapshot_id: Optional[str] = None) -> str:
        """Create a state snapshot (internal)."""
        if not snapshot_id:
            snapshot_id = f"snapshot_{datetime.utcnow().timestamp()}"
            
        snapshot = StateSnapshot(
            id=snapshot_id,
            timestamp=datetime.utcnow(),
            data=self.state.copy(),
            metadata={
                "change_count": len(self._change_history),
                "state_size": len(str(self.state))
            }
        )
        
        self._snapshots[snapshot_id] = snapshot
        self._change_count = 0
        
        # Persist snapshot
        if self.enable_persistence:
            await self._persist_snapshot(snapshot)
            
        logger.info(f"Created snapshot {snapshot_id}")
        return snapshot_id
        
    async def _notify_listeners(self, key: str, change: StateChange):
        """Notify listeners of state changes."""
        for pattern, callbacks in self._listeners.items():
            if self._match_pattern(key, pattern):
                for callback in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(key, change)
                        else:
                            callback(key, change)
                    except Exception as e:
                        logger.error(f"Error in state listener: {e}")
                        
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern."""
        if pattern == "*":
            return True
        elif pattern.endswith("*"):
            prefix = pattern[:-1]
            return key.startswith(prefix)
        else:
            return key == pattern
            
    async def _persist_change(self, change: StateChange):
        """Persist a state change to disk."""
        if not self.persistence_dir:
            return
            
        try:
            change_file = self.persistence_dir / f"change_{change.timestamp.timestamp()}.json"
            
            change_data = {
                "timestamp": change.timestamp.isoformat(),
                "change_type": change.change_type.value,
                "key": change.key,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "metadata": change.metadata
            }
            
            with open(change_file, "w") as f:
                json.dump(change_data, f)
                
        except Exception as e:
            logger.error(f"Failed to persist change: {e}")
            
    async def _persist_snapshot(self, snapshot: StateSnapshot):
        """Persist a snapshot to disk."""
        if not self.persistence_dir:
            return
            
        try:
            snapshot_file = self.persistence_dir / f"{snapshot.id}.pkl"
            
            with open(snapshot_file, "wb") as f:
                pickle.dump(snapshot, f)
                
            # Also save as JSON for readability
            json_file = self.persistence_dir / f"{snapshot.id}.json"
            
            snapshot_data = {
                "id": snapshot.id,
                "timestamp": snapshot.timestamp.isoformat(),
                "data": snapshot.data,
                "metadata": snapshot.metadata
            }
            
            with open(json_file, "w") as f:
                json.dump(snapshot_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to persist snapshot: {e}")
            
    async def _restore_state(self):
        """Restore state from persistence."""
        if not self.persistence_dir or not self.persistence_dir.exists():
            return
            
        try:
            # Find latest snapshot
            snapshot_files = list(self.persistence_dir.glob("snapshot_*.pkl"))
            
            if snapshot_files:
                latest_snapshot = max(snapshot_files, key=lambda f: f.stat().st_mtime)
                
                with open(latest_snapshot, "rb") as f:
                    snapshot = pickle.load(f)
                    
                self.state = snapshot.data
                self._snapshots[snapshot.id] = snapshot
                
                logger.info(f"Restored state from snapshot {snapshot.id}")
                
            # Load recent changes
            change_files = sorted(self.persistence_dir.glob("change_*.json"))
            
            for change_file in change_files[-100:]:  # Load last 100 changes
                try:
                    with open(change_file, "r") as f:
                        change_data = json.load(f)
                        
                    change = StateChange(
                        timestamp=datetime.fromisoformat(change_data["timestamp"]),
                        change_type=StateChangeType(change_data["change_type"]),
                        key=change_data["key"],
                        old_value=change_data.get("old_value"),
                        new_value=change_data.get("new_value"),
                        metadata=change_data.get("metadata", {})
                    )
                    
                    self._change_history.append(change)
                    
                except Exception as e:
                    logger.warning(f"Failed to load change from {change_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to restore state: {e}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Get state manager statistics."""
        return {
            "state_size": len(str(self.state)),
            "cache_size": len(self._cache),
            "change_history_size": len(self._change_history),
            "snapshot_count": len(self._snapshots),
            "listener_count": sum(len(callbacks) for callbacks in self._listeners.values()),
            "cache_enabled": self._cache_enabled,
            "persistence_enabled": self.enable_persistence
        }