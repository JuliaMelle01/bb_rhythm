# imports for run job
import datetime
import numpy as np
import itertools
import pandas as pd
import cv2
import os
import pytz

import bb_behavior.db


def cluster_interactions_over_time(
    iterable,
    min_gap_size=datetime.timedelta(seconds=1),
    min_event_duration=None,
    y="y",
    time="time",
    color="color",
    loc_info_0="loc_info_0",
    loc_info_1="loc_info_1",
    fill_gaps=True,
):
    """

    :param iterable:
    :param min_gap_size:
    :param min_event_duration:
    :param y:
    :param time:
    :param color:
    :param loc_info_0:
    :param loc_info_1:
    :param fill_gaps:
    :return:
    """
    """Slightly modified version of bb_behavior.plot.time.plot_timeline()"""
    from collections import defaultdict

    last_x_for_y = defaultdict(list)

    for timepoint in iterable:
        dt, y_value, category, location_info_0, location_info_1 = (
            timepoint[time],
            timepoint[y],
            timepoint[color],
            timepoint[loc_info_0],
            timepoint[loc_info_1],
        )
        last_x = last_x_for_y[y_value]

        def should_overwrite_last_event():
            """

            :return:
            """
            if not last_x_for_y[y_value]:
                return False
            last = last_x_for_y[y_value][-1]
            return (
                min_event_duration
                and (last["dt_end"] - last["dt_start"]) < min_event_duration
            )

        def push():
            """

            :return:
            """
            new_event_data = dict(
                Task=y_value,
                Resource=category,
                dt_start=dt,
                dt_end=dt,
                location_info_0=location_info_0,
                location_info_1=location_info_1,
            )

            if should_overwrite_last_event():
                # Overwrite.
                last_x_for_y[y_value][-1] = new_event_data
            else:
                last_x_for_y[y_value].append(new_event_data)

        if not last_x or (category != last_x[-1]["Resource"]):
            push()
            continue
        last_x = last_x[-1]

        delay = dt - last_x["dt_end"]
        if min_gap_size is not None and delay > min_gap_size:
            if fill_gaps:
                overwrite_possible = (
                    should_overwrite_last_event() and len(last_x_for_y[y_value]) >= 2
                )
                if overwrite_possible:
                    last_x = last_x_for_y[y_value][-2]

                gap_data = dict(
                    Task=y_value,
                    Resource="Gap",
                    dt_start=last_x["dt_end"],
                    dt_end=dt,
                    loc_info_0=loc_info_0,
                    loc_info_1=loc_info_1,
                )
                if overwrite_possible:
                    last_x_for_y[y_value][-1] = gap_data
                else:
                    last_x_for_y[y_value].append(gap_data)
            push()
            continue

        last_x["dt_end"] = dt
        last_x["location_info_0_end"] = location_info_0
        last_x["location_info_1_end"] = location_info_1

    for _, sessions in last_x_for_y.items():
        if len(sessions) == 0:
            continue
        # Check if last session doesn't meet min length criteria.
        last = sessions[-1]
        if (
            min_event_duration
            and (last["dt_end"] - last["dt_start"]) < min_event_duration
        ):
            del sessions[-1]

    df = list(itertools.chain(*list(s for s in last_x_for_y.values() if s is not None)))

    if len(df) == 0:
        return None
    return last_x_for_y


def extract_parameters_from_events(event):
    """

    :param event:
    :return:
    """
    bee_id0, bee_id1 = event["Task"].split("_")
    dt_start = event["dt_start"]
    dt_end = event["dt_end"]
    bee_id0_x_pos_start = event["location_info_0"][0]
    bee_id0_y_pos_start = event["location_info_0"][1]
    bee_id0_theta_start = event["location_info_0"][2]
    bee_id1_x_pos_start = event["location_info_1"][0]
    bee_id1_y_pos_start = event["location_info_1"][1]
    bee_id1_theta_start = event["location_info_1"][2]
    bee_id0_x_pos_end = event["location_info_0_end"][0]
    bee_id0_y_pos_end = event["location_info_0_end"][1]
    bee_id0_theta_end = event["location_info_0_end"][2]
    bee_id1_x_pos_end = event["location_info_1_end"][0]
    bee_id1_y_pos_end = event["location_info_1_end"][1]
    bee_id1_theta_end = event["location_info_1_end"][2]
    return {
        "bee_id0": int(bee_id0),
        "bee_id1": int(bee_id1),
        "interaction_start": dt_start,
        "interaction_end": dt_end,
        "x_pos_start_bee0": bee_id0_x_pos_start,
        "y_pos_start_bee0": bee_id0_y_pos_start,
        "theta_start_bee0": bee_id0_theta_start,
        "x_pos_start_bee1": bee_id1_x_pos_start,
        "y_pos_start_bee1": bee_id1_y_pos_start,
        "theta_start_bee1": bee_id1_theta_start,
        "x_pos_end_bee0": bee_id0_x_pos_end,
        "y_pos_end_bee0": bee_id0_y_pos_end,
        "theta_end_bee0": bee_id0_theta_end,
        "x_pos_end_bee1": bee_id1_x_pos_end,
        "y_pos_end_bee1": bee_id1_y_pos_end,
        "theta_end_bee1": bee_id1_theta_end,
    }


