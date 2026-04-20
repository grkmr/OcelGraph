from typing import Annotated

from ocelescope import (
    OCEL,
    OCEL_FIELD,
    Graph,
    GraphEdge,
    GraphNode,
    GraphvizLayoutConfig,
    OCELAnnotation,
    Plugin,
    PluginInput,
    Resource,
    generate_color_map,
    plugin_method,
)
from pydantic import BaseModel, Field

from .util import mine_ocel_graph


# region Input definition
class ObjectRoot(BaseModel):
    class Config:
        title = "Object"

    object_id: str = OCEL_FIELD(
        field_type="object_id",
        title="Object Id",
        ocel_id="ocel",
        description="The ID of the Event which is the root of the OcelGraph",
    )


class EventRoot(BaseModel):
    class Config:
        title = "Event"

    event_id: str = OCEL_FIELD(
        field_type="event_id",
        title="Event Id",
        ocel_id="ocel",
        description="The ID of the Event which is the root of the OcelGraph",
    )


class OCELGraphInput(PluginInput):
    root: ObjectRoot | EventRoot
    depth: int = Field(
        title="OCEL Graph Depth", description="The maximum depth of the ocel graph", default=3, gt=0, le=10
    )
    max_neighbours: int = Field(
        title="Maximum Neighbours", description="The maximum amount of neighbours a node can have", gt=0, default=5
    )


# endregion


# region Resource Defintion
class EventNode(BaseModel):
    id: str
    activity: str


class ObjectNode(BaseModel):
    id: str
    object_type: str


class Relation(BaseModel):
    qualifier: str
    source: str
    target: str
    object_type: str | None = None


class OCELGraph(Resource):
    label = "Ocel Graph"
    description = "A Ocel graph"

    events: list[EventNode] = []
    objects: list[ObjectNode] = []
    relations: list[Relation] = []

    @property
    def event_ids(self) -> list[str]:
        return [event.id for event in self.events]

    @property
    def object_ids(self) -> list[str]:
        return [object.id for object in self.objects]

    def visualize(self) -> Graph:
        color_map = generate_color_map(list(set([object.object_type for object in self.objects])))

        object_nodes = [
            GraphNode(
                id=object_node.id, shape="rectangle", label=object_node.id, color=color_map[object_node.object_type]
            )
            for object_node in self.objects
        ]

        event_nodes = [GraphNode(id=event.id, shape="rectangle", label=event.id) for event in self.events]

        edges = [
            GraphEdge(
                source=edge.source,
                target=edge.target,
                label=edge.qualifier,
                color=color_map[edge.object_type] if edge.object_type else None,
            )
            for edge in self.relations
        ]

        return Graph(
            type="graph",
            nodes=object_nodes + event_nodes,
            edges=edges,
            layout_config=GraphvizLayoutConfig(engine="neato", graphAttrs={"overlap": "prism"}),
        )


# endregion


class OcelGraphDiscovery(Plugin):
    label = "Ocel Graph"
    description = "Discovers a Object-Centric event log graph"
    version = "0.1.0"

    @plugin_method(label="Mine OCEL Graph", description="Mines a OCEL Graph")
    def mine_ocel_graph(
        self,
        ocel: Annotated[
            OCEL,
            OCELAnnotation(label="Event Log", description="The log from which the ocel graph should be mined from"),
        ],
        input: OCELGraphInput,
    ) -> OCELGraph:
        return mine_ocel_graph(ocel, input)
