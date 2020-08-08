from typing import Union


class Monster:
    def __init__(self):
        # basic info
        self.name: Union[str, None] = ""
        self.CR: Union[float, None] = None
        self.XP: Union[int, None] = None
        self.alignment: Union[str, None] = None
        self.size: Union[str, None] = None
        self.type: Union[str, None] = None
        self.init: Union[int, None] = None
        self.senses: Union[int, None] = None
        self.perception: Union[int, None] = None

        # defense
        self.AC: Union[int, None] = None
        self.touch: Union[int, None] = None
        self.flat_footed: Union[int, None] = None
        self.HP: Union[int, None] = None
        self.HD: Union[int, None] = None
        self.fortitude: Union[int, None] = None
        self.reflex: Union[int, None] = None
        self.will: Union[int, None] = None

        # offense
        self.speed: Union[int, None] = None
        self.swim: Union[int, None] = None
        self.fly: Union[int, None] = None
        self.burrow: Union[int, None] = None
        self.attacks: Union[int, None] = None
        self.largest_attack_bonus: Union[int, None] = None
        self.avg_damage: Union[int, None] = None
        self.space: Union[int, None] = None
        self.reach: Union[int, None] = None

        # statistics
        self.strength: Union[int, None] = None
        self.dexterity: Union[int, None] = None
        self.constitution: Union[int, None] = None
        self.intelligence: Union[int, None] = None
        self.wisdom: Union[int, None] = None
        self.charisma: Union[int, None] = None

        self.BAB: Union[int, None] = None
        self.CMB: Union[int, None] = None
        self.CMD: Union[int, None] = None

        self.feats_num: Union[int, None] = 0
        self.skills_num: Union[int, None] = 0

    def __repr__(self):
        return ", ".join(f"({attr}: {val})" for attr, val in vars(self).items())
