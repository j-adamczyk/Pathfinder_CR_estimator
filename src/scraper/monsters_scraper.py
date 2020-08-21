from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import re
from statistics import mean
from typing import List, Match, Optional, Union

from bs4 import BeautifulSoup

from src.scraper.model import Monster
from src.scraper.utils import *

MAX_THREADS = 30
all_feats_names = get_feats_names()


def parse_monster_page(link: str) -> Union[Monster, List[Monster]]:
    """
    Parses statistics of the monster from its page.

    :param link: hyperlink to monster page
    :return: either a single monster info or list of monsters
    """
    """content_bytes: bytes = get_page_content(link)
    soup = BeautifulSoup(content_bytes, "html.parser")
    html: str = content_bytes.decode("utf-8")
    text: str = soup.get_text()"""

    text = """
    Planetar CR 16
    XP 76,800 NG Large outsider (angel, extraplanar, good) Init +8; Senses darkvision 60 ft., detect evil, detect snares and pits, low-light vision, true seeing; Perception +27 Aura protective aura
    DEFENSE
    AC 32, touch 13, flat-footed 28 (+4 Dex, +19 natural, -1 size; +4 deflection vs. evil) hp 229 (17d10+136); regeneration 10 (evil weapons and effects) Fort +19, Ref +11, Will +19; +4 vs. poison, +4 resistance vs. evil DR 10/evil; Immune acid, cold, petrification; Resist electricity 10, fire 10; SR 27
    OFFENSE
    Speed 30 ft., fly 90 ft. (good) Melee +3 holy greatsword +27/+22/+17 (3d6+15/19-20) or slam +24 (2d8+12)  Space 10 ft.; Reach 10 ft.
    Spell-Like Abilities (CL 16th)
     Constant—detect evil, detect snares and pits, discern lies (DC 20), true seeing At will—continual flame, dispel magic, holy smite (DC 21), invisibility (self only), lesser restoration, remove curse, remove disease, remove fear (DC 18), speak with dead (DC 20) 3/day—blade barrier (DC 21), flame strike (DC 22), power word stun, raise dead, waves of fatigue 1/day—earthquake (DC 25), greater restoration, mass charm monster (DC 25), waves of exhaustion
    Cleric Spells Prepared (CL 16th)
     8th—earthquake (DC 25), fire storm (DC 25) 7th—holy word (DC 24), regenerate (2) 6th—banishment(DC 23), greater dispel magic, heal, mass cure moderate wounds (DC 23) 5th—break enchantment, dispel evil (2, DC 22), plane shift (DC 22), righteous might 4th—death ward, dismissal (DC 21), neutralize poison (DC 21), summon monster IV 3rd—cure serious wounds (2), daylight, invisibility purge, summon monster III, wind wall 2nd—align weapon (2), bear’s endurance (2), cure moderate wounds (2), eagle’s splendor 1st—bless (2), cure light wounds (4), shield of faith 0 (at will)— detect magic, purify food and drink, stabilize, virtue
    STATISTICS
    Str 27, Dex 19, Con 24, Int 22, Wis 25, Cha 24 Base Atk +17; CMB +26; CMD 40 Feats Blind-Fight, Cleave, Great Fortitude, Improved Initiative, Improved Sunder, Iron Will, Lightning Reflexes, Power Attack, Toughness Skills Acrobatics +24, Craft (any one) +26, Diplomacy +27, Fly +26, Heal +24, Intimidate+27, Knowledge (history) +23, Knowledge (planes) +26, Knowledge (religion) +26, Perception +27, Sense Motive +27, Stealth +20 Languages Celestial, Draconic, Infernal; truespeech SQ change shape (alter self)
    SPECIAL ABILITIES
    Spellcasting
    Planetars cast divine spells as 16th-level clerics. They do not gain access to domains or other cleric abilities. 
    """

    # replace non-standard dash with a regular ASCII one
    text = text.replace("–", "-")

    # reduce text to the interesting part
    stat_block = re.search(r"(CR\s+[0-9/]+\s+XP[\S\s]*?)SPECIAL ABILITIES|"
                           r"(CR\s+[0-9/]+\)\s+XP[.\S\s]*?)SPECIAL ABILITIES|"
                           r"(CR\s+[0-9/]+\s+XP[\S\s]*?STATISTICS[\S\s]*?)\n\n|"
                           r"(CR\s+[0-9/]+\)\s+XP[\S\s]*?STATISTICS[\S\s]*?)\n\n|"
                           r"(CR\s+[0-9/]+\s+XP[\S\s]*?STATISTICS[\S\s]*?)|"
                           r"(CR\s+[0-9/]+\)\s+XP[\S\s]*?STATISTICS[\S\s]*)",
                           text)

    if not stat_block:
        # page probably is a list of subpages of monsters with particular subtype
        monster_links = get_subpages_links(html)
        result = [parse_monster_page(link) for link in monster_links]

        # we may encounter nested lists of monsters
        return flatten(result)

    # get all the information about the monster; if we don't get something, we
    # will have the default value from the Monster constructor
    monster = Monster()
    monster.link = link
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

    XP = re.search(r"XP\s+([0-9]+,[0-9]+)\s+|"
                   r"XP\s+([0-9]+)\s+", stat_block)
    if XP:
        XP = XP.group(1).replace(",", "")
        monster.XP = int(XP)

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
        # get rid of problematic punctuation
        senses = senses.group(1).replace(",", "").replace(".", "")

        # count "detect magic", "detect evil" etc. as senses
        monster.senses = len(re.findall("detect", senses))

        # all other senses
        for sense in ["blindsense", "blindsight", "greensight", "darkvision",
                      "lifesense", "low-light vision", "mistsight", "scent",
                      "thoughtsense", "tremorsense", "true seeing"]:
            if sense in senses:
                monster.senses += 1

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

    attacks = re.search(r"Melee([\s\S]+)|Ranged([\s\S]+)", stat_block)
    words_to_remove = {"Melee ", "Ranged ", " and ", " or "}
    translation = "|".join(words_to_remove)
    if attacks:
        attacks = attacks.group().split(")")
        attacks = [attack
                   for attack in attacks
                   if re.search(r"[\s\S]+\([0-9]+d[\s\S]+", attack)]

        ranged_index_start = None
        for index, attack in enumerate(attacks):
            if "Ranged" in attack:
                ranged_index_start = index
                break

        if ranged_index_start is not None:
            melee_attacks = attacks[:ranged_index_start]
            ranged_attacks = attacks[ranged_index_start:]
        else:
            melee_attacks = attacks
            ranged_attacks = []

        melee_attacks = [re.sub(translation, "", attack).strip()
                         for attack in melee_attacks]
        ranged_attacks = [re.sub(translation, "", attack).strip()
                          for attack in ranged_attacks]

        melee_attacks = [parse_single_attack_type(attack)
                         for attack in melee_attacks]
        ranged_attacks = [parse_single_attack_type(attack)
                          for attack in ranged_attacks]

        monster.highest_attack_bonus = max([attack["highest_bonus"]
                                            for attack
                                            in melee_attacks + ranged_attacks])

        monster.melee_attacks_num = len(melee_attacks)
        monster.melee_avg_dmg = mean([attack["avg_dmg"]
                                      for attack in melee_attacks])

        monster.ranged_attacks_num = len(ranged_attacks)
        if ranged_attacks:
            monster.ranged_avg_dmg = mean([attack["avg_dmg"]
                                           for attack in ranged_attacks])
        else:
            monster.ranged_avg_dmg = 0

    # TODO: add space and reach


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
        for i, attribute in enumerate(["strength", "dexterity",
                                       "constitution", "intelligence",
                                       "wisdom", "charisma"]):
            if attributes.group(i + 1):
                setattr(monster, attribute, attributes.group(i + 1))

    BAB_CMB_CMD = re.search(r"Base\s+Atk\s+(0|\+[0-9]+|-[0-9]+)[\s\S]+"
                            r"CMB\s+(0|\+[0-9]+|-[0-9]+)[\s\S]+"
                            r"CMD\s+(0|[0-9]+)", stat_block)
    if BAB_CMB_CMD:
        monster.BAB = int(BAB_CMB_CMD.group(1))
        monster.CMB = int(BAB_CMB_CMD.group(2))
        monster.CMD = int(BAB_CMB_CMD.group(3))

    feats = re.search(r"Feats([\s\S]+?)Skills", stat_block)
    if feats:
        feats = feats.group(1).strip().split()
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
    """html: str = get_page_content(
        "https://www.d20pfsrd.com/bestiary/bestiary-hub/monsters-by-cr/") \
        .decode("utf-8")

    monster_links: List[str] = get_official_monster_links(html)"""

    # TODO: remove this in final version, it's here for faster testing
    monster_links = ["https://www.d20pfsrd.com/bestiary/monster-listings/outsiders/angel/planetar/"]

    # if there are less than MAX_THREADS links, spawn less threads, so they are not wasted
    num_threads: int = min(MAX_THREADS, len(monster_links))
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        executor.map(parse_monster_page, monster_links)
