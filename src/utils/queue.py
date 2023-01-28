from collections import deque
from enum import Enum
from random import shuffle
from typing import (
    Deque,
    Generic,
    Iterable,
    Optional,
    Sized,
    TypeVar,
    Self
)


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
        items: Optional[Iterable[T]] = None,
        *,
        items_once: Optional[Iterable[T]] = None,
        repeat: RepeatMode = RepeatMode.All,
        index: int = 0
    ) -> None:
        self._items = [] if items is None else list(items)
        # TODO: items_once needs to be added in __add__ and other methods
        self._alt_queue = deque() if items_once is None else deque(items_once)
        self._repeat = repeat
        self._index = index
        self._advance = False

    def __iter__(self) -> Self:
        """Get self as an iterator."""
        return self

    def __next__(self) -> Optional[T]:
        if self._alt_queue:
            return self._alt_queue.popleft()
        elif self._items:
            if self._repeat != RepeatMode.Single and self._advance:
                self._index += 1
            self._advance = True
            if self._index >= len(self._items):
                if self._repeat == RepeatMode.Off:
                    return None
                self._index %= len(self._items)
            return self._items[self._index]
        else:
            return None

    def __bool__(self) -> bool:
        """Check if the queue is non-empty."""
        return bool(self._items) or bool(self._alt_queue)

    def __eq__(self, other: Self) -> bool:
        """Compare the items of the iterables."""
        if not isinstance(other, Iterable):
            return False
        return self.items == other.items and self.alt_queue == other.alt_queue

    def __len__(self) -> int:
        """Get the amount of items the Queue contains."""
        return len(self._items)

    def __repr__(self) -> str:
        """Representation of the Queue object"""
        return f'{type(self).__qualname__}(alt_queue={self._alt_queue}, items={self._items}, index={self._index})'

    __hash__ = None

    @property
    def items(self) -> list[T]:
        """Get a reference to the queue items."""
        return self._items

    @property
    def alt_queue(self) -> Deque[T]:
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

        If repeat is not Single, the next item will be the one ahead of set index,
        use Queue.jump to avoid this
        """
        return self._index

    @index.setter
    def index(self, value: int):
        self._index = value % len(self)
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


if __name__ == '__main__':
    q = Queue(range(100))
    q.repeat = RepeatMode.Off
    for item in q:
        print(item, end=' ')
