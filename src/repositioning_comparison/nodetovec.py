# -*- coding: utf-8 -*-

from functools import partial
from typing import Iterable, List, Tuple, Type

import gensim
import networkx
import node2vec
import node2vec.edges

__all__ = [
    'fit_node2vec',
    'embed_hadamard',
    'embed_average',
    'embed_weighted_l1',
    'embed_weighted_l2',
]


def fit_node2vec(graph: networkx.Graph) -> gensim.models.Word2Vec:
    node2vec_model = node2vec.Node2Vec(graph, dimensions=64, walk_length=30, num_walks=200, workers=4)
    word2vec_model = node2vec_model.fit(window=10, min_count=1, batch_words=4)
    return word2vec_model


def embed(
        word2vec_model: gensim.models.Word2Vec,
        pair_list: Iterable[Tuple[str, str]],
        edge_embedder_cls: Type[node2vec.edges.EdgeEmbedder],
) -> List:
    """

    :param word2vec_model:
    :param pair_list:
    :param edge_embedder_cls: Which :class:`node2vec.edges.EdgeEmbedder` from :mod:`node2vec.edges` to use.
    :return:
    """
    edge_embeddings = edge_embedder_cls(keyed_vectors=word2vec_model.wv)
    return [
        edge_embeddings[node1, node2].tolist()
        for node1, node2 in pair_list
    ]


embed_hadamard = partial(embed, edge_embedder_cls=node2vec.edges.HadamardEmbedder)
embed_average = partial(embed, edge_embedder_cls=node2vec.edges.AverageEmbedder)
embed_weighted_l1 = partial(embed, edge_embedder_cls=node2vec.edges.WeightedL1Embedder)
embed_weighted_l2 = partial(embed, edge_embedder_cls=node2vec.edges.WeightedL2Embedder)
