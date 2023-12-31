import numpy as np
import matplotlib.pyplot as plt
import pickle

from bingo.evolutionary_algorithms.generalized_crowding import \
                                                GeneralizedCrowdingEA
from bingo.selection.deterministic_crowding import DeterministicCrowding
from bingo.evaluation.evaluation import Evaluation
from bingo.evolutionary_optimizers.island import Island
from bingo.local_optimizers.continuous_local_opt \
    import ContinuousLocalOptimization
from bingo.stats.pareto_front import ParetoFront

from bingo.symbolic_regression import ComponentGenerator, \
                                      AGraphGenerator, \
                                      AGraphCrossover, \
                                      AGraphMutation, \
                                      ExplicitRegression, \
                                      ExplicitTrainingData

from bingo.symbolic_regression.agraph.agraph import AGraph

class CustomCLO(ContinuousLocalOptimization):

    def __call__(self, individual):
        if individual.needs_local_optimization():
            self._optimize_params(individual)
        f, df_dx = individual.evaluate_equation_with_x_gradient_at(
                                                self.training_data.x)
        monotonic_in_X = np.all((f[1:,0] - f[0:-1,0])<=0)
        negative_f = np.all(f<=0)
        if monotonic_in_X and negative_f:
            return self._evaluate_fitness(individual)
        else:
            return np.nan

POP_SIZE = 100
STACK_SIZE = 32
MAX_GEN = 5000
FIT_THRESH = -np.inf
CHECK_FREQ = 500
MIN_GEN = 500

def get_training_data(N=200, ND=15):
    
    X, y = [], []
    X = np.load("../data_X.npy")
    y = np.load("../data_y.npy")
    idxs = np.random.choice(np.arange(X.shape[0]), N*ND)
    training_data = ExplicitTrainingData(x=X[idxs,:], y=y[idxs,:].reshape((-1,1)))
    print(X[idxs,:].shape)
    print(y[idxs,:].shape)

    return training_data

def run_bingo():

    training_data = get_training_data()

    component_generator = ComponentGenerator(training_data.x.shape[1])
    component_generator.add_operator("+")
    component_generator.add_operator("-")
    component_generator.add_operator("*")

    crossover = AGraphCrossover()
    mutation = AGraphMutation(component_generator)

    agraph_generator = AGraphGenerator(STACK_SIZE, component_generator,
                                       use_simplification=True
                                       )

    fitness = ExplicitRegression(training_data=training_data)
    local_opt_fitness = CustomCLO(fitness, algorithm='lm')
    pareto_front = ParetoFront(secondary_key = lambda ag: ag.get_complexity(), 
                            similarity_function=agraph_similarity)

    evaluator = Evaluation(local_opt_fitness, multiprocess=10)

    selection_phase = DeterministicCrowding()
    ea = GeneralizedCrowdingEA(evaluator, crossover,
                      mutation, 0.4, 0.4, selection_phase)

    island = Island(ea, agraph_generator, POP_SIZE, hall_of_fame=pareto_front)
    opt_result = island.evolve_until_convergence(max_generations=MAX_GEN,
                                                  fitness_threshold=FIT_THRESH,
                                        convergence_check_frequency=CHECK_FREQ,
                                              checkpoint_base_name='gpsr_out/checkpoint')

def agraph_similarity(ag_1, ag_2):
    return ag_1.fitness == ag_2.fitness and \
                            ag_1.get_complexity() == ag_2.get_complexity()

if __name__ == '__main__':

    run_bingo()

