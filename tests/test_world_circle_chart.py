import unittest

from workflows.build_world_circle_chart import centered_log_limits, growth_extremes


class CenteredLogLimitsTest(unittest.TestCase):
    def test_limits_are_fixed_and_symmetric_around_world_mean(self):
        data = {
            "2000": {"WLD": 10_000, "AAA": 1_000, "BBB": 20_000},
            "2001": {"WLD": 20_000, "AAA": 1_000, "BBB": 80_000},
        }

        lower, upper = centered_log_limits(data, {"AAA", "BBB"})

        self.assertAlmostEqual(lower * upper, 1)
        self.assertLess(lower, 0.05)
        self.assertGreater(upper, 20)

    def test_aggregate_values_do_not_affect_country_limits(self):
        data = {
            "2000": {
                "WLD": 10_000,
                "AAA": 5_000,
                "BBB": 20_000,
                "AGG": 1,
            }
        }

        lower, upper = centered_log_limits(data, {"AAA", "BBB"})

        self.assertGreater(lower, 0.1)
        self.assertLess(upper, 10)

    def test_missing_world_mean_is_rejected(self):
        with self.assertRaises(RuntimeError):
            centered_log_limits({"2000": {"AAA": 5_000}}, {"AAA"})


class GrowthExtremesTest(unittest.TestCase):
    def test_ranks_only_countries_with_both_endpoint_values(self):
        data = {
            "1990": {"AAA": 100, "BBB": 100, "CCC": 100, "AGG": 1},
            "2025": {"AAA": 50, "BBB": 200, "CCC": 300, "AGG": 1_000},
        }

        winners, losers = growth_extremes(
            data, {"AAA", "BBB", "CCC"}, count=1
        )

        self.assertEqual(winners, ["CCC"])
        self.assertEqual(losers, ["AAA"])

    def test_requires_enough_comparable_countries(self):
        data = {"1990": {"AAA": 100}, "2025": {"AAA": 200}}

        with self.assertRaises(RuntimeError):
            growth_extremes(data, {"AAA"}, count=1)


if __name__ == "__main__":
    unittest.main()