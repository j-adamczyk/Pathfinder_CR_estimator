from concurrent.futures import ThreadPoolExecutor
import re
from typing import Match, List, Optional

from bs4 import BeautifulSoup
import requests

MAX_THREADS = 30


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


def parse_monster_page(link: str) -> None:
    """
    Parses statistics of the monster from its page.

    :param link: hyperlink to monster page
    :return: currently None
    """
    text: bytes = get_page_content(link)
    soup = BeautifulSoup(text, 'html.parser')
    text: str = soup.get_text()

    # reduce text to the interesting part
    text: Match = re.search(r"(CR[.\S\s]*?)SPECIAL ABILITIES|(CR[.\S\s]*?)\n\n",
                            text)

    # TODO: further processing


if __name__ == "__main__":
    # get links for monster listings for all monsters on the page
    text: str = get_page_content(
        "https://www.d20pfsrd.com/bestiary/monster-listings/") \
        .decode('utf-8')

    monster_links: List[str] = re.findall(r"<a href=.+?</a>",
                                          text)

    # some hyperlink list cleaning
    # 3 list comprehensions turned out to be a degree of magnitude faster than 1 for loop

    # filter out 3rd party content
    monster_links = [link
                     for link in monster_links
                     if "3pp" not in link]

    # get only hyperlinks
    monster_links: List[Optional[Match[str]]] = \
        [re.match(r"<a href=\"(https://www.d20pfsrd.com/bestiary/monster-listings/.+?)\">",
                  link)
         for link in monster_links]

    monster_links: List[str] = [link.group(1)
                                for link in monster_links
                                if link]

    # remove first links, since they guide to monster categories, not individual monster pages; instead of doing
    # it by hand, I know that first type is "aberrations" and there are monsters starting with "a", so I get
    # index of first monster and slice list
    i = 0
    for index, link in enumerate(monster_links):
        if "https://www.d20pfsrd.com/bestiary/monster-listings/aberrations/a" in link:
            i: int = index
            break

    monster_links = monster_links[i:]

    # if there are less than MAX_THREADS links, spawn less threads, so they are not wasted
    num_threads: int = min(MAX_THREADS, len(monster_links))
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        executor.map(parse_monster_page, monster_links)
