from collections import deque

from enum import Enum

from random import shuffle

from typing import Generic
from typing import Iterable
from typing import TypeVar
from typing import Self


__all__ = [
    'RepeatMode',
    'Queue'
]


T = TypeVar('T')


class RepeatMode(Enum):
    """Enum for Queue repeat modes."""

    Off = 'off'
    Single = 'single'
    All = 'all'


class Queue(Generic[T]):
    """
    Works like a spotify song Queue.

    Because the point of this class is to allow changing the repeat mode,
    it makes it impossible to normally iterate over the same queue object twice
    without resetting the index. To avoid this problem, copy the object

    Parameters
    ----------
    items: `Optional[Iterable[T]]`
        The list of items the queue contains
    items_once: `Optional[Iterable[T]]`
        The list of items to play after current song.

        If this list has any elements, those will have priority over
        items from the regular list
    repeat: `RepeatMode`
        The repeat state
    index: `int`
        The starting index
    """

    def __init__(
        self,
        items: Iterable[T] | None = None,
        *,
        alt_queue: Iterable[T] | None = None,
        repeat: RepeatMode = RepeatMode.Off,
        index: int = 0
    ) -> None:
        self._items: list[T] = [] if items is None else list(items)
        # TODO: items_once needs to be added in __add__ and other methods
        self._alt_queue: deque[T] = deque() if alt_queue is None else deque(alt_queue)
        self._repeat = repeat
        self._index = index
        self._advance = False
        """
        Used for proper iterating in next.
        Without it, a queue with All/Off repeat would start on the 2nd item.
        """

    def __iter__(self) -> Self:
        """Get self as an iterator."""
        return self

    def __next__(self) -> T:
        if self._alt_queue:
            return self._alt_queue.popleft()
        if self._repeat != RepeatMode.Single and self._advance:
            self._index += 1
        self._advance = True
        if self._index >= len(self._items):
            if self._repeat == RepeatMode.Off:
                raise StopIteration
            self._index %= len(self._items)
        return self._items[self._index]

    def __bool__(self) -> bool:
        """Check if the queue is non-empty."""
        return bool(self._items) or bool(self._alt_queue)

    def __eq__(self, other: Self) -> bool:
        """Compare the items of the iterables."""
        return self.items == other.items and self.alt_queue == other.alt_queue

    def __len__(self) -> int:
        """Get the amount of items the Queue contains."""
        return len(self._items)

    def __repr__(self) -> str:
        """Representation of the Queue object"""
        return f'{type(self).__qualname__}(alt_queue={self._alt_queue}, items={self._items}, index={self._index})'

    @property
    def items(self) -> list[T]:
        """Get a reference to the queue items."""
        return self._items

    @property
    def alt_queue(self) -> deque[T]:
        """Get a reference to the non-repeating items"""
        return self._alt_queue

    @property
    def repeat(self) -> RepeatMode:
        """Get the queue's repeat mode."""
        return self._repeat

    @repeat.setter
    def repeat(self, value: RepeatMode):
        if not isinstance(value, RepeatMode):
            raise TypeError(f"Value must be of type {RepeatMode.__qualname__}")
        self._repeat = value

    @property
    def index(self) -> int:
        """
        Get current index.

        Setting the index higher than Queue length will wrap around.
        """
        return self._index

    @index.setter
    def index(self, value: int):
        self._index = 0
        if self._items:
            self._index = value
        self._advance = False

    @property
    def current(self) -> T:
        """Get current item."""
        return self._items[self._index]

    def shuffle(self) -> None:
        """Shuffles the Queue in place, putting the current item T at position 1 (index 0), and shuffling the rest"""
        curr_i, curr = self.index, self.current
        self._items[0], self._items[curr_i] = curr, self._items[0]
        lst = self._items[1:]
        shuffle(lst)
        self._items[1:] = lst
        self._index = 0

    def clear(self) -> None:
        self._items.clear()
        self._alt_queue.clear()


