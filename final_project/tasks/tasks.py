""" Module which performs ETL on OWID Covid 19 data.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import dask.dataframe as dd
from luigi import ExternalTask, Task, build, LocalTarget

from csci_utils.luigi.dask.target import CSVTarget
from csci_utils.luigi.task import Requirement, Requires, TargetOutput


class DownloadCSV(ExternalTask):
    """Luigi Task to download Covid data csv file from OWID and save the results as a dask collection."""

    file_url = "https://covid.ourworldindata.org/data/owid-covid-data.csv"
    parent_directory = Path(os.path.dirname(os.path.realpath(__file__))).parent.parent
    target_path = "data/covid_data"

    local_directory = os.path.join(str(parent_directory), "data/covid_data/")
    output = TargetOutput(
        file_pattern=local_directory, ext="", target_class=CSVTarget, flag=False
    )

    def run(self):
        """Writes a set of CSV files to data/covid_data folder."""
        data = pd.read_csv(self.file_url)
        ddf = dd.from_pandas(data, chunksize=5000)
        self.output().write_dask(collection=ddf, filename=self.target_path)


class AggregateWeeklyData(Task):
    """Luigi task which aggregates covid daily stats by week."""

    requires = Requires()
    other = Requirement(DownloadCSV)

    parent_directory = Path(os.path.dirname(os.path.realpath(__file__))).parent.parent
    target_filename = os.path.join(str(parent_directory), "data/weekly_data.csv")

    def output(self):
        """Specifies the LocalTarget output for the task"""
        return LocalTarget(self.target_filename)

    def run(self):
        """Aggregates case volume, stringency index and additional stats by country and week.
        Writes the results to data/weekly_data.csv
        """
        raw_data = self.input()["other"].read_dask(filename="*.part").compute()
        raw_data["date"] = pd.to_datetime(raw_data.date)
        raw_data["week"] = raw_data["date"].apply(
            lambda x: x - pd.Timedelta(days=x.weekday())
        )
        raw_data["week"] = raw_data["week"].dt.date.apply(lambda x: str(x))

        weekly_data = (
            raw_data.groupby(["location", "week"])
            .agg(
                {
                    "new_cases": "sum",
                    "stringency_index": "max",
                    "total_deaths": "max",
                    "population": "max",
                    "total_tests": "max",
                }
            )
            .reset_index()
            .dropna()
        )

        weekly_data.to_csv(self.target_filename, index=False)


class LatestWeeklyData(Task):
    """Luigi Task which identifies the latest weekly snapshot for each country."""

    requires = Requires()
    other = Requirement(AggregateWeeklyData)

    parent_directory = Path(os.path.dirname(os.path.realpath(__file__))).parent.parent
    target_filename = os.path.join(str(parent_directory), "data/latest_data.csv")

    def output(self):
        """Specifies the LocalTarget output for the task."""
        return LocalTarget(self.target_filename)

    def run(self):
        """Identifies the latest summary statistic by country and writes the results to data/latest_data.csv"""
        with self.input()["other"].open("r") as f:
            data = f.readlines()

        rows = [ele.strip().split(",") for ele in data]
        column_names = rows.pop(0)
        weekly_data = pd.DataFrame(rows, columns=column_names)
        datatypes = {
            "week": str,
            "new_cases": np.float64,
            "stringency_index": np.float64,
            "total_deaths": np.float64,
            "population": np.float64,
            "total_tests": np.float64,
        }
        weekly_data = weekly_data.astype(datatypes)

        max_week = weekly_data.groupby("location").agg({"week": "max"}).reset_index()
        latest_data = weekly_data.merge(max_week)
        latest_data["death_per_population_pct"] = (
            latest_data["total_deaths"] * 100 / latest_data["population"]
        )
        latest_data["tests_per_population"] = (
            latest_data["total_tests"] / latest_data["population"]
        )
        latest_data.to_csv(self.target_filename, index=False)


class CountryDimension(Task):
    """Luigi Task to create the country dimension table for lookups."""

    requires = Requires()
    raw = Requirement(DownloadCSV)

    parent_directory = Path(os.path.dirname(os.path.realpath(__file__))).parent.parent
    target_filename = os.path.join(str(parent_directory), "data/country_dimension.csv")

    def output(self):
        """Specifies the LocalTarget output for the task."""
        return LocalTarget(self.target_filename)

    def run(self):
        """Writes the country level statistics to data/country_dimension.csv"""
        raw_data = self.input()["raw"].read_dask(filename="*.part").compute()

        country_dimension = (
            raw_data.groupby(["location"])
            .agg(
                {
                    "median_age": "max",
                    "aged_65_older": "max",
                    "aged_70_older": "max",
                    "gdp_per_capita": "max",
                    "cardiovasc_death_rate": "max",
                    "diabetes_prevalence": "max",
                    "female_smokers": "max",
                    "male_smokers": "max",
                    "handwashing_facilities": "max",
                    "life_expectancy": "max",
                    "human_development_index": "max",
                }
            )
            .reset_index()
        )

        country_dimension.to_csv(self.target_filename, index=False)


if __name__ == "__main__":  # pragma: no cover
    build(
        [AggregateWeeklyData(), LatestWeeklyData(), CountryDimension()],
        local_scheduler=True,
    )
