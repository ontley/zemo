__all__ = [
    'to_readable_time',
    'to_ordinal'
]


def to_readable_time(seconds: int) -> str:
    """
    Convert a number of seconds into human readable time.

    Examples:
    - `60 -> '1m'`
    - `61 -> '1m:1s'`
    - `3601 -> '1h:1s'`
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    time = ''
    if h:
        time += f'{h}h'
        if m or s:
            time += ':'
    if m:
        time += f'{m}m'
        if s:
            time += ':'
    if s:
        time += f'{s}s'
    return time


def to_ordinal(n: int) -> str:
    """Convert an integer to it's english ordinal representation."""
    if n in range(11, 14):
        return f'{n}th'
    last_digit = n % 10
    ordinal = str(n)
    if last_digit == 1:
        ordinal += 'st'
    elif last_digit == 2:
        ordinal += 'nd'
    elif last_digit == 3:
        ordinal += 'rd'
    else:
        ordinal += 'th'
    return ordinal