def extract_parameters_from_random_samples(event, interaction_start, interaction_end):
    """

    :param event:
    :param interaction_start:
    :param interaction_end:
    :return:
    """
    return {
        "bee_id0": event[0][0],
        "bee_id1": event[1][0],
        "interaction_start": interaction_start,
        "interaction_end": interaction_end,
        "x_pos_start_bee0": event[0][1],
        "y_pos_start_bee0": event[0][2],
        "theta_start_bee0": event[0][3],
        "x_pos_start_bee1": event[1][1],
        "y_pos_start_bee1": event[1][2],
        "theta_start_bee1": event[1][3],
        "x_pos_end_bee0": event[0][4],
        "y_pos_end_bee0": event[0][5],
        "theta_end_bee0": event[0][6],
        "x_pos_end_bee1": event[1][4],
        "y_pos_end_bee1": event[1][5],
        "theta_end_bee1": event[1][6],
    }


def get_all_interactions_over_time(interaction_generator) -> list:
    """

    :param interaction_generator:
    :return:
    """

    def generator():
        """

        :return:
        """
        for interaction in interaction_generator:
            (
                bee_id0,
                bee_id1,
                timestamp,
                location_parameters_bee0,
                location_parameters_bee1,
            ) = (
                interaction["bee_id0"],
                interaction["bee_id1"],
                interaction["timestamp"],
                interaction["location_info_bee0"],
                interaction["location_info_bee1"],
            )
            # Make sure that the bee_id0 always refers to the one with the lower ID here.
            pair_string = "{}_{}".format(bee_id0, bee_id1)
            yield dict(
                y=pair_string,
                time=timestamp,
                color="interaction",
                loc_info_0=location_parameters_bee0,
                loc_info_1=location_parameters_bee1,
            )

    clustered_interaction_events = cluster_interactions_over_time(
        generator(),
        min_gap_size=datetime.timedelta(seconds=2),
        min_event_duration=datetime.timedelta(seconds=1),
        fill_gaps=False,
    )
    extracted_interactions_lst = []
    for key in clustered_interaction_events:
        event_dict = clustered_interaction_events[key]
        if event_dict:
            # extract event parameters as interactions
            interaction_dict = extract_parameters_from_events(event_dict[0])
            extracted_interactions_lst.append(interaction_dict)
    return extracted_interactions_lst


def add_post_interaction_velocity_change(interaction_events, velocity_df_path=None):
    """

    :param interaction_events:
    :param velocity_df_path:
    :return:
    """
    for interaction_dict in interaction_events:
        # calculate velocity changes
        # "focal" bee
        (
            interaction_dict["vel_change_bee0"],
            interaction_dict["relative_change_bee0"],
        ) = get_velocity_change_per_bee(
            bee_id=interaction_dict["bee_id0"],
            interaction_start=interaction_dict["interaction_start"].replace(
                tzinfo=pytz.UTC
            ),
            interaction_end=interaction_dict["interaction_end"].replace(
                tzinfo=pytz.UTC
            ),
            velocities_path=velocity_df_path,
        )
        # "non-focal" bee
        (
            interaction_dict["vel_change_bee1"],
            interaction_dict["relative_change_bee1"],
        ) = get_velocity_change_per_bee(
            bee_id=interaction_dict["bee_id1"],
            interaction_start=interaction_dict["interaction_start"].replace(
                tzinfo=pytz.UTC
            ),
            interaction_end=interaction_dict["interaction_end"].replace(
                tzinfo=pytz.UTC
            ),
            velocities_path=velocity_df_path,
        )


def fetch_interactions_per_frame(
    cam_ids: list, cursor, dt_from: datetime.datetime, dt_to: datetime.datetime
) -> list:
    """

    :param cam_ids:
    :param cursor:
    :param dt_from:
    :param dt_to:
    :return:
    """
    interactions_lst = []
    for cam_id in cam_ids:
        # get frames in time window
        frame_data = bb_behavior.db.get_frames(cam_id, dt_from, dt_to, cursor=cursor)
        if not frame_data:
            continue

        # for each frame id
        for dt, frame_id, cam_id in frame_data:
            # find interactions per frame
            interactions_detected = bb_behavior.db.find_interactions_in_frame(
                frame_id=frame_id, cursor=cursor
            )

            # append interactions to interaction lst
            for i in interactions_detected:
                interactions_lst.append(
                    {
                        "bee_id0": i[1],
                        "bee_id1": i[2],
                        "timestamp": dt,
                        "location_info_bee0": (i[5], i[6], i[7]),
                        "location_info_bee1": (i[8], i[9], i[10]),
                    }
                )
    return interactions_lst


