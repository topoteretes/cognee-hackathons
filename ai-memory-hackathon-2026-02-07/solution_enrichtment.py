import asyncio
import cognee
import pandas as pd
from pathlib import Path


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
    return [str(row) for row in df.to_dict('records')]

async def main():
    # Read and process invoices
    invoices = read_invoices_csv('data_for_enrichment/new_invoices.csv', 10000)
    await cognee.add(invoices)
    await cognee.cognify(custom_prompt=INVOICE_PROMPT)

    # Read and process transactions
    transactions = read_invoices_csv('data_for_enrichment/new_transactions.csv', 10000, delimiter=';')
    await cognee.add(transactions)
    await cognee.cognify(custom_prompt=TRANSACTION_PROMPT)

    # Visualize the graph
    from cognee.api.v1.visualize.visualize import visualize_graph
    await visualize_graph("./graphs/enriched_graph.html")



if __name__ == "__main__":
    asyncio.run(main())