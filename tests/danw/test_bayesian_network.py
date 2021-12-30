import itertools
import json
import os
import time

import networkx as nx

from netdice.common import Link
from netdice.failures import NodeFailureModel
from netdice.prob import Prob

from unittest import TestCase


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


class TestBayesianNetwork(TestCase):

    def test_bayesian_network(self):
        input_dir = '/data/danw-data/exp/netdice/output/bn/reachability'
        # input_dir = 'tests/danw/inputs'
        bayes_diffs = {}
        bayes_times = {}
        for file in os.listdir(input_dir):
            bayes_diffs[file.split('_')[0]] = {}

        for topo_name in bayes_diffs:
            topo = os.path.abspath(os.path.join(input_dir, topo_name + '_topo.json'))
            bn = os.path.abspath(os.path.join(input_dir, topo_name + '_bn.json'))

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
                    return {'up': up, 'down': down}

                bayes_time_python = 0
                bayes_time_java = 0
                bayes_diff = []
                with open(bn, 'r', encoding='utf-8') as bn_f:
                    bn_j = json.load(bn_f)
                    states = bn_j['bn']
                    for state in states:
                        start = time.time_ns()
                        prob = node_failure_model.get_state_prob(state['state'])
                        end = time.time_ns()
                        if abs(prob.val() - state['probability']) > 1e-8:
                            one_diff = parse_state(state['state'])
                            one_diff['java'] = state['probability']
                            one_diff['python'] = prob
                            bayes_diff.append(one_diff)
                        bayes_time_python += (end - start) / 1e9
                        bayes_time_java += state['time'] / 1e9
                bayes_diffs[topo_name] = bayes_diff
                bayes_times[topo_name] = [bayes_time_python, bayes_time_java]

        with open('tests/danw/outputs/bayes_diffs.json', 'w', encoding='utf-8') as f:
            json.dump(bayes_diffs, f, indent=4)
        with open('tests/danw/outputs/bayes_times.csv', 'w', encoding='utf-8') as f:
            for k, v in bayes_times.items():
                f.write(f'{k}\t{v[0]}\t{v[1]}\n')
