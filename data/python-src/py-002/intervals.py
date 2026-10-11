def merge_intervals(intervals):
    """Merge overlapping closed intervals.

    >>> merge_intervals([(8, 10), (1, 3), (2, 6)])
    [(1, 6), (8, 10)]
    """
    for start, end in intervals:
        if start > end:
            raise ValueError(f"start must not exceed end: {(start, end)}")
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            # Overlapping or touching: extend the last interval, but never shrink it.
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


if __name__ == "__main__":
    cases = [
        [],
        [(5, 7)],
        [(8, 10), (1, 3), (2, 6)],
        [(1, 2), (2, 3)],
        [(1, 10), (2, 3), (4, 5)],
        [(1.5, 2.5), (0, 1)],
    ]
    for case in cases:
        print(f"{case!s:28} -> {merge_intervals(case)}")
    original = [(3, 4), (1, 2)]
    merge_intervals(original)
    print("input unchanged:", original)
    try:
        merge_intervals([(4, 1)])
    except ValueError as e:
        print("ValueError:", e)
