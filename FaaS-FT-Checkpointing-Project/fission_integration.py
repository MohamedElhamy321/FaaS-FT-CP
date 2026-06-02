"""
Fission Function Integration with Incremental Checkpoint System
Provides automatic checkpointing for Fission serverless functions
"""

import os
import json
import time
from typing import Dict, Any, Optional
from flask import request, Response
import requests

# Import checkpoint system
import sys
sys.path.insert(0, '/app')
from incremental_checkpoint import ProductionCheckpointManager

# Initialize checkpoint manager
CHECKPOINT_DIR = os.environ.get('CHECKPOINT_DIR', '/tmp/fission-checkpoints')
checkpoint_manager = ProductionCheckpointManager(
    storage_path=CHECKPOINT_DIR,
    enable_monitoring=True,
    enable_optimizations=True
)

# Checkpoint service URL (if using centralized service)
CHECKPOINT_SERVICE_URL = os.environ.get('CHECKPOINT_SERVICE_URL', 
                                       'http://checkpoint-manager.checkpoint-system.svc.cluster.local:8080')

class FissionCheckpointWrapper:
    """
    Wrapper for Fission functions to add automatic checkpointing
    """
    
    def __init__(self, func, checkpoint_interval: int = 10):
        """
        Initialize wrapper
        
        Args:
            func: The Fission function to wrap
            checkpoint_interval: Create full checkpoint every N invocations
        """
        self.func = func
        self.checkpoint_interval = checkpoint_interval
        self.invocation_count = 0
        self.state = {}
        self.last_checkpoint_id = None
        
    def __call__(self, *args, **kwargs):
        """Execute function with automatic checkpointing"""
        self.invocation_count += 1
        
        # Load checkpoint if recovering
        if self.invocation_count == 1 and self.last_checkpoint_id is None:
            self._try_recover()
        
        # Execute function
        try:
            result = self.func(self.state, *args, **kwargs)
            
            # Create checkpoint
            if self.invocation_count % self.checkpoint_interval == 0:
                self._create_checkpoint()
            
            return result
        except Exception as e:
            # On error, try to recover from last checkpoint
            print(f"Error in function execution: {e}")
            if self._try_recover():
                # Retry after recovery
                result = self.func(self.state, *args, **kwargs)
                return result
            raise
    
    def _create_checkpoint(self):
        """Create checkpoint of current state"""
        try:
            checkpoint = checkpoint_manager.create_checkpoint(self.state)
            self.last_checkpoint_id = checkpoint.checkpoint_id
            print(f"Checkpoint created: {checkpoint.checkpoint_id} ({'FULL' if checkpoint.is_full else 'INCR'})")
        except Exception as e:
            print(f"Warning: Checkpoint creation failed: {e}")
    
    def _try_recover(self) -> bool:
        """Try to recover from last checkpoint"""
        try:
            checkpoints = checkpoint_manager.list_checkpoints()
            if checkpoints:
                latest = checkpoints[-1]
                restored_state = checkpoint_manager.restore_checkpoint(latest['checkpoint_id'])
                self.state = restored_state
                self.last_checkpoint_id = latest['checkpoint_id']
                print(f"Recovered from checkpoint: {latest['checkpoint_id']}")
                return True
        except Exception as e:
            print(f"Recovery failed: {e}")
        return False


def checkpoint_decorator(checkpoint_interval: int = 10):
    """
    Decorator to add automatic checkpointing to Fission functions
    
    Usage:
        @checkpoint_decorator(checkpoint_interval=10)
        def my_function(state, context):
            # Function code
            state['counter'] = state.get('counter', 0) + 1
            return {"counter": state['counter']}
    """
    def decorator(func):
        wrapper = FissionCheckpointWrapper(func, checkpoint_interval)
        return wrapper
    return decorator


