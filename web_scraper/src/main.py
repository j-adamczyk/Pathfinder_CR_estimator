from concurrent.futures.thread import ThreadPoolExecutor

import pandas as pd

from web_scraper.src.monsters_scraper import parse_monster_page
from web_scraper.src.utils import flatten, get_monster_links, get_page_content

if __name__ == "__main__":
    MAX_THREADS = 30

    # get links for monster listings for all monsters on the page
    html: str = get_page_content(
        "https://www.d20pfsrd.com/bestiary/bestiary-hub/monsters-by-cr/") \
        .decode("utf-8")

    monster_links = get_monster_links(html)

    # omit summoned creatures - they have non standard stat blocks and are
    # not "proper" monster living out in the game world
    monster_links = [link for link in monster_links if "summon" not in link]

    # if there are less than MAX_THREADS links, spawn less threads,
    # so they are not wasted
    num_threads = min(MAX_THREADS, len(monster_links))
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # asynchronous, threads will return results when they finish their
        # own work
        results = [result for result
                   in executor.map(parse_monster_page, monster_links)]

    results = [vars(monster) for monster in flatten(results) if monster]

    # since Monster class just holds variables, it's safe and fast to use vars
    dataframe = pd.DataFrame(results)

    dataframe.to_csv("dataset_v1.csv", index_label="index", na_rep="NULL")
