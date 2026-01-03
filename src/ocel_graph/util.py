from typing import cast

import pandas as pd
from ocelescope import OCEL

from .inputs.ocelGraph import EventRoot, OCELGraphInput
from .resources.ocelGraph import E2ORelation, EventNode, O2ORelation, ObjectNode, OCELGraph


def group_relation_entity(
    df: pd.DataFrame,
    entity_ids: list[str],
    id_column: str,
    type_column: str,
    target_id_column: str,
):
    """
    Count how many 'target' entities are linked to each entity (event or object).

    Returns:
        DataFrame with columns: id, type, count
    """
    return (
        df[df[id_column].isin(entity_ids)]
        .groupby([id_column, type_column])[target_id_column]
        .size()
        .reset_index()
        .rename(columns={id_column: "id", type_column: "type", target_id_column: "count"})
    )


def mine_ocel_graph(ocel: OCEL, input: OCELGraphInput):
    graph = OCELGraph()

    events_to_visit = []
    objects_to_visit = []

    if isinstance(input.root, EventRoot):
        root_id = input.root.event_id
        root = ocel.events[ocel.events[ocel.ocel.event_id_column] == input.root.event_id].iloc[0]
        events_to_visit.append(EventNode(id=input.root.event_id, activity_type=root[ocel.ocel.event_activity]))
    else:
        root_id = input.root.object_id
        root = ocel.objects[ocel.objects[ocel.ocel.object_id_column] == input.root.object_id].iloc[0]
        objects_to_visit.append(ObjectNode(id=input.root.object_id, object_type=root[ocel.ocel.object_type_column]))

    for _ in range(input.depth):
        # Get current frontier IDs
        event_ids_to_visit = [event.id for event in events_to_visit]
        object_ids_to_visit = [obj.id for obj in objects_to_visit]

        # Get event-object relations using XOR and not already in the graph
        relations: pd.DataFrame = cast(
            pd.DataFrame,
            ocel.relations[
                (
                    (ocel.relations[ocel.ocel.event_id_column].isin(event_ids_to_visit))
                    ^ (ocel.relations[ocel.ocel.object_id_column].isin(object_ids_to_visit))
                )
                & ~(ocel.relations[ocel.ocel.event_id_column].isin(graph.event_ids))
                & ~(ocel.relations[ocel.ocel.object_id_column].isin(graph.object_ids))
            ],
        )

        # Count object neighbors per event
        events = group_relation_entity(
            df=relations,
            entity_ids=event_ids_to_visit,
            id_column=ocel.ocel.event_id_column,
            type_column=ocel.ocel.event_activity,
            target_id_column=ocel.ocel.object_id_column,
        )

        # Count event neighbors per object
        e2o_objects = group_relation_entity(
            df=relations,
            entity_ids=object_ids_to_visit,
            id_column=ocel.ocel.object_id_column,
            type_column=ocel.ocel.object_type_column,
            target_id_column=ocel.ocel.event_id_column,
        )

        # Get object-object (o2o) relations using XOR
        o2o = cast(
            pd.DataFrame,
            ocel.o2o[
                (
                    (ocel.o2o["ocel:oid_1"].isin(object_ids_to_visit))
                    ^ (ocel.o2o["ocel:oid_2"].isin(object_ids_to_visit))
                )
                & ~(ocel.o2o["ocel:oid_1"].isin(graph.object_ids))
                & ~(ocel.o2o["ocel:oid_2"].isin(graph.object_ids))
            ],
        )

        # Normalize and mirror o2o (treat as undirected)
        o2o = o2o.rename(
            columns={"ocel:oid_1": "id", "ocel:type_1": "type", "ocel:oid_2": "target_id", "ocel:type_2": "target_type"}
        )

        mirrored = o2o.rename(
            columns={"target_id": "id", "target_type": "type", "id": "target_id", "type": "target_type"}
        )

        mirrored_o2o = pd.concat([o2o, mirrored], ignore_index=True).rename(columns={"ocel:qualifier": "qualifier"})

        # Count o2o neighbours for each object
        o2o_objects = group_relation_entity(
            df=mirrored_o2o,
            entity_ids=object_ids_to_visit,
            id_column="id",
            type_column="type",
            target_id_column="target_id",
        )

        # Combine object neighbour counts
        objects = (
            pd.concat([o2o_objects, e2o_objects], ignore_index=True)
            .groupby(["id", "type"], as_index=False)["count"]
            .sum()
        )

        # Update graph with this layer
        graph.objects = graph.objects + objects_to_visit
        graph.events = graph.events + events_to_visit

        # Prepare for next layer
        events_to_visit = []
        objects_to_visit = []

        object_id_with_neighbours = [
            row["id"] for _, row in objects.iterrows() if row["count"] <= input.max_neighbours or row["id"] == root_id
        ]
        event_id_with_neighbours = [
            row["id"] for _, row in events.iterrows() if row["count"] <= input.max_neighbours or row["id"] == root_id
        ]

        for _, row in (
            cast(pd.DataFrame, mirrored_o2o[mirrored_o2o["id"].isin(object_id_with_neighbours)])
            .drop_duplicates(subset=["target_id"], keep="first")
            .iterrows()
        ):
            graph.o2o_relations.append(
                O2ORelation(source=str(row["id"]), target=str(row["target_id"]), qualifier=str(row["qualifier"]))
            )
            objects_to_visit.append(ObjectNode(id=str(row["target_id"]), object_type=str(row["target_type"])))

        for _, row in (
            cast(pd.DataFrame, relations[relations["ocel:oid"].isin(object_id_with_neighbours)])
            .drop_duplicates(subset=["ocel:eid"], keep="first")
            .iterrows()
        ):
            graph.e2o_relations.append(
                E2ORelation(
                    event_id=str(row["ocel:eid"]),
                    object_id=str(row["ocel:oid"]),
                    qualifier=str(row["ocel:qualifier"]),
                    object_type=str(row["ocel:type"]),
                )
            )
            events_to_visit.append(EventNode(id=str(row["ocel:eid"]), activity_type=str(row["ocel:activity"])))

        for _, row in (
            cast(
                pd.DataFrame,
                relations[
                    relations["ocel:eid"].isin(event_id_with_neighbours)
                    & ~relations["ocel:oid"].isin([obj.id for obj in objects_to_visit])
                ],
            )
            .drop_duplicates(subset=["ocel:oid"], keep="first")
            .iterrows()
        ):
            graph.e2o_relations.append(
                E2ORelation(
                    event_id=str(row["ocel:eid"]),
                    object_id=str(row["ocel:oid"]),
                    qualifier=str(row["ocel:qualifier"]),
                    object_type=str(row["ocel:type"]),
                )
            )
            objects_to_visit.append(ObjectNode(id=str(row["ocel:oid"]), object_type=str(row["ocel:type"])))

    graph.objects = graph.objects + objects_to_visit
    graph.events = graph.events + events_to_visit

    return graph
