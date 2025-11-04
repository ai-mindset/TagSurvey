"""Command-line interface for text categorization."""

import argparse
import asyncio
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

from .categorizer import CATEGORIES, categorize_file


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Categorize text using Ollama models",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "input_file", type=str, help="Path to JSON file with text to categorize"
    )

    parser.add_argument(
        "-o", "--output", type=str, help="Path to save categorized results"
    )

    parser.add_argument(
        "-m", "--model", type=str, default="mistral-nemo", help="Ollama model to use"
    )

    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=3,
        help="Number of items to process concurrently",
    )

    parser.add_argument(
        "--no-cache", action="store_true", help="Disable caching of model responses"
    )

    return parser.parse_args()


def main() -> NoReturn:
    """Main entry point for the CLI."""

    # Save reference to built-in print
    builtin_print: Callable = print

    # Try to import rich
    try:
        from rich.console import Console

        console = Console()
        rich_print = console.print
        have_rich = True
    except ImportError:
        rich_print = builtin_print
        have_rich = False

    # Parse arguments
    args = parse_args()

    # Check if input file exists
    if not Path(args.input_file).exists():
        rich_print(f"Error: Input file '{args.input_file}' does not exist.")
        sys.exit(1)

    # Display info
    if have_rich:
        from rich.panel import Panel

        rich_print(Panel(f"Text Categorizer", subtitle="Using Ollama"))
        rich_print(f"[bold]Input:[/bold] {args.input_file}")
        rich_print(f"[bold]Model:[/bold] {args.model}")
        rich_print(f"[bold]Categories:[/bold] {', '.join(CATEGORIES)}")
    else:
        rich_print("Text Categorizer (Using Ollama)")
        rich_print(f"Input: {args.input_file}")
        rich_print(f"Model: {args.model}")
        rich_print(f"Categories: {', '.join(CATEGORIES)}")

    # Run categorization
    try:
        results = asyncio.run(
            categorize_file(
                input_file=args.input_file,
                output_file=args.output,
                model=args.model,
                batch_size=args.batch_size,
                use_cache=not args.no_cache,
            )
        )

        # Display summary
        summary = results["summary"]
        if have_rich:
            rich_print("\n[bold]Results:[/bold]")
            rich_print(f"Processed {summary['total_items']} items")
            rich_print("\n[bold]Category distribution:[/bold]")
            for category, count in sorted(
                summary["category_counts"].items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (count / summary["total_items"]) * 100
                rich_print(f"  {category}: {count} ({percentage:.1f}%)")
        else:
            rich_print("\nResults:")
            rich_print(f"Processed {summary['total_items']} items")
            rich_print("\nCategory distribution:")
            for category, count in sorted(
                summary["category_counts"].items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (count / summary["total_items"]) * 100
                rich_print(f"  {category}: {count} ({percentage:.1f}%)")

        # Note where results are saved
        if args.output:
            if have_rich:
                rich_print(f"\n[bold green]Results saved to:[/bold green] {args.output}")
            else:
                rich_print(f"\nResults saved to: {args.output}")

    except Exception as e:
        rich_print(f"Error: {str(e)}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
