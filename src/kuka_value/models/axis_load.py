"""Supplementary per-axis load domain model."""

from __future__ import annotations

from dataclasses import dataclass

from kuka_value.models.payload import Vector3D


@dataclass(frozen=True)
class AxisLoad:
    """Supplementary load declared on a specific robot axis.

    Distinct from the primary flange payload(s) in LOAD_DATA[n]:
    KUKA robots can carry additional loads mounted on individual axes
    (commonly A3, for balancing), declared once per axis as
    DECL LOAD LOAD_A<n>_DATA={M ..., CM {...}, J {...}} - no array
    index, since there's exactly one declaration per axis.
    """

    axis: int
    mass: float
    center_of_gravity: Vector3D
    inertia: Vector3D | None = None
    source_file: str | None = None

    def is_empty(self) -> bool:
        return self.mass <= 0.0
