import json
import os
import time

from netdice.bgp import BgpIntRouter, BgpExtRouter, Announcement, BgpConfig
from netdice.common import Flow
from netdice.experiments.scenarios import BaseScenario
from netdice.explorer import Explorer
from netdice.failures import LinkFailureModel, NodeFailureModel
from netdice.input_parser import NameResolver, InputParser
from netdice.my_logging import log, log_context, time_measure
from netdice.prob import Prob
from netdice.problem import Problem
from netdice.properties import WaypointProperty, ReachableProperty
from netdice.util import project_root_dir


class SynthScenario(BaseScenario):
    def __init__(self, topo_name: str, suffix: str, topology_file: str, config_file: str, precision: float,
                 collect_hot=False, collect_precision=False, only_link_failures=True, timeout_h=1.0):
        """
        :param topo_name: string name of the network topology
        :param suffix: suffix to be used for the scenario name
        :param topology_file: file name of the topology (JSON or whitespaced text format)
        :param config_file: file name of BGP config
                            (JSON format, assigning route reflectors, border routers and waypoint router)
        :param precision: precision
        :param collect_hot: whether to collect statistics about the fraction of hot edges
        :param collect_precision: whether to collect statistics about the precision trace
        :param only_link_failures: whether to consider link failures only
        :param timeout_h: timeout in hours
        """
        super().__init__(topo_name, suffix, timeout_h)
        self.topology_file = topology_file
        self.config_file = config_file
        self.precision = precision
        self.collect_hot = collect_hot
        self.collect_precision = collect_precision
        self.only_link_failures = only_link_failures

        self.name_resolver = None
        self.nof_nodes = -1
        self.links = []
        self.nof_links = -1

        self.rr_ids = []
        self.br_ids = []
        self.pr_id = -1

    def _load_topology(self):
        self.parser = InputParser(self.topology_file)
        if self.topology_file.split(".")[-1] == "json":
            self.parser._load_data()
            nof_nodes, links = self.parser._topology_from_data(self.parser.data["topology"], self.name_resolver)
        else:
            nof_nodes, links = self.parser._topology_from_data({"file": self.topology_file}, self.name_resolver)
        return nof_nodes, links

    def _load_config(self):
        with open(self.config_file) as f:
            config = json.load(f)
            return config['rrs'], config['brs'], config['point']

    def _load_bgp_config(self):
        # create internal routers
        int_routers = []
        for id in range(0, self.nof_nodes):
            int_routers.append(BgpIntRouter(id, id, 500))

        self._setup_random_rr_topology(int_routers)

        # create border routers
        brs = []
        for br_id in self.br_ids:
            br = int_routers[br_id]
            brs.append(br)

        # if zero route reflectors: setup full mesh
        if len(self.rr_ids) == 0:
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

    def _setup_random_rr_topology(self, int_routers: list):
        # create random route reflectors
        rrs = []
        for rr_id in self.rr_ids:
            rr = int_routers[rr_id]
            rrs.append(rr)
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


class WaypointScenario(SynthScenario):
    def run(self):
        self.name_resolver = NameResolver()
        self.nof_nodes, self.links = self._load_topology()
        self.nof_links = len(self.links)
        self.rr_ids, self.br_ids, self.pr_id = self._load_config()

        log.data("topology", {"name": self.topo_name, "nof_nodes": self.nof_nodes, "nof_links": self.nof_links})

        srcs = set([i for i in range(self.nof_nodes)])
        srcs = srcs.difference(self.br_ids)
        srcs.remove(self.pr_id)
        srcs = list(srcs)
        srcs.sort()

        result_path = os.path.abspath(
            os.path.join(
                project_root_dir,
                "netdice/danwexp/output/json/waypoint/" + self.topo_name + ".json"
            )
        )

        result = {"properties": []}
        with time_measure('total-explore-time'):
            start = time.time()
            for i, src in enumerate(srcs):
                log.info("running %s * %d", str(self), i)

                with log_context(i):
                    # create BGP config
                    bgp_config = self._load_bgp_config()

                    # create failure model
                    if self.only_link_failures:
                        failure_model = LinkFailureModel(Prob(0.001))
                    else:
                        failure_model = NodeFailureModel(Prob(0.001), Prob(0.0001))

                    # create property
                    prop = self.get_property(src)

                    # create problem
                    problem = Problem(self.nof_nodes, self.links, [], bgp_config, failure_model, prop)
                    problem.target_precision = self.precision

                    # run exploration
                    with time_measure("time-explore"):
                        explorer = Explorer(problem, stat_hot=self.collect_hot, stat_prec=self.collect_precision)
                        sol = explorer.explore_all(timeout=self.timeout)
                    log.data("finished", {
                        "precision": sol.p_explored.invert().val(),
                        "p_property": sol.p_property.val(),
                        "num_explored": sol.num_explored
                    })
                    result["properties"].append({"src": src,
                                                 "point": self.pr_id,
                                                 "imprecision": sol.p_explored.invert().val(),
                                                 "probability": sol.p_property.val()})
            end = time.time()
            elapsed = end - start
            result["runtime"] = elapsed
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4)

    def get_property(self, src: int):
        # create random waypoint property
        prop = WaypointProperty(Flow(src, "XXX"), self.pr_id)
        log.data("property", prop.get_human_readable(self.name_resolver))
        return prop


class ReachableScenario(SynthScenario):
    def run(self):
        self.name_resolver = NameResolver()
        self.nof_nodes, self.links = self._load_topology()
        self.nof_links = len(self.links)
        self.rr_ids, self.br_ids, self.pr_id = self._load_config()

        log.data("topology", {"name": self.topo_name, "nof_nodes": self.nof_nodes, "nof_links": self.nof_links})

        srcs = set([i for i in range(self.nof_nodes)])
        srcs = srcs.difference(self.br_ids)
        srcs = list(srcs)
        srcs.sort()

        result_path = os.path.abspath(
            os.path.join(
                project_root_dir,
                "netdice/danwexp/output/json/reachable/" + self.topo_name + ".json"
            )
        )

        result = {"properties": []}
        with time_measure('total-explore-time'):
            start = time.time()
            for i, src in enumerate(srcs):
                log.info("running %s * %d", str(self), i)

                with log_context(i):
                    # create BGP config
                    bgp_config = self._load_bgp_config()

                    # create failure model
                    if self.only_link_failures:
                        failure_model = LinkFailureModel(Prob(0.001))
                    else:
                        failure_model = NodeFailureModel(Prob(0.001), Prob(0.0001))

                    # create property
                    prop = self.get_property(src)

                    # create problem
                    problem = Problem(self.nof_nodes, self.links, [], bgp_config, failure_model, prop)
                    problem.target_precision = self.precision

                    # run exploration
                    with time_measure("time-explore"):
                        explorer = Explorer(problem, stat_hot=self.collect_hot, stat_prec=self.collect_precision)
                        sol = explorer.explore_all(timeout=self.timeout)
                    log.data("finished", {
                        "precision": sol.p_explored.invert().val(),
                        "p_property": sol.p_property.val(),
                        "num_explored": sol.num_explored
                    })
                    result["properties"].append({"src": src,
                                                 "imprecision": sol.p_explored.invert().val(),
                                                 "probability": sol.p_property.val()})
            end = time.time()
            elapsed = end - start
            result["runtime"] = elapsed
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4)

    def get_property(self, src: int):
        # create random reachable property
        prop = ReachableProperty(Flow(src, "XXX"))
        log.data("property", prop.get_human_readable(self.name_resolver))
        return prop
