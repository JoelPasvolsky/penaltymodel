import unittest

import networkx as nx

import penaltymodel as pm


class TestSpecification(unittest.TestCase):
    def test_construction_empty(self):
        spec = pm.Specification(nx.Graph(), [], {}, pm.SPIN)
        self.assertEqual(len(spec), 0)

    def test_construction_typical(self):
        graph = nx.complete_graph(10)
        decision_variables = (0, 4, 5)
        feasible_configurations = {(-1, -1, -1): 0.}

        spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.SPIN)

        self.assertEqual(spec.graph, graph)  # literally the same object
        self.assertEqual(spec.decision_variables, decision_variables)
        self.assertEqual(spec.feasible_configurations, feasible_configurations)
        self.assertIs(spec.vartype, pm.SPIN)

    def test_construction_from_edgelist(self):
        graph = nx.barbell_graph(10, 7)
        decision_variables = (0, 4, 3)
        feasible_configurations = {(-1, -1, -1): 0.}

        # specification from edges
        spec0 = pm.Specification(graph.edges, decision_variables, feasible_configurations, vartype=pm.SPIN)

        # specification from graph
        spec1 = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.SPIN)

        self.assertEqual(spec0, spec1)

    def test_construction_bad_graph(self):
        graph = 1
        decision_variables = (0, 4, 5)
        feasible_configurations = {(-1, -1, -1): 0.}

        with self.assertRaises(TypeError):
            pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.SPIN)

    def test_ranges_default(self):
        graph = nx.barbell_graph(4, 16)
        decision_variables = (0, 4, 3)
        feasible_configurations = {(0, 0, 0): 0.}

        spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.BINARY)

        for v in graph:
            self.assertEqual(spec.ising_linear_ranges[v], [-2, 2])

        for u, v in graph.edges:
            self.assertEqual(spec.ising_quadratic_ranges[u][v], [-1, 1])
            self.assertEqual(spec.ising_quadratic_ranges[v][u], [-1, 1])

    def test_linear_ranges_specified(self):
        graph = nx.barbell_graph(4, 16)
        decision_variables = (0, 4, 3)
        feasible_configurations = {(0, 0, 1): 0.}

        spec = pm.Specification(graph, decision_variables, feasible_configurations,
                                ising_linear_ranges={v: [-v, 2] for v in graph},
                                vartype=pm.BINARY)

        # check default energy ranges
        for v in graph:
            self.assertEqual(spec.ising_linear_ranges[v], [-v, 2])

        spec = pm.Specification(graph, decision_variables, feasible_configurations,
                                ising_linear_ranges={v: (-v, 2) for v in graph},
                                vartype=pm.BINARY)

        # check default energy ranges
        for v in graph:
            self.assertEqual(spec.ising_linear_ranges[v], [-v, 2])

    def test_quadratic_ranges_partially_specified(self):
        graph = nx.barbell_graph(4, 16)
        decision_variables = (0, 4, 3)
        feasible_configurations = {(0, 0, 1): 0.}

        spec = pm.Specification(graph, decision_variables, feasible_configurations,
                                ising_quadratic_ranges={0: {1: [0, 1], 2: [-1, 0]}, 2: {0: [-1, 0]}},
                                vartype=pm.BINARY)

        ising_quadratic_ranges = spec.ising_quadratic_ranges
        for u in ising_quadratic_ranges:
            for v in ising_quadratic_ranges[u]:
                self.assertIs(ising_quadratic_ranges[u][v], ising_quadratic_ranges[v][u])
        for u, v in graph.edges:
            self.assertIn(v, ising_quadratic_ranges[u])
            self.assertIn(u, ising_quadratic_ranges[v])

        self.assertEqual(ising_quadratic_ranges[0][1], [0, 1])

    def test_linear_ranges_bad(self):
        graph = nx.barbell_graph(4, 16)
        decision_variables = (0, 4, 3)
        feasible_configurations = {(0, 0, 1): 0.}

        with self.assertRaises(ValueError):
            pm.Specification(graph, decision_variables, feasible_configurations,
                             ising_linear_ranges={v: [-v, 'a'] for v in graph},
                             vartype=pm.BINARY)

        with self.assertRaises(TypeError):
            pm.Specification(graph, decision_variables, feasible_configurations,
                             ising_linear_ranges={v: [-v, 1, 1] for v in graph},
                             vartype=pm.BINARY)

    def test_vartype_specified(self):
        graph = nx.complete_graph(12)
        decision_variables = (0, 2, 5)
        feasible_configurations = {(1, 1, 1): 0.}

        spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.SPIN)
        self.assertIs(spec.vartype, pm.SPIN)

        spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.BINARY)
        self.assertIs(spec.vartype, pm.BINARY)

        # now set up a spec that can only have one vartype
        graph = nx.complete_graph(12)
        decision_variables = (0, 2, 5)
        feasible_configurations = {(1, 1, -1): 0.}

        spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.SPIN)
        self.assertIs(spec.vartype, pm.SPIN)

        # the feasible_configurations are spin
        with self.assertRaises(ValueError):
            spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.BINARY)

    def test_relabel_typical(self):
        graph = nx.circular_ladder_graph(12)
        decision_variables = (0, 2, 5)
        feasible_configurations = {(1, 1, 1): 0.}
        spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.SPIN)

        mapping = dict(enumerate('abcdefghijklmnopqrstuvwxyz'))

        new_spec = spec.relabel_variables(mapping)

        # create a test spec
        graph = nx.relabel_nodes(graph, mapping)
        decision_variables = (mapping[v] for v in decision_variables)
        test_spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.SPIN)

        self.assertEqual(new_spec, test_spec)
        self.assertEqual(new_spec.ising_linear_ranges, test_spec.ising_linear_ranges)
        self.assertEqual(new_spec.ising_quadratic_ranges, test_spec.ising_quadratic_ranges)

    def test_relabel_copy(self):
        graph = nx.circular_ladder_graph(12)
        decision_variables = (0, 2, 5)
        feasible_configurations = {(1, 1, 1): 0.}
        spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.SPIN)

        mapping = dict(enumerate('abcdefghijklmnopqrstuvwxyz'))

        new_spec = spec.relabel_variables(mapping, copy=True)

        # create a test spec
        graph = nx.relabel_nodes(graph, mapping)
        decision_variables = (mapping[v] for v in decision_variables)
        test_spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.SPIN)

        self.assertEqual(new_spec, test_spec)
        self.assertEqual(new_spec.ising_linear_ranges, test_spec.ising_linear_ranges)
        self.assertEqual(new_spec.ising_quadratic_ranges, test_spec.ising_quadratic_ranges)

    def test_relabel_inplace(self):
        graph = nx.circular_ladder_graph(12)
        decision_variables = (0, 2, 5)
        feasible_configurations = {(1, 1, 1): 0.}
        spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.SPIN)

        mapping = {i: v for i, v in enumerate('abcdefghijklmnopqrstuvwxyz') if i in graph}

        new_spec = spec.relabel_variables(mapping, copy=False)

        self.assertIs(new_spec, spec)  # should be the same object
        self.assertIs(new_spec.graph, spec.graph)

        # create a test spec
        graph = nx.relabel_nodes(graph, mapping)
        decision_variables = (mapping[v] for v in decision_variables)
        test_spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.SPIN)

        self.assertEqual(new_spec, test_spec)
        self.assertEqual(new_spec.ising_linear_ranges, test_spec.ising_linear_ranges)
        self.assertEqual(new_spec.ising_quadratic_ranges, test_spec.ising_quadratic_ranges)

    def test_relabel_inplace_identity(self):
        graph = nx.circular_ladder_graph(12)
        decision_variables = (0, 2, 5)
        feasible_configurations = {(1, 1, 1): 0.}
        spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.SPIN)

        mapping = {v: v for v in graph}

        new_spec = spec.relabel_variables(mapping, copy=False)

    def test_relabel_inplace_overlap(self):
        graph = nx.circular_ladder_graph(12)
        decision_variables = (0, 2, 5)
        feasible_configurations = {(1, 1, 1): 0.}
        spec = pm.Specification(graph, decision_variables, feasible_configurations, vartype=pm.SPIN)

        mapping = {v: v + 5 for v in graph}

        new_spec = spec.relabel_variables(mapping, copy=False)
