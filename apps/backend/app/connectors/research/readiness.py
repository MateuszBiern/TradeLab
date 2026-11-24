import os


SOURCE_SETUP = {
    "twelve_data_prices": (("TWELVE_DATA_API_KEY",), "Wymaga klucza Twelve Data. Ceny i katalog instrumentow sa pobierane dopiero na zadanie."),
    "google_news": ((), "Publiczny kana\u0142 RSS, bez klucza API."),
    "sec_filings": (("SEC_USER_AGENT",), "Wpisz SEC_USER_AGENT z nazw\u0105 aplikacji i swoim adresem e-mail w lokalnym pliku .env."),
    "world_bank": ((), "Publiczne wska\u017aniki makroekonomiczne, bez klucza API."),
    "x_posts": (("X_BEARER_TOKEN", "X_INGESTION_ENABLED"), "Wymaga tokenu X API oraz X_INGESTION_ENABLED=true. Sprawd\u017a koszt odczytu przed w\u0142\u0105czeniem."),
    "youtube_videos": (("YOUTUBE_API_KEY",), "Wymaga klucza YouTube Data API v3; zapisane dane API s\u0105 od\u015bwie\u017cane lub usuwane przed up\u0142ywem 30 dni."),
    "instagram_posts": (("INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_USER_ID"), "Wymaga tokenu API oraz ID konta Business/Creator i zatwierdzonego dost\u0119pu do hashtag search."),
}


def missing_configuration(source_key: str) -> list[str]:
    required, _message = SOURCE_SETUP.get(source_key, ((), ""))
    missing = [name for name in required if not os.getenv(name)]
    if source_key == "x_posts" and os.getenv("X_INGESTION_ENABLED", "").lower() != "true":
        missing.append("X_INGESTION_ENABLED=true")
    if source_key == "sec_filings":
        user_agent = os.getenv("SEC_USER_AGENT", "").lower()
        if "your-email" in user_agent or "example.com" in user_agent or "@" not in user_agent:
            missing.append("SEC_USER_AGENT z prawdziwym adresem e-mail")
    return missing


def is_configured(source_key: str) -> bool:
    return not missing_configuration(source_key)
