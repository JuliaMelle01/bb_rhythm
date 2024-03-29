import matplotlib.colors
from matplotlib import rcParams
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import seaborn as sns
import numpy as np
import numpy.ma as ma
import datetime
from scipy.ndimage import gaussian_filter1d
from skimage import filters

from . import utils
from . import rhythm
from . import interactions


# Fig. 1
def plot_velocity_over_time_with_weather(
    velocity_df,
    weather_df,
    dt_from,
    dt_to,
    age_map=True,
    age_map_step_size=5,
    smoothing=False,
    rounded=False,
    round_time="60min",
    age_bins=None,
    imshow=False,
    image_path=None,
    y_lim=None,
    axs=None,
):
    """

    :param velocity_df:
    :param weather_df:
    :param dt_from:
    :param dt_to:
    :param age_map:
    :param age_map_step_size:
    :param smoothing:
    :param rounded:
    :param round_time:
    :param age_bins:
    :param imshow:
    :param image_path:
    :param y_lim:
    :param axs:
    :return:
    """
    if axs is None:
        # create figure
        fig, axs = plt.subplots(
            3,
            1,
            figsize=(16, 10),
            sharex=True,
            gridspec_kw={"height_ratios": [8, 1, 1]},
        )
        fig.suptitle("Mean movement speed over time")
        fig.tight_layout()
    else:
        axs[0].set_title("Mean movement speed over time")

    # plot velocities
    plot_velocity_per_age_group(
        velocity_df,
        axs[0],
        dt_from=dt_from,
        dt_to=dt_to,
        age_map=age_map,
        age_map_step_size=age_map_step_size,
        age_bins=age_bins,
        smoothing=smoothing,
        rounded=rounded,
        round_time=round_time,
        y_lim=y_lim,
    )

    # plot weather
    plot_weather_data(weather_df, axs, dt_from, dt_to)

    # plot settings
    plt.xticks(rotation=90)
    plt.xlabel("Time")

    # show and save plot
    if imshow:
        plt.show()

    if image_path is not None:
        plt.savefig(image_path)


def plot_weather_data(weather_df, axs, dt_from, dt_to):
    # subset time
    weather_df = weather_df[
        (weather_df["date"] >= dt_from) & (weather_df["date"] < dt_to)
    ]

    # plot temperature
    plot_weather_subplot(
        axs[1], dt_from, dt_to, "Temp [C°]", "temperature_air_mean_200", weather_df
    )

    # plot wind speed
    plot_weather_subplot(axs[2], dt_from, dt_to, "Wind [m/s]", "wind_speed", weather_df)


def plot_weather_subplot(ax, dt_from, dt_to, y_label, column, weather_df):
    ax.plot(weather_df["date"], weather_df[column])
    ax.set_ylabel(y_label)
    ax.grid(True)

    # add grey bars for nighttime
    add_grey_nighttime_bars(ax, weather_df)
    ax.set_xlim(xmin=dt_from, xmax=dt_to)


def add_grey_nighttime_bars(ax, df):
    for day in np.unique([day.date() for day in df.date]):
        day = datetime.datetime.combine(day, df.date.iloc[0].to_pydatetime().time())
        ax.axvspan(
            day,
            day + datetime.timedelta(hours=6),
            facecolor="lightgrey",
            edgecolor=None,
            alpha=0.5,
            linewidth=0,
        )
        ax.axvspan(
            day + datetime.timedelta(hours=18),
            day + datetime.timedelta(hours=24),
            facecolor="lightgrey",
            linewidth=0,
            edgecolor=None,
            alpha=0.5,
        )


def add_distance_bars(ax, distance_series, n_bins, palette="Greys"):
    distances = pd.qcut(distance_series.unique(), n_bins)
    distance_palette = sns.color_palette(palette, len(distances.unique()))
    i = 0
    for distance in sorted(distances.unique()):
        ax.axvspan(distance.left, distance.right, color=distance_palette[i], alpha=0.3)
        print(distance)
        i += 1


def plot_velocity_per_age_group(
    time_age_velocity_df,
    ax,
    dt_from,
    dt_to,
    age_map=False,
    age_bins=None,
    age_map_step_size=5,
    age_bins_n=None,
    bin_max_n=None,
    bin_labels=None,
    smoothing=False,
    rounded=False,
    round_time="60min",
    y_lim=None,
):
    """

    :param time_age_velocity_df:
    :param ax:
    :param dt_from:
    :param dt_to:
    :param age_map:
    :param age_bins:
    :param age_map_step_size:
    :param age_bins_n:
    :param bin_max_n:
    :param bin_labels:
    :param smoothing:
    :param rounded:
    :param round_time:
    :param y_lim:
    :return:
    """
    # remove NaNs
    time_age_velocity_df = time_age_velocity_df[~pd.isnull(time_age_velocity_df.age)]

    # subset time
    time_age_velocity_df = time_age_velocity_df[
        (time_age_velocity_df["date"] >= dt_from)
        & (time_age_velocity_df["date"] < dt_to)
    ]

    if rounded:
        time_age_velocity_df = round_time_age_velocity_df(
            round_time, time_age_velocity_df
        )

    # add human-readable age bins to df
    sorted_by = "age"
    if age_map:
        binning = utils.Binning(bin_name="Age [days]", bin_parameter=sorted_by)
        binning.add_bins_to_df(
            time_age_velocity_df,
            n_bins=age_bins_n,
            step_size=age_map_step_size,
            bin_max_n=bin_max_n,
            bins=age_bins,
            bin_labels=bin_labels,
        )
        sorted_by = binning.bin_name

    # create color palette
    palette = create_age_color_palette(
        binning.bins.unique(), sorted_by, time_age_velocity_df
    )

    # smooth lines per group, but still plot transparently 95% confidence interval for non-smoothed lines
    if smoothing:
        plot_smoothed_age_velocity_over_time(
            ax, palette, sorted_by, time_age_velocity_df
        )

    # plot non-smoothed lines
    else:
        plot_non_smoothed_age_velocity_over_time(
            ax, palette, sorted_by, time_age_velocity_df
        )

    # add grey bars for nighttime
    add_grey_nighttime_bars(ax, time_age_velocity_df)

    # axis settings
    ax.set_ylabel("Mean movement speed [mm/s]")
    ax.set_xlim(xmin=dt_from, xmax=dt_to)
    if y_lim is not None:
        ax.set_ylim(ymin=y_lim[0], ymax=y_lim[1])
    ax.legend(loc="upper right", title="Age [days]")


