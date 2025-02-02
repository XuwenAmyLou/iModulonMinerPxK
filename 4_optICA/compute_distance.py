"""
Clusters the S vectors generated from random_restart_ica.py
The output files are S.csv and A.csv.

To execute the code:

mpiexec -n <n_cores> python cluster_components.py -i ITERATIONS [-o OUT_DIR ]

n_cores: Number of processors to use
OUT_DIR: Path to output directory
ITERATIONS: Total number of ICA runs
"""


import argparse
import os
import re

# Limiting threads for various libraries
os.environ["OMP_NUM_THREADS"] = "1"  # OpenMP
os.environ["OPENBLAS_NUM_THREADS"] = "1"  # OpenBLAS
os.environ["MKL_NUM_THREADS"] = "1"  # MKL
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"  # Accelerate
os.environ["NUMEXPR_NUM_THREADS"] = "1"  # NumExpr

import shutil
import sys
import time
import itertools

import numpy as np
import pandas as pd
from mpi4py import MPI
from scipy import sparse

# Argument parsing
parser = argparse.ArgumentParser(description="Generates Distance Matrix")
parser.add_argument(
    "-i", type=int, dest="iterations", required=True, help="Number of ICA runs"
)
parser.add_argument(
    "-o",
    dest="out_dir",
    default="",
    help="Path to output file directory (default: current directory)",
)
args = parser.parse_args()


# -----------------------------------------------------------
# Split the work

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
nWorkers = comm.Get_size()

n_iters = args.iterations
# -----------------------------------------------------------

# -----------------------------------------------------------
# Parse directories

if args.out_dir == "":
    OUT_DIR = os.getcwd()
else:
    OUT_DIR = args.out_dir

tmp_dir = os.path.join(OUT_DIR, "tmp")

# -----------------------------------------------------------


def timeit(start):
    end = time.time()
    t = end - start
    if t < 60:
        print("{:.2f} seconds elapsed".format(t))
    elif t < 3600:
        print("{:.2f} minutes elapsed".format(t / 60))
    else:
        print("{:.2f} hours elapsed".format(t / 3600))
    return end


t = time.time()

# ----------------------------------------------------------

# Discover available proc_i_S.csv files
proc_files = [f for f in os.listdir(tmp_dir) if f.startswith("proc_") and f.endswith("_S.csv")]
proc_indices = [int(f.split('_')[1]) for f in proc_files]

# Generate task pairs based on available files
tasks = [(i, j) for i in proc_indices for j in proc_indices if i <= j]

# Split up tasks evenly

worker_tasks = {w: [] for w in range(nWorkers)}
w_idx = 0
for task in tasks:
    worker_tasks[w_idx].append(task)
    w_idx = (w_idx + 1) % nWorkers

n_tasks = len(worker_tasks[rank])

if rank == 0:
    print("\nComputing clusters...")

t1 = time.time()

# Load S matrices piece-wise to conserve memory
for i, j in worker_tasks[rank]:
    S1 = pd.read_csv(os.path.join(tmp_dir, "proc_{}_S.csv".format(i)), index_col=0)
    S2 = pd.read_csv(os.path.join(tmp_dir, "proc_{}_S.csv".format(j)), index_col=0)
    dist = abs(np.dot(S1.T, S2))
    dist[dist < 0.5] = 0
    dist_file = os.path.join(tmp_dir, "dist_{}_{}.npz".format(i, j))
    sparse_dist = sparse.coo_matrix(np.clip(dist, 0, 1))
    sparse.save_npz(dist_file, sparse_dist)

# Wait for processors to finish
if rank == 0:
    test = 1
else:
    test = 0
test = comm.bcast(test, root=0)
if rank == 0:
    print("\nDistance matrix completed!")
    timeit(t1)
