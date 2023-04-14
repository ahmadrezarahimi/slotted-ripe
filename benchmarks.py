import algos as algos
import utils as utils
import os
import math
from petrelic.multiplicative.pairing import GT, Bn
import time
import matplotlib.pyplot as plt

n = 10
# L_values = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
L_values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
'''
remove():
    removes all the files that are created by functions
'''
def remove():
    os.remove("crs.db")
    os.remove("pks.db")
    os.remove("sks.db")
    os.remove("attributes.db")
    os.remove("hsk.db")
    os.remove("mpk.db")

'''
convert_size():
    converts the size of the file into a readable format
'''
def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

'''
print_size():
    prints the size of the file
'''
def print_size(file_path):
    print(f"Size of {file_path}: {convert_size(os.path.getsize(file_path))}")

'''
benchmark():
    runs the benchmarking for the given L and n
    Here L is the number of slots, and n is the length of attribute vector
'''
def benchmark(L, n):
    print(f"Benchmarking for L={L}, n={n}")

    start_time = time.time()
    algos.setup(n, L)
    setup_time = time.time() - start_time
    print_size("crs.db")

    algos.batchKeyGen("crs.db", n, L)

    start_time = time.time()
    algos.aggregate("attributes.db", "pks.db", "crs.db", n, L)
    aggregate_time = time.time() - start_time
    print_size("mpk.db")

    sks = utils.load_sk("sks.db", 0)
    mpk = utils.load_mpk("mpk.db")
    hsk = utils.load_hsk("hsk.db", 0)

    sk = sks
    y = [Bn(0)] * n
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

    # print the results
    print(f"Setup time: {setup_time:.2f} seconds")
    print(f"Aggregate time: {aggregate_time:.2f} seconds")
    print(f"Encryption time: {avg_enc_time:.2f} ms")
    print(f"Decryption time: {avg_dec_time:.2f} ms")
    print("\n")

    return setup_time, aggregate_time, avg_enc_time, avg_dec_time

# Variables to store benchmark results
setup_times = []
aggregate_times = []
enc_times = []
dec_times = []
sizes_crs = []
sizes_mpk = []

# Open the output file
with open("benchmarks.txt", "w") as outfile:
    for L in L_values:
        st, agt, et, dt = benchmark(L, n)
        setup_times.append(st)
        aggregate_times.append(agt)
        enc_times.append(et)
        dec_times.append(dt)
        sizes_crs.append(os.path.getsize("crs.db"))
        sizes_mpk.append(os.path.getsize("mpk.db"))

        outfile.write(f"L={L}, n={n}\n")
        outfile.write(f"Setup time: {st:.2f} seconds\n")
        outfile.write(f"Aggregate time: {agt:.2f} seconds\n")
        outfile.write(f"Encryption time: {et:.2f} ms\n")
        outfile.write(f"Decryption time: {dt:.2f} ms\n")
        outfile.write(f"Size of crs: {convert_size(sizes_crs[-1])}\n")
        outfile.write(f"Size of mpk: {convert_size(sizes_mpk[-1])}\n")
        outfile.write("\n")

        remove()

# Plotting the charts


'''
plot_chart():
'''
def plot_chart(x, y1, y2, xlabel, ylabel, title, filename, y1_label, y2_label):
    plt.plot(x, y1, label=y1_label)
    plt.plot(x, y2, label=y2_label)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.savefig(filename)
    plt.clf()

# Adjust y-axis limits for Encryption and Decryption time
plt.ylim([min(enc_times + dec_times) * 0.9, max(enc_times + dec_times) * 1.1])

plot_chart(L_values, enc_times, dec_times, "L", "Time (ms)", "Encryption & Decryption Time vs L", "enc_dec_time.png", "Encryption Time", "Decryption Time")
plot_chart(L_values, setup_times, aggregate_times, "L", "Time (s)", "Setup & Aggregate Time vs L", "setup_aggregate_time.png", "Setup Time", "Aggregate Time")

def plot_chart2(x, y, xlabel, ylabel, title, filename):
    plt.plot(x, y)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.savefig(filename)
    plt.clf()

sizes_crs_mb = [size / (1024 * 1024) for size in sizes_crs]
plot_chart2(L_values, sizes_crs_mb, "L", "Size (MB)", "Size of CRS vs L (in MB)", "size_crs_mb.png")

print("Benchmark results saved in benchmarks.txt and corresponding charts saved as images.")
