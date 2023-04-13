import algos as algos
import utils as utils
import os
from petrelic.multiplicative.pairing import G1, G2, GT, G1Element, G2Element,GTElement, Bn

L = 1
n = 9

beta,t = algos.setup(n, L)
crs = utils.load_crs(L)
algos.batchKeyGen("crs.db", n, L)
g1, g2, Z, h, Gamma, A, B, U,W = crs
gt = g1.pair(g2)
pks = utils.load_public_keys("pks.db",L)
sks = utils.load_sk("sks.db", 0)
algos.aggregate("attributes.db", "pks.db", "crs.db", n, L)
mpk = utils.load_mpk("mpk.db")
hsk = utils.load_hsk("hsk.db",0)
X = hsk[3]
X1 = X + [sks,Bn(1)]
X1s = Bn(0)
for i in range(len(X1)):
    X1s = X1s.mod_add(X1[i],G1.order())
print(X1s)


sk = sks
y = [Bn(0)] * n
y1 = y + [Bn(0), Bn(0)]
xys = Bn(0)
for i in range(len(y1)):
    xys = xys.mod_add(X1[i].mod_mul(y1[i],G1.order()),G1.order())
print("inner product is: \t\t",xys)
m = GT.generator()
ct,s = algos.Enc(mpk, y, m)
m_dec = algos.Dec(hsk, sk, ct)


pairing1 = ct[1].pair(B[0])
m2= ct[0] * (pairing1**-1)

print("Computed message: \t\t",m2)
print("Computed paiding prod: \t",gt**(s*X1s*beta*t[0]))
print("Decrypted message: \t\t",m_dec)
print("Original message: \t\t",m)
os.remove("crs.db")
os.remove("pks.db")
os.remove("sks.db")
os.remove("attributes.db")
os.remove("hsk.db")
os.remove("mpk.db")
