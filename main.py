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
            self.CompoundActionTracker = [(self.Label,self.InOutMapping)]
        else:
            self.CompoundActionTracker = compound

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

        self.CompoundActionsList = set()

    def compile(self):
        #note, renamed/relocated actions to self.CompoundActionsList so that I could access it from a different function
        #actions = set() 
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
                    new_action = Action('compound',concrete_graph, final_graph, compound=deepcopy(compound_action.CompoundActionTracker))
                    new_action.CompoundActionTracker.append((a.Label, in_to_graph)) #add the newest step to the compound action
                    #l = len(actions)
                    #actions.add(new_action)
                    l = len(self.CompoundActionsList)
                    self.CompoundActionsList.add(new_action)
                    #if l != len(actions):
                    if l != len(self.CompoundActionsList):
                        q.put((n+1,new_action))
        ##for a in actions:
        for a in self.CompoundActionsList:
            print(a, '\n')
            print(a.CompoundActionTracker)
        ##print(len(actions), q.qsize())
        print(len(self.CompoundActionsList), q.qsize())

    #tries the actions and compound actions 
    #to see if one will work with the given input
    #to satisfy the constraints
    def find_solution(self, initial_state):
        for action in self.Actions:
            curr_state = deepcopy(initial_state)
            curr_state.apply(action.Output, action.InOutMapping.clone())
            
            #then check if it meets constraint
            if self.Constraint.falsified_by(curr_state):
                print("this does not meet the constraint")
                continue
            else:
                return action

        for a_set in self.CompoundActionsList:
            #first apply the compound action
            curr_state = deepcopy(initial_state)
            for a in a_set.CompoundActionTracker:
                action = self.find_action(a[0])
                if action is not None:
                    curr_state.apply(action.Output, a[1].clone())
            
            #then check if it meets constraint
            if self.Constraint.falsified_by(curr_state):
                print("this does not meet the constraint")
                continue
            else:
                return a_set

        return None

    #returns an action given the action's name
    def find_action(self, name):
        for a in self.Actions:
            if a.Label == name:
                return a
        return None


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
            Action('make_ball',
                Graph([
                ]),
                Graph([
                    Edge('Ball', (a,)),
                ])
            ),
            Action('make_hand',
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
    sol = ase.find_solution(g) #right now it just returns the first action it applies just because anything meets the constraints
    print(sol.CompoundActionTracker)
    Stats(p).sort_stats('cumtime').print_stats()

