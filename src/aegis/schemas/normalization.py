import string
import unicodedata

from nltk.corpus import stopwords

# Instantiating the set at the module level avoids recreating
# the set object on every function invocation.
NLTK_STOP_WORDS = set(stopwords.words("english"))


def canonical_mangle_processor(anonymized_note: str) -> str:
    # 1. Unicode Normalization (NFKD) & Lowercase Case-Folding
    nfkd_form = unicodedata.normalize("NFKD", anonymized_note)
    lowered = nfkd_form.lower()

    # 2. Optimized Punctuation Removal Mapping
    no_punctuation = lowered.translate(str.maketrans("", "", string.punctuation))

    # 3. Fast-Path Tokenization via Word Boundaries
    tokens = no_punctuation.split()

    # 4. Deduplication & NLTK Stop-Word Filtering
    meaningful_tokens = {token for token in tokens if token not in NLTK_STOP_WORDS}

    # 5. Canonical Lexicographical Alphabetical Sort (Standard Industrial Sequence)
    sorted_tokens = sorted(list(meaningful_tokens))

    # 6. Join to yield a deterministic, hashable string representation
    return " ".join(sorted_tokens)
