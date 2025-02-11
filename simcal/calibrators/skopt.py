from itertools import count
from time import time

import skopt.optimizer as skopt
from skopt.space import *

import simcal.calibrators as sc
import simcal.exceptions as exception
import simcal.simulator as Simulator
from simcal.parameters import Exponential, Linear, Ordered, Value, Ordinal
import simcal.coordinators.base as Coordinator

def _eval(simulator: Simulator, params, calibration, stoptime):
    try:
        return calibration, simulator(calibration, stoptime), params
    except exception.Timeout:
        raise
    except Exception as e:
        raise exception.SimulationFail(params, e)


# Base estimators can be
# "GP" for Gradient Process Regressor
# "RF" for Random Forrest Regresor
# "ET" for Extra Trees Regressor or
# "GBRT" for Gradient Boosting Quantile Regressor trees
class ScikitOptimizer(sc.Base):
    def __init__(self, starts, base_estimator="GP", seed=None):
        super().__init__()
        self.seed = seed
        self.base_estimator = base_estimator
        self.starts = starts

    def calibrate(self, simulator: Simulator, early_stopping_loss: float | int | None = None,
                  iterations: int | None = None, timelimit: float | int | None = None,
                  coordinator: Coordinator.Base | None = None) -> tuple[dict[str, Value | float | int], float]:
        from simcal.coordinators import Base as Coordinator

        # self._categorical_params = {}
        parameters = []
        for (key, param) in self._ordered_params.items():
            if isinstance(param, Exponential):
                if param.integer:
                    parameters.append(Integer(int(param.from_normalized(param.range_start)),
                                              int(param.from_normalized(param.range_end)), 'log-uniform', 2, name=key))
                else:
                    parameters.append(Real(float(param.from_normalized(param.range_start)),
                                           float(param.from_normalized(param.range_end)), 'log-uniform', 2, name=key))

            elif isinstance(param, Linear):
                if param.integer:
                    parameters.append(Integer(param.start, param.end, 'uniform', 2, name=key))
                else:
                    parameters.append(Real(param.start, param.end, 'uniform', 2, name=key))
            elif isinstance(param, Ordinal):
                parameters.append(Integer(0, len(param.options)-1, 'uniform', 2, name=key))
            elif isinstance(param, Ordered):
                if param.integer:
                    parameters.append(Integer(param.range_start, param.range_end, 'uniform', 2, name=key))
                else:
                    parameters.append(Real(param.range_start, param.range_end, 'uniform', 2, name=key))
        for (key, param) in self._categorical_params.items():
            parameters.append(Categorical(param.categories, name=key))

        opt = skopt.Optimizer(
            dimensions=parameters,
            base_estimator=self.base_estimator,
            n_initial_points=self.starts,
            random_state=self.seed
        )

        if coordinator is None:
            coordinator = Coordinator()
        if timelimit is None:
            stoptime = float('inf')
        else:
            stoptime = time() + timelimit
        if iterations is None:
            itr = count(start=0, step=1)
        else:
            itr = range(0, iterations)
        try:
            for i in itr:
                if time() > stoptime:
                    break

                calibration = {}
                # for key in self._ordered_params:
                #     param = self._ordered_params[key]
                #     calibration[key] = param.from_normalized(random.uniform(param.range_start, param.range_end))
                #
                # for key in self._categorical_params:
                #     calibration[key] = random.choice(self._categorical_params[key].get_categories())
                params = opt.ask()
                calibration = self.to_regular_params(parameters, params)
                coordinator.allocate(_eval, (simulator, params, calibration, stoptime))
                results = coordinator.collect()
                for current, loss, tell in results:
                    if loss is None:
                        continue
                    # print(best_loss,loss,current)
                    opt.tell(tell, loss)
            results = coordinator.await_all()
            for current, loss, tell in results:
                if loss is None:
                    continue
                opt.tell(tell, loss)
        except exception.Timeout:
            # print("Random had to catch a timeout")
            results = opt.get_result()
            results.x = self.to_regular_params(parameters, results.x)
            return results.x, results.fun
        except exception.EarlyTermination as e:
            ebest, eloss = e.result
            if eloss is None:
                results = opt.get_result()
                results.x = self.to_regular_params(parameters, results.x)
                if results.fun < eloss:
                    e.result = (results.x, results.fun)
            raise e
        except BaseException as e:
            results = opt.get_result()
            results.x = self.to_regular_params(parameters, results.x)
            raise exception.EarlyTermination((results.x, results.fun), e)

        results = opt.get_result()
        results.x = self.to_regular_params(parameters, results.x)
        return results.x, results.fun

    def to_regular_params(self, parameters, params):
        calibration = {}
        for param, value in zip(parameters, params):
            if param.name in self._ordered_params:
                if isinstance(self._ordered_params[param.name], Ordinal):
                    calibration[param.name] = self._ordered_params[param.name].from_index(value)
                else:
                    calibration[param.name] = self._ordered_params[param.name].apply_format(value)
            else:
                calibration[param.name] = self._categorical_params[param.name].apply_format(value)

        return calibration
