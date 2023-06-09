from petrelic.multiplicative.pairing import G1, G2, GT, G1Element, G2Element,GTElement, Bn
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import utils as utils

'''
setup():
    generates the CRS and stores it in the crs.db file
    n: number of attributes
    L: number of users
'''
def setup(n, L):
    g1 = G1.generator()
    g2 = G2.generator()

    order = G1.order()
    alpha = G1.order().random()
    beta = G1.order().random()
    gamma = G1.order().random()
    gamma_inv = gamma.mod_inverse(order)

    Z = g1.pair(g2) ** alpha
    h = g1 ** beta
    Gamma = g1 ** gamma
    n1 = n + 1

    Ur = [[Bn(1) for _ in range(n1)] for _ in range(L)]
    U = [[g1 ** uri for uri in ur] for ur in Ur]
    t = [Bn(1) for _ in range(L)]
    A = [g2 ** t[i] for i in range(L)]
    B = [g2 ** alpha * a ** beta for a in A]

    def compute_W(i, j):
        return [A[i] ** (ur * gamma_inv) for ur in Ur[j]]

    W = [[[None] * n1 for _ in range(L)] for _ in range(L)]

    with ThreadPoolExecutor() as executor:
        futures = {(i, j): executor.submit(compute_W, i, j) for i in range(L) for j in range(L) if i != j}

    for i in range(L):
        for j in range(L):
            if i != j:
                W[i][j] = futures[(i, j)].result()

    utils.store_crs(A, B, Gamma, U, W, Z, g1, g2, h)


'''
keyGen():
    generates the public and secret keys for a user
    crs_db_path: path to the crs.db file
    i: user id
    n: number of attributes
    L: number of users
'''
def keyGen(crs_db_path, i, n, L):
    r = G1.order().random()
    conn = sqlite3.connect(crs_db_path)
    cur = conn.cursor()

    # Load U1
    cur.execute('SELECT value FROM crs_U WHERE i = ? AND j = ?', (i, n))
    result = cur.fetchone()
    if result is not None:
        U1 = G1Element.from_binary(result[0])** (-r)
    else:
        raise ValueError(f"Data not found for i={i}, j={n} in crs_U")

    # Load Wh
    Wh = [None] * L
    for j in range(L):
        if j != i:
            cur.execute('SELECT value FROM crs_W WHERE i = ? AND j = ? AND k = ?', (j, i, n))
            result = cur.fetchone()
            if result is not None:
                Wh[j] = G2Element.from_binary(result[0])**r
            else:
                raise ValueError(f"Data not found for i={j}, j={i}, k={n} in crs_W")

    conn.close()
    pk = [U1, Wh]
    sk = r
    return pk,sk
'''
batchKeyGen():
    generates the public and secret keys for all users
    db_path: path to the crs.db file
    n: number of attributes
    L: number of users
'''
#TODO this function already samples random attributes for each user for the purpose of benchmarking, in real world we want to give our attributes directly to aggregate
def batchKeyGen(db_path, n, L):
    conn_crs = sqlite3.connect(db_path)

    conn_pks = sqlite3.connect('pks.db')
    cur_pks = conn_pks.cursor()

    def store_pk(cur_pks, pk, i):
        cur_pks.execute('INSERT OR REPLACE INTO public_keys_U1 (i, U1) VALUES (?, ?)', (i, pk[0].to_binary()))

        for j, wh in enumerate(pk[1]):
            if wh is not None:
                cur_pks.execute('INSERT OR REPLACE INTO public_keys_Wh (i, j, Wh) VALUES (?, ?, ?)',
                                (i, j, wh.to_binary()))

    cur_pks.execute('''CREATE TABLE IF NOT EXISTS public_keys_U1 (i INTEGER PRIMARY KEY, U1 BLOB)''')
    cur_pks.execute('''CREATE TABLE IF NOT EXISTS public_keys_Wh (i INTEGER, j INTEGER, Wh BLOB, PRIMARY KEY (i, j))''')

    conn_sks = sqlite3.connect('sks.db')
    cur_sks = conn_sks.cursor()
    cur_sks.execute('''CREATE TABLE IF NOT EXISTS secret_keys (i INTEGER PRIMARY KEY, sk BLOB)''')

    conn_attr = sqlite3.connect('attributes.db')
    cur_attr = conn_attr.cursor()
    cur_attr.execute('''CREATE TABLE IF NOT EXISTS attributes (i INTEGER, j INTEGER, value BLOB, PRIMARY KEY (i, j))''')

    for i in range(L):
        pk, sk = keyGen(db_path, i, n, L)
        store_pk(cur_pks, pk, i)
        cur_sks.execute('INSERT OR REPLACE INTO secret_keys (i, sk) VALUES (?, ?)', (i, sk.binary()))
        attr = [G1.order().random() for _ in range(n)]

        for j, value in enumerate(attr):
            cur_attr.execute('INSERT OR REPLACE INTO attributes (i, j, value) VALUES (?, ?, ?)', (i, j, value.binary()))


    conn_crs.close()
    conn_pks.commit()
    conn_pks.close()
    conn_sks.commit()
    conn_sks.close()
    conn_attr.commit()
    conn_attr.close()


