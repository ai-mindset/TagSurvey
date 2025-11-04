"""Module for converting Excel workbooks to JSON format.

This module provides functions to read Excel workbooks and convert their
columns to structured JSON objects, with a focus on qualitative survey data.
"""

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


def extract_question_text(column_name: str) -> str:
    """Extract the question text from a column name.

    Args:
        column_name: The original column name from the Excel file

    Returns:
        The cleaned question text

    >>> extract_question_text("Q5: What further information would help you?")
    'What further information would help you?'
    >>> extract_question_text("Q5.What further information would help you?")
    'What further information would help you?'
    >>> extract_question_text("What further information would help you?")
    'What further information would help you?'
    """
    # Look for common question number patterns: Q5:, Q5., 5., etc.
    patterns = [
        r"^Q\d+[\s\-\.:]+\s*",  # Q5: or Q5. or Q5 -
        r"^\d+[\s\-\.:]+\s*",  # 5: or 5. or 5 -
    ]

    result = column_name
    for pattern in patterns:
        result = re.sub(pattern, "", result)

    return result.strip()


def extract_question_number(column_name: str) -> int | None:
    """Extract the question number from a column name.

    Args:
        column_name: The original column name from the Excel file

    Returns:
        The question number if found, None otherwise

    >>> extract_question_number("Q5: What further information would help you?")
    5
    >>> extract_question_number("5. What is your name?")
    5
    >>> extract_question_number("What is your name?") is None
    True
    """
    # Try to extract question number using regex
    patterns = [
        r"^Q(\d+)[\s\-\.:]+",  # Q5: or Q5. or Q5 -
        r"^(\d+)[\s\-\.:]+",  # 5: or 5. or 5 -
    ]

    for pattern in patterns:
        match = re.match(pattern, column_name)
        if match:
            return int(match.group(1))

    return None


def clean_response(text: Any) -> str | None:
    """Clean and normalize a response value.

    Args:
        text: The response value from the Excel cell

    Returns:
        The cleaned response text or None if empty/NA

    >>> clean_response("  Better data  ")
    'Better data'
    >>> clean_response("N/A")
    None
    >>> clean_response("NA")
    None
    >>> clean_response(None) is None
    True
    >>> clean_response(123)
    '123'
    >>> clean_response(float("nan")) is None
    True
    """
    if pd.isna(text):
        return None

    # Convert to string if needed
    str_text = str(text).strip()

    # Replace common non-response indicators with None
    non_responses = {"n/a", "na", "not applicable", "none", ""}
    if str_text.lower() in non_responses:
        return None

    return str_text


def convert_sheet_to_json(
    df: pd.DataFrame, question_prefix_pattern: str | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Convert a dataframe (Excel sheet) to a structured JSON object.

    Args:
        df: The pandas DataFrame containing the sheet data
        question_prefix_pattern: Optional regex pattern to identify and remove question prefixes

    Returns:
        Dictionary with column data structured for JSON export

    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     "Q1: Favorite color?": ["Blue", "Red", None],
    ...     "Q2: Age?": [42, 38, 25]
    ... })
    >>> result = convert_sheet_to_json(df)
    >>> len(result["columns"])
    2
    >>> result["columns"][0]["question"]
    'Favorite color?'
    >>> len(result["columns"][0]["responses"])
    2  # None value is filtered out
    """
    columns_data = []

    for column in df.columns:
        # Extract the actual question text
        question = extract_question_text(column)

        # Extract question number or generate a sequential one
        question_num = extract_question_number(column)

        # Gather non-empty responses
        responses = []
        for idx, value in enumerate(df[column]):
            cleaned = clean_response(value)
            if cleaned is not None:
                responses.append({"id": str(idx), "text": cleaned})

        # Add to columns data if there are any responses
        if responses:
            column_data = {"question": question, "responses": responses}

            # Add question number key if available
            if question_num is not None:
                column_data["question_id"] = f"question{question_num}"
            else:
                # Use the index in the dataframe as a fallback
                column_idx = df.columns.get_loc(column) + 1
                column_data["question_id"] = f"question{column_idx}"

            columns_data.append(column_data)

    return {"columns": columns_data}


def process_excel_file(
    file_path: str | Path,
    sheet_name: str | int | list[str | int] | None = None,
    output_dir: str | Path | None = None,
    prefix_filter: str | None = None,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Process an Excel file and convert to JSON.

    Args:
        file_path: Path to the Excel file
        sheet_name: Optional sheet name(s) or index(es) to process. If None, processes all sheets.
        output_dir: Optional directory to save the JSON output files
        prefix_filter: Optional regex pattern to filter column names

    Returns:
        Dictionary containing the processed data from all sheets

    >>> # This test requires an actual Excel file
    >>> # result = process_excel_file("sample.xlsx")
    >>> # isinstance(result, dict)
    >>> # True
    """
    # Convert path to Path object
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")

    # Create output directory if specified and it doesn't exist
    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # Read the Excel file
    try:
        xl = pd.ExcelFile(file_path)

        # Determine which sheets to process
        if sheet_name is None:
            sheets_to_process = xl.sheet_names
        elif isinstance(sheet_name, list):
            sheets_to_process = sheet_name
        else:
            sheets_to_process = [sheet_name]

        # Process each sheet
        all_data = {}
        for sheet in sheets_to_process:
            try:
                # Skip sheet if it doesn't exist
                if isinstance(sheet, str) and sheet not in xl.sheet_names:
                    continue

                # Read the sheet into a DataFrame
                df = pd.read_excel(xl, sheet_name=sheet)

                # Filter columns if prefix_filter is specified
                if prefix_filter:
                    df = df.filter(regex=prefix_filter)

                # Convert the sheet to JSON structure
                sheet_data = convert_sheet_to_json(df)

                # Add to the collection
                sheet_name_str = str(sheet)
                all_data[sheet_name_str] = sheet_data

                # Save to a file if output_dir is specified
                if output_dir is not None:
                    # Create a valid filename from the sheet name
                    safe_name = re.sub(r"[^\w\-_.]", "_", sheet_name_str)
                    output_file = output_dir / f"{safe_name}.json"

                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(sheet_data, f, indent=2, ensure_ascii=False)

            except Exception as e:
                # Log the error but continue processing other sheets
                print(f"Error processing sheet {sheet}: {e}")

        return all_data

    except Exception as e:
        raise RuntimeError(f"Failed to process Excel file: {e}") from e


def main(
    excel_path: str | Path,
    output_path: str | Path | None = None,
    sheet_name: str | int | list[str | int] | None = None,
) -> None:
    """Command-line entry point for the Excel to JSON converter.

    Args:
        excel_path: Path to the Excel file
        output_path: Directory to save JSON output
        sheet_name: Optional sheet name or index to process
    """
    try:
        result = process_excel_file(
            file_path=excel_path, sheet_name=sheet_name, output_dir=output_path
        )

        # Print summary
        sheet_count = len(result)
        total_columns = sum(len(data["columns"]) for data in result.values())
        print(
            f"Successfully processed {sheet_count} sheets with {total_columns} columns total"
        )

        if output_path:
            print(f"JSON files saved to {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert Excel workbooks to JSON format")
    parser.add_argument("excel_file", type=str, help="Path to the Excel workbook")
    parser.add_argument(
        "-o", "--output", type=str, help="Directory for saving JSON output files"
    )
    parser.add_argument(
        "-s", "--sheet", type=str, help="Specific sheet to process (name or index)"
    )

    args = parser.parse_args()

    main(excel_path=args.excel_file, output_path=args.output, sheet_name=args.sheet)
