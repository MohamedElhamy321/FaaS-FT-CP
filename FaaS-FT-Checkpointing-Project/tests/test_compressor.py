"""
Unit tests for DeltaCompressor
"""

import sys
import os
import time
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from incremental_checkpoint.compressor import DeltaCompressor, OptimizedDeltaCompressor


class TestDeltaCompressor(unittest.TestCase):
    """Test cases for DeltaCompressor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.compressor = DeltaCompressor()
    
    def test_initialization(self):
        """Test compressor initializes correctly"""
        self.assertEqual(self.compressor.compression_level, 6)
        self.assertEqual(len(self.compressor.compression_stats), 0)
    
    def test_initialization_custom_level(self):
        """Test initialization with custom compression level"""
        compressor = DeltaCompressor(compression_level=9)
        self.assertEqual(compressor.compression_level, 9)
    
    def test_initialization_invalid_level(self):
        """Test initialization with invalid compression level"""
        with self.assertRaises(ValueError):
            DeltaCompressor(compression_level=0)
        with self.assertRaises(ValueError):
            DeltaCompressor(compression_level=10)
    
    def test_compress_decompress_round_trip(self):
        """Test compression and decompression preserve data"""
        changes = {'key1': 'value1', 'key2': 42, 'key3': [1, 2, 3]}
        
        compressed = self.compressor.compress_delta(changes)
        decompressed = self.compressor.decompress_delta(compressed)
        
        self.assertEqual(changes, decompressed)
    
    def test_compress_empty_dict(self):
        """Test compressing empty dictionary"""
        changes = {}
        compressed = self.compressor.compress_delta(changes)
        decompressed = self.compressor.decompress_delta(compressed)
        
        self.assertEqual(changes, decompressed)
    
    def test_compress_reduces_size(self):
        """Test compression actually reduces size"""
        # Create data with repetition (compresses well)
        changes = {f'key_{i}': 'repeated_value' * 10 for i in range(100)}
        
        import pickle
        original_size = len(pickle.dumps(changes))
        compressed_size = len(self.compressor.compress_delta(changes))
        
        self.assertLess(compressed_size, original_size)
    
    def test_compress_complex_types(self):
        """Test compression of complex data types"""
        changes = {
            'string': 'hello world',
            'int': 12345,
            'float': 3.14159,
            'bool': True,
            'none': None,
            'list': [1, 2, 3, 4, 5],
            'dict': {'nested': 'value'},
            'tuple': (1, 2, 3),
            'set': {1, 2, 3}
        }
        
        compressed = self.compressor.compress_delta(changes)
        decompressed = self.compressor.decompress_delta(compressed)
        
        # Sets may not preserve order exactly, check separately
        self.assertEqual(set(decompressed['set']), set(changes['set']))
        del changes['set']
        del decompressed['set']
        
        self.assertEqual(changes, decompressed)
    
    def test_decompress_empty_data(self):
        """Test decompressing empty data raises error"""
        with self.assertRaises(ValueError):
            self.compressor.decompress_delta(b'')
    
    def test_decompress_invalid_data(self):
        """Test decompressing invalid data raises error"""
        with self.assertRaises(ValueError):
            self.compressor.decompress_delta(b'invalid_compressed_data')
    
    def test_compression_statistics_recorded(self):
        """Test compression statistics are recorded"""
        changes = {'key': 'value'}
        self.compressor.compress_delta(changes)
        
        self.assertEqual(len(self.compressor.compression_stats), 1)
        
        stat = self.compressor.compression_stats[0]
        self.assertIn('original_size', stat)
        self.assertIn('compressed_size', stat)
        self.assertIn('compression_ratio', stat)
        self.assertIn('compression_time_ms', stat)
    
    def test_get_compression_ratio_no_compressions(self):
        """Test compression ratio when no compressions performed"""
        ratio = self.compressor.get_compression_ratio()
        self.assertEqual(ratio, 1.0)
    
    def test_get_compression_ratio_with_compressions(self):
        """Test compression ratio calculation"""
        changes = {f'key_{i}': 'value' * 10 for i in range(50)}
        self.compressor.compress_delta(changes)
        
        ratio = self.compressor.get_compression_ratio()
        self.assertGreater(ratio, 1.0)  # Should have some compression
    
    def test_get_statistics_empty(self):
        """Test statistics when no compressions performed"""
        stats = self.compressor.get_statistics()
        
        self.assertEqual(stats['total_compressions'], 0)
        self.assertEqual(stats['total_original_size'], 0)
        self.assertEqual(stats['total_compressed_size'], 0)
    
    def test_get_statistics_with_data(self):
        """Test statistics calculation"""
        changes1 = {'key1': 'value1'}
        changes2 = {'key2': 'value2' * 10}
        
        self.compressor.compress_delta(changes1)
        self.compressor.compress_delta(changes2)
        
        stats = self.compressor.get_statistics()
        
        self.assertEqual(stats['total_compressions'], 2)
        self.assertGreater(stats['total_original_size'], 0)
        self.assertGreater(stats['total_compressed_size'], 0)
        self.assertGreater(stats['total_savings_bytes'], 0)
        self.assertGreater(stats['total_savings_percent'], 0)
    
    def test_reset_statistics(self):
        """Test resetting statistics"""
        changes = {'key': 'value'}
        self.compressor.compress_delta(changes)
        
        self.assertEqual(len(self.compressor.compression_stats), 1)
        
        self.compressor.reset_statistics()
        
        self.assertEqual(len(self.compressor.compression_stats), 0)
    
    def test_estimate_compressed_size(self):
        """Test compressed size estimation"""
        changes = {'key': 'value'}
        self.compressor.compress_delta(changes)
        
        estimated = self.compressor.estimate_compressed_size(changes)
        self.assertGreater(estimated, 0)
    
    def test_compression_levels(self):
        """Test different compression levels"""
        changes = {f'key_{i}': 'repeated' * 20 for i in range(100)}
        
        sizes = {}
        for level in [1, 6, 9]:
            compressor = DeltaCompressor(compression_level=level)
            compressed = compressor.compress_delta(changes)
            sizes[level] = len(compressed)
        
        # Higher compression levels should produce smaller sizes
        self.assertGreaterEqual(sizes[1], sizes[6])
        self.assertGreaterEqual(sizes[6], sizes[9])
    
    def test_performance_100kb_data(self):
        """Test compression performance with ~100KB data"""
        # Create ~100KB of data
        changes = {f'key_{i}': 'x' * 1000 for i in range(100)}
        
        start = time.time()
        compressed = self.compressor.compress_delta(changes)
        elapsed = time.time() - start
        
        # Should compress in reasonable time (<200ms)
        self.assertLess(elapsed, 0.2)
        
        # Verify decompression works
        decompressed = self.compressor.decompress_delta(compressed)
        self.assertEqual(len(changes), len(decompressed))
    
    def test_large_values(self):
        """Test compression of large values"""
        # Create 1MB value
        large_value = 'x' * (1024 * 1024)
        changes = {'large_key': large_value}
        
        compressed = self.compressor.compress_delta(changes)
        decompressed = self.compressor.decompress_delta(compressed)
        
        self.assertEqual(changes, decompressed)


class TestOptimizedDeltaCompressor(unittest.TestCase):
    """Test cases for OptimizedDeltaCompressor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.compressor = OptimizedDeltaCompressor(num_workers=2, parallel_threshold=10)
    
    def tearDown(self):
        """Clean up"""
        self.compressor.shutdown()
    
    def test_initialization(self):
        """Test optimized compressor initializes correctly"""
        self.assertEqual(self.compressor.num_workers, 2)
        self.assertEqual(self.compressor.parallel_threshold, 10)
    
    def test_compress_parallel_small_data(self):
        """Test parallel compression falls back for small data"""
        changes = {'key1': 'value1', 'key2': 'value2'}  # Below threshold
        
        compressed = self.compressor.compress_delta_parallel(changes)
        decompressed = self.compressor.decompress_delta_parallel(compressed)
        
        self.assertEqual(changes, decompressed)
    
    def test_compress_parallel_large_data(self):
        """Test parallel compression for large data"""
        # Create data above threshold
        changes = {f'key_{i}': f'value_{i}' for i in range(100)}
        
        compressed = self.compressor.compress_delta_parallel(changes)
        decompressed = self.compressor.decompress_delta_parallel(compressed)
        
        self.assertEqual(changes, decompressed)
    
    def test_parallel_format_detection(self):
        """Test detection of parallel compression format"""
        changes = {f'key_{i}': 'value' for i in range(100)}
        
        # Parallel compressed
        parallel_compressed = self.compressor.compress_delta_parallel(changes)
        self.assertTrue(self.compressor._is_parallel_format(parallel_compressed))
        
        # Regular compressed
        regular_compressed = self.compressor.compress_delta({'key': 'value'})
        self.assertFalse(self.compressor._is_parallel_format(regular_compressed))
    
    def test_split_dict(self):
        """Test dictionary splitting"""
        data = {f'key_{i}': i for i in range(100)}
        chunks = self.compressor._split_dict(data, 4)
        
        # Should have 4 chunks
        self.assertEqual(len(chunks), 4)
        
        # All items should be present
        merged = {}
        for chunk in chunks:
            merged.update(chunk)
        self.assertEqual(data, merged)
    
    def test_combine_extract_chunks(self):
        """Test combining and extracting chunks"""
        chunks = [b'chunk1', b'chunk2', b'chunk3']
        
        combined = self.compressor._combine_chunks(chunks)
        extracted = self.compressor._extract_chunks(combined)
        
        self.assertEqual(chunks, extracted)
    
    def test_shutdown(self):
        """Test executor shutdown"""
        # Use executor
        changes = {f'key_{i}': 'value' for i in range(100)}
        self.compressor.compress_delta_parallel(changes)
        
        # Shutdown
        self.compressor.shutdown()
        self.assertIsNone(self.compressor._executor)


