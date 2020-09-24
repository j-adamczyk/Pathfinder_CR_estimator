from typing import List, Union


class Monster:
    def __init__(self):
        # technical details
        self.link: str = ""

        # basic info
        self.name: str = ""
        self.CR: Union[float, None] = None
        self.XP: Union[int, None] = None
        self.alignment: Union[str, None] = None
        self.size: Union[str, None] = None
        self.type: Union[str, None] = None
        self.init: Union[int, None] = None
        self.senses: int = 0
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
        self.speed: int = 0
        self.burrow: int = 0
        self.climb: int = 0
        self.fly: int = 0
        self.swim: int = 0

        self.highest_attack_bonus: Union[int, None] = None

        self.melee_attacks_num: int = 0
        self.melee_avg_dmg: int = 0
        
        self.ranged_attacks_num: int = 0
        self.ranged_avg_dmg: int = 0

        self.space: int = 5
        self.reach: int = 5

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

        self.feats_num: int = 0
        self.skills_num: int = 0

    def __repr__(self):
        return "\n".join(f"{attr}: {val}"
                         for attr, val in vars(self).items())
