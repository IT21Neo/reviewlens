"""Label definitions — the single source of truth for sentiment and aspect labels.

Every other module (gold-label builder, keyword baseline, LLM schema, tools) imports
these constants, so a label can never be spelled two different ways.
The human-readable rules live in docs/annotation_guideline.md. Do not change these
lists after annotation has started (project brief, section 5).
"""

SENTIMENTS = ("positive", "neutral", "negative")

ASPECTS = ("taste", "price", "service", "comfort", "portion", "other")

ASPECT_DESCRIPTIONS = {
    "taste": "food/drink quality: flavour, freshness, doneness, temperature, texture, smell",
    "price": "price and value for money: expensive, cheap, worth it, extra charges",
    "service": "staff and service process: politeness, speed, waiting time, wrong orders, billing",
    "comfort": "the place: cleanliness, decoration, atmosphere, air-con, noise, seating, toilets, view",
    "portion": "amount of food: big/small portions, being full",
    "other": "any other opinion: parking, location, menu variety, opening hours, take-away/delivery",
}
