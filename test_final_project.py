#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for Final ProblemSet."""

import os
from unittest import TestCase
from contextlib import contextmanager
from tempfile import TemporaryDirectory

import pandas as pd
import numpy as np
import dask.dataframe as dd
from luigi import build, LocalTarget
from final_project.tasks.tasks import DownloadCSV, AggregateWeeklyData, LatestWeeklyData, CountryDimension
from csci_utils.luigi.dask.target import CSVTarget
from csci_utils.luigi.task import Requirement, Requires, TargetOutput


class DownloadCSVTest(TestCase):
    def test_input_output(self):
        self.assertIsInstance(DownloadCSV().output(), CSVTarget)
        self.assertIsInstance(AggregateWeeklyData().input()["other"], CSVTarget)
        self.assertIsInstance(AggregateWeeklyData().output(), LocalTarget)

    def test_run_output(self):
        with TemporaryDirectory() as tmp:
            # Mock data
            dummy = pd.DataFrame(
                {
                    "location": ["Dummy", "Dummy", "Dummy"],
                    "date": ["2020-01-01", "2020-01-02", "2020-01-03"],
                    "new_cases": [10, 20, 30],
                    "stringency_index": [20, 20, 20],
                    "total_deaths": [1, 2, 5],
                    "population": [10000, 10000, 10000],
                    "total_tests": [50, 60, 70],
                    "median_age": [50, 60, 70],
                    "aged_65_older": [50, 60, 70],
                    "aged_70_older": [50, 60, 70],
                    "gdp_per_capita": [50, 60, 70],
                    "cardiovasc_death_rate": [50, 60, 70],
                    "diabetes_prevalence": [50, 60, 70],
                    "female_smokers": [50, 60, 70],
                    "male_smokers": [50, 60, 70],
                    "handwashing_facilities": [50, 60, 70],
                    "life_expectancy": [50, 60, 70],
                    "human_development_index": [50, 60, 70],

                }
            )
            # Define expected outputs
            expected_weekly_data = pd.DataFrame(
                {
                    "location": ["Dummy"],
                    "week": ["2019-12-30"],
                    "new_cases": [60],
                    "stringency_index": [20],
                    "total_deaths": [5],
                    "population": [10000],
                    "total_tests": [70],
                }
            )

            expected_latest_data = expected_weekly_data.copy()
            expected_latest_data = expected_latest_data.astype(
                {
                    "week": str,
                    "new_cases": np.float64,
                    "stringency_index": np.float64,
                    "total_deaths": np.float64,
                    "population": np.float64,
                    "total_tests": np.float64,
                }
            )
            expected_latest_data["death_per_population_pct"] = 5 * 100 / 10000
            expected_latest_data["tests_per_population"] = 70 / 10000

            expected_country_dimension = pd.DataFrame(
                {
                    "location": ["Dummy"],
                    "median_age": [70],
                    "aged_65_older": [70],
                    "aged_70_older": [70],
                    "gdp_per_capita": [70],
                    "cardiovasc_death_rate": [70],
                    "diabetes_prevalence": [70],
                    "female_smokers": [70],
                    "male_smokers": [70],
                    "handwashing_facilities": [70],
                    "life_expectancy": [70],
                    "human_development_index": [70]

                }
            )

            filepath = tmp + "/random.csv"
            file_target_path = tmp + "/data/"
            weekly_target_file_path = tmp + "/data/weekly_data.csv"
            latest_target_file_path = tmp + "/data/latest_data.csv"
            country_dim_target_file_path = tmp + "/data/country_dimension.csv"

            # Mock test class.
            class MockDownloadCSV(DownloadCSV):
                file_url = filepath
                target_path = file_target_path
                output = TargetOutput(
                    file_pattern=file_target_path,
                    ext="",
                    target_class=CSVTarget,
                    flag=False,
                )

            class MockAggregateWeekly(AggregateWeeklyData):
                other = Requirement(MockDownloadCSV)
                target_filename = weekly_target_file_path

            class MockLatestWeekly(LatestWeeklyData):
                other = Requirement(MockAggregateWeekly)
                target_filename = latest_target_file_path

            class MockCountry(CountryDimension):
                raw = Requirement(MockDownloadCSV)
                target_filename = country_dim_target_file_path

            # Write dummy data
            dummy.to_csv(filepath, index=False)

            build(
                [MockDownloadCSV(), MockAggregateWeekly(), MockLatestWeekly(), MockCountry()],
                local_scheduler=True,
            )

            # Read written data
            weekly_output = pd.read_csv(weekly_target_file_path)
            latest_output = pd.read_csv(latest_target_file_path)
            country_output = pd.read_csv(country_dim_target_file_path)

            # Check if file is present
            self.assertTrue(os.path.exists(file_target_path))
            self.assertTrue(os.path.exists(weekly_target_file_path))
            self.assertTrue(os.path.exists(latest_target_file_path))
            self.assertTrue(os.path.exists(country_dim_target_file_path))

            # Check data
            pd.testing.assert_frame_equal(expected_weekly_data, weekly_output)
            pd.testing.assert_frame_equal(expected_latest_data, latest_output)
            pd.testing.assert_frame_equal(expected_country_dimension, country_output)
