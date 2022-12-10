import os
import sys
from core import Vibingway, utils

if __name__ == "__main__":

    # Set working directory and prepare logging.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    utils.setup_uvloop()
    utils.setup_logging()

    # Launch the bot.
    bot = Vibingway()
    bot.run()

    # Close with exit code.
    sys.exit(bot.exit_code)
