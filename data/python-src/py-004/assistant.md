Three details decide whether the result is correct and deterministic:

- **What counts as a word.** `\w+` would also match underscores and split `don't` into two words. I use letters and digits in any script, optionally joined by an apostrophe, so `don't` and `naïve` stay whole. The curly apostrophe `’` is normalised to `'`, so `don’t` and `don't` are counted together.
- **Case.** Comparison uses `casefold()`, which is stricter than `lower()` for some non-English letters, so `The` and `the` are the same word.
- **Ties.** Sorting by the key `(-count, word)` puts the highest count first and breaks ties alphabetically. `heapq.nsmallest` uses that key in O(n log k), which is cheaper than sorting all distinct words when k is small.

```python
{{file top_words.py}}
```

```
{{run python top_words.py}}
```

Edge cases: an empty text returns `[]`, `k <= 0` returns `[]`, and a `k` larger than the number of distinct words returns all of them. `naïve_naive` is split at the underscore because `_` is not part of a word here; change the pattern if your text uses underscores inside words.
