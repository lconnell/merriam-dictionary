# Merriam-Webster Dictionary Scrape Script

This script scrapes the Merriam-Webster dictionary API to fetch definitions and examples for words saved in the user's dictionary.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export MW_EMAIL="your_email"
export MW_PASSWORD="your_password"
export DICT_API_KEY="your_api_key"
```

## Usage

```bash
python dictionary_scrape.py
```

### Optional Arguments

- `--no-stdout`: Disable logging to stdout
- `--no-logfile`: Disable logging to a file

### Logging

Logs are written to `dictionary_scrape.log` by default.

## Output

The script outputs a JSON file containing the following structure:

```json
{
    "total_words": 123,
    "data": [
        {
            "word": "word1",
            "description": "description1",
            "examples": ["example1", "example2"]
        },
        ...
    ]
}
```

The output is also logged to `dictionary_output.json` by default.

## Notes

- The script uses Selenium to log in and extract cookies from the Merriam-Webster website.
- It then uses the dictionary API to fetch definitions and examples for each word.
- The script is designed to be polite to the server by adding a delay between requests.

## License

MIT License