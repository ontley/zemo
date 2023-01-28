from collections import deque
from enum import Enum
from random import shuffle
from typing import (
    Deque,
    Generic,
    Iterable,
    Iterator,
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
        self._jumped = False
        self._advanced = False

    def __iter__(self) -> Iterator[T]:
        """Get self as iterator."""
        while True:
            if self._alt_queue:
                yield self._alt_queue.popleft()
            elif self._items:
                self._jumped = False
                self._advanced = True
                if self._index >= len(self._items):
                    if self._repeat == RepeatMode.Off:
                        break
                    self._index %= len(self._items)
                yield self._items[self._index]
                if self._repeat != RepeatMode.Single:
                    self._index += 1
            else:
                break

    def __bool__(self) -> bool:
        """Check if the queue is non-empty."""
        return bool(self._items) or bool(self._alt_queue)

    def __eq__(self, other: Sized) -> bool:
        """Compare the items of the iterables."""
        if not isinstance(other, Iterable):
            return False
        return len(self) == len(other) and \
            all(s_item == o_item for s_item, o_item in zip(self._items, other))

    def __add__(self, other: Self) -> Self:
        """Concatenate two Queues."""
        if not isinstance(other, Queue):
            raise TypeError(
                f'Can only concatenate {type(self).__name__} \
                        (not "{type(other).__name__}") and {type(self).__name__}'
            )
        return Queue(items=self._items + other._items)

    def __iadd__(self, other: Self) -> None:
        """Concatenate to self."""
        if not isinstance(other, Queue):
            raise TypeError(
                f'Can only concatenate {type(self).__name__} \
                        (not "{type(other).__name__}") and {type(self).__name__}'
            )
        self._items += other._items

    def __mult__(self, times: int) -> Self:
        """
        Repeat the Queue an integer amount of times.

        Returns a Queue with the same repeat mode
        """
        if not isinstance(times, int):
            raise TypeError(
                f'Can not multiply {type(self).__name__} \
                        by non-int of type {type(times).__name__}'
            )
        return Queue(
            items=self._items*times,
            repeat=self._repeat
        )

    def __imult__(self, times: int) -> None:
        """Repeat own items an integer amount of times."""
        if not isinstance(times, int):
            raise TypeError(
                f'Can not multiply {type(self).__name__} \
                        by non-int of type {type(times).__name__}'
            )
        self._items *= times

    def __len__(self) -> int:
        """Get the amount of items the Queue contains."""
        return len(self._items)

    def __repr__(self) -> str:
        """Representation of the Queue object"""
        return f'{type(self).__qualname__}({self._items}, {self._index})'

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
            raise TypeError(f"value must be of type {RepeatMode.__qualname__}")

        if self._jumped:
            if self._repeat == RepeatMode.Single != value:
                self._index -= 1
            elif self._repeat != RepeatMode.Single == value:
                self._index += 1
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
        self._index = value % len(self._items)
        self._advanced = False

    @property
    def current(self) -> T:
        """Get current item."""
        return self._items[self._index]

    def jump(self, index: int) -> None:
        """
        Force next item to be at `index`, even if repeat mode is changed after.

        Raises
        ------
        `ValueError`: index is out of range
        """
        if index not in range(len(self)):
            raise ValueError('index out of range')
        self._jumped = True
        if self._advanced and self._repeat != RepeatMode.Single:
            index -= 1
        self.index = index

    def skip(self, offset: int = 1) -> None:
        """Skip ahead, force next item to be at current index + `offset`"""
        self._jumped = True
        if self._advanced and self._repeat != RepeatMode.Single:
            offset -= 1
        self.index += offset

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
