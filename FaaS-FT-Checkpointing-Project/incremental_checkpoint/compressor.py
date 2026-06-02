"""
Delta Compressor
Efficiently compresses state changes using serialization and compression
"""

import pickle
import zlib
import time
from typing import Dict, Any, List, Optional


class DeltaCompressor:
    """
    Compresses state changes using efficient delta encoding and compression.
    
    Uses pickle for serialization and zlib for compression to achieve
    high compression ratios on incremental state changes.
    
    Example:
        compressor = DeltaCompressor()
        
        changes = {'counter': 5, 'new_key': 'value'}
        compressed = compressor.compress_delta(changes)
        
        # Later, decompress
        restored_changes = compressor.decompress_delta(compressed)
    """
    
    def __init__(self, compression_level: int = 6):
        """
        Initialize the delta compressor.
        
        Args:
            compression_level: zlib compression level (1-9)
                1 = fastest, least compression
                9 = slowest, best compression
                6 = balanced (default)
        """
        if not 1 <= compression_level <= 9:
            raise ValueError("Compression level must be between 1 and 9")
        
        self.compression_level = compression_level
        self.compression_stats: List[Dict[str, Any]] = []
        
    def compress_delta(self, changes: dict) -> bytes:
        """
        Compress state changes using efficient delta encoding.
        
        Args:
            changes: Dictionary of state changes to compress
            
        Returns:
            Compressed binary data
            
        Example:
            >>> compressor = DeltaCompressor()
            >>> changes = {'key1': 'value1', 'key2': 'value2'}
            >>> compressed = compressor.compress_delta(changes)
            >>> len(compressed) < len(str(changes))
            True
        """
        start_time = time.time()
        
        # Serialize changes using pickle (fastest Python serialization)
        try:
            serialized = pickle.dumps(changes, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            raise ValueError(f"Failed to serialize changes: {e}")
        
        original_size = len(serialized)
        
        # Apply zlib compression
        try:
            compressed = zlib.compress(serialized, level=self.compression_level)
        except Exception as e:
            raise ValueError(f"Failed to compress data: {e}")
        
        compressed_size = len(compressed)
        compression_time = time.time() - start_time
        
        # Record compression statistics
        self.compression_stats.append({
            'timestamp': time.time(),
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': original_size / max(1, compressed_size),
            'compression_time_ms': compression_time * 1000,
            'num_keys': len(changes)
        })
        
        return compressed
    
    def decompress_delta(self, compressed_data: bytes) -> dict:
        """
        Decompress delta back to state changes.
        
        Args:
            compressed_data: Compressed binary data
            
        Returns:
            Dictionary of state changes
            
        Raises:
            ValueError: If decompression or deserialization fails
            
        Example:
            >>> compressor = DeltaCompressor()
            >>> changes = {'key': 'value'}
            >>> compressed = compressor.compress_delta(changes)
            >>> restored = compressor.decompress_delta(compressed)
            >>> restored == changes
            True
        """
        if not compressed_data:
            raise ValueError("Cannot decompress empty data")
        
        try:
            # Decompress using zlib
            decompressed = zlib.decompress(compressed_data)
        except Exception as e:
            raise ValueError(f"Failed to decompress data: {e}")
        
        try:
            # Deserialize using pickle
            changes = pickle.loads(decompressed)
        except Exception as e:
            raise ValueError(f"Failed to deserialize data: {e}")
        
        if not isinstance(changes, dict):
            raise ValueError(f"Expected dict, got {type(changes)}")
        
        return changes
    
    def get_compression_ratio(self) -> float:
        """
        Get average compression ratio across all compressions.
        
        Returns:
            Average compression ratio (original_size / compressed_size)
            Returns 1.0 if no compressions have been performed
            
        Example:
            >>> compressor = DeltaCompressor()
            >>> compressor.compress_delta({'key': 'value'})
            >>> ratio = compressor.get_compression_ratio()
            >>> ratio > 1.0
            True
        """
        if not self.compression_stats:
            return 1.0
        
        ratios = [stat['compression_ratio'] for stat in self.compression_stats]
        return sum(ratios) / len(ratios)
    
    def get_statistics(self) -> dict:
        """
        Get detailed compression statistics.
        
        Returns:
            Dictionary with compression statistics:
            - total_compressions: Number of compressions performed
            - average_compression_ratio: Average compression ratio
            - total_original_size: Total size before compression
            - total_compressed_size: Total size after compression
            - total_savings_bytes: Total bytes saved
            - total_savings_percent: Percentage of space saved
            - average_compression_time_ms: Average time per compression
            
        Example:
            >>> stats = compressor.get_statistics()
            >>> print(f"Saved {stats['total_savings_percent']:.1f}% space")
        """
        if not self.compression_stats:
            return {
                'total_compressions': 0,
                'average_compression_ratio': 1.0,
                'total_original_size': 0,
                'total_compressed_size': 0,
                'total_savings_bytes': 0,
                'total_savings_percent': 0.0,
                'average_compression_time_ms': 0.0
            }
        
        total_original = sum(stat['original_size'] for stat in self.compression_stats)
        total_compressed = sum(stat['compressed_size'] for stat in self.compression_stats)
        total_time = sum(stat['compression_time_ms'] for stat in self.compression_stats)
        
        savings_bytes = total_original - total_compressed
        savings_percent = (savings_bytes / max(1, total_original)) * 100
        
        return {
            'total_compressions': len(self.compression_stats),
            'average_compression_ratio': self.get_compression_ratio(),
            'total_original_size': total_original,
            'total_compressed_size': total_compressed,
            'total_savings_bytes': savings_bytes,
            'total_savings_percent': savings_percent,
            'average_compression_time_ms': total_time / len(self.compression_stats)
        }
    
    def reset_statistics(self) -> None:
        """
        Reset compression statistics.
        
        Example:
            >>> compressor.reset_statistics()
            >>> compressor.get_statistics()['total_compressions']
            0
        """
        self.compression_stats.clear()
    
    def estimate_compressed_size(self, changes: dict) -> int:
        """
        Estimate compressed size without actually compressing.
        
        Uses average compression ratio from previous compressions.
        
        Args:
            changes: Dictionary to estimate compressed size for
            
        Returns:
            Estimated compressed size in bytes
        """
        # Estimate serialized size
        estimated_serialized = len(pickle.dumps(changes, protocol=pickle.HIGHEST_PROTOCOL))
        
        # Apply average compression ratio
        avg_ratio = self.get_compression_ratio()
        estimated_compressed = int(estimated_serialized / avg_ratio)
        
        return estimated_compressed


class OptimizedDeltaCompressor(DeltaCompressor):
    """
    Optimized version with parallel compression for large datasets.
    
    Uses threading for parallel compression of large change sets.
    Falls back to single-threaded for small datasets.
    """
    
    def __init__(self, compression_level: int = 6, num_workers: int = 4, 
                 parallel_threshold: int = 1000):
        """
        Initialize optimized delta compressor.
        
        Args:
            compression_level: zlib compression level (1-9)
            num_workers: Number of parallel workers for compression
            parallel_threshold: Minimum keys to trigger parallel compression
        """
        super().__init__(compression_level)
        self.num_workers = num_workers
        self.parallel_threshold = parallel_threshold
        self._executor = None
    
    def _get_executor(self):
        """Lazy initialization of thread pool executor"""
        if self._executor is None:
            from concurrent.futures import ThreadPoolExecutor
            self._executor = ThreadPoolExecutor(max_workers=self.num_workers)
        return self._executor
    
    def compress_delta_parallel(self, changes: dict) -> bytes:
        """
        Compress large change sets in parallel.
        
        Automatically falls back to single-threaded for small datasets.
        
        Args:
            changes: Dictionary of state changes to compress
            
        Returns:
            Compressed binary data
        """
        # For small changes, use regular compression
        if len(changes) < self.parallel_threshold:
            return self.compress_delta(changes)
        
        # Split changes into chunks
        chunks = self._split_dict(changes, self.num_workers)
        
        # Compress chunks in parallel
        executor = self._get_executor()
        futures = [
            executor.submit(self.compress_delta, chunk)
            for chunk in chunks
        ]
        
        compressed_chunks = [f.result() for f in futures]
        
        # Combine compressed chunks
        return self._combine_chunks(compressed_chunks)
    
    def decompress_delta_parallel(self, compressed_data: bytes) -> dict:
        """
        Decompress parallel-compressed data.
        
        Args:
            compressed_data: Compressed binary data from parallel compression
            
        Returns:
            Dictionary of state changes
        """
        # Check if this is parallel-compressed data
        if not self._is_parallel_format(compressed_data):
            # Regular compressed data
            return self.decompress_delta(compressed_data)
        
        # Extract chunks
        chunks = self._extract_chunks(compressed_data)
        
        # Decompress chunks in parallel
        executor = self._get_executor()
        futures = [
            executor.submit(self.decompress_delta, chunk)
            for chunk in chunks
        ]
        
        decompressed_chunks = [f.result() for f in futures]
        
        # Merge all chunks
        merged = {}
        for chunk in decompressed_chunks:
            merged.update(chunk)
        
        return merged
    
    def _split_dict(self, d: dict, n: int) -> List[dict]:
        """Split dictionary into n roughly equal chunks"""
        items = list(d.items())
        chunk_size = max(1, len(items) // n)
        
        chunks = []
        for i in range(0, len(items), chunk_size):
            chunk_items = items[i:i + chunk_size]
            chunks.append(dict(chunk_items))
        
        return chunks
    
    def _combine_chunks(self, chunks: List[bytes]) -> bytes:
        """
        Combine compressed chunks with metadata.
        
        Format: [PARALLEL_MARKER][num_chunks][chunk1_size][chunk1]...
        """
        import struct
        
        # Parallel format marker (4 bytes: 'PARA')
        result = b'PARA'
        
        # Number of chunks (4 bytes)
        result += struct.pack('I', len(chunks))
        
        # Each chunk: [size][data]
        for chunk in chunks:
            result += struct.pack('I', len(chunk))
            result += chunk
        
        return result
    
    def _is_parallel_format(self, data: bytes) -> bool:
        """Check if data is in parallel compression format"""
        return data[:4] == b'PARA'
    
    def _extract_chunks(self, data: bytes) -> List[bytes]:
        """Extract chunks from parallel-compressed data"""
        import struct
        
        if not self._is_parallel_format(data):
            raise ValueError("Data is not in parallel format")
        
        offset = 4  # Skip marker
        
        # Read number of chunks
        num_chunks = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        
        # Extract each chunk
        chunks = []
        for _ in range(num_chunks):
            # Read chunk size
            chunk_size = struct.unpack('I', data[offset:offset+4])[0]
            offset += 4
            
            # Read chunk data
            chunk_data = data[offset:offset+chunk_size]
            offset += chunk_size
            
            chunks.append(chunk_data)
        
        return chunks
    
    def shutdown(self):
        """Shutdown the thread pool executor"""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
    
    def __del__(self):
        """Cleanup on deletion"""
        self.shutdown()
