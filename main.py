from time import time
from petrelic.multiplicative.pairing import G1, G2, GT, G1Element, G2Element,GTElement, Bn
from concurrent.futures import ThreadPoolExecutor
import sqlite3

def setup(n, L):
    g1 = G1.generator()
    g2 = G2.generator()

    order = G1.order()
    alpha = order.random()
    beta = order.random()
    gamma = order.random()
    gamma_inv = gamma.mod_inverse(order)

    Z = g1.pair(g2) ** alpha
    h = g1 ** beta
    Gamma = g1 ** gamma
    n1 = n + 1

    Ur = [[order.random() for _ in range(n1)] for _ in range(L)]
    U = [[g1 ** uri for uri in ur] for ur in Ur]

    A = [g2 ** order.random() for _ in range(L)]
    alpha_beta = alpha * beta
    B = [a ** alpha_beta for a in A]

    def compute_W(i, j):
        return [a ** (ur * gamma_inv) for a, ur in zip(A, Ur[i])]

    with ThreadPoolExecutor() as executor:
        W = [[executor.submit(compute_W, i, j) if i != j else [] for j in range(L)] for i in range(L)]

    for i in range(L):
        for j in range(L):
            if i != j:
                W[i][j] = W[i][j].result()

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
            for k, w in enumerate(col):
                cur.execute('INSERT OR REPLACE INTO crs_W (i, j, k, value) VALUES (?, ?, ?, ?)', (i, j, k, w.to_binary()))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()


def load_crs(db_path='crs.db'):
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
        if i!=j:
            W[i][j].append(G2Element.from_binary(value))

    conn.close()

    crs = g1, g2, Z, h, Gamma, A, B, U,W
    return crs


L = 100
n = 10

start_time = time()
setup(n, L)
g1, g2, Z, h, Gamma, A, B, U,W = load_crs("crs.db")
elapsed_time = time() - start_time
print("CRS gen time:", elapsed_time)

print(W[0][0])
