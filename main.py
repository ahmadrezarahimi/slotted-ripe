from time import time

from petrelic.bn import Bn
from petrelic.multiplicative.pairing import G1, G2, GT, G1Element, G2Element,GTElement, Bn
from concurrent.futures import ThreadPoolExecutor
import sqlite3



def load_secret_keys(db_path='sks.db'):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute('SELECT i, value FROM secret_keys ORDER BY i')
    sks = [Bn.from_binary(row[1]) for row in cur.fetchall()]

    conn.close()

    return sks



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
L = 1
n = 1

start_time = time()
setup(n, L)
elapsed_time = time() - start_time
print("CRS setup time:", elapsed_time)
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
# L = 100
# n = 10
# start_time = time()
# setup(n, L)
# elapsed_time = time() - start_time
# print("CRS setup time:", elapsed_time)
#
# start_time = time()
# pk,sk = keyGen('crs.db', 0, n, L)
# elapsed_time = time() - start_time
# print("KeyGen time:", elapsed_time)
#
# start_time = time()
# batchKeyGen('crs.db', n, L)
# elapsed_time = time() - start_time
# print("BatchKeyGen time:", elapsed_time)
#
# start_time = time()
# aggregate("attributes.db", "pks.db", "crs.db", n, L)
# elapsed_time = time() - start_time
# print("Aggregate time:", elapsed_time)




