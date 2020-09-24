import math

import pytest

from web_scraper.src.utils import *


def test_existing_page():
    content = get_page_content("https://www.google.com/")
    assert content is not None


def test_nonexistent_page():
    with pytest.raises(requests.exceptions.ConnectionError):
        get_page_content("https://nonexistentpage.com")


def test_simple_flatten():
    nested = [[0], [1], [2]]
    flattened = flatten(nested)
    assert flattened == [0, 1, 2]


def test_deeper_flatten():
    nested = [[[0], [1]], [2], [[3], [[4], [5]]]]
    flattened = flatten(nested)
    assert flattened == [0, 1, 2, 3, 4, 5]


def test_different_structures_flatten():
    nested = ([0], {1: 2, 3: [4]}, (5, [6, [7]]))
    flattened = flatten(nested)
    assert flattened == [0, 1, 3, 5, 6, 7]


def test_get_feats_names():
    feats_names = get_feats_names()
    assert feats_names

    # test feat names of all lengths
    assert "Dodge" in feats_names
    assert "Weapon Finesse" in feats_names
    assert "Back to Back" in feats_names
    assert "Extra Spontaneous Spell Mastery" in feats_names
    assert "First General of the East" in feats_names
    assert "Blessed by a God or Dragon" in feats_names


def test_crit_chance_no_inf():
    crit_str = ""
    chance, multiplier = get_crit_info(crit_str)
    assert math.isclose(chance, 0.05)
    assert multiplier == 2


def test_crit_chance_range():
    crit_str = "/19-20"
    chance, multiplier = get_crit_info(crit_str)
    assert math.isclose(chance, 0.1)
    assert multiplier == 2


def test_crit_chance_multiplier():
    crit_str = "/x3"
    chance, multiplier = get_crit_info(crit_str)
    assert math.isclose(chance, 0.05)
    assert multiplier == 3


def test_crit_chance_range_and_multiplier():
    crit_str = "/19-20/x3"
    chance, multiplier = get_crit_info(crit_str)
    assert math.isclose(chance, 0.1)
    assert multiplier == 3


def test_parse_simple_attack_type():
    attack_str = "short sword +5 (1d6+1/19-20)"
    attack_info = parse_single_attack_type(attack_str)
    assert attack_info["attacks_num"] == 1
    assert attack_info["highest_bonus"] == 5
    assert math.isclose(attack_info["avg_dmg"], 5.0)


def test_parse_multiple_attacks():
    attack_str = "short sword +11/+6/+1/-4 (1d6+1/19-20)"
    attack_info = parse_single_attack_type(attack_str)
    assert attack_info["attacks_num"] == 4
    assert attack_info["highest_bonus"] == 11
    assert math.isclose(attack_info["avg_dmg"], 5.0)


def test_negative_attack_bonus():
    attack_str = "short sword -1 (1d6+1/19-20)"
    attack_info = parse_single_attack_type(attack_str)
    assert attack_info["attacks_num"] == 1
    assert attack_info["highest_bonus"] == -1
    assert math.isclose(attack_info["avg_dmg"], 5.0)



