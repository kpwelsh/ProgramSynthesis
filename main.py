from Graph import Graph, Vertex, Edge
from copy import deepcopy
import itertools

class Constraint:
    def __init__(self):
        pass

    def falsified_by(self, g):
        # Returns True if there is no way to 
        # make the constraint True by adding more edges/nodes
        # to the graph g.
        pass

class Action:
    def __init__(self, input, output):
        self.Input = input
        self.Output = output
    
    def __call__(self, g):
        for mapping in g.match(self.Input):
            yield g.apply(self.Output, mapping)

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

    def compile(self):
        self.Nodes = [Node(AbstractGraph())]
        
        for n in self.Nodes:
            root_graph, root_mapping = n.get_root_mapping() # Could be cached
            for mapping in g.ConcreteGraph.match(existing_graph.ConcreteGraph):
                # Invert the mapping to get a mapping from g to existing_graph
                flipped = {v:k for k,v in mapping.items()}
                # Append the root_mapping to the end of this mapping
                full_mapping = {}
                for k,v in flipped.items():
                    if v in root_mapping.keys():
                        full_mapping[k] = root_mapping[v]
                
                # Abstract graphs satisfy the constraints if their concrete graphs don't falsify them. 
                if not self.Constraint.falsified_by(g.ConcreteGraph.apply(root_graph, full_mapping)):
                    # TODO: 



if __name__ == '__main__':
    a, b = Vertex(2)

    g = Graph([
        Edge('Ball', (a,)),
        Edge('Ball', (b,))
    ])

    in_g = Graph([
        #Edge('Ball', (a,))
    ])

    out_g = Graph([
        Edge('Hand', (a,)),
        Edge('Orange', (b,))
    ])

    a = Action(in_g, out_g)

    ag = AbstractGraph(g)

    for cg, m in ag.match(g):
        print(cg)
        print()

