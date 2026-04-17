import os
from typing import Any

import pandas as pd
import pdfplumber

from services.llm_service import GroqClient


EXPECTED_COLUMNS = ["supplier", "product", "demand", "inventory", "delay"]


def parse_excel(file_path: str) -> list[dict[str, Any]]:
    if file_path.lower().endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    df.columns = [col.strip().lower() for col in df.columns]
    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = 0 if col in {"demand", "inventory", "delay"} else "unknown"

    result = (
        df[EXPECTED_COLUMNS]
        .fillna({"supplier": "unknown", "product": "unknown", "demand": 0, "inventory": 0, "delay": 0})
        .to_dict(orient="records")
    )
    return result


def parse_pdf(file_path: str) -> list[dict[str, Any]]:
    pages_text: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text() or ""
            if extracted:
                pages_text.append(extracted)
    full_text = "\n".join(pages_text)
    client = GroqClient()
    return client.extract_structured_json(full_text)


def detect_and_parse(file_path: str) -> tuple[str, list[dict[str, Any]]]:
    extension = os.path.splitext(file_path)[1].lower()
    if extension in {".xlsx", ".csv"}:
        return "excel", parse_excel(file_path)
    if extension == ".pdf":
        return "pdf", parse_pdf(file_path)
    raise ValueError("Unsupported file type. Allowed: .xlsx, .csv, .pdf")
