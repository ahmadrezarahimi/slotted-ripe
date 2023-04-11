from math import ceil,sqrt,log2
from petrelic.multiplicative.pairing import G1,G2,GT,G1Element,G2Element,Bn

def setup(n,L):

    g1 = G1.generator()
    g2 = G2.generator()

    alpha = G1.order().random()
    beta = G1.order().random()
    gamma = G1.order().random()

    Z = g1.pair(g2)**alpha
    h = g1 ** beta
    Gamma = g1 ** gamma
    n1 = n+1
    U = []
    A = []
    B = []
    W = []
    Ur = []
    for i in range(L):
        Ui = []
        Uri = []
        for w in range(n1):
            Uri.append(G1.order().random())
            Ui.append(g1 ** Uri[-1])
        Ur.append(Uri)
        U.append(Ui)
        t = G2.order().random()
        Ai = g2 ** t
        A.append(Ai)
        B.append(g2**alpha * Ai**beta)

    for i in range(L):
        Wi = []
        for j in range(L):
            Wj = []
            if i != j:
                for w in range(n1):
                    Wj.append(A[i] ** (Ur[i][w] * gamma.mod_pow(-1,G1.order())))
            Wi.append(Wj)
        W.append(Wi)
    crs = (g1,g2,Z,h,Gamma,A,B,U,W)
    return crs
def keyGen(crs,i,L,n):
    #parse crs
    g1,g2,Z,h,Gamma,A,B,U,W = crs
    r = G1.order().random()
    T = (U[i][-1] ** r) ** -1
    Wh = []
    for j in range(L):
        if j!= i:
            Wh.append(W[i][j][-1]**r)
    pk = [T,Wh]
    x = []
    for i in range(n):
        x.append(G1.order().random())
    return pk,x

def aggregate(crs,n,L,pks,xs):
    g1, g2, Z, h, Gamma, A, B, U, W = crs
    T = []
    Wh = []
    for i in range(L):
        Ti = pks[i][0]
        for w in range(n):
            Ti *= U[i][w]** (-1 * xs[i][w])
        T.append(Ti)
    for j in range(L-1):
        Whj = []
        for i in range(L-1):
            Whi = pks[j][1][i]
            if i != j:
                for w in range(n):
                    # TODO the pow is wrong, -1 must be added
                    Whi*= W[j][i][w]** (-1*xs[i][w])
            Whj.append(Whi)
        Wh.append(Whj)

