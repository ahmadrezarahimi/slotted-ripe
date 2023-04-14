import algos as algos
import utils as utils
import os
from petrelic.multiplicative.pairing import GT, Bn

L = 10
n = 10

algos.setup(n, L)
crs = utils.load_crs(L)
algos.batchKeyGen("crs.db", n, L)
g1, g2, Z, h, Gamma, A, B, U,W = crs
gt = g1.pair(g2)
pks = utils.load_public_keys("pks.db",L)
sks = utils.load_sk("sks.db", 0)
algos.aggregate("attributes.db", "pks.db", "crs.db", n, L)
mpk = utils.load_mpk("mpk.db")
hsk = utils.load_hsk("hsk.db",0)

sk = sks
y = [Bn(0)] * n
m = GT.generator()**GT.order().random()
ct = algos.Enc(mpk, y, m)
m_dec = algos.Dec(hsk, sk, ct)
assert(m == m_dec)