def get_velocity_change_per_bee(
    bee_id, interaction_start, interaction_end, velocities_path=None
):
    """

    :param bee_id:
    :param interaction_start:
    :param interaction_end:
    :param velocities_path:
    :return:
    """
    delta_t = datetime.timedelta(0, 30)
    dt_before, dt_after = interaction_start - delta_t, interaction_end + delta_t

    if type(bee_id) == np.int64:
        bee_id = bee_id.item()

    try:
        # fetch velocities
        velocities = pd.read_pickle(os.path.join(velocities_path, "%d.pickle" % bee_id))
    except (FileNotFoundError, TypeError):
        # fetch velocities
        velocities = bb_behavior.db.trajectory.get_bee_velocities(
            bee_id,
            dt_before,
            dt_after,
            confidence_threshold=0.1,
            max_mm_per_second=15.0,
        )

    if velocities is None:
        return None, None

    vel_before = np.mean(
        velocities[
            (
                velocities["datetime"].map(lambda x: x.replace(tzinfo=pytz.UTC))
                >= dt_before
            )
            & (
                velocities["datetime"].map(lambda x: x.replace(tzinfo=pytz.UTC))
                < interaction_start
            )
        ]["velocity"]
    )
    vel_after = np.mean(
        velocities[
            (
                velocities["datetime"].map(lambda x: x.replace(tzinfo=pytz.UTC))
                > interaction_end
            )
            & (
                velocities["datetime"].map(lambda x: x.replace(tzinfo=pytz.UTC))
                <= dt_after
            )
        ]["velocity"]
    )
    del velocities
    vel_change = vel_after - vel_before
    if (vel_before == 0) or np.isinf(vel_before) or np.isnan(vel_before):
        percent_change = np.NaN
    else:
        percent_change = (vel_change / vel_before) * 100
    return vel_change, percent_change


def extract_parameters_from_random_samples(event, interaction_start, interaction_end):
    return {
        "bee_id0": event[0][0],
        "bee_id1": event[1][0],
        "interaction_start": interaction_start,
        "interaction_end": interaction_end,
        "bee_id0_x_pos_start": event[0][1],
        "bee_id0_y_pos_start": event[0][2],
        "bee_id0_theta_start": event[0][3],
        "bee_id1_x_pos_start": event[1][1],
        "bee_id1_y_pos_start": event[1][2],
        "bee_id1_theta_start": event[1][3],
        "bee_id0_x_pos_end": event[0][4],
        "bee_id0_y_pos_end": event[0][5],
        "bee_id0_theta_end": event[0][6],
        "bee_id1_x_pos_end": event[1][4],
        "bee_id1_y_pos_end": event[1][5],
        "bee_id1_theta_end": event[1][6],
    }


def swap_focal_bee_to_be_low_circadian(df):
    new_frame_dict = {
        "circadianess_focal": [],
        "x_pos_start_focal": [],
        "y_pos_start_focal": [],
        "theta_start_focal": [],
        "vel_change_bee_focal": [],
        "rel_change_bee_focal": [],
        "circadianess_non_focal": [],
        "x_pos_start_non_focal": [],
        "y_pos_start_non_focal": [],
        "theta_start_non_focal": [],
        "vel_change_bee_non_focal": [],
        "rel_change_bee_non_focal": [],
    }
    parameters = [
        "circadianess",
        "x_pos_start",
        "y_pos_start",
        "theta_start",
        "vel_change_bee",
        "rel_change_bee",
    ]
    for index, interaction in df.iterrows():
        if interaction["circadianess_focal"] > interaction["circadianess_non_focal"]:
            for parameter in parameters:
                focal = interaction["%s_focal" % parameter]
                non_focal = interaction["%s_non_focal" % parameter]
                new_frame_dict["%s_focal" % parameter].extend([non_focal])
                new_frame_dict["%s_non_focal" % parameter].extend([focal])
        else:
            for parameter in parameters:
                new_frame_dict["%s_focal" % parameter].extend(
                    [interaction["%s_focal" % parameter]]
                )
                new_frame_dict["%s_non_focal" % parameter].extend(
                    [interaction["%s_non_focal" % parameter]]
                )
    for parameter in parameters:
        df["%s_focal" % parameter] = new_frame_dict["%s_focal" % parameter]
        df["%s_non_focal" % parameter] = new_frame_dict["%s_non_focal" % parameter]
    return df


# transform coordinates
def transform_coordinates(interaction, focal_bee=0):
    bee0_x = interaction["x_pos_start_bee0"]
    bee0_y = interaction["y_pos_start_bee0"]
    bee0_theta = interaction["theta_start_bee0"]
    bee1_x = interaction["x_pos_start_bee1"]
    bee1_y = interaction["y_pos_start_bee1"]
    bee1_theta = interaction["theta_start_bee1"]

    if focal_bee == 0:
        # translation to make bee0 coordinates the origin
        x_prime = bee1_x - bee0_x
        y_prime = bee1_y - bee0_y
        bee1_coords = np.array([x_prime, y_prime])

        # rotation to make bee0 angle zero
        transformed = rotate(-bee0_theta, bee1_coords)

        # return transformed coordinates and angle of non-focal bee
        return transformed[0], transformed[1], bee1_theta - bee0_theta

    else:
        # translation to make bee1 coordinates the origin
        x_prime = bee0_x - bee1_x
        y_prime = bee0_y - bee1_y
        bee0_coords = np.array([x_prime, y_prime])

        # rotation to make bee1 angle zero
        transformed = rotate(-bee1_theta, bee0_coords)

        return transformed[0], transformed[1], bee0_theta - bee1_theta