# Example Fission function with checkpointing
@checkpoint_decorator(checkpoint_interval=5)
def fibonacci_with_checkpoint(state, context):
    """
    Fibonacci calculator with automatic checkpointing
    
    Maintains state across invocations and recovers from failures
    """
    # Get request body
    body = request.get_json()
    n = body.get('n', 10) if body else 10
    
    # Initialize or update state
    if 'cache' not in state:
        state['cache'] = {0: 0, 1: 1}
        state['invocations'] = 0
        state['total_computed'] = 0
    
    state['invocations'] += 1
    
    # Compute Fibonacci using cached values
    cache = state['cache']
    
    def fib(num):
        if num in cache:
            return cache[num]
        cache[num] = fib(num - 1) + fib(num - 2)
        return cache[num]
    
    result = fib(n)
    state['total_computed'] += 1
    
    return {
        "n": n,
        "fibonacci": result,
        "invocations": state['invocations'],
        "cache_size": len(state['cache']),
        "total_computed": state['total_computed']
    }


# Example stateful counter function
@checkpoint_decorator(checkpoint_interval=10)
def stateful_counter(state, context):
    """
    Stateful counter with automatic checkpointing
    """
    # Initialize state
    if 'counter' not in state:
        state['counter'] = 0
        state['history'] = []
    
    # Increment counter
    state['counter'] += 1
    state['history'].append({
        'count': state['counter'],
        'timestamp': time.time()
    })
    
    # Keep only last 100 entries
    if len(state['history']) > 100:
        state['history'] = state['history'][-100:]
    
    return {
        "counter": state['counter'],
        "history_size": len(state['history'])
    }


# Direct API endpoints for checkpoint management
def checkpoint_create_endpoint(context):
    """
    Fission endpoint to create checkpoint manually
    
    POST /checkpoint
    Body: {"state": {...}}
    """
    body = request.get_json()
    state = body.get('state', {})
    
    try:
        checkpoint = checkpoint_manager.create_checkpoint(state)
        return {
            "checkpoint_id": checkpoint.checkpoint_id,
            "is_full": checkpoint.is_full,
            "timestamp": checkpoint.timestamp
        }
    except Exception as e:
        return {"error": str(e)}, 500


def checkpoint_restore_endpoint(context):
    """
    Fission endpoint to restore from checkpoint
    
    GET /checkpoint/<id>
    """
    checkpoint_id = request.args.get('id')
    if not checkpoint_id:
        return {"error": "checkpoint_id required"}, 400
    
    try:
        checkpoint_id = int(checkpoint_id)
        state = checkpoint_manager.restore_checkpoint(checkpoint_id)
        return {"state": state, "checkpoint_id": checkpoint_id}
    except Exception as e:
        return {"error": str(e)}, 500


def checkpoint_list_endpoint(context):
    """
    Fission endpoint to list checkpoints
    
    GET /checkpoints
    """
    try:
        checkpoints = checkpoint_manager.list_checkpoints()
        return {"checkpoints": checkpoints}
    except Exception as e:
        return {"error": str(e)}, 500


# Health check for Fission
def health_check(context):
    """Health check endpoint for Fission function"""
    return {
        "status": "healthy",
        "checkpoint_service": "available",
        "checkpoint_dir": CHECKPOINT_DIR
    }


# Example: Integration with existing Fission function
def wrap_existing_function(existing_func, checkpoint_interval: int = 10):
    """
    Wrap an existing Fission function with checkpointing
    
    Args:
        existing_func: Existing Fission function
        checkpoint_interval: Checkpoint every N invocations
    
    Returns:
        Wrapped function with checkpointing
    """
    wrapper = FissionCheckpointWrapper(existing_func, checkpoint_interval)
    return wrapper


if __name__ == "__main__":
    # For local testing
    print("Fission Checkpoint Integration Module")
    print("Functions available:")
    print("  - fibonacci_with_checkpoint")
    print("  - stateful_counter")
    print("  - checkpoint_create_endpoint")
    print("  - checkpoint_restore_endpoint")
    print("  - checkpoint_list_endpoint")
    print("  - health_check")
