from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import re
from typing import List, Match, Optional, Union

from bs4 import BeautifulSoup

from scraper.model import Monster
from scraper.utils import get_feats_names, get_page_content, flatten


MAX_THREADS = 30
all_feats_names = get_feats_names()


def parse_monster_page(link: str) -> Union[Monster, List[Monster]]:
    """
    Parses statistics of the monster from its page.

    :param link: hyperlink to monster page
    :return: either a single monster info or list of monsters
    """
    content_bytes: bytes = get_page_content(link)
    soup = BeautifulSoup(content_bytes, "html.parser")
    html: str = content_bytes.decode("utf-8")
    text: str = soup.get_text()

    # replace non-standard dash with a regular ASCII one
    text = text.replace("–", "-")

    # reduce text to the interesting part
    stat_block = re.search(r"(CR[.\S\s]*?)SPECIAL ABILITIES|(CR[.\S\s]*?)\n\n", text)

    if not stat_block:
        # page probably is a list of subpages of monsters with particular subtype
        monster_links = get_subpages_links(html)
        result = []
        for link in monster_links:
            monster = parse_monster_page(link)
            result.append(monster)

        # we may encounter nested lists of monsters
        return list(flatten(result))

    # get all the information about the monster; if we don't get something, we
    # will have the default value from the Monster constructor
    monster = Monster()
    stat_block = stat_block.group()

    name = re.search(r"(.+?) - d20PFSRD", text)
    if name:
        monster.name = name.group(1)

    # division into separate blocks for parsing makes further regrexes faster
    blocks = re.match(r"([\s\S]+)"
                      r"DEFENSE([\s\S]+)"
                      r"OFFENSE([\s\S]+)"
                      r"STATISTICS([\s\S]+)", stat_block)

    parse_basic_info(blocks.group(1), monster)
    parse_defense(blocks.group(2), monster)
    parse_offense(blocks.group(3), monster)
    parse_statistics(blocks.group(4), monster)

    print(monster)
    return monster


def get_subpages_links(html_text: str) -> List[str]:
    """
    Gets monster links from a page containing list of subpages.

    :param html_text: content bytes of page decoded as string
    :return: list of links to monster pages
    """
    # remove sidebars, get only main page content
    html_text: Optional[Match[str]] = re.search(
        r"<!-- Content -->[\S\s]*Subpages([\S\s]*)", html_text)
    if not html_text:
        exit()
    else:
        html_text: str = html_text.group(1)

    links: List[str] = get_official_monster_links(html_text)

    # sometimes links are duplicated here, where some have "/" at the end, when some do not
    links = [link if not link.endswith("/")
             else link[:-1]
             for link in links]

    # guarantee uniqueness
    return list(set(links))


def parse_basic_info(stat_block: str, monster: Monster) -> None:
    """
    Parses the first part of the monster stat block, basic info like Challenge
    Rating, XP, type etc. and fills the appropriate fields in the monster object.
    Warning: this does not include name, which is before the stat block!

    :param stat_block: string with the monster statistics block
    :param monster: Monster class object to fill
    """
    CR = re.search(r"CR\s+(.+)\)\s+|CR\s+(.+)\s+", stat_block)
    if CR:
        # this handles fractional CRs through interpreting all numbers as
        # (potentially space-divided) Fraction strings
        CR = CR.group(1) if CR.group(1) else CR.group(2)
        monster.CR = float(sum(Fraction(s) for s in CR.split()))

    XP = re.search(r"XP\s+([0-9]+)\s+", stat_block)
    if XP:
        monster.XP = int(XP.group(1))

    alignment = re.search(r"\s+(LG|NG|CG|LN|N|CN|LE|NE|CE)\s+", stat_block)
    if alignment:
        monster.alignment = alignment.group(1)

    size = re.search(r"\s+(Fine|Diminutive|Tiny|Small|Medium|Large|Huge|"
                     r"Gargantuan|Colossal)\s+",
                     stat_block)
    if size:
        monster.size = size.group(1)

    creature_type = re.search(r"\s+(aberration|animal|construct|dragon|fey|"
                              r"humanoid|magical beast|monstrous humanoid|"
                              r"ooze|outsider|plant|undead|vermin)",
                              stat_block)
    if creature_type:
        monster.type = creature_type.group(1).capitalize()

    init = re.search(r"Init\s+(0|\+[0-9]+|-[0-9]+)", stat_block)
    if init:
        monster.init = int(init.group(1))

    senses = re.search(r"Senses([\S\s]+);", stat_block)
    if senses:
        senses = {sense.lower() for sense in senses.group(1).split()}
        counter = 0
        for sense in ["blindsense", "blindsight", "greensight", "darkvision",
                      "lifesense", "low-light vision", "mistsight", "scent",
                      "thoughtsense", "tremorsense"]:
            if sense in senses:
                counter += 1
        monster.senses = int(counter)

    "XP 50 N Diminutive animal Init +2; Senses blindsense 20 ft., low-light vision; Perception +6"
    perception = re.search(r"Perception\s+(0|\+[0-9]+|-[0-9]+)", stat_block)
    if perception:
        monster.perception = int(perception.group(1))


