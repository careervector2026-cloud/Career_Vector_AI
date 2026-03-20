#difficulty_engine.py
def determine_difficulty(github_score, leetcode_score, readiness_score):

    combined = (github_score + leetcode_score + readiness_score) / 3

    if combined > 0.75:
        return "hard"

    if combined > 0.45:
        return "medium"

    return "easy"

def adjust_difficulty(current_difficulty, score):

    levels = ["easy", "medium", "hard"]

    idx = levels.index(current_difficulty)

    if score > 0.75 and idx < 2:
        idx += 1

    elif score < 0.45 and idx > 0:
        idx -= 1

    return levels[idx]