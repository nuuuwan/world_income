import unittest

import pandas as pd

from workflows.asia_gdp_barchart import filter_asian_countries


class FilterAsianCountriesTest(unittest.TestCase):
    def test_keeps_only_asian_countries(self):
        countries = pd.DataFrame(
            {
                "iso": ["LKA", "FRA", "JPN"],
                "CONTINENT": ["Asia", "Europe", "Asia"],
            }
        )

        filtered = filter_asian_countries(countries)

        self.assertEqual(list(filtered["iso"]), ["LKA", "JPN"])