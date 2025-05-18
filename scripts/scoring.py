from rapidfuzz import fuzz

def score_responses(expected, actual, threshold=85):
    """Compares actual responses to expected words, returns score and details."""
    score = 0
    details = {}
    for cue, correct_word in expected.items():
        response = actual.get(cue, "").lower().strip()
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