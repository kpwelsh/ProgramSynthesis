from Graph import Graph, Vertex, Edge, VertexMapping
from copy import deepcopy
import itertools
from queue import Queue

class Constraint:
    def __init__(self):
        self.G = Graph([Edge('asdf', [Vertex()])])

    def falsified_by(self, g):
        # Returns True if there is no way to 
        # make the constraint True by adding more edges/nodes
        # to the graph g.
        #pass
        return self.G in g

class Action:
    def __init__(self, input, output, mapping = None):
        self.Input = input
        self.Output = output
        if mapping is None:
            self.InOutMapping = VertexMapping({i:i for i in self.Input.V if i in self.Output.V})
        else:
            self.InOutMapping = mapping
        
        self.Input, in_mapping = self.Input.clone()
        self.Output, out_mapping = self.Output.clone()
    
        self.InOutMapping = ~(~self.InOutMapping * in_mapping) * out_mapping

        self.ToRemove = set(v for v in self.Input.V if v not in self.InOutMapping)


        self.ActionGraph = Graph([*self.Input.E, *self.Output.E])
        for i,o in self.InOutMapping.AtoB.items():
            self.ActionGraph.add_edge(Edge('*', (i,o)))
    
    def __call__(self, g):
        for mapping in g.match(self.Input):
            _g = deepcopy(g)
            for v in self.ToRemove:
                _g.remove_vertex(mapping[v])
            m = (~self.InOutMapping) * mapping
            yield _g.apply(self.Output, m), m

    def __invert__(self):
        return Action(self.Output, self.Input, ~self.InOutMapping)
    
    def __str__(self):
        return f'{self.Input}\n----\n{self.InOutMapping}\n----\n{self.Output}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(self.ActionGraph)
    def __eq__(self, other):
        return self.ActionGraph == other.ActionGraph

class AbstractGraph:
    def __init__(self, concrete_graph = None):
        if concrete_graph is None:
            concrete_graph = Graph([])
        self.ConcreteGraph = concrete_graph
    
    def match(self, g):
        distinct_graphs = set()
        # Similar to Graph.match, except we are allowed to create new 
        # vertices and edges to satisfy the match
        for r in range(0, len(g.V) + 1):
            # Select which vertices of g to try to match against
            # our sub graph. The remaining vertices will be created to 
            # satisfy the rest of the match.
            for combo in itertools.combinations(g.V, r):
                _g = g[combo]
                for mapping in self.ConcreteGraph.match(_g):
                    # Mapping starts as a partial mapping, but then
                    # the full mapping is infered by making new vertices when
                    # applying the graph to the current concrete one
                    next_concrete_graph = deepcopy(self.ConcreteGraph)
                    next_concrete_graph.apply(g, mapping)
                    if next_concrete_graph not in distinct_graphs:
                        distinct_graphs.add(next_concrete_graph)
                        yield next_concrete_graph, mapping

    
    def __str__(self):
        return str(self.ConcreteGraph)
    def __repr__(self):
        return repr(self.ConcreteGraph)

    def __hash__(self):
        return hash(self.ConcreteGraph)
    def __eq__(self, other):
        return self.ConcreteGraph == other.ConcreteGraph


class AbstractStateExplorer:
    def __init__(self, constraint, actions):
        self.Constraint = constraint
        self.Actions = actions

    def compile(self):
        actions = {}
        q = Queue()
        for a in self.Actions:
            if self.Constraint.falsified_by(a.Output):
                continue
            q.put((1,a))

        while not q.empty():
            n, compound_action = q.get()
            if n > 8:
                break
            intermediate = AbstractGraph(compound_action.Input)
            for a in self.Actions:
                for concrete_graph, out_to_graph in intermediate.match(a.Output):
                    final_graph = deepcopy(concrete_graph)
                    final_graph.apply(compound_action.Output, ~compound_action.InOutMapping.clone())
                    if self.Constraint.falsified_by(final_graph):
                        continue
                    in_to_graph = a.InOutMapping * out_to_graph
                    concrete_graph.remove(a.Output, out_to_graph)
                    concrete_graph.apply(a.Input, in_to_graph)
                    concrete_graph.prune()
                    new_action = Action(concrete_graph, final_graph)
                    if new_action not in actions.keys():
                        actions[compound_action] = None
                        q.put((n+1,new_action))
        print(ignored, total)
        for a in actions:
            print(a,'\n')
        print(len(actions))


if __name__ == '__main__':
    a, b = Vertex(2)

    g = Graph([
        Edge('Ball', (a,)),
        Edge('Ball', (b,))
    ])

    in_g = Graph([
        Edge('Ball', (a,))
    ])

    out_g = Graph([
        Edge('Hand', (a,)),
        ~Edge('Ball', (a,)),
        Edge('Orange', (b,))
    ])

    #a = Action(in_g, out_g)

    ase = AbstractStateExplorer(Constraint(), 
        [
            Action(
                Graph([
                ]),
                Graph([
                    Edge('Ball', (a,)),
                ])
            ),
            Action(
                Graph([
                ]),
                Graph([
                    Edge('Hand', (b,)),
                ])
            )
        ]
    )

    from cProfile import Profile
    from pstats import Stats
    p = Profile()
    p.enable()
    ase.compile()
    p.disable()
    Stats(p).sort_stats('cumtime').print_stats()

