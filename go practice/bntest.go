package main

import (
	"fmt"
	bls12381 "github.com/consensys/gnark-crypto/ecc/bls12-381"
	"github.com/consensys/gnark-crypto/ecc/bls12-381/fr"
	"math/big"
)

func main() {
	fmt.Println("Order of G1 (order of Fr):", fr.Modulus())

	_, _, g1A, _ := bls12381.Generators()
	fmt.Println("Generator of G1:", g1A)
	g1AB := g1A.Bytes()
	fmt.Println("Bytes of the generator of G1:", g1AB)

	gtemp := bls12381.G1Affine{}
	err := gtemp.Unmarshal(g1AB[:]) // Convert [96]byte to []byte by slicing the array
	if err != nil {
		fmt.Println("Error unmarshaling G1:", err)
		return
	}
	fmt.Println(gtemp)
	fmt.Println("Length of G1 bytes:", len(g1AB))

	// Generate a random scalar.
	var randomScalar fr.Element
	randomScalar.SetRandom()
	fmt.Println(randomScalar)
	randomScalarBytes := randomScalar.Bytes()
	randomScalarBigInt := new(big.Int).SetBytes(randomScalarBytes[:])
	var g1temp bls12381.G1Affine
	g1temp.ScalarMultiplication(&g1A, randomScalarBigInt)
	fmt.Println(g1temp)
}
