from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock


if TYPE_CHECKING:
    from dmock._expectation import Expectation


class DeclarativeMock(Mock):
    """Declarative wrapper around unittest.mock.Mock with spec=."""

    def __init__(self, spec: type, /, **kwargs: object) -> None:
        super().__init__(spec=spec, **kwargs)

    def expect(self, name: str, /, *args: object, **kwargs: object) -> Expectation:
        raise NotImplementedError

    def assert_expectations(self) -> None: ...

    def _dispatch(self, name: str, /, *args: object, **kwargs: object) -> object: ...

    def __repr__(self) -> str:
        raise NotImplementedError
