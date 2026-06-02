"""
Advanced Compression & Deduplication Manager for Checkpoints

Provides:
- Multiple compression algorithms (LZ4, Zstd, gzip)
- Intelligent algorithm selection based on content type
- Content-based deduplication using hash storage
- Compression statistics and monitoring
- Transparent integration with checkpoint system
"""

import zlib
import hashlib
import json
import time
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any
from pathlib import Path

try:
    import lz4.frame
    LZ4_AVAILABLE = True
except ImportError:
    LZ4_AVAILABLE = False

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False


class CompressionAlgorithm(Enum):
    """Supported compression algorithms"""
    NONE = "none"
    GZIP = "gzip"       # Built-in, good balance
    LZ4 = "lz4"         # Fast compression, moderate ratio
    ZSTD = "zstd"       # Best ratio, good speed
    

class ContentType(Enum):
    """Content type for intelligent algorithm selection"""
    BINARY = "binary"           # Generic binary data
    TEXT = "text"               # Text/JSON data
    NUMERIC = "numeric"         # Numeric arrays
    ALREADY_COMPRESSED = "compressed"  # Already compressed (images, etc)


@dataclass
class CompressionResult:
    """Result of compression operation"""
    compressed_data: bytes
    original_size: int
    compressed_size: int
    compression_ratio: float
    algorithm: CompressionAlgorithm
    compression_time_ms: float
    is_deduplicated: bool = False
    content_hash: Optional[str] = None
    
    @property
    def space_saved(self) -> int:
        """Bytes saved by compression"""
        return self.original_size - self.compressed_size
    
    @property
    def space_saved_percent(self) -> float:
        """Percentage of space saved"""
        if self.original_size == 0:
            return 0.0
        return (self.space_saved / self.original_size) * 100


@dataclass
class DecompressionResult:
    """Result of decompression operation"""
    data: bytes
    original_size: int
    compressed_size: int
    decompression_time_ms: float
    algorithm: CompressionAlgorithm
    was_deduplicated: bool = False


@dataclass
class CompressionStats:
    """Compression statistics"""
    total_compressions: int = 0
    total_decompressions: int = 0
    total_original_bytes: int = 0
    total_compressed_bytes: int = 0
    total_compression_time_ms: float = 0.0
    total_decompression_time_ms: float = 0.0
    deduplication_hits: int = 0
    deduplication_misses: int = 0
    algorithm_usage: Dict[str, int] = field(default_factory=dict)
    
    @property
    def avg_compression_ratio(self) -> float:
        """Average compression ratio"""
        if self.total_original_bytes == 0:
            return 1.0
        return self.total_compressed_bytes / self.total_original_bytes
    
    @property
    def avg_compression_time_ms(self) -> float:
        """Average compression time"""
        if self.total_compressions == 0:
            return 0.0
        return self.total_compression_time_ms / self.total_compressions
    
    @property
    def avg_decompression_time_ms(self) -> float:
        """Average decompression time"""
        if self.total_decompressions == 0:
            return 0.0
        return self.total_decompression_time_ms / self.total_decompressions
    
    @property
    def total_space_saved(self) -> int:
        """Total bytes saved"""
        return self.total_original_bytes - self.total_compressed_bytes
    
    @property
    def space_saved_percent(self) -> float:
        """Percentage of space saved"""
        if self.total_original_bytes == 0:
            return 0.0
        return (self.total_space_saved / self.total_original_bytes) * 100
    
    @property
    def deduplication_hit_rate(self) -> float:
        """Percentage of deduplication hits"""
        total = self.deduplication_hits + self.deduplication_misses
        if total == 0:
            return 0.0
        return (self.deduplication_hits / total) * 100


