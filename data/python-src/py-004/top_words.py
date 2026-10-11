import heapq
import re
from collections import Counter

# Letters and digits in any script, optionally joined by apostrophes: "don't", "rock'n'roll", "naïve".
WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")


def top_k_words(text, k):
    """Return up to k (word, count) pairs, most frequent first, ties in alphabetical order.

    Words are compared case-insensitively. k <= 0 returns an empty list.
    """
    if k <= 0:
        return []
    counts = Counter(w.replace("’", "'") for w in WORD.findall(text.casefold()))
    # nsmallest with key (-count, word) gives highest count first, then alphabetical: O(n log k).
    return heapq.nsmallest(k, counts.items(), key=lambda item: (-item[1], item[0]))


if __name__ == "__main__":
    text = "The cat and the hat. THE end? Don't stop; don’t. Cat, hat, cat! naïve_naive"
    print(top_k_words(text, 3))
    print(top_k_words(text, 100)[-3:])
    print(top_k_words("b a c b a", 2))
    print(top_k_words("", 5), top_k_words(text, 0))
