"""Deterministic randomness.

Every random draw in this project comes from here. Nothing calls `random.` or
`np.random.` directly, so that the same seed always produces byte-identical output.
"""
from __future__ import annotations

import hashlib

import numpy as np


class SeedFactory:
    """Hands out one independent generator per named stream.

    Streams are derived from (seed, name) by hashing, so the generator for
    "orders" is the same whether or not "customers" was drawn from first.
    That independence is what makes partial regeneration reproducible.
    """

    def __init__(self, seed: int) -> None:
        self.seed = int(seed)
        self._cache: dict[str, np.random.Generator] = {}

    def stream(self, name: str) -> np.random.Generator:
        if name not in self._cache:
            digest = hashlib.sha256(f"{self.seed}:{name}".encode()).digest()
            derived = int.from_bytes(digest[:8], "big")
            self._cache[name] = np.random.default_rng(derived)
        return self._cache[name]

    def reset(self) -> None:
        self._cache.clear()
