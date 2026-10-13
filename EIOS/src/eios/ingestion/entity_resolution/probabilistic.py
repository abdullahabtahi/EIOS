"""Probabilistic Fellegi-Sunter record linkage with Jaro-Winkler distance (US4)."""

from typing import Any


def jaro_similarity(s1: str, s2: str) -> float:
    """Calculate standard Jaro distance between two strings."""
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    match_distance = max(len1, len2) // 2 - 1
    if match_distance < 0:
        match_distance = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0
    transpositions = 0

    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    transpositions = transpositions // 2
    return (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3.0


def jaro_winkler_similarity(s1: str, s2: str, prefix_weight: float = 0.1) -> float:
    """Calculate Jaro-Winkler distance with prefix scaling factor."""
    j_sim = jaro_similarity(s1.lower().strip(), s2.lower().strip())
    if j_sim < 0.7:
        return j_sim

    # Find common prefix length up to 4
    prefix_len = 0
    for c1, c2 in zip(s1.lower().strip(), s2.lower().strip()):
        if c1 == c2:
            prefix_len += 1
        else:
            break
        if prefix_len == 4:
            break

    return j_sim + (prefix_len * prefix_weight * (1.0 - j_sim))


class ProbabilisticLinker:
    """Fellegi-Sunter record linkage engine with calibrated weights."""

    def __init__(self, threshold: float = 0.85) -> None:
        self.threshold = threshold

    def evaluate_pair(
        self, profile1: dict[str, Any], profile2: dict[str, Any]
    ) -> tuple[float, bool]:
        """Compute composite match probability score between two candidate client profiles."""
        weights = {
            "name": 0.45,
            "dob": 0.25,
            "country": 0.15,
            "device": 0.15,
        }
        total_score = 0.0

        # Name comparison (Jaro-Winkler)
        n1 = profile1.get("full_name", "")
        n2 = profile2.get("full_name", "")
        if n1 and n2:
            sim = jaro_winkler_similarity(n1, n2)
            total_score += sim * weights["name"]

        # Date of birth comparison
        dob1 = str(profile1.get("dob", ""))
        dob2 = str(profile2.get("dob", ""))
        if dob1 and dob2 and dob1 == dob2:
            total_score += weights["dob"]

        # Country comparison
        c1 = str(profile1.get("country", "")).upper()
        c2 = str(profile2.get("country", "")).upper()
        if c1 and c2 and c1 == c2:
            total_score += weights["country"]

        # Device comparison
        d1 = profile1.get("device_id")
        d2 = profile2.get("device_id")
        if d1 and d2 and d1 == d2:
            total_score += weights["device"]

        is_match = total_score >= self.threshold
        return total_score, is_match
