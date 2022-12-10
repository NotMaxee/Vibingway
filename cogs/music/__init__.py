import logging
from typing import Any, Dict

import wavelink
import wavelink.websocket

from .cog import Music

OLD_PROCESS_DATA = None

def install_patch():
    logger: logging.Logger = logging.getLogger("wavelink.websocket")

    async def process_data(self, data: Dict[str, Any]) -> None:
        op = data.get("op", None)
        if not op:
            return

        if op == "stats":
            self.node.stats = wavelink.Stats(self.node, data)
            return

        try:
            player = self.node.get_player(self.node.bot.get_guild(int(data["guildId"])))  # type: ignore
        except KeyError:
            return

        if player is None:
            return

        if op == "event":
            event, payload = await self._get_event_payload(data["type"], data)
            logger.debug(f"op: event:: {data}")

            # Bugfix for https://github.com/PythonistaGuild/Wavelink/issues/156.
            if event == "track_end" and payload.get("reason") != "REPLACED":
                player._source = None

            self.dispatch(event, player, **payload)

        elif op == "playerUpdate":
            logger.debug(f"op: playerUpdate:: {data}")
            try:
                await player.update_state(data)
            except KeyError:
                pass
    
    OLD_PROCESS_DATA = wavelink.websocket.Websocket.process_data
    wavelink.websocket.Websocket.process_data = process_data

def uninstall_patch():
    wavelink.websocket.Websocket.process_data = OLD_PROCESS_DATA

async def setup(bot):
    install_patch()
    await bot.add_cog(Music(bot))


async def teardown(bot):
    uninstall_patch()