def parse_defense(stat_block: str, monster: Monster) -> None:
    """
    Parses the second part of the monster stat block, DEFENSE. It includes
    Armor Class (regular, touch and flat-footed), HP and saving throw bonuses.

    :param stat_block: string with the monster statistics block
    :param monster: Monster class object to fill
    """
    armor = re.search(r"AC\s+(0|[0-9]+)[\s\S]+"
                      r"touch\s+(0|[0-9]+)[\s\S]+"
                      r"flat-footed\s+(0|[0-9]+)",
                      stat_block)
    if armor:
        monster.AC = int(armor.group(1))
        monster.touch = int(armor.group(2))
        monster.flat_footed = int(armor.group(3))

    HP_and_HD = re.search(r"hp\s+([0-9]+)\s+\(([0-9]+).*\)\s+", stat_block)
    if HP_and_HD:
        monster.HP = int(HP_and_HD.group(1))
        monster.HD = int(HP_and_HD.group(2))

    saving_throws = re.search(r"Fort\s+(0|\+[0-9]+|-[0-9]+)[\s\S]+"
                              r"Ref\s+(0|\+[0-9]+|-[0-9]+)[\s\S]+"
                              r"Will\s+(0|\+[0-9]+|-[0-9]+)",
                              stat_block)
    if saving_throws:
        monster.fortitude = int(saving_throws.group(1))
        monster.reflex = int(saving_throws.group(2))
        monster.will = int(saving_throws.group(3))


def parse_offense(stat_block: str, monster: Monster) -> None:
    """
    Parses the third part of the monster stat block, OFFENSE. It includes
    speed with various movement types and attacks (number, types, hit bonuses
    and damage).

    :param stat_block: string with the monster statistics block
    :param monster: Monster class object to fill
    """
    speed = re.search(r"Speed\s+([0-9]+)", stat_block)
    if speed:
        monster.speed = int(speed.group(1))

    for movement_type in ["burrow", "climb", "fly"]:
        movement = re.search(movement_type + r"\s+([0-9]+)", stat_block)
        if movement:
            setattr(monster, movement_type, movement.group(1))

    # TODO: parse attacks, space and reach, remove stat block in the final version
    # example stat block for reference
    """
    CR 1/8
    XP 50 N Diminutive animal Init +2; Senses blindsense 20 ft., low-light vision; Perception +6
    DEFENSE
    AC 16, touch 16, flat-footed 14 (+2 Dex, +4 size) hp 2 (1d8–2) Fort +0, Ref +4, Will +2
    OFFENSE
    Speed 5 ft., fly 40 ft. (good) Melee bite +6 (1d3–4)* Space 1 ft.; Reach 0 ft.
    STATISTICS
    Str 1, Dex 15, Con 6, Int 2, Wis 14, Cha 5 Base Atk +0; CMB –2; CMD 3 Feats Weapon Finesse Skills Fly +16, Perception +6; Racial Modifier +4 Perception
    SPECIAL ABILITIES
    """


