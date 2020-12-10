from Graph import Graph, Vertex, Edge, VertexMapping
from copy import deepcopy
import itertools
from queue import Queue
from collections import defaultdict

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
    def __init__(self, label, input, output, mapping = None, compound = None):
        self.Label = label
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

        #this is used to track what actions/mappings are needed to complete a "compound action"
        if compound is None:
            compound = []
        self.CompoundActionTracker = compound + [(self.Label, self.InOutMapping * ~out_mapping)]

        self.ActionGraph = Graph([*self.Input.E, *self.Output.E])
        for i,o in self.InOutMapping.AtoB.items():
            self.ActionGraph.add_edge(Edge('*', (i,o)))
        self.ActionGraph.process()
    
    def __call__(self, g):
        for mapping in g.match(self.Input, proper = True):
            _g = deepcopy(g)
            for v in self.ToRemove:
                _g.remove_vertex(mapping[v])
            m = (~self.InOutMapping) * mapping
            _g.apply(self.Output, m)
            yield _g, m

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

    def is_solvedby(self, other):
        if len(self.Input.V) - len(other.Input.V) != len(self.Output.V) - len(other.Output.V):
            return False
        if len(self.Input.E) - len(other.Input.E) != len(self.Output.E) - len(other.Output.E):
            return False
        self_counts = defaultdict(int)
        other_counts = defaultdict(int)

        for e in self.Input.E:
            self_counts[e.Label] -= 1
        for e in other.Input.E:
            other_counts[e.Label] -= 1
        for e in self.Output.E:
            self_counts[e.Label] += 1
        for e in other.Output.E:
            other_counts[e.Label] += 1

        for e, c in self_counts.items():
            if c != 0 and other_counts[e] != c:
                return False
        # This is wrong for relationships
        return True


        if other.Output not in self.Output:
            return False
        for mapping in self.Input.match(other.Input):
            g = deepcopy(self.Input)
            m = ~other.InOutMapping * mapping
            g.apply(other.Output, m)
            g.process()
            if g == self.Output:
                return True
        return False
        
    def __len__(self):
        return len(self.ActionGraph.V)

class AbstractGraph:
    def __init__(self, concrete_graph = None):
        if concrete_graph is None:
            concrete_graph = Graph([])
        self.ConcreteGraph = concrete_graph
    
    def match(self, g):
        distinct_graphs = set()
        # Similar to Graph.match, except we are allowed to create new 
        # vertices and edges to satisfy the match
        for r in range(len(g.V), -1, -1):
            # Select which vertices of g to try to match against
            # our sub graph. The remaining vertices will be created to 
            # satisfy the rest of the match.
            for combo in itertools.combinations(g.V, r):
                _g = g[combo]
                # for v in g.V - _g.V:
                #     if g[combo + (v,)] in self.ConcreteGraph:
                #         continue
                #         break
                # else:
                for mapping in self.ConcreteGraph.match(_g):
                    # Mapping starts as a partial mapping, but then
                    # the full mapping is infered by making new vertices when
                    # applying the graph to the current concrete one
                    next_concrete_graph = deepcopy(self.ConcreteGraph)
                    next_concrete_graph.apply(g, mapping)
                    # for v in next_concrete_graph.V - set(mapping.values()):
                    #     next_concrete_graph.remove_vertex(v)

                    next_concrete_graph.prune()
                    next_concrete_graph.process()
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

        self.CompoundActionsList = set()

    def compile(self, depth):
        self.CompoundActionsList = set()
        q = Queue()
        for a in self.Actions:
            q.put((1, a))
            self.CompoundActionsList.add(a)

        while not q.empty():
            n, compound_action = q.get()
            if n > depth:
                break
            found = False
            for a in self.CompoundActionsList:
                if not a is compound_action and compound_action.is_solvedby(a):
                    found = True
                    break
            if found:
                self.CompoundActionsList.remove(compound_action)
                continue
            intermediate = AbstractGraph(compound_action.Input)
            for a in self.Actions:
                for concrete_graph, out_to_graph in intermediate.match(a.Output):
                    final_graph = deepcopy(concrete_graph)
                    final_graph.apply(compound_action.Output, ~compound_action.InOutMapping.clone())
                    in_to_graph = a.InOutMapping * out_to_graph
                    concrete_graph.remove(a.Output, out_to_graph)
                    concrete_graph.apply(a.Input, in_to_graph)

                    concrete_graph.prune()
                    concrete_graph.process()

                    new_action = Action(a.Label,concrete_graph, final_graph, compound=deepcopy(compound_action.CompoundActionTracker))
                    if new_action not in self.CompoundActionsList:
                        self.CompoundActionsList.add(new_action)
                        q.put((n+1,new_action))

        cal = list(sorted(self.CompoundActionsList, key = len))
        for i in reversed(range(len(cal))):
            for j in range(i):
                if cal[i].is_solvedby(cal[j]):
                    del cal[i]
                    break
        self.CompoundActionsList = cal
        for a in cal:
            pass#print(a)


    #tries the actions and compound actions 
    #to see if one will work with the given input
    #to satisfy the constraints
    def find_solution(self, initial_state):
        for a in self.CompoundActionsList:
            #first apply the compound action
            for curr_state, _ in a(initial_state):
                print(curr_state)
                continue
                #then check if it meets constraint
                if self.Constraint.falsified_by(curr_state):
                    print("this does not meet the constraint")
                    continue
                else:
                    return a, curr_state

        return None

if __name__ == '__main__':
    a, b, c, d = Vertex(4)

    g = Graph([
        Edge('Ring', (a,)),
        Edge('Ring', (b,)),
        Edge('Top', (a,)),
        Edge('Top', (b,)),
        Edge('Base', (c,)),
        Edge('Base', (d,)),
        Edge('Above', (a, c)),
        Edge('Above', (b, d))
    ])

    a, b, c = Vertex(3)
    ase = AbstractStateExplorer(Constraint(), 
        [
            Action('Move Ring',
                Graph([
                    Edge('Ring', (a,)),
                    Edge('Top', (a,)),
                    Edge('Top', (b,)),
                    ~Edge('Above', (a,b)),
                    ~Edge('Above', (b,a)),
                    Edge('Above', (a, c))
                ]),
                Graph([
                    Edge('Ring', (a,)),
                    Edge('Top', (a,)),
                    ~Edge('Top', (b,)),
                    Edge('Above', (a,b)),
                    ~Edge('Above', (b,a)),
                    ~Edge('Above', (a, c)),
                    Edge('Top', (c,))
                ])
            )
        ]
    )

    a, b, c = Vertex(3)
    ase = AbstractStateExplorer(Constraint(), 
        [
            Action('sort_ball',
                Graph([
                    Edge('Ball', (a,)),
                    Edge('Hand', (b,)),
                ]),
                Graph([
                    Edge('Ball', (a,)),
                    Edge('Sorted', (a,)),
                    Edge('Hand', (b,)),
                ])
            ),
            Action('buy_orange',
                Graph([
                ]),
                Graph([
                    Edge('Orange', (a,)),
                ])
            )
        ]
    )

    from cProfile import Profile
    from pstats import Stats
    p = Profile()
    p.enable()
    for i in range(10):
        ase.compile(i)
        print(len(ase.CompoundActionsList))
    p.disable()
    #sol, end_state = ase.find_solution(g) #right now it just returns the first action it applies just because anything meets the constraints
    #print('solution', sol.CompoundActionTracker)
    #print(end_state)
    #Stats(p).sort_stats('cumtime').print_stats()

