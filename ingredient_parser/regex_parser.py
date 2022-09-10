#!/usr/bin/env python3

import re
from itertools import chain

from .parsers import ParsedIngredient
from .preprocess import PreProcessor

UNITS = {
    "tablespoon": ["tbsp", "tbsps", "tablespoon", "tablespoons", "Tbsp"],
    "teaspoon": ["tsp", "tsps", "teaspoon", "teaspoons"],
    "gram": ["g", "gram", "grams", "g can", "g cans", "g tin", "g tins"],
    "kilogram": ["kg", "kilogram", "kilograms"],
    "liter": ["l", "liter", "liters", "litre", "litres"],
    "milliliter": ["ml", "milliliter", "milliliters"],
    "pinch": ["pinch", "pinches"],
    "handful": ["handful", "handfuls"],
    "clove": ["cloves", "clove"],
    "sprig": ["sprig", "sprigs"],
    "stick": ["stick", "sticks"],
    "dimension": ["cm", "inch", "'"],
    "cup": ["cup", "cups", "mug", "mugs"],
    "bunch": ["bunches", "bunch"],
    "rasher": ["rasher", "rashers"],
    "ounce": ["ounce", "ounces", "oz", "oz."],
    "pound": ["pound", "pounds", "lb", "lbs", "lb.", "lbs."],
    "wedge": ["wedge", "wedges"],
}
UNIT_MODIFIERS = ["small", "medium", "medium-size", "large", "big", "heaped", "heaping", "fat", "scant"]
# Convert values to list
UNITS_LIST = list(chain.from_iterable(UNITS.values()))
# Sort list in order of decreasing length. This is important for the regex matching, so we don't match a shorter substring
UNITS_LIST.sort(key=lambda x: len(x), reverse=True)

# This matches an integer, decimal number or range (e.g. 1, 0.5, 1-2)
QUANTITY_RE = r"""
(?P<quantity>(?:        # Creates a match group called quantity. Match everything inside the parentheses
(^\d+\s*x\s)?           # Optional capture group that matches e.g. 1x or 1 x followed by a space
\d+                     # Match at least one number
([\.\-]\d+)?            # Optionally matches a decimal point followed by at least one number, or a - followed by at least one number
))
"""
# This matches any string in the list of sizes and/or units
UNITS_RE = rf"""
(?P<unit>(?:                        # Creates a match group called unit
(({"|".join(UNIT_MODIFIERS)})\s)?   # Optionally match a size before the unit. Join the sizes in an OR list
(({"|".join(UNITS_LIST)})\s)?      # Optionally match a unit. Join all ingredients into a giant OR list
))                                  # Make this match group optional
"""
# Create full ingredient parser regular expression
PARSER_RE = rf"""
{QUANTITY_RE}           # Use QUANTITY_RE from above
\s*                     # Match zero or more whitespace characters
{UNITS_RE}              # Use UNITS_RE from above
(?P<name>(?:.*))        # Match zero of more characters in a match group called name
"""
# Precompile parser regular expression
PARSER_PATTERN = re.compile(PARSER_RE, re.VERBOSE)


def parse_ingredient_regex(sentence: str) -> ParsedIngredient:
    """Parse an ingredient senetence using regular expression based approach to return structured data.

    This parser uses a regular expression to attempt to extract information from the sentence.
    For this to work, a basic structure of the sentence is assumed:
    [optional quantity] [optional unit] [name], [comment]

    The quantity regex matches integers, decimals and ranges. Sentences cleaned using the PreProcessor class before being passed
    to the regular expression so fractions and other formats for quantities are converted to those listed.

    The unit regex matches from a predefined list of units. If the unit in the sentence is not in this list, it will end up in the name.
    The unit can be preceeded by an optional modifier such as small, medium, large.

    Following any quantity and/or unit, all subsquent characters in the sentence are captured in a single regex capture group.
    An attempt is then made to split this string at the first comma.
    If successful, the first part becomes the name and the second part becomes the comment.
    If unsuccesful (because there is no comma), the whole string is returned as the name.

    Parameters
    ----------
    sentence : str
        Ingredient sentence to parse

    Returns
    -------
    ParsedIngredient
        Dictionary of structured data parsed from input string

    Examples
    --------
    >>> parse_ingredient_regex("2 yellow onions, finely chopped")
    {'sentence': '2 yellow onions, finely chopped', 'quantity': '2', 'unit': '', 'name': 'yellow onions', 'comment': 'finely chopped', 'other': ''}

    >>> parse_ingredient_regex("100 ml milk")
    {'sentence': '100 ml milk', quantity': '100', 'unit': 'ml', 'name': 'milk', 'comment': '', 'other': ''}

    >>> parse_ingredient_regex("1 onion, finely chopped")
    {'sentence': '1 onion, finely chopped', quantity': '1', 'unit': '', 'name': 'onion', 'comment': 'finely chopped', 'other': ''}

    >>> parse_ingredient_regex("2 1/2 cups plain flour")
    {'sentnece': '2 1/2 cups plain flour', quantity': '2.5', 'unit': 'cups', 'name': 'plain flour', 'comment': '', 'other': ''}

    >>> parse_ingredient_regex("2 1/2 cups plain flour")
    {'sentnece': '12 heaped tsp ground cumin', quantity': '12', 'unit': 'heaped tsp', 'name': 'ground cumin', 'comment': '', 'other': ''}

    >>> parse_ingredient_regex("2 1/2 cups plain flour")
    {'sentnece': '2 medium sweet potatoes, peeled and chopped into 1-inch cubes', quantity': '2', 'unit': 'medium', 'name': 'sweet potatoes', 'comment': 'peeled and chopped into 1-inch cubes', 'other': ''}
    """
    parsed: ParsedIngredient = {
        "sentence": sentence,
        "quantity": "",
        "unit": "",
        "name": "",
        "comment": "",
        "other": "",
    }

    processed_sentence = PreProcessor(sentence)
    res = PARSER_PATTERN.match(processed_sentence.sentence)
    if res is not None:

        parsed["quantity"] = (res.group("quantity") or "").strip()
        parsed["unit"] = (res.group("unit") or "").strip()

        # Split name by comma, but at most one split
        # This is attempt to split the comment from the name
        name = res.group("name" or "").split(",", 1)
        if len(name) > 1:
            parsed["name"] = name[0].strip()
            parsed["comment"] = name[1].strip()
        else:
            parsed["name"] = name[0].strip()

    return parsed