def parse_statistics(stat_block: str, monster: Monster) -> None:
    """
    Parses the fourth part of the monster stat block, STATISTICS. It includes
    6 attribute scores, BAB, CMB, CMD, feats and skills.

    :param stat_block: string with the monster statistics block
    :param monster: Monster class object to fill
    """
    attributes = re.search(r"Str\s+([0-9]+)[\s\S]+"
                           r"Dex\s+([0-9]+)[\s\S]+"
                           r"Con\s+([0-9]+)[\s\S]+"
                           r"Int\s+([0-9]+)[\s\S]+"
                           r"Wis\s+([0-9]+)[\s\S]+"
                           r"Cha\s+([0-9]+)",
                           stat_block)
    if attributes:
        monster.strength = int(attributes.group(1))
        monster.dexterity = int(attributes.group(2))
        monster.constitution = int(attributes.group(3))
        monster.intelligence = int(attributes.group(4))
        monster.wisdom = int(attributes.group(5))
        monster.charisma = int(attributes.group(6))

    BAB_CMB_CMD = re.search(r"Base\s+Atk\s+(0|\+[0-9]+|-[0-9]+)[\s\S]+"
                            r"CMB\s+(0|\+[0-9]+|-[0-9]+)[\s\S]+"
                            r"CMD\s+(0|[0-9]+)", stat_block)
    if BAB_CMB_CMD:
        monster.BAB = int(BAB_CMB_CMD.group(1))
        monster.CMB = int(BAB_CMB_CMD.group(2))
        monster.CMD = int(BAB_CMB_CMD.group(3))

    feats = re.search(r"Feats ([\s\S]+?) Skills", stat_block)
    if feats:
        feats = feats.group(1).split()
        monster.feats_num = 0
        # most feats have 1 or 2 words, the longest one has 6 words
        # first try to find and remove 1-word feats, than 2-word etc.
        to_remove = set()
        for curr_length in range(1, 7):
            i = 0
            while i + curr_length <= len(feats):
                feat = " ".join(feats[i:i + curr_length])
                if feat in all_feats_names:
                    monster.feats_num += 1
                    # remove the words we used to create this feat name
                    to_remove |= {j for j in range(i, i + curr_length)}
                    i = i + curr_length
                else:
                    i += 1
            feats = [feat for i, feat in enumerate(feats) if i not in to_remove]

    skills = re.search(r"Skills([\s\S]+)", stat_block)
    skills_names = {"Acrobatics", "Appraise", "Bluff", "Climb", "Craft",
                    "Diplomacy", "Disable Device", "Disguise", "Escape Artist",
                    "Fly", "Handle Animal", "Heal", "Intimidate",
                    "Knowledge (arcana)", "Knowledge (dungeoneering)",
                    "Knowledge (engineering)", "Knowledge (geography)",
                    "Knowledge (history)", "Knowledge (local)",
                    "Knowledge (nature)", "Knowledge (nobility)",
                    "Knowledge (planes)", "Knowledge (religion)", "Linguistics",
                    "Perception", "Perform", "Profession", "Ride",
                    "Sense Motive", "Sleight of Hand", "Spellcraft", "Stealth",
                    "Survival", "Swim", "Use Magic Device"}
    if skills:
        skills = skills.group(1)
        monster.skills_num = 0
        for skill in skills_names:
            if skill in skills:
                monster.skills_num += 1


def get_official_monster_links(html_text: str) -> List[str]:
    """
    Gets all the links to the single monster pages, only the official ones (no
    3rd party content).

    :param html_text: page HTML code, decoded from content bytes as string
    :return: list of links
    """
    links: List[str] = re.findall(r"<a href=.+?</a>", html_text)

    # some hyperlink list cleaning
    # 3 list comprehensions turned out to be a degree of magnitude faster than 1 for loop

    # filter out 3rd party content
    links = [link for link in links
             if not re.compile("3pp|3PP|tohc|TOHC").search(link)]

    # get only hyperlinks
    links: List[Optional[Match[str]]] = \
        [re.match(r"<a href=\"(https://www.d20pfsrd.com/bestiary/monster-listings/.+?)\">", link)
         for link in links]
    links: List[str] = [link.group(1) for link in links if link]

    return links


if __name__ == "__main__":
    # get links for monster listings for all monsters on the page
    html: str = get_page_content(
        "https://www.d20pfsrd.com/bestiary/bestiary-hub/monsters-by-cr/") \
        .decode("utf-8")

    monster_links: List[str] = get_official_monster_links(html)

    # TODO: remove this limit in final version, it's here for faster testing
    monster_links = monster_links[:1]

    # if there are less than MAX_THREADS links, spawn less threads, so they are not wasted
    num_threads: int = min(MAX_THREADS, len(monster_links))
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        executor.map(parse_monster_page, monster_links)
