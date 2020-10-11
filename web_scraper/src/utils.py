import collections
import re
from typing import Dict, List, Set, Tuple, Union

import requests


def get_page_content(link: str) -> bytes:
    """
    Makes request and returns response content if status code was OK.

    :param link: hyperlink to page
    :return: response content
    """
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; "
                             "Intel Mac OS X 10_11_6) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/61.0.3163.100 Safari/537.36"}

    response = requests.get(link, headers=headers)

    html = response.content.decode("utf-8")

    # we can get 404 in 2 cases: true error or redirect page for malformed
    # URLs with suggestions; in the second case we should return content
    # despite code 404
    if response.status_code != requests.codes.ok and \
            "We've found at least one possible match" not in html:
        raise ConnectionError("Page", link, "returned status code",
                              response.status_code)

    return response.content


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


def get_monster_links(html_text: str) -> List[str]:
    """
    Gets all the links to the single monster pages, only the official ones (no
    3rd party content).

    :param html_text: page HTML code, decoded from content bytes as string
    :return: list of links
    """
    links = re.findall(r"<a href=.+?</a>", html_text)

    # some hyperlink list cleaning
    # 3 list comprehensions turned out to be a degree of magnitude faster than 1 for loop

    # filter out 3rd party content
    links = [link for link in links
             if not re.compile("3pp|3PP|tohc|TOHC").search(link)]

    # get only hyperlinks
    links = [re.match(r"<a href=\"(https://www.d20pfsrd.com/bestiary/monster-listings/.+?)\">", link)
             for link in links]
    links = [link.group(1) for link in links if link]

    return links


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


def get_subpages_links(html_text: str) -> List[str]:
    """
    Gets monster links from a page containing list of subpages.

    :param html_text: content bytes of page decoded as string
    :return: list of links to monster pages
    """
    # remove sidebars, get only main page content
    content = re.search(r'<!-- Content -->[\S\s]*'
                        r'<div class="ogn-childpages"[\s\S]*'
                        r'Subpages([\S\s]*?)'
                        r'</div>',
                        html_text)
    if not content:
        return []
    else:
        content = content.group(1)

    links = get_monster_links(content)

    # sometimes links are duplicated here, where some have "/" at the end, when some do not
    links = [link if not link.endswith("/")
             else link[:-1]
             for link in links]

    # guarantee uniqueness
    return list(set(links))


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
    if not text:
        # may happen if there is no critical hit info, assume defaults
        return 0.05, 2

    lower_bound = re.search(r"(1[0-9])-20", text)
    if lower_bound:
        lower_bound = int(lower_bound.group(1))
        crit_chance = round((20 - lower_bound + 1) * 0.05, 2)
    else:
        crit_chance = 0.05

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
              "avg_dmg": 0,
              "full_dmg": 0}

    to_remove_regex = r"melee|Melee|ranged|Ranged|touch"
    text = re.sub(to_remove_regex, "", text)

    bonuses = re.search(r"([0-9+\-/]+)\s+\(", text)
    if not bonuses:
        # check if the attack bonus is not mismatched, e.g. +1 javelin (...)
        # instead of proper javelin +0 (...)
        # this has to be a fallback option, since we can have magical attacks
        # like +1 longsword +6/+1 (...) and we want to capture 2nd group of
        # numbers (+6/+1 here)
        bonuses = re.search(r"([0-9+\-/]+)\s*[a-zA-Z\-]+\s*\(", text)

    if bonuses:
        bonuses = bonuses.group(1)
        result["attacks_num"] = bonuses.count("/") + 1

        bonuses = re.search(r"\+[0-9]+|-[0-9]+", bonuses).group()
        # since bonuses are always sorted descending, we can take the first one
        result["highest_bonus"] = int(bonuses)
    else:
        return result

    if result["attacks_num"] == 1:
        # attacks could be natural attacks, in which case there are no "/",
        # multiple attacks are denoted by number before attack name
        num_attacks = re.match(r"[0-9]+", text)
        if num_attacks:
            num_attacks = num_attacks.group()
            result["attacks_num"] = int(num_attacks)

    attack_effects = re.search(r"\((.+)", text)
    if attack_effects:
        attack_effects_str = attack_effects.group(1)
        attack_effects = re.search(r"([0-9]+d[0-9]+[+|\-][0-9]+)(.*)|"
                                   r"([0-9]+d[0-9]+)(.*)",
                                   attack_effects_str)

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

        for _, die_num, die_size in re.findall(
                r"(\+|plus)\s*([0-9]+)d([0-9]+)", attack_effects_str):
            die_num = int(die_num)
            die_size = int(die_size)
            avg_bonus_dmg = die_num * ((1 + die_size) / 2)
            avg_dmg += avg_bonus_dmg

        result["avg_dmg"] = avg_dmg

    result["full_dmg"] = result["attacks_num"] * result["avg_dmg"]

    return result


def process_attacks_logic(attacks, logic):
    """
    Applies logical operators between attacks ("and", "or"), grouping attacks
    and taking the attack groups with higher overall damage. For "and",
    damage is summed up. For "or", group with higher damage is chosen.

    For alternatives, ties are broken in favor of the attack with higher:
    avg_dmg, attacks_num, highest_bonus.
    If all of those fail, the attack with lower index is retained.

    :param attacks: list of dictionaries with individual attack types' stats
    :param logic: list of elements "and"/"or"/"" (logical operator between
    this and previous attack, or lack thereof)
    """
    attacks = attacks.copy()
    if not attacks:
        return []

    # "and" binds stronger than "or", so we group attacks first, then take
    # alternatives

    # iterating with indices descending avoids problems with indexing while
    # iterating and deleting elements

    # "and" part
    i = len(attacks)
    while i > 0:
        i -= 1
        if logic[i] == "and":
            # current attack and previous one are "and"-ed
            prev_atk = attacks[i - 1]
            curr_atk = attacks[i]

            prev_atk["highest_bonus"] = max(prev_atk["highest_bonus"],
                                            curr_atk["highest_bonus"])
            for attr in ["avg_dmg", "attacks_num", "full_dmg"]:
                prev_atk[attr] = prev_atk[attr] + curr_atk[attr]

            del attacks[i]
            del logic[i]

    # "or" part
    i = len(attacks)
    while i > 0:
        i -= 1
        if logic[i] == "or":
            # current attack and previous one are "or"-ed
            prev_atk = attacks[i - 1]
            curr_atk = attacks[i]
            choice = None  # choose attack to delete
            for feature in ["full_dmg", "avg_dmg", "attacks_num",
                            "highest_bonus"]:
                prev = prev_atk[feature]
                curr = curr_atk[feature]
                if prev < curr:
                    # choose prev_atk to delete
                    choice = i - 1
                    break
                elif prev > curr:
                    # choose curr_atk to delete
                    choice = i
                    break
                # else values equal, need to check further features

            if choice is not None:
                # found unequal value to choose
                del attacks[choice]
            else:
                # everything was tied, remove curr_atk
                del attacks[i]

    return attacks
