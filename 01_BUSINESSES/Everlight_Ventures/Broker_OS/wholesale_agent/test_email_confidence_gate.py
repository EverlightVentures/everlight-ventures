"""
Tests for email_confidence_gate.py -- new deliverability-verified policy (2026-05-27).

Operator policy: deliverability-verified is the bar, not identity-verified.
No direct-mail tier. Send to anything we can deliver.
Tiers: send | try | skip
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import pytest
from email_confidence_gate import (
    email_score,
    tier_for,
    categorize,
    TIER_SEND,
    TIER_TRY,
    TIER_SKIP,
)


# ---------------------------------------------------------------------------
# Test 10: constants exist with correct string values
# ---------------------------------------------------------------------------

class TestConstants:
    def test_tier_send_value(self):
        assert TIER_SEND == "send"

    def test_tier_try_value(self):
        assert TIER_TRY == "try"

    def test_tier_skip_value(self):
        assert TIER_SKIP == "skip"


# ---------------------------------------------------------------------------
# email_score unit tests
# ---------------------------------------------------------------------------

class TestEmailScore:
    def test_verified_good_identity_high_score(self):
        """Test 1: verified + good identity -> score is high (send-worthy)."""
        c = {"email": "j@gmail.com", "confidence": 80, "verified": True,
             "sources": ["mx_check", "emailrep"]}
        s = email_score(c, identity_score=80)
        # base=50 + identity=min(20,80//5=16)=16 + disc=min(20,80//5=16)=16 = 82
        assert s >= 50, f"verified + good identity should score high, got {s}"

    def test_mx_only_no_verified_above_35(self):
        """Test 2: mx_ok only (no verified) + identity -> score >= 35 -> try tier."""
        c = {"email": "j@yahoo.com", "confidence": 60, "verified": False,
             "sources": ["mx_check"]}
        s = email_score(c, identity_score=50)
        # base=30 + identity=min(20,10)=10 + disc=min(20,12)=12 = 52
        assert s >= 35, f"mx_ok no-verified should score >=35, got {s}"
        t = tier_for(s, c)
        assert t == TIER_TRY, f"mx_ok score>=35 should be TIER_TRY, got {t}"

    def test_catch_all_source_skipped(self):
        """Test 3: catch-all source -> skip even if mx_ok."""
        c = {"email": "j@catch.com", "confidence": 70, "verified": False,
             "sources": ["mx_check", "catch-all"]}
        s = email_score(c, identity_score=60)
        t = tier_for(s, c)
        # -40 penalty makes score drop; still has mx so tier_for checks score
        # score = 30+min(20,12)+min(20,14)-40 = 30+12+14-40 = 16 < 35 -> skip
        assert t == TIER_SKIP, f"catch-all source must be TIER_SKIP, got {t}"

    def test_disposable_source_skipped(self):
        """Test 4: disposable domain source -> skip."""
        c = {"email": "j@temp.com", "confidence": 60, "verified": False,
             "sources": ["mx_check", "disposable"]}
        s = email_score(c, identity_score=60)
        t = tier_for(s, c)
        assert t == TIER_SKIP, f"disposable source must be TIER_SKIP, got {t}"

    def test_no_mx_skip(self):
        """Test 5: no MX at all -> skip regardless of score."""
        c = {"email": "j@dead.com", "confidence": 0, "verified": False,
             "sources": ["emailrep"]}  # no mx token
        t = tier_for(email_score(c, 90), c)
        assert t == TIER_SKIP, f"no MX must be TIER_SKIP, got {t}"

    def test_score_clamped_0_to_100(self):
        """Score never goes below 0 or above 100."""
        low = email_score({"email": "x@y.com", "confidence": 0, "verified": False, "sources": []}, 0)
        high = email_score({"email": "x@y.com", "confidence": 100, "verified": True,
                            "sources": ["mx_check"]}, 100)
        assert low >= 0
        assert high <= 100

    def test_duplicate_penalty_applied(self):
        """Test 7: duplicate_emails set -> -25 penalty."""
        c = {"email": "dup@gmail.com", "confidence": 80, "verified": True,
             "sources": ["mx_check", "emailrep"]}
        s_no_dup = email_score(c, identity_score=80)
        s_dup = email_score(c, identity_score=80, duplicate_emails={"dup@gmail.com"})
        assert s_dup == max(0, s_no_dup - 25), (
            f"Duplicate penalty should be -25: {s_no_dup} -> {s_dup}"
        )

    def test_duplicate_penalty_case_insensitive(self):
        """Duplicate check is case-insensitive."""
        c = {"email": "Dup@Gmail.Com", "confidence": 60, "verified": False,
             "sources": ["mx_check"]}
        s_no_dup = email_score(c, identity_score=40)
        s_dup = email_score(c, identity_score=40, duplicate_emails={"dup@gmail.com"})
        assert s_dup < s_no_dup


# ---------------------------------------------------------------------------
# tier_for boundary tests
# ---------------------------------------------------------------------------

class TestTierFor:
    def _mx_cand(self, verified=False):
        return {"email": "x@y.com", "confidence": 50, "verified": verified,
                "sources": ["mx_check"]}

    def _no_mx_cand(self):
        return {"email": "x@y.com", "confidence": 50, "verified": False,
                "sources": ["emailrep"]}

    def test_score_34_mx_ok_is_skip(self):
        """Test 9a: score=34 with mx_ok -> skip."""
        t = tier_for(34, self._mx_cand(verified=False))
        assert t == TIER_SKIP, f"score=34 mx_ok should be TIER_SKIP, got {t}"

    def test_score_35_mx_ok_is_try(self):
        """Test 9b: score=35 with mx_ok -> try."""
        t = tier_for(35, self._mx_cand(verified=False))
        assert t == TIER_TRY, f"score=35 mx_ok should be TIER_TRY, got {t}"

    def test_verified_is_always_send(self):
        """Verified candidate always -> send (regardless of score)."""
        t = tier_for(0, self._mx_cand(verified=True))
        assert t == TIER_SEND

    def test_no_mx_is_always_skip(self):
        """No MX -> skip even with high score."""
        t = tier_for(100, self._no_mx_cand())
        assert t == TIER_SKIP


# ---------------------------------------------------------------------------
# categorize integration tests
# ---------------------------------------------------------------------------

class TestCategorize:
    def test_empty_candidates_returns_skip(self):
        """Test 6: empty candidates -> skip."""
        result = categorize([], identity_score=80)
        assert result["tier"] == TIER_SKIP
        assert result["best_email"] is None
        assert result["score"] == 0
        assert result["ranked"] == []
        assert "reason" in result

    def test_verified_good_identity_resolves_to_send(self):
        """Test 1 (via categorize): verified + good identity -> send."""
        candidates = [
            {"email": "eddie.howard@gmail.com", "confidence": 80, "verified": True,
             "sources": ["mx_check", "emailrep"]},
        ]
        result = categorize(candidates, identity_score=80)
        assert result["tier"] == TIER_SEND
        assert result["best_email"] == "eddie.howard@gmail.com"

    def test_mx_only_unverified_resolves_to_try(self):
        """Test 2 (via categorize): mx_ok, no verified -> try (operator sends anyway)."""
        candidates = [
            {"email": "bennie.leggett@yahoo.com", "confidence": 60, "verified": False,
             "sources": ["mx_check"]},
        ]
        result = categorize(candidates, identity_score=50)
        assert result["tier"] == TIER_TRY
        assert result["best_email"] == "bennie.leggett@yahoo.com"

    def test_catch_all_source_resolves_to_skip(self):
        """Test 3 (via categorize): catch-all -> skip."""
        candidates = [
            {"email": "owner@catchall.com", "confidence": 70, "verified": False,
             "sources": ["mx_check", "catch-all"]},
        ]
        result = categorize(candidates, identity_score=60)
        assert result["tier"] == TIER_SKIP
        assert result["best_email"] is None

    def test_disposable_resolves_to_skip(self):
        """Test 4 (via categorize): disposable -> skip."""
        candidates = [
            {"email": "temp@disposable.com", "confidence": 60, "verified": False,
             "sources": ["mx_check", "disposable"]},
        ]
        result = categorize(candidates, identity_score=50)
        assert result["tier"] == TIER_SKIP

    def test_no_mx_resolves_to_skip(self):
        """Test 5 (via categorize): no MX -> skip."""
        candidates = [
            {"email": "owner@dead-domain.com", "confidence": 0, "verified": False,
             "sources": ["emailrep"]},  # no mx token
        ]
        result = categorize(candidates, identity_score=90)
        assert result["tier"] == TIER_SKIP
        assert result["best_email"] is None

    def test_duplicate_penalty_in_categorize(self):
        """Test 7 (via categorize): duplicate_emails kwarg flows through.

        Candidate without dup: base=30 + id=min(20,10)=10 + disc=min(20,12)=12 = 52 -> try
        Candidate with dup: 52 - 25 = 27 < 35 -> skip (no sendable candidate -> score=0)
        """
        candidates = [
            {"email": "shared@gmail.com", "confidence": 60, "verified": False,
             "sources": ["mx_check"]},
        ]
        # Without duplicate penalty score should be >= 35 -> try
        result_no_dup = categorize(candidates, identity_score=50)
        assert result_no_dup["tier"] == TIER_TRY
        # With duplicate penalty, score drops to 27 < 35 -> all candidates skip
        result_dup = categorize(candidates, identity_score=50,
                                duplicate_emails={"shared@gmail.com"})
        assert result_dup["tier"] == TIER_SKIP, (
            f"Duplicate penalty should push score below 35, making it SKIP. "
            f"ranked={result_dup['ranked']}"
        )
        assert result_dup["best_email"] is None

    def test_ranking_verified_beats_higher_unverified_at_equal_score(self):
        """
        Test 8: tiebreak -- verified wins at EQUAL score.
        If verified scores strictly less than unverified, the higher unverified wins.
        """
        # Construct two candidates with the same raw score but different verified flags.
        # verified=True: base=50 + id=0 + disc=0 = 50, sources=["mx_check"]
        # unverified with score=50: base=30 + id=min(20,20)=20 + disc=0 = 50, sources=["mx_check"]
        verified_cand = {
            "email": "verified@domain.com", "confidence": 0, "verified": True,
            "sources": ["mx_check"],
        }
        unverified_cand = {
            "email": "unverified@domain.com", "confidence": 0, "verified": False,
            "sources": ["mx_check"],
        }
        s_v = email_score(verified_cand, identity_score=0)
        s_u = email_score(unverified_cand, identity_score=100)
        assert s_v == s_u, f"Scores must match for tiebreak test: {s_v} vs {s_u}"

        result = categorize([unverified_cand, verified_cand], identity_score=0)
        # At equal score, verified should win the tiebreak
        assert result["best_email"] == "verified@domain.com", (
            f"Verified should win tiebreak at equal score, got {result['best_email']}"
        )

    def test_ranking_strictly_higher_unverified_wins_over_lower_verified(self):
        """
        Test 8b: if unverified scores STRICTLY higher (both are sendable), unverified wins.
        Verified tiebreak only applies at equal score.

        To make unverified outscore verified while both remain sendable:
        - verified at id=100, conf=0: base=50 + id=min(20,20)=20 + disc=0 = 70 -> TIER_SEND
        - unverified at id=100, conf=100: base=30 + id=20 + disc=20 = 70 -- tied!

        The only way unverified can STRICTLY outscore verified (with same identity input)
        is if verified has a PENALTY but that penalty doesn't eliminate its tier (verified
        stays TIER_SEND regardless of score). So the test must use a dup penalty on the
        verified candidate to drop it from 70 to 45 while unverified stays at 70 -> try.
        Both are non-skip (verified->send, unverified->try); unverified score 70 > verified 45.
        """
        verified_low = {
            "email": "verified_dup@domain.com", "confidence": 0, "verified": True,
            "sources": ["mx_check"],
        }
        unverified_high = {
            "email": "unverified_clean@domain.com", "confidence": 100, "verified": False,
            "sources": ["mx_check"],
        }
        # verified with dup penalty at id=100: 50+20+0-25 = 45
        s_v = email_score(verified_low, identity_score=100,
                          duplicate_emails={"verified_dup@domain.com"})
        # unverified at id=100: 30+20+20 = 70
        s_u = email_score(unverified_high, identity_score=100)
        assert s_u > s_v, (
            f"unverified_high ({s_u}) must outscore verified_dup ({s_v})"
        )
        # Both should be sendable tiers
        assert tier_for(s_v, verified_low) == TIER_SEND
        assert tier_for(s_u, unverified_high) == TIER_TRY

        result = categorize(
            [verified_low, unverified_high],
            identity_score=100,
            duplicate_emails={"verified_dup@domain.com"},
        )
        assert result["best_email"] == "unverified_clean@domain.com", (
            f"Higher-scoring unverified (70) should beat verified with dup penalty (45), "
            f"got {result['best_email']}. ranked={result['ranked']}"
        )

    def test_ranked_contains_all_candidates_with_required_keys(self):
        candidates = [
            {"email": "a@gmail.com", "confidence": 60, "verified": True,
             "sources": ["mx_check"]},
            {"email": "b@yahoo.com", "confidence": 30, "verified": False,
             "sources": ["mx_check"]},
            {"email": "c@hotmail.com", "confidence": 80, "verified": True,
             "sources": ["mx_check"]},
        ]
        result = categorize(candidates, identity_score=70)
        assert len(result["ranked"]) == 3
        for item in result["ranked"]:
            assert "email" in item
            assert "score" in item
            assert "tier" in item
            assert "verified" in item

    def test_reason_is_non_empty_string(self):
        candidates = [{"email": "a@b.com", "confidence": 50, "verified": True,
                       "sources": ["mx_check"]}]
        result = categorize(candidates, identity_score=60)
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0

    def test_all_skip_returns_skip_with_none_best(self):
        """All candidates skip -> tier=skip, best_email=None."""
        candidates = [
            {"email": "x@dead.com", "confidence": 0, "verified": False, "sources": []},
            {"email": "y@dead.com", "confidence": 0, "verified": False, "sources": []},
        ]
        result = categorize(candidates, identity_score=90)
        assert result["tier"] == TIER_SKIP
        assert result["best_email"] is None
        assert len(result["ranked"]) == 2
