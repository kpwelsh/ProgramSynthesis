from collections import defaultdict
import itertools
from copy import deepcopy, copy
from Primes import PRIMES


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

    def values(self):
        return self.AtoB.values

    def __contains__(self, v):
        return v in self.AtoB.keys()

    def __getitem__(self, key):
        return self.AtoB[key]
    
    def __setitem__(self, key, value):
        self.AtoB[key] = value
        self.BtoA[value] = key

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

    def __lt__(self, other):
        return self.Id < other.Id
    def __gt__(self, other):
        return self.Id > other.Id

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
    PRIME_MAPPING = {}
    def __init__(self, label, vertices, neg = False):
        if neg:
            label = "~" + label
        if label not in Edge.PRIME_MAPPING.keys():
            Edge.PRIME_MAPPING[label] = PRIMES[len(Edge.PRIME_MAPPING)]
        self.Prime = Edge.PRIME_MAPPING[label]
        self.Label = label

        self.Vertices = vertices
        self.Neg = neg
        #self.HashCache = hash(self.Label) + sum(map(hash, self.Vertices))

    def map_vertices(self, mapping):
        vertices = []
        for v in self.Vertices:
            if v not in mapping:
                mapping.add_mapping({v:Vertex()})
            vertices.append(mapping[v])
        e = Edge(self.Label.lstrip('~'), vertices, self.Neg)
        return e

    def clone(self, mapping):
        vertices = []
        for v in self.Vertices:
            if v not in mapping:
                mapping[v] = Vertex()
            vertices.append(mapping[v])
        e = Edge(self.Label.lstrip('~'), vertices, self.Neg)
        return e
                
    def __str__(self):
        inner = ','.join(map(str, self.Vertices))
        return f'{self.Label}({inner})'
    def __repr__(self):
        return str(self)
    def __hash__(self):
        return hash(self.Label) + sum(map(hash, self.Vertices))
    def __eq__(self, other):
        return self.Label == other.Label and all(v1 == v2 for v1,v2 in zip(self, other))
    def __iter__(self):
        return iter(self.Vertices)
    def __invert__(self):
        e = Edge(self.Label.lstrip('~'), self.Vertices, not self.Neg)
        return e

    def __lt__(self, other):
        if self.Label < other.Label:
            return True
        return tuple(self.Vertices) < tuple(other.Vertices)
    def __gt__(self, other):
        if self.Label > other.Label:
            return True
        return tuple(self.Vertices) > tuple(other.Vertices)

