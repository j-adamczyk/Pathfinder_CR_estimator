import collections
import re
from typing import Dict, Set, Tuple, Union

import requests


def get_page_content(link: str) -> bytes:
    """
    Makes request and returns response content if status code was OK.

    :param link: hyperlink to page
    :return: response content
    """
    request: requests.models.Response = requests.get(link)

    if request.status_code != requests.codes.ok:
        raise ConnectionError("Page", link, "returned status code",
                              request.status_code)

    return request.content


def flatten(iterable):
    """
    Flattens arbitrarily nested iterable structures.
    Warning: for dictionaries it only flattens keys and ignores values!

    :param iterable: nested iterables to be flattened
    :return: elements from all iterables flattened into the list
    """
    # code shamelessly taken from StackOverflow, thanks to Noctis Skytower
    # for this pretty solution
    iterator = iter(iterable)
    array, stack = collections.deque(), collections.deque()
    while True:
        try:
            value = next(iterator)
        except StopIteration:
            if not stack:
                return list(array)
            iterator = stack.pop()
        else:
            if not isinstance(value, str) \
               and isinstance(value, collections.abc.Iterable):
                stack.append(iterator)
                iterator = iter(value)
            else:
                array.append(value)


def get_feats_names() -> Set[str]:
    """
    Parses page with feats names and returns their set.

    :return: set of names of feats
    """
    content_bytes: bytes = get_page_content("https://www.d20pfsrd.com/feats/")
    html: str = content_bytes.decode("utf-8")
    html = re.search(r"General Feats</a></span></h4>([\s\S]+)", html).group(1)

    feats = re.findall(r"<a href=\"https://www.d20pfsrd.com/feats/.*?\">(.*?)</a>", html)
    feats = {re.search(r"(.+)\(|(.+)", feat).group() for feat in feats}
    feats = {feat if not feat.endswith("(")
             else feat[:-1].rstrip()
             for feat in feats}

    return feats


def get_crit_info(text: str) -> Tuple[float, int]:
    """
    Calculates critical hit chance and multiplier from string. For example:
    - 20: 5%
    - 19-20: 10%
    - 18-20: 15%
    If the range is larger than only 20 (5%), the multiplier is 2. Otherwise
    the multiplier (x2, x3 or x4) may be specified.

    Therefore, the formula is either 0.05 (for 20) or:
    (20 - lower_bound + 1) * 0.05

    :param text: string with critical chance
    :return: critical chance as float, rounded to 2 decimal places (so to
    nearest 0.05) and critical multiplier as integer
    """
    lower_bound = re.search(r"(1[0-9])-20", text)
    if not lower_bound:
        crit_chance = 0.05
    else:
        lower_bound = int(lower_bound.group(1))
        crit_chance = round((20 - lower_bound + 1) * 0.05, 2)

    crit_multiplier = re.search(r"x[0-9]", text)
    if crit_multiplier:
        crit_multiplier = crit_multiplier.group()
        crit_multiplier = crit_multiplier[1:]  # remove "x"
        crit_multiplier = int(crit_multiplier)
    else:
        crit_multiplier = 2

    return crit_chance, crit_multiplier


def parse_single_attack_type(text: str) -> Dict[str, Union[int, float]]:
    """
    Parses single attack type string in format:
    ATTACK NAME +X/+Y/+Z/.../-A/-B (AdB+C/19-20)
    e. g. short sword +3 (1d6+1/19-20)

    Returned dict:
    - "attack_num" - number of attacks, e. g. for +5/+3/-5 it would be 3
    - "highest_bonus" - largest attack bonus, e. g. for +5/+3/-5 it would be +5
    - "avg_dmg" - average damage dealt with a single attack of this type;
    critical damage is included proportionately to the crit change (critical
    range)

    :param text: single attack string to parse
    :return: dictionary with keys and values described above
    """
    result = {"attacks_num": 0,
              "highest_bonus": 0,
              "avg_dmg": 0}

    bonuses = re.search(r"([0-9+\-/]+)\s+\(", text)
    if bonuses:
        bonuses = bonuses.group()
        result["attacks_num"] = bonuses.count("/") + 1

        bonuses = re.search(r"\+[0-9]+|-[0-9]+", bonuses).group()
        # since bonuses are always sorted descending, we can take the first one
        result["highest_bonus"] = int(bonuses)
    else:
        return result

    attack_effects = re.search(r"\((.+)", text)
    if attack_effects:
        attack_effects = attack_effects.group(1)
        attack_effects = re.match(r"([0-9]+d[0-9]+[+|\-][0-9]+)(.+)|"
                                  r"([0-9]+d[0-9]+)(.+)",
                                  attack_effects)

        damage = attack_effects.group(1) if attack_effects.group(1) \
            else attack_effects.group(3)
        crit_effect = attack_effects.group(2) if attack_effects.group(2) \
            else attack_effects.group(4)

        damage = re.match(r"([0-9]+)d([0-9]+)([+|\-][0-9]+|)", damage)
        die_num = int(damage.group(1))
        die_size = int(damage.group(2))
        dmg_bonus = int(damage.group(3)) if damage.group(3) else 0

        # X-sided die roll average value is just a mean (expected) value for
        # discrete uniform probability distribution with values in range [1, X]
        # therefore (1 + X) / 2
        avg_dmg = die_num * ((1 + die_size) / 2) + dmg_bonus

        # use critical hits in average damage calculation: critical hits are
        # really just like additional attacks with % of chances of happening,
        # which directly changes their damage
        crit_chance, crit_multiplier = get_crit_info(crit_effect)

        avg_dmg += crit_chance * avg_dmg * (crit_multiplier - 1)
        avg_dmg = round(avg_dmg * 2) / 2  # round to nearest 0.5

        result["avg_dmg"] = avg_dmg

    return result
