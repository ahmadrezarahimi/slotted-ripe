from petrelic.multiplicative.pairing import G1, G2, GT, G1Element, G2Element,GTElement, Bn
from concurrent.futures import ThreadPoolExecutor
import sqlite3

import utils as utils


def setup(n, L):
    g1 = G1.generator()
    g2 = G2.generator()

    order = G1.order()
    alpha = order.random()
    beta = order.random()
    gamma: Bn = order.random()
    gamma_inv = gamma.mod_inverse(order)

    Z = g1.pair(g2) ** alpha
    h = g1 ** beta
    Gamma = g1 ** gamma
    n1 = n + 1

    Ur = [[order.random() for _ in range(n1)] for _ in range(L)]
    U = [[g1 ** uri for uri in ur] for ur in Ur]
    t = [order.random() for _ in range(L)]
    A = [g2 ** t[i] for i in range(L)]
    B = [g2**alpha * a ** beta for a in A]

    def compute_W(i, j):
        return [a ** (ur * gamma_inv) for a, ur in zip(A, Ur[i])]

    with ThreadPoolExecutor() as executor:
        W = [[executor.submit(compute_W, i, j) if i != j else [] for j in range(L)] for i in range(L)]

    for i in range(L):
        for j in range(L):
            if i != j:
                W[i][j] = W[i][j].result()
    utils.store_crs(A, B, Gamma, U, W, Z, g1, g2, h)

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

def aggregate(attributes_db_path, pks_db_path, crs_db_path, n, L):
    # Load attributes
    X = utils.load_attributes(attributes_db_path, n,L)

    # Load public keys
    pks = utils.load_public_keys(pks_db_path, L)

    # Load CRS
    g1, g2, Z, h, Gamma, A, B, U,W = utils.load_crs(L,crs_db_path)

    # fuse attributes into the public keys
    #the U part
    for i in range(L):
        for j in range(n):
            pks[i][0] = pks[i][0] * (U[i][j] ** -X[i][j])
    #the W part
    for i in range(L):
        for j in range(L):
            if j != i:
                for k in range(n):
                    pks[i][1][j] = pks[i][1][j] * (W[i][j][k] ** X[i][k])
    # for each w in [0,n] we compute Uhat[w] as product of all U[i][w] for i in [0,L]
    Uhat = [None] * (n+2)
    for w in range(n+1):
        Uhat[w] = G1.neutral_element()
        for i in range(L):
            Uhat[w] = Uhat[w] * U[i][w]
    # and last elemet of uhat is the product of all psk[i][0] for i in [0,L]
    Uhat[n+1] = G1.neutral_element()
    for i in range(L):
        Uhat[n+1] = Uhat[n+1] * pks[i][0]
    # We define What the same way as Uhat, where for each i in [0,L] and for each w in [0,n] we compute What[i][w] as product of all W[i][j][w] for j in [0,L] and i!=j
    What = [[None] * (n+2) for _ in range(L)]
    for i in range(L):
        for w in range(n+1):
            What[i][w] = G2.neutral_element()
            for j in range(L):
                if i != j:
                    What[i][w] = What[i][w] * W[i][j][w]
        What[i][n+1] = G2.neutral_element()
        for j in range(L):
            if i != j:
                What[i][n+1] = What[i][n+1] * pks[j][1][i]
        What[i][n+1] = What[i][n+1]**-1


    # We create an array of helping secret keys, we call it hsk and we define it as follows:
    # hsk[i] = (g1,g2,i,A[i],B[i],What[i])
    # We create an array of helping secret keys, we call it hsk and we define it as follows:
    # hsk[i] = (g1,g2,i,X[i],A[i],B[i],What[i]) for each i in [0,L]
    hsk = [(g1, g2, i, X[i], A[i], B[i], What[i]) for i in range(L)]
    utils.store_hsk('hsk.db', hsk)
    utils.store_mpk(g1, g2, h, Z, Gamma, Uhat)


def Enc(mpk, y, m):
    g1, g2, h, Z, Gamma, Uhat = mpk
    n = len(y)

    # Sample randomness s, r, and z
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
    print("Pairing product is \t",(pairing2 * pairing3) ** (Xbarinv))
    m = ct0 * (pairing1**-1) * ((pairing2 * pairing3) ** (Xbarinv))

    return m