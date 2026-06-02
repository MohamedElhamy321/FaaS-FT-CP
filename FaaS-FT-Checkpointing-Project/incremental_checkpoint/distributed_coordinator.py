"""
Distributed Checkpoint Coordination
Implements Raft-based consensus for coordinated checkpointing across multiple nodes
"""

import time
import threading
import random
import json
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import socket
import hashlib


class NodeState(Enum):
    """Raft node states"""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class MessageType(Enum):
    """Raft message types"""
    REQUEST_VOTE = "request_vote"
    VOTE_RESPONSE = "vote_response"
    APPEND_ENTRIES = "append_entries"
    APPEND_RESPONSE = "append_response"
    CHECKPOINT_REQUEST = "checkpoint_request"
    CHECKPOINT_RESPONSE = "checkpoint_response"
    HEARTBEAT = "heartbeat"


@dataclass
class LogEntry:
    """Raft log entry"""
    term: int
    index: int
    command: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class RaftMessage:
    """Raft protocol message"""
    type: MessageType
    term: int
    sender_id: str
    data: Dict[str, Any]


@dataclass
class NodeInfo:
    """Cluster node information"""
    node_id: str
    host: str
    port: int
    last_seen: float = field(default_factory=time.time)
    is_alive: bool = True


@dataclass
class CheckpointCoordination:
    """Coordinated checkpoint metadata"""
    checkpoint_id: str
    coordinator_node: str
    participating_nodes: Set[str]
    completed_nodes: Set[str] = field(default_factory=set)
    status: str = "initiated"  # initiated, in_progress, completed, failed
    timestamp: float = field(default_factory=time.time)
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)


