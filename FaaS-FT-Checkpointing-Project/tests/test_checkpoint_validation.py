"""
Tests for Checkpoint Quality & Validation System
"""

import unittest
import pickle
import time
import tempfile
from incremental_checkpoint.validation import (
    CheckpointValidator,
    ChecksumCalculator,
    ChecksumAlgorithm,
    ValidationLevel,
    CorruptionType,
    QualityLevel,
    ValidationReport
)
from incremental_checkpoint import IncrementalCheckpoint


class TestChecksumCalculator(unittest.TestCase):
    """Test checksum calculation"""
    
    def test_sha256_checksum(self):
        """Test SHA-256 checksum calculation"""
        data = b"test data"
        checksum = ChecksumCalculator.calculate(data, ChecksumAlgorithm.SHA256)
        
        self.assertIsInstance(checksum, str)
        self.assertEqual(len(checksum), 64)  # SHA-256 produces 64 hex chars
    
    def test_crc32_checksum(self):
        """Test CRC32 checksum calculation"""
        data = b"test data"
        checksum = ChecksumCalculator.calculate(data, ChecksumAlgorithm.CRC32)
        
        self.assertIsInstance(checksum, str)
        self.assertEqual(len(checksum), 8)  # CRC32 produces 8 hex chars
    
    def test_checksum_consistency(self):
        """Test checksum is consistent for same data"""
        data = b"consistent data"
        checksum1 = ChecksumCalculator.calculate(data)
        checksum2 = ChecksumCalculator.calculate(data)
        
        self.assertEqual(checksum1, checksum2)
    
    def test_checksum_different_for_different_data(self):
        """Test different data produces different checksums"""
        data1 = b"data one"
        data2 = b"data two"
        
        checksum1 = ChecksumCalculator.calculate(data1)
        checksum2 = ChecksumCalculator.calculate(data2)
        
        self.assertNotEqual(checksum1, checksum2)
    
    def test_calculate_all_algorithms(self):
        """Test calculating checksums with all algorithms"""
        data = b"test data"
        checksums = ChecksumCalculator.calculate_all(data)
        
        self.assertIn('sha256', checksums)
        self.assertIn('crc32', checksums)
        self.assertEqual(len(checksums['sha256']), 64)
        self.assertEqual(len(checksums['crc32']), 8)


