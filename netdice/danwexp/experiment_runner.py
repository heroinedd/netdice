import math
import os
from multiprocessing.context import Process

import numpy as np

from netdice.my_logging import log, log_context


class ExperimentRunner:
    """
    Helper class for running experiments.
    """

    def __init__(self, output_dir: str, prefix: str):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.scenarios = []     # list[BaseScenario]
        self.prefix = prefix

    def run_all(self, nof_processes: int):
        procs = []
        if len(self.scenarios) == 0:
            return
        if len(self.scenarios) < nof_processes:
            nof_processes = len(self.scenarios)
        width = math.ceil(len(self.scenarios) / float(nof_processes))
        for i in range(0, nof_processes):
            l = i * width
            u = min((i + 1) * width, len(self.scenarios))
            if nof_processes == 1:
                ExperimentRunner._run_scenarios(self.scenarios, self.output_dir)
            else:
                part = self.scenarios[l:u]
                p = Process(target=ExperimentRunner._run_scenarios, args=(part, self.output_dir))
                procs.append(p)
                p.start()

        for p in procs:
            p.join()

    def filter(self, filter: list):
        """
        Removes all scenarios whose full name is not in the provided filter list.
        """
        new_scenarios = []
        for s in self.scenarios:
            if str(s) in filter:
                new_scenarios.append(s)
        self.scenarios = new_scenarios

    @staticmethod
    def _run_scenarios(scenarios: list, output_dir: str):
        """
        :param scenarios: list[BasicScenario]
        """
        np.random.seed()
        for s in scenarios:
            data_file = os.path.join(output_dir, "{}_data.log".format(s.topo_name))
            log_file = os.path.join(output_dir, "{}_log.log".format(s.topo_name))
            log.initialize('ERROR', data_log_file=data_file, log_file=log_file, file_level='INFO')
            with log_context(str(s)):
                try:
                    s.run()
                except Exception:
                    log.error("Exception while running scenario %s", str(s), exc_info=True)
            log.is_initialized = False
