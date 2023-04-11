from algos import *
from time import time


L = 100
n = 10
# CRS gen time
s = time()
crs = setup(n,L)
e = time()
print("CRS gen time:",e-s)
s = time()
pks = []
xs = []
for i in range(L):
    pk,x = keyGen(crs,i,L,n)
    pks.append(pk)
    xs.append(x)
e = time()
print("KeyGen time:",e-s)

# print(pks[0][1][8])

s = time()
aggregate(crs,n,L,pks,xs)
e = time()
print("Agg time:",e-s)