class TestCompressionScenarios(unittest.TestCase):
    """Test real-world compression scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.compressor = DeltaCompressor()
    
    def test_serverless_function_state(self):
        """Test compression of serverless function state changes"""
        changes = {
            'execution_id': 'exec_12345',
            'memory_used_mb': 256,
            'cpu_time_ms': 150,
            'variables': {'x': 10, 'y': 20, 'result': 30},
            'logs': ['Starting', 'Processing', 'Complete']
        }
        
        compressed = self.compressor.compress_delta(changes)
        decompressed = self.compressor.decompress_delta(compressed)
        
        self.assertEqual(changes, decompressed)
    
    def test_incremental_checkpoint_scenario(self):
        """Test typical incremental checkpoint scenario"""
        # Simulate 10 checkpoints with small changes
        state = {f'var_{i}': f'initial_{i}' for i in range(1000)}
        
        total_full_size = 0
        total_incremental_size = 0
        
        for checkpoint in range(10):
            # Change 10% of variables
            import random
            for i in random.sample(range(1000), 100):
                state[f'var_{i}'] = f'checkpoint_{checkpoint}_value_{i}'
            
            # Full checkpoint
            import pickle
            full_size = len(pickle.dumps(state))
            total_full_size += full_size
            
            # Incremental checkpoint (only changes)
            changes = {k: v for k, v in list(state.items())[:100]}
            incremental = self.compressor.compress_delta(changes)
            total_incremental_size += len(incremental)
        
        # Incremental should be much smaller
        savings_percent = ((total_full_size - total_incremental_size) / total_full_size) * 100
        print(f"\nIncremental checkpoint savings: {savings_percent:.1f}%")
        self.assertGreater(savings_percent, 50)  # At least 50% savings


def run_tests():
    """Run all tests and display results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDeltaCompressor))
    suite.addTests(loader.loadTestsFromTestCase(TestOptimizedDeltaCompressor))
    suite.addTests(loader.loadTestsFromTestCase(TestCompressionScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
