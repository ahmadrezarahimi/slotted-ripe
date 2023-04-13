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


def keyGen(db_path, i, n, L):
    r = G1.order().random()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Load U1
    cur.execute('SELECT value FROM crs_U WHERE i = ? AND j = ?', (i, n))
    result = cur.fetchone()
    rinv = r.mod_inverse(G1.order())
    if result is not None:
        U1 = G1Element.from_binary(result[0]) ** rinv
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


def load_secret_keys(db_path='sks.db'):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute('SELECT i, value FROM secret_keys ORDER BY i')
    sks = [Bn.from_binary(row[1]) for row in cur.fetchall()]

    conn.close()

    return sks
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


def aggregate(attributes_db_path, pks_db_path, crs_db_path, n, L):
    # Load attributes
    X = load_attributes(attributes_db_path, n,L)

    # Load public keys
    pks = load_public_keys(pks_db_path, L)

    # Load CRS
    g1, g2, Z, h, Gamma, A, B, U,W = load_crs(crs_db_path)

    # fuse attributes into the public keys
    #the U part
    for i in range(L):
        for j in range(n):
            pks[i][0] = pks[i][0] * (U[i][j] ** X[i][j].mod_inverse(G1.order()))
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
        Uhat[n] = Uhat[n] * pks[i][0]
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
        What[i][n+1] = What[i][n+1] ** -1
    # Here we compute masterpublic key
    mpk = (g1,g2,h,Z,Gamma,Uhat)
    # We create an array of helping secret keys, we call it hsk and we define it as follows:
    # hsk[i] = (g1,g2,i,A[i],B[i],What[i])
    # We create an array of helping secret keys, we call it hsk and we define it as follows:
    # hsk[i] = (g1,g2,i,X[i],A[i],B[i],What[i]) for each i in [0,L]
    hsk = [(g1, g2, i, X[i], A[i], B[i], What[i]) for i in range(L)]

    store_hsk('hsk.db', hsk)
    # store_hsk(hsk, 'hsk.db')
    with sqlite3.connect('mpk.db') as conn_mpk:
        cur_mpk = conn_mpk.cursor()
        cur_mpk.execute('CREATE TABLE IF NOT EXISTS master_public_key (name TEXT PRIMARY KEY, value BLOB)')
        conn_mpk.commit()
        cur_mpk.execute("INSERT OR REPLACE INTO master_public_key (name, value) VALUES ('g1', ?)", (g1.to_binary(),))
        cur_mpk.execute("INSERT OR REPLACE INTO master_public_key (name, value) VALUES ('g2', ?)", (g2.to_binary(),))
        cur_mpk.execute("INSERT OR REPLACE INTO master_public_key (name, value) VALUES ('h', ?)", (h.to_binary(),))
        cur_mpk.execute("INSERT OR REPLACE INTO master_public_key (name, value) VALUES ('Z', ?)", (Z.to_binary(),))
        cur_mpk.execute("INSERT OR REPLACE INTO master_public_key (name, value) VALUES ('Gamma', ?)",
                        (Gamma.to_binary(),))
        cur_mpk.executemany("INSERT OR REPLACE INTO master_public_key (name, value) VALUES (?, ?)",
                            [('Uhat_' + str(i), elem.to_binary()) for i, elem in enumerate(Uhat)])
        conn_mpk.commit()

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

