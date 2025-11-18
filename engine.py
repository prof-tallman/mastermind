
import random
from collections import Counter
from collections.abc import Sequence
from typing import Any

from sandbox import BotProcess, BotTimeout, BotError

DEFAULT_SEED = 104
CODE_COLORS = "code_colors"
CODE_LENGTH = "code_length"
GAME_SEED   = "game_seed"
MAX_TURNS   = "max_turns"
BOT_NAMEID  = "name"
BOT_AUTHOR  = "author"
FDBK_BLACK  = "black"
FDBK_WHITE  = "white"
FDBK_GUESS  = "guess"

def validate_code(
        code: Sequence[Any],
        settings: dict[str, object],
    ) -> tuple[bool, str]:
    """
    Validate a submitted code against the game settings.

    Returns a tuple ``(is_valid, message)`` where ``is_valid`` is True if the
    code has the correct length and uses only allowed color symbols, and
    ``message`` provides an explanation.
    """

    length = settings[CODE_LENGTH]
    colors = set(settings[CODE_COLORS])
    if len(code) != length:
        return (False, "wrong length")
    elif any(c not in colors for c in code):
        return (False, "invalid color symbol")
    else:
        return (True, "valid code")


def score_feedback(
        code: Sequence[Any], 
        guess: Sequence[Any]
    ) -> dict[str, object]:
    """
    Calculate Mastermind-style feedback for a guess.

    A black peg means a correct color in the correct position. A white peg
    means a correct color in the wrong position. No peg means the guessed
    color does not appear in the code.
    """

    # Count the number of matches, filtering down to the position matches
    black = sum(s == g for s, g in zip(code, guess))

    # Count the number of color matches, filtering out the position matches
    secret_counter = Counter(s for s, g in zip(code, guess) if s != g)
    guess_counter = Counter(g for s, g in zip(code, guess) if s != g)
    white = sum((secret_counter & guess_counter).values())

    return { FDBK_BLACK: black, FDBK_WHITE: white, FDBK_GUESS: guess }


class Game:
    """
    Represents a full Mastermind-style game engine.

    A Game object stores the game settings, manages its own random number
    generator, and is responsible for running an entire game round against a
    bot. This includes generating the secret code, calling the bot to make
    guesses, checking each guess for validity, scoring the feedback, sending
    feedback back to the bot, and detecting timeouts or errors. The engine
    returns a dictionary describing the final outcome of the game.
    """

    def __init__(
            self, 
            settings: dict[str, object], 
            verbose: bool = True
        ) -> None:
        """
        Initialize a Game instance using the provided settings.

        The settings dictionary must include:
            - "code_colors": the list of allowed colors
            - "code_length": the required code length
            - "max_turns":   the maximum number of turns allowed

        It may also include:
            - "game_seed":   an optional random number seed
        """
        # Validate the settings
        required_keys = [CODE_COLORS, CODE_LENGTH, MAX_TURNS]
        for key in required_keys:
            if key not in settings:
                raise ValueError(f"Settings must specify '{key}'")
        if GAME_SEED not in settings:
            settings[GAME_SEED] = DEFAULT_SEED

        self.verbose = verbose
        self.settings = settings
        self.rng = random.Random(self.settings[GAME_SEED])

    def _rand_code(self) -> Sequence[Any]:
        """
        Generate a random secret code for the game.

        The code is created by randomly selecting colors (with replacement)
        from the list of allowed colors. The number of selections is equal to
        the code length defined in the game settings.
        
        Returns:
            A sequence representing the randomly generated secret code.
        """
        code_length = self.settings[CODE_LENGTH]
        code_colors = self.settings[CODE_COLORS] 
        return self.rng.choices(code_colors, k=code_length)

    def run_game_loop(self, bot_module: str) -> dict[str, object]:
        """
        Run a full round of the game using the bot specified by its module name.

        The game engine loads the bot in a separate process, generates a secret
        code, and then repeatedly asks the bot to make guesses. After each guess
        the engine validates the code, scores the feedback (black and white pegs),
        and sends that feedback back to the bot. The loop continues until the bot
        guesses the secret code, runs out of turns, makes an error, or times out.

        Args:
            bot_module: The name of the module containing the bot's code. The bot
                must implement the functions `make_guess` and `receive_feedback`.

        Returns:
            A dictionary describing the result of the game. The dictionary contains:
                - "turns":    The number of turns used in the game.
                - "result":   Either "win" or "loss".
                - "reason":   A short explanation (e.g., "guessed code",
                              "timeout", or "exhausted turns").
                - "secret":   The secret code generated for the game.
                - "history":  A list of feedback dictionaries, one for each turn.

            The bot process is always stopped before this function returns.
        """
        secret = self._rand_code()
        bot_process = None
        history = []

        def make_result(
                turns: int, 
                result: str, 
                reason: str,
                bot_info: dict[str, str] = { BOT_NAMEID: "unknown", BOT_AUTHOR: "unknown" }
            ) -> dict[str, object]:
            """ Helper function to build the result dictionary. """
            return {
                "turns": turns,
                "result": result,
                "reason": reason,
                "secret": secret,
                "history": history,
                "botinfo": bot_info
            }

        try:
            # Start the bot process. We use a separate process for the bots to
            # protect the engine from errors.
            bot_process = BotProcess(bot_module, self.settings)
            bot_process.start()
        
            # Get the bot's ID information
            try:
                bot_info = bot_process.call("bot_info")
            except BotError as error:
                return make_result(-1, "loss", f"exception: {error}")
            except BotTimeout:
                return make_result(-1, "loss", "timeout")

            # Generate the secret code and display some game info to the user.
            if self.verbose:
                print(f"{bot_info[BOT_NAMEID]} by {bot_info[BOT_AUTHOR]}")
                print(f"Secret Code: {secret}")
                title = " -=| GUESSES |=- "
                width = len(str(secret))
                print(f"{title:^{width}} : B W")

            # Step through the bots turns. This loop may break prematurely if,
            # for example, the bot either wins, timeouts, or crashes.
            for turn in range(1, self.settings[MAX_TURNS] + 1):

                # Allow the bot to take a turn
                try:
                    guess = bot_process.call("make_guess")
                except BotError as error:
                    return make_result(turn, "loss", f"exception: {error}", bot_info)
                except BotTimeout:
                    return make_result(turn, "loss", "timeout", bot_info)

                # Evaluate the bot's guess
                ok, _ = validate_code(guess, self.settings)
                if not ok:
                    return make_result(turn, "loss", "invalid code")
                feedback = score_feedback(secret, guess)
                history.append(feedback)
                if self.verbose:
                    print(f"{guess} :"
                          f" {feedback[FDBK_BLACK]}"
                          f" {feedback[FDBK_WHITE]}")
                
                # Provide feedback to the bot
                try:
                    bot_process.call("receive_feedback", feedback)
                except BotError as error:
                    return make_result(turn, "loss", f"exception: {error}", bot_info)
                except BotTimeout:
                    return make_result(turn, "loss", "timeout", bot_info)
                
                # Check for win
                if feedback[FDBK_BLACK] == self.settings[CODE_LENGTH]:
                    return make_result(turn, "win", "guessed code", bot_info)

            # End of for-loop, bot must have exhausted its turns
            return make_result(self.settings[MAX_TURNS], 
                               "loss", "exhausted turns",
                               bot_info)

        finally:
            if bot_process is not None:
                try: 
                    bot_process.stop()
                except Exception:
                    pass