def apply_transformation(interaction_df):
    # apply transformation of coordinates
    transformed_coords_focal0 = interaction_df.apply(
        transform_coordinates, axis=1, result_type="expand", focal_bee=0
    )
    transformed_coords_focal1 = interaction_df.apply(
        transform_coordinates, axis=1, result_type="expand", focal_bee=1
    )

    # rounded coordinates to discretize positions
    transformed_coords_focal0 = transformed_coords_focal0.apply(round)
    transformed_coords_focal1 = transformed_coords_focal1.apply(round)

    # append columns to original vel_change_matrix_df
    interaction_df[
        ["focal0_x_trans", "focal0_y_trans", "focal0_theta_trans"]
    ] = transformed_coords_focal0
    interaction_df[
        ["focal1_x_trans", "focal1_y_trans", "focal1_theta_trans"]
    ] = transformed_coords_focal1

    return interaction_df


def get_dist(row):
    return np.linalg.norm([row["x"], row["y"]])


def get_dist_special_coord(row):
    return np.linalg.norm([row["x_1"], row["y_1"]])


def get_duration(
    df, end_parameter="interaction_end", start_parameter="interaction_start"
):
    df["duration"] = [
        row.total_seconds() for row in (df[end_parameter] - df[start_parameter])
    ]


def get_hour(df, start_parameter="interaction_start"):
    df["hour"] = df[start_parameter].dt.hour


def concat_interaction_times(combined_df, df):
    combined_df["interaction_start"] = pd.concat(
        [df["interaction_start"], df["interaction_start"]], ignore_index=True
    )
    combined_df["interaction_end"] = pd.concat(
        [df["interaction_end"], df["interaction_end"]], ignore_index=True
    )


def concat_ages(combined_df, df):
    combined_df["age_focal"] = pd.concat([df["age_bee0"], df["age_bee1"]])
    combined_df["age_non_focal"] = pd.concat([df["age_bee1"], df["age_bee0"]])


def concat_circ(combined_df, df):
    combined_df["r_squared_focal"] = pd.concat(
        [df["r_squared_bee0"], df["r_squared_bee1"]]
    )
    combined_df["r_squared_non_focal"] = pd.concat(
        [df["r_squared_bee1"], df["r_squared_bee0"]]
    )


def concat_amplitude(combined_df, df):
    combined_df["amplitude_focal"] = pd.concat(
        [df["amplitude_bee0"], df["amplitude_bee1"]]
    )
    combined_df["amplitude_non_focal"] = pd.concat(
        [df["amplitude_bee1"], df["amplitude_bee0"]]
    )


def concat_bee_id(combined_df, df):
    combined_df["bee_id_focal"] = pd.concat([df["bee_id0"], df["bee_id1"]])
    combined_df["bee_id_non_focal"] = pd.concat([df["bee_id1"], df["bee_id0"]])


def concat_phase(combined_df, df):
    combined_df["phase_focal"] = pd.concat([df["phase_bee0"], df["phase_bee1"]])
    combined_df["phase_non_focal"] = pd.concat([df["phase_bee1"], df["phase_bee0"]])


def concat_is_bursty(combined_df, df):
    combined_df["is_bursty_focal"] = pd.concat(
        [df["is_bursty_bee0"], df["is_bursty_bee1"]]
    )
    combined_df["is_bursty_non_focal"] = pd.concat(
        [df["is_bursty_bee1"], df["is_bursty_bee0"]]
    )


def concat_is_forager(combined_df, df):
    combined_df["is_foraging_focal"] = pd.concat(
        [df["is_foraging_bee0"], df["is_foraging_bee1"]]
    )
    combined_df["is_foraging_non_focal"] = pd.concat(
        [df["is_foraging_bee1"], df["is_foraging_bee0"]]
    )


def concat_p_value(combined_df, df):
    combined_df["p_value_focal"] = pd.concat([df["p_value_bee0"], df["p_value_bee1"]])
    combined_df["p_value_non_focal"] = pd.concat(
        [df["p_value_bee1"], df["p_value_bee0"]]
    )


def combine_bees_from_interaction_df_to_be_all_focal(df, trans=False):
    combined_df = pd.DataFrame()
    if "r_squared_bee0" in df.columns:
        concat_circ(combined_df, df)
    if "amplitude_bee0" in df.columns:
        concat_amplitude(combined_df, df)
    if "age_bee0" in df.columns:
        concat_ages(combined_df, df)
    if "vel_change_bee0" in df.columns:
        concat_velocity_changes(combined_df, df)
    if "rel_change_bee0" in df.columns:
        concat_rel_velocity_changes(combined_df, df)
    if ("x_pos_start_bee0" in df.columns) or ("focal0_x_trans" in df.columns):
        concat_position(combined_df, df, trans=trans)
    if "bee_id0" in df.columns:
        concat_bee_id(combined_df, df)
    if "interaction_start" in df.columns:
        concat_interaction_times(combined_df, df)
    if "p_value_bee0" in df.columns:
        concat_p_value(combined_df, df)
    if "phase_bee0" in df.columns:
        concat_phase(combined_df, df)
    if "is_foraging_bee0" in df.columns:
        concat_is_forager(combined_df, df)
        concat_is_bursty(combined_df, df)
    return combined_df


