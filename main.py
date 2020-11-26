from Graph import Graph, Vertex, Edge, VertexMapping
from copy import deepcopy
import itertools
from queue import Queue

class Constraint:
    def __init__(self):
        pass

    def falsified_by(self, g):
        # Returns True if there is no way to 
        # make the constraint True by adding more edges/nodes
        # to the graph g.
        #pass
        return False

class Action:
    def __init__(self, input, output, mapping = None):
        self.Input = input
        self.Output = output
        if mapping is None:
            self.InOutMapping = VertexMapping({i:i for i in self.Input.V if i in self.Output.V})
        else:
            self.InOutMapping = mapping

        self.ToRemove = set(v for v in self.Input.V if v not in self.InOutMapping)
    
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
                    next_concrete_graph = self.ConcreteGraph.apply(g, mapping)
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


class Node:
    def __init__(self, ag, parent = None, parent_mapping = None):
        self.AG = ag
        self.Parent = parent
        self.ParentMapping = parent_mapping

    def get_root_mapping(self):
        if self.Parent is None:
            return self.AG.ConcreteGraph, {v : v for v in self.AG.ConcreteGraph.V}
        else:
            g, mapping = self.Parent.get_root_mapping()
            m = {}
            for k,v in self.ParentMapping.items():
                if v in mapping.keys():
                    m[k] = mapping[v]
            return g, m


class AbstractStateExplorer:
    def __init__(self, constraint, actions):
        self.Constraint = constraint
        self.Nodes = []
        self.Actions = actions

    def compile(self):

        processed_stuff = []


        q = Queue()
        final = AbstractGraph()
        for a in self.Actions:
            for concrete_graph, _ in final.match(a.Output):
                if self.Constraint.falsified_by(concrete_graph):
                    continue
                other_final = AbstractGraph(concrete_graph)
                for previous_state, mapping in (~a)(concrete_graph):
                    q.put((other_final, mapping, AbstractGraph(previous_state)))
        
        for i in range(8):
            if q.empty():
                break
            (final, compound_mapping, intermediate) = q.get()
            for a in self.Actions:
                for concrete_graph, _ in intermediate.match(a.Output):
                    other_final_concrete_graph = concrete_graph.apply(final.ConcreteGraph, updated_mapping)
                    if self.Constraint.falsified_by(other_final_concrete_graph):
                        continue
                    for previous_state, mapping in (~a)(concrete_graph):
                        q.put((AbstractGraph(other_final_concrete_graph), mapping, AbstractGraph(previous_state)))
                    #q.put((AbstractGraph(other_final_concrete_graph), VertexMapping({v:v for v in concrete_graph.V}), AbstractGraph(concrete_graph)))

        while not q.empty():
            print(q.get())




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
        Edge('Orange', (b,))
    ])

    a = Action(in_g, out_g)

    ase = AbstractStateExplorer(Constraint(), [a])

    ase.compile()

