import wavelink

class RequestedTrack(object):
    """Mixin for requested audio tracks."""
    def __init__(self):
        self._requester_id: int = None

    @property
    def 


class RequestedYoutubeTrack(wavelink.YouTubeTrack):
    def __init__(self, *args, requester:int=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.requester = requester