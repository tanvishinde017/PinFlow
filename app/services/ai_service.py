"""
PinFlow AI — AI Content Generation Service
Uses Anthropic Claude to generate Pinterest-optimised titles, descriptions, and hashtags.
Returns 5 title variants and 5 description variants for maximum A/B flexibility.
"""

import re
import json
import anthropic
from flask import current_app


# Tone style guide passed into Claude's system prompt
_TONE_GUIDE = {
    "viral":     "energetic, hype-driven, uses 1-2 relevant emojis, FOMO-inducing, trending language",
    "luxury":    "elegant, aspirational, refined, no emojis, prestige-focused, sophisticated vocabulary",
    "casual":    "friendly, conversational, relatable, light emoji use, like a best-friend recommendation",
    "affiliate": "benefit-focused, deal-oriented, call-to-action heavy, value/savings-highlighted",
}


def _get_client() -> anthropic.Anthropic:
    """Create Anthropic client using the key stored in Flask config."""
    return anthropic.Anthropic(api_key=current_app.config["ANTHROPIC_API_KEY"])


def generate_pin_content(title: str, price: str, tone: str = "viral") -> dict:
    """
    Generate 5 Pinterest titles, 5 descriptions, hashtags, and a CTA for a product.

    Args:
        title: Product title from Amazon
        price: Product price string
        tone:  One of 'viral' | 'luxury' | 'casual' | 'affiliate'

    Returns:
        {
            "titles":       [str, str, str, str, str],
            "descriptions": [str, str, str, str, str],
            "hashtags":     "string of 10-15 hashtags",
            "cta":          "short call-to-action",
            "tone":         tone,
        }
    """
    style = _TONE_GUIDE.get(tone, _TONE_GUIDE["viral"])

    prompt = f"""You are a Pinterest marketing expert specialising in affiliate content.

Product title: {title}
Price: {price}
Tone: {tone} — {style}

Generate Pinterest content for this product. Return ONLY valid JSON (no markdown, no preamble) with EXACTLY this structure:
{{
  "titles": [
    "Title option 1 — max 100 chars",
    "Title option 2 — max 100 chars",
    "Title option 3 — max 100 chars",
    "Title option 4 — max 100 chars",
    "Title option 5 — max 100 chars"
  ],
  "descriptions": [
    "Description 1 — 150-200 chars, engaging, ends naturally",
    "Description 2 — 150-200 chars, different angle",
    "Description 3 — 150-200 chars, lifestyle-focused",
    "Description 4 — 150-200 chars, problem/solution angle",
    "Description 5 — 150-200 chars, social proof angle"
  ],
  "hashtags": "#tag1 #tag2 #tag3 ... (10-15 relevant hashtags as one string)",
  "cta": "Short call-to-action phrase, max 10 words"
}}

Rules:
- Each title must be meaningfully different (not just rephrasing)
- Each description must take a clearly different marketing angle
- Hashtags must be relevant to the product category
- Match the {tone} tone throughout"""

    client = _get_client()

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if Claude wraps output
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    parsed = json.loads(raw)
    parsed["tone"] = tone
    return parsed


def generate_all_tones(title: str, price: str) -> dict:
    """
    Generate content for all four tones in parallel (one call each).
    Returns a dict keyed by tone name.
    """
    results = {}
    for tone in _TONE_GUIDE:
        try:
            results[tone] = generate_pin_content(title, price, tone)
        except Exception as exc:
            print(f"[ai_service] Tone '{tone}' failed: {exc}")
            results[tone] = _fallback_content(title, tone)
    return results


def _fallback_content(title: str, tone: str) -> dict:
    """Graceful fallback when Claude API is unavailable."""
    short = title[:60]
    return {
        "titles": [
            f"🔥 {short}",
            f"✨ You Need This: {short}",
            f"Shop This Trending {short}",
            f"Discover: {short}",
            f"Don't Miss This {short}",
        ],
        "descriptions": [
            f"This {short} is taking over Pinterest! Perfect for every lifestyle. Tap to see why everyone loves it.",
            f"Looking for something special? This {short} checks every box. See the details inside!",
            f"Upgrade your everyday with this {short}. Quality you can see and feel. Shop the link!",
            f"Struggling to find the perfect item? {short} solves that problem. Available now!",
            f"Thousands already love this {short}. Join the trend and discover why it's everywhere right now.",
        ],
        "hashtags": "#amazonfinds #trending #viral #musthave #deals #shopping #style #lifestyle #inspo #discover",
        "cta": "Shop now before it's gone!",
        "tone": tone,
    }
