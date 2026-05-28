"""
Tests for email_confidence_gate.py

Covers:
  - Verified high-confidence email + high identity_score -> auto_email
  - Verified email + mid identity_score -> review
  - Unverified email (any identity_score) -> NOT auto_email (capped at 60)
  - Empty candidates -> directmail
  - Ranking picks the highest-scoring email as best
  - tier_for boundary values
  - No-confidence-value penalty
"""
import sys
import os

# Make sure we can import from the same directory
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from email_confidence_gate import (
    email_score,
    tier_for,
    categorize,
    TIER_AUTO,
    TIER_REVIEW,
    TIER_DIRECTMAIL,
)


# ---------------------------------------------------------------------------
# email_score unit tests
# ---------------------------------------------------------------------------

class TestEmailScore:
    def test_high_identity_high_confidence_verified_gives_auto_range(self):
        """Verified, high confidence, high identity -> score in auto range (>=75)."""
        candidate = {"email": "john@gmail.com", "confidence": 80, "verified": True, "sources": []}
        score = email_score(candidate, identity_score=90)
        # base = 90*0.70 + 80*0.30 = 63 + 24 = 87
        assert score >= 75, f"Expected >=75 for auto tier, got {score}"

    def test_verified_mid_identity_gives_review_range(self):
        """Verified + mid identity_score -> score in review range (55-74)."""
        candidate = {"email": "john@gmail.com", "confidence": 70, "verified": True, "sources": []}
        score = email_score(candidate, identity_score=65)
        # base = 65*0.70 + 70*0.30 = 45.5 + 21 = 66.5 -> 67
        assert 55 <= score < 75, f"Expected 55-74 for review tier, got {score}"

    def test_unverified_email_capped_at_60_regardless_of_identity(self):
        """Unverified email is always capped at 60 -- never reaches auto_email."""
        candidate = {"email": "john@gmail.com", "confidence": 99, "verified": False, "sources": []}
        score = email_score(candidate, identity_score=100)
        assert score <= 60, f"Unverified email must not exceed 60, got {score}"

    def test_unverified_high_identity_not_auto(self):
        """Even perfect identity score cannot reach auto tier if email unverified."""
        candidate = {"email": "john@gmail.com", "confidence": 90, "verified": False, "sources": []}
        score = email_score(candidate, identity_score=100)
        assert tier_for(score) != TIER_AUTO

    def test_none_confidence_applies_penalty(self):
        """Missing confidence applies a 10-point penalty."""
        candidate_no_conf = {"email": "a@b.com", "confidence": None, "verified": True, "sources": []}
        candidate_zero_conf = {"email": "a@b.com", "confidence": 0, "verified": True, "sources": []}
        score_none = email_score(candidate_no_conf, identity_score=70)
        score_zero = email_score(candidate_zero_conf, identity_score=70)
        # None should score 10 points less than explicit 0
        assert score_none < score_zero, (
            f"None confidence ({score_none}) should score less than explicit 0 ({score_zero})"
        )

    def test_score_clamped_0_to_100(self):
        """Score never goes below 0 or above 100."""
        low = email_score({"email": "x@y.com", "confidence": 0, "verified": False, "sources": []}, 0)
        high = email_score({"email": "x@y.com", "confidence": 100, "verified": True, "sources": []}, 100)
        assert low >= 0
        assert high <= 100

    def test_score_returns_int(self):
        candidate = {"email": "a@b.com", "confidence": 50, "verified": True, "sources": []}
        s = email_score(candidate, 50)
        assert isinstance(s, int)


# ---------------------------------------------------------------------------
# tier_for unit tests
# ---------------------------------------------------------------------------

class TestTierFor:
    def test_75_is_auto(self):
        assert tier_for(75) == TIER_AUTO

    def test_74_is_review(self):
        assert tier_for(74) == TIER_REVIEW

    def test_55_is_review(self):
        assert tier_for(55) == TIER_REVIEW

    def test_54_is_directmail(self):
        assert tier_for(54) == TIER_DIRECTMAIL

    def test_0_is_directmail(self):
        assert tier_for(0) == TIER_DIRECTMAIL

    def test_100_is_auto(self):
        assert tier_for(100) == TIER_AUTO


# ---------------------------------------------------------------------------
# categorize integration tests
# ---------------------------------------------------------------------------

class TestCategorize:
    def test_empty_candidates_returns_directmail(self):
        result = categorize([], identity_score=80)
        assert result["tier"] == TIER_DIRECTMAIL
        assert result["best_email"] is None
        assert result["score"] == 0
        assert "ranked" in result
        assert result["ranked"] == []
        assert "No email candidates" in result["reason"] or "direct mail" in result["reason"].lower()

    def test_high_confidence_verified_resolves_to_auto(self):
        candidates = [
            {"email": "eddie.howard@gmail.com", "confidence": 85, "verified": True, "sources": ["emailrep"]},
        ]
        result = categorize(candidates, identity_score=90)
        assert result["tier"] == TIER_AUTO
        assert result["best_email"] == "eddie.howard@gmail.com"
        assert result["score"] >= 75

    def test_mid_identity_verified_resolves_to_review(self):
        candidates = [
            {"email": "bennie.leggett@yahoo.com", "confidence": 70, "verified": True, "sources": []},
        ]
        result = categorize(candidates, identity_score=65)
        assert result["tier"] == TIER_REVIEW

    def test_unverified_never_auto(self):
        candidates = [
            {"email": "test@gmail.com", "confidence": 95, "verified": False, "sources": []},
        ]
        result = categorize(candidates, identity_score=100)
        assert result["tier"] != TIER_AUTO

    def test_ranking_picks_highest_scoring_email(self):
        """categorize must return the highest-scored candidate as best_email."""
        candidates = [
            {"email": "low@yahoo.com",   "confidence": 20,  "verified": False, "sources": []},
            {"email": "high@gmail.com",  "confidence": 85,  "verified": True,  "sources": []},
            {"email": "mid@outlook.com", "confidence": 55,  "verified": True,  "sources": []},
        ]
        result = categorize(candidates, identity_score=85)
        assert result["best_email"] == "high@gmail.com"
        # Ranked list is sorted best-first
        assert result["ranked"][0]["email"] == "high@gmail.com"

    def test_ranked_contains_all_candidates(self):
        candidates = [
            {"email": "a@gmail.com",   "confidence": 60, "verified": True,  "sources": []},
            {"email": "b@yahoo.com",   "confidence": 30, "verified": False, "sources": []},
            {"email": "c@hotmail.com", "confidence": 80, "verified": True,  "sources": []},
        ]
        result = categorize(candidates, identity_score=70)
        assert len(result["ranked"]) == 3

    def test_all_low_scores_route_directmail(self):
        """Very low identity + unverified emails -> directmail."""
        candidates = [
            {"email": "x@gmail.com", "confidence": 10, "verified": False, "sources": []},
            {"email": "y@yahoo.com", "confidence": 5,  "verified": False, "sources": []},
        ]
        result = categorize(candidates, identity_score=10)
        assert result["tier"] == TIER_DIRECTMAIL

    def test_reason_is_non_empty_string(self):
        candidates = [{"email": "a@b.com", "confidence": 50, "verified": True, "sources": []}]
        result = categorize(candidates, identity_score=60)
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0
