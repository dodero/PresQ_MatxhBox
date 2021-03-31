import os
import tarfile
from typing import Tuple, Any, Mapping, Iterable

import pandas


def load_results(run_id: str, basedir: str = '../results') -> Tuple[pandas.DataFrame, Mapping]:
    """
    Load a set of results from a tar file. It is expected to contain the output
    generated by /bin/benchmark.py

    Parameters
    ----------
    run_id : str
        Run identifier, which is the name of the tgz without the extension
    basedir : str
        Directory where the results are stored

    Returns
    -------
    out : pair
        The first one corresponds to the results of Find2, and the second
        is a dictionary where the key corresponds to the parametrization of FindQ
        and the value is the DataFrame with the results.
    """
    tar = tarfile.open(os.path.join(basedir, f'{run_id}.tgz'))
    find2 = pandas.read_csv(tar.extractfile(f'{run_id}/find2.csv'))
    find2.dropna(0, inplace=True, how='any')
    findq = {}
    for m in tar.getnames():
        filename = os.path.basename(m)
        if filename.startswith('findg'):
            name = os.path.splitext(filename)[0]
            _, lambd, gamma = name.split('_')
            findq[(float(lambd), float(gamma))] = pandas.read_csv(tar.extractfile(f'{m}'))
    return find2, findq


def compute_stats(data: pandas.DataFrame, filter_by: Tuple[str, Any]):
    """
    From a DataFrame containing the summary of the runs of one of the algorithm,
    compute the mean and standard deviation of the run-time and match-ratio

    Notes
    -----
    Since exact matches may have been lost by the unary search, or the bootstrapping, the ratio is computed over the
    possible values to obtain.

    Parameters
    ----------
    data : DataFrame
        As output from benchmark.py
    filter_by: pair of string/value
        Restrict the computation to a subset of the data (i.e. filter only by alpha = 0.1)

    Returns
    -------
    out : tuple(mean time, std time, mean ratio, mean std, number of aggregated rows)
    """
    max_ind_column = None
    for c in data.columns:
        if c.startswith('max_'):
            max_ind_column = c

    mask = (data[filter_by[0]] == filter_by[1])
    masked = data[mask]

    match = (masked[max_ind_column] / masked['exact'])
    return masked['time'].mean(), masked['time'].std(), match.mean(), match.std(), mask.sum()


def general_stats(find2: pandas.DataFrame, findq: Mapping[Any, pandas.DataFrame], findq_subset: Iterable = None,
                  alpha: float = 0.1):
    """
    Compute the statistics from both find2 and findq results

    Parameters
    ----------
    find2 :
        Find2 results
    findq :
        Set of FindQ results
    findq_subset :
        Use only these keys from the findq dictionary
    alpha :
        Compute statistics for this value of alpha

    Returns
    -------
    out : DataFrame
        A DataFrame with the aggregated information
    """
    if findq_subset is not None:
        findq = dict([(key, findq[key]) for key in findq_subset])

    rows = [('Find2', None, None) + compute_stats(find2, ('alpha', alpha))]

    for (lambd, gamma), v in findq.items():
        rows.append(('FindQ', lambd, 1 - alpha * gamma) + compute_stats(v, ('alpha', alpha)))

    return pandas.DataFrame(
        rows, columns=['Method', 'Lambda', 'Gamma', 'Time (mean)', 'Time (std)', 'Match (mean)', 'Match (std)', 'N']
    )
