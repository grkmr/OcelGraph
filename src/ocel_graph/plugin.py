from typing import Annotated

from ocelescope import (
    OCEL,
    OCELAnnotation,
    Plugin,
    plugin_method,
)

from .input import OCELGraphInput
from .resource import OCELGraph
from .util import mine_ocel_graph


class OcelGraphDiscovery(Plugin):
    label = "Ocel Graph"
    description = "Discovers a Object-Centric event log graph"
    version = "1.0.5"

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