def plot_non_smoothed_age_velocity_over_time(
    ax, palette, sorted_by, time_age_velocity_df
):
    sns.lineplot(
        data=time_age_velocity_df,
        x="date",
        y="velocity",
        hue=sorted_by,
        ax=ax,
        palette=palette,
    )


def plot_smoothed_age_velocity_over_time(
    ax, palette, sorted_by, time_age_velocity_df, hue_order=None
):
    # get smoothed velocities
    time_age_velocity_df = get_smoothed_velocities(sorted_by, time_age_velocity_df)

    # plot
    sns.lineplot(
        data=time_age_velocity_df,
        x="date",
        y="velocity",
        hue=sorted_by,
        linewidth=0,
        legend=False,
        ax=ax,
        palette=palette,
        hue_order=hue_order,
    )
    sns.lineplot(
        data=time_age_velocity_df,
        x="date",
        y="velocity_smoothed",
        errorbar=None,
        hue=sorted_by,
        ax=ax,
        palette=palette,
        hue_order=hue_order,
    )


def get_smoothed_velocities(sorted_by, time_age_velocity_df):
    time_age_velocity_df.loc[:, "velocity_smoothed"] = time_age_velocity_df["velocity"].copy()
    for age_bin in time_age_velocity_df[sorted_by].unique():
        time_age_velocity_df.loc[
            time_age_velocity_df.loc[:, sorted_by] == age_bin, "velocity_smoothed"
        ] = gaussian_filter1d(
            time_age_velocity_df["velocity"].loc[
                (time_age_velocity_df.loc[:, sorted_by] == age_bin,)
            ],
            sigma=4,
        )
    return time_age_velocity_df


def create_age_color_palette(age_map, sorted_by, time_age_velocity_df):
    """

    :param age_map:
    :param sorted_by:
    :param time_age_velocity_df:
    :return:
    """
    if age_map is not None:
        palette = sns.color_palette(
            "viridis", len(time_age_velocity_df[sorted_by].unique()) * 4
        )
        palette = [
            palette[i * 4] for i in range(len(time_age_velocity_df[sorted_by].unique()))
        ]
    else:
        palette = sns.color_palette(
            "viridis", len(time_age_velocity_df[sorted_by].unique())
        )
    return palette


def round_time_age_velocity_df(round_time, time_age_velocity_df):
    """

    :param round_time:
    :param time_age_velocity_df:
    :return:
    """
    time_age_velocity_df["date"] = time_age_velocity_df["date"].dt.round(round_time)
    time_age_velocity_df = (
        time_age_velocity_df.groupby(["date", "age"])["velocity"].mean().reset_index()
    )
    return time_age_velocity_df


# Fig. 2
def plot_boxplot(circadianess_df, ax, x="age_bins", order=None):
    sns.boxplot(
        circadianess_df,
        ax=ax,
        x=x,
        y="mean",
        width=0.5,
        flierprops={"marker": "o", "color": (0, 0, 0, 0)},
        boxprops={"facecolor": (0, 0, 0, 0), "edgecolor": "blue"},
        whiskerprops={"color": "blue"},
        medianprops={"color": "green", "linewidth": 1},
        showfliers=True,
        capprops={"color": "blue"},
        order=order,
    )


def set_fig_props_circadianess_per_age_plot(fig):
    fig.supxlabel("Age [days]")
    fig.supylabel("")
    fig.suptitle("Proportion of circadian tested bees")


def plot_raincloudplot(circadianess_df, ax, x="age_bins", hue_norm=None, order=None):
    # Create violin plots without mini-boxplots inside.
    sns.violinplot(
        data=circadianess_df,
        x=x,
        y="mean",
        color="mediumslateblue",
        cut=0,
        inner=None,
        ax=ax,
        order=order,
    )

    # Clip the lower half of each violin.
    for item in ax.collections:
        x0, y0, width, height = item.get_paths()[0].get_extents().bounds
        item.set_clip_path(
            plt.Rectangle((x0, y0), width / 2, height, transform=ax.transData)  # /2,
        )

    # Create strip plots with partially transparent points of different colors depending on the group.
    num_items = len(ax.collections)
    sns.stripplot(
        data=circadianess_df,
        x=x,
        y="mean",
        hue="count",
        size=7,
        ax=ax,
        hue_norm=hue_norm,
        order=order,
    )

    # Shift each strip plot strictly below the correponding volin.
    for item in ax.collections[num_items:]:
        for pos in item.get_offsets():
            pos[0] = pos[0] + 0.125

    # Create narrow boxplots on top of the corresponding violin and strip plots, with thick lines, the mean values, without the outliers.
    sns.boxplot(
        data=circadianess_df,
        x=x,
        y="mean",
        width=0.25,
        showfliers=False,
        showmeans=True,
        meanprops=dict(markerfacecolor="lightgreen", markersize=5, zorder=3),
        boxprops=dict(facecolor=(0, 0, 0, 0), linewidth=3, zorder=3),
        whiskerprops=dict(linewidth=3),
        capprops=dict(linewidth=3),
        medianprops=dict(linewidth=3),
        order=order,
        ax=ax,
    )


