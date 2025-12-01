
import os
import sys

import engine


def parse_args():
    """
    Parse command line arguments.

    Usage:
        python mastermind.py <bot_module> [num_trials]

    - bot_module: required, name of the bot file/module
    - num_trials: optional, defaults to 1
    """
    if len(sys.argv) < 2:
        print("Usage: python mastermind.py <bot_module> [num_trials]")
        sys.exit(1)

    bot_filename = sys.argv[1]
    bot_module = bot_filename[:-3]
    if not os.path.exists(bot_filename):
        print(f"Error: bot '{bot_filename}' does not exist")
        sys.exit(1)

    if len(sys.argv) >= 3:
        try:
            num_trials = int(sys.argv[2])
            if num_trials < 1:
                print("num_trials must be a positive integer.")
                sys.exit(1)
        except ValueError:
            print("num_trials must be an integer.")
            sys.exit(1)
    else:
        num_trials = 1

    return bot_module, num_trials


def main():
    bot_module, num_trials = parse_args()

    settings = {
        'game_seed': 12345677,
        'bot_seed': None,
        'max_turns': 1500,
        'code_length': 4,
        'code_colors': [ 'R', 'G', 'U', 'Y', 'K', 'W' ],
    }

    total_turns = 0

    # Multiple trials show abbreviated output
    # Single trial display the entire game
    if num_trials == 1:
        mastermind = engine.Game(settings, verbose=True)
    else:
        mastermind = engine.Game(settings, verbose=False)

    # Run all of the games
    for _ in range(num_trials):
        result = mastermind.run_game_loop(bot_module)
        if result["result"] == "win":
            total_turns += result["turns"]
        else:
            total_turns += settings["max_turns"]
            print(f"Error: Bot forfeited game due to '{result['reason']}'")

    # Get bot info for display
    bot_info = result.get("botinfo", {})
    name = bot_info.get(engine.BOT_NAMEID, "Unknown Bot")
    author = bot_info.get(engine.BOT_AUTHOR, "Unknown Author")

    # Print summary
    avg_turns = total_turns // num_trials
    print("\n==== MASTERMIND RESULTS ====")
    print(f"Bot: {name} by {author}")
    print(f"Total Trials: {num_trials}")
    print(f"Average Turns: {avg_turns:.2f}\n")


if __name__ == '__main__':
    main()