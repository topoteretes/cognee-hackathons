import os
from dotenv import load_dotenv

# Load Qdrant credentials (shared with snapshot scripts in ai-memory-hackathon/)
load_dotenv()
os.environ["VECTOR_DB_PROVIDER"] = "qdrant"
os.environ.setdefault("VECTOR_DB_URL", os.getenv("QDRANT_URL", ""))
os.environ.setdefault("VECTOR_DB_KEY", os.getenv("QDRANT_API_KEY", ""))

# Note, those definitions need to be above all other imports
# Since we are using Ollama locally, we do not need an API key, although it is important that it is defined, and not an empty string.
os.environ["LLM_API_KEY"] = "."
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["LLM_MODEL"] = "cognee-distillabs-model-gguf-quantized"
os.environ["LLM_ENDPOINT"] = "http://localhost:11434/v1"
os.environ["LLM_MAX_TOKENS"] = "16384"

os.environ["EMBEDDING_PROVIDER"] = "ollama"
os.environ["EMBEDDING_MODEL"] = "nomic-embed-text:latest"
os.environ["EMBEDDING_ENDPOINT"] = "http://localhost:11434/api/embed"
os.environ["EMBEDDING_DIMENSIONS"] = "768"
os.environ["HUGGINGFACE_TOKENIZER"] = "nomic-ai/nomic-embed-text-v1.5"

# IMPORTANT: Register Qdrant adapter BEFORE importing any cognee modules
import cognee_community_vector_adapter_qdrant.register

from custom_retriever import GraphCompletionRetrieverWithUserPrompt
import asyncio
import pathlib

async def main():
    """
    QUICK README:

    This file shows how to do searches on the previously created graph using a
    custom graph retriever.

    You can set your environment variables like the ones above to whichever models you want,
    using os.environ. If you decide to import cognee, make sure these environment variables
    are set BEFORE the line which imports cognee.

    IMPORTANT: Put you user_prompt.txt file (change the name if you wish) to a directory called
    "prompts", in the same level as the "custom_retriever.py" script. You can see why this is
    important in the custom retriever; just look for the use of "render_prompt()" function.

    To run a search, create an instance of the retriever with the desired user and system prompt,
    and use the "get_completion()" function of the retriever to get search results.

    """

    user_questions = [
        "Vendor 2 says they received a wrong payment, can you check whether all payments to Vendor 2 are correct?",
        "We ordered a new laptop from Vendor 3 but it was not delivered, can you check whether we ever paid for a laptop from Vendor 3?",
        # "Vendor 4 complaints that we order always a few items from them. Do we always order low quantities from them?",
        # "We are auditing our hardware budget. Have we paid for any storage devices or hard drives recently?",
        # "Did we buy any 'UltraWide' monitors from Vendor 2, or were they standard screens?",
        # "Can you confirm if the 'ASUS' equipment ordered last month has been fully paid for?",
        # "We returned a defective item to Vendor 3 this month. Can you check if we received a refund or discount on that transaction?"
        # "Which vendors consistently give us discounts on our orders?",
        # "Do we usually wait until the due date to pay Vendor 15, or do we pay them early?",
        # "Vendor 4 is asking for more business. Do we typically spend more with them or with Vendor 2?",
        # "Is there any vendor where we constantly have payment discrepancies?",
        # "Did we clear all our bills for the high-value equipment orders?"
    ]
    system_prompt_path = pathlib.Path(
        os.path.join(pathlib.Path(__file__).parent, "prompts/system_prompt.txt")
    ).resolve()

    retriever = GraphCompletionRetrieverWithUserPrompt(
        user_prompt_filename="user_prompt.txt",
        system_prompt_path=str(system_prompt_path),
        top_k=10,
    )

    user_answers = []
    for question in user_questions:
        completion = await retriever.get_completion(query=question)
        user_answers.append(completion)

    for i in range(len(user_questions)):
        print(f"Question: {user_questions[i]}")
        print(f"Answer: {user_answers[i][0]}")
        print("-" * 50)


if __name__ == "__main__":
    import resource

    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    print("Before:", soft, hard)
    resource.setrlimit(resource.RLIMIT_NOFILE, (min(10000, hard), hard))

    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    print("After: ", soft, hard)
    asyncio.run(main())
