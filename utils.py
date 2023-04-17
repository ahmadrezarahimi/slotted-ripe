from petrelic.multiplicative.pairing import G1Element, G2Element, GTElement, Bn
import sqlite3
import csv
import os
import math
import pandas as pd
'''
store_crs(): Stores the CRS data in the database
inputs: CRS (G1, G2, GT, h, Gamma, A, B, U, W)
output: None
'''


def store_crs(A, B, Gamma, U, W, Z, g1, g2, h):
    conn = sqlite3.connect("crs.db")
    cur = conn.cursor()
    # Create the tables
    cur.execute('CREATE TABLE IF NOT EXISTS crs_g1 (id INTEGER PRIMARY KEY, value BLOB)')
    cur.execute('CREATE TABLE IF NOT EXISTS crs_g2 (id INTEGER PRIMARY KEY, value BLOB)')
    cur.execute('CREATE TABLE IF NOT EXISTS crs_gt (id INTEGER PRIMARY KEY, value BLOB)')
    cur.execute('CREATE TABLE IF NOT EXISTS crs_h (id INTEGER PRIMARY KEY, value BLOB)')
    cur.execute('CREATE TABLE IF NOT EXISTS crs_gamma (id INTEGER PRIMARY KEY, value BLOB)')
    cur.execute('CREATE TABLE IF NOT EXISTS crs_A (id INTEGER PRIMARY KEY, value BLOB)')
    cur.execute('CREATE TABLE IF NOT EXISTS crs_B (id INTEGER PRIMARY KEY, value BLOB)')
    cur.execute('CREATE TABLE IF NOT EXISTS crs_U (i INTEGER, j INTEGER, value BLOB, PRIMARY KEY (i, j))')
    cur.execute('CREATE TABLE IF NOT EXISTS crs_W (i INTEGER, j INTEGER, k INTEGER, value BLOB, PRIMARY KEY (i, j, k))')
    # Store the CRS data in the database
    cur.execute('INSERT OR REPLACE INTO crs_g1 (id, value) VALUES (?, ?)', (1, g1.to_binary()))
    cur.execute('INSERT OR REPLACE INTO crs_g2 (id, value) VALUES (?, ?)', (1, g2.to_binary()))
    cur.execute('INSERT OR REPLACE INTO crs_gt (id, value) VALUES (?, ?)', (1, Z.to_binary()))
    cur.execute('INSERT OR REPLACE INTO crs_h (id, value) VALUES (?, ?)', (1, h.to_binary()))
    cur.execute('INSERT OR REPLACE INTO crs_gamma (id, value) VALUES (?, ?)', (1, Gamma.to_binary()))
    for i, a in enumerate(A):
        cur.execute('INSERT OR REPLACE INTO crs_A (id, value) VALUES (?, ?)', (i, a.to_binary()))
    for i, b in enumerate(B):
        cur.execute('INSERT OR REPLACE INTO crs_B (id, value) VALUES (?, ?)', (i, b.to_binary()))
    for i, row in enumerate(U):
        for j, u in enumerate(row):
            cur.execute('INSERT OR REPLACE INTO crs_U (i, j, value) VALUES (?, ?, ?)', (i, j, u.to_binary()))
    for i, row in enumerate(W):
        for j, col in enumerate(row):
            if i != j:
                for k, w in enumerate(col):
                    cur.execute('INSERT OR REPLACE INTO crs_W (i, j, k, value) VALUES (?, ?, ?, ?)',
                                (i, j, k, w.to_binary()))
    # Commit the changes and close the connection
    conn.commit()
    conn.close()


'''
load_crs(): Loads the CRS data from the database
inputs: L (number of slots) and db_path (path to the database)
output: CRS (G1, G2, GT, h, Gamma, A, B, U, W)
'''


