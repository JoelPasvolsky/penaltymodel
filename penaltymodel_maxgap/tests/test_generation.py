import unittest

from collections import defaultdict
import itertools

import networkx as nx
import dwave_networkx as dnx
import penaltymodel.core as pm
import dimod

import penaltymodel.maxgap as maxgap

from pysmt.environment import get_env, reset_env


class TestGeneration(unittest.TestCase):
    def setUp(self):
        self.env = reset_env()

    def test_impossible_model(self):
        graph = nx.path_graph(3)
        configurations = {(-1, -1, -1): 0,
                          (-1, +1, -1): 0,
                          (+1, -1, -1): 0,
                          (+1, +1, +1): 0}
        decision_variables = (0, 1, 2)
        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        min_classical_gap = 2

        with self.assertRaises(pm.ImpossiblePenaltyModel):
            maxgap.generate_ising(graph, configurations, decision_variables,
                                  linear_energy_ranges,
                                  quadratic_energy_ranges,
                                  min_classical_gap,
                                  None)

    def check_linear_energy_ranges(self, linear, linear_energy_ranges):
        for v, bias in linear.items():
            min_, max_ = linear_energy_ranges[v]
            self.assertGreaterEqual(bias, min_)
            self.assertLessEqual(bias, max_)

    def check_quadratic_energy_ranges(self, quadratic, quadratic_energy_ranges):
        for edge, bias in quadratic.items():
            min_, max_ = quadratic_energy_ranges[edge]
            self.assertGreaterEqual(bias, min_)
            self.assertLessEqual(bias, max_)

    def check_generated_ising_model(self, feasible_configurations, decision_variables,
                                    linear, quadratic, ground_energy, infeasible_gap):
        """Check that the given Ising model has the correct energy levels"""
        if not feasible_configurations:
            return

        response = dimod.ExactSolver().sample_ising(linear, quadratic)

        # samples are returned in order of energy
        sample, ground = next(iter(response.data(['sample', 'energy'])))
        gap = float('inf')

        self.assertIn(tuple(sample[v] for v in decision_variables), feasible_configurations)

        seen_configs = set()

        for sample, energy in response.data(['sample', 'energy']):
            config = tuple(sample[v] for v in decision_variables)

            # we want the minimum energy for each config of the decisison variables,
            # so once we've seen it once we can skip
            if config in seen_configs:
                continue

            if config in feasible_configurations:
                self.assertAlmostEqual(energy, ground)
                seen_configs.add(config)
            else:
                gap = min(gap, energy - ground)

        self.assertAlmostEqual(ground_energy, ground)
        self.assertAlmostEqual(gap, infeasible_gap)

    def test_trivial(self):
        # this should test things like empty graphs and empty configs
        pass

    def test_basic(self):
        """A typical use case, an AND gate on a chimera tile."""
        graph = dnx.chimera_graph(1, 1, 4)
        configurations = {(-1, -1, -1): 0,
                          (-1, +1, -1): 0,
                          (+1, -1, -1): 0,
                          (+1, +1, +1): 0}
        decision_variables = (0, 1, 2)
        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        min_classical_gap = 2

        h, J, offset, gap = maxgap.generate_ising(graph, configurations, decision_variables,
                                                  linear_energy_ranges,
                                                  quadratic_energy_ranges,
                                                  min_classical_gap,
                                                  None)
        self.check_generated_ising_model(configurations, decision_variables, h, J, offset, gap)
        self.check_linear_energy_ranges(h, linear_energy_ranges)
        self.check_quadratic_energy_ranges(J, quadratic_energy_ranges)

    def test_restricted_energy_ranges(self):
        """Create asymmetric energy ranges and test against that."""
        graph = dnx.chimera_graph(1, 1, 3)
        configurations = {(-1, -1, -1): 0,
                          (-1, +1, -1): 0,
                          (+1, -1, -1): 0,
                          (+1, +1, +1): 0}
        decision_variables = (0, 1, 2)
        linear_energy_ranges = {v: (-1., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., .5) for u, v in graph.edges}
        min_classical_gap = 2

        h, J, offset, gap = maxgap.generate_ising(graph, configurations, decision_variables,
                                                  linear_energy_ranges,
                                                  quadratic_energy_ranges,
                                                  min_classical_gap,
                                                  None)
        self.check_generated_ising_model(configurations, decision_variables, h, J, offset, gap)
        self.check_linear_energy_ranges(h, linear_energy_ranges)
        self.check_quadratic_energy_ranges(J, quadratic_energy_ranges)

    def test_disjoint(self):
        graph = dnx.chimera_graph(1, 1, 3)
        graph.add_edge(8, 9)

        configurations = {(-1, -1, -1): 0,
                          (+1, +1, -1): 0}
        decision_variables = (0, 1, 8)

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        min_classical_gap = 2

        h, J, offset, gap = maxgap.generate_ising(graph, configurations, decision_variables,
                                                  linear_energy_ranges,
                                                  quadratic_energy_ranges,
                                                  min_classical_gap,
                                                  None)
        self.check_generated_ising_model(configurations, decision_variables, h, J, offset, gap)
        self.check_linear_energy_ranges(h, linear_energy_ranges)
        self.check_quadratic_energy_ranges(J, quadratic_energy_ranges)

        graph = dnx.chimera_graph(1, 1, 3)
        graph.add_edge(8, 9)

        configurations = {(-1, -1, +1, -1): 0,
                          (+1, +1, -1, -1): 0}
        decision_variables = (0, 1, 3, 8)

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        min_classical_gap = 2

        h, J, offset, gap = maxgap.generate_ising(graph, configurations, decision_variables,
                                                  linear_energy_ranges,
                                                  quadratic_energy_ranges,
                                                  min_classical_gap,
                                                  None)
        self.check_generated_ising_model(configurations, decision_variables, h, J, offset, gap)
        self.check_linear_energy_ranges(h, linear_energy_ranges)
        self.check_quadratic_energy_ranges(J, quadratic_energy_ranges)

    def test_basic_no_aux(self):
        graph = nx.complete_graph(4)

        configurations = {(-1, -1, -1, -1): 0, (1, 1, 1, 1): 0}
        decision_variables = list(graph)

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        min_classical_gap = 2

        h, J, offset, gap = maxgap.generate_ising(graph, configurations, decision_variables,
                                                  linear_energy_ranges,
                                                  quadratic_energy_ranges,
                                                  min_classical_gap,
                                                  None)
        self.check_generated_ising_model(configurations, decision_variables, h, J, offset, gap)
        self.check_linear_energy_ranges(h, linear_energy_ranges)
        self.check_quadratic_energy_ranges(J, quadratic_energy_ranges)

    def test_one_aux(self):
        graph = nx.complete_graph(3)

        configurations = {(-1, -1): 0, (1, 1): 0}

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        decision_variables = [0, 1]
        min_classical_gap = 2

        h, J, offset, gap = maxgap.generate_ising(graph, configurations, decision_variables,
                                                  linear_energy_ranges,
                                                  quadratic_energy_ranges,
                                                  min_classical_gap,
                                                  None)
        self.check_generated_ising_model(configurations, decision_variables, h, J, offset, gap)
        self.check_linear_energy_ranges(h, linear_energy_ranges)
        self.check_quadratic_energy_ranges(J, quadratic_energy_ranges)

    # def test_specify_msat(self):
    #     """Test a simple model specifying yices as the smt solver. Combined
    #     with the other test_specify_... tests, serves as a smoke test for
    #     the smt_solver_name parameter.
    #     """
    #     linear_energy_ranges = defaultdict(lambda: (-2., 2.))
    #     quadratic_energy_ranges = defaultdict(lambda: (-1., 1.))

    #     graph = nx.complete_graph(3)
    #     configurations = {(-1, -1): 0, (1, 1): 0}
    #     decision_variables = [0, 1]

    #     h, J, offset, gap = maxgap.generate_ising(graph, configurations, decision_variables,
    #                                               linear_energy_ranges,
    #                                               quadratic_energy_ranges,
    #                                               'msat')
    #     self.check_generated_ising_model(configurations, decision_variables, h, J, offset, gap)

    def test_specify_z3(self):
        """Test a simple model specifying yices as the smt solver. Combined
        with the other test_specify_... tests, serves as a smoke test for
        the smt_solver_name parameter.
        """
        graph = nx.complete_graph(3)
        configurations = {(-1, -1): 0, (1, 1): 0}
        decision_variables = [0, 1]
        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        min_classical_gap = 2

        h, J, offset, gap = maxgap.generate_ising(graph, configurations, decision_variables,
                                                  linear_energy_ranges,
                                                  quadratic_energy_ranges,
                                                  min_classical_gap,
                                                  'z3')
        self.check_generated_ising_model(configurations, decision_variables, h, J, offset, gap)

    def test_multiplication(self):

        graph = nx.complete_graph(4)
        configurations = {(x, y, x * y): 0 for x, y in itertools.product((-1, 1), repeat=2)}
        decision_variables = [0, 1, 2]

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}
        min_classical_gap = 1

        h, J, offset, gap = maxgap.generate_ising(graph, configurations, decision_variables,
                                                  linear_energy_ranges,
                                                  quadratic_energy_ranges,
                                                  min_classical_gap,
                                                  None)
        self.check_generated_ising_model(configurations, decision_variables, h, J, offset, gap)
        self.check_linear_energy_ranges(h, linear_energy_ranges)
        self.check_quadratic_energy_ranges(J, quadratic_energy_ranges)

    def test_negative_min_gap_impossible_bqm(self):
        # XOR Gate problem without auxiliary variables
        # Note: Regardless of the negative gap, this BQM should remain impossible.
        negative_gap = -3
        decision_variables = ['a', 'b', 'c']
        xor_gate = {(-1, -1, -1): 0,
                    (-1, 1, 1): 0,
                    (1, -1, 1): 0,
                    (1, 1, -1): 0}
        graph = nx.complete_graph(decision_variables)

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}

        with self.assertRaises(pm.ImpossiblePenaltyModel):
            maxgap.generate_ising(graph, xor_gate, decision_variables,
                                  linear_energy_ranges,
                                  quadratic_energy_ranges,
                                  negative_gap,
                                  None)

    def test_negative_min_gap_feasible_bqm(self):
        # Regardless of the negative min classical gap, this feasible BQM should return its usual
        # max classical gap.
        negative_gap = -2
        decision_variables = ['a']
        config = {(-1,): -1}
        graph = nx.complete_graph(decision_variables)

        linear_energy_ranges = {v: (-2., 2.) for v in graph}
        quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}

        _, _, _, gap = maxgap.generate_ising(graph, config, decision_variables,
                                             linear_energy_ranges,
                                             quadratic_energy_ranges,
                                             negative_gap,
                                             None)

        expected_gap = 2
        self.assertEqual(expected_gap, gap)

    def test_min_gap_no_aux(self):
        # Verify min_classical_gap parameter works
        def run_same_problem(min_classical_gap):
            decision_variables = ['a', 'b', 'c']
            or_gate = {(-1, -1, -1): 0,
                       (-1, 1, 1): 0,
                       (1, -1, 1): 0,
                       (1, 1, 1): 0}
            graph = nx.complete_graph(decision_variables)

            linear_energy_ranges = {v: (-2., 2.) for v in graph}
            quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}

            return maxgap.generate_ising(graph, or_gate, decision_variables,
                                         linear_energy_ranges,
                                         quadratic_energy_ranges,
                                         min_classical_gap,
                                         None)

        # Run problem with a min_classical_gap that is too large
        with self.assertRaises(pm.ImpossiblePenaltyModel):
            large_min_gap = 3
            run_same_problem(large_min_gap)

        # Lowering min_classical_gap should lead to a bqm being found
        smaller_min_gap = 1.5
        _, _, _, gap = run_same_problem(smaller_min_gap)
        self.assertGreaterEqual(gap, smaller_min_gap)

    def test_min_gap_with_aux(self):
        # Verify min_classical_gap parameter works
        def run_same_problem(min_classical_gap):
            decision_variables = ['a', 'b', 'c']
            xor_gate = {(-1, -1, -1): 0,
                        (-1, 1, 1): 0,
                        (1, -1, 1): 0,
                        (1, 1, -1): 0}
            graph = nx.complete_graph(decision_variables + ['aux0'])

            linear_energy_ranges = {v: (-2., 2.) for v in graph}
            quadratic_energy_ranges = {(u, v): (-1., 1.) for u, v in graph.edges}

            return maxgap.generate_ising(graph, xor_gate, decision_variables,
                                         linear_energy_ranges,
                                         quadratic_energy_ranges,
                                         min_classical_gap,
                                         None)

        # Run problem with a min_classical_gap that is too large
        with self.assertRaises(pm.ImpossiblePenaltyModel):
            large_min_gap = 2
            run_same_problem(large_min_gap)

        # Lowering min_classical_gap should lead to a bqm being found
        smaller_min_gap = 0.5
        _, _, _, gap = run_same_problem(smaller_min_gap)
        self.assertGreaterEqual(gap, smaller_min_gap)
