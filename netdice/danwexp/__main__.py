import argparse
import json
import os

from netdice.danwexp.scenarios import SynthScenario
from netdice.experiments.analyzer import Analyzer
from netdice.danwexp.experiment_runner import ExperimentRunner
from netdice.my_logging import log
from netdice.util import get_relative_to_working_directory

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

    input_dir = get_relative_to_working_directory('input')
    output_dir = get_relative_to_working_directory('output')

    if args.run:
        # run experiments
        runner = ExperimentRunner(output_dir, "")

        # input files
        zoo_dir = os.path.join(input_dir, "zoo")

        # Topology Zoo / target 10^-4 / +hot
        for name in os.listdir(zoo_dir):
            if name == 'UsCarrier':
                base_dir = os.path.join(zoo_dir, name)
                topology_file = os.path.join(base_dir, name + '.in')
                config_file = os.path.join(base_dir, 'config.json')
                runner.scenarios.append(SynthScenario(name, "default", topology_file, config_file, 1.0E-3))

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