class CompressionManager:
    """
    Advanced compression manager with multiple algorithms and deduplication
    
    Features:
    - Automatic algorithm selection based on content
    - Content-based deduplication using SHA-256 hashes
    - Compression statistics and monitoring
    - Thread-safe operations
    - Configurable compression levels
    """
    
    def __init__(self,
                 storage_path: Optional[str] = None,
                 enable_deduplication: bool = True,
                 default_algorithm: CompressionAlgorithm = CompressionAlgorithm.ZSTD,
                 compression_level: int = 3):
        """
        Initialize compression manager
        
        Args:
            storage_path: Path for deduplication storage (None = in-memory only)
            enable_deduplication: Enable content-based deduplication
            default_algorithm: Default compression algorithm
            compression_level: Compression level (1-22 for zstd, 1-9 for others)
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self.enable_deduplication = enable_deduplication
        self.compression_level = compression_level
        
        # Set default algorithm based on availability
        if default_algorithm == CompressionAlgorithm.ZSTD and not ZSTD_AVAILABLE:
            default_algorithm = CompressionAlgorithm.LZ4 if LZ4_AVAILABLE else CompressionAlgorithm.GZIP
        elif default_algorithm == CompressionAlgorithm.LZ4 and not LZ4_AVAILABLE:
            default_algorithm = CompressionAlgorithm.ZSTD if ZSTD_AVAILABLE else CompressionAlgorithm.GZIP
        
        self.default_algorithm = default_algorithm
        
        # Deduplication cache: hash -> (compressed_data, metadata)
        self._dedup_cache: Dict[str, Tuple[bytes, Dict[str, Any]]] = {}
        self._cache_lock = threading.Lock()
        
        # Statistics
        self._stats = CompressionStats()
        self._stats_lock = threading.Lock()
        
        # Initialize storage
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._dedup_dir = self.storage_path / "dedup"
            self._dedup_dir.mkdir(exist_ok=True)
            self._load_dedup_index()
    
    def _load_dedup_index(self):
        """Load deduplication index from disk"""
        index_file = self.storage_path / "dedup_index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    index = json.load(f)
                    # Load metadata only, data loaded on demand
                    for hash_key, metadata in index.items():
                        self._dedup_cache[hash_key] = (None, metadata)
            except Exception:
                pass  # Start fresh if index is corrupted
    
    def _save_dedup_index(self):
        """Save deduplication index to disk"""
        if not self.storage_path:
            return
        
        index_file = self.storage_path / "dedup_index.json"
        index = {hash_key: metadata for hash_key, (_, metadata) in self._dedup_cache.items()}
        
        try:
            with open(index_file, 'w') as f:
                json.dump(index, f)
        except Exception:
            pass  # Non-critical operation
    
    def _compute_hash(self, data: bytes) -> str:
        """Compute SHA-256 hash of data"""
        return hashlib.sha256(data).hexdigest()
    
    def _detect_content_type(self, data: bytes) -> ContentType:
        """Detect content type for algorithm selection"""
        if len(data) == 0:
            return ContentType.BINARY
        
        # Check if already compressed (low entropy)
        sample_size = min(1024, len(data))
        sample = data[:sample_size]
        unique_bytes = len(set(sample))
        
        # If very high entropy, likely already compressed
        if unique_bytes > sample_size * 0.9:
            return ContentType.ALREADY_COMPRESSED
        
        # Check if text (printable ASCII/UTF-8)
        try:
            sample.decode('utf-8')
            return ContentType.TEXT
        except UnicodeDecodeError:
            pass
        
        # Check for numeric patterns (arrays)
        if len(data) >= 8:
            # Simple heuristic: lots of zeros or repeated patterns
            zero_count = data.count(b'\x00')
            if zero_count > len(data) * 0.3:
                return ContentType.NUMERIC
        
        return ContentType.BINARY
    
    def _select_algorithm(self, data: bytes, content_type: Optional[ContentType] = None) -> CompressionAlgorithm:
        """Select best algorithm based on content type"""
        if content_type is None:
            content_type = self._detect_content_type(data)
        
        # Don't compress already compressed data
        if content_type == ContentType.ALREADY_COMPRESSED:
            return CompressionAlgorithm.NONE
        
        # Use default for most cases
        if content_type == ContentType.TEXT and ZSTD_AVAILABLE:
            return CompressionAlgorithm.ZSTD  # Best for text
        elif content_type == ContentType.NUMERIC and LZ4_AVAILABLE:
            return CompressionAlgorithm.LZ4  # Fast for numeric data
        
        return self.default_algorithm
    
    def _compress_gzip(self, data: bytes) -> bytes:
        """Compress using gzip"""
        return zlib.compress(data, level=self.compression_level)
    
    def _decompress_gzip(self, data: bytes) -> bytes:
        """Decompress using gzip"""
        return zlib.decompress(data)
    
    def _compress_lz4(self, data: bytes) -> bytes:
        """Compress using LZ4"""
        if not LZ4_AVAILABLE:
            raise RuntimeError("LZ4 not available")
        return lz4.frame.compress(data, compression_level=self.compression_level)
    
    def _decompress_lz4(self, data: bytes) -> bytes:
        """Decompress using LZ4"""
        if not LZ4_AVAILABLE:
            raise RuntimeError("LZ4 not available")
        return lz4.frame.decompress(data)
    
    def _compress_zstd(self, data: bytes) -> bytes:
        """Compress using Zstandard"""
        if not ZSTD_AVAILABLE:
            raise RuntimeError("Zstandard not available")
        cctx = zstd.ZstdCompressor(level=self.compression_level)
        return cctx.compress(data)
    
    def _decompress_zstd(self, data: bytes) -> bytes:
        """Decompress using Zstandard"""
        if not ZSTD_AVAILABLE:
            raise RuntimeError("Zstandard not available")
        dctx = zstd.ZstdDecompressor()
        return dctx.decompress(data)
    
    def compress(self,
                 data: bytes,
                 algorithm: Optional[CompressionAlgorithm] = None,
                 content_type: Optional[ContentType] = None) -> CompressionResult:
        """
        Compress data with optional deduplication
        
        Args:
            data: Data to compress
            algorithm: Compression algorithm (None = auto-select)
            content_type: Content type hint (None = auto-detect)
        
        Returns:
            CompressionResult with compressed data and metadata
        """
        start_time = time.time()
        original_size = len(data)
        
        # Compute hash for deduplication
        content_hash = None
        is_deduplicated = False
        
        if self.enable_deduplication:
            content_hash = self._compute_hash(data)
            
            with self._cache_lock:
                if content_hash in self._dedup_cache:
                    # Deduplication hit
                    cached_data, metadata = self._dedup_cache[content_hash]
                    
                    # Load from disk if needed
                    if cached_data is None and self.storage_path:
                        dedup_file = self._dedup_dir / content_hash
                        if dedup_file.exists():
                            with open(dedup_file, 'rb') as f:
                                cached_data = f.read()
                                self._dedup_cache[content_hash] = (cached_data, metadata)
                    
                    if cached_data is not None:
                        compression_time = (time.time() - start_time) * 1000
                        
                        with self._stats_lock:
                            self._stats.deduplication_hits += 1
                            self._stats.total_compressions += 1
                            self._stats.total_original_bytes += original_size
                            self._stats.total_compressed_bytes += len(cached_data)
                            self._stats.total_compression_time_ms += compression_time
                        
                        return CompressionResult(
                            compressed_data=cached_data,
                            original_size=original_size,
                            compressed_size=len(cached_data),
                            compression_ratio=len(cached_data) / original_size if original_size > 0 else 1.0,
                            algorithm=CompressionAlgorithm(metadata['algorithm']),
                            compression_time_ms=compression_time,
                            is_deduplicated=True,
                            content_hash=content_hash
                        )
        
        # Select algorithm
        if algorithm is None:
            algorithm = self._select_algorithm(data, content_type)
        
        # Compress data
        if algorithm == CompressionAlgorithm.NONE:
            compressed_data = data
        elif algorithm == CompressionAlgorithm.GZIP:
            compressed_data = self._compress_gzip(data)
        elif algorithm == CompressionAlgorithm.LZ4:
            compressed_data = self._compress_lz4(data)
        elif algorithm == CompressionAlgorithm.ZSTD:
            compressed_data = self._compress_zstd(data)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        compressed_size = len(compressed_data)
        compression_time = (time.time() - start_time) * 1000
        
        # Store in dedup cache
        if self.enable_deduplication and content_hash:
            metadata = {
                'algorithm': algorithm.value,
                'original_size': original_size,
                'compressed_size': compressed_size
            }
            
            with self._cache_lock:
                self._dedup_cache[content_hash] = (compressed_data, metadata)
                self._stats.deduplication_misses += 1
                
                # Save to disk if configured
                if self.storage_path:
                    dedup_file = self._dedup_dir / content_hash
                    with open(dedup_file, 'wb') as f:
                        f.write(compressed_data)
                    self._save_dedup_index()
        
        # Update statistics
        with self._stats_lock:
            self._stats.total_compressions += 1
            self._stats.total_original_bytes += original_size
            self._stats.total_compressed_bytes += compressed_size
            self._stats.total_compression_time_ms += compression_time
            algo_key = algorithm.value
            self._stats.algorithm_usage[algo_key] = self._stats.algorithm_usage.get(algo_key, 0) + 1
        
        return CompressionResult(
            compressed_data=compressed_data,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compressed_size / original_size if original_size > 0 else 1.0,
            algorithm=algorithm,
            compression_time_ms=compression_time,
            is_deduplicated=is_deduplicated,
            content_hash=content_hash
        )
    
    def decompress(self,
                   compressed_data: bytes,
                   algorithm: CompressionAlgorithm,
                   original_size: Optional[int] = None) -> DecompressionResult:
        """
        Decompress data
        
        Args:
            compressed_data: Compressed data
            algorithm: Compression algorithm used
            original_size: Original size hint (for validation)
        
        Returns:
            DecompressionResult with decompressed data
        """
        start_time = time.time()
        compressed_size = len(compressed_data)
        
        # Decompress
        if algorithm == CompressionAlgorithm.NONE:
            data = compressed_data
        elif algorithm == CompressionAlgorithm.GZIP:
            data = self._decompress_gzip(compressed_data)
        elif algorithm == CompressionAlgorithm.LZ4:
            data = self._decompress_lz4(compressed_data)
        elif algorithm == CompressionAlgorithm.ZSTD:
            data = self._decompress_zstd(compressed_data)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        decompression_time = (time.time() - start_time) * 1000
        actual_size = len(data)
        
        # Validate size if provided
        if original_size is not None and actual_size != original_size:
            raise ValueError(f"Size mismatch: expected {original_size}, got {actual_size}")
        
        # Update statistics
        with self._stats_lock:
            self._stats.total_decompressions += 1
            self._stats.total_decompression_time_ms += decompression_time
        
        return DecompressionResult(
            data=data,
            original_size=actual_size,
            compressed_size=compressed_size,
            decompression_time_ms=decompression_time,
            algorithm=algorithm
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics"""
        with self._stats_lock:
            return {
                'total_compressions': self._stats.total_compressions,
                'total_decompressions': self._stats.total_decompressions,
                'total_original_bytes': self._stats.total_original_bytes,
                'total_compressed_bytes': self._stats.total_compressed_bytes,
                'total_space_saved': self._stats.total_space_saved,
                'space_saved_percent': self._stats.space_saved_percent,
                'avg_compression_ratio': self._stats.avg_compression_ratio,
                'avg_compression_time_ms': self._stats.avg_compression_time_ms,
                'avg_decompression_time_ms': self._stats.avg_decompression_time_ms,
                'deduplication_hits': self._stats.deduplication_hits,
                'deduplication_misses': self._stats.deduplication_misses,
                'deduplication_hit_rate': self._stats.deduplication_hit_rate,
                'algorithm_usage': self._stats.algorithm_usage,
                'dedup_cache_size': len(self._dedup_cache),
                'available_algorithms': self._get_available_algorithms()
            }
    
    def _get_available_algorithms(self) -> list:
        """Get list of available compression algorithms"""
        algorithms = ['gzip']  # Always available
        if LZ4_AVAILABLE:
            algorithms.append('lz4')
        if ZSTD_AVAILABLE:
            algorithms.append('zstd')
        return algorithms
    
    def clear_cache(self):
        """Clear deduplication cache"""
        with self._cache_lock:
            self._dedup_cache.clear()
            if self.storage_path:
                index_file = self.storage_path / "dedup_index.json"
                if index_file.exists():
                    index_file.unlink()
