import datetime
import hashlib
from collections import defaultdict
from pathlib import Path

import click
import numpy as np
import pandas as pd
from sqlite_utils import Database


def process_champions_dataset(dataset, admin_levels):
    # lowercase all keys
    for k in list(dataset.keys()):
        if k.lower() != k:
            dataset[k.lower()] = dataset.pop(k)
    # add admin levels
    for key, value in admin_levels.items():
        dataset[f"level_{key}"] = value
    # add a full name with all admin levels - without name
    dataset["full_name"] = " > ".join(
        [dataset["level_continent"]]
        + [dataset.get(f"level_{key}", "") for key in range(0, 10)]
    )

    return dataset


def process_points_dataset(dataset, admin_levels):
    # replace keys:
    for k, k_new in (
        [
            (f"Distance to {n}% (km)", f"distance_to_{n}_in_km")
            for n in [25, 50, 75, 90, 99]
        ]
        + [
            (f"Points bonus @ {n}%", f"points_bonus_at_{n}")
            for n in [25, 50, 75, 90, 99]
        ]
        + [("Completed (km)", "completed_in_km"), ("Total (km)", "total_in_km")]
    ):
        if k in dataset:
            dataset[k_new] = dataset.pop(k)
    # lowercase all keys
    for k in list(dataset.keys()):
        if k.lower() != k:
            dataset[k.lower()] = dataset.pop(k)
    # add admin levels
    for key, value in admin_levels.items():
        dataset[f"level_{key}"] = value
    # mark if row is a region
    if "-" in dataset["name"]:
        dataset["region"] = True

    # remove all "-" from name
    dataset["pure_name"] = dataset["name"].replace("-", "").strip()

    # add a full name with all admin levels - include empty ones!
    dataset["full_name"] = " > ".join(
        [dataset["level_continent"]]
        + [dataset.get(f"level_{key}", "") for key in range(0, 10)]
        + [dataset["pure_name"]]
    )

    return dataset


@click.command()
@click.argument("filename", type=click.Path(exists=True))
def main(filename):
    # use first row as headers
    df = pd.read_excel(filename, header=1)

    db = Database(Path(filename).stem + ".db")
    if not db["points"].exists():
        db["points"].create(
            # predefine the interesting fields to have this fields ordered
            {
                "id": str,
                "pure_name": str,
                "full_name": str,
                "region": bool,
                "completed_in_km": float,
                "percentage": float,
                "distance_to_25_in_km": float,
                "distance_to_50_in_km": float,
                "distance_to_75_in_km": float,
                "updated": str,
            },
            pk="id",
        )

    if not db["champions"].exists():
        db["champions"].create(
            {
                "id": str,
                "full_name": str,
                "name": str,
                "points": float,
                "updated": str,
            },
            pk="id",
        )

    # use the date from the filename for "updated" column
    dt = datetime.datetime.strptime(filename, "earth-%d-%m-%y.xlsx").date()

    admin_levels = defaultdict(dict)
    datasets = defaultdict(list)
    for index, row in df.iterrows():
        if row.Name == "Earth":
            # ignore "Earth"
            continue
        if row.Name in ["East Asia", "Europe"]:  # values missing for other continents!
            # Continents don't have a prefix so this is the easiest way to filter them out
            admin_levels["continent"] = row.Name
            continue

        if row.Name.startswith("-"):
            cnt = row.Name.count("-")
            level = cnt + 1
            # names for administrations are different by country,
            # use the count of "-" as level number
            admin_levels[level] = row.Name.replace("-", "").strip()
            # clean old levels
            for i in range(10):
                if i > level:
                    if i in admin_levels:
                        del admin_levels[i]

        if row.Name.startswith("Achievements"):
            # drop this otherwise empty row
            continue
        if row.Name.startswith("Bonus points"):
            # drop for now
            continue
        elif row.Name.startswith("Monthly champion"):
            # champion rows have empty (nan) columns, remove them first
            ds = process_champions_dataset(row.dropna().to_dict(), admin_levels)
            table = "champions"
        else:
            ds = process_points_dataset(row.to_dict(), admin_levels)
            table = "points"

        # create an id based on the full_name (including admin levels)
        m = hashlib.sha1()
        m.update(ds["full_name"].encode())
        ds["id"] = m.hexdigest()
        ds["updated"] = dt

        # prepare for bulkwrite of all datasets
        datasets[table].append(ds)

    for table in datasets.keys():
        db[table].insert_all(datasets[table], alter=True, replace=True)


if __name__ == "__main__":
    main()
