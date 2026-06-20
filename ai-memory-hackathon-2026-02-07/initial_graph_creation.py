import asyncio
import os
os.environ["ENV"] = "dev"
# Here, one can setup any model they wish. OpenAI and Phi4 were used in testing.
# os.environ["LLM_PROVIDER"] = "ollama"
# os.environ["LLM_MODEL"] = "phi4:latest"
# os.environ["LLM_ENDPOINT"] = "http://localhost:11434/v1"
os.environ["LLM_API_KEY"] = "."
os.environ["EMBEDDING_PROVIDER"] = "ollama"
os.environ["EMBEDDING_MODEL"] = "nomic-embed-text:latest"
os.environ["EMBEDDING_ENDPOINT"] = "http://localhost:11434/api/embed"
os.environ["EMBEDDING_DIMENSIONS"] = "768"
os.environ["HUGGINGFACE_TOKENIZER"] = "nomic-ai/nomic-embed-text-v1.5"
import cognee
import pandas as pd
from pathlib import Path
from helper_functions import export_cognee_data


def load_prompt(filename):
    """Load a prompt from the prompts directory"""
    prompt_path = Path(__file__).parent / "prompts" / filename
    with open(prompt_path, 'r') as f:
        return f.read()


# Load prompts from files
INVOICE_PROMPT = load_prompt("invoice_prompt.txt")
TRANSACTION_PROMPT = load_prompt("transaction_prompt.txt")


def read_invoices_csv(filepath, n_rows, delimiter=','):
    df = pd.read_csv(filepath, sep=delimiter).head(n_rows)
    print(filepath)
    print(df)
    # return "\n".join(str(row) for row in df.to_dict('records'))
    return [str(row) for row in df.to_dict('records')]

async def main():
    # Create a clean slate for cognee -- reset data and system state
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)

    # Read and process invoices
    invoices = read_invoices_csv('data/invoices.csv', 200)
    await cognee.add(invoices)
    await cognee.cognify(custom_prompt=INVOICE_PROMPT)

    # Read and process transactions
    transactions = read_invoices_csv('data/transactions.csv', 200, delimiter=';')
    await cognee.add(transactions)
    await cognee.cognify(custom_prompt=TRANSACTION_PROMPT)

    # Visualize the graph
    from cognee.api.v1.visualize.visualize import visualize_graph
    await visualize_graph("./graphs/initial_graph_small.html")

    # Export the data for sharing
    print("\n" + "=" * 60)
    print("Exporting cognee data...")
    await export_cognee_data()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())