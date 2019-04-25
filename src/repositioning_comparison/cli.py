import click

from .create_graph import create_himmelstein_graph
from .download import ensure_data, DIRECTORY
from .nodetovec import nodetovec, HadamardEmbedder, AverageEmbedder, WeightedL1Embedder, WeightedL2Embedder
from .subgraph import subgraph
from .train import train, validate
from .pairs import train_pairs, test_pairs

GRAPH_TYPES = ['subgraph', 'wholegraph', 'permutation1', 'permutation2', 'permutation3', 'permutation4', 'permutation5']
EMBEDDER_TYPES = ['HadamardEmbedder', 'AverageEmbedder', 'WeightedL1Embedder', 'WeightedL2Embedder']


@click.command()
@click.argument('graphtype', type=click.Choice(GRAPH_TYPES))
@click.option('--data-directory', type=click.Path(dir_okay=True, file_okay=False), default=DIRECTORY, show_default=True)
@click.option('--method', default='node2vec', type=click.Choice(['node2vec', 'edge2vec', 'metapath2vec']))
@click.option('--embedder', default='HadamardEmbedder', type=click.Choice(EMBEDDER_TYPES))
def main(graphtype, data_directory, method, embedder):
    """This cli runs the ComparisonNRL."""
    nodepath, edgepath, featurepath, validatepath = ensure_data(directory=data_directory)

    if graphtype == 'subgraph' and method == 'node2vec':
        result = subgraph_node2vec(nodepath, edgepath, featurepath, embedder)
        click.echo(f'Result: {result}')
    elif graphtype == 'wholegraph' and method == 'node2vec':
        wholegraph = create_himmelstein_graph(nodepath,edgepath)
        result = graph_node2vec(wholegraph,nodepath, edgepath, featurepath,validatepath, embedder)
        click.echo(f'Result: {result}')


def subgraph_node2vec(nodepath, edgepath, featurepath, embedder):
    biggraph = create_himmelstein_graph(nodepath, edgepath)
    thisgraph, positive_list, positive_label, negative_list, negative_label = subgraph(featurepath, biggraph, 3, 10,
                                                                                       20)
    model = nodetovec(thisgraph)
    if embedder == 'HadamardEmbedder':
        positive_vecs = HadamardEmbedder(model, positive_list)
        negative_vecs = HadamardEmbedder(model, negative_list)
    elif embedder == 'AverageEmbedder':
        positive_vecs = AverageEmbedder(model, positive_list)
        negative_vecs = AverageEmbedder(model, negative_list)
    elif embedder == 'WeightedL1Embedder':
        positive_vecs = WeightedL1Embedder(model, positive_list)
        negative_vecs = WeightedL1Embedder(model, negative_list)
    elif embedder == 'WeightedL2Embedder':
        positive_vecs = WeightedL2Embedder(model, positive_list)
        negative_vecs = WeightedL2Embedder(model, negative_list)
    else:
        raise NotImplementedError

    train_vecs = positive_vecs[0:5] + negative_vecs[0:15]
    train_labels = positive_label[0:5] + negative_label[0:15]
    test_vecs = positive_vecs[5:] + negative_vecs[15:]
    test_labels = positive_label[5:] + negative_label[15:]
    lg = train(train_vecs, train_labels)
    roc = validate(lg, test_vecs, test_labels)
    return roc


def graph_node2vec(graph,nodepath, edgepath, featurepath,validatepath, embedder):
    model = nodetovec(graph)
    train_list,train_labels = train_pairs(featurepath)
    test_list,test_labels = test_pairs(validatepath)
    if embedder == 'HadamardEmbedder':
        train_vecs = HadamardEmbedder(model,train_list)
        test_vecs = HadamardEmbedder(model,test_list)
    elif embedder == 'AverageEmbedder':
        train_vecs = AverageEmbedder(model,train_list)
        test_vecs = AverageEmbedder(model,test_list)
    elif embedder == 'WeightedL1Embedder':
        train_vecs = WeightedL1Embedder(model,train_list)
        test_vecs = WeightedL1Embedder(model,test_list)
    elif embedder == 'WeightedL2Embedder':
        train_vecs = WeightedL2Embedder(model,train_list)
        test_vecs = WeightedL2Embedder(model,test_list)
    else:
        raise NotImplementedError
    lg = train(train_vecs, train_labels)
    roc = validate(lg, test_vecs, test_labels)
    return roc
