import itertools
import json
import os
import time

import networkx as nx

from common import Link
from failures import NodeFailureModel
from prob import Prob


def sort_links(links):
    sorted = {}
    edges = {}
    graph = nx.Graph()
    for link in links:
        u = link.u
        v = link.v
        sorted[link] = 0
        if u < v:
            edges[(u, v)] = link
        else:
            edges[(v, u)] = link
        graph.add_node(u)
        graph.add_node(v)
        graph.add_edge(u, v)

    for mf in [1, 2, 3]:
        components = nx.k_edge_components(graph, k=(mf + 1))
        for component in components:
            if len(component) > 1:
                for u, v in itertools.combinations(component, 2):
                    if (u, v) in edges:
                        sorted[edges[u, v]] = mf
                    elif (v, u) in edges:
                        sorted[edges[v, u]] = mf

    sorted = list(sorted.items())
    sorted.sort(key=lambda x: -x[1])
    sorted = [x[0] for x in sorted]
    for link in sorted:
        print(link)
    return sorted


if __name__ == "__main__":
    topo = os.path.abspath('E:/ANTS/mytool/output/bn/reachability/AsnetAm_topo.json')
    bn = os.path.abspath('E:/ANTS/mytool/output/bn/reachability/AsnetAm_bn.json')
    with open(topo, 'r', encoding='utf-8') as topo_f:
        topo_j = json.load(topo_f)

        nof_nodes = topo_j['nof_nodes']
        links = []
        for link in topo_j['links']:
            links.append(Link(int(link[0]), int(link[1]), 1, 1))

        node_failure_model = NodeFailureModel(Prob(0.001), Prob(0.0001))
        node_failure_model.initialize_for_topology(nof_nodes, links)

        def parse_state(bv: []):
            up = []
            down = []
            for i, b in enumerate(bv):
                if b == 0:
                    down.append((links[i].u, links[i].v))
                elif b == 1:
                    up.append((links[i].u, links[i].v))
            print(f'up: {up}')
            print(f'down: {down}')

        with open(bn, 'r', encoding='utf-8') as bn_f:
            bn_j = json.load(bn_f)
            t1, t2 = 0, 0
            states = bn_j['bn']
            for state in states:
                start = time.time_ns()
                prob = node_failure_model.get_state_prob(state['state'])
                end = time.time_ns()
                if abs(prob.val() - state['probability']) > 1e-8:
                    parse_state(state['state'])
                    print(f"{prob}\t{state['probability']}")
                # if (end - start) < state['time']:
                #     parse_state(state['state'])
                #     print(f"{end - start}\t{state['time']}")
                t1 += (end - start) / 1e9
                t2 += state['time'] / 1e9
            print(f'{t1}\t{t2}')
