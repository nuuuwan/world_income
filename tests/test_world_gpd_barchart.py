import unittest

import pandas as pd

from workflows.world_gpd_barchart import (
    filter_countries_by_population,
    log_limits,
    ranked_country_label,
    region_extremes,
    sorted_country_values,
)


class RankedCountryLabelTest(unittest.TestCase):
    def test_uses_one_based_rank(self):
        country = pd.Series({"iso": "LKA", "NAME_LONG": "Sri Lanka"}, name=11)

        self.assertEqual(ranked_country_label(country), "Sri Lanka (12)")

    def test_uses_country_name_override(self):
        country = pd.Series(
            {"iso": "ARE", "NAME_LONG": "United Arab Emirates"}, name=2
        )

        self.assertEqual(ranked_country_label(country, {"ARE": "UAE"}), "UAE (3)")


class PopulationFilterTest(unittest.TestCase):
    def test_excludes_only_countries_below_one_million(self):
        countries = pd.DataFrame({"iso": ["LOW", "EDGE", "HIGH", "MISS"]})
        population = {"LOW": 999_999, "EDGE": 1_000_000, "HIGH": 2_000_000}

        filtered = filter_countries_by_population(countries, population)

        self.assertEqual(list(filtered["iso"]), ["EDGE", "HIGH", "MISS"])


class SortedCountryValuesTest(unittest.TestCase):
    def setUp(self):
        self.countries = pd.DataFrame(
            {
                "iso": ["LKA", "AAA", "BBB"],
                "CONTINENT": ["Asia", "Africa", "Europe"],
            }
        )

    def test_sorts_positive_country_values_from_lowest_to_highest(self):
        year_data = {"LKA": 20, "AAA": 10, "BBB": 30, "WLD": 25}

        bars = sorted_country_values(self.countries, year_data)

        self.assertEqual(list(bars["iso"]), ["AAA", "LKA", "BBB"])
        self.assertEqual(list(bars["value"]), [10, 20, 30])

    def test_can_sort_country_values_from_highest_to_lowest(self):
        year_data = {"LKA": 20, "AAA": 10, "BBB": 30}

        bars = sorted_country_values(self.countries, year_data, ascending=False)

        self.assertEqual(list(bars["iso"]), ["BBB", "LKA", "AAA"])
        self.assertEqual(list(bars["value"]), [30, 20, 10])

    def test_excludes_missing_and_non_positive_values(self):
        year_data = {"LKA": 0, "AAA": None, "BBB": 30}

        bars = sorted_country_values(self.countries, year_data)

        self.assertEqual(list(bars["iso"]), ["BBB"])


class LogLimitsTest(unittest.TestCase):
    def test_limits_cover_all_country_values_but_not_aggregates(self):
        countries = pd.DataFrame(
            {"iso": ["AAA", "BBB"], "CONTINENT": ["Africa", "Europe"]}
        )
        data = {
            "2000": {"AAA": 700, "BBB": 20_000, "WLD": 1},
            "2001": {"AAA": 800, "BBB": 125_000, "HIC": 10_000_000},
        }

        lower, upper = log_limits(countries, data)

        self.assertEqual(lower, 100)
        self.assertGreater(upper, 125_000)
        self.assertLess(upper, 10_000_000)


class RegionExtremesTest(unittest.TestCase):
    def test_selects_lowest_and_highest_country_in_each_region(self):
        bars = pd.DataFrame(
            {
                "iso": ["AAA", "BBB", "CCC", "DDD"],
                "CONTINENT": ["Africa", "Europe", "Africa", "Europe"],
                "value": [10, 20, 30, 40],
            }
        )

        extremes = region_extremes(bars)

        self.assertEqual(
            [country["iso"] for country in extremes],
            ["AAA", "CCC", "BBB", "DDD"],
        )
if __name__ == "__main__":
    unittest.main()