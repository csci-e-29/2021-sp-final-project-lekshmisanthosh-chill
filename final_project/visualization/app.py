import os
from pathlib import Path

import streamlit as st
import pandas as pd
import altair as alt


st.set_page_config(layout="wide")
alt.data_transformers.disable_max_rows()


def plot_scatter_with_regression(
    x_col: str, source: pd.DataFrame, y_col: str = "death_per_population_pct"
):
    """Helper function to plot scatter plots with regression lines for death 5.
    :args
        x_col: The X axis
        source: dataframe with the x_col and y_col
        y_col: The Y axis
    :returns
        alt.Chart layered chart object
    """
    scatter = (
        alt.Chart(source)
        .mark_circle(color="#E57373")
        .encode(
            x=x_col,
            y=alt.Y(y_col, title="Death per population in %"),
            tooltip=alt.Tooltip(["location"]),
        )
        .properties(width=400, height=250, title=f"Death per population % by {x_col}")
    )
    regression = scatter.transform_regression(x_col, y_col).mark_line(
        color="#E57373", opacity=0.4
    )
    return scatter + regression


def main():

    DATA_PATH = os.path.join(
        Path(os.path.dirname(os.path.realpath(__file__))).parent.parent, "data"
    )
    # Read data
    weekly_data = pd.read_csv(DATA_PATH + "/weekly_data.csv")
    latest_data = pd.read_csv(DATA_PATH + "/latest_data.csv")
    country_dimension = pd.read_csv(DATA_PATH + "/country_dimension.csv")

    # Do relevant joins
    country_dimension = country_dimension.merge(
        latest_data[["location", "death_per_population_pct", "tests_per_population"]],
        how="left",
    )
    list_of_countries = latest_data["location"]

    # Plot dashboards
    st.title("An observational study of covid 19 data")
    st.markdown(
        "This is the final project for CSCI-29. The data presented here has been extracted from [Our world in data](https://ourworldindata.org/). "
        "The information presented here examines the relationship between different socio-economic variables and covid impact, "
        "quantified in terms of % death and cases. The study is purely observational and no causational inference should be drawn from the data."
    )

    st.header(
        "Is there a relationship between stringency index and the number of cases?"
    )

    country_filter = st.selectbox("Select country", list_of_countries, index=0)
    st.markdown(
        "Stringency index is a composite measure based on nine response indicators including school closures, workplace closures, "
        "and travel bans, rescaled to a value from 0 to 100, 100 being strictest. Number of cases refer to the total number of cases reported for a given country."
    )

    weekly_new_cases = (
        alt.Chart(weekly_data[weekly_data.location == country_filter])
        .mark_line(color="#E57373")
        .encode(
            x="week:T",
            y=alt.Y("sum(new_cases)", title="Total number of new cases"),
            tooltip=alt.Tooltip(["location", "sum(new_cases)"]),
        )
        .properties(width=1000, height=500)
    )
    weekly_stringency = (
        alt.Chart(weekly_data[weekly_data.location == country_filter])
        .mark_bar(color="#CFD8DC", opacity=0.5)
        .encode(
            x="week:T",
            y=alt.Y("mean(stringency_index)", title="Mean Stringency Index"),
            tooltip=alt.Tooltip(["location", "mean(stringency_index)"]),
        )
        .properties(width=1000, height=500)
    )

    final = (
        alt.layer(weekly_stringency, weekly_new_cases)
        .resolve_scale(y="independent")
        .properties(title="Stringency Index vs the total number of cases")
        .interactive()
    )

    col1, col2 = st.beta_columns((3, 1))

    col1.write(final)
    col2.markdown(
        "The grey bar represents the stringency levels each week for the country chosen. "
        "The red line represents the total number of reported cases each week. "
        "We can observe a weak negative correlation between stringency index and reported cases."
        "Some countries (United States, for instance) were late to incorporate the stringency measures. "
        "Certain countries like India started off strong but after containing the first wave, they lowered the stringency measures."
        " The patterns that you see here should be taken with a grain of salt because there are other confounding factors in play,"
        "such as origin of new variants, some of which are very contagious and can cause an uptick in cases regardless of the stringency measures in place."
    )

    # Plot Section 2
    st.header(
        "Is there any noticable relationships between covid death % various socioeconomic variables?"
    )
    st.markdown(
        "Here, death % is the total # of recorded deaths expressed as a percentage of population. Each dot represents a country and the plots conver 106 countries."
    )
    grid = alt.vconcat(
        alt.hconcat(
            plot_scatter_with_regression("median_age", source=country_dimension),
            plot_scatter_with_regression("gdp_per_capita", source=country_dimension),
        ),
        alt.hconcat(
            plot_scatter_with_regression(
                "cardiovasc_death_rate", source=country_dimension
            ),
            plot_scatter_with_regression(
                "diabetes_prevalence", source=country_dimension
            ),
        ),
        alt.hconcat(
            plot_scatter_with_regression(
                "handwashing_facilities", source=country_dimension
            ),
            plot_scatter_with_regression(
                "human_development_index", source=country_dimension
            ),
        ),
    )

    col1, col2 = st.beta_columns((3, 1))
    col1.write(grid)
    col2.markdown(
        "**Median Age**: It is interesting to note that the higher the median age, greater is the dealth %. This seems to be intuitive since older population is more "
        "vulnerable to the virus. "
    )

    col2.markdown(
        "**GDC Per Capita**: The pattern that we see here is slightly misleading as it shows there are more death rates in developed countries. It is likely that the underdeveloped countries may not be reporting accurate death tolls. "
        "It is also possible that developed countries may have more access to testing."
    )

    col2.markdown(
        "**Human Development Index**: Human development index also shows a pattern similar to GDP per capita. HDI is derived from GDP per capita."
    )

    col2.markdown(
        "**Diabetes prevalence and cardiovascular health**: No discernable patterns found. There is a very weak negative correlation between the 2 variables."
    )

    # Plot section 3

    st.header("Do countries with higher GDP per capita tend to do more testing?")
    st.markdown(
        "Here, the bar length represent the ratio between the # of tests done till date by population. The color encodes the gdp per capita."
    )

    test_by_gdp = country_dimension[
        ["location", "gdp_per_capita", "tests_per_population"]
    ].dropna()

    test_by_gdp = test_by_gdp.sort_values("tests_per_population", ascending=False).iloc[
        :60,
    ]

    tests_chart = (
        alt.Chart(test_by_gdp)
        .mark_bar()
        .encode(
            x=alt.X("location", sort="-y"),
            y="tests_per_population",
            color=alt.Color("gdp_per_capita", scale=alt.Scale(scheme="reds")),
        )
    ).properties(height=500)

    st.write(tests_chart)


if __name__ == "__main__":
    main()