def plot_violin_swarm_plot(
    circadianess_df,
    ax,
    x="age_bins",
    size_norm=None,
    date_ann=False,
    count_ann=False,
    order=None,
):
    # get coordinates from swarm plot
    sns.swarmplot(data=circadianess_df, x=x, y="mean", ax=ax, size=7.0)
    coordinates = [
        ma.getdata(ax.collections[i].get_offsets()) for i in range(len(ax.collections))
    ]
    ax.clear()

    # plot violins
    sns.violinplot(
        data=circadianess_df,
        x=x,
        y="mean",
        palette=["lightgrey"],
        cut=0,
        saturation=0.5,
        scale="width",
        orient="v",
        ax=ax,
        inner="quartile",
        alpha=0.5,
        order=order,
    )
    circadianess_df["count"][circadianess_df["count"] == "nan"] = 0.0

    # plot scatter
    if date_ann:
        sns.scatterplot(
            data=circadianess_df,
            x=x,
            y="mean",
            size="count",
            hue="date",
            palette="viridis",
            size_norm=size_norm,
            ax=ax,
        )
    else:
        sns.scatterplot(
            data=circadianess_df,
            x=x,
            y="mean",
            size="count",
            size_norm=size_norm,
            ax=ax,
        )

    # annotate number of counts
    if count_ann:
        for x, y, count in zip(
            circadianess_df[x], circadianess_df["mean"], circadianess_df["count"]
        ):
            ax.annotate(count, xy=(x, y))

    # use coordinates from swarm plot to spread scatters
    ax_index = find_ax_collection_for_plotting(ax)
    ax.collections[ax_index].set_offsets(
        [item for sublist in coordinates for item in sublist]
    )


def find_ax_collection_for_plotting(ax):
    ax_index = 0
    for i in range(len(ax.collections)):
        if ax.collections[i].get_offsets().size != 0:
            ax_index = i
    return ax_index


def plot_circadianess_per_age_group(
    circadianess_df,
    plot_type="boxplot",
    young=False,
    file_path=None,
    age_map_step_size=5,
    age_bins=None,
    age_map=False,
    bin_max_n=None,
    bin_labels=None,
    age_bins_n=None,
    bin_parameter="age",
    bin_name="Age [days]",
    remove_none=True,
):
    # calculate well tested circadianess
    rhythm.calculate_well_tested_circadianess_cosinor(circadianess_df)

    # add human-readable age bins to df
    binning = utils.Binning(bin_name=bin_name, bin_parameter=bin_parameter)
    circadianess_df = binning.add_bins_to_df(
        circadianess_df,
        n_bins=age_bins_n,
        step_size=age_map_step_size,
        bin_max_n=bin_max_n,
        remove_none=remove_none,
        bins=age_bins,
        bin_labels=bin_labels,
    )

    circadianess_df_young = None
    if young:
        # get subset of young bees
        circadianess_df_young = circadianess_df[circadianess_df["age"] <= 5]

        # Create dataframe with aggregated mean and count of well tested circadianess per day
        circadianess_df_young = rhythm.create_mean_count_circadianess_per_day_df(
            circadianess_df_young, column="age"
        )

    # Create dataframe with aggregated mean and count of well tested circadianess per day
    circadianess_df = rhythm.create_mean_count_circadianess_per_day_df(
        circadianess_df, column=binning.bin_name
    )

    # get count norm for shared legend
    min_count = circadianess_df["count"].min()
    max_count = circadianess_df["count"].max()

    plot_agg_well_tested_circadianess_per_bee_age(
        circadianess_df,
        circadianess_df_young,
        max_count,
        min_count,
        plot_type,
        young,
        file_path,
        binning,
    )


def plot_agg_well_tested_circadianess_per_bee_age(
    circadianess_df,
    circadianess_df_young,
    max_count=None,
    min_count=None,
    plot_type="boxplot",
    young=False,
    file_path=None,
    binning=None,
):
    if young:
        # create figure and subplots
        fig, (ax0, ax1) = plt.subplots(
            1, 2, sharey=True, gridspec_kw={"width_ratios": [3, 7]}, figsize=(16, 8)
        )

        # plot
        plot_agg_circadianess_according_plot_type(
            ax=ax0,
            circadianess_df=circadianess_df_young,
            norm=(min_count, max_count),
            plot_type=plot_type,
            x="age",
        )

        # set axis properties
        if ax0.get_legend():
            ax0.legend().set_visible(False)
        set_ax_props_circadianess_per_age_group_plot(ax0)

    else:
        # create figure and subplots
        fig, ax1 = plt.subplots(1, 1, figsize=(15, 10))

    # plot
    plot_agg_circadianess_according_plot_type(
        ax=ax1,
        circadianess_df=circadianess_df,
        norm=(min_count, max_count),
        plot_type=plot_type,
        x=binning.bin_name,
        order=sorted(list(pd.Series(binning.bin_labels).dropna().unique())),
    )

    # set axis properties
    if ax1.get_legend():
        ax1.legend(
            bbox_to_anchor=(1.02, 1),
            loc="upper left",
            borderaxespad=0,
            title="Samples per day",
        )
    set_ax_props_circadianess_per_age_group_plot(ax1)

    # set label properties
    set_fig_props_circadianess_per_age_plot(fig)

    # set plt properties
    plt.ylim(0.0, 1.1)
    plt.tight_layout()
    if file_path:
        plt.savefig(file_path)


def plot_agg_circadianess_according_plot_type(
    ax=None,
    circadianess_df=None,
    norm=None,
    plot_type="boxplot",
    x="Age [days]",
    date_ann=False,
    count_ann=False,
    order=None,
):
    if plot_type == "boxplot":
        plot_boxplot(circadianess_df, x=x, ax=ax, order=order)
    elif plot_type == "violin_swarm":
        plot_violin_swarm_plot(
            circadianess_df,
            ax=ax,
            x=x,
            size_norm=norm,
            date_ann=date_ann,
            count_ann=count_ann,
            order=order,
        )
    elif plot_type == "raincloud":
        plot_raincloudplot(circadianess_df, ax=ax, x=x, hue_norm=norm, order=order)
    else:
        raise ValueError(
            "Incorrect plot type. Possible types: ['boxplot', 'violin_swarm', 'raincloud']"
        )


def set_ax_props_circadianess_per_age_group_plot(ax):
    # set step size ax ticks
    ax.yaxis.set_major_locator(ticker.MultipleLocator(0.1))

    # set ax labels
    ax.set_xlabel("")
    ax.set_ylabel("")


