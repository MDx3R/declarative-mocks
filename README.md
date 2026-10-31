![Checks](https://github.com/MDx3R/declarative-mocks/actions/workflows/ci.yml/badge.svg)
![PyPI](https://img.shields.io/pypi/v/declarative-mocks.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

# declarative-mocks

**Declare mock behavior as ordered expectations**. Write readable and maintainable tests with explicit call patterns, return sequences, and side effects using **dmock**.

It is fully documented. Public methods and matchers ship with docstring examples, and pretty much everything about API and behavior is described in [REFERENCE.md](REFERENCE.md) and [SPEC.md](SPEC.md).

## Installation

```bash
pip install declarative-mocks
```

_dmock_ requires Python 3.11+.

## Usage

Normally you would set a return value, then check the object field by field and assert the call separately:

```python
from dataclasses import dataclass, field
from datetime import datetime
from unittest.mock import Mock

@dataclass
class User:
    id: int
    name: str
    email: str
    created_at: datetime = field(default_factory=datetime.now)

class Directory:
    def lookup(self, name: str) -> User: ...

service = Mock(spec=Directory)
service.lookup.return_value = User(id=1, name="Ada", email="ada@example.com")

user = service.lookup("ada")
assert isinstance(user.id, int)
assert user.name.startswith("A")
assert "@" in user.email
assert abs((datetime.now() - user.created_at).total_seconds()) < 5
service.lookup.assert_called_once_with("ada")
```

Here's an example of how **dmock** improves your tests:

```python
from dmock import AnythingOfType, Contains, DeclarativeMock, IsNow, StartsWith

service = DeclarativeMock(Directory)
service.expect(Directory.lookup, StartsWith("a")).returns(
    User(id=1, name="Ada", email="ada@example.com")
)

assert service.lookup("ada") == User(
    id=1,
    name="Ada",
    email="ada@example.com",
    created_at=IsNow(),
)

# verify is automatic with pytest
service.verify()
```

That's not all! **dmock** can do so much more than that, for example:

Successive outcomes apply to the next matching call, in order:

```python
from dmock import DeclarativeMock

api = DeclarativeMock(ApiClient)
# Using `ApiClient.next_page` helps a type checker to check
# the `expect` arguments and the values passed to `.returns` and `.runs`
api.expect(ApiClient.next_page).returns({"items": [1], "cursor": "a"})
# or you could use the string form to produce a lenient expectation: any arguments, any outcome
api.expect("next_page").returns({"items": [2], "cursor": None})
# first call → first dict; second call → second dict

calc = DeclarativeMock(Calculator)
calc.expect("price", 100).runs(lambda x: x - 1).returns(99)
assert calc.price(100) == 99  # from the lambda
assert calc.price(100) == 99  # from .returns(99)
```

`expect(...)` with no further arguments matches a call with no arguments. A keyword matches only that keyword:

```python
from dmock import Anything, DeclarativeMock

m = DeclarativeMock(Worker)
m.expect("run")  # called with no arguments
m.expect("run", Anything()).returns(0)  # any single positional arg
m.expect("run", job_id=123).returns("queued")  # this is keyword only
```

`ANY_ARGS` and `ANY_KWARGS` match any positional and keyword arguments, including none:

```python
from dmock import ANY_ARGS, ANY_KWARGS, DeclarativeMock

m = DeclarativeMock(Worker)
m.expect("run", ANY_ARGS, ANY_KWARGS).returns(0)  # any positional and keyword args, including none
```

Only one quantifier per expectation is allowed. The last outcome repeats when the count allows more calls, and `verify()` checks the counts:

```python
from dmock import DeclarativeMock

calc = DeclarativeMock(Calculator)
calc.expect("price", 100).returns(99).once()
assert calc.price(100) == 99

calc.expect("price", 200).returns(99).times(3)  # last outcome repeats for the extra calls
assert [calc.price(200) for _ in range(3)] == [99, 99, 99]

calc.expect("price", 300).returns(99).between(1, 3)
assert calc.price(300) == 99

calc.expect("price", 400).never()
calc.verify()
```

Async methods use the same DSL. `runs()` accepts a sync or an async function:

```python
from dmock import Anything, DeclarativeMock

mock = DeclarativeMock(MyService)
mock.expect(MyService.aprocess_order, Anything()).returns("ok")
assert await mock.aprocess_order(1) == "ok"

mock.expect(MyService.aprocess_order, Anything()).runs(lambda order_id: f"sync-{order_id}")
assert await mock.aprocess_order(7) == "sync-7"

async def async_fn(order_id: int) -> str:
    return f"async-{order_id}"

mock.expect(MyService.aprocess_order, Anything()).runs(async_fn)
assert await mock.aprocess_order(9) == "async-9"
```

The matcher set is rich enough that even the most complicated call stays as **one declarative expectation**. Prefixes, partial mappings, lengths, order, and formats compose in place:

```python
from dmock import (
    AnyOrder,
    DeclarativeMock,
    Equals,
    GreaterThan,
    HasLen,
    IsUUID,
    PartialMapping,
    StartsWith,
)

class EventBus:
    def publish(self, *, topic: str, headers: dict, payload: dict) -> bool: ...

bus = DeclarativeMock(EventBus)
bus.expect(
    "publish",
    topic=StartsWith("orders.events."),
    headers=PartialMapping(
        {
            "x-correlation-id": IsUUID(),
            "x-origin-service": Equals("checkout-service"),
        }
    ),
    payload=PartialMapping(
        {
            "order_id": GreaterThan(0),
            "items": HasLen(GreaterThan(0))
            & AnyOrder(
                [
                    PartialMapping({"sku": "SKU-AAA", "qty": 1}),
                    PartialMapping({"sku": "SKU-BBB", "qty": 2}),
                ]
            ),
        }
    ),
).returns(True)

assert bus.publish(
    topic="orders.events.completed",
    headers={
        "x-correlation-id": "12345678-1234-4234-8234-123456789abc",
        "x-origin-service": "checkout-service",
        "x-extra": "ignored",
    },
    payload={
        "order_id": 884,
        "items": [
            {"sku": "SKU-BBB", "qty": 2, "note": "second"},
            {"sku": "SKU-AAA", "qty": 1},
        ],
        "currency": "USD",
    },
)

bus.verify()
```

**dmock** is built on `unittest.mock`, has zero runtime dependencies, and doesn't patch anything. Unregistered calls fail immediately. Nothing on live modules or instances is rewritten.

Look up the dmock source code and tests yourself, it's full of examples!

## Limitations & non-goals

- **No signature binding at runtime.** `expect("method", …)` checks that `method` exists on the spec, not that the argument list matches the real signature at runtime.
- **No automatic** `verify()` **outside pytest.** The pytest plugin checks every mock when the test finishes. Other runners still need an explicit `verify()`.
- **No spies and no patching.** The library does not wrap live objects, modules, or `sys.modules`. Just construct a `DeclarativeMock` and pass it in.
- **Not thread-safe.** Concurrent use of one mock from multiple threads is out of scope.

## Roadmap

Nothing is planned for 0.5.0, feel free to suggest!

- **Other test runners (low priority)** - unittest and similar runners do not verify mocks on teardown the way the pytest plugin does.

Other ideas belong in GitHub Issues.

## Development

```bash
poetry install
ruff check .
ruff format --check .
mypy src tests
pytest
coverage run -m pytest
coverage report
```

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for setup, commits, and tests. Agents follow **[AGENTS.md](AGENTS.md)**.

## License

MIT