def load_crs(L, db_path='crs.db'):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute('SELECT value FROM crs_g1 WHERE id = 1')
    g1 = G1Element.from_binary(cur.fetchone()[0])
    cur.execute('SELECT value FROM crs_g2 WHERE id = 1')
    g2 = G2Element.from_binary(cur.fetchone()[0])
    cur.execute('SELECT value FROM crs_gt WHERE id = 1')
    Z = GTElement.from_binary(cur.fetchone()[0])
    cur.execute('SELECT value FROM crs_h WHERE id = 1')
    h = G1Element.from_binary(cur.fetchone()[0])
    cur.execute('SELECT value FROM crs_gamma WHERE id = 1')
    Gamma = G1Element.from_binary(cur.fetchone()[0])

    cur.execute('SELECT value FROM crs_A ORDER BY id')
    A = [G2Element.from_binary(row[0]) for row in cur.fetchall()]
    cur.execute('SELECT value FROM crs_B ORDER BY id')
    B = [G2Element.from_binary(row[0]) for row in cur.fetchall()]

    cur.execute('SELECT i, j, value FROM crs_U ORDER BY i, j')
    U = [[] for _ in range(L)]
    for row in cur.fetchall():
        i, j, value = row
        U[i].append(G1Element.from_binary(value))

    cur.execute('SELECT i, j, k, value FROM crs_W ORDER BY i, j, k')
    W = [[[] for _ in range(L)] for _ in range(L)]
    for row in cur.fetchall():
        i, j, k, value = row
        if i != j:
            W[i][j].append(G2Element.from_binary(value))

    conn.close()

    crs = g1, g2, Z, h, Gamma, A, B, U, W
    return crs


'''
load_public_keys(): Loads the public keys from the database
inputs: db_path (path to the database) and L (number of slots)
output: pks (list of public keys)
'''


def load_public_keys(db_path, L):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    pks = []
    for i in range(L):
        cur.execute('SELECT U1 FROM public_keys_U1 WHERE i = ?', (i,))
        U1_binary = cur.fetchone()[0]
        U1 = G1Element.from_binary(U1_binary)

        Wh = [None] * L
        for j in range(L):
            if j != i:
                cur.execute('SELECT Wh FROM public_keys_Wh WHERE i = ? AND j = ?', (i, j))
                Wh_binary = cur.fetchone()[0]
                Wh[j] = G2Element.from_binary(Wh_binary)

        pks.append([U1, Wh])

    conn.close()
    return pks


'''
load_sk(): Loads the secret key of the ith user from the database
inputs: sk_db_path (path to the database) and i (index of the user)
output: sk (secret key) as a Bn object
'''


def load_sk(sk_db_path, i):
    with sqlite3.connect(sk_db_path) as conn_sk:
        cur_sk = conn_sk.cursor()
        cur_sk.execute('SELECT sk FROM secret_keys WHERE i=?', (i,))
        sk_data = cur_sk.fetchone()

        if sk_data is not None:
            sk_binary = sk_data[0]
            sk = Bn.from_binary(sk_binary)
            return sk
        else:
            raise ValueError("Secret key not found for index {}".format(i))


'''
load_attributes(): Loads the attributes of the ith user from the database
inputs: db_path (path to the database), n (number of attributes) and L (number of slots)
output: attributes (list of attributes)
'''


def load_attributes(db_path, n, L):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    attributes = []
    for i in range(L):
        attr_i = []
        for j in range(n):
            cur.execute('SELECT value FROM attributes WHERE i = ? AND j = ?', (i, j))
            value_binary = cur.fetchone()[0]
            value = Bn.from_binary(value_binary)
            attr_i.append(value)
        attributes.append(attr_i)

    conn.close()
    return attributes


'''
store_hsk(): Stores the helping secret key of the ith user in the database
inputs: db_path (path to the database) and hsk (helping secret key)
output: None
'''


