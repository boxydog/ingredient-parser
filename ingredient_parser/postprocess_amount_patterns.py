#!/usr/bin/env python3

from typing import Any


def match_pattern(
    tokens: list[str], labels: list[str], pattern: list[str]
) -> list[tuple[int]]:
    """Find a pattern of labels and return the indicesof the start and end of match.

    For example, consider the sentence:
    One 15-ounce can diced tomatoes, with liquid

    It has the tokens and labels:
    ['1', '15', 'ounce', 'can', 'diced', 'tomatoes', ',', 'with', 'liquid']
    ['QTY', 'QTY', 'UNIT', 'UNIT', 'COMMENT', 'NAME', 'COMMA', 'COMMENT', 'COMMENT']

    If we search for the pattern:
    ["QTY", "QTY", "UNIT", "UNIT"]

    Then we get:
    [(0, 3)]

    Raises
    ------
    ValueError
        When the length of tokens and labels are not equal.

    Parameters
    ----------
    tokens : list[str]
        List of tokens to return matching pattern from.
    labels : list[str]
        List of labels to find matching pattern in.
    pattern : list[str]
        Pattern to match inside labels.

    Returns
    -------
    list[tuple[int]]
        List of matching lists of token.
    """

    if len(tokens) != len(labels):
        raise ValueError("The length of tokens and labels must be the same.")

    if len(pattern) > len(tokens):
        # We can never find a match.
        return []

    plen = len(pattern)
    matches = []
    for i in range(len(labels)):
        # Short circuit: If the label[i] is not equal to the first element of pattern
        # skip to next iteration
        if labels[i] == pattern[0] and labels[i : i + plen] == pattern:
            matches.append((i, i + plen))

    return matches


def sizable_unit_pattern(
    tokens: list[str], labels: list[str], scores: list[float]
) -> list[dict[str, Any]]:
    """Identify sentences which match the pattern where there is a quantity-unit pair
    split by one or mroe quantity-unit pairs e.g.

    * 1 28 ounce can
    * 2 17.3 oz (484g) package

    Return the correct sets of quantities and units, or an empty list.

    For example, for the sentence: 1 28 ounce can; the correct amounts are:
    [
        {"quantity": "1", "unit": ["can"], "score": [...]},
        {"quantity": "28", "unit": ["ounce"], "score": [...]},
    ]

    Parameters
    ----------
    tokens : list[str]
        Tokens for input sentence
    labels : list[str]
        Labels for input sentence tokens
    scores : list[float]
        Scores for each label

    Returns
    -------
    list[dict[str, Any]]
        List of dictionaries for each set of amounts.
        The dictionary contains:
            quantity: str
            unit: list[str]
            score: list[float]
    """
    # We assume that the pattern will not be longer than the first element defined here.
    patterns = [
        ["QTY", "QTY", "UNIT", "QTY", "UNIT", "QTY", "UNIT", "UNIT"],
        ["QTY", "QTY", "UNIT", "QTY", "UNIT", "UNIT"],
        ["QTY", "QTY", "UNIT", "UNIT"],
    ]

    # List of possible units at end of pattern that constitute a match
    end_units = [
        "bag",
        "block",
        "box",
        "can",
        "envelope",
        "jar",
        "package",
        "packet",
        "tin",
    ]

    # Only keep QTY and UNIT tokens
    tokens = [token for token, label in zip(tokens, labels) if label in ["QTY", "UNIT"]]
    scores = [score for score, label in zip(scores, labels) if label in ["QTY", "UNIT"]]
    labels = [label for label in labels if label in ["QTY", "UNIT"]]

    amount_groups = []
    for pattern in patterns:
        for match in match_pattern(tokens, labels, pattern):
            matching_tokens = tokens[match[0] : match[1]]
            matching_scores = scores[match[0] : match[1]]
            # If the pattern ends with one of end_units, we have found a match for
            # this pattern!
            if matching_tokens[-1] in end_units:
                # The first pair is the first and last items
                first = {
                    "quantity": matching_tokens.pop(0),
                    "unit": [matching_tokens.pop(-1)],
                    "score": [matching_scores.pop(0), matching_scores.pop(-1)],
                }
                amount_groups.append(first)

                for i in range(0, len(matching_tokens), 2):
                    quantity = matching_tokens[i]
                    unit = matching_tokens[i + 1]
                    scores = matching_scores[i : i + 1]
                    group = {
                        "quantity": quantity,
                        "unit": [unit],
                        "score": scores,
                    }
                    amount_groups.append(group)

    return amount_groups


def fallback_pattern(
    tokens: list[str], labels: list[str], scores: list[float]
) -> list[dict[str, Any]]:
    """Fallback pattern for grouping quantities and units into amounts.

    Parameters
    ----------
    tokens : list[str]
        Tokens for input sentence
    labels : list[str]
        Labels for input sentence tokens
    scores : list[float]
        Scores for each label

    Returns
    -------
    list[dict[str, Any]]
        List of dictionaries for each set of amounts.
        The dictionary contains:
            quantity: str
            unit: list[str]
            score: list[float]
    """
    groups = []
    prev_label = None
    for token, label, score in zip(tokens, labels, scores):
        if label == "QTY":
            groups.append({"quantity": token, "unit": [], "score": [score]})

        elif label == "UNIT":
            # No quantity found yet, so create a group without a quantity
            if len(groups) == 0:
                groups.append({"quantity": "", "unit": [], "score": []})

            if prev_label == "COMMA":
                groups[-1]["unit"].append(",")

            groups[-1]["unit"].append(token)
            groups[-1]["score"].append(score)

        prev_label = label

    return groups
