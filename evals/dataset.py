"""Tiny fixed eval dataset — representative NL questions over a known CSV.

Loose, property-style checks (does the answer mention the right number?) so normal LLM
output variance doesn't flap. Run against the real model.
"""

from __future__ import annotations

EVAL_CSV = b"region,product,sales\nwest,widget,100\neast,widget,200\nwest,gadget,50\neast,gadget,75\n"

EVAL_CASES = [
    {
        "name": "total_sales",
        "question": "What is the total of the sales column?",
        # 100+200+50+75 = 425
        "expect_substring": "425",
    },
    {
        "name": "rows_count",
        "question": "How many rows are in the dataset?",
        "expect_substring": "4",
    },
    {
        "name": "top_region",
        "question": "Which region has the highest total sales?",
        "expect_substring_any": ["east", "East"],
    },
]
