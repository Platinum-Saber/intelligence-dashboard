import random
from datetime import datetime, timedelta

from app.models.news import NewsItem

_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "FX": [
        (
            "USD/LKR {dir} to {rate} as Sri Lanka {reason}",
            "The Sri Lankan rupee {dir_long} against the US dollar amid {reason}, according to CBSL data.",
        ),
        (
            "Rupee {dir} on {reason}; CBSL holds policy rate",
            "Sri Lanka's central bank kept its policy rate unchanged as the rupee {dir_long} on {reason}.",
        ),
        (
            "Sri Lanka forex reserves {event} for {month}",
            "Official reserve assets {event} during {month}, signalling {implication} for the rupee outlook.",
        ),
    ],
    "COPPER": [
        (
            "LME copper {dir} {pct}% on {reason}",
            "Copper futures on the London Metal Exchange {dir_long} {pct}% as {reason} influenced metals markets.",
        ),
        (
            "China copper demand {signal} after factory survey",
            "A Caixin PMI survey indicated copper demand from China {signal}, pushing prices {dir}.",
        ),
        (
            "Chilean miners' output {event} amid labour dispute",
            "Production at Chile's largest copper mine {event} following {reason}, tightening global supply.",
        ),
    ],
    "ALUMINIUM": [
        (
            "Aluminium slips {pct}% on surplus fears",
            "LME aluminium prices fell {pct}% as analysts flagged rising inventory levels in {region}.",
        ),
        (
            "Aluminium prices {dir} after {country} smelter {event}",
            "A major {country} aluminium smelter {event}, sending prices {dir} on supply {implication}.",
        ),
    ],
    "TRADE": [
        (
            "UAE–Sri Lanka trade corridor sees {event}",
            "Trade flows between the UAE and Sri Lanka {event} following {reason}, impacting import timelines.",
        ),
        (
            "Vietnam export {event} raises supply chain concerns",
            "Vietnam's manufacturing exports {event} amid {reason}, with potential knock-on effects for regional supply chains.",
        ),
        (
            "China shipping costs {dir} on container {reason}",
            "Freight rates from Chinese ports {dir_long} as container {reason} persisted into {month}.",
        ),
    ],
    "LOGISTICS": [
        (
            "Colombo port handling times {event} after {reason}",
            "Cargo processing at the Port of Colombo {event} following {reason}, affecting import delivery schedules.",
        ),
        (
            "Flood warnings issued for {district} Province; logistics disrupted",
            "Heavy rainfall triggered flood warnings in Sri Lanka's {district} Province, with road transport {impact}.",
        ),
    ],
}

_DIRS = [("rose", "strengthened"), ("fell", "weakened"), ("edged up", "gained marginally"), ("dipped", "eased slightly")]
_REASONS = [
    "global risk-off sentiment", "stronger US jobs data", "OPEC output signals",
    "IMF programme progress", "domestic inflation data", "trade balance improvement",
    "geopolitical uncertainty", "capital flow pressures",
]
_MONTHS = ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"]
_COUNTRIES = ["China", "UAE", "Vietnam", "Indonesia", "Australia"]
_REGIONS = ["China", "Europe", "the Middle East", "Southeast Asia"]
_DISTRICTS = ["Western", "Southern", "Central", "Northern", "Sabaragamuwa"]
_IMPACTS = ["severely disrupted", "partially affected", "at risk of delays"]
_IMPLICATIONS = ["a tighter market", "further weakness", "a modest recovery", "stability"]
_EVENTS_UP = ["increased", "expanded", "recovered", "climbed", "rose"]
_EVENTS_DOWN = ["declined", "fell", "contracted", "dropped", "weakened"]


def _pick(lst: list) -> str:
    return random.choice(lst)


def _render(template: str, **kw) -> str:
    d, d_long = _pick(_DIRS)
    pct = round(random.uniform(0.5, 3.5), 1)
    rate = round(random.uniform(289, 308), 2)
    event = _pick(_EVENTS_UP if random.random() > 0.5 else _EVENTS_DOWN)
    return template.format(
        dir=d, dir_long=d_long, pct=pct, rate=rate,
        reason=_pick(_REASONS), month=_pick(_MONTHS),
        country=_pick(_COUNTRIES), region=_pick(_REGIONS),
        district=_pick(_DISTRICTS), impact=_pick(_IMPACTS),
        implication=_pick(_IMPLICATIONS), event=event,
        signal=_pick(["improving", "weakening", "stabilising"]),
        **kw,
    )


def generate_news(days: int = 90) -> list[NewsItem]:
    records: list[NewsItem] = []
    base_ts = datetime.utcnow() - timedelta(days=days)
    topics = list(_TEMPLATES.keys())

    for i in range(days):
        day_ts = base_ts + timedelta(days=i)
        # 4–8 articles per day
        for _ in range(random.randint(4, 8)):
            topic = _pick(topics)
            headline_tpl, summary_tpl = _pick(_TEMPLATES[topic])
            published_at = day_ts + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
            records.append(NewsItem(
                published_at=published_at,
                headline=_render(headline_tpl),
                summary=_render(summary_tpl),
                url=None,
                source="debug",
                topic=topic,
                relevance_score=round(random.uniform(0.4, 1.0), 2),
                sentiment=None,  # Phase 2
            ))

    return records
