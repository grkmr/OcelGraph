from typing import Annotated

from ocelescope import OCEL, OCEL_FIELD, OCELAnnotation, Plugin, PluginInput, plugin_method
from pydantic import BaseModel, Field

from .resources.ocelGraph import OCELGraph
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