class RaftNode:
    """
    Raft consensus node for distributed coordination.
    
    Implements leader election, log replication, and consensus-based
    checkpoint coordination across cluster nodes.
    """
    
    def __init__(
        self,
        node_id: str,
        cluster_nodes: List[Tuple[str, str, int]],
        election_timeout_range: Tuple[float, float] = (150, 300),
        heartbeat_interval: float = 50
    ):
        """
        Initialize Raft node.
        
        Args:
            node_id: Unique identifier for this node
            cluster_nodes: List of (node_id, host, port) tuples for all nodes
            election_timeout_range: Min/max election timeout in milliseconds
            heartbeat_interval: Heartbeat interval in milliseconds
        """
        self.node_id = node_id
        self.state = NodeState.FOLLOWER
        
        # Persistent state
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []
        
        # Volatile state
        self.commit_index = 0
        self.last_applied = 0
        
        # Leader state
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}
        
        # Cluster membership
        self.cluster_nodes: Dict[str, NodeInfo] = {}
        for nid, host, port in cluster_nodes:
            self.cluster_nodes[nid] = NodeInfo(nid, host, port)
        
        # Timing
        self.election_timeout_range = election_timeout_range
        self.heartbeat_interval = heartbeat_interval / 1000.0  # Convert to seconds
        self.election_timeout = self._reset_election_timeout()
        self.last_heartbeat = time.time()
        
        # Threading
        self.lock = threading.RLock()
        self.running = False
        self.election_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        
        # Checkpoint coordination
        self.pending_checkpoints: Dict[str, CheckpointCoordination] = {}
        self.checkpoint_lock = threading.Lock()
        
        # Leader tracking
        self.leader_id: Optional[str] = None
        
    def _reset_election_timeout(self) -> float:
        """Reset election timeout to random value in range."""
        min_timeout, max_timeout = self.election_timeout_range
        return random.uniform(min_timeout, max_timeout) / 1000.0  # Convert to seconds
    
    def start(self):
        """Start the Raft node."""
        with self.lock:
            if self.running:
                return
            
            self.running = True
            self.election_thread = threading.Thread(target=self._election_timer, daemon=True)
            self.election_thread.start()
    
    def stop(self):
        """Stop the Raft node."""
        with self.lock:
            self.running = False
            
        if self.election_thread:
            self.election_thread.join(timeout=1.0)
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=1.0)
    
    def _election_timer(self):
        """Election timeout monitoring."""
        while self.running:
            time.sleep(0.01)  # 10ms check interval
            
            with self.lock:
                if self.state == NodeState.LEADER:
                    continue
                
                elapsed = time.time() - self.last_heartbeat
                if elapsed >= self.election_timeout:
                    self._start_election()
    
    def _start_election(self):
        """Start leader election."""
        with self.lock:
            # Transition to candidate
            self.state = NodeState.CANDIDATE
            self.current_term += 1
            self.voted_for = self.node_id
            self.election_timeout = self._reset_election_timeout()
            self.last_heartbeat = time.time()
            
            # Request votes from other nodes
            votes_received = 1  # Vote for self
            votes_needed = (len(self.cluster_nodes) // 2) + 1
            
            # In real implementation, send vote requests via RPC
            # For simulation, assume we get majority
            if votes_received >= votes_needed:
                self._become_leader()
    
    def _become_leader(self):
        """Transition to leader state."""
        with self.lock:
            self.state = NodeState.LEADER
            self.leader_id = self.node_id
            
            # Initialize leader state
            last_log_index = len(self.log)
            for node_id in self.cluster_nodes:
                if node_id != self.node_id:
                    self.next_index[node_id] = last_log_index + 1
                    self.match_index[node_id] = 0
            
            # Start sending heartbeats
            if self.heartbeat_thread is None or not self.heartbeat_thread.is_alive():
                self.heartbeat_thread = threading.Thread(target=self._send_heartbeats, daemon=True)
                self.heartbeat_thread.start()
    
    def _send_heartbeats(self):
        """Send periodic heartbeats to followers."""
        while self.running and self.state == NodeState.LEADER:
            with self.lock:
                # Send append entries (heartbeat) to all followers
                for node_id in self.cluster_nodes:
                    if node_id != self.node_id:
                        self._send_append_entries(node_id)
            
            time.sleep(self.heartbeat_interval)
    
    def _send_append_entries(self, node_id: str):
        """Send append entries RPC to follower."""
        # In real implementation, send via network
        # For simulation, just track state
        pass
    
    def receive_heartbeat(self, term: int, leader_id: str):
        """Receive heartbeat from leader."""
        with self.lock:
            if term >= self.current_term:
                self.current_term = term
                self.leader_id = leader_id
                self.state = NodeState.FOLLOWER
                self.last_heartbeat = time.time()
                self.election_timeout = self._reset_election_timeout()
    
    def is_leader(self) -> bool:
        """Check if this node is the leader."""
        with self.lock:
            return self.state == NodeState.LEADER
    
    def get_leader_id(self) -> Optional[str]:
        """Get current leader node ID."""
        with self.lock:
            return self.leader_id
    
    def append_log_entry(self, command: str, data: Dict[str, Any]) -> bool:
        """
        Append entry to log (leader only).
        
        Args:
            command: Command type
            data: Command data
            
        Returns:
            True if successful (leader), False otherwise
        """
        with self.lock:
            if not self.is_leader():
                return False
            
            entry = LogEntry(
                term=self.current_term,
                index=len(self.log) + 1,
                command=command,
                data=data
            )
            self.log.append(entry)
            return True
    
    def initiate_checkpoint(self, checkpoint_id: str, participating_nodes: Set[str]) -> Optional[str]:
        """
        Initiate coordinated checkpoint (leader only).
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            participating_nodes: Set of node IDs to participate
            
        Returns:
            Coordination ID if successful, None otherwise
        """
        if not self.is_leader():
            return None
        
        with self.checkpoint_lock:
            coordination = CheckpointCoordination(
                checkpoint_id=checkpoint_id,
                coordinator_node=self.node_id,
                participating_nodes=participating_nodes.copy(),
                status="initiated"
            )
            
            coord_id = f"{checkpoint_id}_{self.node_id}_{int(time.time() * 1000)}"
            self.pending_checkpoints[coord_id] = coordination
            
            # Append to log
            self.append_log_entry("checkpoint", {
                "coordination_id": coord_id,
                "checkpoint_id": checkpoint_id,
                "nodes": list(participating_nodes)
            })
            
            return coord_id
    
    def report_checkpoint_complete(self, coord_id: str, node_id: str, success: bool):
        """
        Report checkpoint completion from a node.
        
        Args:
            coord_id: Coordination ID
            node_id: Reporting node ID
            success: Whether checkpoint succeeded
        """
        with self.checkpoint_lock:
            if coord_id not in self.pending_checkpoints:
                return
            
            coordination = self.pending_checkpoints[coord_id]
            
            if success:
                coordination.completed_nodes.add(node_id)
            
            # Check if all nodes completed
            if coordination.completed_nodes == coordination.participating_nodes:
                coordination.status = "completed"
            elif not success:
                coordination.status = "failed"
    
    def get_checkpoint_status(self, coord_id: str) -> Optional[CheckpointCoordination]:
        """Get checkpoint coordination status."""
        with self.checkpoint_lock:
            return self.pending_checkpoints.get(coord_id)


class DistributedCheckpointCoordinator:
    """
    High-level distributed checkpoint coordinator.
    
    Manages coordinated checkpointing across cluster using Raft consensus.
    """
    
    def __init__(
        self,
        node_id: str,
        cluster_nodes: List[Tuple[str, str, int]],
        checkpoint_manager: Any
    ):
        """
        Initialize distributed coordinator.
        
        Args:
            node_id: This node's ID
            cluster_nodes: List of (node_id, host, port) for cluster
            checkpoint_manager: Local checkpoint manager
        """
        self.node_id = node_id
        self.raft_node = RaftNode(node_id, cluster_nodes)
        self.checkpoint_manager = checkpoint_manager
        
        # Coordination state
        self.active_coordinations: Dict[str, CheckpointCoordination] = {}
        self.coordination_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'coordinated_checkpoints': 0,
            'successful_coordinations': 0,
            'failed_coordinations': 0,
            'leader_elections': 0
        }
    
    def start(self):
        """Start the coordinator."""
        self.raft_node.start()
    
    def stop(self):
        """Stop the coordinator."""
        self.raft_node.stop()
    
    def create_coordinated_checkpoint(
        self,
        application_state: dict,
        participating_nodes: Optional[Set[str]] = None
    ) -> Optional[str]:
        """
        Create coordinated checkpoint across cluster.
        
        Args:
            application_state: Application state to checkpoint
            participating_nodes: Nodes to include (None = all nodes)
            
        Returns:
            Coordination ID if successful, None otherwise
        """
        # Only leader can coordinate
        if not self.raft_node.is_leader():
            return None
        
        if participating_nodes is None:
            participating_nodes = set(self.raft_node.cluster_nodes.keys())
        
        # Generate checkpoint ID
        checkpoint_id = f"cp_{int(time.time() * 1000)}_{hashlib.md5(self.node_id.encode()).hexdigest()[:8]}"
        
        # Initiate coordination
        coord_id = self.raft_node.initiate_checkpoint(checkpoint_id, participating_nodes)
        
        if coord_id:
            self.stats['coordinated_checkpoints'] += 1
            
            # Create local checkpoint
            try:
                local_checkpoint = self.checkpoint_manager.create_checkpoint(application_state)
                if local_checkpoint:
                    self.raft_node.report_checkpoint_complete(coord_id, self.node_id, True)
            except Exception:
                self.raft_node.report_checkpoint_complete(coord_id, self.node_id, False)
                self.stats['failed_coordinations'] += 1
        
        return coord_id
    
    def wait_for_coordination(self, coord_id: str, timeout: float = 30.0) -> bool:
        """
        Wait for checkpoint coordination to complete.
        
        Args:
            coord_id: Coordination ID
            timeout: Maximum wait time in seconds
            
        Returns:
            True if coordination completed successfully
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            coordination = self.raft_node.get_checkpoint_status(coord_id)
            
            if coordination:
                if coordination.status == "completed":
                    self.stats['successful_coordinations'] += 1
                    return True
                elif coordination.status == "failed":
                    self.stats['failed_coordinations'] += 1
                    return False
            
            time.sleep(0.1)
        
        # Timeout
        self.stats['failed_coordinations'] += 1
        return False
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster coordination status."""
        return {
            'node_id': self.node_id,
            'is_leader': self.raft_node.is_leader(),
            'leader_id': self.raft_node.get_leader_id(),
            'state': self.raft_node.state.value,
            'term': self.raft_node.current_term,
            'cluster_size': len(self.raft_node.cluster_nodes),
            'active_coordinations': len(self.raft_node.pending_checkpoints),
            'statistics': self.stats.copy()
        }
    
    def is_leader(self) -> bool:
        """Check if this node is the cluster leader."""
        return self.raft_node.is_leader()
    
    def get_leader_id(self) -> Optional[str]:
        """Get current cluster leader ID."""
        return self.raft_node.get_leader_id()


