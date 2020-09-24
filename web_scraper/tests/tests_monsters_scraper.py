import math
import re
from typing import Tuple

import pytest

from web_scraper.src.model import Monster
from web_scraper.src.monsters_scraper import parse_basic_info, parse_defense, \
    parse_offense, parse_statistics


def get_parts(text: str) -> Tuple[str, str, str, str, str]:
    text = text.replace("–", "-")

    stat_block = re.search(r"(CR\s+[0-9/]+\)?\s+XP[\S\s]*?)SPECIAL ABILITIES|"
                           r"(CR\s+[0-9/]+\)?\s+XP[\S\s]*?STATISTICS[\S\s]*?)\n\n|"
                           r"(CR\s+[0-9/]+\)?\s+XP[\S\s]*?STATISTICS[\S\s]*)",
                           text).group(1)

    name = re.search(r"\n(.+)[ ]+\(?CR", text)
    name = name.group(1).strip() if name else ""

    basic_info_block = re.search(r"([\s\S]+)DEFENSE", stat_block).group(1)
    defense_block = re.search(r"DEFENSE([\s\S]+)OFFENSE", stat_block).group(1)
    offense_block = re.search(r"OFFENSE([\s\S]+)(TACTICS|STATISTICS)",
                              stat_block).group(1)
    statistics_block = re.search(r"STATISTICS([\s\S]+)", stat_block).group(1)

    return name, basic_info_block, defense_block, offense_block, statistics_block


@pytest.fixture
def get_tiefling() -> Tuple[str, str, str, str, str]:
    with open("example_monsters/tiefling.txt") as file:
        text = file.read()

    return get_parts(text)


@pytest.fixture
def get_planetar() -> Tuple[str, str, str, str, str]:
    with open("example_monsters/planetar.txt") as file:
        text = file.read()

    return get_parts(text)


@pytest.fixture
def get_minotaur() -> Tuple[str, str, str, str, str]:
    with open("example_monsters/minotaur.txt") as file:
        text = file.read()

    return get_parts(text)


def test_name(get_tiefling, get_planetar, get_minotaur):
    tiefling_name, _, _, _, _ = get_tiefling
    planetar_name, _, _, _, _ = get_planetar
    minotaur_name, _, _, _, _ = get_minotaur

    assert tiefling_name == "Tiefling"
    assert planetar_name == "Planetar"
    assert minotaur_name == "Minotaur"


def test_tiefling_basic_info(get_tiefling):
    _, basic_info, _, _, _ = get_tiefling
    monster = Monster()
    parse_basic_info(basic_info, monster)

    assert math.isclose(monster.CR, 0.5)
    assert monster.XP == 200
    assert monster.alignment == "NE"
    assert monster.size == "Medium"
    assert monster.type == "Outsider"
    assert monster.init == 3
    assert monster.senses == 1
    assert monster.perception == 5


def test_tiefling_defense(get_tiefling):
    _, _, defense, _, _ = get_tiefling
    monster = Monster()
    parse_defense(defense, monster)

    assert monster.AC == 16
    assert monster.touch == 13
    assert monster.flat_footed == 13
    assert monster.HP == 10
    assert monster.HD == 1
    assert monster.fortitude == 2
    assert monster.reflex == 5
    assert monster.will == 1


def test_tiefling_offense(get_tiefling):
    _, _, _, offense, _ = get_tiefling
    monster = Monster()
    parse_offense(offense, monster)

    assert monster.speed == 30
    assert monster.highest_attack_bonus == 3
    assert monster.melee_attacks_num == 1
    assert math.isclose(monster.melee_median_dmg, 4.5)
    assert monster.ranged_attacks_num == 1
    assert math.isclose(monster.ranged_median_dmg, 4.5)
    assert monster.space == 5
    assert monster.reach == 5


def test_tiefling_statistics(get_tiefling):
    _, _, _, _, statistics = get_tiefling
    monster = Monster()
    parse_statistics(statistics, monster)

    assert monster.strength == 13
    assert monster.dexterity == 17
    assert monster.constitution == 14
    assert monster.intelligence == 12
    assert monster.wisdom == 12
    assert monster.charisma == 6
    assert monster.BAB == 0
    assert monster.CMB == 1
    assert monster.CMD == 14
    assert monster.feats_num == 1
    assert monster.skills_num == 9


