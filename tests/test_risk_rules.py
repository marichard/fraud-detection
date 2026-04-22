from risk_rules import label_risk, score_transaction


# Baseline: a clean, low-risk domestic transaction with no fraud signals.
BASE_TX = {
    "device_risk_score": 10,
    "is_international": 0,
    "ip_country": "US",
    "country": "US",
    "amount_usd": 50.0,
    "velocity_24h": 1,
    "failed_logins_24h": 0,
    "prior_chargebacks": 0,
}


def _tx(**overrides):
    return {**BASE_TX, **overrides}


# --- label_risk ---

def test_label_risk_thresholds():
    assert label_risk(10) == "low"
    assert label_risk(29) == "low"
    assert label_risk(30) == "medium"
    assert label_risk(59) == "medium"
    assert label_risk(60) == "high"
    assert label_risk(75) == "high"


# --- baseline ---

def test_clean_transaction_scores_zero():
    assert score_transaction(BASE_TX) == 0


# --- device risk ---

def test_high_device_risk_adds_risk():
    assert score_transaction(_tx(device_risk_score=70)) > score_transaction(_tx(device_risk_score=50))
    assert score_transaction(_tx(device_risk_score=50)) > score_transaction(BASE_TX)


def test_high_device_risk_scores_25():
    assert score_transaction(_tx(device_risk_score=70)) == 25
    assert score_transaction(_tx(device_risk_score=99)) == 25


def test_mid_device_risk_scores_10():
    assert score_transaction(_tx(device_risk_score=40)) == 10
    assert score_transaction(_tx(device_risk_score=69)) == 10


# --- international ---

def test_international_transaction_adds_risk():
    intl = score_transaction(_tx(is_international=1))
    domestic = score_transaction(BASE_TX)
    assert intl > domestic


def test_international_adds_15():
    assert score_transaction(_tx(is_international=1)) == 15


# --- IP-country mismatch ---

def test_ip_country_mismatch_adds_risk():
    mismatch = score_transaction(_tx(ip_country="RU", country="US"))
    match = score_transaction(BASE_TX)
    assert mismatch > match


def test_ip_country_mismatch_adds_20():
    assert score_transaction(_tx(ip_country="RU", country="US")) == 20


def test_ip_country_match_adds_nothing():
    assert score_transaction(_tx(ip_country="US", country="US")) == 0


def test_missing_ip_country_no_error():
    tx = {k: v for k, v in BASE_TX.items() if k not in ("ip_country", "country")}
    assert score_transaction(tx) == 0


# --- amount ---

def test_large_amount_adds_risk():
    assert score_transaction(_tx(amount_usd=1000)) > score_transaction(_tx(amount_usd=500))
    assert score_transaction(_tx(amount_usd=500)) > score_transaction(BASE_TX)


def test_amount_over_1000_adds_25():
    assert score_transaction(_tx(amount_usd=1000)) == 25
    assert score_transaction(_tx(amount_usd=5000)) == 25


def test_amount_500_to_999_adds_10():
    assert score_transaction(_tx(amount_usd=500)) == 10
    assert score_transaction(_tx(amount_usd=999)) == 10


# --- velocity ---

def test_high_velocity_adds_risk():
    assert score_transaction(_tx(velocity_24h=6)) > score_transaction(_tx(velocity_24h=3))
    assert score_transaction(_tx(velocity_24h=3)) > score_transaction(BASE_TX)


def test_velocity_6_plus_adds_20():
    assert score_transaction(_tx(velocity_24h=6)) == 20
    assert score_transaction(_tx(velocity_24h=10)) == 20


def test_velocity_3_to_5_adds_5():
    assert score_transaction(_tx(velocity_24h=3)) == 5
    assert score_transaction(_tx(velocity_24h=5)) == 5


# --- failed logins ---

def test_failed_logins_add_risk():
    assert score_transaction(_tx(failed_logins_24h=5)) > score_transaction(_tx(failed_logins_24h=2))
    assert score_transaction(_tx(failed_logins_24h=2)) > score_transaction(BASE_TX)


def test_failed_logins_5_plus_adds_20():
    assert score_transaction(_tx(failed_logins_24h=5)) == 20


def test_failed_logins_2_to_4_adds_10():
    assert score_transaction(_tx(failed_logins_24h=2)) == 10
    assert score_transaction(_tx(failed_logins_24h=4)) == 10


# --- prior chargebacks ---

def test_prior_chargebacks_add_risk():
    assert score_transaction(_tx(prior_chargebacks=2)) > score_transaction(_tx(prior_chargebacks=1))
    assert score_transaction(_tx(prior_chargebacks=1)) > score_transaction(BASE_TX)


def test_two_plus_prior_chargebacks_adds_25():
    assert score_transaction(_tx(prior_chargebacks=2)) == 25
    assert score_transaction(_tx(prior_chargebacks=5)) == 25


def test_one_prior_chargeback_adds_10():
    assert score_transaction(_tx(prior_chargebacks=1)) == 10


# --- compounding signals ---

def test_compounding_signals_exceed_any_single_signal():
    single = score_transaction(_tx(device_risk_score=80))  # +25
    compound = score_transaction(_tx(
        device_risk_score=80,    # +25
        is_international=1,      # +15
        velocity_24h=7,          # +20
        prior_chargebacks=2,     # +25
    ))
    assert compound > single
    assert label_risk(compound) == "high"


def test_score_clamped_to_100():
    all_signals = _tx(
        device_risk_score=85,
        is_international=1,
        ip_country="RU",
        country="US",
        amount_usd=1500,
        velocity_24h=8,
        failed_logins_24h=6,
        prior_chargebacks=3,
    )
    assert score_transaction(all_signals) == 100


def test_score_never_negative():
    assert score_transaction(BASE_TX) >= 0
