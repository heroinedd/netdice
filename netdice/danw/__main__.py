import os
import time

from danw.scenario import Scenario
from my_logging import log
from netdice.util import get_relative_to_working_directory

input_base = get_relative_to_working_directory("input")


def run_one_net(name: str):
    input_dir = os.path.join(input_base, name)
    output_dir = os.path.join(input_dir, "output")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    current_time = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
    log.initialize('ERROR', data_log_file=os.path.join(output_dir, f'data{current_time}.log'),
                   log_file=os.path.join(output_dir, f'log{current_time}.log'), file_level='INFO')
    scenario = Scenario(name, "default", os.path.join(input_dir, name + '.in'),
                        os.path.join(input_dir, 'property.json'), 1.0E-4, collect_hot=True, collect_precision=False)
    scenario.run()
    log.is_initialized = False


if __name__ == "__main__":
    # i = -1
    # for name in os.listdir(input_base):
    #     i += 1
    #     if i < 62:
    #         continue
    #     elif i >= 63:
    #         break
    #     else:
    #         print(name)
    #         run_one_net(name)
    run_one_net('VtlWavenet2008')
