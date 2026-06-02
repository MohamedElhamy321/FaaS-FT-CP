"""
Comprehensive tests for compression and deduplication
"""

import unittest
import tempfile
import shutil
from incremental_checkpoint.compression_manager import (
    CompressionManager,
    CompressionAlgorithm,
    ContentType
)


class TestCompressionManager(unittest.TestCase):
    """Test compression manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = CompressionManager(
            storage_path=self.temp_dir,
            enable_deduplication=True,
            default_algorithm=CompressionAlgorithm.ZSTD
        )
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_compress_decompress_gzip(self):
        """Test gzip compression and decompression"""
        original_data = b"Hello World! " * 100
        
        # Compress
        result = self.manager.compress(original_data, algorithm=CompressionAlgorithm.GZIP)
        
        self.assertTrue(result.compressed_size < result.original_size)
        self.assertEqual(result.algorithm, CompressionAlgorithm.GZIP)
        self.assertEqual(result.original_size, len(original_data))
        
        # Decompress
        decompressed = self.manager.decompress(
            result.compressed_data,
            CompressionAlgorithm.GZIP,
            result.original_size
        )
        
        self.assertEqual(decompressed.data, original_data)
    
    def test_compress_decompress_zstd(self):
        """Test Zstandard compression and decompression"""
        original_data = b"Testing Zstandard compression " * 100
        
        # Compress
        result = self.manager.compress(original_data, algorithm=CompressionAlgorithm.ZSTD)
        
        self.assertTrue(result.compressed_size < result.original_size)
        self.assertEqual(result.algorithm, CompressionAlgorithm.ZSTD)
        
        # Decompress
        decompressed = self.manager.decompress(
            result.compressed_data,
            CompressionAlgorithm.ZSTD
        )
        
        self.assertEqual(decompressed.data, original_data)
    
    def test_compress_decompress_lz4(self):
        """Test LZ4 compression and decompression"""
        original_data = b"Testing LZ4 compression " * 100
        
        # Compress
        result = self.manager.compress(original_data, algorithm=CompressionAlgorithm.LZ4)
        
        self.assertTrue(result.compressed_size < result.original_size)
        self.assertEqual(result.algorithm, CompressionAlgorithm.LZ4)
        
        # Decompress
        decompressed = self.manager.decompress(
            result.compressed_data,
            CompressionAlgorithm.LZ4
        )
        
        self.assertEqual(decompressed.data, original_data)
    
    def test_deduplication(self):
        """Test content-based deduplication"""
        data = b"Duplicate data " * 50
        
        # First compression
        result1 = self.manager.compress(data)
        self.assertFalse(result1.is_deduplicated)
        
        # Second compression of same data should be deduplicated
        result2 = self.manager.compress(data)
        self.assertTrue(result2.is_deduplicated)
        self.assertEqual(result1.content_hash, result2.content_hash)
        
        # Check stats
        stats = self.manager.get_stats()
        self.assertEqual(stats['deduplication_hits'], 1)
        self.assertEqual(stats['deduplication_misses'], 1)
    
    def test_compression_ratio(self):
        """Test compression ratio calculation"""
        # Highly compressible data
        data = b"A" * 10000
        
        result = self.manager.compress(data)
        
        # Should achieve good compression
        self.assertTrue(result.compression_ratio < 0.1)
        self.assertTrue(result.space_saved_percent > 90)
    
    def test_auto_algorithm_selection(self):
        """Test automatic algorithm selection based on content"""
        # Text data (should use ZSTD)
        text_data = b"This is text data " * 100
        result = self.manager.compress(text_data)
        self.assertIn(result.algorithm, [CompressionAlgorithm.ZSTD, CompressionAlgorithm.GZIP])
        
        # Already compressed data (should skip compression)
        import random
        random_data = bytes([random.randint(0, 255) for _ in range(1000)])
        result = self.manager.compress(random_data)
        # High entropy data might not compress well or be skipped
        self.assertIsNotNone(result.algorithm)
    
    def test_content_type_detection(self):
        """Test content type detection"""
        # Text data
        text_data = b"Hello World! This is text."
        content_type = self.manager._detect_content_type(text_data)
        self.assertEqual(content_type, ContentType.TEXT)
        
        # Binary data with zeros (numeric pattern)
        numeric_data = b"\x00" * 500 + b"\x01" * 500
        content_type = self.manager._detect_content_type(numeric_data)
        self.assertEqual(content_type, ContentType.NUMERIC)
    
    def test_statistics_tracking(self):
        """Test compression statistics tracking"""
        data1 = b"First data " * 50
        data2 = b"Second data " * 50
        
        # Perform compressions
        self.manager.compress(data1)
        self.manager.compress(data2)
        
        # Perform decompressions
        result = self.manager.compress(data1)
        self.manager.decompress(result.compressed_data, result.algorithm)
        
        # Check stats
        stats = self.manager.get_stats()
        self.assertEqual(stats['total_compressions'], 3)  # 2 unique + 1 dedup
        self.assertEqual(stats['total_decompressions'], 1)
        self.assertGreater(stats['total_original_bytes'], 0)
        self.assertGreater(stats['total_compressed_bytes'], 0)
        self.assertGreater(stats['space_saved_percent'], 0)
    
    def test_empty_data(self):
        """Test compression of empty data"""
        data = b""
        
        result = self.manager.compress(data)
        
        self.assertEqual(result.original_size, 0)
        self.assertEqual(result.compression_ratio, 1.0)
    
    def test_cache_persistence(self):
        """Test deduplication cache persistence"""
        data = b"Persistent data " * 50
        
        # Compress data
        result1 = self.manager.compress(data)
        content_hash = result1.content_hash
        
        # Create new manager with same storage
        new_manager = CompressionManager(
            storage_path=self.temp_dir,
            enable_deduplication=True
        )
        
        # Should load from disk
        result2 = new_manager.compress(data)
        self.assertTrue(result2.is_deduplicated)
        self.assertEqual(result2.content_hash, content_hash)
    
    def test_compression_with_different_levels(self):
        """Test compression with different levels"""
        data = b"Test compression levels " * 100
        
        # Level 1 (fast)
        mgr_fast = CompressionManager(
            storage_path=None,
            enable_deduplication=False,
            compression_level=1
        )
        result_fast = mgr_fast.compress(data, algorithm=CompressionAlgorithm.ZSTD)
        
        # Level 10 (better ratio)
        mgr_best = CompressionManager(
            storage_path=None,
            enable_deduplication=False,
            compression_level=10
        )
        result_best = mgr_best.compress(data, algorithm=CompressionAlgorithm.ZSTD)
        
        # Higher level should give better (or equal) compression
        self.assertLessEqual(result_best.compressed_size, result_fast.compressed_size * 1.1)
    
    def test_clear_cache(self):
        """Test cache clearing"""
        data = b"Cache test " * 50
        
        # Compress data
        self.manager.compress(data)
        
        stats_before = self.manager.get_stats()
        self.assertGreater(stats_before['dedup_cache_size'], 0)
        
        # Clear cache
        self.manager.clear_cache()
        
        stats_after = self.manager.get_stats()
        self.assertEqual(stats_after['dedup_cache_size'], 0)


class TestCompressionPerformance(unittest.TestCase):
    """Test compression performance"""
    
    def setUp(self):
        """Set up test environment"""
        self.manager = CompressionManager(
            storage_path=None,
            enable_deduplication=False
        )
    
    def test_compression_speed(self):
        """Test compression speed is reasonable"""
        data = b"Performance test " * 1000
        
        result = self.manager.compress(data)
        
        # Should complete in reasonable time (<100ms for small data)
        self.assertLess(result.compression_time_ms, 100)
    
    def test_decompression_speed(self):
        """Test decompression speed is reasonable"""
        data = b"Performance test " * 1000
        
        result = self.manager.compress(data)
        decompressed = self.manager.decompress(result.compressed_data, result.algorithm)
        
        # Decompression should be fast (<50ms for small data)
        self.assertLess(decompressed.decompression_time_ms, 50)
    
    def test_large_data_compression(self):
        """Test compression of larger data"""
        # 1MB of data
        data = b"Large data test " * 65536
        
        result = self.manager.compress(data, algorithm=CompressionAlgorithm.LZ4)
        
        # Should compress reasonably well and fast
        self.assertLess(result.compression_ratio, 1.0)
        self.assertLess(result.compression_time_ms, 1000)  # <1 second
    
    def test_algorithm_comparison(self):
        """Compare different algorithms"""
        data = b"Algorithm comparison " * 1000
        
        results = {}
        for algo in [CompressionAlgorithm.GZIP, CompressionAlgorithm.LZ4, CompressionAlgorithm.ZSTD]:
            try:
                result = self.manager.compress(data, algorithm=algo)
                results[algo.value] = {
                    'ratio': result.compression_ratio,
                    'time': result.compression_time_ms,
                    'size': result.compressed_size
                }
            except RuntimeError:
                # Algorithm not available
                pass
        
        # At least GZIP should be available
        self.assertIn('gzip', results)
        
        # Print comparison for debugging
        print("\nAlgorithm Comparison:")
        for algo, metrics in results.items():
            print(f"  {algo}: ratio={metrics['ratio']:.3f}, "
                  f"time={metrics['time']:.2f}ms, size={metrics['size']} bytes")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