def concat_velocity_changes(combined_df, df):
    combined_df["vel_change_bee_focal"] = pd.concat(
        [df["vel_change_bee0"], df["vel_change_bee1"]]
    )
    combined_df["vel_change_bee_non_focal"] = pd.concat(
        [df["vel_change_bee1"], df["vel_change_bee0"]]
    )


def concat_rel_velocity_changes(combined_df, df):
    combined_df["rel_change_bee_focal"] = pd.concat(
        [df["rel_change_bee0"], df["rel_change_bee1"]]
    )
    combined_df["rel_change_bee_non_focal"] = pd.concat(
        [df["rel_change_bee1"], df["rel_change_bee0"]]
    )


def concat_position(combined_df, df, trans=False):
    if trans:
        combined_df["x_pos_start_focal"] = pd.concat(
            [df["focal0_x_trans"], df["focal1_x_trans"]]
        )
        combined_df["x_pos_start_non_focal"] = pd.concat(
            [df["focal1_x_trans"], df["focal0_x_trans"]]
        )
        combined_df["y_pos_start_focal"] = pd.concat(
            [df["focal0_y_trans"], df["focal1_y_trans"]]
        )
        combined_df["y_pos_start_non_focal"] = pd.concat(
            [df["focal1_y_trans"], df["focal0_y_trans"]]
        )
        combined_df["theta_start_focal"] = pd.concat(
            [df["focal0_theta"], df["focal1_theta"]]
        )
        combined_df["theta_start_non_focal"] = pd.concat(
            [df["focal1_theta"], df["focal0_theta"]]
        )
    else:
        combined_df["x_pos_start_focal"] = pd.concat(
            [df["x_pos_start_bee0"], df["x_pos_start_bee1"]]
        )
        combined_df["x_pos_start_non_focal"] = pd.concat(
            [df["x_pos_start_bee1"], df["x_pos_start_bee0"]]
        )
        combined_df["y_pos_start_focal"] = pd.concat(
            [df["y_pos_start_bee0"], df["y_pos_start_bee0"]]
        )
        combined_df["y_pos_start_non_focal"] = pd.concat(
            [df["y_pos_start_bee1"], df["y_pos_start_bee0"]]
        )
        combined_df["theta_start_focal"] = pd.concat(
            [df["theta_start_bee0"], df["theta_start_bee1"]]
        )
        combined_df["theta_start_non_focal"] = pd.concat(
            [df["theta_start_bee1"], df["theta_start_bee0"]]
        )


def clean_interaction_df(interaction_df, column_subset=None):
    if column_subset is None:
        column_subset = interaction_df.columns
    for column in interaction_df[column_subset].columns:
        interaction_df = interaction_df[~interaction_df[column].isnull()]
        interaction_df = interaction_df[~np.isinf(interaction_df[column])]
    return interaction_df


def get_interactions(dt_from=None, dt_to=None, db_connection=None):
    with db_connection as db:
        cursor = db.cursor()

        # get frames
        frame_data = bb_behavior.db.get_frames(0, dt_from, dt_to, cursor=cursor)
        if not frame_data:
            return {None: dict(error="No frames fetched..")}

        interactions_lst = []
        # for each frame id
        for dt, frame_id, cam_id in frame_data:
            # get interactions
            interactions_detected = bb_behavior.db.find_interactions_in_frame(
                frame_id=frame_id, cursor=cursor, max_distance=14.0
            )
            for i in interactions_detected:
                interactions_lst.append(
                    {
                        "bee_id0": i[1],
                        "bee_id1": i[2],
                        "timestamp": dt,
                        "location_info_bee0": (i[5], i[6], i[7]),
                        "location_info_bee1": (i[8], i[9], i[10]),
                    }
                )

        # cluster interactions per time in events
        events = get_all_interactions_over_time(interactions_lst)
        if not events:
            return {None: dict(error="No events found..")}

        # get interactions and velocity changes
        extracted_interactions_lst = []
        for key in events:
            event_dict = events[key]
            if events[key]:
                # extract events parameters as interactions
                interaction_dict = extract_parameters_from_events(event_dict[0])
                # get velocity changes
                # "focal" bee
                (
                    interaction_dict["vel_change_bee0"],
                    interaction_dict["rel_change_bee0"],
                ) = get_velocity_change_per_bee(
                    bee_id=interaction_dict["bee_id0"],
                    interaction_start=interaction_dict["interaction_start"],
                    interaction_end=interaction_dict["interaction_end"],
                )
                # "non-focal" bee
                (
                    interaction_dict["vel_change_bee1"],
                    interaction_dict["rel_change_bee1"],
                ) = get_velocity_change_per_bee(
                    bee_id=interaction_dict["bee_id1"],
                    interaction_start=interaction_dict["interaction_start"],
                    interaction_end=interaction_dict["interaction_end"],
                )
                extracted_interactions_lst.append(interaction_dict)
        return extracted_interactions_lst


def rotate(theta, vec):
    """
    Rotates a 2d vector anti-clockwise by an angle theta (in rad).
    """
    rot_mat = np.array(
        [[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]]
    )
    return rot_mat @ vec


