#!/usr/bin/env python3
"""Tests for Spirometry Curve Analyzer.

Run with: python -m pytest test_spirometry_analyzer.py -v
    or:   python test_spirometry_analyzer.py
"""
import json
import os
import sys
import tempfile
import unittest

from spiro_analyze import (
    predicted_fev1,
    predicted_fvc,
    predicted_fev1_fvc,
    lln_fev1_fvc,
    percent_predicted,
    bronchodilator_response,
    interpret_spirometry,
    process_csv,
    main,
)


class TestPredictedValues(unittest.TestCase):
    """Test reference equation predictions."""

    def test_predicted_fev1_male(self):
        """Predicted FEV1 for a 40-year-old 175cm male."""
        result = predicted_fev1(40, 175, "M")
        self.assertGreater(result, 2.0)
        self.assertLess(result, 5.0)

    def test_predicted_fev1_female(self):
        """Predicted FEV1 for a 40-year-old 165cm female."""
        result = predicted_fev1(40, 165, "F")
        self.assertGreater(result, 1.5)
        self.assertLess(result, 4.0)

    def test_predicted_fev1_male_greater_than_female(self):
        """Males should have higher predicted FEV1 than females at same age/height."""
        male = predicted_fev1(40, 175, "M")
        female = predicted_fev1(40, 175, "F")
        self.assertGreater(male, female)

    def test_predicted_fev1_decreases_with_age(self):
        """FEV1 predicted should decrease with age."""
        young = predicted_fev1(20, 175, "M")
        old = predicted_fev1(70, 175, "M")
        self.assertGreater(young, old)

    def test_predicted_fev1_increases_with_height(self):
        """FEV1 predicted should increase with height."""
        short = predicted_fev1(40, 160, "M")
        tall = predicted_fev1(40, 190, "M")
        self.assertGreater(tall, short)

    def test_predicted_fvc_male(self):
        """Predicted FVC for a 40-year-old 175cm male."""
        result = predicted_fvc(40, 175, "M")
        self.assertGreater(result, 2.5)
        self.assertLess(result, 6.0)

    def test_predicted_fvc_female(self):
        """Predicted FVC for a 40-year-old 165cm female."""
        result = predicted_fvc(40, 165, "F")
        self.assertGreater(result, 2.0)
        self.assertLess(result, 5.0)

    def test_predicted_ratio(self):
        """Predicted FEV1/FVC ratio should be around 0.75-0.85."""
        result = predicted_fev1_fvc(40, 175, "M")
        self.assertGreater(result, 0.70)
        self.assertLess(result, 0.90)

    def test_invalid_sex(self):
        """Invalid sex raises ValueError."""
        with self.assertRaises(ValueError):
            predicted_fev1(40, 175, "X")

    def test_lln_decreases_with_age(self):
        """LLN should decrease with age (fixed ratio over-diagnoses in elderly)."""
        young = lln_fev1_fvc(30, "M")
        old = lln_fev1_fvc(75, "M")
        self.assertGreater(young, old)


class TestPercentPredicted(unittest.TestCase):
    """Test percent predicted calculation."""

    def test_exact_predicted(self):
        """100% of predicted."""
        self.assertAlmostEqual(percent_predicted(3.5, 3.5), 100.0)

    def test_half_predicted(self):
        """50% of predicted."""
        self.assertAlmostEqual(percent_predicted(1.75, 3.5), 50.0)

    def test_zero_predicted_raises(self):
        with self.assertRaises(ValueError):
            percent_predicted(3.0, 0.0)


class TestBronchodilatorResponse(unittest.TestCase):
    """Test bronchodilator response assessment."""

    def test_significant_response(self):
        """12% and 200mL improvement is significant."""
        result = bronchodilator_response(2.0, 2.3)
        self.assertTrue(result.is_significant)
        self.assertAlmostEqual(result.fev1_change_ml, 300.0)
        self.assertAlmostEqual(result.fev1_change_percent, 15.0)

    def test_not_significant_small_percent(self):
        """Large absolute change but < 12% is not significant."""
        result = bronchodilator_response(4.0, 4.15)
        # 150 mL = 3.75% -> not significant
        self.assertFalse(result.is_significant)

    def test_not_significant_small_absolute(self):
        """12% but < 200mL is not significant."""
        result = bronchodilator_response(1.0, 1.13)
        # 130 mL, 13% -> not significant (absolute < 200)
        self.assertFalse(result.is_significant)

    def test_borderline_significant(self):
        """12% and 200mL should be significant."""
        # Use values that give exactly 12% and 200mL
        # fev1_pre = 1.66, change = 200mL = 0.2L, change% = 0.2/1.66*100 = 12.05%
        result = bronchodilator_response(1.66, 1.86)
        self.assertTrue(result.is_significant)


