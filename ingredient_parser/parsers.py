#!/usr/bin/env python3

import argparse
import json
import pickle
import os
from typing import Any, Dict, List

from .preprocess import PreProcessor

MODEL = None
pkg_dir, _ = os.path.split(__file__)
model_path = os.path.join(pkg_dir, "model.pickle")
with open(model_path, "rb") as f:
    MODEL = pickle.load(f)


def find_idx(labels: List[str], key: str) -> List[int]:
    """Find indices of elements matching key in list

    Parameters
    ----------
    labels : List[str]
        List to search for key in
    key : str
        Key to find in list
    """
    matches = []
    for idx, el in enumerate(labels):
        if el == key:
            matches.append(idx)
    return matches


def average(labels: List[str], scores: List[Dict[str, float]], key: str) -> float:
    """Average the scores for labels matching key

    Parameters
    ----------
    labels : List[str]
        List to search key for
    scores : List[float]
        Confidence score for each labels
    key : str
        Key to calculate confidence for

    Returns
    -------
    float
        Confidence, average of all labels with given key
    """
    score_list = []
    for idx, el in enumerate(labels):
        if el == key:
            score_list.append(scores[idx][key])

    if len(score_list) == 0:
        return 0

    average = sum(score_list) / len(score_list)
    return round(average, 4)


def parse_ingredient(sentence: str, confidence: bool = False) -> Dict[str, Any]:
    """Parse ingredient senetence using CRF model to return structured data

    Parameters
    ----------
    sentence : str
        Ingredient sentence to parse
    confidence : bool, optional
        Return confidence scores for labels

    Returns
    -------
    Dict[str, Any]
        Dictionary of structured data parsed from input string
    """
    if MODEL is None:
        raise Exception("Model didn't loaded.")

    processed_sentence = PreProcessor(sentence)
    tokens = processed_sentence.tokenized_sentence
    labels = MODEL.predict([processed_sentence.sentence_features()])[0]
    scores = MODEL.predict_marginals([processed_sentence.sentence_features()])[0]

    quantity = " ".join([tokens[idx] for idx in find_idx(labels, "QTY")])
    unit = " ".join([tokens[idx] for idx in find_idx(labels, "UNIT")])
    name = " ".join([tokens[idx] for idx in find_idx(labels, "NAME")])
    comment = " ".join([tokens[idx] for idx in find_idx(labels, "COMMENT")])
    other = " ".join([tokens[idx] for idx in find_idx(labels, "OTHER")])

    parsed: Dict[str, Any] = {
        "sentence": sentence,
        "quantity": quantity,
        "unit": unit,
        "name": name,
        "comment": comment,
        "other": other,
    }

    if confidence:
        parsed["confidence"] = {
            "quantity": average(labels, scores, "QTY"),
            "unit": average(labels, scores, "UNIT"),
            "name": average(labels, scores, "NAME"),
            "comment": average(labels, scores, "COMMENT"),
            "other": average(labels, scores, "OTHER"),
        }
        return parsed

    else:
        return parsed


def parse_multiple_ingredients(
    sentences: List[str], confidence: bool = False
) -> List[Dict[str, Any]]:
    """Parse multiple ingredients from text file.
    Each line of the file is one ingredient sentence

    Parameters
    ----------
    sentences : List[str]
        List of sentences to parse
    confidence : bool, optional
        Return confidence scores for labels

    Returns
    -------
    List[Dict[str, Any]]
        List of dictionaries of structured data parsed from input sentences
    """
    parsed = []
    for sent in sentences:
        parsed.append(parse_ingredient(sent, model, confidence))

    return parsed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse ingredient into structured data"
    )
    parser.add_argument("-s", "--string", help="Ingredient string to parse")
    parser.add_argument(
        "-c",
        "--confidence",
        action="store_true",
        help="Return confidence scores for labels",
    )
    parser.add_argument(
        "-f", "--file", help="Path to file of ingredient strings to parse"
    )
    args = parser.parse_args()

    with open(args.model, "rb") as f:
        model = pickle.load(f)

    if args.string is not None:
        parsed = parse_ingredient(args.string, args.confidence)
        print(json.dumps(parsed, indent=2))
    elif args.file is not None:
        parsed_multiple = parse_multiple_ingredients(args.file, args.confidence)
        print(json.dumps(parsed_multiple, indent=2))