def get_non_focal_bee_mask(x, y, theta):
    # create empty result frame
    non_focal_bee = np.zeros((29, 29))

    # get standard edge points of bee
    a = np.array((-7, -2)).astype(float)
    b = np.array((-7, 2)).astype(float)
    c = np.array((4, 2)).astype(float)
    d = np.array((4, -2)).astype(float)

    # rotate all edge points by theta
    if theta != 0:
        a = rotate(theta, a)
        b = rotate(theta, b)
        c = rotate(theta, c)
        d = rotate(theta, d)

    # add offset and move origin to (14,14) to correspond to
    # matrix coordinates
    a += [x + 14, y + 14]
    b += [x + 14, y + 14]
    c += [x + 14, y + 14]
    d += [x + 14, y + 14]

    points = np.array([a, b, c, d]).round().astype(int)

    # draw rectangle based on edge points
    return cv2.fillPoly(non_focal_bee, [points], 1)


def compute_interaction_points(interaction_df, overlap_dict, whose_change="focal"):
    # create empty matrix for interaction counts
    counts = np.zeros((9, 16))

    # create empty matrix for accumulating velocities
    vels = np.zeros((9, 16))

    for i in range(len(interaction_df)):
        overlap = overlap_dict[interaction_df.index[i]].reshape((9, 16))

        # add count and velocity values
        if np.sum(overlap) >= 1:
            counts += overlap
            vel = (
                overlap
                * interaction_df.iloc[i][["vel_change_bee_%s" % whose_change]][0]
            )
            if not np.isnan(vel).any():
                vels += vel

    avg_vel = np.divide(vels, counts, out=np.zeros_like(vels), where=counts != 0)
    return counts, avg_vel


def create_overlap_dict(interaction_df, focal_id):
    overlap_dict = {}
    n_rows = len(interaction_df)

    interaction_df = interaction_df.to_dict(orient="index")

    for index in interaction_df:
        overlap_dict[index] = get_bee_body_overlap(
            interaction_df[index], focal_id
        ).ravel()
        if index % 10000 == 0:
            print("%d/%d" % (index, n_rows))

    return overlap_dict


def recreate_overlap_dict_from_df(overlap_df):
    overlap_dict_new = {}
    for column in overlap_df.columns:
        overlap_dict_new[column] = overlap_df[column].to_numpy().reshape((8, 16))
    return overlap_dict_new


def get_bee_body_overlap(interaction_df_row, focal_id):
    # create mask for focal bee
    focal_bee = np.zeros((29, 29))
    focal_bee[10:19, 5:21] = 1

    # get coordinates of interacting bee
    x = interaction_df_row[f"focal{focal_id}_x_trans"]
    y = interaction_df_row[f"focal{focal_id}_y_trans"]
    theta = interaction_df_row[f"focal{focal_id}_theta_trans"]

    # create mask for non-focal bee
    non_focal_bee = get_non_focal_bee_mask(x, y, theta)
    # get overlap
    overlap = np.logical_and(focal_bee, non_focal_bee)
    return overlap[10:19, 5:21].astype(bool)


def filter_combined_interaction_df_by_overlaps(combined_df, overlap_df):
    combined_df["overlapping"] = np.zeros(len(combined_df.index)).astype(bool).tolist()
    for column in overlap_df.columns:
        combined_df["overlapping"].iloc[column] = bool(overlap_df[column].sum())
    combined_df = combined_df[combined_df["overlapping"]]
    combined_df.drop(columns=["overlapping"], inplace=True)
    return combined_df


def extract_parameters_from_random_sampled_interactions(
    event, interaction_start, interaction_end
):
    return {
        "bee_id0": event[0][0],
        "bee_id1": event[1][0],
        "interaction_start": interaction_start,
        "interaction_end": interaction_end,
        "bee_id0_x_pos_start": event[0][1],
        "bee_id0_y_pos_start": event[0][2],
        "bee_id0_theta_start": event[0][3],
        "bee_id1_x_pos_start": event[1][1],
        "bee_id1_y_pos_start": event[1][2],
        "bee_id1_theta_start": event[1][3],
        "bee_id0_x_pos_end": event[0][4],
        "bee_id0_y_pos_end": event[0][5],
        "bee_id0_theta_end": event[0][6],
        "bee_id1_x_pos_end": event[1][4],
        "bee_id1_y_pos_end": event[1][5],
        "bee_id1_theta_end": event[1][6],
    }


