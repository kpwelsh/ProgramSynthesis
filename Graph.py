from collections import defaultdict
import itertools
from copy import deepcopy, copy

class VertexMapping:
    def __init__(self, mapping = {}):
        # Represents a bi-directional mapping between
        # vertices

        self.AtoB = {}
        self.BtoA = {}
        self.add_mapping(mapping)

    def add_mapping(self, mapping):
        for v1, v2 in mapping.items():
            self.AtoB[v1] = v2
            self.BtoA[v2] = v1
    
    def remove_mapping(self, keys):
        for k in keys:
            if k in self:
                del self.BtoA[self.AtoB[k]]
                del self.AtoB[k]

    def __contains__(self, v):
        return v in self.AtoB.keys()

    def __getitem__(self, key):
        return self.AtoB[key]

    def __call__(self, g):
        return Graph((e.map_vertices(self) for e in g.E))

    def __mul__(self, rhs):
        mapping = {}
        for a, b in self.AtoB.items():
            if b in rhs.AtoB.keys():
                mapping[a] = rhs[b]
        vm = VertexMapping(mapping)
        return vm
    
    def __invert__(self):
        m = VertexMapping()
        # Maybe deepcopy here?
        m.AtoB = self.BtoA
        m.BtoA = self.AtoB
        return m

    def __str__(self):
        inner = ','.join(map(str,self.AtoB.items()))
        return f'{{{inner}}}'
    
    def __repr__(self):
        return str(self)

    def __iter__(self):
        return iter(self.AtoB.keys())

    def clone(self):
        return deepcopy(self)
    

class Vertex:
    ID = 0

    def __new__(cls, n = 1):
        if n == 1:
            return super(Vertex, cls).__new__(cls)
        vs = []
        for i in range(n):
            v = super(Vertex, cls).__new__(cls)
            v.__init__()
            vs.append(v)
        return vs

    def __init__(self):
        self.Id = Vertex.ID
        Vertex.ID += 1
    def __str__(self):
        return str(self.Id)
    def __repr__(self):
        return str(self)
    def __hash__(self):
        return hash(self.Id)
    def __eq__(self, other):
        return self.Id == other.Id

class Edge:
    def __init__(self, label, vertices):
        self.Label = label
        self.Vertices = vertices
        self.Neg = False

    def map_vertices(self, mapping):
        vertices = []
        for v in self.Vertices:
            if v not in mapping:
                mapping.add_mapping({v:Vertex()})
            vertices.append(mapping[v])
        e = Edge(self.Label, vertices)
        e.Neg = self.Neg
        return e

    def clone(self):
        e = Edge(self.Label, [Vertex() for v in self.Vertices])
        e.Neg = self.Neg
        return e
                
    def __str__(self):
        inner = ','.join(map(str, self.Vertices))
        return f'{self.Label}({inner})'
    def __repr__(self):
        return str(self)
    def __hash__(self):
        return hash(self.Label) + sum(map(hash, self.Vertices))
    def __eq__(self, other):
        return self.Label == other.Label and all(v1 == v2 for v1,v2 in zip(self, other)) and self.Neg == other.Neg
    def __iter__(self):
        return iter(self.Vertices)
    def __invert__(self):
        e = Edge(self.Label, self.Vertices)
        e.Neg = not self.Neg
        return e

class Graph:
    def __init__(self, edges = []):
        self.V = set()
        self.E = set()
        self.EdgeMap = defaultdict(set)

        for e in edges:
            self.add_edge(e)
    
    def remove_vertex(self, v):
        if v in self.V:
            self.V.remove(v)
            for e in self.EdgeMap[v]:
                self.E.remove(e)

    def add_edge(self, e):
        if ~e in self.E:
            self.E.remove(~e)
            for v in e:
                self.EdgeMap[v].remove(~e)
                if len(self.EdgeMap[v]) == 0:
                    del self.EdgeMap[v]
                    self.V.remove(v)
        else:
            if e not in self.E:
                self.E.add(e)
                for v in e:
                    self.V.add(v)
                    if e not in self.EdgeMap[v]:
                        self.EdgeMap[v].add(e)
    
    def __contains__(self, other):
        return any(self.match(other))

    def match(self, other):
        # Checking containment amounts to finding a vertex mapping M from 
        # other.V -> self.V for all other.V such that if R(other.V) then R(M(self.V))
        if len(self.V) < len(other.V):
            return
        vertices = list(other.V)
        # Try all mappings
        for perm in itertools.permutations(self.V, len(other.V)):
            mapping = VertexMapping({v1: v2 for v1, v2 in zip(vertices, perm)})
            # Check if its a consistent mapping
            consistent = True
            for v1 in vertices:
                for e1 in other.EdgeMap[v1]:
                    e = Edge(e1.Label, (mapping[v] for v in e1))
                    if (e not in self.EdgeMap[mapping[v1]]) or (~e in self.EdgeMap[mapping[v1]]):
                        consistent = False
                        break
                if not consistent:
                    break
            else:
                yield mapping
        return

    def apply(self, other, mapping):
        # Uses the mapping to apply the relationships expressed in other
        # to the vertices in self.
        modified_g = deepcopy(self)
        for e in mapping(other).E:
            modified_g.add_edge(e)
        return modified_g

    def clone(self):
        return Graph((e.clone() for e in self.E))

    def __hash__(self):
        return 1 # Dummy hash function to enable convenient set operations

    def __eq__(self, other):
        return self in other and other in self

    def __str__(self):
        return '\n'.join(map(str, self.E))
    
    def __repr__(self):
        return str(self)
    
    def __iter__(self):
        return iter(self.E)
    
    def __or__(self, other):
        return Graph(itertools.chain(self, other.clone()))

    def __getitem__(self, vertices):
        edges = set()
        for v in vertices:
            if v not in self.V:
                raise KeyError()
            for e in self.EdgeMap[v]:
                if e not in edges and all((_v in vertices for _v in e)):
                    edges.add(e)
        return Graph(edges)


if __name__ == '__main__':
    a = Vertex()
    b = Vertex()
    c = Vertex()
    
    g = Graph(
        [
            Edge('Holding', (a, b)),
            Edge('Hand', (a,)),
            Edge('Ball', (b,)),
            Edge('Ball', (c,))
        ]
    )

    a = Vertex()
    b = Vertex()
    c = Vertex()

    g2 = Graph(
        [
            Edge('Ball', (a,)),
            Edge('Ball', (c,)),
            Edge('Hand', (b,))
        ]
    )

    print(g2 in g)
    for m in g.match(g2):
        print(m)