def fuse_u(pks, U, X, i, n):
    for j in range(n):
        pks[i][0] = pks[i][0] * (U[i][j] ** -X[i][j])
    return pks[i][0]

def fuse_w(pks, W, X, i, L, n):
    result = [None] * L
    for j in range(L):
        if j != i:
            result[j] = pks[i][1][j]
            for k in range(n):
                result[j] = result[j] * (W[i][j][k] ** X[i][k])
    return result

def compute_uhat(U, w, L):
    result = G1.neutral_element()
    for i in range(L):
        result = result * U[i][w]
    return result

def compute_what(W, i, w, L):
    result = G2.neutral_element()
    for j in range(L):
        if i != j:
            result = result * W[i][j][w]
    return result
'''
aggregate():
    aggregates the public keys of all users
    attributes_db_path: path to the attributes.db file
    pks_db_path: path to the pks.db file
    crs_db_path: path to the crs.db file
    n: number of attributes
    L: number of users
'''
def aggregate(attributes_db_path, pks_db_path, crs_db_path, n, L):
    # Load attributes
    X = utils.load_attributes(attributes_db_path, n,L)

    # Load public keys
    pks = utils.load_public_keys(pks_db_path, L)

    # Load CRS
    g1, g2, Z, h, Gamma, A, B, U,W = utils.load_crs(L,crs_db_path)
    with ThreadPoolExecutor() as executor:
        # Fuse U
        u_futures = [executor.submit(fuse_u, pks, U, X, i, n) for i in range(L)]
        u_results = [future.result() for future in u_futures]

        # Fuse W
        w_futures = [executor.submit(fuse_w, pks, W, X, i, L, n) for i in range(L)]
        w_results = [future.result() for future in w_futures]

    for i in range(L):
        pks[i][0] = u_results[i]
        for j in range(L):
            if j != i:
                pks[i][1][j] = w_results[i][j]

        # Compute Uhat
    Uhat = [None] * (n + 2)
    for w in range(n + 1):
        Uhat[w] = compute_uhat(U, w, L)

    # Compute the last element of Uhat
    Uhat[n + 1] = G1.neutral_element()
    for i in range(L):
        Uhat[n + 1] = Uhat[n + 1] * pks[i][0]

    # Compute What
    What = [[None] * (n + 2) for _ in range(L)]
    for i in range(L):
        for w in range(n + 1):
            What[i][w] = compute_what(W, i, w, L)

    # Compute the last element of What
    for i in range(L):
        What[i][n + 1] = G2.neutral_element()
        for j in range(L):
            if i != j:
                What[i][n + 1] = What[i][n + 1] * pks[j][1][i]
        What[i][n + 1] = What[i][n + 1] ** -1

    hsk = [(g1, g2, i, X[i], A[i], B[i], What[i]) for i in range(L)]

    # Store the master public key and the helping secret key
    utils.store_hsk('hsk.db', hsk)
    utils.store_mpk(g1, g2, h, Z, Gamma, Uhat)



'''
Enc():
    encrypts a message m for a set of attributes y
    mpk: master public key
    y: set of attributes
    m: message
'''
def Enc(mpk, y, m):
    g1, g2, h, Z, Gamma, Uhat = mpk
    n = len(y)

    # Generate random values
    s = G1.order().random()
    r = G1.order().random()
    z = G1.order().random()

    # Compute ct[0], ct[1], and ct[3]
    ct0 = m * Z ** s
    ct1 = g1 ** s
    ct3 = Gamma ** z

    # Compute ct[2] as a list of size n+2
    y1 = y + [Bn(0), Bn(0)]

    ct2 = [None] * (n+2)
    for w in range(n+2):
        t = y1[w].mod_mul(r,G1.order())
        t = t.mod_add(s,G1.order())
        ct2[w] = (h ** t) * Uhat[w] ** (-1*z)

    ct = [ct0, ct1, ct2, ct3]
    return ct



'''
Dec():
    decrypts a ciphertext ct
    hsk: helping secret key
    sk: secret key
    ct: ciphertext
'''
def Dec(hsk, sk, ct):
    g1, g2, i, X, A, B, What = hsk
    ct0, ct1, ct2, ct3 = ct

    X1 = X + [sk, Bn(1)]
    Xbar = Bn(0)
    n2 = len(X) + 2
    for i in range(n2):
        Xbar = Xbar.mod_add(X1[i], G1.order())

    pairing1 = ct1.pair(B)
    pairing2 = GT.neutral_element()
    for w in range(n2):
        pairing2 *= (ct2[w] ** X1[w]).pair(A)
    pairing3 = GT.neutral_element()
    for w in range(n2):
        pairing3 *= ct3.pair(What[w]**X1[w])
    Xbarinv = Xbar.mod_inverse(G1.order())
    m = ct0 * (pairing1**-1) * ((pairing2 * pairing3) ** (Xbarinv))

    return m