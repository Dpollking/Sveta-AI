from backend.services import risk_engine


def test_weight_lookup_matches_spec_severity_ordering():
    assert risk_engine.weight_for("MONEY_REQUEST") > risk_engine.weight_for("SUSPICIOUS_LINK")
    assert risk_engine.weight_for("SUSPICIOUS_LINK") > risk_engine.weight_for("MESSENGER_MOVE")


def test_score_discounted_for_short_conversations():
    short = risk_engine.compute_score(["MONEY_REQUEST"], message_count=5, money_sent_simulated=False)
    long = risk_engine.compute_score(["MONEY_REQUEST"], message_count=40, money_sent_simulated=False)
    assert short < long


def test_money_sent_multiplier_increases_score():
    without = risk_engine.compute_score(["MONEY_REQUEST"], message_count=40, money_sent_simulated=False)
    with_money = risk_engine.compute_score(["MONEY_REQUEST"], message_count=40, money_sent_simulated=True)
    assert with_money > without


def test_score_is_clamped_to_100():
    score = risk_engine.compute_score(
        ["MONEY_REQUEST", "BLACKMAIL_SIMULATION", "BIOMETRIC_REQUEST", "PASSWORD_REQUEST"],
        message_count=100, money_sent_simulated=True,
    )
    assert score <= 100


def test_classify_thresholds():
    assert risk_engine.classify(0) == "low"
    assert risk_engine.classify(15) == "medium"
    assert risk_engine.classify(30) == "high"
    assert risk_engine.classify(50) == "critical"
