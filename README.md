
# Simple PBFT implementation using Python

A rather simplistic implementation of the pBFT protocol using Python 3.8. It is helpful to analyze
and possibly optimize the algorithm, as well as use it for proof-of-concepts.

The repo is still a work in progress with tons of room for optimizations, but anyone wanting to help me improving it is welcome to contribute to it.

Unit tests:

```sh
python3 -m unittest test_util.py test_node.py test_network.py
```
## Prerequisites
Was tested with `Python 3.8.10`
Install `aiologger`: `pip install aiologger`

## Known bugs
* ResourceWarning: unclosed event loop

# TODO: 
* Move collection classes from `util.py` to `db.py`
* Trigger view change after every X requests; currently the primary is only changed when the faulty timer kicks in
* use tinyrpc or gRPC to make the application distributed.
* The Signature is just a shell for now. Decide when to use signature versus MAC for improved performance.
* Replace the collection classes with in-memory datatase, for better performance.
* 100% unit test coverage