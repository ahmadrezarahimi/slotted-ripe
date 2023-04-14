# Slotted Ripe

This is an implementation of the Slotted Ripe cryptographic scheme using the BLS12-381 curve. The code leverages the [Petrelic](https://github.com/asonnino/petrelic) library, which provides a Python interface for working with elliptic curve pairings and cryptographic primitives.

**Important Note:** This implementation is a draft and should not be used in any real-world applications. There is no security guarantee.

## Petrelic Library

The Petrelic library provides a Python interface for working with elliptic curve pairings, supporting several well-known curves, including the BLS12-381 curve used in this implementation.

### Installation on Ubuntu

To install the Petrelic library on Ubuntu, follow these steps:

1. Install the required dependencies:

sudo apt-get update
sudo apt-get install -y libgmp-dev libsodium-dev libssl-dev


2. Install the Petrelic library using pip:

pip install petrelic


## Usage

Run benchmarks.py
