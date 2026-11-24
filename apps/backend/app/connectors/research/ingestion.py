import asyncio
import email.utils
import hashlib
import html
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from xml.etree import ElementTree

import asyncpg
import httpx
from app.connectors.research.readiness import missing_configuration

logger = logging.getLogger("tradelab.ingestion")


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, str] | None = None, headers: dict[str, str] | None = None) -> Any:
    """Fetch JSON with bounded retries for temporary network and rate-limit errors."""
    for attempt in range(3):
        try:
            response = await client.get(url, params=params, headers=headers)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if attempt == 2:
                raise RuntimeError(f"{type(exc).__name__} while requesting {url}: {exc!r}") from exc
            delay = 5 * (attempt + 1)
            logger.warning("Temporary %s from %s; retrying in %ss", type(exc).__name__, url, delay)
            await asyncio.sleep(delay)
            continue

        if response.status_code == 429 or response.status_code >= 500:
            if attempt == 2:
                detail = response.text[:500].strip() or response.reason_phrase
                raise RuntimeError(f"HTTP {response.status_code} from {url}: {detail}")
            retry_after = response.headers.get("Retry-After", "")
            delay = int(retry_after) if retry_after.isdigit() else 6 * (attempt + 1)
            delay = min(max(delay, 5), 60)
            logger.warning("HTTP %s from %s; retrying in %ss", response.status_code, url, delay)
            await asyncio.sleep(delay)
            continue

        if response.is_error:
            detail = response.text[:500].strip() or response.reason_phrase
            raise RuntimeError(f"HTTP {response.status_code} from {url}: {detail}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError(f"Non-JSON response from {url}: {response.text[:300]!r}") from exc
        return payload
    raise RuntimeError(f"Request failed after retries: {url}")


@dataclass
class Document:
    external_id: str
    title: str
    url: str | None
    published_at: datetime | None
    body: str
    metadata: dict[str, Any]


def _date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if len(value) == 8 and value.isdigit():
            return datetime.strptime(value, "%Y%m%d").replace(tzinfo=timezone.utc)
        if len(value) == 14 and value.isdigit():
            return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _feed_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except (TypeError, ValueError, OverflowError):
        return None


async def _google_news(client: httpx.AsyncClient) -> list[Document]:
    locale = os.getenv("GOOGLE_NEWS_LOCALE", "US:en")
    language, country = locale.split(":", 1) if ":" in locale else ("US", "en")
    query = os.getenv("GOOGLE_NEWS_QUERY") or '(stocks OR earnings OR shares OR merger OR acquisition OR inflation OR "central bank" OR oil OR sanctions OR "drug approval")'
    response = await client.get("https://news.google.com/rss/search", params={"q": query, "hl": country, "gl": language, "ceid": locale}, follow_redirects=True)
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    docs = []
    for item in root.findall("./channel/item"):
        title = item.findtext("title") or "Untitled news item"
        url = item.findtext("link")
        if not url:
            continue
        description = html.unescape(item.findtext("description") or "")
        description = re.sub(r"<[^>]+>", " ", description)
        description = re.sub(r"\s+", " ", description).strip()
        docs.append(Document(url, title, url, _feed_date(item.findtext("pubDate")), description,
            {"publisher": item.findtext("source") or "Google News", "topics_query": query}))
    return docs


async def _sec_filings(client: httpx.AsyncClient) -> list[Document]:
    response = await client.get("https://www.sec.gov/cgi-bin/browse-edgar", params={
        "action": "getcurrent", "owner": "include", "count": "100", "output": "atom",
    }, headers={"User-Agent": os.environ["SEC_USER_AGENT"], "Accept": "application/atom+xml, application/xml"})
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    atom = "{http://www.w3.org/2005/Atom}"
    docs = []
    for item in root.findall(f"{atom}entry"):
        title = item.findtext(f"{atom}title") or "SEC filing"
        link = item.find(f"{atom}link")
        url = link.get("href") if link is not None else None
        if not url:
            continue
        entry_id = item.findtext(f"{atom}id") or url
        docs.append(Document(entry_id, title, url, _date(item.findtext(f"{atom}updated")),
            item.findtext(f"{atom}summary") or "", {"source": "SEC EDGAR", "entry_id": entry_id}))
    return docs


async def _world_bank(client: httpx.AsyncClient) -> list[Document]:
    countries = os.getenv("WORLD_BANK_COUNTRIES", "WLD;USA;CHN;EUU;POL;JPN;DEU;GBR;IND;BRA")
    indicators = {"FP.CPI.TOTL.ZG": "Inflation", "NY.GDP.MKTP.KD.ZG": "GDP growth", "SL.UEM.TOTL.ZS": "Unemployment"}
    docs = []
    for code, label in indicators.items():
        response = await client.get(f"https://api.worldbank.org/v2/country/{countries}/indicator/{code}", params={"format": "json", "per_page": "100"})
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            continue
        for row in payload[1]:
            if row.get("value") is None:
                continue
            country = row.get("country", {}).get("value") or row.get("countryiso3code") or "Unknown country"
            year = row.get("date", "")
            title = f"{label}: {country} ({year})"
            url = f"https://api.worldbank.org/v2/country/{row.get('countryiso3code', '')}/indicator/{code}?date={year}&format=json"
            body = json.dumps({"indicator": label, "value": row.get("value"), "unit": row.get("unit"), "year": year}, ensure_ascii=True)
            docs.append(Document(f"{code}:{row.get('countryiso3code')}:{year}", title, url, None, body,
                {"indicator_code": code, "country_code": row.get("countryiso3code"), "year": year, "value": row.get("value")}))
    return docs


async def _gdelt(client: httpx.AsyncClient) -> list[Document]:
    params = {
        "query": '(company OR shares OR stock OR approval OR trial OR acquisition OR earnings OR crypto)',
        "mode": "ArtList", "format": "json", "sort": "datedesc", "maxrecords": "100",
    }
    params["timespan"] = "1d"
    payload = await _get_json(client, "https://api.gdeltproject.org/api/v2/doc/doc", params)
    items = payload.get("articles", [])
    return [Document(str(row.get("url", "")), str(row.get("title") or "Untitled article"),
                     row.get("url"), _date(row.get("seendate")),
                     str(row.get("title") or ""), {"domain": row.get("domain"), "language": row.get("language"), "source_country": row.get("sourcecountry")})
            for row in items if row.get("url")]


async def _clinical_trials(client: httpx.AsyncClient) -> list[Document]:
    payload = await _get_json(client, "https://clinicaltrials.gov/api/v2/studies", {
        "format": "json", "pageSize": "100", "sort": "LastUpdatePostDate:desc",
        "query.cond": "cancer OR diabetes OR cardiovascular OR rare disease",
    })
    docs = []
    for row in payload.get("studies", []):
        protocol = row.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        nct = ident.get("nctId")
        if not nct:
            continue
        title = ident.get("briefTitle") or nct
        last_update = status.get("lastUpdatePostDateStruct", {}).get("date")
        docs.append(Document(nct, title, f"https://clinicaltrials.gov/study/{nct}",
            _date(last_update or status.get("studyFirstPostDateStruct", {}).get("date")),
            json.dumps({"status": status.get("overallStatus"), "phase": protocol.get("designModule", {}).get("phases"), "conditions": protocol.get("conditionsModule", {}).get("conditions", [])}, ensure_ascii=True),
            {"nct_id": nct, "overall_status": status.get("overallStatus"), "last_update": last_update}))
    return docs


async def _openfda(client: httpx.AsyncClient) -> list[Document]:
    payload = await _get_json(client, "https://api.fda.gov/drug/drugsfda.json", {"limit": "99", "sort": "submissions.submission_status_date:desc"})
    docs = []
    for row in payload.get("results", []):
        app = row.get("application_number") or "unknown"
        product_names = [p.get("brand_name") for p in row.get("products", []) if p.get("brand_name")]
        submissions = row.get("submissions", [])
        latest = max(submissions, key=lambda s: s.get("submission_status_date", ""), default={})
        title = f"{', '.join(product_names[:3]) or 'Drug application'} ({app})"
        docs.append(Document(app, title, f"https://api.fda.gov/drug/drugsfda.json?search=application_number:%22{quote(app)}%22",
            _date(latest.get("submission_status_date")),
            json.dumps({"sponsor": row.get("sponsor_name"), "latest_submission_type": latest.get("submission_type"), "latest_submission_status": latest.get("submission_status")}, ensure_ascii=True),
            {"application_number": app, "sponsor": row.get("sponsor_name"), "submission_status": latest.get("submission_status")}))
    return docs


async def _x_posts(client: httpx.AsyncClient) -> list[Document]:
    token = os.environ["X_BEARER_TOKEN"]
    query = os.getenv("X_SEARCH_QUERY") or '(stocks OR shares OR earnings OR merger OR inflation OR oil) -is:retweet'
    limit = min(max(int(os.getenv("X_MAX_RESULTS", "10")), 10), 100)
    payload = await _get_json(client, "https://api.x.com/2/tweets/search/recent", {
        "query": query, "max_results": str(limit), "tweet.fields": "created_at,author_id,public_metrics,lang",
    }, headers={"Authorization": f"Bearer {token}"})
    docs = []
    for row in payload.get("data", []) if isinstance(payload, dict) else []:
        post_id = str(row.get("id", ""))
        if not post_id:
            continue
        text = str(row.get("text") or "")
        docs.append(Document(post_id, text[:500] or "X post", f"https://x.com/i/web/status/{post_id}",
            _date(row.get("created_at")), text,
            {"author_id": row.get("author_id"), "language": row.get("lang"), "metrics": row.get("public_metrics", {}), "query": query}))
    return docs


async def _youtube_videos(client: httpx.AsyncClient) -> list[Document]:
    query = os.getenv("YOUTUBE_SEARCH_QUERY") or "stocks|earnings|company|market|inflation|oil"
    payload = await _get_json(client, "https://www.googleapis.com/youtube/v3/search", {
        "key": os.environ["YOUTUBE_API_KEY"], "part": "snippet", "type": "video", "order": "date", "maxResults": "25", "q": query,
    })
    docs = []
    for row in payload.get("items", []) if isinstance(payload, dict) else []:
        video_id = row.get("id", {}).get("videoId")
        snippet = row.get("snippet", {})
        if not video_id:
            continue
        docs.append(Document(str(video_id), str(snippet.get("title") or "YouTube video"),
            f"https://www.youtube.com/watch?v={video_id}", _date(snippet.get("publishedAt")),
            str(snippet.get("description") or ""), {"channel": snippet.get("channelTitle"), "query": query, "source": "YouTube Data API"}))
    return docs


async def _instagram_posts(client: httpx.AsyncClient) -> list[Document]:
    token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
    user_id = os.environ["INSTAGRAM_USER_ID"]
    version = os.getenv("INSTAGRAM_GRAPH_API_VERSION", "v24.0")
    hashtags = [tag.strip().lstrip("#") for tag in os.getenv("INSTAGRAM_HASHTAGS", "stocks,investing,earnings,finance,technology").split(",") if tag.strip()][:30]
    headers = {"Authorization": f"Bearer {token}"}
    docs = []
    for tag in hashtags:
        found = await _get_json(client, f"https://graph.facebook.com/{version}/ig_hashtag_search", {"user_id": user_id, "q": tag}, headers=headers)
        hashtag_id = next(iter(found.get("data", [])), {}).get("id") if isinstance(found, dict) else None
        if not hashtag_id:
            continue
        media = await _get_json(client, f"https://graph.facebook.com/{version}/{hashtag_id}/recent_media", {
            "user_id": user_id, "fields": "id,caption,media_type,permalink,timestamp", "limit": "25",
        }, headers=headers)
        for row in media.get("data", []) if isinstance(media, dict) else []:
            media_id = str(row.get("id", ""))
            if not media_id:
                continue
            caption = str(row.get("caption") or "")
            docs.append(Document(media_id, caption[:500] or f"Instagram post #{tag}", row.get("permalink"),
                _date(row.get("timestamp")), caption, {"hashtag": tag, "media_type": row.get("media_type"), "source": "Instagram Graph API"}))
    return docs


CONNECTORS = {
    "gdelt_news": _gdelt,
    "clinical_trials": _clinical_trials,
    "openfda_drugs": _openfda,
    "google_news": _google_news,
    "sec_filings": _sec_filings,
    "world_bank": _world_bank,
    "x_posts": _x_posts,
    "youtube_videos": _youtube_videos,
    "instagram_posts": _instagram_posts,
}

POLL_INTERVALS = {"world_bank": 86400, "youtube_videos": 3600, "instagram_posts": 21600, "x_posts": 3600}


async def ingest_source(connection: asyncpg.Connection, source: asyncpg.Record, client: httpx.AsyncClient) -> tuple[int, int]:
    source_key = source["source_key"]
    run_id = await connection.fetchval(
        "INSERT INTO source_ingestion_runs (source_id, status) VALUES ($1, 'running') RETURNING id", source["id"])
    try:
        documents = await CONNECTORS[source_key](client)
        inserted = 0
        for doc in documents:
            fingerprint = hashlib.sha256("\0".join([source_key, doc.external_id, doc.title, doc.url or "", doc.body]).encode()).hexdigest()
            inserted_now = await connection.fetchval(
                """INSERT INTO source_documents (source_id, external_id, canonical_url, title, published_at, content_hash, body_text, metadata)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb)
                   ON CONFLICT (source_id, content_hash) DO UPDATE SET
                       external_id=EXCLUDED.external_id, canonical_url=EXCLUDED.canonical_url,
                       title=EXCLUDED.title, published_at=EXCLUDED.published_at,
                       body_text=EXCLUDED.body_text, metadata=EXCLUDED.metadata, retrieved_at=NOW()
                   RETURNING (xmax = 0)""",
                source["id"], doc.external_id, doc.url, doc.title[:2000], doc.published_at, fingerprint, doc.body[:50000], json.dumps(doc.metadata))
            inserted += bool(inserted_now)
        await connection.execute("UPDATE research_sources SET last_success_at=NOW(), last_polled_at=NOW(), last_error=NULL, updated_at=NOW() WHERE id=$1", source["id"])
        await connection.execute("UPDATE source_ingestion_runs SET status='completed', fetched_count=$2, inserted_count=$3, finished_at=NOW() WHERE id=$1", run_id, len(documents), inserted)
        return len(documents), inserted
    except Exception as exc:
        message = str(exc).strip() or repr(exc) or type(exc).__name__
        message = f"{type(exc).__name__}: {message}"[:2000]
        await connection.execute("UPDATE research_sources SET last_polled_at=NOW(), last_error=$2, updated_at=NOW() WHERE id=$1", source["id"], message)
        await connection.execute("UPDATE source_ingestion_runs SET status='failed', error_message=$2, finished_at=NOW() WHERE id=$1", run_id, message)
        raise


async def run_once() -> None:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        await conn.execute("""DELETE FROM opportunity_documents od USING source_documents d, research_sources s
            WHERE od.document_id=d.id AND s.id=d.source_id
              AND s.source_key IN ('x_posts','youtube_videos','instagram_posts')
              AND d.retrieved_at < NOW() - INTERVAL '29 days'""")
        purged = await conn.execute("""DELETE FROM source_documents d USING research_sources s
            WHERE s.id=d.source_id AND s.source_key IN ('x_posts','youtube_videos','instagram_posts')
              AND d.retrieved_at < NOW() - INTERVAL '29 days'""")
        logger.info("social API records older than 29 days purged: %s", purged.rsplit(" ", 1)[-1])
        sources = await conn.fetch("SELECT * FROM research_sources WHERE enabled AND source_key = ANY($1::text[]) ORDER BY source_key", list(CONNECTORS))
        headers = {"User-Agent": "TradeLabAI local research application/0.1 (read-only)"}
        timeout = httpx.Timeout(75, connect=20)
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            for source in sources:
                source_key = source["source_key"]
                missing = missing_configuration(source_key)
                if missing:
                    logger.info("%s not called; missing configuration: %s", source_key, ", ".join(missing))
                    continue
                interval = POLL_INTERVALS.get(source_key, max(300, int(os.getenv("INGESTION_INTERVAL_SECONDS", "1800"))))
                last_polled = source["last_polled_at"]
                if last_polled and (datetime.now(timezone.utc) - last_polled).total_seconds() < interval:
                    continue
                try:
                    count, new_count = await ingest_source(conn, source, client)
                    logger.info("%s: fetched=%s inserted=%s", source_key, count, new_count)
                except Exception:
                    logger.exception("Ingestion failed for %s", source_key)
    finally:
        await conn.close()


async def main() -> None:
    from app.core.migrations import apply_migrations
    await apply_migrations()
    interval = max(300, int(os.getenv("INGESTION_INTERVAL_SECONDS", "1800")))
    while True:
        await run_once()
        await asyncio.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    logging.getLogger("httpx").setLevel(logging.WARNING)
    asyncio.run(main())
