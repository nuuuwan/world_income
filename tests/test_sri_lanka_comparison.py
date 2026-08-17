import unittest

from workflows.build_sri_lanka_comparison import comparison_group


class ComparisonGroupTest(unittest.TestCase):
    def test_thresholds_are_inclusive_for_similar_group(self):
        reference_value = 100

        self.assertEqual(comparison_group(79.99, reference_value), "lower")
        self.assertEqual(comparison_group(80, reference_value), "similar")
        self.assertEqual(comparison_group(125, reference_value), "similar")
        self.assertEqual(comparison_group(125.01, reference_value), "higher")

    def test_missing_values_have_no_data(self):
        self.assertEqual(comparison_group(None, 100), "no_data")
        self.assertEqual(comparison_group(100, None), "no_data")


if __name__ == "__main__":
    unittest.main()