def store_hsk(db_path, hsk):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS helping_secret_key
                   (i INTEGER PRIMARY KEY, g1 BLOB, g2 BLOB)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS helping_secret_key_X
                   (i INTEGER, idx INTEGER, X_elem BLOB, PRIMARY KEY (i, idx))''')
    cur.execute('''CREATE TABLE IF NOT EXISTS helping_secret_key_A
                   (i INTEGER, A_elem BLOB, PRIMARY KEY (i))''')
    cur.execute('''CREATE TABLE IF NOT EXISTS helping_secret_key_B
                   (i INTEGER, B_elem BLOB, PRIMARY KEY (i))''')
    cur.execute('''CREATE TABLE IF NOT EXISTS helping_secret_key_What
                   (i INTEGER, idx INTEGER, What_elem BLOB, PRIMARY KEY (i, idx))''')

    for i, (g1, g2, idx, X_elem, A_elem, B_elem, What_elem) in enumerate(hsk):
        cur.execute('INSERT OR REPLACE INTO helping_secret_key (i, g1, g2) VALUES (?, ?, ?)',
                    (i, g1.to_binary(), g2.to_binary()))

        for j, x in enumerate(X_elem):
            cur.execute('INSERT OR REPLACE INTO helping_secret_key_X (i, idx, X_elem) VALUES (?, ?, ?)',
                        (i, j, x.binary()))

        cur.execute('INSERT OR REPLACE INTO helping_secret_key_A (i, A_elem) VALUES (?, ?)',
                    (i, A_elem.to_binary()))

        cur.execute('INSERT OR REPLACE INTO helping_secret_key_B (i, B_elem) VALUES (?, ?)',
                    (i, B_elem.to_binary()))

        for j, what in enumerate(What_elem):
            cur.execute('INSERT OR REPLACE INTO helping_secret_key_What (i, idx, What_elem) VALUES (?, ?, ?)',
                        (i, j, what.to_binary()))

    conn.commit()
    conn.close()


'''
load_hsk(): Loads the helping secret key of the ith user from the database
inputs: db_path (path to the database) and i (index of the user)
output: hsk (helping secret key)
'''


def load_hsk(db_path, i):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('SELECT * FROM helping_secret_key WHERE i=?', (i,))
    row = cur.fetchone()

    if row is None:
        raise ValueError(f"Helping secret key with index {i} not found.")

    g1 = G1Element.from_binary(row[1])
    g2 = G2Element.from_binary(row[2])

    cur.execute('SELECT X_elem FROM helping_secret_key_X WHERE i=? ORDER BY idx', (i,))
    X_elem = [Bn.from_binary(x[0]) for x in cur.fetchall()]

    cur.execute('SELECT A_elem FROM helping_secret_key_A WHERE i=?', (i,))
    A_elem = G2Element.from_binary(cur.fetchone()[0])

    cur.execute('SELECT B_elem FROM helping_secret_key_B WHERE i=?', (i,))
    B_elem = G2Element.from_binary(cur.fetchone()[0])

    cur.execute('SELECT idx, What_elem FROM helping_secret_key_What WHERE i=? ORDER BY idx', (i,))
    what_rows = cur.fetchall()
    What_elem = [None] * len(what_rows)
    for row in what_rows:
        idx, what = row
        What_elem[idx] = G2Element.from_binary(what)

    conn.close()
    return g1, g2, i, X_elem, A_elem, B_elem, What_elem


'''
store_mpk(): Stores the master public key in the database
inputs: g1, g2, h, Z, Gamma, Uhat (master public key)
output: None
'''


# def store_mpk(g1, g2, h, Z, Gamma, Uhat):
#     with sqlite3.connect('mpk.db') as conn_mpk:
#         cur_mpk = conn_mpk.cursor()
#         cur_mpk.execute('CREATE TABLE IF NOT EXISTS master_public_key (name TEXT PRIMARY KEY, value BLOB)')
#         cur_mpk.execute('CREATE TABLE IF NOT EXISTS uhat (id INTEGER PRIMARY KEY, value BLOB)')
#         conn_mpk.commit()
#
#         cur_mpk.execute("INSERT OR REPLACE INTO master_public_key (name, value) VALUES ('g1', ?)", (g1.to_binary(),))
#         cur_mpk.execute("INSERT OR REPLACE INTO master_public_key (name, value) VALUES ('g2', ?)", (g2.to_binary(),))
#         cur_mpk.execute("INSERT OR REPLACE INTO master_public_key (name, value) VALUES ('h', ?)", (h.to_binary(),))
#         cur_mpk.execute("INSERT OR REPLACE INTO master_public_key (name, value) VALUES ('Z', ?)", (Z.to_binary(),))
#         cur_mpk.execute("INSERT OR REPLACE INTO master_public_key (name, value) VALUES ('Gamma', ?)",
#                         (Gamma.to_binary(),))
#
#         cur_mpk.executemany("INSERT OR REPLACE INTO uhat (id, value) VALUES (?, ?)",
#                             [(i, elem.to_binary()) for i, elem in enumerate(Uhat)])
#
#         conn_mpk.commit()
#
#
# '''
# load_mpk(): Loads the master public key from the database
# inputs: db_path (path to the database)
# output: g1, g2, h, Z, Gamma, Uhat (master public key)
# '''
#
#
# def load_mpk(db_path):
#     conn = sqlite3.connect(db_path)
#     cur = conn.cursor()
#
#     cur.execute("SELECT value FROM master_public_key WHERE name='g1'")
#     g1 = G1Element.from_binary(cur.fetchone()[0])
#
#     cur.execute("SELECT value FROM master_public_key WHERE name='g2'")
#     g2 = G2Element.from_binary(cur.fetchone()[0])
#
#     cur.execute("SELECT value FROM master_public_key WHERE name='h'")
#     h = G1Element.from_binary(cur.fetchone()[0])
#
#     cur.execute("SELECT value FROM master_public_key WHERE name='Z'")
#     Z = GTElement.from_binary(cur.fetchone()[0])
#
#     cur.execute("SELECT value FROM master_public_key WHERE name='Gamma'")
#     Gamma = G1Element.from_binary(cur.fetchone()[0])
#
#     cur.execute("SELECT value FROM uhat ORDER BY id")
#     Uhat_rows = cur.fetchall()
#     Uhat = [G1Element.from_binary(row[0]) for row in Uhat_rows]
#
#     conn.close()
#     return g1, g2, h, Z, Gamma, Uhat