# Fig. 5
def get_bin_distributions_as_histmap(
    df,
    plot_path,
    group_type1="bins_non_focal",
    group_type2="bins_focal",
    bin_func=True,
    bin_parameter="circadianess",
    n_bins=6,
    step_size=None,
    bin_max_n=None,
    remove_none=True,
    change_type1="vel_change_bee_focal",
    printing=True,
):
    if bin_func:
        binning = utils.Binning(bin_name=group_type1, bin_parameter=bin_parameter)
        df = binning.add_bins_to_df(
            df,
            n_bins=n_bins,
            step_size=step_size,
            bin_max_n=bin_max_n,
            remove_none=remove_none,
        )
        binning = utils.Binning(bin_name=group_type2, bin_parameter=bin_parameter)
        df = binning.add_bins_to_df(
            df,
            n_bins=n_bins,
            step_size=step_size,
            bin_max_n=bin_max_n,
            remove_none=remove_none,
        )

    # print info per bin
    if printing:
        for name, group in df[[group_type1, group_type2, change_type1]].groupby(
            [group_type1, group_type2]
        ):
            print(name)
            print("\n")
            print(group.describe())
            print("\n\n")

    # plot distribution per bin as histogram
    rcParams.update({"figure.autolayout": True})
    g = sns.FacetGrid(
        df[[group_type1, group_type2, change_type1]],
        col=group_type2,
        row=group_type1,
        margin_titles=True,
        row_order=df[group_type1].unique().categories[::-1],
    )
    g.map(sns.histplot, change_type1, kde=True)
    g.figure.subplots_adjust(wspace=0.02, hspace=0.02)
    plt.savefig(plot_path)


def plot_bins_velocity_focal_non_focal(
    combined_df,
    plot_path=None,
    axs=None,
    bin_parameter2="r_squared_focal",
    bin_parameter1="r_squared_non_focal",
    n_bins=6,
    bins=None,
    step_size=None,
    bin_max_n=None,
    remove_none=True,
    bin_labels=None,
    change_type="vel_change_bee_focal",
    group_type1="bins_non_focal",
    group_type2="bins_focal",
    fig_label_bin_metric="Circadian power",
    agg_func="median",
    fig_title_agg_func="Median",
    norm=None,
    cbar=True,
):
    # add bins
    binning = utils.Binning(bin_name=group_type1, bin_parameter=bin_parameter1)
    combined_df = binning.add_bins_to_df(
        combined_df,
        n_bins=n_bins,
        step_size=step_size,
        bin_max_n=bin_max_n,
        remove_none=remove_none,
        bin_labels=bin_labels,
        bins=bins,
    )
    binning = utils.Binning(bin_name=group_type2, bin_parameter=bin_parameter2)
    combined_df = binning.add_bins_to_df(
        combined_df,
        n_bins=n_bins,
        step_size=step_size,
        bin_max_n=bin_max_n,
        remove_none=remove_none,
        bin_labels=bin_labels,
        bins=bins,
    )

    # create pivot for plotting
    plot_pivot = (
        combined_df[[group_type1, group_type2, change_type]]
        .groupby([group_type1, group_type2])
        .apply(agg_func)
        .unstack(level=-1)
    )

    # plot
    rcParams.update({"figure.autolayout": True})
    if axs is None:
        fig, axs = plt.subplots(1, 1, figsize=(7.5, 7.5))
    sns.heatmap(
        plot_pivot, annot=True, cmap="rocket", robust=True, norm=norm, ax=axs, cbar=cbar
    )
    axs.invert_yaxis()
    axs.set_title("%s velocity change of focal bee" % fig_title_agg_func)
    axs.set_xticklabels(sorted(combined_df.bins_focal.unique()))
    axs.set_yticklabels(sorted(combined_df.bins_non_focal.unique()), rotation=0)
    axs.set(
        xlabel="%s of focal bee" % fig_label_bin_metric,
        ylabel="%s of non-focal bee" % fig_label_bin_metric,
    )
    if plot_path:
        plt.savefig(plot_path)
    else:
        return axs


def prepare_interaction_df_for_plotting(interaction_df, relative_change_clean=False):
    # add duration, hour, start_velocity to df
    interactions.get_duration(interaction_df)
    interactions.get_start_velocity(interaction_df)
    interactions.get_hour(interaction_df)

    # filter age = 0 out
    if "age_focal" in interaction_df.columns:
        interaction_df = interaction_df[
            (interaction_df["age_focal"] > 0) & (interaction_df["age_non_focal"] > 0)
        ]

    # filter Nans and infs
    to_be_cleaned_columns = [
        "amplitude_focal",
        "amplitude_non_focal",
        "vel_change_bee_focal",
        "vel_change_bee_non_focal",
        "r_squared_focal",
        "r_squared_non_focal",
    ]

    if relative_change_clean:
        to_be_cleaned_columns.extend(
            ["rel_change_bee_focal", "rel_change_bee_non_focal"]
        )
    interaction_df = interactions.clean_interaction_df(
        interaction_df, to_be_cleaned_columns
    )
    return interaction_df


def plot_p_values_per_bin_from_test(
    test_result_dict,
    ax=None,
    n_bins=6,
    fig_label_bin_metric="Circadian power",
    plot_path=None,
    pkl_path=None,
    norm=None,
):
    if not ax:
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    p_values = np.array(
        [test_result_dict[key].pvalue for key in test_result_dict]
    ).reshape((n_bins, n_bins))
    if norm:
        norm = matplotlib.colors.Normalize(*norm)
    sns.heatmap(data=p_values, ax=ax, annot=True, cmap="rocket", norm=norm)
    ax.invert_yaxis()
    ax.set_title("P-values")
    x_labels = np.array(
        [
            [key[0] for key in test_result_dict][i]
            for i in range(0, n_bins * n_bins, n_bins)
        ]
    )
    y_labels = np.array(
        [
            [key[1] for key in test_result_dict][i]
            for i in range(0, n_bins * n_bins, n_bins)
        ]
    )
    # case for comparison tests
    if x_labels.ndim > 1:
        x_labels_copy = x_labels.copy()
        x_labels = [
            f"{x_label[1]}\n{y_label[1]}"
            for x_label, y_label in zip(
                x_labels.reshape((n_bins, 2)), y_labels.reshape((n_bins, 2))
            )
        ]
        y_labels = [
            f"{x_label[0]}\n{y_label[0]}"
            for x_label, y_label in zip(
                x_labels_copy.reshape((n_bins, 2)), y_labels.reshape((n_bins, 2))
            )
        ]
    ax.set_xticklabels(x_labels)
    ax.set_yticklabels(y_labels, rotation=0)
    ax.set(
        xlabel="%s of focal bee" % fig_label_bin_metric,
        ylabel="%s of non-focal bee" % fig_label_bin_metric,
    )
    if plot_path:
        plt.savefig(plot_path)
    if pkl_path:
        np.save(pkl_path, p_values)
    return ax


