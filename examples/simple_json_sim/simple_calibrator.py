#!/usr/bin/env python3
import json
import os
from pathlib import Path

from sklearn.metrics import mean_squared_error as sklearn_mean_squared_error

import simcal as sc
from groundtruth import ground_truth

simple_json_sim = Path(os.path.dirname(os.path.realpath(__file__)))


class ExampleSimulator(sc.Simulator):
    def __init__(self, ground_truth, loss, time=0):
        super().__init__()
        self.time = time
        self.ground_truth = ground_truth
        self.loss_function = loss

    def single_simulation(self, env, x, json_file):
        cmdargs = [simple_json_sim / "simple_simulator.py"] + [json_file.name] + list(x) + [self.time]
        std_out, std_err, exit_code = env.bash("python3", cmdargs)
        if std_err:
            print(std_out, std_err, exit_code)

        with env.open("results.txt", "r") as file:
            results = file.read()

        return float(results)

    def run(self, env, args):
        res = []
        # Run simulator for all known ground truth points
        print(args)
        env.tmp_dir(directory=".")
        json_file = env.tmp_file(directory=env.get_cwd(), encoding='utf8')
        json.dump(args, json_file, default=lambda o: str(o))
        json_file.flush()
        for x in self.ground_truth[0]:
            res.append(self.single_simulation(env, x, json_file))
        return self.loss_function(res, self.ground_truth[1])


# make some fake evaluation scenarios for the example
known_points = []
for x in (1.39904, 254441, 5.05656):
    for y in (1.1558, 3.384, 40395, 7.36):
        for z in (0.637, 2.281, 3.876, 5.459, 7.038):
            for w in (0.448, 1.527, 2.587, 3.641, 4.693, 5.743):
                known_points.append((x, y, z, w))

# get ground truth data the fake scenarios
data = []
for x in known_points:
    data.append(ground_truth(*x))
ground_truth_data = [known_points, data]

loss = sklearn_mean_squared_error

simulator = ExampleSimulator(ground_truth_data, loss)

# prepare the calibrator and setup the arguments to calibrate with their ranges
# calibrator = sc.calibrators.Grid()
# calibrator = sc.calibrators.Random()
calibrator = sc.calibrators.ScikitOptimizer(1000)
# calibrator = sc.calibrators.GeneticAlgorithm(100,10,.50,.01)

calibrator.add_param("a", sc.parameter.Linear(0, 20).format("%.2f"))
calibrator.add_param("b", sc.parameter.Linear(0, 8).format("%.2f"))
calibrator.add_param("c", sc.parameter.Linear(0, 10).format("%.2f"))
calibrator.add_param("d", sc.parameter.Linear(0, 6).format("%.2f"))

coordinator = sc.coordinators.ThreadPool(pool_size=4)  # Making a coordinator is optional, and only needed if you
# wish to run multiple simulations at once, possibly using multiple cpu cores or multiple compute nodes

calibration, loss = calibrator.calibrate(simulator, timelimit=79200, coordinator=coordinator)
print("final calibration")
print(calibration)
print("Expected")
print([10, 4, 5, 3])
print(loss)
