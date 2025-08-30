import os
import random
import math # Import math for infinity values in Minimax
import time # Import time for delays
import platform
import smtplib
import csv
from email.message import EmailMessage

# --- ANSI escape codes for colors (for board and Elo tiers) ---
COLOR_RED = "\033[31m"
COLOR_BLUE = "\033[34m"
COLOR_RESET = "\033[0m" # Resets the color back to default

# --- Safe beep wrapper for platform compatibility ---
def safe_beep(frequency=1000, duration=200):
    """Plays a system beep, safely handling different operating systems."""
    if platform.system() == "Windows":
        try:
            import winsound
            winsound.Beep(frequency, duration)
        except ImportError:
            pass # winsound not available
    # No-op for other operating systems or if winsound fails

# --- Elo Rating System Components ---

def color_text(text, color_code):
    """Applies ANSI color codes to text."""
    return f"\033[{color_code}m{text}\033[0m"

def get_level(rating):
    """Calculates a player's level based on their rating."""
    return f"Level {int(rating ** 0.5)}"

class Player:
    """Represents a player with an Elo rating."""
    def __init__(self, name, rating=1200, k_factor=30): # Adjusted default rating for new players
        self.name = name
        self.rating = rating
        self.k_factor = k_factor
        self.old_names = []  # track previous names (optional)

    def __str__(self):
        """Returns a string representation of the player with their rating, tier, and progress bar."""
        tier = get_tier(self.rating)
        level = get_level(self.rating)
        progress = get_progress_bar(self.rating)
        return f"{self.name}: {round(self.rating)} ({tier}, {level}) [K={self.k_factor}] {progress}"

def get_tier(rating):
    """Determines a player's tier based on their rating."""
    if rating < 500:
        return color_text("Noob 🐣", "38;5;130")
    elif rating < 1000:
        return color_text("Beginner 🧑‍🎓", "37")
    elif rating < 1500:
        return color_text("Novice 🚹", "38;5;209")
    elif rating < 2000:
        return color_text("Intermediate 🧠", "38;5;225")
    elif rating < 2500:
        return color_text("Advanced 🧪", "38;5;228")
    elif rating < 3000:
        return color_text("Expert 🢼", "38;5;117")
    elif rating < 3500:
        return color_text("Elite 🧮", "38;5;201")
    elif rating < 4000:
        return color_text("Master 🧙", "38;5;46")
    elif rating < 4500:
        return color_text("Grandmaster 🏆", "34")
    elif rating < 5000:
        return color_text("Supergrandmaster 🫸", "31")
    else:
        return color_text("Legendary �", "38;5;51")

def get_tier_color_code(rating):
    """Returns the ANSI color code for a player's tier."""
    if rating < 500:
        return "38;5;130"
    elif rating < 1000:
        return "37"
    elif rating < 1500:
        return "38;5;209"
    elif rating < 2000:
        return "38;5;225"
    elif rating < 2500:
        return "38;5;228"
    elif rating < 3000:
        return "38;5;117"
    elif rating < 3500:
        return "38;5;201"
    elif rating < 4000:
        return "38;5;46"
    elif rating < 4500:
        return "34"
    elif rating < 5000:
        return "31"
    else:
        return "38;5;51"

def get_progress_bar(rating):
    """Generates a progress bar for a player's current tier."""
    tiers = [
        (1, 499), (500, 999), (1000, 1499), (1500, 1999), (2000, 2499),
        (2500, 2999), (3000, 3499), (3500, 3999), (4000, 4499), (4500, 4999),
        (5000, 9999)
    ]
    for low, high in tiers:
        if low <= rating <= high:
            progress = (rating - low) / (high - low + 1) # Added +1 to avoid division by zero for narrow tiers
            filled = int(progress * 10)
            empty = 10 - filled
            color = get_tier_color_code(rating)
            bar = "[" + "█" * filled + "░" * empty + "]"
            return f"\033[{color}m{bar}\033[0m"
    return "[██████████]"

def calculate_expected_score(player_a, player_b):
    """Calculates the expected score for player A against player B."""
    return 1 / (1 + 10 ** ((player_b.rating - player_a.rating) / 400))