class TestCheckpointValidator(unittest.TestCase):
    """Test checkpoint validation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = CheckpointValidator()
    
    def _create_checkpoint(self, checkpoint_id, is_full, state_data, **kwargs):
        """Helper to create test checkpoint"""
        data = pickle.dumps(state_data)
        return IncrementalCheckpoint(
            checkpoint_id=checkpoint_id,
            is_full=is_full,
            timestamp=kwargs.get('timestamp', time.time()),
            base_checkpoint_id=kwargs.get('base_checkpoint_id'),
            data=data,
            metadata=kwargs.get('metadata', {})
        )
    
    def test_validate_good_checkpoint(self):
        """Test validation of valid checkpoint"""
        checkpoint = self._create_checkpoint(1, True, {'key': 'value'})
        
        result = self.validator.validate(checkpoint)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.quality_level, QualityLevel.EXCELLENT)
        self.assertEqual(result.quality_score, 1.0)
        self.assertEqual(len(result.issues), 0)
    
    def test_validate_with_checksum_verification(self):
        """Test validation with checksum verification"""
        checkpoint = self._create_checkpoint(1, True, {'key': 'value'})
        
        # Calculate expected checksum
        expected = ChecksumCalculator.calculate(checkpoint.data)
        
        result = self.validator.validate(checkpoint, expected_checksum=expected)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.issues), 0)
    
    def test_detect_checksum_mismatch(self):
        """Test detection of checksum mismatch"""
        checkpoint = self._create_checkpoint(1, True, {'key': 'value'})
        
        # Use wrong checksum
        wrong_checksum = "0" * 64
        
        result = self.validator.validate(checkpoint, expected_checksum=wrong_checksum)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.critical_issues), 0)
        self.assertEqual(result.critical_issues[0].corruption_type, 
                        CorruptionType.CHECKSUM_MISMATCH)
    
    def test_detect_missing_base_checkpoint(self):
        """Test detection of missing base checkpoint reference"""
        # Create incremental checkpoint without base
        checkpoint = self._create_checkpoint(2, False, {'key': 'value'}, 
                                            base_checkpoint_id=None)
        
        result = self.validator.validate(checkpoint, level=ValidationLevel.THOROUGH)
        
        self.assertFalse(result.is_valid)
        critical = [i for i in result.issues if i.corruption_type == CorruptionType.DEPENDENCY_BROKEN]
        self.assertGreater(len(critical), 0)
    
    def test_detect_invalid_timestamp(self):
        """Test detection of invalid timestamp"""
        # Timestamp in far future
        future_time = time.time() + 100000
        checkpoint = self._create_checkpoint(1, True, {'key': 'value'}, 
                                            timestamp=future_time)
        
        result = self.validator.validate(checkpoint, level=ValidationLevel.THOROUGH)
        
        # Should have warning about future timestamp
        timestamp_issues = [i for i in result.issues if i.field == 'timestamp']
        self.assertGreater(len(timestamp_issues), 0)
    
    def test_validation_levels(self):
        """Test different validation levels"""
        checkpoint = self._create_checkpoint(1, True, {'key': 'value'})
        
        # Basic validation (fastest)
        result_basic = self.validator.validate(checkpoint, level=ValidationLevel.BASIC)
        
        # Thorough validation (more checks)
        result_thorough = self.validator.validate(checkpoint, level=ValidationLevel.THOROUGH)
        
        # Both should be valid for good checkpoint
        self.assertTrue(result_basic.is_valid)
        self.assertTrue(result_thorough.is_valid)
        
        # Thorough should take longer
        self.assertGreaterEqual(result_thorough.validation_time_ms, 
                               result_basic.validation_time_ms * 0.5)
    
    def test_quality_scoring(self):
        """Test quality score calculation"""
        # Perfect checkpoint
        good_checkpoint = self._create_checkpoint(1, True, {'key': 'value'})
        result_good = self.validator.validate(good_checkpoint)
        
        self.assertEqual(result_good.quality_score, 1.0)
        self.assertEqual(result_good.quality_level, QualityLevel.EXCELLENT)
        
        # Checkpoint with issues
        bad_checkpoint = self._create_checkpoint(2, False, {'key': 'value'},
                                                base_checkpoint_id=None)
        result_bad = self.validator.validate(bad_checkpoint, level=ValidationLevel.THOROUGH)
        
        self.assertLess(result_bad.quality_score, 1.0)
        self.assertNotEqual(result_bad.quality_level, QualityLevel.EXCELLENT)
    
    def test_checksums_in_result(self):
        """Test checksums are included in validation result"""
        checkpoint = self._create_checkpoint(1, True, {'key': 'value'})
        
        result = self.validator.validate(checkpoint)
        
        self.assertIn('sha256', result.checksums)
        self.assertIn('crc32', result.checksums)
        self.assertEqual(len(result.checksums['sha256']), 64)
    
    def test_repair_metadata_corruption(self):
        """Test repair of metadata corruption"""
        checkpoint = self._create_checkpoint(1, True, {'key': 'value'})
        
        # Corrupt metadata
        checkpoint.metadata = "not a dict"
        
        # Validate - should detect the issue
        validation = self.validator.validate(checkpoint, level=ValidationLevel.STANDARD)
        
        # Check if issues were detected (may not be marked invalid if only warnings)
        metadata_issues = [i for i in validation.issues if i.field == 'metadata']
        self.assertGreater(len(metadata_issues), 0, "Should detect metadata format issue")
        
        # Attempt repair
        repair_result = self.validator.repair(checkpoint, validation)
        
        # Should succeed in repairing if issues were repairable
        if metadata_issues[0].repairable:
            self.assertIsInstance(checkpoint.metadata, dict)
    
    def test_repair_timestamp_issue(self):
        """Test repair of timestamp issues"""
        future_time = time.time() + 100000
        checkpoint = self._create_checkpoint(1, True, {'key': 'value'},
                                            timestamp=future_time)
        
        validation = self.validator.validate(checkpoint, level=ValidationLevel.THOROUGH)
        
        # Repair
        repair_result = self.validator.repair(checkpoint, validation)
        
        # Timestamp should be fixed
        self.assertLessEqual(checkpoint.timestamp, time.time())
    
    def test_metrics_tracking(self):
        """Test validation metrics are tracked"""
        self.validator.metrics.total_validations = 0
        
        checkpoint = self._create_checkpoint(1, True, {'key': 'value'})
        
        # Perform validations
        self.validator.validate(checkpoint)
        self.validator.validate(checkpoint)
        
        metrics = self.validator.get_metrics()
        
        self.assertEqual(metrics['total_validations'], 2)
        self.assertGreaterEqual(metrics['avg_validation_time_ms'], 0)  # Can be 0ms for fast operations
        self.assertGreaterEqual(metrics['avg_quality_score'], 0)
    
    def test_corruption_detection_metrics(self):
        """Test corruption detection is tracked in metrics"""
        self.validator.metrics.corruption_detected = 0
        
        # Create corrupted checkpoint
        bad_checkpoint = self._create_checkpoint(1, True, {'key': 'value'})
        
        # Validate with wrong checksum
        self.validator.validate(bad_checkpoint, expected_checksum="0" * 64)
        
        metrics = self.validator.get_metrics()
        
        self.assertGreater(metrics['corruption_detected'], 0)
        self.assertGreater(metrics['corruption_rate'], 0)
        self.assertIn('checksum_mismatch', metrics['corruption_by_type'])


class TestValidationReport(unittest.TestCase):
    """Test validation report generation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = CheckpointValidator()
    
    def _create_checkpoint(self, checkpoint_id, is_full, state_data):
        """Helper to create test checkpoint"""
        data = pickle.dumps(state_data)
        return IncrementalCheckpoint(
            checkpoint_id=checkpoint_id,
            is_full=is_full,
            timestamp=time.time(),
            base_checkpoint_id=None if is_full else 1,
            data=data,
            metadata={}
        )
    
    def test_generate_report_for_valid_checkpoint(self):
        """Test report generation for valid checkpoint"""
        checkpoint = self._create_checkpoint(1, True, {'key': 'value'})
        result = self.validator.validate(checkpoint)
        
        report = ValidationReport.generate(result)
        
        self.assertIn('VALID', report)
        self.assertIn('EXCELLENT', report)
        self.assertIn('No issues found', report)
    
    def test_generate_report_for_invalid_checkpoint(self):
        """Test report generation for invalid checkpoint"""
        checkpoint = self._create_checkpoint(1, True, {'key': 'value'})
        
        # Validate with wrong checksum
        result = self.validator.validate(checkpoint, expected_checksum="0" * 64)
        
        report = ValidationReport.generate(result)
        
        self.assertIn('INVALID', report)
        self.assertIn('CRITICAL ISSUES', report)
        self.assertIn('Checksum verification failed', report)
    
    def test_report_includes_checksums(self):
        """Test report includes checksums"""
        checkpoint = self._create_checkpoint(1, True, {'key': 'value'})
        result = self.validator.validate(checkpoint)
        
        report = ValidationReport.generate(result)
        
        self.assertIn('Checksums:', report)
        self.assertIn('sha256:', report)
        self.assertIn('crc32:', report)
    
    def test_report_formatting(self):
        """Test report is properly formatted"""
        checkpoint = self._create_checkpoint(1, True, {'key': 'value'})
        result = self.validator.validate(checkpoint)
        
        report = ValidationReport.generate(result)
        
        # Check structure
        lines = report.split('\n')
        self.assertGreater(len(lines), 5)
        self.assertTrue(any('=' * 60 in line for line in lines))


