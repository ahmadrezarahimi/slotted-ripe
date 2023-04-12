from math import ceil, sqrt, log2
from petrelic.multiplicative.pairing import G1, G2, GT, G1Element, G2Element, Bn
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor
from pathos.multiprocessing import Pool
from loky import get_reusable_executor
import threading

def generate_arrays(params, results):
    index, n, alpha, beta = params
    n1 = n + 1

    Ui = [G1.random() for _ in range(n1)]
    Uri = [G2.random() for _ in range(n1)]

    Ai = G1.random()
    Bi = G2.random()
    results[index] = (Ui, Uri, Ai, Bi)


def setup(n, L):
    alpha = Bn.random(G1.order())
    beta = Bn.random(G1.order())
    gamma = Bn.random(G1.order())

    g1 = G1.generator()
    g2 = G2.generator()
    Z = g1.pair(g2) ** alpha
    h = g1 ** beta
    Gamma = g1 ** gamma

    n1 = n + 1
    U = []
    A = []
    B = []
    W = []
    Ur = []

    executor = get_reusable_executor()
    results = list(executor.map(generate_arrays, [(i, n, alpha, beta) for i in range(L)]))

    for result in results:
        Ui, Uri, Ai, Bi = result
        U.append(Ui)
        Ur.append(Uri)
        A.append(Ai)
        B.append(Bi)

    for i in range(L):
        Wi = []
        for j in range(L):
            Wj = []
            if i != j:
                for w in range(n1):
                    Wj.append(A[i] ** (Ur[i][w] * gamma.mod_inverse(G1.order())))
            Wi.append(Wj)
        W.append(Wi)

    crs = (g1, g2, Z, h, Gamma, A, B, U, W)
    return crs



# ... (the rest of the algos.py file remains the same)





def keyGen(crs, i, L, n):
    g1, g2, Z, h, Gamma, A, B, U, W = crs
    order = G1.order()
    r = order.random()
    T = (U[i][-1] ** r) ** -1
    Wh = [W[i][j][-1] ** r for j in range(L) if j != i]

    pk = [T, Wh]
    x = [order.random() for _ in range(n)]

    return pk, x


def aggregate(crs, n, L, pks, xs):
    g1, g2, Z, h, Gamma, A, B, U, W = crs

    T = [
        pk[0] * product(U[i][w] ** (-1 * x) for w, x in enumerate(x_list))
        for i, (pk, x_list) in enumerate(zip(pks, xs))
    ]

    Wh = [
        [
            pk[1][i] * product(W[j][i][w] ** (-1 * x) for w, x in enumerate(xs[j if j < i else j + 1]))
            for i in range(L - 1)
        ]
        for j, pk in enumerate(pks)
    ]

def product(iterable):
    result = G1.neutral_element()
    for x in iterable:
        result *= x
    return result

