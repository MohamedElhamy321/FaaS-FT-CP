"""
State Change Tracker
Detects and tracks changes in application state between checkpoints
"""

import hashlib
import time
from typing import Dict, Set, List, Any, Optional


class StateChangeTracker:
    """
    Tracks changes to application state between checkpoints.
    
    Uses hash-based comparison to efficiently identify modified, added,
    and deleted state keys without storing full state copies.
    
    Example:
        tracker = StateChangeTracker()
        
        # First checkpoint
        state1 = {'counter': 0, 'data': 'hello'}
        tracker.update_baseline(state1)
        
        # Second checkpoint - detect changes
        state2 = {'counter': 5, 'data': 'hello', 'new_key': 'world'}
        changes = tracker.track_changes(state2)
        # Returns: {'counter': 5, 'new_key': 'world'}
    """
    
    def __init__(self):
        """Initialize the state change tracker."""
        self.previous_state_hash: Dict[str, str] = {}
        self.changed_keys: Set[str] = set()
        self.change_log: List[Dict[str, Any]] = []
        self.baseline_timestamp: Optional[float] = None
        
    def track_changes(self, current_state: dict) -> dict:
        """
        Compare current state with previous baseline and identify changes.
        
        Args:
            current_state: Dictionary representing current application state
            
        Returns:
            Dictionary containing only the changed key-value pairs
            
        Example:
            >>> tracker = StateChangeTracker()
            >>> tracker.update_baseline({'x': 1, 'y': 2})
            >>> changes = tracker.track_changes({'x': 1, 'y': 3, 'z': 4})
            >>> changes
            {'y': 3, 'z': 4}
        """
        changes = {}
        current_timestamp = time.time()
        
        # Track modified and new keys
        for key, value in current_state.items():
            current_hash = self._calculate_hash(value)
            previous_hash = self.previous_state_hash.get(key)
            
            if current_hash != previous_hash:
                changes[key] = value
                self.changed_keys.add(key)
                
                # Log the change
                self.change_log.append({
                    'key': key,
                    'timestamp': current_timestamp,
                    'size_bytes': self._estimate_size(value),
                    'type': 'modified' if previous_hash else 'added'
                })
        
        # Track deleted keys
        deleted_keys = set(self.previous_state_hash.keys()) - set(current_state.keys())
        for key in deleted_keys:
            # Mark deletion with special prefix
            changes[f"__deleted_{key}"] = None
            self.changed_keys.add(key)
            
            self.change_log.append({
                'key': key,
                'timestamp': current_timestamp,
                'size_bytes': 0,
                'type': 'deleted'
            })
        
        return changes
    
    def update_baseline(self, state: dict) -> None:
        """
        Update the baseline state for next comparison.
        
        Args:
            state: Dictionary representing the new baseline state
            
        Example:
            >>> tracker = StateChangeTracker()
            >>> tracker.update_baseline({'counter': 10, 'name': 'test'})
        """
        self.previous_state_hash = {
            key: self._calculate_hash(value) 
            for key, value in state.items()
        }
        self.baseline_timestamp = time.time()
        
    def _calculate_hash(self, value: Any) -> str:
        """
        Calculate hash for a value to detect changes.
        
        Uses MD5 for speed. For production with security requirements,
        consider SHA-256.
        
        Args:
            value: Any Python object
            
        Returns:
            Hexadecimal hash string
        """
        # Convert value to string representation for hashing
        value_str = str(value)
        
        # Handle large values efficiently
        if len(value_str) > 10000:
            # For large values, sample beginning, middle, and end
            value_str = value_str[:3000] + value_str[len(value_str)//2:len(value_str)//2+3000] + value_str[-3000:]
        
        return hashlib.md5(value_str.encode('utf-8')).hexdigest()
    
    def _estimate_size(self, value: Any) -> int:
        """
        Estimate the size of a value in bytes.
        
        Args:
            value: Any Python object
            
        Returns:
            Estimated size in bytes
        """
        import sys
        
        try:
            # Try to get actual size
            return sys.getsizeof(value)
        except:
            # Fallback to string length estimation
            return len(str(value))
    
    def get_change_statistics(self) -> dict:
        """
        Get statistics about state changes since tracking began.
        
        Returns:
            Dictionary with statistics:
            - total_changes: Total number of changes logged
            - unique_keys_changed: Number of unique keys modified
            - change_rate: Changes per second (if baseline set)
            - changes_by_type: Breakdown by change type
            - total_size_changed: Total bytes changed
            
        Example:
            >>> stats = tracker.get_change_statistics()
            >>> print(f"Total changes: {stats['total_changes']}")
        """
        # Calculate time elapsed
        time_elapsed = 0
        if self.baseline_timestamp:
            time_elapsed = time.time() - self.baseline_timestamp
        
        # Group changes by type
        changes_by_type = {'added': 0, 'modified': 0, 'deleted': 0}
        total_size = 0
        
        for change in self.change_log:
            change_type = change.get('type', 'unknown')
            changes_by_type[change_type] = changes_by_type.get(change_type, 0) + 1
            total_size += change.get('size_bytes', 0)
        
        return {
            'total_changes': len(self.change_log),
            'unique_keys_changed': len(self.changed_keys),
            'change_rate': len(self.change_log) / max(1, time_elapsed),
            'changes_by_type': changes_by_type,
            'total_size_changed_bytes': total_size,
            'time_elapsed_seconds': time_elapsed
        }
    
    def reset(self) -> None:
        """
        Reset the tracker to initial state.
        
        Clears all tracked changes and baseline state.
        """
        self.previous_state_hash.clear()
        self.changed_keys.clear()
        self.change_log.clear()
        self.baseline_timestamp = None
    
    def get_changed_keys(self) -> Set[str]:
        """
        Get the set of all keys that have changed.
        
        Returns:
            Set of key names that have been modified, added, or deleted
        """
        return self.changed_keys.copy()
    
    def has_changes(self, state: dict) -> bool:
        """
        Check if state has changes without tracking them.
        
        Args:
            state: Dictionary to check for changes
            
        Returns:
            True if state differs from baseline, False otherwise
        """
        if not self.previous_state_hash:
            return True  # No baseline, consider it changed
        
        # Quick check: different number of keys
        if len(state) != len(self.previous_state_hash):
            return True
        
        # Check if any values changed
        for key, value in state.items():
            current_hash = self._calculate_hash(value)
            previous_hash = self.previous_state_hash.get(key)
            
            if current_hash != previous_hash:
                return True
        
        return False