# Fig. 3
def get_label_for_line(line):
    leg = line.axes.get_legend()
    ind = line.axes.get_lines().index(line)
    return leg.texts[ind].get_text(), leg.get_lines()[ind].get_color()


def set_label_for_line(line, label):
    leg = line.axes.get_legend()
    ind = line.axes.get_lines().index(line)
    leg.texts[ind].set_text(label)


def apply_three_group_age_map_for_plotting_phase(circadianess_df):
    # subgroup them by age and replace in human-readable form
    max_age = circadianess_df.age.max()
    circadianess_df["age_bins"] = pd.cut(
        x=circadianess_df["age"], bins=[-1, 0, 10, 25, max_age]
    )

    age_dict = {
        "(0.0, 10.0]": "Age < 10 days",
        "(10.0, 25.0]": "Age >= 10, < 25 days",
        ("(25.0, %s]" % str(float(max_age))): "Age >= 25 days",
        "(-1.0, 0.0]": "Nan",
        "nan": "Nan",
    }
    circadianess_df["Age [days]"] = [
        age_dict[str(item)] for item in circadianess_df["age_bins"]
    ]
    circadianess_df = circadianess_df[circadianess_df["Age [days]"] != "Nan"]
    return circadianess_df


def plot_histogram_phase_dist(
    circadianess_df,
    plot_path=None,
    hue="Age [days]",
    hue_order=["Age < 10 days", "Age >= 10, < 25 days", "Age >= 25 days"],
):
    # plot histogram grouped phase distribution by age
    sns.set_theme()
    fig, ax = plt.subplots(figsize=(16, 10))
    sns.histplot(
        circadianess_df,
        x="phase_plt",
        hue=hue,
        common_norm=False,
        kde=True,
        element="step",
        stat="probability",
        ax=ax,
        hue_order=hue_order,
    )
    ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
    plt.xlabel("Phase in (h)")
    plt.ylabel("Frequency")
    plt.title("Phase distribution")
    plt.grid(visible=True)
    if plot_path:
        plt.savefig(plot_path)


def plot_phase_per_age_group(
    circadianess_df,
    plot_path=None,
    fit_type="cosine",
    time_reference=None,
    bin_name="Age [days]",
    bin_parameter="age",
    n_bins=None,
    step_size=None,
    bin_max_n=None,
    remove_none=True,
    bins=[0, 10, 25],
    bin_labels=["Age < 10 days", "Age >= 10, < 25 days", "Age >= 25 days"],
):
    # add bins
    binning = utils.Binning(bin_name=bin_name, bin_parameter=bin_parameter)
    circadianess_df = binning.add_bins_to_df(
        circadianess_df,
        n_bins=n_bins,
        step_size=step_size,
        bin_max_n=bin_max_n,
        remove_none=remove_none,
        bins=bins,
        bin_labels=bin_labels,
    )

    # map time interval of [-pi, pi] to 24h
    circadianess_df = rhythm.add_phase_plt_to_df_cosinor(circadianess_df)

    # plot
    plot_histogram_phase_dist(
        circadianess_df,
        plot_path=plot_path,
        hue=binning.bin_name,
        hue_order=sorted(list(pd.Series(binning.bin_labels).dropna().unique())),
    )


def plot_phase_per_age(
    circadianess_df,
    plot_path=None,
    annotate=True,
    fit_type="cosine",
    time_reference=None,
):
    # filter data
    circadianess_df = circadianess_df[circadianess_df["age"] >= 0]

    # map time interval of [-pi, pi] to 24h
    circadianess_df = rhythm.add_phase_plt_to_df(
        circadianess_df, fit_type=fit_type, time_reference=time_reference
    )

    # Plotting
    # set seaborn parameters so grid is visible
    sns.set_theme()

    # plot histogram grouped phase distribution by age
    fig, (ax1, ax2, ax23, ax3) = plt.subplots(
        1, 4, figsize=(30, 8), gridspec_kw={"width_ratios": [1, 2, 1, 0.05]}
    )

    # plot histogram
    sns.kdeplot(
        circadianess_df,
        x="phase_plt",
        hue="age",
        common_norm=False,
        ax=ax1,
        palette="viridis",
    )

    # plot maxima
    label_col_dict = {}
    scatter_coords = []
    for line in ax1.lines:
        label, label_col = get_label_for_line(line)
        label_col_dict[label_col] = label
    for line in ax1.lines:
        xs, ys = line.get_data()
        line_col = line.get_color()
        mode_idx = np.argmax(ys)
        ax2.vlines(xs[mode_idx], 0, ys[mode_idx], ls="--", colors=line_col)
        ax2.plot([xs[mode_idx]], [np.max(ys)], marker="o", markersize=3, color=line_col)
        ax2.text(
            xs[mode_idx],
            -0.055,
            s=str(label_col_dict[line_col])
            + ": "
            + str(np.round(xs[mode_idx], 2))
            + "h",
            ha="center",
            color=line_col,
            rotation=90,
            **{"size": "8"},
        )
        scatter_coords.append(
            {"age": label_col_dict[line_col], "max": xs[mode_idx], "col": line_col}
        )

    # Remove the legend and add a colorbar
    norm = plt.Normalize(circadianess_df["age"].min(), circadianess_df["age"].max())
    sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
    scatter_df = pd.DataFrame(scatter_coords)
    scatter_df["counts"] = [
        circadianess_df["age"].value_counts().to_dict()[float(value)]
        for value in scatter_df["age"]
    ]
    scatter_df["age"] = scatter_df["age"].astype(float)
    sns.scatterplot(
        data=scatter_df,
        x="age",
        y="max",
        color=scatter_df["col"],
        ax=ax23,
        size="counts",
    )
    if annotate:
        for x, y, count in zip(
            scatter_df["age"], scatter_df["max"], scatter_df["counts"]
        ):
            ax23.annotate(count, xy=(x, y))
    ax1.get_legend().remove()
    ax3.figure.colorbar(sm, cax=ax3)

    # labels and axis settings
    ax1.sharey(ax2)
    ax1.xaxis.set_major_locator(ticker.MultipleLocator(2))
    ax23.xaxis.set_major_locator(ticker.MultipleLocator(2))
    ax2.set_xticks([])
    ax2.set_ylabel("")
    ax2.set_xlabel("")
    ax1.set_xlabel("Phase in (h)")
    ax1.set_ylabel("Frequency")
    ax1.set_title("Phase distribution")
    ax2.set_title("Mean of phase distribution")
    ax3.set_title("Age (days)")
    plt.grid(visible=True)
    plt.tight_layout()

    # save figure
    if plot_path:
        plt.savefig(plot_path)


