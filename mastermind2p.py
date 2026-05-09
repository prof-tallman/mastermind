
import os
import sys
import time
import random
from itertools import zip_longest

import engine


def format_guess_entry(entry):
    """Return (guess_str, black, white) from a history entry dict."""
    guess = entry["guess"]
    if isinstance(guess, (list, tuple)):
        guess_str = "".join(str(x) for x in guess)
    else:
        guess_str = str(guess)
    black = entry.get("black", 0)
    white = entry.get("white", 0)
    return guess_str, black, white

def parse_args():
    """
    Parse command line arguments.

    Usage:
        python mastermind.py <bot_module> [num_trials]

    - bot_module: required, name of the bot file/module
    - num_trials: optional, defaults to 1
    """
    if not (3 <= len(sys.argv) <= 4):
        print(f"Usage: {sys.argv[0]} bot1.py bot2.py [seed]")
        sys.exit(1)

    bot1_path = sys.argv[1]
    bot2_path = sys.argv[2]
    seed = None

    if len(sys.argv) == 4:
        seed_arg = sys.argv[3]
        try:
            seed = int(seed_arg)
        except ValueError:
            print(f"Warning: seed '{seed_arg}' is not an integer; using None instead.")
            seed = None

    bot_filename1 = sys.argv[1]
    bot_module1 = bot_filename1[:-3]
    if not os.path.exists(bot_filename1):
        print(f"Error: bot '{bot_filename1}' does not exist")
        sys.exit(1)

    bot_filename2 = sys.argv[2]
    bot_module2 = bot_filename2[:-3]
    if not os.path.exists(bot_filename2):
        print(f"Error: bot '{bot_filename2}' does not exist")
        sys.exit(1)

    return bot_module1, bot_module2, seed


def main():
    bot_module1, bot_module2, seed = parse_args()
    if seed == None:
        seed = random.randint(0, 1000000)

    settings = {
        'game_seed': seed,
        'bot_seed': None,
        'max_turns': 1500,
        'code_length': 4,
        'code_colors': [ 'R', 'G', 'U', 'Y', 'K', 'W' ],
    }

    mastermind1 = engine.Game(settings, verbose=False)
    mastermind2 = engine.Game(settings, verbose=False)

    result1 = mastermind1.run_game_loop(bot_module1)
    result2 = mastermind2.run_game_loop(bot_module2)

    # Get bot info for display
    name1 = result1['botinfo'][engine.BOT_NAMEID]
    author1 = result1['botinfo'][engine.BOT_AUTHOR]
    name2 = result2['botinfo'][engine.BOT_NAMEID]
    author2 = result2['botinfo'][engine.BOT_AUTHOR]

    history1 = result1['history']
    history2 = result2['history']

    # Determine width needed for displaying guesses nicely.
    guess_lengths = []
    for h in history1:
        g, _, _ = format_guess_entry(h)
        guess_lengths.append(len(g))
    for h in history2:
        g, _, _ = format_guess_entry(h)
        guess_lengths.append(len(g))
    guess_width = max(guess_lengths) if guess_lengths else 4
    col_width = guess_width + 8   # "  BB WW" is 6 chars plus padding

    # Header
    print()
    header1 = f"{name1}"
    header2 = f"{name2}"
    print(f"{'Turn':>4} | {header1:<{col_width}} | {header2:<{col_width}}")
    print("-" * (4 + 3 + col_width + 3 + col_width + 4))

    # Row-by-row output
    for turn, (h1, h2) in enumerate(zip_longest(history1, history2), start=1):
        if h1 is not None:
            g1, b1, w1 = format_guess_entry(h1)
            col1 = f"{g1:<{guess_width}}  {b1:2d} {w1:2d}"
        else:
            col1 = " " * col_width

        if h2 is not None:
            g2, b2, w2 = format_guess_entry(h2)
            col2 = f"{g2:<{guess_width}}  {b2:2d} {w2:2d}"
        else:
            col2 = " " * col_width

        print(f"{turn:>4} | {col1:<{col_width}} | {col2:<{col_width}}")
        time.sleep(1)

    # Print summary
    print(f"\n==== MASTERMIND RESULTS (seed = {seed}) ====")
    if len(history1) < len(history2):
        print(f"Winner is {name1} by {author1}\n\n")
    elif len(history2) < len(history1):
        print(f"Winner is {name2} by {author2}\n\n")
    else:
        print(f"Tie game! Play again with a different seed\n\n")


if __name__ == '__main__':
    main()