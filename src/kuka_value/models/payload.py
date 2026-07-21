"""Payload domain models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Vector3D:
    """Three-dimensional vector for center of gravity and inertia."""

    x: float
    y: float
    z: float

    @classmethod
    def zero(cls) -> Vector3D:
        return cls(x=0.0, y=0.0, z=0.0)

    def is_zero(self) -> bool:
        return self.x == 0.0 and self.y == 0.0 and self.z == 0.0


@dataclass(frozen=True)
class Orientation:
    """A/B/C orientation angles (degrees) of the useful center of gravity."""

    a: float
    b: float
    c: float

    @classmethod
    def zero(cls) -> Orientation:
        return cls(a=0.0, b=0.0, c=0.0)

    def is_zero(self) -> bool:
        return self.a == 0.0 and self.b == 0.0 and self.c == 0.0


@dataclass
class Payload:
    """Extracted payload data from LOAD_DATA."""

    mass: float
    center_of_gravity: Vector3D
    inertia: Vector3D | None = None
    orientation: Orientation | None = None
    indices: list[int] = field(default_factory=list)
    source_file: str | None = None

    def is_empty(self) -> bool:
        return self.mass <= 0.0

    def same_payload(self, other: Payload) -> bool:
        """Check if two payloads have identical physical properties."""
        return (
            self.mass == other.mass
            and self.center_of_gravity == other.center_of_gravity
            and self.inertia == other.inertia
            and self.orientation == other.orientation
        )

    def merge_indices(self, other: Payload) -> Payload:
        """Create a new Payload combining indices from both."""
        return Payload(
            mass=self.mass,
            center_of_gravity=self.center_of_gravity,
            inertia=self.inertia,
            orientation=self.orientation,
            indices=self.indices + other.indices,
            source_file=self.source_file,
        )
