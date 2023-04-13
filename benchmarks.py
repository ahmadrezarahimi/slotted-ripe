import time
import algos
import os
import utils
def benchmark(L, n):
    # Setup
    start_time = time.time()
    algos.setup(n, L)
    setup_time = time.time() - start_time
    print(f"Setup runtime: {setup_time:.4f} seconds")
    algos.batchKeyGen("crs.db", n, L)
    # Aggregate
    start_time = time.time()
    algos.aggregate("attributes.db", "pks.db", "crs.db", n, L)
    aggregate_time = time.time() - start_time
    print(f"Aggregate runtime: {aggregate_time:.4f} seconds")

benchmark(100,10)
os.remove("crs.db")
os.remove("pks.db")
os.remove("sks.db")
os.remove("attributes.db")
os.remove("hsk.db")
os.remove("mpk.db")