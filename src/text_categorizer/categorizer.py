"""Text categorization using Ollama models.

This module provides functions to categorize text into predefined categories.
"""

import asyncio
import hashlib
import json
from collections.abc import AsyncGenerator
from pathlib import Path

# Available categories
CATEGORIES = [
    "Funding",
    "Data",
    "Governance",
    "Workforce",
    "Comms and engagement",
    "Other",
]


async def get_ollama_response(text: str, model: str = "gemma3:27b-it-qat") -> str:
    """Query Ollama model with the given text.

    Args:
        text: Text to send to the model
        model: Ollama model name

    Returns:
        Model's response as a string

    >>> import asyncio
    >>> # This test requires Ollama running
    >>> # response = asyncio.run(get_ollama_response("Need more funding"))
    >>> # isinstance(response, str)
    >>> # True
    """
    import httpx

    # Prepare the prompt
    categories_str = ", ".join(CATEGORIES)
    prompt = f"""You have a list of categories that you want to assign to some text. 
    Here is the list: {categories_str}. You must assign one or more of those categories in the list, to the following text. Each text can be labelled with more than one category, as long as it is considered relevant. 

Text to categorize: {text}

First, think about which categories apply. Then, provide your answer as a comma-separated list 
of categories that apply to this text. Only include categories from the provided list.

Categories:"""

    # Send request to Ollama API
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()
    except httpx.HTTPError as e:
        print(f"Error calling Ollama API: {e}")
        return ""


def extract_categories(response: str) -> set[str]:
    """Extract categories from model response.

    Args:
        response: Raw text response from the model

    Returns:
        Set of identified categories

    >>> extract_categories("Funding, Data")
    {'Funding', 'Data'}
    >>> extract_categories("This text is about Funding and Governance.")
    {'Funding', 'Governance'}
    >>> extract_categories("None of these categories apply")
    {'Other'}
    """
    # Try to extract categories from the response
    detected = set()

    # First, try to handle comma-separated format
    for item in response.split(","):
        item = item.strip()
        if item in CATEGORIES:
            detected.add(item)

    # If that didn't work, try to find category names in the text
    if not detected:
        for category in CATEGORIES:
            if category.lower() in response.lower():
                detected.add(category)

    # Default to "Other" if no categories were found
    if not detected:
        detected.add("Other")

    return detected


async def process_item(
    item: dict, model: str = "llama3", cache_dir: Path | None = None
) -> dict:
    """Process a single text item and assign categories.

    Args:
        item: Dictionary containing text to categorize
        model: Ollama model to use
        cache_dir: Optional directory for caching results

    Returns:
        Item with added categories

    >>> import asyncio
    >>> # This test requires Ollama running
    >>> # result = asyncio.run(process_item({"description": "We need more funding"}))
    >>> # "categories" in result
    >>> # True
    """
    text = item.get("description", "")
    if not text:
        return {**item, "categories": ["Other"]}

    # Initialize cache file path
    cache_file = None

    # Check cache if enabled
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        text_hash = hashlib.md5(f"{text}:{model}".encode()).hexdigest()
        cache_file = cache_dir / f"{text_hash}.json"

        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    cached = json.load(f)
                    return {**item, "categories": cached["categories"]}
            except (json.JSONDecodeError, KeyError):
                pass

    # Get model response
    response = await get_ollama_response(text, model)

    # Extract categories
    categories = extract_categories(response)
    result = {**item, "categories": list(categories)}

    # Save to cache if enabled
    if cache_dir and cache_file:
        with open(cache_file, "w") as f:
            json.dump({"text": text, "categories": list(categories)}, f)

    return result


async def process_batch(
    items: list[dict],
    batch_size: int = 3,
    model: str = "llama3",
    cache_dir: Path | None = None,
) -> AsyncGenerator[dict]:
    """Process items in batches to limit concurrency.

    Args:
        items: List of items to process
        batch_size: Number of items to process concurrently
        model: Ollama model to use
        cache_dir: Optional directory for caching results

    Yields:
        Processed items with categories
    """
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        tasks = [process_item(item, model, cache_dir) for item in batch]
        results = await asyncio.gather(*tasks)
        for result in results:
            yield result


async def categorize_file(
    input_file: str | Path,
    output_file: str | Path | None = None,
    model: str = "llama3",
    batch_size: int = 3,
    use_cache: bool = True,
) -> dict:
    """Categorize all items in a JSON file.

    Args:
        input_file: Path to input JSON file
        output_file: Optional path to save results
        model: Ollama model to use
        batch_size: Number of items to process concurrently
        use_cache: Whether to use caching

    Returns:
        Dictionary with categorized items
    """
    # Load input data
    with open(input_file) as f:
        data = json.load(f)

    # Handle various possible input formats
    if isinstance(data, dict) and "needs" in data:
        items = data["needs"]
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError(
            "Unsupported JSON format. Expected dict with 'needs' key or list."
        )

    # Set up cache if enabled
    cache_dir = Path("~/.cache/text_categorizer").expanduser() if use_cache else None

    # Process all items
    results = []
    async for result in process_batch(items, batch_size, model, cache_dir):
        results.append(result)

        # Print progress
        print(f"Processed {len(results)}/{len(items)} items", end="\r")

    print(f"Processed {len(results)}/{len(items)} items")

    # Add summary
    category_counts = {}
    for item in results:
        for category in item.get("categories", []):
            category_counts[category] = category_counts.get(category, 0) + 1

    output = {
        "categorized_items": results,
        "summary": {"total_items": len(results), "category_counts": category_counts},
    }

    # Save results if output file provided
    if output_file:
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Results saved to {output_file}")

    return output