def load_mpk(mpk_db_path):
    with sqlite3.connect(mpk_db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT g1, g2, h, Z, Gamma, Uhat FROM mpk WHERE id = ?", (0,))
        result = cur.fetchone()
        if result is not None:
            g1, g2, h, Z, Gamma, Uhat_binary = result
            Uhat = [G1Element.from_binary(element) for element in Uhat_binary]
            return G1Element.from_binary(g1), G2Element.from_binary(g2), G1Element.from_binary(h), G2Element.from_binary(Z), G1Element.from_binary(Gamma), Uhat
        else:
            raise ValueError("Data not found in mpk")

def load_mpk(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT value FROM master_public_key WHERE name='g1'")
    g1 = G1Element.from_binary(cur.fetchone()[0])

    cur.execute("SELECT value FROM master_public_key WHERE name='g2'")
    g2 = G2Element.from_binary(cur.fetchone()[0])

    cur.execute("SELECT value FROM master_public_key WHERE name='h'")
    h = G1Element.from_binary(cur.fetchone()[0])

    cur.execute("SELECT value FROM master_public_key WHERE name='Z'")
    Z = GTElement.from_binary(cur.fetchone()[0])

    cur.execute("SELECT value FROM master_public_key WHERE name='Gamma'")
    Gamma = G1Element.from_binary(cur.fetchone()[0])

    cur.execute("SELECT name, value FROM master_public_key WHERE name LIKE 'Uhat_%' ORDER BY name")
    Uhat_rows = cur.fetchall()
    Uhat = [G1Element.from_binary(row[1]) for row in Uhat_rows]

    conn.close()
    return g1, g2, h, Z, Gamma, Uhat


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
    zinv = z.mod_inverse(G1.order())
    for w in range(n+2):
        ct2[w] = h ** (y1[w].mod_mul(r,G1.order()).mod_add(s,G1.order())) * Uhat[w] ** (zinv)

    ct = [ct0, ct1, ct2, ct3]
    return ct

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


def Dec(hsk, sk, ct):
    g1, g2, i, X, A, B, What = hsk
    ct0, ct1, ct2, ct3 = ct

    X1 = X + [sk, Bn(1)]
    Xbar = Bn(0)
    for i in range(len(X1)):
        Xbar = Xbar.mod_add(X1[i], G1.order())
    n2 = len(X)+2
    pairing1 = ct1.pair(B)
    pairing2 = GT.neutral_element()
    for w in range(n2):
        pairing2 *= (ct2[w] ** X1[w]).pair(A)
    pairing3 = GT.neutral_element()
    for w in range(n2):
        pairing3 *= ct3.pair(What[w]**X1[w])
    Xbarinv = Xbar.mod_inverse(G1.order())
    m = ct0 * (pairing1**-1) * (pairing2 * pairing3) ** (Xbarinv)

    return m
# L = 1
# n = 1
#
# # start_time = time()
# # setup(n, L)
# # elapsed_time = time() - start_time
# # print("CRS setup time:", elapsed_time)
# # pk,sk = keyGen('crs.db', 0, n, L)
# # batchKeyGen('crs.db', n, L)
# # aggregate("attributes.db", "pks.db", "crs.db", n, L)
# hsk = load_hsk("hsk.db", 0)
# mpk = load_mpk("mpk.db")
# sk = load_sk("sks.db", 0)
# X  = load_attributes("attributes.db",n,L)
# print(X)
# # print(hsk)
# # # print(sk)
# # #
# y = [Bn(0)]
# m = GT.generator()
# ct = Enc(mpk, y, m)
# m_dec = Dec(hsk, sk, ct)
# print(m_dec)
# print(m)
#
# a = G1.generator()
# b = G2.generator()
# c = G1.order().random()
# cinv = c.mod_inverse(G1.order())
# print(c.mod_mul(cinv,G1.order()))
# m2 = GT.neutral_element()
# print(G1.neutral_element())

#time the running time of algorithms setup, batchkeygen, aggregate and enc and dec for L=100 and n = 10
L = 100
n = 10
start_time = time()
setup(n, L)
elapsed_time = time() - start_time
print("CRS setup time:", elapsed_time)

start_time = time()
pk,sk = keyGen('crs.db', 0, n, L)
elapsed_time = time() - start_time
print("KeyGen time:", elapsed_time)

start_time = time()
batchKeyGen('crs.db', n, L)
elapsed_time = time() - start_time
print("BatchKeyGen time:", elapsed_time)

start_time = time()
aggregate("attributes.db", "pks.db", "crs.db", n, L)
elapsed_time = time() - start_time
print("Aggregate time:", elapsed_time)