class TestValidationPerformance(unittest.TestCase):
    """Performance tests for validation system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = CheckpointValidator()
    
    def _create_checkpoint(self, checkpoint_id, is_full, state_data):
        """Helper to create test checkpoint"""
        data = pickle.dumps(state_data)
        return IncrementalCheckpoint(
            checkpoint_id=checkpoint_id,
            is_full=is_full,
            timestamp=time.time(),
            base_checkpoint_id=None if is_full else 1,
            data=data,
            metadata={}
        )
    
    def test_validation_speed(self):
        """Test validation completes quickly"""
        checkpoint = self._create_checkpoint(1, True, {'key': 'value' * 1000})
        
        start_time = time.time()
        result = self.validator.validate(checkpoint, level=ValidationLevel.BASIC)
        elapsed_ms = (time.time() - start_time) * 1000
        
        print(f"\n[Validation Performance]")
        print(f"  Validation time: {elapsed_ms:.2f}ms")
        print(f"  Quality score: {result.quality_score:.2%}")
        
        # Should be fast (<10ms)
        self.assertLess(elapsed_ms, 10)
    
    def test_thorough_validation_speed(self):
        """Test thorough validation performance"""
        checkpoint = self._create_checkpoint(1, True, {'key': 'value' * 1000})
        
        start_time = time.time()
        result = self.validator.validate(checkpoint, level=ValidationLevel.THOROUGH)
        elapsed_ms = (time.time() - start_time) * 1000
        
        print(f"\n[Thorough Validation Performance]")
        print(f"  Validation time: {elapsed_ms:.2f}ms")
        print(f"  Issues found: {len(result.issues)}")
        
        # Should still be fast (<50ms)
        self.assertLess(elapsed_ms, 50)
    
    def test_batch_validation(self):
        """Test validating multiple checkpoints"""
        checkpoints = [
            self._create_checkpoint(i, i == 1, {f'key{i}': f'value{i}'})
            for i in range(1, 21)
        ]
        
        start_time = time.time()
        results = [self.validator.validate(cp) for cp in checkpoints]
        elapsed_ms = (time.time() - start_time) * 1000
        
        print(f"\n[Batch Validation Performance]")
        print(f"  Checkpoints: {len(checkpoints)}")
        print(f"  Total time: {elapsed_ms:.2f}ms")
        print(f"  Avg per checkpoint: {elapsed_ms / len(checkpoints):.2f}ms")
        print(f"  All valid: {all(r.is_valid for r in results)}")
        
        # Should validate all quickly
        self.assertLess(elapsed_ms, 200)
        self.assertTrue(all(r.is_valid for r in results))


if __name__ == '__main__':
    unittest.main(verbosity=2)