def test_planetar_basic_info(get_planetar):
    _, basic_info, _, _, _ = get_planetar
    monster = Monster()
    parse_basic_info(basic_info, monster)

    assert math.isclose(monster.CR, 16)
    assert monster.XP == 76800
    assert monster.alignment == "NG"
    assert monster.size == "Large"
    assert monster.type == "Outsider"
    assert monster.init == 8
    assert monster.senses == 5
    assert monster.perception == 27


def test_planetar_defense(get_planetar):
    _, _, defense, _, _ = get_planetar
    monster = Monster()
    parse_defense(defense, monster)

    assert monster.AC == 32
    assert monster.touch == 13
    assert monster.flat_footed == 28
    assert monster.HP == 229
    assert monster.HD == 17
    assert monster.fortitude == 19
    assert monster.reflex == 11
    assert monster.will == 19


def test_planetar_offense(get_planetar):
    _, _, _, offense, _ = get_planetar
    monster = Monster()
    parse_offense(offense, monster)

    assert monster.speed == 30
    assert monster.fly == 90
    assert monster.highest_attack_bonus == 27
    assert monster.melee_attacks_num == 3
    assert math.isclose(monster.melee_median_dmg, 27.0)
    assert monster.ranged_attacks_num == 0
    assert math.isclose(monster.ranged_median_dmg, 0.0)
    assert monster.space == 10
    assert monster.reach == 10


def test_planetar_statistics(get_planetar):
    _, _, _, _, statistics = get_planetar
    monster = Monster()
    parse_statistics(statistics, monster)

    assert monster.strength == 27
    assert monster.dexterity == 19
    assert monster.constitution == 24
    assert monster.intelligence == 22
    assert monster.wisdom == 25
    assert monster.charisma == 24
    assert monster.BAB == 17
    assert monster.CMB == 26
    assert monster.CMD == 40
    assert monster.feats_num == 9
    assert monster.skills_num == 12


def test_minotaur_basic_info(get_minotaur):
    _, basic_info, _, _, _ = get_minotaur
    monster = Monster()
    parse_basic_info(basic_info, monster)

    assert math.isclose(monster.CR, 4)
    assert monster.XP == 1200
    assert monster.alignment == "CE"
    assert monster.size == "Large"
    assert monster.type == "Monstrous humanoid"
    assert monster.init == 0
    assert monster.senses == 1
    assert monster.perception == 10


def test_minotaur_defense(get_minotaur):
    _, _, defense, _, _ = get_minotaur
    monster = Monster()
    parse_defense(defense, monster)

    assert monster.AC == 14
    assert monster.touch == 9
    assert monster.flat_footed == 14
    assert monster.HP == 45
    assert monster.HD == 6
    assert monster.fortitude == 6
    assert monster.reflex == 5
    assert monster.will == 5


def test_minotaur_offense(get_minotaur):
    _, _, _, offense, _ = get_minotaur
    monster = Monster()
    parse_offense(offense, monster)

    assert monster.speed == 30
    assert monster.highest_attack_bonus == 9
    assert monster.melee_attacks_num == 3
    assert math.isclose(monster.melee_median_dmg, 17.5)
    assert monster.ranged_attacks_num == 0
    assert math.isclose(monster.ranged_median_dmg, 0.0)
    assert monster.space == 10
    assert monster.reach == 10


def test_minotaur_statistics(get_minotaur):
    _, _, _, _, statistics = get_minotaur
    monster = Monster()
    parse_statistics(statistics, monster)

    assert monster.strength == 19
    assert monster.dexterity == 10
    assert monster.constitution == 15
    assert monster.intelligence == 7
    assert monster.wisdom == 10
    assert monster.charisma == 8
    assert monster.BAB == 6
    assert monster.CMB == 11
    assert monster.CMD == 21
    assert monster.feats_num == 3
    assert monster.skills_num == 4
