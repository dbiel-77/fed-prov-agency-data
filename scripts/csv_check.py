import pandas as pd
import unicodedata
import re

# Define suspicious Unicode patterns
SUSPICIOUS_CHARS = [
    "\u200B",  # Zero-width space
    "\u200C",  # Zero-width non-joiner
    "\u200D",  # Zero-width joiner
    "\u2060",  # Word joiner
    "\uFEFF",  # BOM
    "\u00A0",  # Non-breaking space
]

# Precompiled regex to detect raw unicode sequences (e.g., \u00A0)
RAW_UNICODE_REGEX = re.compile(r"\\u[0-9a-fA-F]{4}")

def nontext_finder(path, encoding="utf-8"):
    """
    Scan a CSV file for invisible or suspicious Unicode characters.
    
    Parameters:
        path (str): Path to the CSV file.
        encoding (str): Encoding of the file (default is UTF-8).
    
    Returns:
        List of (row_idx, col, issue_description, raw_value)
    """
    df = pd.read_csv(path, dtype=str, encoding=encoding)
    findings = []

    for row_idx, row in df.iterrows():
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                continue
            for c in val:
                if c in SUSPICIOUS_CHARS:
                    name = unicodedata.name(c, "UNKNOWN")
                    findings.append((row_idx, col, f"Suspicious char: {name}", val))
            if RAW_UNICODE_REGEX.search(val):
                findings.append((row_idx, col, "Raw Unicode escape sequence", val))
    
    return findings
