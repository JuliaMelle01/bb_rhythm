from wetterdienst.provider.dwd.observation import (
    DwdObservationRequest,
    DwdObservationResolution,
)
from wetterdienst import Settings

from functools import reduce
import pandas as pd


def get_weather_parameter_df(
    dt_from, dt_to, parameter, station_name="Berlin-Tempelhof"
):
    settings = Settings(tidy=True, si_units=False, humanize=True)
    parameter = [(param) for param in parameter]
    stations = DwdObservationRequest(
        parameter=parameter,
        resolution=DwdObservationResolution.MINUTE_10,
        start_date=dt_from,
        end_date=dt_to,
        settings=settings,
    ).filter_by_name(name=station_name)
    weather_lst = []
    for res in stations.values.query():
        weather_lst.append(res)
    return weather_lst[0].df


def combine_weather_frames(df):
    dfs = []
    for name, group in df.groupby(["parameter"]):
        group.rename(columns={"value": name}, inplace=True)
        group.drop(columns=["parameter"], inplace=True)
        dfs.append(group)
    df_merged = reduce(
        lambda left, right: pd.merge(
            left,
            right,
            left_on=["date", "station_id"],
            right_on=["date", "station_id"],
            how="outer",
        ),
        dfs,
    )
    return df_merged


def get_weather_frame(
    dt_from,
    dt_to,
    station_name="Berlin-Tempelhof",
    weather_params=["wind_speed", "temperature_air_mean_200"],
):
    df = get_weather_parameter_df(
        dt_from, dt_to, parameter=weather_params, station_name=station_name
    )
    df.drop(columns=["quality", "dataset"], inplace=True)
    weather_df = combine_weather_frames(df)
    return weather_df


def combine_weather_velocity_dfs(velocity_df, weather_df):
    velocity_df.rename(columns={"datetime": "date"}, inplace=True)
    velocity_df.drop(columns=["time_passed"], inplace=True)
    velocity_df = velocity_df[
        ~(pd.isnull(velocity_df.velocity) or pd.isinf(velocity_df.velocity))
    ]
    velocity_df = (
        velocity_df.date.dt.round("10min")
        .groupby(["date"])["velocity"]
        .mean()
        .reset_index()
    )
    weather_df.drop(columns=["station_id"], inplace=True)
    velocity_weather_df = weather_df.set_index("date").join(
        velocity_df.set_index("date"), on="date", how="inner"
    )
    return velocity_weather_df
