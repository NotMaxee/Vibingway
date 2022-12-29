import discord
from io import BytesIO


__all__ = ("ELLIPSIS", "truncate", "human_join", "format_seconds", "create_text_file")

ELLIPSIS = "…"
"""The ellipsis character used for :func:`utils.string.truncate`."""


def truncate(string, length):
    """Truncate a string to a given length.

    Functions as follows:

    * If length is 0 or less, returns an empty string.
    * If length is less than the length of the input string, returns the
      string truncated to length-1 and appends :data:`~utils.string.ELLIPSIS`.
    * Otherwise, returns the input string.

    Examples
    --------

    .. code-block:: python3

        description = "This is a very long and detailed description."
        shortened = utils.string.truncate(description, 20)
        # shortened = "This ia very long…"

    Parameters
    ----------
    string: str
        The string to truncate.
    length: int
        The maximum length of the string. Any characters past
        this limit will be removed and the last character is
        replaced with ``…``.

    Returns
    -------
    str
        The truncated string.
    """
    if length <= 0:
        return ""
    elif len(string) > length:
        return string[: length - 1] + "…"
    else:
        return string


def human_join(items, bold=False, code=False, concatenator="and"):
    r"""Join a list of objects and return human readable representation.

    Examples
    --------

    .. code-block:: python3

        >>> from utils.string import human_join
        >>> human_join([])
        ""
        >>> human_join([1])
        "1"
        >>> human_join([1, 2])
        "1 and 2"
        >>> human_join([1, 2, 3])
        "1, 2 and 3"
        >>> human_join([1, 2, 3], concatenator="or")
        "1, 2 or 3"
        >>> human_join([1, 2], bold=True)
        "**1** and **2**"
        >>> human_join([1, 2], code=True)
        "`1` and `2`"

    Parameters
    ----------
    items: List[Union[Any]]]
        A list of strings or other objects to be joined.
    bold: Optional[bool]
        Whether to surround items with ``**``. Defaults to ``False``.
    code: Optional[bool]
        Whether to surround items with ``\`\```. Defaults to ``False``.
    concatenator: Optional[str]
        The concatenator to use for the second last and
        last item.

    Returns
    -------
    str
        The joined list of items.
    """
    fmt = "{}"
    if code:
        fmt = f"`{fmt}`"
    if bold:
        fmt = f"**{fmt}**"

    items = [fmt.format(item) for item in items]

    if len(items) == 0:
        return ""
    elif len(items) == 1:
        return str(items[0])

    return "{} {} {}".format(", ".join(items[:-1]), concatenator, items[-1])


def format_seconds(seconds: (int | float)):
    """Returns a human readable string representation of the given amount of seconds.

    Parameters
    ----------
    seconds: Union[int, float]
        An amount of seconds.

    Returns
    -------
    str
        A string in the form of ``hh:mm:ss`` or ``mm:ss`` if there are no hours.
    """
    seconds = round(seconds)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    if hours:
        return f"{hours:0>2d}:{minutes:0>2d}:{seconds:0>2d}"
    else:
        return f"{minutes:0>2d}:{seconds:0>2d}"


def create_text_file(name: str, content: str):
    """Create a :class:`discord.File` with the given name and content.

    The file extension is set to `txt`.

    Parameters
    ----------
    name: str
        The filename without the file extension.
    content: str
        The content of the file.

    Returns
    -------
    discord.File
        The file object.
    """
    buffer = BytesIO(str(content).encode("utf-8"))
    return discord.File(buffer, f"{name}.txt")
