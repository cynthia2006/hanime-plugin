import yarl


def urljoin(base, fragment):
    """Join URL according to WHATWG rules"""

    return str(yarl.URL(base).join(yarl.URL(fragment)))

def urljoinpath(base, *fragments):
    """Join fragment to the URL path"""

    return str(yarl.URL(base).joinpath(*fragments))