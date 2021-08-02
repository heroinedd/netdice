import json
import os
from shutil import rmtree

from netdice.my_logging import log
import networkx as nx

from netdice.util import get_relative_to_working_directory

prefix = 'E:/study/MyTool/ResultCompare/inputs/netdice/'


def transform_log(input_file: str):

    if not os.path.exists(input_file):
        log.error("could not open input file '%s'", input_file)
        exit(1)

    with open(input_file, 'r') as input:
        output_file = ""
        root = {}

        rrs = []
        brs = []
        waypoint = ""
        time_explore = ""

        for line in input.readlines():
            tmp = json.loads(line)

            if "topology" in tmp:
                output_file = prefix + tmp["topology"]["name"] + ".json"
                root["topology"] = tmp["topology"]
                root["scenarios"] = []

            if "rrs" in tmp:
                rrs = tmp["rrs"]

            if "brs" in tmp:
                brs = tmp["brs"]

            if "property" in tmp:
                waypoint = tmp["property"]

            if "time-explore" in tmp:
                time_explore = tmp["time-explore"]

            if "finished" in tmp:
                finished = tmp["finished"]
                root["scenarios"].append({"rrs": rrs,
                                          "brs": brs,
                                          "property": waypoint,
                                          "time-explore": time_explore,
                                          "finished": finished})

        with open(output_file, 'w', encoding='utf8') as output:
            json.dump(root, output, indent=4, ensure_ascii=False)


def get_k_edge_component(file_name: str):
    G = nx.Graph()
    with open(file_name) as f:
        f.readline()
        line = f.readline()
        while line:
            t = line.strip().split(" ")
            G.add_edge(t[0], t[1])
            line = f.readline()
    components = nx.k_edge_components(G, k=3)
    for component in components:
        if len(component) > 1:
            print(component)


def combine_property_hot_edges(property_path: str, hot_edge_path: str):
    with open(property_path) as f1:
        j = json.load(f1)
        topology = j['topology']
        scenarios = j['scenarios']
        with open(hot_edge_path) as f2:
            for i, scenario in enumerate(scenarios):
                f2.readline()
                hes = []
                for j in range(3):
                    line = f2.readline()
                    line = line.split('{')[1]
                    line = line.split('}')[0]
                    line = line.replace('(', '[')
                    line = line.replace(')', ']')
                    line = '{\"hot_edges\":[' + line + ']}'
                    hes.append(json.loads(line)['hot_edges'])
                scenario['hot_edges'] = hes
        j = {'topology': topology, 'scenarios': scenarios}
        with open(property_path.split('.json')[0] + '_with_he.json', 'w', encoding='utf-8') as f3:
            json.dump(j, f3, indent=4)


if __name__ == "__main__":
    """
    generate "property.json"
    """
    # input_dir = get_relative_to_working_directory("input")
    # cnt = -1
    # for network in os.listdir(input_dir):
    #     cnt += 1
    #     if cnt < 0:
    #         continue
    #     elif cnt >= 80:
    #         break
    #     else:
    #         output_dir = os.path.join(input_dir, network, 'output')
    #         for file in os.listdir(output_dir):
    #             if file.startswith('data'):
    #                 transform_log(os.path.join(output_dir, file))
    #                 break

    """
    delete folder "output"
    """
    # for network in os.listdir(input_dir):
    #     output_dir = os.path.join(input_dir, network, 'output')
    #     if os.path.exists(output_dir):
    #         rmtree(output_dir)

    """
    add hot_edges into "property.json"
    """
    combine_property_hot_edges('./input/VtlWavenet2008/property.json',
                               './input/VtlWavenet2008/output/log2021-07-13-19-21-26.log')