class TestInterpretSpirometry(unittest.TestCase):
    """Test spirometry interpretation."""

    def test_normal_spirometry(self):
        """Normal values should classify as normal."""
        # Use predicted values for a healthy 40yo 175cm male
        fev1_p = predicted_fev1(40, 175, "M")
        fvc_p = predicted_fvc(40, 175, "M")
        result = interpret_spirometry(fev1_p, fvc_p, 40, 175, "M")
        self.assertEqual(result.pattern, "Normal spirometry")
        self.assertIsNone(result.severity)
        self.assertFalse(result.obstruction_present)
        self.assertFalse(result.restriction_suggested)

    def test_obstructive_mild(self):
        """FEV1/FVC < 0.70 with FEV1 >= 80% predicted = mild obstructive."""
        result = interpret_spirometry(3.0, 5.0, 60, 175, "M")
        self.assertIn("Obstructive", result.pattern)
        self.assertTrue(result.obstruction_present)
        self.assertEqual(result.severity, "Mild")

    def test_obstructive_moderate(self):
        """FEV1 50-79% predicted = moderate."""
        result = interpret_spirometry(2.0, 4.5, 60, 175, "M")
        self.assertIn("Obstructive", result.pattern)
        self.assertEqual(result.severity, "Moderate")

    def test_obstructive_severe(self):
        """FEV1 30-49% predicted = severe."""
        result = interpret_spirometry(1.2, 4.0, 60, 175, "M")
        self.assertIn("Obstructive", result.pattern)
        self.assertEqual(result.severity, "Severe")

    def test_obstructive_very_severe(self):
        """FEV1 < 30% predicted = very severe."""
        result = interpret_spirometry(0.5, 3.5, 60, 175, "M")
        self.assertIn("Obstructive", result.pattern)
        self.assertEqual(result.severity, "Very severe")

    def test_restrictive_pattern(self):
        """Normal ratio but low FVC = restrictive."""
        # Normal ratio but FVC < 80% predicted for 50yo 160cm F
        # predicted_fvc(50, 160, "F") ≈ 2.93, so FVC=2.2 gives ~75%
        result = interpret_spirometry(1.8, 2.2, 50, 160, "F")
        self.assertIn("Restrictive", result.pattern)
        self.assertFalse(result.obstruction_present)
        self.assertTrue(result.restriction_suggested)

    def test_mixed_pattern(self):
        """Low ratio AND low FVC = mixed."""
        result = interpret_spirometry(1.0, 2.5, 65, 170, "M")
        self.assertIn("Mixed", result.pattern)
        self.assertTrue(result.obstruction_present)
        self.assertTrue(result.restriction_suggested)

    def test_gold_staging(self):
        """Obstructive pattern should include GOLD stage."""
        result = interpret_spirometry(2.0, 4.5, 60, 175, "M")
        self.assertIsNotNone(result.gold_stage)
        self.assertIn("GOLD", result.gold_stage)

    def test_fev1_exceeds_fvc_raises(self):
        """FEV1 > FVC should raise ValueError."""
        with self.assertRaises(ValueError):
            interpret_spirometry(5.0, 3.0, 40, 175, "M")

    def test_negative_values_raises(self):
        with self.assertRaises(ValueError):
            interpret_spirometry(-1.0, 3.0, 40, 175, "M")


class TestBatchProcessing(unittest.TestCase):
    """Test CSV batch processing."""

    def test_batch_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inp = os.path.join(tmpdir, "in.csv")
            out = os.path.join(tmpdir, "out.csv")
            with open(inp, "w") as f:
                f.write("patient_id,fev1,fvc,age,height_cm,sex\n")
                f.write("P001,3.5,4.5,40,175,M\n")
                f.write("P002,2.0,4.0,60,175,M\n")
                f.write("P003,2.5,2.8,50,160,F\n")
            n = process_csv(inp, out)
            self.assertEqual(n, 3)
            self.assertTrue(os.path.exists(out))


class TestCLI(unittest.TestCase):
    """Test CLI interface."""

    def test_single_command(self):
        ret = main(["single", "--fev1", "3.5", "--fvc", "4.5",
                     "--age", "40", "--height", "175", "--sex", "M"])
        self.assertEqual(ret, 0)

    def test_predicted_command(self):
        ret = main(["predicted", "--age", "40", "--height", "175", "--sex", "M"])
        self.assertEqual(ret, 0)

    def test_no_command(self):
        ret = main([])
        self.assertEqual(ret, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
