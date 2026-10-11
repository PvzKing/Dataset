The approach is to sort by start, then walk the list once and either extend the last merged interval or start a new one. A few decisions are worth stating up front:

- **Intervals are closed**, so touching intervals like `(1, 2)` and `(2, 3)` merge into `(1, 3)`. If you need half-open intervals, change `<=` to `<`.
- **A contained interval must not shrink its container.** For `(1, 10)` followed by `(2, 3)`, the end stays 10, which is why the code uses `max` instead of simply taking the new end.
- **The input list is not modified.** `sorted()` returns a new list.
- **Invalid pairs such as `(4, 1)` raise `ValueError`** instead of silently producing a strange result.

```python
{{file intervals.py}}
```

```
{{run python intervals.py}}
```

Sorting dominates, so the function runs in O(n log n) time and uses O(n) extra space for the result.
