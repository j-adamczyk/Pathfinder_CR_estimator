from fractions import Fraction
from statistics import median

from bs4 import BeautifulSoup

from web_scraper.src.model import Monster
from web_scraper.src.utils import *  # we use all utility functions

all_feats_names = get_feats_names()  # threads only read this, so it's safe


def parse_monster_page(link: str) -> Union[List[Monster], None]:
    """
    Parses statistics of the monster from its page.

    :param link: hyperlink to monster page
    :return: either a single monster info or list of monsters
    """
    try:
        content_bytes: bytes = get_page_content(link)
    except ConnectionError as e:
        # may happen if page is malformed
        return None
    soup = BeautifulSoup(content_bytes, "html.parser")
    html: str = content_bytes.decode("utf-8")
    text: str = soup.get_text()

    # replace non-standard dash with a regular ASCII one
    text = text.replace("–", "-")

    # for some unexplainable reason Pathfinder marks 0.5 as "-1/2", replace it
    # with normal notation
    text = text.replace("-1/2", ".5")

    # fix some possible typos
    text = text.replace("Xp", "XP")

    # reduce text to the interesting part
    stat_block = re.search(
        r"(CR\s*[0-9/]+\)?[\s]*?\(?XP[\S\s]*?)SPECIAL ABILITIES|"
        r"(CR\s*[0-9/]+\)?[\s]*?\(?XP[\S\s]*?STATISTICS[\S\s]*)\n\n|"
        r"(CR\s*[0-9/]+\)?[\s]*?\(?XP[\S\s]*?STATISTICS[\S\s]*)",
        text)

    # also get additional pages that may be linked; may be empty list
    subpages_links = get_subpages_links(html)
    subpages_monsters = [parse_monster_page(link) for link in subpages_links
                         if "summon" not in link]

    # filter out possible None values
    subpages_monsters = [monster for monster in subpages_monsters if monster]

    subpages_monsters = flatten(subpages_monsters)

    if not stat_block:
        # we may have a malformed URL, but d20pfsrd managed to create a
        # suggestions page with redirects
        suggestion = re.search(r"We've found at least one possible match "
                               r"for the page you really want([\s\S]*)",
                               html)
        if suggestion:
            suggestion = suggestion.group(1)
            link = re.search(r'<a href="(.*?)">', suggestion)
            if link:
                link = link.group(1)
                monster = parse_monster_page(link)
                result = [monster] + subpages_monsters
                return result
        else:
            return subpages_monsters if subpages_monsters else None

    # get all the information about the monster; if we don't get something, we
    # will have the default value from the Monster constructor
    monster = Monster()
    monster.link = link
    stat_block = stat_block.group()

    name = re.search(r"\n(.+)\s*\(?\s*CR\s*[0-9/]*\s*\)?\s*\(?XP", text)
    if name:
        name = name.group(1).strip()
        if "3pp" in name:
            # some things slip though previous 3rd party content filters
            return None

        if name.endswith("("):
            name = name[:-1].rstrip().capitalize()

        monster.name = name
    else:
        # if we don't know the monster's name, omit it
        return None

    try:
        # division into separate blocks for parsing makes further regrexes faster
        basic_info_block = re.search(r"([\s\S]+?)DEFENSE",
                                     stat_block).group(1)
        defense_block = re.search(r"DEFENSE([\s\S]+?)OFFENSE",
                                  stat_block).group(1)
        offense_block = re.search(r"OFFENSE([\s\S]+?)(TACTICS|STATISTICS)",
                                  stat_block).group(1)
        statistics_block = re.search(r"STATISTICS([\s\S]+)\n\n|"
                                     r"STATISTICS\n([\S ]+)|"
                                     r"STATISTICS([\s\S]+)",
                                     stat_block).group()

        parse_basic_info(basic_info_block, monster)
        parse_defense(defense_block, monster)
        parse_offense(offense_block, monster)
        parse_statistics(statistics_block, monster)
    except AttributeError:
        # some pages have errors in sections (e. g. 3 "statistics" sections),
        # they throw exceptions as regexes can't recognize sections
        return None

    result = [monster] + subpages_monsters
    return result


