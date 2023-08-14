#!/usr/bin/env python3

import argparse
import xml.etree.ElementTree as ET
from itertools import pairwise
from pathlib import Path

from nltk.tokenize import RegexpTokenizer
from tqdm import tqdm
from training_utils import load_csv

# Tokeniser from preprocess.py
group_a = r"[\w!\#\$\£\€%\&'\*\+\-\.:;>=<\?@\^_`\\\|\~]+"
group_b = r"[\(\)\[\]\{\}\,\"/]"
REGEXP_TOKENIZER = RegexpTokenizer(rf"{group_a}|{group_b}", gaps=False)


def score_sentence_similarity(first: str, second: str) -> float:
    """Calculate Dice coefficient for two strings.

    The dice coefficient is a measure of similarity determined by calculating
    the proportion of shared bigrams.

    Parameters
    ----------
    first : str
        First string
    second : str
        Second string

    Returns
    -------
    float
        Similarity score between 0 and 1.
        0 means the two strings do not share any bigrams.
        1 means the two strings are identical.
    """

    if first == second:
        # Indentical sentences have maximum score of 1
        return 1

    first_tokens = set(REGEXP_TOKENIZER.tokenize(first))
    second_tokens = set(REGEXP_TOKENIZER.tokenize(second))

    intersection = first_tokens & second_tokens

    return 2.0 * len(intersection) / (len(first_tokens) + len(second_tokens))


def create_html_table(
    indices: list[int],
    sentences: list[str],
    labels: list[dict[str, str]],
    sentence_source: list[tuple[str, int]],
) -> ET.Element:
    """Create HTM table to show similar sentences and their labels

    Parameters
    ----------
    indices : list[int]
        Indices of sentences to turn into table
    sentences : list[str]
        List of all sentences
    labels : list[dict[str, str]]
        List of labels for each sentence

    """
    table = ET.Element("table")

    header_tr = ET.Element("tr")
    for heading in [
        "Dataset",
        "Index",
        "Sentence",
        "Name",
        "Quantity",
        "Unit",
        "Comment",
    ]:
        td = ET.Element("td", attrib={"class": "row-heading"})
        td.text = heading
        header_tr.append(td)

    table.append(header_tr)

    for idx in indices:
        sentence = sentences[idx]
        sentence_labels = labels[idx]
        dataset, dataset_idx = sentence_source[idx]

        tr = ET.Element("tr")

        dataset_td = ET.Element("td", attrib={"class": "row"})
        dataset_td.text = dataset
        tr.append(dataset_td)

        index_td = ET.Element("td", attrib={"class": "row"})
        index_td.text = str(dataset_idx + 2)
        tr.append(index_td)

        sentence_td = ET.Element("td", attrib={"class": "row"})
        sentence_td.text = sentence
        tr.append(sentence_td)

        name_td = ET.Element("td", attrib={"class": "row"})
        name_td.text = sentence_labels["name"]
        tr.append(name_td)

        quantity_td = ET.Element("td", attrib={"class": "row"})
        quantity_td.text = sentence_labels["quantity"]
        tr.append(quantity_td)

        unit_td = ET.Element("td", attrib={"class": "row"})
        unit_td.text = sentence_labels["unit"]
        tr.append(unit_td)

        comment_td = ET.Element("td", attrib={"class": "row"})
        comment_td.text = sentence_labels["comment"]
        tr.append(comment_td)

        table.append(tr)

    return table


def results_to_html(
    similar: dict[int, list[int]],
    sentences: list[str],
    labels: list[dict[str, str]],
    sentence_source: list[tuple[str, int]],
) -> None:
    """Output similarity results to html file.
    The file contains a table for each group of similar sentences

    Parameters
    ----------
    similar : dict[int, list[int]]
        Dictionary of sentence index and list of similar sentence indices
    sentences : list[str]
        List of ingredient sentences
    labels : list[dict[str, str]]
        List of dictionary of ingredient sentence labels
    sentence_source : list[tuple[str, int]]
        List of tuples of (dataset_name, index_in_dataset) for each ingredient sentence
    """
    html = ET.Element("html")
    head = ET.Element("head")
    body = ET.Element("body")
    html.append(head)
    html.append(body)

    style = ET.Element("style", attrib={"type": "text/css"})
    style.text = """
    body {
      font-family: sans-serif;
      margin: 2rem;
    }
    table {
      margin-bottom: 2rem;
      border-collapse: collapse;
      border: black 3px solid;
    }
    td {
      padding: 0.5rem 1rem;
      border: black 1px solid;
    }
    .mismatch {
      font-weight: 700;
      background-color: #CC6666;
    }
    .row-heading {
      font-style: italic;
      background-color: #ddd;
    }
    """
    head.append(style)

    heading = ET.Element("h1")
    heading.text = "Similar sentences and their labels"
    body.append(heading)

    for k, v in similar.items():
        idx = [k] + v
        table = create_html_table(idx, sentences, labels, sentence_source)
        body.append(table)

    ET.indent(html, space="    ")
    with open("consistency_results.html", "w") as f:
        f.write("<!DOCTYPE html>\n")
        f.write(ET.tostring(html, encoding="unicode", method="html"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""Data cleaning helper function.\n
        Check the consistency of labels for similar sentences."""
    )
    parser.add_argument(
        "--datasets",
        "-d",
        action="extend",
        dest="datasets",
        nargs="+",
        help="Datasets in csv format",
    )
    parser.add_argument(
        "-n",
        "--number",
        default=30000,
        type=int,
        help="Number of entries in dataset to check",
    )
    args = parser.parse_args()

    print("[INFO] Loading dataset.")
    sentences, labels, sentence_source = [], [], []
    for dataset in args.datasets:
        dataset_id = Path(dataset).name.split("-")[0]
        dataset_sents, dataset_labels = load_csv(dataset, args.number)

        dataset_sentence_source = [(dataset_id, i) for i in range(len(dataset_sents))]
        sentence_source.extend(dataset_sentence_source)

        sentences.extend(dataset_sents)
        labels.extend(dataset_labels)

    similar = {}
    unmatched_indices = set(range(len(sentences)))
    # This set contains the index of each entry in the dataframe
    # Once an input has been matched, we will remove it's index from this set
    # If the index is not in the set, we cannot match it again,
    # nor will we find matches for it
    for i, sentence in tqdm(
        enumerate(sentences), total=len(sentences), unit="sentence"
    ):
        if i not in unmatched_indices:
            continue

        unmatched_indices.remove(i)

        scores = [score_sentence_similarity(sentence, other) for other in sentences[i:]]
        matches = [
            i + j
            for j, score in enumerate(scores)
            if score > 0.85 and i + j in unmatched_indices
        ]

        for m in matches:
            unmatched_indices.remove(m)

        if len(matches) > 0:
            similar[i] = matches

    max_similarity = dict(
        sorted(similar.items(), key=lambda item: len(item[1]), reverse=True)
    )

    results_to_html(max_similarity, sentences, labels, sentence_source)
