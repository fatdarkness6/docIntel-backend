import json

from openai import OpenAI

from app.core.config import settings
from app.services.text_service import (
    split_text,
)


client = OpenAI(
    api_key=settings.openai_api_key
)


def summarize_document(text: str) -> str:
    chunks = split_text(text)

    # Small document
    if len(chunks) == 1:
        response = client.responses.create(
            model="gpt-5-nano",
            input=f"""
Create a concise, UI-friendly summary of this document.

STRICT RULES:
- Maximum 150 words total.
- Start with a 2-3 sentence overview.
- Then give 3-5 key points.
- Each key point must be one short sentence.
- Do not repeat information.
- Do not create a separate conclusion.
- Do not list every technical detail.
- Include numbers only when genuinely important.
- Use plain, easy-to-scan language.

Format exactly like this:

Overview
<2-3 sentences>

Key Points
- <point>
- <point>
- <point>

Document:

{text}
"""
        )

        return response.output_text.strip()

    # Large document
    chunk_summaries = []

    for chunk in chunks:
        response = client.responses.create(
            model="gpt-5-nano",
            input=f"""
Summarize this section in no more than 60 words.

Keep only the most important information.
Do not explain minor details.
Do not repeat ideas.
Preserve important names or numbers only when necessary.

Section:

{chunk}
"""
        )

        chunk_summaries.append(
            response.output_text.strip()
        )

    combined = "\n\n".join(
        chunk_summaries
    )

    final_response = client.responses.create(
        model="gpt-5-nano",
        input=f"""
Create one concise, UI-friendly summary from these section summaries.

STRICT RULES:
- Maximum 150 words total.
- Start with a 2-3 sentence overview.
- Then give exactly 3-5 important key points.
- Each key point must be one short sentence.
- Remove repeated information.
- Do not include every technical detail.
- Do not create an "Important facts" section.
- Do not create a conclusion section.
- Do not mention that these came from separate sections.

Format exactly like this:

Overview
<2-3 sentences>

Key Points
- <point>
- <point>
- <point>

Section summaries:

{combined}
"""
    )

    return final_response.output_text.strip()


def generate_dataset_insights(
    analysis: dict
) -> str:
    analysis_text = json.dumps(
        analysis,
        indent=2
    )

    response = client.responses.create(
        model="gpt-5-nano",

        instructions="""
You are a data analyst.

Analyze the dataset statistics provided by Python.

Give:
- important observations
- unusual values
- useful trends
- missing data problems
- possible business insights

Do not invent information.
Only use the provided statistics.
Keep the response concise.
""",

        input=analysis_text
    )

    return response.output_text


def ask_document_question(
    relevant_chunks: list[dict],
    question: str,
    history: list[dict]
) -> str:

    document_context = "\n\n---\n\n".join(
        f"[Chunk {chunk['chunk_index']}]\n{chunk['content']}"
        for chunk in relevant_chunks
    )

    messages = []

    for item in history:
        messages.append({
            "role": "user",
            "content": item["question"]
        })

        messages.append({
            "role": "assistant",
            "content": item["answer"]
        })

    messages.append({
        "role": "user",
        "content": question
    })

    response = client.responses.create(
        model="gpt-5-nano",

        instructions=f"""
        Answer using ONLY the provided document context.

        Use previous conversation only to understand
        what the user is referring to.

        If the answer isn't available in the provided context,
        say that you couldn't find it.

        Document context:

        {document_context}
        """,

        input=messages
    )

    return response.output_text