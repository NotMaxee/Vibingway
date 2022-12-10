import asyncio


def setup_uvloop():
    """Attempts to use ``uvloop`` as the default asyncio event loop.
    
    See https://github.com/MagicStack/uvloop.
    """
    try:
        import uvloop
    except ImportError:
        pass
    else:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())