def infer_root_cause(features, rules):
    scores = {}

    for cause, rule in rules.items():
        score = 0
        for key, weight in rule.items():
            score += features.get(key, 0) * weight
        scores[cause] = score

    return sorted(scores.items(),
                  key=lambda x: x[1],
                  reverse=True)