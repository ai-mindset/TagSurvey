"""Example of integrating Excel converter with the categorization system.

This module demonstrates how to combine the Excel converter with the
text categorization functionality.
"""

import asyncio
import json
from pathlib import Path

from text_categorizer import categorizer, excel_converter


async def process_excel_and_categorize(
    excel_path: str | Path,
    output_dir: str | Path | None = None,
    sheet_name: str | None = None,
    model: str = "mistral-nemo",
    batch_size: int = 3,
    use_cache: bool = True,
) -> dict:
    """Process Excel file and categorize the extracted text responses.

    Args:
        excel_path: Path to the Excel file
        output_dir: Directory to save output files
        sheet_name: Optional specific sheet to process
        model: Ollama model to use
        batch_size: Number of items to process concurrently
        use_cache: Whether to use caching

    Returns:
        Dictionary with categorization results
    """
    # Create output directory if specified
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # Process the Excel file to extract questions and responses
    excel_data = excel_converter.process_excel_file(
        file_path=excel_path, sheet_name=sheet_name, output_dir=output_dir
    )

    all_results = {}

    # Process each sheet
    for sheet_name, sheet_data in excel_data.items():
        sheet_results = []

        # Process each column (question)
        for column_data in sheet_data["columns"]:
            question = column_data["question"]
            question_id = column_data["question_id"]
            responses = column_data["responses"]

            # Prepare for categorization
            items_to_categorize = []
            for response in responses:
                # Format responses for the categorizer
                items_to_categorize.append(
                    {"id": response["id"], "description": response["text"]}
                )

            # Skip if no valid responses
            if not items_to_categorize:
                continue

            # Create a temporary JSON file for this question's responses
            temp_file = Path(f"temp_{sheet_name}_{len(question)}.json")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(items_to_categorize, f)

            # Process with categorizer
            try:
                output_file = None
                if output_dir:
                    # Create a safe filename
                    safe_name = question[:30].replace(" ", "_")
                    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "_-")
                    output_file = (
                        output_dir
                        / f"{sheet_name}_{question_id}_{safe_name}_categorized.json"
                    )

                # Run categorization
                categorization_result = await categorizer.categorize_file(
                    input_file=temp_file,
                    output_file=output_file,
                    model=model,
                    batch_size=batch_size,
                    use_cache=use_cache,
                )

                # Add question information to the result
                categorization_result["question"] = question
                categorization_result["question_id"] = question_id

                sheet_results.append(categorization_result)

            finally:
                # Clean up temporary file
                if temp_file.exists():
                    temp_file.unlink()

        all_results[sheet_name] = sheet_results

        # Create a combined results file for the sheet if output_dir specified
        if output_dir and sheet_results:
            combined_output = output_dir / f"{sheet_name}_all_categorized.json"
            with open(combined_output, "w", encoding="utf-8") as f:
                json.dump(
                    {"sheet_name": sheet_name, "results": sheet_results}, f, indent=2
                )

    return all_results


async def main():
    """Example usage of the integrated Excel-to-categorization pipeline."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Process Excel files and categorize text responses"
    )
    parser.add_argument(
        "excel_file", type=str, help="Path to Excel file with survey responses"
    )
    parser.add_argument("-o", "--output", type=str, help="Directory for output files")
    parser.add_argument("-s", "--sheet", type=str, help="Specific sheet to process")
    parser.add_argument(
        "-m", "--model", type=str, default="mistral-nemo", help="Ollama model to use"
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=3,
        help="Batch size for concurrent processing",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable response caching"
    )

    args = parser.parse_args()

    try:
        print(f"Processing Excel file: {args.excel_file}")

        results = await process_excel_and_categorize(
            excel_path=args.excel_file,
            output_dir=args.output,
            sheet_name=args.sheet,
            model=args.model,
            batch_size=args.batch_size,
            use_cache=not args.no_cache,
        )

        # Print summary
        sheet_count = len(results)
        question_count = sum(len(questions) for questions in results.values())

        print(f"\nProcessed {sheet_count} sheets with {question_count} questions total")
        if args.output:
            print(f"Results saved to {args.output}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
