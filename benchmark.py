import algos as algos
import utils as utils
from petrelic.multiplicative.pairing import GT, Bn
import time
import os
import tqdm
def generate_y(X):
    n = len(X)
    y = [Bn(0)] * n
    temp_sum = Bn(0)

    for i in range(n - 1):
        y[i] = GT.order().random()
        temp_sum += X[i] * y[i]

    y[-1] = -temp_sum * X[-1].mod_inverse(GT.order())

    return y

'''
benchmark():
    runs the benchmarking for the given L and n
    Here L is the number of slots, and n is the length of attribute vector
'''
def benchmark(L, n):
    start_time = time.time()
    algos.setup(n, L)
    setup_time = time.time() - start_time

    algos.batchKeyGen("crs.db", n, L)

    start_time = time.time()
    algos.aggregate("attributes.db", "pks.db", "crs.db", n, L)
    aggregate_time = time.time() - start_time

    sks = utils.load_sk("sks.db", 0)
    mpk = utils.load_mpk("mpk.msgpack")
    hsk = utils.load_hsk("hsk.db", 0)
    X = hsk[3]
    sk = sks
    y = generate_y(X)
    m = GT.generator() ** GT.order().random()

    # Encryption (100 times) and average time
    enc_times = []
    for _ in range(100):
        start_time = time.time()
        ct = algos.Enc(mpk, y, m)
        enc_time = (time.time() - start_time) * 1000
        enc_times.append(enc_time)
    avg_enc_time = sum(enc_times) / len(enc_times)

    # Decryption (100 times) and average time
    dec_times = []
    for _ in range(100):
        start_time = time.time()
        m_dec = algos.Dec(hsk, sk, ct)
        dec_time = (time.time() - start_time) * 1000
        dec_times.append(dec_time)
    avg_dec_time = sum(dec_times) / len(dec_times)

    # Check if decryption is correct
    assert (m == m_dec)
    return setup_time, aggregate_time, avg_enc_time, avg_dec_time


from tqdm import tqdm

from tqdm import tqdm

def run_benchmarks(L_values, n_values):
    setup_times_matrix, aggregate_times_matrix, enc_times_matrix, dec_times_matrix, sizes_crs_matrix, sizes_mpk_matrix = utils.initialize_matrices(L_values, n_values)

    total_iterations = len(n_values) * len(L_values)
    progress_bar = tqdm(total=total_iterations, desc="Benchmarking", ncols=100)

    for i, n_value in enumerate(n_values):
        for j, L_value in enumerate(L_values):
            st, agt, et, dt = benchmark(L_value, n_value)
            setup_times_matrix[i][j] = st
            aggregate_times_matrix[i][j] = agt
            enc_times_matrix[i][j] = et
            dec_times_matrix[i][j] = dt
            sizes_crs_matrix[i][j] = os.path.getsize("crs.db")
            sizes_mpk_matrix[i][j] = os.path.getsize("mpk.msgpack")
            utils.remove()
            progress_bar.update(1)

    progress_bar.close()

    # Store the benchmark results in a CSV file
    utils.store_benchmarks(L_values, n_values, setup_times_matrix, aggregate_times_matrix, enc_times_matrix,
                     dec_times_matrix, sizes_crs_matrix, sizes_mpk_matrix, "benchmarks.csv")

    return setup_times_matrix, aggregate_times_matrix, enc_times_matrix, dec_times_matrix, sizes_crs_matrix, sizes_mpk_matrix