def plot_phase_per_date(phase_per_date_df, plot_path=None):
    fig, ax = plt.subplots(2, 1)
    sns.lineplot(
        data=phase_per_date_df, x="date", y="phase_mean", hue="age_group", ax=ax[0]
    )
    sns.lineplot(
        data=phase_per_date_df, x="date", y="phase_std", hue="age_group", ax=ax[1]
    )
    if plot_path:
        plt.savefig(plot_path)


# Fig 6
def plot_body_location_of_interactions(
    vel_change_matrix_df,
    plot_dir=None,
    imshow=False,
    annotate=False,
    ax=None,
    title_extra=None,
):
    # plot settings
    rcParams.update({"figure.autolayout": True})
    plt.rcParams["axes.facecolor"] = "white"
    plt.tight_layout()

    # create figure
    if ax is None:
        fig, ax = plt.subplots(figsize=(16, 12))

    # plot
    sns.scatterplot(
        data=vel_change_matrix_df,
        x="x",
        y="y",
        hue="vel_change_bee_focal",
        palette="viridis",
        hue_norm=(
            vel_change_matrix_df["vel_change_bee_focal"][
                vel_change_matrix_df["vel_change_bee_focal"] != 0.0
            ].quantile(0.05),
            vel_change_matrix_df["vel_change_bee_focal"][
                vel_change_matrix_df["vel_change_bee_focal"] != 0.0
            ].quantile(0.95),
        ),
        size="count",
        sizes=(0, 500),
        ax=ax,
    )

    # add annotations one by one with a loop
    if annotate:
        vel_change_matrix_df.vel_change_bee_focal = vel_change_matrix_df.vel_change_bee_focal.round(
            2
        )
        for line in range(0, vel_change_matrix_df.shape[0]):
            ax.text(
                vel_change_matrix_df.x[line],
                vel_change_matrix_df.y[line],
                vel_change_matrix_df.vel_change_bee_focal[line],
                horizontalalignment="center",
                color="black",
            )

    # legend settings
    handles, labels = ax.get_legend_handles_labels()
    labels = [
        "Velocity change" if item == "vel_change_bee_focal" else item for item in labels
    ]
    labels = ["Count" if item == "count" else item for item in labels]
    ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(1, 1))

    # label plot
    plt.xlabel("x position")
    plt.ylabel("y position")

    if title_extra is None:
        ax.set_title("Velocity change per body location")
    else:
        ax.set_title("Velocity change per body location\n%s" % str(title_extra))
    if imshow:
        plt.imshow()
    if plot_dir:
        plt.savefig(plot_dir)


def transform_interaction_df_to_vel_change_matrix_df(vel_change_df_trans):
    # group velocity changes by coordinates
    vel_change_matrix_df = (
        vel_change_df_trans.groupby(["focal0_x_trans", "focal0_y_trans"])[
            "vel_change_bee_focal"
        ]
        .agg([("count", "count"), ("vel_change_bee_focal", "median")])
        .reset_index()
    )
    vel_change_matrix_df.rename(
        columns={"focal0_x_trans": "x", "focal0_y_trans": "y"}, inplace=True
    )
    return vel_change_matrix_df


def transform_interaction_matrix_to_df(
    vel_change_matrix, count_matrix, whose_change="focal"
):
    vel_change_matrix_df = (
        pd.DataFrame(vel_change_matrix)
        .stack()
        .rename_axis(["y", "x"])
        .reset_index(name="vel_change_bee_%s" % whose_change)
    )
    count_matrix_df = (
        pd.DataFrame(count_matrix)
        .stack()
        .rename_axis(["y", "x"])
        .reset_index(name="count")
    )
    return pd.merge(vel_change_matrix_df, count_matrix_df, on=["y", "x"], how="outer")