import msgpack

def store_mpk(g1, g2, h, Z, Gamma, Uhat, filename='mpk.msgpack'):
    data = {
        'g1': g1.to_binary(),
        'g2': g2.to_binary(),
        'h': h.to_binary(),
        'Z': Z.to_binary(),
        'Gamma': Gamma.to_binary(),
        'Uhat': [elem.to_binary() for elem in Uhat]
    }

    with open(filename, 'wb') as outfile:
        msgpack.dump(data, outfile)

def load_mpk(filename='mpk.msgpack'):
    with open(filename, 'rb') as infile:
        data = msgpack.load(infile)

    g1 = G1Element.from_binary(data['g1'])
    g2 = G2Element.from_binary(data['g2'])
    h = G1Element.from_binary(data['h'])
    Z = GTElement.from_binary(data['Z'])
    Gamma = G1Element.from_binary(data['Gamma'])
    Uhat = [G1Element.from_binary(elem) for elem in data['Uhat']]

    return g1, g2, h, Z, Gamma, Uhat
# -------------------- Draw Plots --------------------
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

def custom_format_number(number):
    if number >= 1000:
        return f"{number:.0f}"
    elif number >= 100:
        return f"{number:.1f}"
    else:
        return f"{number:.2f}"

def plot_heatmap(matrix, x, y, xlabel, ylabel, title, filename, unit):
    data = np.array(matrix)

    # Create a custom annotation matrix based on the custom_format_number function
    annot = np.vectorize(custom_format_number)(data)

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(data, annot=annot, fmt="", cmap="viridis", cbar_kws={"label": unit}, ax=ax, xticklabels=x, yticklabels=y)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)

    plt.savefig(filename)
    plt.clf()


# Call the plot_heatmap function with the corresponding units


def plot_3d_chart(x, y, z, xlabel, ylabel, zlabel, title, filename):
    x, y = np.meshgrid(x, y)
    z = np.array(z)

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_surface(x, y, z, cmap='viridis', edgecolor='none')

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_zlabel(zlabel)
    ax.set_title(title)

    plt.savefig(filename)
    plt.clf()



