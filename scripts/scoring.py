# Write a working MVP scoring module using fuzzy string matching
scoring_code = """
from rapidfuzz import fuzz

def score_responses(expected, actual, threshold=85):
    score = 0
    details = {}
    for cue, correct_word in expected.items():
        response = actual.get(cue, "").lower()
        similarity = fuzz.ratio(correct_word.lower(), response)
        match = similarity >= threshold
        details[cue] = {
            "expected": correct_word,
            "response": response,
            "match": match,
            "similarity": similarity
        }
        if match:
            score += 1
    return score, details
"""

# Write to the scoring.py file
scoring_path = Path("/mnt/data/remindful_app/scripts/scoring.py")
scoring_path.write_text(scoring_code)

scoring_path.name