def update_ratings(player_a, player_b, result):
    expected_a = calculate_expected_score(player_a, player_b)
    expected_b = calculate_expected_score(player_b, player_a)

    avg = (player_a.rating + player_b.rating) / 2
    adjusted_k_a = player_a.k_factor / 50
    adjusted_k_b = player_b.k_factor / 50
    adjust_value_a = avg ** adjusted_k_a
    adjust_value_b = avg ** adjusted_k_b

    old_rating_a = player_a.rating
    old_rating_b = player_b.rating

    player_a.rating += adjust_value_a * (result - expected_a)
    player_b.rating += adjust_value_b * ((1 - result) - expected_b)

    player_a.rating = max(1, min(9999, player_a.rating))
    player_b.rating = max(1, min(9999, player_b.rating))

    return old_rating_a, old_rating_b, player_a.rating, player_b.rating

def undo_last_match(players_dict, match_history, redo_stack):
    """Undoes the last recorded match, restoring player ratings."""
    if not match_history:
        print("❌ No match to undo.")
        return

    name_a, name_b, old_rating_a, old_rating_b, new_rating_a, new_rating_b = match_history.pop()

    if name_a in players_dict and name_b in players_dict:
        # The tuple stored in redo_stack is (name_a, name_b, rating_a_after_match, rating_b_after_match, rating_a_before_match, rating_b_before_match)
        redo_stack.append((name_a, name_b, new_rating_a, new_rating_b, old_rating_a, old_rating_b))
        players_dict[name_a].rating = old_rating_a
        players_dict[name_b].rating = old_rating_b
        print(f"↩️ Undid last match between {name_a} and {name_b}. Ratings restored.")
        safe_beep(700, 200)
    else:
        print("❌ One or both players not found. Cannot undo.")

def redo_last_match(players_dict, redo_stack, match_history):
    """Redoes the last undone match, reapplying rating changes."""
    if not redo_stack:
        print("❌ No match to redo.")
        return

    # Correctly interpret what's popped from redo_stack
    # It stores (name_a, name_b, rating_a_after_match, rating_b_after_match, rating_a_before_match, rating_b_before_match)
    name_a, name_b, rating_a_after_match, rating_b_after_match, rating_a_before_match, rating_b_before_match = redo_stack.pop()

    if name_a in players_dict and name_b in players_dict:
        # Set ratings to the 'after match' values (which were the 'new' ratings before undo)
        players_dict[name_a].rating = rating_a_after_match
        players_dict[name_b].rating = rating_b_after_match
        
        # Push the original match record back to match_history
        match_history.append((name_a, name_b, rating_a_before_match, rating_b_before_match, rating_a_after_match, rating_b_after_match))
        
        print(f"🔁 Redid match between {name_a} and {name_b}. Ratings reapplied.")
        safe_beep(750, 200)
    else:
        print("❌ One or both players not found. Cannot redo.")

def show_leaderboard(players_dict):
    """Prints the current Elo leaderboard."""
    if not players_dict:
        print("No players registered yet.")
        return

    sorted_players = sorted(players_dict.values(), key=lambda p: p.rating, reverse=True)
    print("\n📊 Elo Leaderboard:")
    safe_beep(1000, 200)
    for i, player in enumerate(sorted_players, start=1):
        print(f"{i}. {player}")

def export_leaderboard(players_dict, filename="leaderboard.txt"):
    """Exports the leaderboard to a text file."""
    if not players_dict:
        print("No players to export.")
        return
    sorted_players = sorted(players_dict.values(), key=lambda p: p.rating, reverse=True)
    with open(filename, "w", encoding='utf-8') as file:
        file.write("📊 Elo Leaderboard:\n")
        for i, player in enumerate(sorted_players, start=1):
            file.write(f"{i}. {str(player)}\n")
    print(f"📁 Leaderboard exported to {filename}")
    safe_beep(1200, 200)

