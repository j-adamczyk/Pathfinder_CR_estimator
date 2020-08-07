import collections

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
