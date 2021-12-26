import argparse
import os

from netdice.danwexp.experiment_runner import ExperimentRunner
from netdice.danwexp.scenarios import WaypointScenario, ReachableScenario
from netdice.util import project_root_dir

if __name__ == "__main__":
    parser = argparse.ArgumentParser("netdice.danwexp")
    parser.add_argument('-zoo', action="store_true", help='run configurations under zoo/')
    parser.add_argument('-mrinfo', action="store_true", help='run configurations under mrinfo/')
    parser.add_argument('-link', action="store_true", help='link failure only if appointed (default node failure model)')
    parser.add_argument('-waypoint', action='store_true', help='check waypoint')
    parser.add_argument('-reachability', action='store_true', help='check reachability')
    parser.add_argument("-p", "--processes", help='number of processes to use', type=int, default=1)
    args = parser.parse_args()

    input_dir = os.path.abspath(os.path.join(project_root_dir, "netdice/danwexp/input"))
    output_dir = os.path.abspath(os.path.join(project_root_dir, "netdice/danwexp/output"))

    if args.link:
        output_dir = os.path.abspath(os.path.join(output_dir, "link"))
    else:
        output_dir = os.path.abspath(os.path.join(output_dir, "node"))

    # run experiments
    runner = ExperimentRunner(output_dir, "")

    def add_scenario(sname, topo, cfg):
        if args.waypoint:
            runner.scenarios.append(WaypointScenario(sname, "default", topo, cfg, 1.0E-4, only_link_failures=args.link))
        if args.reachability:
            runner.scenarios.append(ReachableScenario(sname, "default", topo, cfg, 1.0E-4, only_link_failures=args.link))

    # Topology Zoo / target 10^-4 / +hot
    if args.zoo:
        zoo_dir = os.path.join(input_dir, "zoo")
        for name in os.listdir(zoo_dir):
            base_dir = os.path.join(zoo_dir, name)
            topology_file = os.path.join(base_dir, name + '.in')
            config_file = os.path.join(base_dir, 'config.json')
            add_scenario(name, topology_file, config_file)

    # mrinfo / target 10^-4 / +hot
    if args.mrinfo:
        mrinfo_dir = os.path.join(input_dir, "mrinfo")
        for name in os.listdir(mrinfo_dir):
            base_dir = os.path.join(mrinfo_dir, name)
            topology_file = os.path.join(base_dir, name + '.json')
            config_file = os.path.join(base_dir, 'config.json')
            add_scenario(name, topology_file, config_file)

    runner.run_all(args.processes)
