# Text Categorisation Tool

A privacy-first, lightweight, efficient tool for categorising unstructured text responses from Excel workbooks into predefined categories using open-source Ollama models.

## Overview

This project provides a simple framework for processing and categorising qualitative survey data. It extracts free-text responses from Excel workbooks and uses local Ollama models to categorise them into predefined categories. This is especially useful for analysing open-ended survey questions where responses vary widely.

### Key Features

- **Excel Processing**: Extract questions and responses directly from Excel workbooks
- **Local Inference**: Uses Ollama to run powerful language models on your own hardware
- **Configurable Categories**: Easily adapt the tool to your specific categorisation needs
- **Efficient Batching**: Processes texts in parallel for faster throughput
- **Result Caching**: Avoids redundant model calls to save time and resources
- **Question Tracking**: Intelligently identifies and tracks question numbers across sheets
- **Lightweight**: Minimal dependencies, focused on a single task

## Project Structure

```
text_categorizer/
├── categorizer.py        # Text categorization module
├── excel_converter.py    # Excel file processing module
├── integration.py        # Integration of both modules
└── README.md             # This documentation
```

## Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.com) installed and running locally
- Basic understanding of Excel data formats

## Installation

1. Clone or download this repository:
   ```bash
   git clone https://github.com/ai-mindset/text_categorizer.git
   cd text_categorizer
   ```

2. Install the required dependencies:
   ```bash
   uv pip install -e . 
   ```

3. Install and start Ollama:
   ```bash
   # Install Ollama from https://ollama.com/download
   
   # Start the Ollama server
   ollama serve
   ```

4. Pull the default model:
   ```bash
   ollama pull mistral-nemo
   ```

## Usage

### Basic Operation

To process an Excel file and categorise its contents:

```bash
python integration.py survey_responses.xlsx -o ./results
```

This will:
1. Read all sheets in `survey_responses.xlsx`
2. Extract questions and their associated responses
3. Categorise each response into one of the predefined categories
4. Save the results to the `./results` directory

### Command-line Options

```
python integration.py INPUT_FILE [OPTIONS]

Arguments:
  INPUT_FILE              Path to Excel file containing survey responses

Options:
  -o, --output PATH       Directory to save output files
  -s, --sheet TEXT        Specific sheet to process (processes all sheets if omitted)
  -m, --model TEXT        Ollama model to use (default: mistral-nemo)
  -b, --batch-size INT    Number of responses to process concurrently (default: 3)
  --no-cache              Disable caching of model responses
```

### Examples

Process a specific sheet with a different model:
```bash
python integration.py quarterly_survey.xlsx -s "Q2 Responses" -m phi4 -o ./categorized
```

Process with larger batch size (faster on powerful machines):
```bash
python integration.py feedback.xlsx -b 5 -o ./output
```

Process without using cached responses:
```bash
python integration.py new_data.xlsx --no-cache -o ./fresh_results
```

## Input Format

The tool works with standard Excel workbooks (.xlsx files). Each column in a sheet is treated as a separate question, with rows representing individual responses.

For optimal results:
- Columns should have headers that include the question text
- Question numbering (e.g., "Q1:", "Q5.", etc.) helps with organisation
- Each sheet typically represents a separate survey or questionnaire

Example Excel structure:
```
| Q1: What is your role? | Q2: What challenges do you face? | Q3: What resources would help? |
|------------------------|----------------------------------|--------------------------------|
| Team Lead              | Time management                  | Better training                |
| Developer              | Technical complexity             | More documentation             |
| Manager                | Resource allocation              | Additional funding             |
```

## Output Format

The tool generates JSON files that contain:
1. Individual question files with categorised responses
2. Combined files for each sheet with all questions

Example output structure:
```json
{
  "sheet_name": "Survey Responses",
  "results": [
    {
      "question": "What resources would help?",
      "question_id": "question3",
      "categorized_items": [
        {
          "id": "0",
          "description": "Better training",
          "categories": ["Workforce"]
        },
        {
          "id": "1",
          "description": "More documentation",
          "categories": ["Data"]
        },
        {
          "id": "2",
          "description": "Additional funding",
          "categories": ["Funding"]
        }
      ],
      "summary": {
        "total_items": 3,
        "category_counts": {
          "Workforce": 1,
          "Data": 1,
          "Funding": 1
        }
      }
    }
  ]
}
```

## Available Categories

By default, the tool categorises responses into these categories:
- Funding
- Data
- Governance
- Workforce
- Comms and engagement
- Other

To modify these categories, edit the `CATEGORIES` list in `categorizer.py`.

## Performance Considerations

- **Model Selection**: Smaller models run faster but may be less accurate
- **Batch Size**: Higher values process more texts in parallel but require more memory
- **Caching**: Enables faster re-processing of the same data
- **File Size**: Very large Excel files may require more memory

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | Ensure all files are in the same directory |
| "Model not found" errors | Verify Ollama is running (`ollama serve`) and model is installed (`ollama list`) |
| Slow processing | Try a smaller batch size or use a smaller model |
| Excel file errors | Check that your Excel file is not corrupted or password-protected |
| Memory errors | Process individual sheets instead of the entire workbook |

## License

MIT
