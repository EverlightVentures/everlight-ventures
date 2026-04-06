"""
NLP Engine -- spaCy-powered text analysis for Everlight Ventures.

Entity extraction, sentiment scoring, email parsing, and lead qualification
from unstructured text. Powers Piper's outreach, Filter's lead scoring,
and the broker pipeline's enrichment.

Uses: spaCy (MIT license) -- free, open source.
Model: en_core_web_sm (small English model, ~12MB).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

try:
    import spacy
    _SPACY_AVAILABLE = True
except ImportError:
    _SPACY_AVAILABLE = False

log = logging.getLogger(__name__)

# Load spaCy model (lazy)
_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is None and _SPACY_AVAILABLE:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            log.warning("spaCy model en_core_web_sm not found, falling back to regex-only mode")
    return _nlp


# Sentiment lexicon (lightweight, no API needed)
POSITIVE_WORDS = {
    "great", "excellent", "amazing", "love", "interested", "excited", "perfect",
    "wonderful", "fantastic", "yes", "absolutely", "definitely", "impressive",
    "awesome", "brilliant", "happy", "thrilled", "opportunity", "growth",
    "profit", "win", "success", "deal", "close", "partner", "agree", "ready",
    "urgent", "asap", "priority", "budget", "approved", "signed", "confirm",
}
NEGATIVE_WORDS = {
    "no", "not", "never", "bad", "terrible", "hate", "unsubscribe", "stop",
    "cancel", "reject", "decline", "spam", "waste", "expensive", "overpriced",
    "busy", "later", "maybe", "unfortunately", "sorry", "unable", "difficult",
    "problem", "issue", "complaint", "refund", "disappointed", "frustrated",
    "competitor", "alternative", "elsewhere", "delay", "postpone", "pause",
}


@dataclass
class TextAnalysis:
    """Result of NLP analysis on a text."""
    text: str = ""
    entities: list[dict] = field(default_factory=list)
    sentiment_score: float = 0.0      # -1 (negative) to +1 (positive)
    sentiment_label: str = "neutral"   # positive, negative, neutral
    key_phrases: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    money_amounts: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    people: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    is_interested: bool = False        # Does this text signal buying interest?
    urgency_score: float = 0.0         # 0 (no urgency) to 1 (very urgent)

    def to_dict(self) -> dict:
        return {
            "sentiment_score": self.sentiment_score,
            "sentiment_label": self.sentiment_label,
            "entities": self.entities,
            "organizations": self.organizations,
            "people": self.people,
            "locations": self.locations,
            "money_amounts": self.money_amounts,
            "emails": self.emails,
            "is_interested": self.is_interested,
            "urgency_score": self.urgency_score,
            "key_phrases": self.key_phrases[:5],
        }


def analyze_text(text: str) -> TextAnalysis:
    """Full NLP analysis of a text string.

    Extracts entities, sentiment, contact info, and buying signals.
    Used by Piper (outreach), Filter (lead scoring), broker pipeline.
    """
    nlp = _get_nlp()
    result = TextAnalysis(text=text)

    # Named Entity Recognition (spaCy if available, else regex fallback)
    if nlp is not None:
        doc = nlp(text)
        for ent in doc.ents:
            result.entities.append({"text": ent.text, "label": ent.label_})
            if ent.label_ == "ORG":
                result.organizations.append(ent.text)
            elif ent.label_ == "PERSON":
                result.people.append(ent.text)
            elif ent.label_ in ("GPE", "LOC"):
                result.locations.append(ent.text)
            elif ent.label_ == "MONEY":
                result.money_amounts.append(ent.text)
    else:
        # Regex fallback for money detection when spaCy unavailable
        result.money_amounts = re.findall(r'\$[\d,]+(?:\.\d{2})?', text)

    # Extract emails, phones, URLs with regex
    result.emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    result.phones = re.findall(r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}', text)
    result.urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)

    # Sentiment analysis (lexicon-based, no API)
    words = set(text.lower().split())
    pos_count = len(words & POSITIVE_WORDS)
    neg_count = len(words & NEGATIVE_WORDS)
    total = pos_count + neg_count
    if total > 0:
        result.sentiment_score = (pos_count - neg_count) / total
    result.sentiment_label = (
        "positive" if result.sentiment_score > 0.2
        else "negative" if result.sentiment_score < -0.2
        else "neutral"
    )

    # Buying interest signals
    interest_phrases = {"interested", "demo", "pricing", "how much", "get started",
                       "sign up", "trial", "budget", "timeline", "quote", "proposal"}
    result.is_interested = bool(words & interest_phrases)

    # Urgency scoring
    urgency_words = {"asap", "urgent", "immediately", "today", "deadline",
                     "rush", "priority", "critical", "now", "quickly"}
    urgency_matches = len(words & urgency_words)
    result.urgency_score = min(urgency_matches / 3.0, 1.0)

    # Key phrases (noun chunks if spaCy available, else simple bigrams)
    if nlp is not None:
        doc = nlp(text) if not hasattr(result, '_doc') else doc
        result.key_phrases = [chunk.text for chunk in doc.noun_chunks
                              if len(chunk.text.split()) >= 2][:10]
    else:
        words = text.split()
        result.key_phrases = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)
                              if words[i][0].isupper() and len(words[i]) > 2][:10]

    return result


def analyze_email_reply(email_text: str) -> dict:
    """Specialized analysis for email replies in outreach sequences.

    Returns signals useful for outreach_optimizer ML model:
    - reply_sentiment (-1 to 1)
    - is_interested (bool)
    - urgency (0-1)
    - objections detected
    - next_action suggestion
    """
    analysis = analyze_text(email_text)

    # Detect common objections
    objection_patterns = {
        "budget": ["budget", "expensive", "cost", "afford", "price"],
        "timing": ["later", "next quarter", "not now", "busy", "postpone"],
        "authority": ["check with", "talk to", "manager", "boss", "team"],
        "need": ["don't need", "not interested", "no need", "already have"],
        "competitor": ["competitor", "alternative", "using", "switched"],
    }
    objections = []
    text_lower = email_text.lower()
    for obj_type, keywords in objection_patterns.items():
        if any(kw in text_lower for kw in keywords):
            objections.append(obj_type)

    # Suggest next action
    if analysis.is_interested and analysis.urgency_score > 0.3:
        next_action = "book_call_now"
    elif analysis.is_interested:
        next_action = "send_proposal"
    elif "timing" in objections:
        next_action = "schedule_followup_30d"
    elif "budget" in objections:
        next_action = "send_roi_case_study"
    elif "authority" in objections:
        next_action = "request_intro_to_decision_maker"
    elif "need" in objections or "competitor" in objections:
        next_action = "nurture_long_term"
    elif analysis.sentiment_score < -0.3:
        next_action = "pause_outreach"
    else:
        next_action = "follow_up_3d"

    return {
        "reply_sentiment": analysis.sentiment_score,
        "sentiment_label": analysis.sentiment_label,
        "is_interested": analysis.is_interested,
        "urgency": analysis.urgency_score,
        "objections": objections,
        "next_action": next_action,
        "organizations": analysis.organizations,
        "people": analysis.people,
        "money_amounts": analysis.money_amounts,
        "key_phrases": analysis.key_phrases[:5],
    }


def extract_lead_features(text: str) -> dict:
    """Extract ML-ready features from a lead description or email.

    Returns normalized features compatible with LeadScorer input.
    """
    analysis = analyze_text(text)

    # Estimate budget from money mentions
    budget = 0
    for m in analysis.money_amounts:
        nums = re.findall(r'[\d,]+', m.replace(",", ""))
        if nums:
            budget = max(budget, float(nums[0]))

    return {
        "budget": budget,
        "urgency": analysis.urgency_score,
        "is_tech": 1 if any(t in analysis.text.lower() for t in
                           ["saas", "software", "tech", "ai", "app", "platform"]) else 0,
        "engagement_score": min(analysis.sentiment_score + 0.5, 1.0) if analysis.sentiment_score > 0 else 0.3,
        "pain_score": min(len(analysis.key_phrases) / 5.0, 1.0),
        "referral_source": 0.8 if analysis.is_interested else 0.3,
        "has_existing_tool": 1 if any(w in analysis.text.lower() for w in
                                      ["currently using", "switched from", "migrating"]) else 0,
        "sentiment": analysis.sentiment_score,
        "organizations": analysis.organizations,
        "people": analysis.people,
    }