def get_intermediate_time_windows_df(df, dt_from, dt_to):
    intermediate_df = pd.DataFrame(
        columns=["bee_id", "non_interaction_start", "non_interaction_end"]
    )
    for bee_id, group in df.groupby(["bee_id_focal"]):
        group.sort_values(by=["interaction_start"], inplace=True)
        non_interaction_start = dt_from
        non_interaction_end = group["interaction_start"].iloc[0]
        if non_interaction_start < non_interaction_end:
            intermediate_df = pd.concat(
                [
                    intermediate_df,
                    create_row_non_interaction_df(
                        bee_id, non_interaction_start, non_interaction_end
                    ),
                ],
                ignore_index=True,
            )
        # for bee_id subframe
        current_interaction_start = group["interaction_start"].iloc[0]
        current_interaction_end = group["interaction_end"].iloc[0]
        for index, row in group.iterrows():
            if in_between(
                current_interaction_start,
                row["interaction_start"],
                current_interaction_end,
                row["interaction_end"],
            ):
                continue
            if overlap_after(
                current_interaction_start,
                row["interaction_start"],
                current_interaction_end,
                row["interaction_end"],
            ):
                current_interaction_end = row["interaction_end"]
            if after(
                current_interaction_start,
                row["interaction_start"],
                current_interaction_end,
                row["interaction_end"],
            ):
                intermediate_df = pd.concat(
                    [
                        intermediate_df,
                        create_row_non_interaction_df(
                            bee_id, current_interaction_end, row["interaction_start"]
                        ),
                    ],
                    ignore_index=True,
                )
                current_interaction_start = row["interaction_start"]
                current_interaction_end = row["interaction_end"]
            if row["interaction_end"] > dt_to:
                current_interaction_end = row["interaction_end"]
                break
        if current_interaction_end <= dt_to:
            intermediate_df = pd.concat(
                [
                    intermediate_df,
                    create_row_non_interaction_df(
                        bee_id, current_interaction_end, dt_to
                    ),
                ],
                ignore_index=True,
            )
    return intermediate_df


def in_between(
    interaction_start_0, interaction_start_1, interaction_end_0, interaction_end_1
):
    # assuming interaction_start_0 <= interaction_start_1
    return (interaction_start_0 <= interaction_start_1) & (
        interaction_end_0 >= interaction_end_1
    )


def overlap_after(
    interaction_start_0, interaction_start_1, interaction_end_0, interaction_end_1
):
    # assuming interaction_start_0 <= interaction_start_1
    return (
        (interaction_start_0 <= interaction_start_1)
        & (interaction_start_1 < interaction_end_0)
        & (interaction_end_0 < interaction_end_1)
    )


def after(
    interaction_start_0, interaction_start_1, interaction_end_0, interaction_end_1
):
    # assuming interaction_start_0 <= interaction_start_1
    return interaction_end_0 < interaction_start_1


def create_row_non_interaction_df(bee_id, non_interaction_start, non_interaction_end):
    return pd.DataFrame(
        {
            "bee_id": [bee_id],
            "non_interaction_start": [non_interaction_start],
            "non_interaction_end": [non_interaction_end],
        }
    )


def add_features(interactions_df, feature_df, bee_id, features):
    """

    :param interactions_df:
    :param feature_df:
    :param bee_id:
    :param features:
    :return:
    """
    interactions_df.rename(columns={"bee_id%d" % bee_id: "bee_id"}, inplace=True)
    interactions_df = pd.merge(
        interactions_df, feature_df, how="left", on=["date", "bee_id"]
    )

    rename_dict = {feature: feature + "_bee%d" % bee_id for feature in features}
    rename_dict["bee_id"] = "bee_id%d" % bee_id

    interactions_df.rename(columns=rename_dict, inplace=True)

    return interactions_df


def add_circadianess_to_interaction_df(interactions_df, circadian_df):
    """

    :param interactions_df:
    :param circadian_df:
    :return:
    """
    interactions_df["date"] = [
        interaction.replace(hour=0, minute=0, second=0, microsecond=0)
        + datetime.timedelta(hours=12)
        for interaction in interactions_df["interaction_start"]
    ]

    fit_features = ["phase", "r_squared", "amplitude", "p_value", "age"]

    interactions_df = add_features(
        interactions_df, circadian_df, bee_id=0, features=fit_features
    )
    interactions_df = add_features(
        interactions_df, circadian_df, bee_id=1, features=fit_features
    )

    interactions_df.drop(columns=["date"], inplace=True)

    return interactions_df


def add_feature_to_interaction_df(interactions_df, feature_df, features):
    interactions_df["date"] = interactions_df["interaction_start"].dt.date.astype(
        "datetime64[ns]"
    )

    interactions_df = add_features(
        interactions_df, feature_df, bee_id=0, features=features
    )
    interactions_df = add_features(
        interactions_df, feature_df, bee_id=1, features=features
    )

    interactions_df.drop(columns=["date"], inplace=True)

    return interactions_df


def get_start_velocity(df):
    df["velocity_start_focal"] = (
        df["vel_change_bee_focal"] * 100 / df["rel_change_bee_focal"]
    )
    df["velocity_start_non_focal"] = (
        df["vel_change_bee_non_focal"] * 100 / df["rel_change_bee_non_focal"]
    )


def filter_overlap(interaction_df):
    """

    :param interaction_df:
    :return:
    """
    interaction_df = interaction_df[interaction_df["overlapping"].values]
    return interaction_df


def add_velocity_change_to_intermediate_time_windows_df(intermediate_df, velocities):
    vel_change_lst = len(intermediate_df) * [None]
    rel_change_lst = len(intermediate_df) * [None]
    for index, row in intermediate_df.iterrows():
        # get velocity changes
        vel_change_lst[index], rel_change_lst[index] = get_velocity_change_per_bee(
            interaction_start=row["non_interaction_start"],
            interaction_end=row["non_interaction_end"],
            velocities=velocities,
        )
    intermediate_df["vel_change_bee"] = vel_change_lst
    intermediate_df["rel_change_bee"] = rel_change_lst
    return intermediate_df


