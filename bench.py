import algos as algos
import utils as utils
import os
from petrelic.multiplicative.pairing import G1, G2, GT, G1Element, G2Element,GTElement, Bn

L = 1
n = 8

algos.setup(n, L)
crs = utils.load_crs(L)
algos.batchKeyGen("crs.db", n, L)
g1, g2, Z, h, Gamma, A, B, U,W = crs
pks = utils.load_public_keys("pks.db",L)
sks = utils.load_sk("sks.db", 0)
algos.aggregate("attributes.db", "pks.db", "crs.db", n, L)
mpk = utils.load_mpk("mpk.db")
hsk = utils.load_hsk("hsk.db",0)
sk = sks
y = [Bn(0)] * n
m = GT.generator()
ct = algos.Enc(mpk, y, m)
m_dec = algos.Dec(hsk, sk, ct)
print("Decrypted message: \t",m_dec)
print("Original message: \t",m)
print(ct[0])
print(ct[1])
print(ct[2])
print(ct[3])
os.remove("crs.db")
os.remove("pks.db")
os.remove("sks.db")
os.remove("attributes.db")
os.remove("hsk.db")
os.remove("mpk.db")
