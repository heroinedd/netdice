from networkx import NetworkXError

from netdice.common import Flow, FwGraph
from netdice.igp import IgpProvider
from netdice.my_logging import log
from netdice.problem import Problem, Solution


class Explorer:
    """
    Implementation of one-by-one failure exploration.
    """

    def __init__(self, p: Problem, full_trace=False, stat_hot=False, stat_prec=False):
        """
        :param p: problem for which to perform inference on
        :param full_trace: whether to collect the full trace of explored states
        :param stat_hot: whether to collect statistics about hot edges
        :param stat_prec: whether to collect the precision trace
        """
        self.problem = p
        self.solution = None
        self._full_trace = full_trace
        self._stat_hot = stat_hot
        self._stat_prec = stat_prec

        self._igp_provider = IgpProvider(p)
        self._trace = []

        self._prev_state = None
        self._queue = None
        self._hot_edges = None

    def explore_all(self):
        """
        Perform failure exploration.

        :return: Solution object
        """
        self.solution = Solution()

        self._prev_state = [-1] * self.problem.nof_links
        self._queue = [[1] * self.problem.nof_links]
        self._hot_edges = []

        for i in range(3):
            tmp = []
            hes = set()
            for state in self._queue:
                cur_hot_edges = self._explore(state)
                for he in cur_hot_edges:
                    nxt_state = state.copy()
                    nxt_state[self.problem.link_id_for_edge[he]] = 0
                    tmp.append(nxt_state)
                hes = hes.union(cur_hot_edges)
            self._queue = tmp
            self._hot_edges.append(hes)

        for k, hes in enumerate(self._hot_edges):
            log.info(f'k: {k}, hot_edges: {hes}')

        return self.solution

    def _explore(self, state: list):
        """
        Explore a given state.
        """
        log.debug("exploring: {}".format(state))

        self._update_graph(state)

        # update shortest paths, partitions, etc.
        self._igp_provider.recompute()

        hot_edges = set()
        fw_graphs = {}
        for flow in self.problem.property.flows:
            self._setup_partition_run_bgp(flow)
            fwg, decision_points = self._construct_fw_graph_decision_points(flow)
            fw_graphs[flow] = fwg
            log.debug("computed forwarding graph: %s", fwg)
            self._add_hot_edges_bgp(flow, fwg, decision_points, hot_edges)

        return hot_edges

    def _update_graph(self, state: list):
        for i in range(0, len(state)):
            if state[i] != 0 and self._prev_state[i] == 0:
                self.problem.add_link_to_G(i)
            elif state[i] == 0 and self._prev_state[i] != 0:
                try:
                    self.problem.remove_link_from_G(i)
                except NetworkXError:
                    pass
            self._prev_state[i] = state[i]

    def _restore_graph(self):
        for i in range(0, len(self._prev_state)):
            if self._prev_state[i] == 0:
                self.problem.add_link_to_G(i)

    def _construct_fw_graph_decision_points(self, flow: Flow) -> tuple:
        """
        :return:  (FwGraph, list[int]). The first entry is the forwarding graph,
                  the second entry are the decision points
        """
        fwg = FwGraph(self.problem.nof_nodes, flow.src, flow.dst)
        decision_points = []
        visited = [False]*self.problem.nof_nodes
        # putting None as next hop makes sure that the source of the flow becomes a decision point
        self._visit_construct_fw_graph(fwg, decision_points, visited, flow.src, None)
        return fwg, decision_points

    def _visit_construct_fw_graph(self, fwg: FwGraph, decision_points: list, visited: list, cur: int, prev_next_hop):
        if visited[cur]:
            return
        visited[cur] = True

        sr_next = self._igp_provider.get_static_route_at(cur, fwg.dst)
        if sr_next is None:
            bgp_next_hop = self._igp_provider.get_bgp_next_hop(cur, fwg.dst)
            '''
            if bgp_next_hop != prev_next_hop:
                decision_points.append(cur)
            if bgp_next_hop is not None:
                if bgp_next_hop.is_external():
                    # traffic exits the network here
                    fwg.add_fw_rule(cur, -1)
                else:
                    next_routers = self._igp_provider.get_next_routers_shortest_paths(cur, bgp_next_hop.assigned_node)
                    for next in next_routers:
                        fwg.add_fw_rule(cur, next)
                        self._visit_construct_fw_graph(fwg, decision_points, visited, next, bgp_next_hop)

            Supporting BGP multi-path
            By: dan
            '''
            for one_next_hop in bgp_next_hop:
                if one_next_hop != prev_next_hop:
                    decision_points.append(cur)
                if one_next_hop is not None:
                    if one_next_hop.is_external():
                        # traffic exits the network here
                        fwg.add_fw_rule(cur, -1)
                    else:
                        next_routers = self._igp_provider.get_next_routers_shortest_paths(cur, one_next_hop.assigned_node)
                        for next in next_routers:
                            fwg.add_fw_rule(cur, next)
                            self._visit_construct_fw_graph(fwg, decision_points, visited, next, one_next_hop)
        else:
            if self.problem.G.has_edge(cur, sr_next):
                fwg.add_fw_rule(cur, sr_next)
                # putting None as next hop makes sure that the target of the static route becomes a decision point
                self._visit_construct_fw_graph(fwg, decision_points, visited, sr_next, None)

    def _setup_partition_run_bgp(self, flow: Flow):
        self.problem.bgp.init_partition(flow, self._igp_provider)

        # run BGP to determine the selected next hops
        self.problem.bgp.run()
        self._igp_provider.update_bgp_next_hops(flow.dst, self.problem.bgp.get_next_hops_for_internal())
        log.debug("computed next hops: %s", self._igp_provider._bgp_next_hop_data)

    def _add_hot_edges_bgp(self, flow: Flow, fwg: FwGraph, decision_points: list, hot_edges: set):
        # mark edges between any RR and BR as hot
        for rr in self.problem.bgp.rr_in_partition:
            for br in self.problem.bgp.br_top3_in_partition:
                Explorer.add_edges_of_path(self._igp_provider.get_a_shortest_path(rr.assigned_node, br.assigned_node), hot_edges)

        # mark shortest paths from decision points to selected next hops as hot
        for r in decision_points:
            bgp_router = self.problem.bgp_config.get_bgp_router_for_node(r)
            bgp_next_hop = bgp_router.get_selected_next_hop()
            '''
            if not bgp_next_hop.is_external():
                Explorer.add_edges_of_path(self._igp_provider.get_a_shortest_path(r, bgp_next_hop.assigned_node), hot_edges)

            Supporting BGP multi-path
            By: dan
            '''
            for one_next_hop in bgp_next_hop:
                if not one_next_hop.is_external():
                    Explorer.add_edges_of_path(self._igp_provider.get_a_shortest_path(r, one_next_hop.assigned_node),
                                               hot_edges)

        # mark edges on forwarding graph as hot
        for e in fwg.traversed_edges:
            Explorer.add_normalized(e, hot_edges)

        if len(self.problem.bgp.rr_in_partition) == 0:
            # ensure connectivity by adding all shortest paths from source to border routers
            for br in self.problem.bgp.br_top3_in_partition:
                Explorer.add_edges_of_path(self._igp_provider.get_a_shortest_path(flow.src, br.assigned_node), hot_edges)

    @staticmethod
    def add_edges_of_path(path: list, edges: set):
        u = None
        for v in path:
            if u is not None:
                Explorer.add_normalized((u, v), edges)
            u = v

    @staticmethod
    def add_normalized(e: tuple, add_to: set):
        if e[0] < e[1]:  # normalize edge representation
            add_to.add((e[0], e[1]))
        else:
            add_to.add((e[1], e[0]))