class Graph:
    def __init__(self, edges = []):
        self.V = set()
        self.E = set()
        self.EdgeMap = defaultdict(set)
        self.Prime = 1

        for e in edges:
            self.add_edge(e)
        self.process()

    def process(self):
        self.SubGraphs = defaultdict(int)
        seen = set()
        for v in self.V:
            if v not in seen:
                component = self.connected_component(v)
                seen |= component
                if len(component) == len(self.V):
                    self.SubGraphs[self] += 1
                    break
                self.SubGraphs[self[component]] += 1

    
    def connected_component(self, v, component = None):
        if component is None:
            component = set()
        component.add(v)
        for e in self.EdgeMap[v]:
            for v in e:
                if v not in component:
                    self.connected_component(v, component)
        return component

    def remove_vertex(self, v):
        if v in self.V:
            self.V.remove(v)
            for e in self.EdgeMap[v]:
                self.E.remove(e)
            del self.EdgeMap[v]

    def remove_edge(self, e):
        if e in self.E:
            self.E.remove(e)
            self.Prime /= e.Prime
            for v in set(e):
                self.EdgeMap[v].remove(e)

    def add_edge(self, e):
        self.remove_edge(~e)
        if e not in self.E:
            self.E.add(e)
            self.Prime *= e.Prime
            for v in e:
                self.V.add(v)
                if e not in self.EdgeMap[v]:
                    self.EdgeMap[v].add(e)
    
    def __contains__(self, other):
        v = self.Prime / other.Prime
        if int(v) != v:
            return False
        return any(self.match(other))

    def match(self, other, proper = False):
        # Checking containment amounts to finding a vertex mapping M from 
        # other.V -> self.V for all other.V such that if R(other.V) then R(M(self.V))
        # v = self.Prime / other.Prime
        # if int(v) != v and not proper:
        #     return
        if len(other.V) > len(self.V):
            return
        vertices = list(other.V)

        if not proper:
            for mapping in self.__match(other, vertices, proper = proper):
                g = mapping(other)
                for e in g.E:
                    if e not in self.E:
                        break
                    if ~e in self.E:
                        break
                else:
                    yield mapping
            return

        # Try all mappings
        for perm in itertools.permutations(self.V, len(other.V)):
            mapping = VertexMapping({v1: v2 for v1, v2 in zip(vertices, perm)})
            g = mapping(other)
            for e in g.E:
                if proper:
                    if not e.Neg and not e in self.E:
                        break
                    if ~e in self.E:
                        break
                else:
                    if e not in self.E:
                        break
                    if ~e in self.E:
                        break
            else:
                yield mapping
        return

    def __match(self, other, remaining_verts : list, mapping = None, proper = False):
        if mapping is None:
            mapping = VertexMapping()

        if len(remaining_verts) == 0:
            yield mapping
            return
        
        v = remaining_verts[0]
        remaining_verts = remaining_verts[1:]
        if v in mapping:
            for full_mapping in self.__match(other, remaining_verts, mapping, proper):
                yield full_mapping

        for v2 in self.V:
            for e1 in other.EdgeMap[v]:
                found = False
                for e2 in self.EdgeMap[v2]:
                    if e1.Label == e2.Label:
                        found = True
                        break
                if not found:
                    break
            else:
                m = mapping.clone()
                
                m.add_mapping({v:v2})
                for full_mapping in self.__match(other, remaining_verts, m, proper):
                    yield full_mapping

    def apply(self, other, mapping):
        for e in mapping(other).E:
            self.add_edge(e)
    
    def remove(self, other, mapping):
        for e in mapping(other).E:
            self.remove_edge(e)

    def prune(self):
        to_remove = []
        for v in self.V:
            if len(self.EdgeMap[v]) == 0:
                to_remove.append(v)
        for v in to_remove:
            self.V.remove(v)
            del self.EdgeMap[v]

    def clone(self):
        mapping = VertexMapping()
        return Graph([e.clone(mapping) for e in self.E]), mapping

    def __deepcopy__(self, memo):
        return Graph([deepcopy(e, memo) for e in self.E])

    def __hash__(self):
        return hash(self.Prime)

    def __eq__(self, other):
        if self.Prime != other.Prime:
            return False
        
        if len(self.SubGraphs) != len(other.SubGraphs):
            return False
        if len(self.SubGraphs) > 1:
            for a, c in self.SubGraphs.items():
                if a not in other.SubGraphs.keys() or other.SubGraphs[a] != c:
                    return False
            return True
        prime_a = defaultdict(list)
        prime_b = defaultdict(list)
        for v in other.V:
            p = 1
            for e in other.EdgeMap[v]:
                p *= e.Prime
            prime_a[p].append(v)
        for v in self.V:
            p = 1
            for e in self.EdgeMap[v]:
                p *= e.Prime
            prime_b[p].append(v)

        mapping_groups = []
        for k in prime_a.keys():
            a = prime_a[k]
            b = prime_b[k]
            mapping_groups.append(
                [itertools.zip_longest(perm, b) for perm in itertools.permutations(a)]
            )
        for mapping in itertools.product(*mapping_groups):
            vm = VertexMapping({k:v for k,v in itertools.chain(*mapping)})
            for e in other.E:
                e = e.map_vertices(vm)
                if e not in self.E:
                    break
                if ~e in self.E:
                    break
            else:
                return True
        return False

    def __str__(self):
        return str(dict(self.EdgeMap))
    
    def __repr__(self):
        return str(self)
    
    def __iter__(self):
        return iter(self.E)

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
            Edge('Hand', (a,)),
            Edge('Ball', (a,)),
            Edge('Ball', (c,))
        ]
    )

    a = Vertex()
    b = Vertex()
    c = Vertex()

    g2 = Graph(
        [
            Edge('Ball', (b,)),
            Edge('Ball', (c,)),
            Edge('Hand', (b,))
        ]
    )


    print(g2 == g)
    

    #print(g2 in g)
    #for m in g.match(g2):
    #    print(m)