def add_circadian_meta_data_to_intermediate_time_windows_df(
    intermediate_df, interaction_df
):
    meta_params = ["age", "amplitude", "circadianess", "p_value"]
    meta_params_dict = {}
    for param in meta_params:
        meta_params_dict[param] = len(intermediate_df) * [None]
    for index, row in intermediate_df.iterrows():
        for param in meta_params:
            try:
                meta_params_dict[param][index] = (
                    interaction_df[
                        (row["bee_id"] == interaction_df["bee_id_focal"])
                        & (
                            row["non_interaction_start"].to_pydatetime().date()
                            == interaction_df["interaction_start"].dt.date
                        )
                    ][param + "_focal"]
                    .sample(n=1)
                    .iloc[0]
                )
            except (KeyError, ValueError):
                continue
    for param in meta_params:
        intermediate_df[param] = meta_params_dict[param]
    return intermediate_df


def create_intermediate_df_per_bee(dt_from, dt_to, interaction_df, velocities):
    intermediate_df = get_intermediate_time_windows_df(interaction_df, dt_from, dt_to)
    intermediate_df = add_velocity_change_to_intermediate_time_windows_df(
        intermediate_df, velocities
    )
    intermediate_df = add_circadian_meta_data_to_intermediate_time_windows_df(
        intermediate_df, interaction_df
    )
    return intermediate_df


def get_min_and_max_pos(path):
    interactions = pd.read_pickle(path)
    interactions = interactions[
        ["x_pos_start_bee0", "y_pos_start_bee0", "x_pos_start_bee1", "y_pos_start_bee1"]
    ]
    x_vals = pd.concat(
        [interactions["x_pos_start_bee0"], interactions["x_pos_start_bee1"]]
    )
    y_vals = pd.concat(
        [interactions["y_pos_start_bee0"], interactions["y_pos_start_bee1"]]
    )

    return np.min(x_vals), np.max(x_vals), np.min(y_vals), np.max(y_vals)


def assign_random_bees_as_interactions(db, df_grouped, cam_ids=None):
    """

    :param db:
    :param df_grouped:
    :return:
    """
    cursor = db.cursor()
    # for each interaction
    interactions = []
    for i, group in df_grouped.iterrows():
        table_name = bb_behavior.db.base.get_detections_tablename()
        interaction_start = group["interaction_start"]
        interaction_end = group["interaction_end"]
        delta = datetime.timedelta(seconds=1)
        min_cam_id = min(cam_ids)
        max_cam_id = max(cam_ids)
        sql_statement = """SELECT A.bee_id, A.x_pos, A.y_pos, A.orientation, B.x_pos, B.y_pos, B.orientation
                               FROM {} A, {} B
                               WHERE A.timestamp BETWEEN %s AND %s 
                                     AND A.cam_id BETWEEN %s AND %s 
                                     AND A.bee_id_confidence >= 0.01 
                                     AND B.timestamp BETWEEN %s AND %s 
                                     AND B.cam_id BETWEEN 2 AND 3 
                                     AND B.bee_id_confidence >= 0.01 
                                     AND A.bee_id=B.bee_id
                               ORDER BY random()
                               limit %s;""".format(
            table_name, table_name
        )
        cursor.execute(
            sql_statement,
            (
                interaction_start,
                interaction_start + delta,
                str(min_cam_id),
                str(max_cam_id),
                interaction_end,
                interaction_end + delta,
                str(2 * group["bee_id0"]),
            ),
        )
        random_sampled_interactions = cursor.fetchall()

        for index in range(0, len(random_sampled_interactions), 2):
            try:
                # pick two random samples
                interaction_dict = extract_parameters_from_random_samples(
                    random_sampled_interactions[index : index + 2],
                    interaction_start,
                    interaction_end,
                )
            except IndexError:
                continue

            # append interaction to interaction list
            interactions.append(interaction_dict)
    return interactions


def get_sub_interaction_df_for_null_model_sampling(
    dt_from, dt_to, interaction_model_path
):
    """

    :param dt_from:
    :param dt_to:
    :param interaction_model_path:
    :return:
    """
    # get interactions start and end time current interaction model
    # read interaction frame and get relevant subset of columns
    df_all = pd.read_pickle(interaction_model_path)
    df_all.drop(
        columns=df_all.columns.difference(
            ["interaction_start", "interaction_end", "bee_id0", "overlapping"]
        ),
        inplace=True,
    )
    # filter overlap
    df_all = filter_overlap(df_all)
    # subset time window
    df = df_all[
        (df_all["interaction_start"] >= dt_from) & (df_all["interaction_end"] < dt_to)
    ]
    del df_all
    # round per second and group df
    df["interaction_start"] = df["interaction_start"].dt.round("1S")
    df["interaction_end"] = df["interaction_end"].dt.round("1S")
    df_grouped = (
        df.groupby(by=["interaction_start", "interaction_end"])["bee_id0"]
        .count()
        .reset_index()
    )
    del df
    return df_grouped
