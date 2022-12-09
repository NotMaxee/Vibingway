import enum


class LoopModes(enum.StrEnum):
    """A list of all available looping modes."""

    #: Disables looping.
    OFF = "off"

    #: Loops the entire queue.
    ALL = "all"

    #: Loops the current track.
    TRACK = "track"
    
class QueueOrder(enum.StrEnum):
    """A list of all available queue orders."""

    #: Plays tracks in order.
    NORMAL = "normal"

    #: Plays tracks in reverse order.
    REVERSE = "reverse"

    #: Plays tracks in a random order.
    RANDOM = "random"


class TrackType(enum.IntEnum):
    """A list of track types."""

    #: Youtube tracks.
    YOUTUBE = 0

    #: Youtube music track.
    YOUTUBE_MUSIC = 1

    #: Soundcloud tracks.
    SOUNDCLOUD = 2