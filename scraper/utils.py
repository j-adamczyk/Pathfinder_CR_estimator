import collections
import re
from typing import Set

import requests


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


def flatten(iterable):
    """
    Flattens arbitrarily nested iterable structures.

    :param iterable: nested iterables to be flattened
    :return: elements from all iterables flattened into the type of the
    outermost iterable
    """
    # code shamelessly stolen from StackOverflow, thanks to Noctis Skytower
    # for this pretty solution
    iterator = iter(iterable)
    array, stack = collections.deque(), collections.deque()
    while True:
        try:
            value = next(iterator)
        except StopIteration:
            if not stack:
                return tuple(array)
            iterator = stack.pop()
        else:
            if not isinstance(value, str) \
               and isinstance(value, collections.Iterable):
                stack.append(iterator)
                iterator = iter(value)
            else:
                array.append(value)


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
