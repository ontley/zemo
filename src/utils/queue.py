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

    Because the point of this class is to allow changing the repeat mode during iteration,
    it makes it impossible to normally iterate over the same queue object twice
    without resetting the index. To avoid this problem, copy the object

    Parameters
    ----------
    items: `Optional[Iterable[T]]`
        The list of items the queue contains
    priority_queue: `Optional[Iterable[T]]`
        Items with priority over regular items.

        The queue will first yield the priority items, and then the regular items.

        Priority items are popped off when yielded, this is done to imitate the Spotify queue.
    repeat: `RepeatMode`
        The repeat state
    index: `int`
        The starting index
    """

    def __init__(
        self,
        items: Iterable[T] | None = None,
        *,
        priority_items: Iterable[T] | None = None,
        repeat: RepeatMode = RepeatMode.Off,
        index: int = 0,
    ) -> None:
        self._items: list[T] = [] if items is None else list(items)
        self._prio_items: deque[T] = deque() if priority_items is None else deque(priority_items)
        self._current: T | None = None
        self._repeat: RepeatMode = repeat
        self._index: int = index
        self._advance: bool = False
        """
        Used for proper iterating in __next__.
        Without it, a queue with All/Off repeat would start on the 2nd item.
        """

    def __iter__(self) -> Self:
        """Get self as an iterator."""
        return self

    def __next__(self) -> T:
        if self._prio_items:
            self._current = self._prio_items.popleft()
            return self._current
        if len(self._items) == 0:
            raise StopIteration
        # _advance is False if the queue hasn't yielded anything, or it skipped/jumped
        # this is needed because we don't want to advance the queue if we're guaranteeing the next item
        if self._repeat != RepeatMode.Single and self._advance:
            self._index += 1
        self._advance = True
        if self._index >= len(self._items):
            if self._repeat == RepeatMode.Off:
                raise StopIteration
            self._index %= len(self._items)
        self._current = self._items[self._index]
        return self._current

    def __bool__(self) -> bool:
        """Check if the queue is non-empty."""
        return bool(self._items) or bool(self._prio_items)

    def __eq__(self, other: Self) -> bool:
        """Compare the items of the iterables."""
        return self.items == other.items and self.prio_items == other.prio_items

    def __len__(self) -> int:
        """The length of the queue's items"""
        return len(self._items)

    def __repr__(self) -> str:
        """Representation of the Queue object"""
        return f'{type(self).__qualname__}(alt_queue={self._prio_items}, items={self._items}, index={self._index})'

    @property
    def items(self) -> list[T]:
        """Get a reference to the queue items."""
        return self._items

    @property
    def prio_items(self) -> deque[T]:
        """Get a reference to the priority items"""
        return self._prio_items

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
    def current(self) -> T | None:
        """
        Get current (last yielded) item.

        None if the queue hasn't yielded anything
        """
        return self._current

    def shuffle(self) -> None:
        """
        Shuffles the Queue in place, putting the current item at position 1 (index 0), and shuffling the rest.

        This does NOT shuffle the priority queue.
        """
        curr_i, curr = self.index, self.current
        # check if the queue has yielded anything
        if curr is None:
            shuffle(self._items)
        else:
            self._items[0], self._items[curr_i] = curr, self._items[0]
            lst = self._items[1:]
            shuffle(lst)
            self._items[1:] = lst
        self._index = 0

    def clear(self) -> None:
        self._items.clear()
        self._prio_items.clear()