def parse_basic_info(stat_block: str, monster: Monster) -> None:
    """
    Parses the first part of the monster stat block, basic info like Challenge
    Rating, XP, type etc. and fills the appropriate fields in the monster object.
    Warning: this does not include name, which is before the stat block!

    :param stat_block: string with the monster statistics block
    :param monster: Monster class object to fill
    """
    CR = re.search(r"CR\s+\(?(.+?)\)?\s+", stat_block)
    if CR:
        # this handles fractional CRs through interpreting all numbers as
        # (potentially space-divided) Fraction strings
        CR = CR.group(1) if CR.group(1) else CR.group(2)
        monster.CR = float(sum(Fraction(s) for s in CR.split()))

    XP = re.search(r"XP\s+([0-9]+,[0-9]+)\)?|"
                   r"XP\s+([0-9]+)\)?", stat_block)
    if XP:
        XP = XP.group(1) if XP.group(1) else XP.group(2)
        XP = XP.replace(",", "")
        monster.XP = int(XP)

    alignment = re.search(r"(LG|NG|CG|LN|CN|LE|NE|CE|N)", stat_block)
    if alignment:
        monster.alignment = alignment.group(1)

    # there are typos like this one in some descriptions
    stat_block = stat_block.replace("Diminuitive", "Diminutive")

    size = re.search(r"(Fine|Diminutive|Tiny|Small|Medium|Large|Huge|"
                     r"Gargantuan|Colossal)",
                     stat_block)
    if size:
        monster.size = size.group(1)

    creature_type = re.search(r"(aberration|animal|construct|dragon|fey|"
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
    armor = re.search(r"AC\s+([0-9]+)[\s\S]+"
                      r"touch\s+([0-9]+)[\s\S]+"
                      r"flat-footed\s+([0-9]+)",
                      stat_block)
    if armor:
        monster.AC = int(armor.group(1))
        monster.touch = int(armor.group(2))
        monster.flat_footed = int(armor.group(3))

    HP_and_HD = re.search(r"hp\s+([0-9]+)\s+\(([0-9]+)d", stat_block)
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
            setattr(monster, movement_type, int(movement.group(1)))

    attacks = re.search(r"(Melee|Ranged)([\s\S]+)"
                        r"(Space|Reach|Special Attacks|Spell-Like Abilities)",
                        stat_block)
    if attacks:
        attacks = attacks.group().split(")")
        attacks = [attack
                   for attack in attacks
                   if re.search(r"[\s\S]+\([0-9]+d[\s\S]+", attack)]

    if attacks:
        # attacks may now be empty e. g. if creature only has non-standard
        # attacks
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

        # attacks may have "and" and "or" logical operators, dividing them
        # into groups of possible attacks; we have to apply this logic to
        # parsed attacks, choosing "best" possible ones (i.e. most powerful)

        melee_logic = []
        for attack in melee_attacks:
            if "or " in attack:
                melee_logic.append("or")
            elif "and " in attack:
                melee_logic.append("and")
            else:
                melee_logic.append("")

        ranged_logic = []
        for attack in ranged_attacks:
            if "or " in attack:
                ranged_logic.append("or")
            elif "and " in attack:
                ranged_logic.append("and")
            else:
                ranged_logic.append("")

        words_to_remove = {"Melee ", "Ranged ", " and ", " or "}
        translation = "|".join(words_to_remove)
        melee_attacks = [re.sub(translation, "", attack).strip()
                         for attack in melee_attacks]
        ranged_attacks = [re.sub(translation, "", attack).strip()
                          for attack in ranged_attacks]

        melee_attacks = [parse_single_attack_type(attack)
                         for attack in melee_attacks]
        ranged_attacks = [parse_single_attack_type(attack)
                          for attack in ranged_attacks]

        # this is highest possible attack bonus, it may or may not be used in
        # practice by creature (e. g. it is "or"-ed with attacks with higher
        # damage, but lower attack bonus)
        monster.highest_attack_bonus = int(max([attack["highest_bonus"]
                                                for attack
                                                in melee_attacks + ranged_attacks]))

        melee_attacks = process_attacks_logic(melee_attacks, melee_logic)
        ranged_attacks = process_attacks_logic(ranged_attacks, ranged_logic)

        monster.melee_attacks_num = sum([attack["attacks_num"]
                                         for attack in melee_attacks])
        if melee_attacks:
            full_damages = [attack["full_dmg"] for attack in melee_attacks]
            full_damages = flatten(full_damages)
            monster.melee_median_dmg = max(median(full_damages), 0)
        else:
            monster.melee_median_dmg = 0

        monster.ranged_attacks_num = sum([attack["attacks_num"]
                                          for attack in ranged_attacks])
        if ranged_attacks:
            damages = [[attack["avg_dmg"]] * attack["attacks_num"]
                       for attack in ranged_attacks]
            damages = flatten(damages)
            monster.ranged_median_dmg = max(median(damages), 0)
        else:
            monster.ranged_median_dmg = 0

    space = re.search(r"Space\s+([0-9.]+)", stat_block)
    if space:
        monster.space = round(float(space.group(1)), 1)

    reach = re.search(r"Reach\s+([0-9]+)", stat_block)
    if reach:
        monster.reach = int(reach.group(1))


def parse_statistics(stat_block: str, monster: Monster) -> None:
    """
    Parses the fourth part of the monster stat block, STATISTICS. It includes
    6 attribute scores, BAB, CMB, CMD, feats and skills.

    :param stat_block: string with the monster statistics block
    :param monster: Monster class object to fill
    """
    attributes = {"Str": "strength",
                  "Dex": "dexterity",
                  "Con": "constitution",
                  "Int": "intelligence",
                  "Wis": "wisdom",
                  "Cha": "charisma"}
    for attr_short, attr_long in attributes.items():
        regex = attr_short + r"\s*([0-9]+)"
        attr_val = re.search(regex, stat_block)
        if attr_val:
            setattr(monster, attr_long, int(attr_val.group(1)))

    BAB = re.search(r"Base\s*Atk\s*(0|\+[0-9]+|-[0-9]+)", stat_block)
    if BAB:
        monster.BAB = int(BAB.group(1))

    CMB = re.search(r"CMB\s*(0|\+[0-9]+|-[0-9]+)", stat_block)
    if CMB:
        monster.CMB = int(CMB.group(1))

    CMD = re.search(r"CMD\s*[-+]?(0|[0-9]+)", stat_block)
    if CMD:
        monster.CMD = int(CMD.group(1))

    feats = re.search(r"Feats([\s\S]+?)Skills", stat_block)
    if feats:
        feats = feats.group(1).strip().replace(",", "").split()
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
    skills_names = {"Acrobatics", "Appraise", "Bluff", "Climb", "Diplomacy",
                    "Disable Device", "Disguise", "Escape Artist", "Fly",
                    "Handle Animal", "Heal", "Intimidate", "Linguistics",
                    "Perception", "Perform", "Profession", "Ride",
                    "Sense Motive", "Sleight of Hand", "Spellcraft",
                    "Stealth", "Survival", "Swim", "Use Magic Device"}
    if skills:
        skills = skills.group(1)
        # there are many Knowledge skills (e. g. Knowledge (nature)), so we
        # can just count this word
        monster.skills_num = len(re.findall("Knowledge", skills))
        monster.skills_num += len(re.findall("Craft", skills))
        for skill in skills_names:
            if skill in skills:
                monster.skills_num += 1