# others
def plot_circadian_fit(
    df_row,
    velocities=None,
    plot_path=None,
    linear_model=False,
    constant_model=False,
    fixed_minimum_model=False,
):
    df_row = dict(df_row)
    if velocities is None:
        with bb_behavior.db.base.get_database_connection(
            application_name="find_interactions_in_frame"
        ) as db:
            cursor = db.cursor()
            delta = datetime.timedelta(days=1, hours=12)
            # fetch velocities
            velocities = bb_behavior.db.trajectory.get_bee_velocities(
                df_row["bee_id"],
                df_row["date"] - delta,
                df_row["date"] + delta,
                confidence_threshold=0.1,
                max_mm_per_second=15.0,
                cursor=cursor,
            )
    velocities_resampled = velocities.copy()
    velocities_resampled.set_index("datetime", inplace=True)

    if velocities_resampled.shape[0] > 10000:
        velocities_resampled = velocities_resampled.resample("2min").mean()

    ts_resampled = np.array(
        [t.total_seconds() for t in velocities_resampled.index - df_row["date"]]
    )

    angular_frequency = df_row["angular_frequency"]
    amplitude, phase, offset = df_row["parameters"]

    base_activity = max(0, offset - amplitude)
    max_activity = offset + amplitude
    fraction_circadian = 2.0 * ((max_activity / (base_activity + max_activity)) - 0.5)

    fig, ax = plt.subplots(figsize=(20, 5))

    ax.axvline(
        velocities_resampled.index[0] + datetime.timedelta(days=1, hours=phase),
        color="g",
        linestyle=":",
    )
    ax.axhline(base_activity, color="k", linestyle="--")
    ax.axhline(max_activity, color="k", linestyle="--")

    y = np.cos(ts_resampled * angular_frequency - phase) * amplitude + offset
    velocities_resampled["circadian_model"] = y

    velocities_resampled.plot(y="velocity", ax=ax, color="k", alpha=0.3)
    velocities_resampled.plot(y="circadian_model", ax=ax, color="g", alpha=1.0)

    title = (
        "bee_id: {}, age: {}, date: {}"
        "R^2 (vs constant): {}, R^2 (vs linear): {}\n"
        "circadian: {}, amplitude: {}, phase: {}h".format(
            df_row["bee_id"],
            df_row["age"],
            df_row["date"],
            df_row["r_squared"],
            df_row["r_squared_linear"],
            fraction_circadian,
            2.0 * amplitude,
            phase,
        )
    )

    if linear_model:
        b0, b1 = df_row["linear_parameters"]
        y_linear = (ts_resampled * b1) + b0
        velocities_resampled["linear_model"] = y_linear
        velocities_resampled.plot(
            y="linear_model", ax=ax, color="r", linestyle="--", alpha=1.0
        )

    if constant_model:
        mean = df_row["constant_parameters"][0]
        velocities_resampled["constant_model"] = mean
        velocities_resampled.plot(
            y="constant_model", ax=ax, color="r", linestyle=":", alpha=1.0
        )

    if fixed_minimum_model:
        fixed_minimum_r_squared = np.nan
        fixed_amplitude, fixed_phase = np.nan, np.nan
        if "fixed_minimum_model" in df_row:
            fixed_minimum_r_squared = df_row["fixed_minimum_model"]["r_squared"]
            fixed_amplitude, fixed_phase = df_row["fixed_minimum_model"]["parameters"]
            y = (
                np.cos(ts_resampled * angular_frequency - fixed_phase) * fixed_amplitude
                + fixed_amplitude
            )
            velocities_resampled["circadian_model_fixed_min"] = y
            velocities_resampled.plot(
                y="circadian_model_fixed_min",
                ax=ax,
                color="b",
                linestyle=":",
                alpha=1.0,
            )
        title = (
            title
            + "\nR^2 of zero-min model (vs constant): {}, amplitude: {}, phase: {}h".format(
                fixed_minimum_r_squared, 2.0 * fixed_amplitude, fixed_phase
            )
        )

    p90 = np.percentile(velocities.velocity.values, 95)
    plt.ylim(0, p90)
    plt.title(title)
    if plot_path:
        plt.savefig(plot_path)


def nan_tolerant_gaussian_filtering(U, sigma):
    V = U.copy()
    V[np.isnan(U)] = 0
    VV = filters.gaussian(V, sigma=sigma)

    W = 0 * U.copy() + 1
    W[np.isnan(U)] = 0
    WW = filters.gaussian(W, sigma=sigma)

    return VV / WW


def plot_fit_params_per_loc(
    df,
    variable,
    xrange,
    yrange,
    label=None,
    cmap=None,
    vmin=None,
    vmax=None,
    center=None,
    robust=True,
    smooth=False,
    cm=" [cm]",
    transparency=False,
    alpha_var="n_samples",
    ticks=None,
    save_to="phase_per_pos.png",
):
    df[["x_grid", "y_grid"]] = df[["x_grid", "y_grid"]].astype(int)

    fig, axs = plt.subplots(1, 2, figsize=(14, 5))
    cbar_ax = fig.add_axes([1, 0.23, 0.03, 0.6])

    for side in [0, 1]:
        df_grid = pd.pivot(
            data=df[df["side"] == side],
            index="y_grid",
            columns="x_grid",
            values=variable,
        )

        # set x and y range
        df_grid = df_grid.loc[yrange[0] : yrange[1], xrange[0] : xrange[1]]

        alpha_grid = None

        if transparency:
            alpha_grid = pd.pivot(
                data=df[df["side"] == side],
                index="y_grid",
                columns="x_grid",
                values=alpha_var,
            ).fillna(0)
            alpha_grid = alpha_grid.loc[yrange[0] : yrange[1], xrange[0] : xrange[1]]

            # scale alpha values between zero and one
            alpha_grid = alpha_grid.to_numpy()
            alpha_grid /= np.max(alpha_grid)

        if smooth:
            grid = df_grid.to_numpy()
            grid = nan_tolerant_gaussian_filtering(grid, sigma=1)
            df_grid.loc[:, :] = grid
        # df_grid = df_grid.interpolate(method='linear')
        # df_grid = df_grid.fillna(method='bfill')

        if not label:
            label = variable

        sns.heatmap(
            df_grid,
            vmin=vmin,
            vmax=vmax,
            ax=axs[side],
            xticklabels=5,
            yticklabels=5,
            center=center,
            cmap=cmap,
            cbar=side,
            cbar_kws={"label": label, "ticks": ticks},
            cbar_ax=cbar_ax,
            robust=robust,
            alpha=alpha_grid,
        )

        axs[side].set_xlabel("x position" + cm)
        ylabel = "y position" + cm if side == 0 else ""
        title = "View on side %d" % side
        axs[side].set_ylabel(ylabel)
        axs[side].set_title(title)

    plt.tight_layout()

    if save_to:
        plt.savefig(save_to)

    plt.show()


