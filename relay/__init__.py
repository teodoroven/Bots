"""
Открывает публичный namespace прикладного слоя `relay`.
"""

from __future__ import annotations

from . import public as _public

__all__: list[str] = list(_public.__all__)

for _name in __all__:
    globals()[_name] = getattr(_public, _name)

del _name
del _public
