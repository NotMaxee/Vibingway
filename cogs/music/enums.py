import enum



class Repeat(enum.StrEnum):
    """An enumerator over the different repeat modes."""
    #: Disables repeating the playlist.
    OFF = "off"

    #: Loops the entire playlist.
    ALL = "all"

    #: Loops the current track.
    TRACK = "track"

class TrackType(enum.IntEnum):
    """A list of track types."""

    #: Youtube tracks.
    YOUTUBE = 0

    #: Youtube music track.
    YOUTUBE_MUSIC = 1

    #: Soundcloud tracks.
    SOUNDCLOUD = 2