"""Offline checks on the committed dataset (run after `python -m scripts.prepare_data`)."""
import csv
import re
from collections import Counter

import pytest

PATH = "data/reviews.csv"
FIELDS = ["review_id", "product_id", "review_text", "rating", "review_date", "source"]


@pytest.fixture(scope="module")
def rows():
    with open(PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FIELDS
        return list(reader)


def test_size_and_balance(rows):
    assert len(rows) == 300
    assert Counter(r["rating"] for r in rows) == {str(s): 60 for s in range(1, 6)}


def test_ids_unique_and_stable_format(rows):
    ids = [r["review_id"] for r in rows]
    assert len(set(ids)) == len(ids)
    assert all(re.fullmatch(r"w\d{3}", i) for i in ids)


def test_text_length_and_source(rows):
    for r in rows:
        assert 30 <= len(r["review_text"]) <= 1500
        assert r["source"].startswith("wongnai-corpus@")


def test_no_unmasked_phone_numbers(rows):
    phone = re.compile(r"(?<!\d)0\d{1,2}[-\s]?\d{3}[-\s]?\d{3,4}(?!\d)")
    assert not [r["review_id"] for r in rows if phone.search(r["review_text"])]


def test_raw_download_is_gitignored():
    assert "data/raw/" in open(".gitignore", encoding="utf-8").read().splitlines()
