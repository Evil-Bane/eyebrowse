"""Browser identity: an isolated profile dir for rotation.

A fresh identity = a fresh ``user_data_dir`` (purges cookies / localStorage / canvas seed),
paired with a fresh proxy IP and ``geoip=True`` for geo/timezone cohesion. CloakBrowser already
mints a **novel fingerprint per launch** (its ``--fingerprint`` seed), so identity only needs to
own the isolated storage — no manual OS/screen spoofing required.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass


@dataclass
class Identity:
    """A rotation identity: an isolated profile dir (cookies/storage are scoped to it)."""

    user_data_dir: str | None = None


def random_identity(
    *,
    profiles_dir: str = "profiles",
    with_profile: bool = True,
) -> Identity:
    """Generate a fresh identity.

    with_profile=True mints an isolated ``user_data_dir`` (for a *persistent* identity you can
    reuse). Ephemeral rotations leave it None — a new context already yields a novel fingerprint
    and empty storage.
    """
    user_data_dir = None
    if with_profile:
        os.makedirs(profiles_dir, exist_ok=True)
        user_data_dir = tempfile.mkdtemp(prefix="eb-", dir=profiles_dir)
    return Identity(user_data_dir=user_data_dir)