def plot_binned_velocity_change(
    combined_df,
    plot_path=None,
    axs=None,
    bin_parameter2="r_squared_focal",
    bin_parameter1="r_squared_non_focal",
    change_type="vel_change_bee_focal",
    fig_label_bin_metric="Circadian power",
    agg_func="median",
    unit="quantile",
    vmin=None,
    vmax=None,
):
    # Create combination matrix.
    plot_pivot = pd.pivot_table(
        data=combined_df,
        values=change_type,
        index=bin_parameter1,
        columns=bin_parameter2,
        aggfunc=agg_func,
    )

    plt.rcParams.update({"font.size": 6})
    # Plot.
    # vmin = -1.02 if 'start_vel' in bin_parameter1 and change_type == 'vel_change_bee_focal' else None
    # vmax = 0.4 if 'start_vel' in bin_parameter1 and change_type == 'vel_change_bee_focal' else None
    # vmin = -17 if 'start_vel' in bin_parameter1 and change_type == 'rel_change_bee_focal' else None
    # vmax = 70 if 'start_vel' in bin_parameter1 and change_type == 'rel_change_bee_focal' else None

    sns.set_theme()
    if axs is None:
        fig, axs = plt.subplots(1, 1, figsize=(6, 6), dpi=300)
    label = (
        "Number of interactions"
        if agg_func == "count"
        else f"{agg_func.capitalize()} velocity change of focal bee [mm/s]"
    )
    if change_type == "rel_change_bee_focal":
        label = "Relative velocity change of focal bee [%]"
    sns.heatmap(
        plot_pivot,
        annot=True,
        cmap="viridis",
        robust=True,
        ax=axs,
        cbar_kws={"label": label},
        alpha=0.95,
        vmin=vmin,
        vmax=vmax,
    )
    axs.invert_yaxis()

    if unit != "":
        unit = f"[{unit}]"
    axs.set(
        xlabel=f"{fig_label_bin_metric} of focal bee {unit}",
        ylabel=f"{fig_label_bin_metric} of non-focal bee {unit}",
    )
    plt.savefig(plot_path + ".png", bbox_inches="tight")
    plt.savefig(plot_path + ".svg", bbox_inches="tight")


def whiten_out_low_sample_size_areas(
    ax: matplotlib.axes.Axes, df: pd.DataFrame, distance_column: str, alpha_column: str
):
    """

    :param ax:
    :param dist:
    :param distance_column:
    :param alpha_column:
    :return:
    """
    distances = pd.qcut(df[distance_column].unique(), len(df[distance_column].unique()))
    alpha = (
        df.groupby([distance_column])[alpha_column]
        .mean()
        .reset_index()
        .sort_values(by=distance_column)[alpha_column]
        .round(2)
    )
    alpha = (alpha - alpha.min()) / (alpha.max() - alpha.min())
    i = 0
    for distance in sorted(distances.unique()):
        if i == 0:
            print(alpha[i])
            ax.axvspan(
                distance.left - 5,
                distance.right,
                color="white",
                edgecolor=None,
                facecolor=None,
                linewidth=0,
                alpha=alpha[i],
                zorder=2,
            )
        elif i == (len(distances.unique()) - 1):
            ax.axvspan(
                distance.left,
                distance.right + 10,
                color="white",
                edgecolor=None,
                facecolor=None,
                linewidth=0,
                alpha=alpha[i],
                zorder=2,
            )
        else:
            ax.axvspan(
                distance.left,
                distance.right,
                color="white",
                edgecolor=None,
                facecolor=None,
                linewidth=0,
                alpha=alpha[i],
                zorder=2,
            )
        i += 1


def plot_cosinor_with_velocities(ax, velocity_df, velocity_subperiod_df, color, day, cosinor_df, bee_id, round_up_to,
                                 ylim, set_xticks=True):
    """

    :param ax:
    :param velocity_df:
    :param velocity_subperiod_df:
    :param color:
    :param day:
    :param cosinor_df:
    :param bee_id:
    :param round_up_to:
    :param ylim:
    :param set_xticks:
    :return:
    """
    # round to median movement speed
    velocity_df["datetime"] = velocity_df["datetime"].dt.round(round_up_to)
    velocity_df_median = velocity_df.groupby(["datetime"])[["velocity", "time_passed"]].median().reset_index()

    # calculate X and Y of cosinor fit
    X, Y = rhythm.fit_cosinor_from_df(bee_id, day, cosinor_df, velocity_df_median)

    # add grey nighttimes
    add_grey_nighttime_bars(ax, velocity_subperiod_df)

    # plot cosinor fit
    sns.lineplot(x=velocity_df_median.datetime.values, y=Y, color=color, ax=ax, linestyle="--")
    # plot 95% percentile velocities
    sns.lineplot(
        data=velocity_df, x="datetime", y="velocity",
        errorbar=("pi", 90),
        color=color, ax=ax, estimator="median", linewidth=0,
    )
    # plot median velocities
    sns.scatterplot(velocity_df_median, x="datetime", y="velocity", color=color, marker="X", size=0.75, ax=ax)

    # x-axis settings
    if set_xticks:
        date_form = matplotlib.dates.DateFormatter("%m-%d %Hh")
        ax.xaxis.set_major_formatter(date_form)
        ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[2, 4, 6, 8, 10, 14, 16, 18, 20, 22]))
        ax.tick_params(which='minor', length=2)
        ax.set_xticks(ax.get_xticks())
        ax.set_xticklabels(ax.get_xticklabels(), rotation=15, ha='right')
    ax.set_xlim(velocity_subperiod_df.date.min(), velocity_subperiod_df.date.max() + datetime.timedelta(hours=6))
    ax.set_xlabel("Date")

    # y-axis settings
    ax.yaxis.set_major_locator(ticker.MultipleLocator(5))
    ax.set_ylim(ylim)
    ax.set_ylabel("Movement speed [mm/s]")

    # figure settings
    ax.set_title("Movement speed and cosinor fit of individuals", fontsize=rcParams['axes.labelsize'])

    # legend settings
    legends = [
        (mpatches.Patch(color=color, alpha=0.4), '95% Movement\nspeed [mm/s]'),
        ((mlines.Line2D([], [], color=color, marker='x', linewidth=0, markersize=3)), "Median\nmovement speed per h"),
        ((mlines.Line2D([], [], color=color, linestyle='--')), 'Cosinor fit'),
    ]
    leg = ax.legend(*zip(*legends), loc='upper left', framealpha=1.0, edgecolor=(1.0, 1.0, 1.0, 1.0))