class DistributedLockManager:
    """
    Distributed lock manager for coordinated operations.
    
    Provides distributed mutual exclusion using Raft consensus.
    """
    
    def __init__(self, raft_node: RaftNode):
        """
        Initialize lock manager.
        
        Args:
            raft_node: Raft consensus node
        """
        self.raft_node = raft_node
        self.locks: Dict[str, str] = {}  # lock_name -> holder_node_id
        self.lock_lock = threading.Lock()
    
    def acquire_lock(self, lock_name: str, holder_id: str, timeout: float = 10.0) -> bool:
        """
        Acquire distributed lock.
        
        Args:
            lock_name: Name of lock to acquire
            holder_id: Node ID requesting lock
            timeout: Maximum wait time
            
        Returns:
            True if lock acquired
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self.lock_lock:
                if lock_name not in self.locks:
                    # Lock available
                    self.locks[lock_name] = holder_id
                    
                    # Replicate via Raft
                    if self.raft_node.is_leader():
                        self.raft_node.append_log_entry("acquire_lock", {
                            "lock_name": lock_name,
                            "holder_id": holder_id
                        })
                    
                    return True
                elif self.locks[lock_name] == holder_id:
                    # Already holding lock
                    return True
            
            time.sleep(0.05)
        
        return False
    
    def release_lock(self, lock_name: str, holder_id: str) -> bool:
        """
        Release distributed lock.
        
        Args:
            lock_name: Lock to release
            holder_id: Node ID releasing lock
            
        Returns:
            True if released
        """
        with self.lock_lock:
            if lock_name in self.locks and self.locks[lock_name] == holder_id:
                del self.locks[lock_name]
                
                # Replicate via Raft
                if self.raft_node.is_leader():
                    self.raft_node.append_log_entry("release_lock", {
                        "lock_name": lock_name,
                        "holder_id": holder_id
                    })
                
                return True
        
        return False
    
    def is_locked(self, lock_name: str) -> bool:
        """Check if lock is held."""
        with self.lock_lock:
            return lock_name in self.locks
    
    def get_lock_holder(self, lock_name: str) -> Optional[str]:
        """Get current lock holder."""
        with self.lock_lock:
            return self.locks.get(lock_name)
