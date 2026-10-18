"""Static protocols for spec methods and properties."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, ParamSpec, Protocol, TypeAlias, TypeVar


if TYPE_CHECKING:
    from typing import Any


T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")
T_co = TypeVar("T_co", covariant=True)


class PropertyDescriptor(Protocol[T, R]):
    """Property whose instance type is `T` and whose value type is `R`.

    `getter` mentions `R` as a parameter so `R` stays invariant. A covariant
    `R` is solved as the union of the property type and the supplied value.
    """

    def __get__(self, instance: T, owner: type[T] | None = None, /) -> R:
        """Return the property value for `instance`."""
        ...

    def getter(self, fget: Callable[[T], R], /) -> object:
        """Return a copy of this property with getter `fget`."""
        ...


PropertyOf: TypeAlias = PropertyDescriptor[T, R] | Callable[[T], R]


class ClassOf(Protocol[T_co]):
    """Class object whose instances are `T_co`.

    `mro` is present on a class and absent on a function, so a function is not
    a spec. `__call__` parameters are `Any` so every constructor signature
    matches; `object` would reject a class whose parameters are not `object`.
    """

    __name__: str

    def mro(self) -> list[type]:
        """Return the method resolution order."""
        ...

    def __call__(self, *args: Any, **kwargs: Any) -> T_co:
        """Return an instance of this class."""
        ...
