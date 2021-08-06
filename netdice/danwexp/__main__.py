import argparse
import json
import os

from netdice.danwexp.experiment_runner import ExperimentRunner
from netdice.danwexp.scenarios import WaypointScenario, ReachableScenario
from netdice.experiments.analyzer import Analyzer
from netdice.my_logging import log
from netdice.util import project_root_dir

if __name__ == "__main__":
    parser = argparse.ArgumentParser("netdice.danwexp")
    parser.add_argument('--run', action="store_true", help='run experiments')
    parser.add_argument('--analyze', action="store_true", help='analyze results and generate plots (after --run)')
    parser.add_argument("-p", "--processes", help='number of processes to use', type=int, default=1)
    args = parser.parse_args()

    if not args.run and not args.analyze:
        parser.print_usage()
        print("must provide either --run or --analyze flag")
        exit(1)

    input_dir = os.path.abspath(os.path.join(project_root_dir, "netdice/danwexp/input"))
    output_dir = os.path.abspath(os.path.join(project_root_dir, "netdice/danwexp/output"))

    if args.run:
        # run experiments
        runner = ExperimentRunner(output_dir, "")

        # input files
        zoo_dir = os.path.join(input_dir, "zoo")

        # Topology Zoo / target 10^-4 / +hot
        for name in os.listdir(zoo_dir):
            base_dir = os.path.join(zoo_dir, name)
            topology_file = os.path.join(base_dir, name + '.in')
            config_file = os.path.join(base_dir, 'config.json')
            runner.scenarios.append(WaypointScenario(name, "default", topology_file, config_file, 1.0E-4))
            runner.scenarios.append(ReachableScenario(name, "default", topology_file, config_file, 1.0E-4))

        runner.run_all(args.processes)

    if args.analyze:
        log.initialize('INFO')
        log.info("Generating plots for data directory '%s'", input_dir)

        # collect experiment data
        log.info("Collecting data...")
        data = []
        for fname in os.listdir(input_dir):
            if fname.startswith("experiment_data") and fname.endswith(".log"):
                fpath = os.path.join(input_dir, fname)
                with open(fpath, 'r') as f:
                    for line in f:
                        data.append(json.loads(line))

        # analyze data, create plots
        Analyzer(data, output_dir).analyze()