def export_leaderboard_csv(players_dict):
    """Exports the leaderboard to a CSV file."""
    if not players_dict:
        print("No players to export.")
        return
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"leaderboard_{timestamp}.csv"
    sorted_players = sorted(players_dict.values(), key=lambda p: p.rating, reverse=True)
    with open(filename, "w", newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Name", "Rating", "Tier", "Level", "K-Factor", "Progress Bar"])
        for player in sorted_players:
            tier = get_tier(player.rating)
            level = get_level(player.rating)
            progress = get_progress_bar(player.rating)
            writer.writerow([player.name, round(player.rating), tier, level, player.k_factor, progress])
    print(f"📁 CSV Leaderboard exported to {filename}")
    safe_beep(1300, 200)

def loading_animation(text="Processing"):
    """Displays a simple loading animation."""
    for i in range(3):
        print(f"{text}{'.' * (i + 1)}", end='\r')
        time.sleep(0.4)
    print(" " * len(text + "..."), end='\r')

def average_rating(players_dict):
    """Calculates the average rating of all registered players."""
    if not players_dict:
        return 0
    total = sum(player.rating for player in players_dict.values())
    return total / len(players_dict)

def email_leaderboard(players_dict, recipient_email):
    """Emails the leaderboard as a CSV attachment."""
    print("Note: Email functionality requires configuring your email client/server settings.")
    print("For security, avoid using real credentials directly in code in production environments.")
    print("This feature might not work depending on your environment's network restrictions and email provider.")
    
    # This feature requires a pre-configured SMTP server and app password,
    # which cannot be done within this sandbox environment.
    # Therefore, this will likely fail unless executed in a local environment with proper setup.
    print("Skipping email attempt as it requires external SMTP server configuration.")
    # You would typically generate the CSV and then attach it like this:
    # timestamp = time.strftime("%Y%m%d-%H%M%S")
    # filename = f"leaderboard_{timestamp}.csv"
    # sorted_players = sorted(players_dict.values(), key=lambda p: p.rating, reverse=True)
    # with open(filename, "w", newline='', encoding='utf-8') as file:
    #     writer = csv.writer(file)
    #     writer.writerow(["Name", "Rating", "Tier", "Progress"])
    #     for player in sorted_players:
    #         tier = get_tier(player.rating)
    #         progress = get_progress_bar(player.rating)
    #         writer.writerow([player.name, round(player.rating), tier, progress])

    # msg = EmailMessage()
    # msg['Subject'] = '📊 Elo Leaderboard Export'
    # msg['From'] = 'your_email@example.com' # <<< REPLACE WITH YOUR SENDER EMAIL
    # msg['To'] = recipient_email
    # msg.set_content('Attached is the latest Elo leaderboard.')

    # with open(filename, 'rb') as f:
    #     file_data = f.read()
    #     msg.add_attachment(file_data, maintype='text', subtype='csv', filename=filename)

    # try:
    #     with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    #         smtp.login('your_email@example.com', 'your_app_password') # <<< REPLACE WITH YOUR EMAIL AND APP PASSWORD
    #         smtp.send_message(msg)
    #     print(f"📤 Leaderboard emailed to {recipient_email}")
    #     safe_beep(1400, 200)
    # except Exception as e:
    #     print(f"❌ Failed to send email: {e}")

# helper to replace player names inside match history / redo stacks
def _replace_name_in_match_lists(from_name, to_name, match_history, match_redo):
    """Helper function to update player names in match history records."""
    def replace_in_list(lst):
        for idx, rec in enumerate(lst):
            if len(rec) >= 2:
                a, b = rec[0], rec[1]
                changed = False
                if a == from_name:
                    a = to_name
                    changed = True
                if b == from_name:
                    b = to_name
                    changed = True
                if changed:
                    lst[idx] = (a, b) + tuple(rec[2:])
    replace_in_list(match_history)
    replace_in_list(match_redo)

def rename_player(players_dict, old_name, new_name, rename_history, rename_redo, match_history, match_redo):
    """Renames a player and updates all associated records."""
    if not old_name or not new_name:
        print("❌ Names cannot be empty.")
        return

    if old_name not in players_dict:
        print(f"❌ Player '{old_name}' not found.")
        return

    if new_name in players_dict:
        print(f"❌ Player '{new_name}' already exists.")
        return

    # Move player and log old name
    players_dict[new_name] = players_dict.pop(old_name)
    players_dict[new_name].old_names.append(old_name)
    players_dict[new_name].name = new_name

    # Update stored match history & redo stacks (so undo/redo still works)
    _replace_name_in_match_lists(old_name, new_name, match_history, match_redo)

    # Record rename action for undo
    rename_history.append((old_name, new_name))
    rename_redo.clear()
    print(f"✅ Renamed '{old_name}' to '{new_name}'.")
    safe_beep(900, 200)

def undo_rename(players_dict, rename_history, rename_redo, match_history, match_redo):
    """Undoes the last player rename operation."""
    if not rename_history:
        print("❌ No rename to undo.")
        return

    old_name, new_name = rename_history.pop()  # undo last rename (old -> new)
    # current player should be under new_name
    if new_name not in players_dict:
        print("❌ Cannot undo rename: current name not found.")
        # put it back just in case
        rename_history.append((old_name, new_name))
        return

    # move back
    players_dict[old_name] = players_dict.pop(new_name)
    players_dict[old_name].name = old_name
    # remove the last recorded old name if present
    if players_dict[old_name].old_names:
        # the last appended should be old_name
        try:
            players_dict[old_name].old_names.pop()
        except Exception:
            pass

    # update match history names back new->old
    _replace_name_in_match_lists(new_name, old_name, match_history, match_redo)

    # record redo tuple so it can be reapplied later if you decide to implement redo
    rename_redo.append((old_name, new_name))
    print(f"↩️ Undo rename: '{new_name}' reverted to '{old_name}'.")
    safe_beep(950, 200)

# 🔍 Search players by tier
def search_players_by_tier(players_dict):
    """Searches and displays players belonging to a specific tier."""
    tier_input = input("Enter tier name (e.g., 'Expert 🧭'): ").strip()
    found = [p for p in players_dict.values() if get_tier(p.rating) == tier_input]
    if not found:
        print("❌ No players found in that tier.")
    else:
        print(f"\n🎯 Players in {tier_input}:")
        for player in found:
            print(player)

# 📈 Show rating distribution
def show_rating_distribution(players_dict):
    """Displays the distribution of players across different rating tiers."""
    distribution = {}
    for player in players_dict.values():
        tier = get_tier(player.rating)
        distribution[tier] = distribution.get(tier, 0) + 1

    print("\n📊 Rating Distribution:")
    for tier, count in sorted(distribution.items(), key=lambda x: x[0]):
        print(f"{tier}: {count} player(s)")

# ⚔️ Compare two players
def compare_players(players_dict):
    """Compares two players and shows their expected win chances."""
    name1 = input("Enter first player name: ")
    name2 = input("Enter second player name: ")

    if name1 not in players_dict or name2 not in players_dict:
        print("❌ Both players must be registered.")
        return

    p1 = players_dict[name1]
    p2 = players_dict[name2]
    expected1 = calculate_expected_score(p1, p2)
    expected2 = calculate_expected_score(p2, p1)

    print(f"\n📊 Comparison:")
    print(f"{p1.name}: {round(p1.rating)} ({get_tier(p1.rating)}, {get_level(p1.rating)})")
    print(f"{p2.name}: {round(p2.rating)} ({get_tier(p2.rating)}, {get_level(p2.rating)})")
    print(f"Expected win chance:")
    print(f"  {p1.name}: {round(expected1 * 100, 2)}%")
    print(f"  {p2.name}: {round(expected2 * 100, 2)}%")

# --- Tic Tac Toe Game Logic (adapted) ---

def print_board(board):
    """
    Prints the Tic Tac Toe board to the console with colored marks,
    ensuring symmetrical alignment for 11-character width.
    'X' will be red, and 'O' will be blue.
    """
    board_width = 11

    print("\n" + "=" * board_width) # Top border
    for i in range(3):
        row_display_parts = []
        for spot in board[i]:
            # Each spot is padded to 3 characters: " X ", " O ", or "   "
            if spot == "X":
                row_display_parts.append(f"{COLOR_RED} {spot} {COLOR_RESET}")
            elif spot == "O":
                row_display_parts.append(f"{COLOR_BLUE} {spot} {COLOR_RESET}")
            else:
                row_display_parts.append("   ") # Three spaces for empty spot
        # Join parts with a single "|" to form the row: " X | O |   "
        print("|".join(row_display_parts))
        if i < 2:
            # Horizontal separator matching the board_width: "---+---+---"
            print("---+" * 2 + "---")
    print("=" * board_width + "\n") # Bottom border

def check_win(board, player):
    """Checks if the given player has won the game."""
    # Check rows
    for row in board:
        if all([s == player for s in row]):
            return True
    # Check columns
    for col in range(3):
        if all([board[row][col] == player for row in range(3)]):
            return True
    # Check diagonals
    if all([board[i][i] == player for i in range(3)]):
        return True
    if all([board[i][2-i] == player for i in range(3)]):
        return True
    return False

def check_draw(board):
    """Checks if the game is a draw (no empty spaces left)."""
    for row in board:
        for spot in row:
            if spot == " ":
                return False
    return True

def get_human_move(player_mark):
    """Gets a valid move from the human player."""
    while True:
        try:
            move = input(f"Player {player_mark}, enter your move (row, column, e.g., 1 2): ")
            row, col = map(int, move.split())
            row -= 1
            col -= 1
            if 0 <= row < 3 and 0 <= col < 3:
                return row, col
            else:
                print("Invalid move. Row and column must be between 1 and 3. Try again.")
        except ValueError:
            print("Invalid input format. Please enter two numbers separated by a space (e.g., 1 2).")
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Please try again.")


def minimax(board, depth, is_maximizing_player, maximizing_player_mark, minimizing_player_mark):
    """
    Implements the Minimax algorithm to evaluate the best move.
    Returns the score for the current board state.
    """
    if check_win(board, maximizing_player_mark):
        return 1
    if check_win(board, minimizing_player_mark):
        return -1
    if check_draw(board):
        return 0

    if is_maximizing_player:
        max_eval = -math.inf
        for r in range(3):
            for c in range(3):
                if board[r][c] == " ":
                    board[r][c] = maximizing_player_mark
                    eval = minimax(board, depth + 1, False, maximizing_player_mark, minimizing_player_mark)
                    board[r][c] = " "
                    max_eval = max(max_eval, eval)
        return max_eval
    else:
        min_eval = math.inf
        for r in range(3):
            for c in range(3):
                if board[r][c] == " ":
                    board[r][c] = minimizing_player_mark
                    eval = minimax(board, depth + 1, True, maximizing_player_mark, minimizing_player_mark)
                    board[r][c] = " "
                    min_eval = min(min_eval, eval)
        return min_eval

def get_ai_move(board, current_ai_player, opponent_player):
    """Determines the AI's optimal move using the Minimax algorithm."""
    best_score = -math.inf
    best_move = (-1, -1)

    for r in range(3):
        for c in range(3):
            if board[r][c] == " ":
                board[r][c] = current_ai_player
                score = minimax(board, 0, False, current_ai_player, opponent_player)
                board[r][c] = " "

                if score > best_score:
                    best_score = score
                    best_move = (r, c)
    return best_move

def get_current_board_evaluation(board, perspective_player, opponent_player):
    """Returns the Minimax evaluation of the current board state from a specific player's perspective."""
    return minimax(board, 0, True, perspective_player, opponent_player)

def run_tic_tac_toe_game(players_dict, match_history, redo_stack):
    """
    Runs a single Tic Tac Toe game session, handling game modes and Elo updates.
    """
    board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
    game_players = ["X", "O"] # Marks on the board
    current_player_index = 0 # X always starts

    print("\n--- Tic Tac Toe Game Modes ---")
    game_mode = ""
    while game_mode not in ["1", "2", "3", "4", "5"]:
        game_mode = input(
            "1. Human vs Human (Ranked Elo Match)\n"
            "2. Human vs Human (Unranked)\n"
            "3. Human vs AI\n"
            "4. AI vs AI\n"
            "5. Back to Main Menu\n"
            "Enter your choice: "
        )
        if game_mode not in ["1", "2", "3", "4", "5"]:
            print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")
    
    if game_mode == "5": # Back to Main Menu
        return

    player_x_obj = None
    player_o_obj = None

    if game_mode == "1": # Human vs Human (Ranked Elo Match)
        print("\n--- Select Players for Ranked Match ---")
        while True:
            name_x = input("Enter name for Player X (from Elo system): ").strip()
            if name_x in players_dict:
                player_x_obj = players_dict[name_x]
                break
            else:
                print(f"❌ Player '{name_x}' not found. Please add them in the Elo Management menu first.")
        
        while True:
            name_o = input("Enter name for Player O (from Elo system): ").strip()
            if name_o in players_dict:
                if name_o == name_x:
                    print("❌ Player O cannot be the same as Player X. Choose a different player.")
                else:
                    player_o_obj = players_dict[name_o]
                    break
            else:
                print(f"❌ Player '{name_o}' not found. Please add them in the Elo Management menu first.")
        
        print(f"\nRanked match: {player_x_obj.name} (X, Rating: {round(player_x_obj.rating)}) vs {player_o_obj.name} (O, Rating: {round(player_o_obj.rating)})")

    print("\nStarting Tic Tac Toe!")
    print("Enter your move as 'row column' (e.g., '1 1' for top-left).")


    while True:
        current_board_player_mark = game_players[current_player_index]
        print_board(board)

        # Display current player's evaluation
        eval_perspective_player = current_board_player_mark
        eval_opponent_player = game_players[(current_player_index + 1) % 2]
        
        board_copy_for_eval = [row[:] for row in board]
        evaluation = get_current_board_evaluation(board_copy_for_eval, eval_perspective_player, eval_opponent_player)
        
        eval_bar_display = ""
        if evaluation == 1:
            eval_bar_display = f"Evaluation (for {eval_perspective_player}): [ {eval_perspective_player} WIN ]"
        elif evaluation == 0:
            eval_bar_display = f"Evaluation (for {eval_perspective_player}): [   DRAW   ]"
        elif evaluation == -1:
            eval_bar_display = f"Evaluation (for {eval_perspective_player}): [ {eval_opponent_player} WIN ]"
        
        print(f"Board Evaluation (from {eval_perspective_player}'s perspective): {evaluation}")
        print(eval_bar_display)

        row, col = -1, -1 # Initialize move coordinates

        if game_mode == "1" or game_mode == "2": # Human vs Human (Ranked or Unranked)
            row, col = get_human_move(current_board_player_mark)
        elif game_mode == "3": # Human vs AI
            if current_board_player_mark == "X": # Human player
                row, col = get_human_move("X")
            else: # AI's turn (O)
                print(f"Player {current_board_player_mark} (AI)'s turn...")
                row, col = get_ai_move(board, "O", "X")
                time.sleep(1)
        elif game_mode == "4": # AI vs AI
            if current_board_player_mark == "X":
                print(f"Player {current_board_player_mark} (AI_1)'s turn...")
                row, col = get_ai_move(board, "X", "O")
            else:
                print(f"Player {current_board_player_mark} (AI_2)'s turn...")
                row, col = get_ai_move(board, "O", "X")
            time.sleep(1)

        # Validate the obtained move
        if not (0 <= row < 3 and 0 <= col < 3 and board[row][col] == " "):
            print("Invalid move detected (or AI returned invalid move). Ending game.")
            break
            
        board[row][col] = current_board_player_mark

        game_over = False
        winner_mark = None
        if check_win(board, current_board_player_mark):
            print_board(board)
            print(f"Player {current_board_player_mark} wins! Congratulations!")
            game_over = True
            winner_mark = current_board_player_mark
        elif check_draw(board):
            print_board(board)
            print("It's a draw!")
            game_over = True
            winner_mark = "DRAW" # Special string for draw

        if game_over:
            # Update Elo ratings if it was a ranked match
            if game_mode == "1": # Ranked Elo Match
                result = 0.5 # Default to draw
                # Determine the winner based on the Tic Tac Toe board mark
                if winner_mark == "X":
                    result = 1
                elif winner_mark == "O":
                    result = 0

                loading_animation("Updating ratings")
                old_x, old_o, new_x, new_o = update_ratings(
                    player_x_obj, player_o_obj, result, player_x_obj.k_factor # Using Player X's K-factor for both
                )
                match_history.append((player_x_obj.name, player_o_obj.name, old_x, old_o, new_x, new_o))
                redo_stack.clear() # Clear redo stack on new match
                print(f"\n--- Elo Rating Update ---")
                print(f"{player_x_obj.name}: {round(old_x)} -> {round(new_x)}")
                print(f"{player_o_obj.name}: {round(old_o)} -> {round(new_o)}")
                safe_beep(800, 300)
            break

        current_player_index = (current_player_index + 1) % 2


# --- Main Application Loop ---

def main():
    """Main function to run the Tic Tac Toe and Elo Rating system."""
    players = {} # Dictionary to store Player objects: {name: Player_object}
    match_history = []
    redo_stack = []
    rename_history = []
    rename_redo = []

    print("Welcome to Tic Tac Toe!")

    while True:
        print("\n--- Main Menu ---")
        print("1. Play Tic Tac Toe")
        print("2. Manage Elo Players")
        print("3. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            run_tic_tac_toe_game(players, match_history, redo_stack)
        elif choice == "2":
            while True:
                print("\n--- Elo Management Menu ---")
                print("1. Add Player")
                print("2. Show Leaderboard") # Was 3
                print("3. Change Player's K-factor") # Was 4
                print("4. Remove Player") # Was 5
                print("5. Export Leaderboard to File (.txt)") # Was 6
                print("6. Export Leaderboard to CSV (.csv)") # Was 7
                print("7. Email Leaderboard (Requires Setup)") # Was 8
                print("8. Search Players by Tier") # Was 9
                print("9. Show Rating Distribution") # Was 10
                print("10. Compare Two Players") # Was 11
                print("11. Undo Last Match") # Was 12
                print("12. Redo Last Match") # Was 13
                print("13. Rename Player") # Was 14
                print("14. Undo Rename Player") # Was 15
                print("15. Back to Main Menu") # Was 16

                elo_choice = input("Enter your choice: ")

                if elo_choice == "1":
                    name = input("Enter player name: ")
                    if name in players:
                        print("Player already exists.")
                        continue
                    rating_input = input("Enter starting rating (or press Enter for 2500): ")
                    k_factor_input = input("Enter starting K-factor (or press Enter for 20): ")
                    try:
                        rating = int(rating_input) if rating_input else 2500
                        k_factor = int(k_factor_input) if k_factor_input else 20
                        rating = max(1, min(9999, rating))
                        k_factor = max(1, min(40, k_factor))
                        players[name] = Player(name, rating, k_factor)
                        print(f"{name} added with rating {rating} and K-factor {k_factor}.")
                        safe_beep(600, 200)
                    except ValueError:
                        print("❌ Invalid input. Rating and K-factor must be numbers.")
                
                elif elo_choice == "2": # Now for Show Leaderboard
                    show_leaderboard(players)

                elif elo_choice == "3": # Now for Change Player's K-factor
                    name = input("Enter player name to change K-factor: ")
                    if name not in players:
                        print("❌ Player not found.")
                        continue
                    try:
                        new_k = int(input(f"Enter new K-factor for {name} (1-40): "))
                        if 1 <= new_k <= 40:
                            players[name].k_factor = new_k
                            print(f"🔧 K-factor for {name} updated to {new_k}.")
                        else:
                            print("❌ K-factor must be between 1 and 40.")
                    except ValueError:
                        print("❌ Invalid number. Try again.")
                
                elif elo_choice == "4": # Now for Remove Player
                    name = input("Enter the player name to remove: ")
                    if name in players:
                        confirm = input(f"Are you sure you want to remove {name}? This cannot be undone. (yes/no): ").lower()
                        if confirm == 'yes':
                            del players[name]
                            print(f"🗑️ {name} has been removed from the leaderboard.")
                        else:
                            print("Removal cancelled.")
                    else:
                        print("❌ Player not found.")

                elif elo_choice == "5": # Now for Export Leaderboard to File
                    export_leaderboard(players)

                elif elo_choice == "6": # Now for Export Leaderboard to CSV
                    export_leaderboard_csv(players)

                elif elo_choice == "7": # Now for Email Leaderboard
                    recipient = input("Enter recipient email: ")
                    email_leaderboard(players, recipient)

                elif elo_choice == "8": # Now for Search Players by Tier
                    search_players_by_tier(players)

                elif elo_choice == "9": # Now for Show Rating Distribution
                    show_rating_distribution(players)

                elif elo_choice == "10": # Now for Compare Two Players
                    compare_players(players)

                elif elo_choice == "11": # Now for Undo Last Match
                    undo_last_match(players, match_history, redo_stack)

                elif elo_choice == "12": # Now for Redo Last Match
                    redo_last_match(players, redo_stack, match_history)

                elif elo_choice == "13": # Now for Rename Player
                    old = input("Enter current player name to rename: ").strip()
                    new = input("Enter new name: ").strip()
                    rename_player(players, old, new, rename_history, rename_redo, match_history, redo_stack)

                elif elo_choice == "14": # Now for Undo Rename Player
                    undo_rename(players, rename_history, rename_redo, match_history, redo_stack)
                
                elif elo_choice == "15": # Now for Back to Main Menu
                    break # Back to Main Menu
                else:
                    print("❌ Invalid choice. Try again.")

        elif choice == "3":
            print("👋 Thanks for playing! Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()
