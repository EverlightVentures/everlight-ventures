from sld.news import parse, fetch_news


def test_parse_articles():
    payload = {"articles": [
        {"title": "Grass fire near Fairfield contained", "url": "https://x/1",
         "domain": "example.com", "seendate": "20260707T120000Z", "socialimage": "https://x/i.jpg"},
        {"title": "Another story", "url": "https://x/2", "domain": "y.com"},
    ]}
    arts = parse(payload)
    assert len(arts) == 2
    assert arts[0]["title"].startswith("Grass fire")
    assert arts[0]["domain"] == "example.com"


def test_fetch_news_builds_place_query():
    seen = {}
    def fake(q, ts, mx):
        seen["q"] = q
        return {"articles": [{"title": "t", "url": "u", "domain": "d"}]}
    out = fetch_news("Solano County", fetch_fn=fake)
    assert '"Solano County"' in seen["q"]
    assert out[0]["title"] == "t"
