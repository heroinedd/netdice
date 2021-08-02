import json
import os

import matplotlib.pyplot as plt
import networkx as nx
from networkx import spring_layout

zoo_dir = "../../eval_sigcomm2020/inputs/zoo"


def print_info():
    nodes = []
    for topo in os.listdir(zoo_dir):
        f = os.path.join(zoo_dir, topo)
        with open(f, 'r', encoding='utf8') as file:
            lines = file.readlines()
            lines = [line.strip('\n') for line in lines]
            n_nodes = int(lines[0])
            n_links = len(set(lines[1:]))
            nodes.append({"topology": topo, "n_lines": len(lines) - 1, "n_nodes": n_nodes, "n_links": n_links})
    with open('output/info.json', 'w', encoding='utf-8') as f:
        json.dump(nodes, f, indent=4)


def load_graph(name: str):
    G = nx.Graph()
    f = os.path.join(zoo_dir, name)
    with open(f, 'r', encoding='utf8') as file:
        nof_nodes = int(file.readline())
        for i in range(nof_nodes):
            r = str(i)
            G.add_node(r, name=r)
        line = file.readline()
        while line:
            t = line.strip().split(" ")
            G.add_edge(t[0], t[1])
            line = file.readline()
    return G


def prune_graph(G: nx.Graph) -> nx.Graph:
    flag = False
    while not flag:
        to_remove = []
        for node in G.nodes:
            if G.degree[node] == 1:
                to_remove.append(node)
        flag = len(to_remove) == 0
        for node in to_remove:
            G.remove_node(node)
    return G


color_br = '#A0CBE2'
color_rr = '#FF0000'
color_ir = '#FFFF00'
node_size = 1000
font_size = 18


def draw_topology(name: str, br, rr):
    G = load_graph(name)
    draw_graph(G, br, rr, name.split('.')[0] + '.png')
    print(f'nodes: {len(G.nodes)}, links: {len(G.edges)}')

    G = prune_graph(G)
    draw_graph(G, br, rr, name.split('.')[0] + '_pruned.png')
    print(f'nodes: {len(G.nodes)}, links: {len(G.edges)}')


def draw_graph(G: nx.Graph, br, rr, name: str):
    def get_color(node):
        if int(node) in br:
            return color_br
        elif int(node) in rr:
            return color_rr
        else:
            return color_ir

    plt.figure(figsize=(15, 15))
    pos = spring_layout(G)

    node_colors = [get_color(node) for node in G.nodes()]
    node_sizes = [node_size] * len(G.nodes())
    node_labels = nx.get_node_attributes(G, 'name')

    nx.draw(G, pos=pos, node_color=node_colors, node_size=node_sizes)
    nx.draw_networkx_labels(G, pos=pos, labels=node_labels, font_size=font_size)

    # plt.savefig('output/' + name.split('.')[0] + '.png')
    plt.savefig('output/' + name)
    plt.show()


def component(name: str):
    G = load_graph(name)
    components = nx.k_edge_components(G, 2)
    for c in components:
        print(c)


if __name__ == "__main__":
    draw_topology('Cogentco.in', br=[], rr=[])
    # from_base = 'E:/study/MyTool/mytool/networks/netdice/zoo'
    # to_base = 'E:/study/MyTool/netdice/netdice/danw/input'
    # for net in os.listdir(from_base):
    #     from_dir = os.path.join(from_base, net)
    #     to_dir = os.path.join(to_base, net)
    #
    #     if not os.path.exists(to_dir):
    #         os.makedirs(to_dir)
    #
    #     copy(os.path.join(from_dir, net + '.in'), os.path.join(to_dir, net + '.in'))
    #     copy(os.path.join(from_dir, 'property.json'), os.path.join(to_dir, 'property.json'))
