from openai import OpenAI

from app.core.config import settings


client = OpenAI(
    api_key=settings.openai_api_key
)


def create_embeddings(
    texts: list[str]
) -> list[list[float]]:

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
        dimensions=512
    )

    return [
        item.embedding
        for item in response.data
    ]