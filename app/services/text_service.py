import re


CHUNK_SIZE = 12_000
CHUNK_OVERLAP = 1_000


def split_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP
) -> list[str]:

    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk)

        start = end - overlap

    return chunks



def tokenize(text: str) -> set[str]:

    words = re.findall(
        r"\b\w+\b",
        text.lower()
    )

    return set(words)


def find_relevant_chunks(
    chunks: list[str],
    question: str,
    limit: int = 3
) -> list[str]:

    question_words = tokenize(
        question
    )

    scored_chunks = []

    for chunk in chunks:

        chunk_words = tokenize(
            chunk
        )

        score = len(
            question_words & chunk_words
        )

        scored_chunks.append(
            (score, chunk)
        )

    scored_chunks.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return [
        chunk
        for score, chunk in scored_chunks[:limit]
    ]