import json
from typing import List

from bgp import BgpIntRouter, BgpExtRouter, Announcement, BgpConfig
from common import Flow
from experiments.scenarios import BaseScenario
from explorer import Explorer
# from netdice.explorer import Explorer
from failures import LinkFailureModel
from input_parser import NameResolver, InputParser
from my_logging import log, log_context, time_measure
from prob import Prob
from problem import Problem
from properties import WaypointProperty


class Scenario(BaseScenario):
    def __init__(self, topo_name, suffix, topology_file: str, scenario_file: str, precision: float, collect_hot=False,
                 collect_precision=False, timeout_h=1.0):
        super().__init__(topo_name, suffix, timeout_h)
        self.topology_file = topology_file
        self.scenario_file = scenario_file
        self.precision = precision
        self.collect_hot = collect_hot
        self.collect_precision = collect_precision
        self.scenarios = []
        self.name_resolver = None
        self.nof_nodes = -1
        self.links = []
        self.nof_links = -1

    def run(self):
        self.name_resolver = NameResolver()
        self._load_topology()
        self._load_scenarios()

        log.data("topology", {"name": self.topo_name, "nof_nodes": self.nof_nodes, "nof_links": self.nof_links})

        for i, scenario in enumerate(self.scenarios):
            log.info("running %s * %d", str(self), i)

            with log_context(i):
                bgp_config = self._load_bgp_config(scenario)

                failure_model = LinkFailureModel(Prob(0.001))

                # create property
                prop = self._load_property(scenario)

                # create problem
                problem = Problem(self.nof_nodes, self.links, [], bgp_config, failure_model, prop)
                problem.target_precision = self.precision

                # collect hot edges
                with time_measure("time-explore"):
                    explorer = Explorer(problem, stat_hot=self.collect_hot, stat_prec=self.collect_precision)
                    explorer.explore_all()

                # # run exploration
                # with time_measure("time-explore"):
                #     explorer = Explorer(problem, stat_hot=self.collect_hot, stat_prec=self.collect_precision)
                #     sol = explorer.explore_all(timeout=self.timeout)
                # log.data("finished", {
                #     "precision": sol.p_explored.invert().val(),
                #     "p_property": sol.p_property.val(),
                #     "num_explored": sol.num_explored
                # })

    def _load_scenarios(self):
        with open(self.scenario_file, 'r') as f:
            root = json.load(f)
        topology = root['topology']
        self.nof_nodes = topology['nof_nodes']
        self.nof_links = topology['nof_links']
        self.scenarios = root['scenarios']

    def _load_topology(self):
        self.parser = InputParser(self.topology_file)
        if self.topology_file.split(".")[-1] == "json":
            self.parser._load_data()
            _, self.links = self.parser._topology_from_data(self.parser.data["topology"], self.name_resolver)
        else:
            _, self.links = self.parser._topology_from_data({"file": self.topology_file}, self.name_resolver)

    def _load_bgp_config(self, scenario):
        int_routers = []
        for id in range(0, self.nof_nodes):
            int_routers.append(BgpIntRouter(id, id, 500))

        self._setup_rr_topology(int_routers, scenario['rrs'])

        # create border routers
        brs = []
        for br_id in scenario['brs']:
            br = int_routers[br_id]
            brs.append(br)
        log.data("brs", scenario['brs'])

        # if zero route reflectors: setup full mesh
        if len(scenario['rrs']) == 0:
            for a in brs:
                for b in int_routers:
                    if (not b.is_border_router()) or a.assigned_node < b.assigned_node:
                        a.peers.append(b)
                        b.peers.append(a)

        ext_routers = []
        ext_anns = {"XXX": {}}
        i = 0
        for br in brs:
            rr1 = BgpExtRouter(8000 + i, 1000 + i, br)
            rr2 = BgpExtRouter(9000 + i, 1000 + i, br)
            ext_routers.append(rr1)
            ext_routers.append(rr2)

            # worst-case announcements
            ext_anns["XXX"][rr1] = Announcement([0, 0, 0, 0])
            ext_anns["XXX"][rr2] = Announcement([0, 0, 0, 0])
            i += 1

        return BgpConfig(int_routers, ext_routers, ext_anns)

    def _setup_rr_topology(self, int_routers: list, rr_ids: List[int]):
        rrs = []
        for rr_id in rr_ids:
            rr = int_routers[rr_id]
            rrs.append(rr)
        log.data("rrs", rr_ids)
        # connect RRs to all other routers
        for rr in rrs:
            for peer in int_routers:
                if peer not in rrs:
                    rr.rr_clients.append(peer)
                    peer.peers.append(rr)
        # connect RRs with each other
        for a in rrs:
            for b in rrs:
                if a.assigned_node < b.assigned_node:
                    a.peers.append(b)
                    b.peers.append(a)

    def _load_property(self, scenario):
        tmp = scenario['property'].split(',')
        src = int(tmp[0].split(':')[1].strip())
        point = int(tmp[2].split(')')[0].strip())
        prop = WaypointProperty(Flow(src, "XXX"), point)
        log.data("property", prop.get_human_readable(self.name_resolver))
        return prop