def store_benchmarks(L_values, n_values, setup_times_matrix, aggregate_times_matrix, enc_times_matrix, dec_times_matrix, sizes_crs_matrix, sizes_mpk_matrix, filename):
    file_exists = os.path.exists(filename)

    with open(filename, "a" if file_exists else "w", newline="") as csvfile:
        fieldnames = [
            "L", "n", "Setup time (s)", "Aggregate time (s)",
            "Encryption time (ms)", "Decryption time (ms)", "Size of crs (B)", "Size of mpk (B)"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for i, n_value in enumerate(n_values):
            for j, L_value in enumerate(L_values):
                writer.writerow({
                    "L": L_value,
                    "n": n_value,
                    "Setup time (s)": setup_times_matrix[i][j],
                    "Aggregate time (s)": aggregate_times_matrix[i][j],
                    "Encryption time (ms)": enc_times_matrix[i][j],
                    "Decryption time (ms)": dec_times_matrix[i][j],
                    "Size of crs (B)": sizes_crs_matrix[i][j],
                    "Size of mpk (B)": sizes_mpk_matrix[i][j]
                })


import pandas as pd

def load_benchmarks(filename):
    df = pd.read_csv(filename)

    # Sort the dataframe by 'L' and 'n' columns
    df = df.sort_values(by=['n', 'L'])


    L_values = sorted(df['L'].unique())
    n_values = sorted(df['n'].unique())

    setup_times_matrix = reshape_matrix(df['Setup time (s)'].tolist(), n_values, L_values)
    aggregate_times_matrix = reshape_matrix(df['Aggregate time (s)'].tolist(), n_values, L_values)
    enc_times_matrix = reshape_matrix(df['Encryption time (ms)'].tolist(), n_values, L_values)
    dec_times_matrix = reshape_matrix(df['Decryption time (ms)'].tolist(), n_values, L_values)
    sizes_crs_matrix = reshape_matrix(df['Size of crs (B)'].tolist(), n_values, L_values)
    sizes_mpk_matrix = reshape_matrix(df['Size of mpk (B)'].tolist(), n_values, L_values)

    return L_values, n_values, setup_times_matrix, aggregate_times_matrix, enc_times_matrix, dec_times_matrix, sizes_crs_matrix, sizes_mpk_matrix


def reshape_matrix(matrix, n_values, L_values):
    return [matrix[i * len(L_values):(i + 1) * len(L_values)] for i in range(len(n_values))]

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
    os.remove("mpk.msgpack")

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

def generate_all_plots(L_values, n_values, setup_times_matrix, aggregate_times_matrix, enc_times_matrix, dec_times_matrix, sizes_crs_matrix_mb, sizes_mpk_matrix_mb):
    plot_heatmap(setup_times_matrix, L_values, n_values, "L", "n", "Setup Time vs L and n (in s)", "plots/setup_time_heatmap.png", "seconds")
    plot_heatmap(aggregate_times_matrix, L_values, n_values, "L", "n", "Aggregate Time vs L and n (in s)", "plots/aggregate_time_heatmap.png", "seconds")
    plot_heatmap(enc_times_matrix, L_values, n_values, "L", "n", "Encryption Time vs L and n (in ms)", "plots/enc_time_heatmap.png", "miliseconds")
    plot_heatmap(dec_times_matrix, L_values, n_values, "L", "n", "Decryption Time vs L and n (in ms)", "plots/dec_time_heatmap.png", "miliseconds")
    plot_heatmap(sizes_crs_matrix_mb, L_values, n_values, "L", "n", "Size of CRS vs L and n (in MB)", "plots/size_crs_heatmap.png", "MB")
    plot_heatmap(sizes_mpk_matrix_mb, L_values, n_values, "L", "n", "Size of mpk vs L and n (in KB)", "plots/size_mpk_heatmap.png", "KB")
    plot_3d_chart(L_values, n_values, setup_times_matrix, "L", "n", "Time (s)", "Setup Time vs L and n", "plots/setup_time_3d.png")
    plot_3d_chart(L_values, n_values, aggregate_times_matrix, "L", "n", "Time (s)", "Aggregate Time vs L and n", "plots/aggregate_time_3d.png")
    plot_3d_chart(L_values, n_values, enc_times_matrix, "L", "n", "Time (ms)", "Encryption Time vs L and n", "plots/encryption_time_3d.png")
    plot_3d_chart(L_values, n_values, dec_times_matrix, "L", "n", "Time (ms)", "Decryption Time vs L and n", "plots/decryption_time_3d.png")
    plot_3d_chart(L_values, n_values, sizes_crs_matrix_mb, "L", "n", "Size (MB)", "Size of CRS vs L and n", "plots/size_crs_3d.png")
    plot_3d_chart(L_values, n_values, sizes_mpk_matrix_mb, "L", "n", "Size (KB)", "Size of MPK vs L and n", "plots/size_mpk_3d.png")


def initialize_matrices(L_values, n_values):
    setup_times_matrix = [[0 for _ in range(len(L_values))] for _ in range(len(n_values))]
    aggregate_times_matrix = [[0 for _ in range(len(L_values))] for _ in range(len(n_values))]
    enc_times_matrix = [[0 for _ in range(len(L_values))] for _ in range(len(n_values))]
    dec_times_matrix = [[0 for _ in range(len(L_values))] for _ in range(len(n_values))]
    sizes_crs_matrix = [[0 for _ in range(len(L_values))] for _ in range(len(n_values))]
    sizes_mpk_matrix = [[0 for _ in range(len(L_values))] for _ in range(len(n_values))]

    return setup_times_matrix, aggregate_times_matrix, enc_times_matrix, dec_times_matrix, sizes_crs_matrix, sizes_mpk_matrix


