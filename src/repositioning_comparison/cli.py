# -*- coding: utf-8 -*-

import json
import os
import sys
from typing import Mapping

import click
import joblib

from .create_graph import create_himmelstein_graph
from .download import DIRECTORY, ensure_data
from .nodetovec import (
    EmbedderFunction, embed_average, embed_hadamard, embed_weighted_l1, embed_weighted_l2,
    fit_node2vec,
)
from .pairs import test_pairs, train_pairs
from .permutation_convert import convert
from .subgraph import generate_subgraph
from .train import train_logistic_regression, validate

DEFAULT_GRAPH_TYPE = 'subgraph'
GRAPH_TYPES = [
    'wholegraph',
    'subgraph',
    'permutation1',
    'permutation2',
    'permutation3',
    'permutation4',
    'permutation5',
]

EMBEDDERS: Mapping[str, EmbedderFunction] = {
    'hadamard': embed_hadamard,
    'average': embed_average,
    'weighted_l1': embed_weighted_l1,
    'weighted_l2': embed_weighted_l2,
}

HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DIRECTORY = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, 'results'))
RESULTS_DIRECTORY = os.environ.get('REPOSITIONING_COMPARISON_DIRECTORY', DEFAULT_DIRECTORY)


@click.command()
@click.option('-t', '--graph-type', type=click.Choice(GRAPH_TYPES), default=DEFAULT_GRAPH_TYPE)
@click.option('--data-directory', type=click.Path(dir_okay=True, file_okay=False), default=DIRECTORY, show_default=True)
@click.option('-d', '--output-directory', type=click.Path(dir_okay=True, file_okay=False), default=RESULTS_DIRECTORY,
              help='Output directory. Defaults to current working directory.', show_default=True)
@click.option('--method', default='node2vec', type=click.Choice(['node2vec', 'edge2vec', 'metapath2vec']))
@click.option('--embedder', default='hadamard', type=click.Choice(list(EMBEDDERS)))
def main(graph_type: str, data_directory: str, output_directory: str, method: str, embedder: str):
    """This cli runs the ComparisonNRL."""
    node_path, edge_path, feature_path, validate_path, permutation_paths = ensure_data(directory=data_directory)

    with open(os.path.join(output_directory, 'metadata.txt'), 'w') as file:
        json.dump(
            {
                'graph': graph_type,
                'method': method,
                'embedder': embedder,
            },
            file,
            indent=2,
            sort_keys=True,
        )

    embedder_fn: EmbedderFunction = EMBEDDERS[embedder]

    click.echo(f'Running method={method}, type={graph_type}, embedder={embedder}')
    if method == 'node2vec':
        if graph_type == 'subgraph':
            subgraph_node2vec_directory = os.path.join(output_directory, 'node2vec_subgraph')
            run_node2vec_subgraph(node_path, edge_path, feature_path, embedder_fn, subgraph_node2vec_directory)

        elif graph_type == 'wholegraph':
            wholegraph_node2vec_directory = os.path.join(output_directory, 'node2vec')
            wholegraph = create_himmelstein_graph(node_path, edge_path)
            run_node2vec(wholegraph, wholegraph_node2vec_directory, feature_path, validate_path, embedder_fn)

        elif graph_type == "permutation1":
            graph = convert(permutation_paths[0], 1)

        else:
            click.secho(f'Graph type not implemented yet: {graph_type}')
            sys.exit(1)

    else:
        click.secho(f'Method not implemented yet: {method}')
        sys.exit(1)


def run_node2vec_subgraph(
        node_path,
        edge_path,
        feature_path,
        embedder_function: EmbedderFunction,
        output_directory,
) -> None:
    if not os.path.exists(output_directory):
        os.mkdir(output_directory)

    click.echo('creating graph')
    graph = create_himmelstein_graph(node_path, edge_path)

    click.echo('creating sub-graph')
    (subgraph,
     positive_list,
     positive_labels,
     negative_list,
     negative_labels) = generate_subgraph(feature_path, graph, cutoff=3, pnumber=10, nnumber=20)

    click.echo('fitting node2vec')
    model = fit_node2vec(subgraph)

    click.echo('generating positive and negative vectors')
    negative_vectors = embedder_function(model, negative_list)
    positive_vectors = embedder_function(model, positive_list)

    train_vectors = positive_vectors[0:5] + negative_vectors[0:15]
    train_labels = positive_labels[0:5] + negative_labels[0:15]
    train_data = [train_vectors, train_labels]
    with open(os.path.join(output_directory, 'train.json'), 'w') as file:
        json.dump(train_data, file, indent=2, sort_keys=True)

    test_vectors = positive_vectors[5:] + negative_vectors[15:]
    test_labels = positive_labels[5:] + negative_labels[15:]
    test_data = [test_vectors, test_labels]
    with open(os.path.join(output_directory, 'test.json'), 'w') as file:
        json.dump(test_data, file, indent=2, sort_keys=True)

    logistic_regression = train_logistic_regression(train_vectors, train_labels)
    with open(os.path.join(output_directory, 'model.joblib'), 'wb') as file:
        joblib.dump(logistic_regression, file)

    roc = validate(logistic_regression, test_vectors, test_labels)
    with open(os.path.join(output_directory, 'validation.json'), 'w') as file:
        json.dump(
            {
                'ROC': roc,
            },
            file,
            sort_keys=True,
            indent=2,
        )


def run_node2vec(
        graph,
        output_directory,
        feature_path,
        validate_path,
        embedder_function: EmbedderFunction,
) -> None:
    if not os.path.exists(output_directory):
        os.mkdir(output_directory)

    model = fit_node2vec(graph)

    train_list, train_labels = train_pairs(feature_path)
    train_vecs = embedder_function(model, train_list)
    train_data = [train_vecs, train_labels]
    with open(os.path.join(output_directory, 'train.json'), 'w') as train_file:
        json.dump(train_data, train_file, indent=2, sort_keys=True)

    test_list, test_labels = test_pairs(validate_path)
    test_vecs = embedder_function(model, test_list)
    test_data = [test_vecs, test_labels]
    with open(os.path.join(output_directory, 'test.json'), 'w') as test_file:
        json.dump(test_data, test_file, indent=2, sort_keys=True)

    lg = train_logistic_regression(train_vecs, train_labels)
    with open(os.path.join(output_directory, 'model.joblib'), 'wb') as model_file:
        joblib.dump(lg, model_file)

    roc = validate(lg, test_vecs, test_labels)
    with open(os.path.join(output_directory, 'validate.txt'), 'w') as validate_file:
        print(f'ROC: {roc}', file=validate_file)
