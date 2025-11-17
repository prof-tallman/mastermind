
import random

class Bot:
    """
    Defines an autonomous bot that plays the Mastermind Game.
    
    Every bot must implement four functions:
      1) __init__(self, settings) Constructor that takes a game settings dictionary
      2) bot_info(self) Function that returns the bot's name and author
      3) make_guess(self) Function that returns a guess at the secret code
      4) receive_feedback(self, feedback) Function with the outcome of the last guess
    """

    def __init__(self, settings):
        """
        Initializes the mastermind bot by saving important game settings and
        creating variables to hold state information.
        
        Parameters: {
            bot_seed: the random number generator seed for this game
            code_colors: list of the possible game colors
            code_length: the number of tokens in this game
        }

        Returns a dict holding the bot's name and author
        """

        # Game settings
        self.rng = random.Random(settings["bot_seed"])
        self.code_colors = settings["code_colors"]
        self.code_length = settings["code_length"]

        # Required bot info
        self.bot_id = {
            "name": "Randy Randolph",
            "author": "Prof. Tallman",
        }
        
        return None


    def bot_info(self):
        """
        Returns the bot ID as { "name": name, "author": author }.
        """
        return self.bot_id
    

    def make_guess(self):
        """
        Bot function to guess a secret code.
        
        Parameters: None
        
        Returns: An iterable of `code_length` number of elements from `code_colors`
        """

        # Randomly choose 4 different colors
        guess = []
        for _ in range(self.code_length):
            guess.append(random.choice(self.code_colors))
        return guess


    def receive_feedback(self, feedback):
        """
        Bot function to record the outcome of the last guess. This function can be
        ignored; but if it is ignored then it means that the bot cannot learn from
        its previous guesses.

        Parameters: { 
            guess: <the last guess>
            black: count of guesses that were the correct color and position
            white: count of guesses that were the correct color but not position
        }

        Returns: None
        """

        black = feedback['black']
        white = feedback['white']
        guess = feedback['guess']

        return None
