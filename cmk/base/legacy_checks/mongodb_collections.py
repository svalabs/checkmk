#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<mongodb_collections:sep(9)>>>
# json


# mypy: disable-error-code="var-annotated"

import json

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.plugins.lib.mongodb import parse_date

check_info = {}


def parse_mongodb_collections(string_table):
    if string_table:
        return json.loads(str(string_table[0][0]))
    return {}


def inventory_mongodb_collections(databases_dict):
    """
    one service per collection
    :param databases_dict:
    :return:
    """
    db_coll_list = []
    for db_name in databases_dict:
        db_coll_list += [
            (f"{db_name}.{coll_name}", {})
            for coll_name in databases_dict.get(db_name).get("collstats", [])
        ]
    return db_coll_list


def check_mongodb_collections(item, params, databases_dict):
    """

    :param item:
    :param params:
    :param databases_dict:
    :return:
    """
    database_name, collection_name = _mongodb_collections_split_namespace(item)
    collection_stats = (
        databases_dict.get(database_name, {}).get("collstats", {}).get(collection_name, {})
    )

    for key, label in (
        ("size", "Uncompressed size in memory"),
        ("storageSize", "Allocated for document storage"),
        ("totalIndexSize", "Total size of indexes"),
    ):
        if key not in collection_stats:
            return

        try:
            value = int(collection_stats.get(key))
        except (KeyError, ValueError):
            continue

        levels = params.get("levels_%s" % key)

        if levels and key in ["size", "storageSize"]:
            levels = (levels[0] * 1024**2, levels[1] * 1024**2)  # MiB to bytes
        elif levels and key in ["totalIndexSize"]:
            levels = (levels[0] * 1024, levels[1] * 1024)  # KByte to bytes

        perfdata = _mongodb_collections_get_perfdata_key(key)
        yield check_levels(
            value, perfdata, levels, human_readable_func=render.bytes, infoname=label
        )

    # check number of indexes per collection (max is 64 indexes)
    try:
        yield check_levels(
            int(collection_stats.get("nindexes")),
            None,
            (62, 65),
            human_readable_func=lambda v: "%d" % v,
            infoname="Number of indexes",
        )
    except (TypeError, ValueError):
        pass

    yield 0, _mongodb_collections_long_output(collection_stats)


def _mongodb_collections_split_namespace(namespace):
    """
    split namespace into database name and collection name
    :param namespace:
    :return:
    """
    try:
        names = namespace.split(".", 1)
        if len(names) > 1:
            return names[0], names[1]
        if len(names) > 0:
            return names[0], ""
    except ValueError:
        pass
    except AttributeError:
        pass
    raise ValueError("error parsing namespace %s" % namespace)


def _mongodb_collections_get_perfdata_key(key):
    if key == "size":
        return "mongodb_collection_size"
    if key == "storageSize":
        return "mongodb_collection_storage_size"
    if key == "totalIndexSize":
        return "mongodb_collection_total_index_size"
    return None


def _mongodb_collections_long_output(data):
    is_sharded = data.get("sharded", None)
    # output per collection
    long_output = ["Collection"]
    if is_sharded:
        long_output.append("- Sharded: %s (Data distributed in cluster)" % is_sharded)
        long_output.append(
            "- Shards: %s (Number of shards)" % _mongodb_collections_get_as_int(data, "shardsCount")
        )
        long_output.append(
            "- Chunks: %s (Total number of chunks)"
            % _mongodb_collections_get_as_int(data, "nchunks")
        )

    long_output.append(
        "- Document Count: %s (Number of documents in collection)"
        % _mongodb_collections_get_as_int(data, "count")
    )
    long_output.append(
        "- Object Size: %s (Average object size)"
        % _mongodb_collections_bytes_human_readable(data, "avgObjSize")
    )
    long_output.append(
        "- Collection Size: %s (Uncompressed size in memory)"
        % _mongodb_collections_bytes_human_readable(data, "size")
    )
    long_output.append(
        "- Storage Size: %s (Allocated for document storage)"
        % _mongodb_collections_bytes_human_readable(data, "storageSize")
    )

    long_output.append("")
    long_output.append("Indexes:")
    long_output.append(
        "- Total Index Size: %s (Total size of all indexes)"
        % _mongodb_collections_bytes_human_readable(data, "totalIndexSize")
    )
    long_output.append(
        "- Number of Indexes: %s" % _mongodb_collections_get_as_int(data, "nindexes")
    )
    for index in _mongodb_collections_get_indexes_as_list(data):
        timestamp_for_humans = _mongodb_collections_timestamp_human_readable(index[2])
        long_output.append(
            f"-- Index '{index[0]}' used {index[1]} times since {timestamp_for_humans}"
        )

    return "\n" + "\n".join(long_output)


def _mongodb_collections_get_indexes_as_list(data):
    """
    get all indexes as a list of (name, access timestamp) and sort them
    :param data:
    :return:
    """
    if "indexStats" not in data:
        return []

    index_list = []
    for index_stat in data.get("indexStats"):
        index_name = index_stat.get("name", "n/a")
        last_access = parse_date(index_stat.get("accesses", {}).get("since", {}).get("$date", 0))
        number_of_operations = index_stat.get("accesses", {}).get("ops", 0)
        index_list.append((index_name, number_of_operations, last_access))

    index_list.sort(key=_mongodb_collections_sort_second, reverse=True)
    return index_list


def _mongodb_collections_sort_second(tup):
    return tup[1]


def _mongodb_collections_bytes_human_readable(data, key):
    try:
        return render.bytes(int(data.get(key)))
    except (TypeError, ValueError):
        return "n/a"


def _mongodb_collections_timestamp_human_readable(value):
    try:
        return render.datetime(int(value))
    except (TypeError, ValueError):
        return "n/a"


def _mongodb_collections_get_as_int(data, key):
    try:
        return int(data.get(key))
    except (TypeError, ValueError):
        return "n/a"


check_info["mongodb_collections"] = LegacyCheckDefinition(
    name="mongodb_collections",
    parse_function=parse_mongodb_collections,
    service_name="MongoDB Collection: %s",
    discovery_function=inventory_mongodb_collections,
    check_function=check_mongodb_collections,
    check_ruleset_name="mongodb_collections",
    check_default_parameters={},
)
