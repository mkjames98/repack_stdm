
from structpy.graph.labeled_digraph import MapMultidigraph
from structpy.graph import Database
from structpy.graph.traversal import preset as traversal

Graph = Database(MapMultidigraph)

_type = 'typ'


class KnowledgeBase(Graph):

    def __init__(self, arcs=None):
        Graph.__init__(self, arcs)

    def add_type(self, subtype, type):
        self.add(subtype, type, _type)

    def types(self, node):
        if self.has_node(node):
            return set(traversal.BreadthFirstOnArcs(self, node, _type)) - {node}
        else:
            return set()

    def subtypes(self, node):
        if self.has_node(node):
            return set(traversal.BreadthFirstOnArcsReverse(self, node, _type)) - {node}
        else:
            return set()

    def attribute(self, rings):
        """
        :param rings: dict<str: node,
                           tuple<
                                 bool: negated,
                                 bool: reverse,
                                 list<relation>: attribute chain
                                >
                          >
        :return: set<str: node>
        """
        result = None
        negs = set()
        for node, ring in rings.items():
            node = node.strip()
            negated, attr_chain = ring
            link = {node}
            for reverse, attr in attr_chain:
                attr = attr.strip()
                if attr == '*':
                    attr = None
                if not reverse:
                    link = set().union(*[self.targets(n, attr)
                                       for n in link if attr is None or self.has_arc_label(n, attr)])
                else:
                    link = set().union(*[self.sources(n, attr)
                                       for n in link if attr is None or self.has_in_arc_label(n, attr)])
            if negated:
                negs.update(link)
            else:
                if result is None:
                    result = link
                else:
                    result.intersection_update(link)
        return result - negs
