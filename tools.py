"""tools.py - STUDENT IMPLEMENTS.  Source tools for the research agents.   Guide: GUIDE.md, part 1.

Rules for every tool:
  * runs on the HOST (not in the sandbox): API keys must never enter the sandbox;
  * returns a STRING (JSON text of compact records) and NEVER raises:
        "NO RESULTS"  when the source answers with nothing,
        "ERROR: ..."  when the source keeps failing after the retries (the agent then tries another source);
  * the docstring is the tool description the LLM reads: keep it precise (what it does, what it returns, when to use it).
Try your tools without any agent:   python tools.py
"""
import json  # noqa: F401
import os  # noqa: F401
import random
import re
import threading
import time  # noqa: F401
import urllib.parse
import xml.etree.ElementTree as ET

import httpx  # noqa: F401
from langchain_core.tools import tool

# ---- constants (given) ----
ARXIV_URL = "https://export.arxiv.org/api/query"  # https only: http answers 301
HF_DAILY_URL = "https://huggingface.co/api/daily_papers"
HF_SEARCH_URL = "https://huggingface.co/api/papers/search"
EXA_URL = "https://mcp.exa.ai/mcp"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_ARXIV_LOCK = threading.Lock()
_ARXIV_LAST_CALL = 0.0


class RetryableError(Exception):
    """Given. Raise it inside a call to ask with_retry to wait and try again (retry_after in seconds, optional)."""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


# ---- TODO 1: retry helper ----
def with_retry(fn, *, attempts=5, base=1.0, cap=30.0):
    """Call fn(); when it raises RetryableError, wait and call it again.

    PSEUDO-CODE:
      for attempt in 0 .. attempts-1:
          try: return fn()
          except RetryableError as e:
              if this was the last attempt: raise
              delay = e.retry_after if the server told us, else exponential backoff base * 2**attempt
              cap the delay at `cap` seconds; add random jitter to the exponential case
              sleep(delay)
    Use it to wrap EVERY network call below. Also treat these as retryable: HTTP 429/500/502/503/504,
    httpx.TransportError (timeouts, connection resets). Read the Retry-After header when present.
    """
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if base < 0 or cap < 0:
        raise ValueError("base and cap must be non-negative")
    for attempt in range(attempts):
        try:
            return fn()
        except RetryableError as exc:
            if attempt == attempts - 1:
                raise
            if exc.retry_after is not None:
                try:
                    delay = float(exc.retry_after)
                except (TypeError, ValueError):
                    delay = base * (2 ** attempt) + random.uniform(0.0, base)
            else:
                delay = base * (2 ** attempt) + random.uniform(0.0, base)
            time.sleep(min(cap, max(0.0, delay)))


def _clean_text(value, limit=None):
    text = " ".join(str(value or "").split())
    return text[:limit] if limit is not None else text


def _clamp(value, low, high):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = low
    return max(low, min(high, value))


def _retry_after(response):
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def _request_once(method, url, **kwargs):
    """Make one HTTP attempt, translating only transient failures for with_retry."""
    try:
        response = httpx.request(method, url, **kwargs)
    except httpx.TransportError as exc:
        raise RetryableError(f"{type(exc).__name__}: {exc}") from exc
    if response.status_code in RETRYABLE_STATUS_CODES:
        raise RetryableError(
            f"HTTP {response.status_code} from {url}",
            retry_after=_retry_after(response),
        )
    response.raise_for_status()
    return response


def _wait_for_arxiv_slot():
    """Serialize arXiv request starts so concurrent subagents remain polite."""
    global _ARXIV_LAST_CALL
    with _ARXIV_LOCK:
        delay = 3.0 - (time.monotonic() - _ARXIV_LAST_CALL)
        if delay > 0:
            time.sleep(delay)
        _ARXIV_LAST_CALL = time.monotonic()


def _tool_error(exc, secret=""):
    message = f"{type(exc).__name__}: {exc}"
    if secret:
        for form in {secret, urllib.parse.quote(secret, safe=""), urllib.parse.quote_plus(secret)}:
            if form:
                message = message.replace(form, "[REDACTED]")
    return f"ERROR: {message}"


# ---- TODO 2: arXiv ----
@tool
def arxiv_search(query: str, max_results: int = 10) -> str:
    """Search arXiv papers by keywords, newest first. Returns a JSON list of {id, url, published, title, summary}."""
    # PSEUDO-CODE:
    #   keep only word characters of `query` -> terms; no terms -> "NO RESULTS" (do not call the network)
    #   respect arXiv etiquette: at least 3 seconds between two arXiv calls (remember the time of the last call)
    #   GET ARXIV_URL params: search_query="all:t1 AND all:t2 ...", sortBy=submittedDate, sortOrder=descending,
    #       max_results=clamp(max_results, 1, 30)           (wrap in with_retry)
    #   parse the Atom XML: each <entry> -> {id (last part of <id> after /abs/), url, published[:10], title, summary}
    #       collapse whitespace/newlines in title and summary; cut summary to ~600 chars
    #   no entries -> "NO RESULTS"; else json.dumps(records, ensure_ascii=False)
    #   any exception -> "ERROR: <type>: <message>"
    try:
        terms = [
            term for term in re.findall(r"[^\W_]+(?:-[^\W_]+)*", str(query or ""), flags=re.UNICODE)
            if term.upper() not in {"AND", "OR", "NOT"}
        ]
        if not terms:
            return "NO RESULTS"
        params = {
            "search_query": " AND ".join(f"all:{term}" for term in terms),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": _clamp(max_results, 1, 30),
            "start": 0,
        }

        def call():
            _wait_for_arxiv_slot()
            return _request_once("GET", ARXIV_URL, params=params, timeout=45.0)

        response = with_retry(call, attempts=7, base=2.0, cap=60.0)
        root = ET.fromstring(response.content)
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        records = []
        for entry in root.findall("atom:entry", namespace):
            raw_id = _clean_text(entry.findtext("atom:id", default="", namespaces=namespace))
            paper_id = raw_id.rsplit("/abs/", 1)[-1].rstrip("/")
            paper_id = re.sub(r"v\d+$", "", paper_id)
            if not paper_id:
                continue
            published = _clean_text(entry.findtext("atom:published", default="", namespaces=namespace))[:10]
            records.append({
                "id": paper_id,
                "url": f"https://arxiv.org/abs/{paper_id}",
                "published": published,
                "title": _clean_text(entry.findtext("atom:title", default="", namespaces=namespace)),
                "summary": _clean_text(
                    entry.findtext("atom:summary", default="", namespaces=namespace), limit=600
                ),
            })
        return json.dumps(records, ensure_ascii=False) if records else "NO RESULTS"
    except Exception as exc:  # tools return errors to the agent; they never crash the run
        return _tool_error(exc)


# ---- TODO 3: Hugging Face ----
@tool
def hf_daily_papers(limit: int = 30, date: str = "", keyword: str = "") -> str:
    """Hugging Face Daily Papers = what is trending in AI research. Returns a JSON list of
    {id, url, published, title, summary, upvotes, github, stars} sorted by upvotes. `date` is YYYY-MM-DD (empty = latest).
    `keyword` filters title/summary; there is no topic search on this endpoint (use hf_search_papers for a topic)."""
    # PSEUDO-CODE:
    #   GET HF_DAILY_URL params: limit (clamp 1..100) and date (only when given)      (with_retry)
    #   response = list of items {"paper": {id, title, summary, upvotes, githubRepo, githubStars, publishedAt}, ...}
    #   map every item to the record shape above (skip items without paper.id); url = https://huggingface.co/papers/<id>
    #   keyword -> keep records whose title+summary contains it (case-insensitive); sort by upvotes descending
    try:
        params = {"limit": _clamp(limit, 1, 100)}
        if str(date or "").strip():
            params["date"] = str(date).strip()
        response = with_retry(
            lambda: _request_once("GET", HF_DAILY_URL, params=params, timeout=45.0),
            attempts=5,
            base=1.0,
            cap=30.0,
        )
        records = _hf_records(response.json(), prefer_ai_summary=False)
        needle = _clean_text(keyword).casefold()
        if needle:
            records = [
                record for record in records
                if needle in f"{record['title']} {record['summary']}".casefold()
            ]
        records.sort(key=lambda record: _numeric(record.get("upvotes")), reverse=True)
        return json.dumps(records, ensure_ascii=False) if records else "NO RESULTS"
    except Exception as exc:
        return _tool_error(exc)


@tool
def hf_search_papers(query: str, limit: int = 10) -> str:
    """Search Hugging Face papers by topic. Returns a JSON list of
    {id, url, published, title, summary, upvotes, github, stars}."""
    # PSEUDO-CODE:
    #   GET HF_SEARCH_URL params: q=query, limit (clamp 1..50)                         (with_retry)
    #   same item shape as the daily endpoint; prefer paper["ai_summary"] over paper["summary"] when present
    try:
        if not _clean_text(query):
            return "NO RESULTS"
        response = with_retry(
            lambda: _request_once(
                "GET",
                HF_SEARCH_URL,
                params={"q": str(query), "limit": _clamp(limit, 1, 50)},
                timeout=45.0,
            ),
            attempts=5,
            base=1.0,
            cap=30.0,
        )
        records = _hf_records(response.json(), prefer_ai_summary=True)
        return json.dumps(records, ensure_ascii=False) if records else "NO RESULTS"
    except Exception as exc:
        return _tool_error(exc)


def _numeric(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _hf_records(payload, *, prefer_ai_summary):
    if not isinstance(payload, list):
        raise ValueError("Hugging Face response is not a list")
    records = []
    for item in payload:
        if not isinstance(item, dict) or not isinstance(item.get("paper"), dict):
            continue
        paper = item["paper"]

        def pick(*names, default=None):
            for name in names:
                value = paper.get(name)
                if value is None or value == "":
                    value = item.get(name)
                if value is not None and value != "":
                    return value
            return default

        paper_id = _clean_text(pick("id", default=""))
        if not paper_id:
            continue
        summary_names = ("ai_summary", "summary") if prefer_ai_summary else ("summary",)
        published = _clean_text(pick("publishedAt", "published", default=""))[:10]
        records.append({
            "id": paper_id,
            "url": f"https://huggingface.co/papers/{paper_id}",
            "published": published,
            "title": _clean_text(pick("title", default="")),
            "summary": _clean_text(pick(*summary_names, default=""), limit=600),
            "upvotes": pick("upvotes", default=0),
            "github": pick("githubRepo", "github", default=""),
            "stars": pick("githubStars", "stars", default=0),
        })
    return records


# ---- TODO 4: web search / fetch through the Exa MCP endpoint ----
@tool
def web_search(query: str, objective: str = "", num_results: int = 5) -> str:
    """Search the web (Exa). Describe the ideal page in natural language. Returns clean text of the top results with URLs."""
    # PSEUDO-CODE:
    #   call the MCP tool "web_search_exa" with arguments {query, objective, numResults}
    #       (objective is REQUIRED by Exa: when empty, build one from the query)
    #   see GUIDE.md part 1.4 for how to call an MCP server over plain HTTP (JSON-RPC "tools/call") and read the answer
    #   read optional env EXA_API_KEY; when present it is sent to the Exa endpoint.
    #       (see GUIDE.md 1.4 for where it goes) => the key then appears in exception text: redact it before returning "ERROR: ..."
    #   WATCH OUT: read GUIDE.md 1.4 about how Exa signals "rate limited" on the free tier, and retry on it
    api_key = (os.getenv("EXA_API_KEY") or "").strip()
    try:
        query = _clean_text(query)
        if not query:
            return "NO RESULTS"
        objective = _clean_text(objective) or f"Find reliable and directly relevant sources about: {query}"
        text = _exa_call(
            "web_search_exa",
            {"query": query, "objective": objective, "numResults": _clamp(num_results, 1, 10)},
            api_key,
        )
        return text if text.strip() else "NO RESULTS"
    except Exception as exc:
        return _tool_error(exc, api_key)


@tool
def web_fetch(url: str) -> str:
    """Read the full content of one web page (e.g. an arXiv abstract page) as markdown. Long pages are truncated."""
    # PSEUDO-CODE: MCP tool "web_fetch_exa" with arguments {"urls": [url]}; truncate the text to ~12000 chars
    api_key = (os.getenv("EXA_API_KEY") or "").strip()
    try:
        url = str(url or "").strip()
        if not re.match(r"^https?://", url):
            return "NO RESULTS"
        text = _exa_call("web_fetch_exa", {"urls": [url]}, api_key)
        text = text.strip()
        return text[:12_000] if text else "NO RESULTS"
    except Exception as exc:
        return _tool_error(exc, api_key)


def _json_rpc_payload(response_text):
    """Decode either Exa's SSE response or a plain JSON response."""
    payloads = []
    for line in response_text.splitlines():
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        payloads.append(json.loads(data))
    if not payloads:
        payloads.append(json.loads(response_text))
    for payload in reversed(payloads):
        if isinstance(payload, dict) and ("result" in payload or "error" in payload):
            return payload
    raise ValueError("Exa response contained no JSON-RPC result")


def _contains_rate_limit(value):
    """Recognize explicit rate-limit flags/messages in JSON-RPC metadata."""
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z]", "", str(key).lower())
            if normalized in {"ratelimited", "isratelimited", "limitreached", "exaratelimited"}:
                if child is True or (isinstance(child, str) and child.lower() not in {"", "false", "no", "0"}):
                    return True
            if normalized in {"status", "statuscode", "code"} and str(child) == "429":
                return True
            if normalized in {"error", "message", "reason"} and _rate_limit_message(str(child)):
                return True
            if _contains_rate_limit(child):
                return True
    elif isinstance(value, list):
        return any(_contains_rate_limit(item) for item in value)
    return False


def _rate_limit_message(text):
    return bool(re.search(r"rate[ -]?limit(?:ed|ing)?|too many requests|quota (?:has been )?exceeded", text, re.I))


def _find_retry_after(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if re.sub(r"[^a-z]", "", str(key).lower()) in {"retryafter", "retryafterseconds"}:
                try:
                    return float(child)
                except (TypeError, ValueError):
                    pass
            found = _find_retry_after(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_retry_after(child)
            if found is not None:
                return found
    return None


def _exa_call(tool_name, arguments, api_key):
    endpoint_params = {"exaApiKey": api_key} if api_key else None
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }

    def call():
        response = _request_once(
            "POST",
            EXA_URL,
            params=endpoint_params,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            json=request,
            timeout=60.0,
        )
        payload = _json_rpc_payload(response.text)
        if "error" in payload:
            error = payload["error"]
            if _contains_rate_limit(error) or _rate_limit_message(json.dumps(error, ensure_ascii=False)):
                raise RetryableError("Exa rate limited the request", _find_retry_after(error))
            raise RuntimeError(f"Exa JSON-RPC error: {error}")
        result = payload.get("result") or {}
        meta = result.get("_meta") or {}
        content = result.get("content") or []
        text = "\n".join(
            str(part.get("text", "")) for part in content
            if isinstance(part, dict) and part.get("type") == "text" and part.get("text")
        ).strip()
        # Exa's free endpoint can report rate limiting with HTTP 200. Prefer the
        # metadata flag, with a conservative fallback for its short error notice.
        short_notice = len(text) < 2_000 and _rate_limit_message(text) and re.search(
            r"retry|api key|exa|request", text, re.I
        )
        if _contains_rate_limit(meta) or short_notice:
            raise RetryableError("Exa rate limited the request", _find_retry_after(meta))
        return text

    return with_retry(call, attempts=7, base=2.0, cap=60.0)


# ---- TODO 5: registry (the researcher subagent gets exactly these) ----
SOURCE_TOOLS = [arxiv_search, hf_daily_papers, hf_search_papers, web_search, web_fetch]


if __name__ == "__main__":
    for name, fn, args in [
        ("arxiv_search", arxiv_search, {"query": "world model", "max_results": 3}),
        ("hf_daily_papers", hf_daily_papers, {"limit": 20}),
        ("hf_search_papers", hf_search_papers, {"query": "world model", "limit": 3}),
        ("web_search", web_search, {"query": "survey paper on world models", "num_results": 2}),
        ("web_fetch", web_fetch, {"url": "https://arxiv.org/abs/1803.10122"}),
    ]:
        try:
            print(f"== {name}\n{fn.invoke(args)[:400]}\n")
        except Exception as exc:  # defensive: public tools normally return an ERROR string instead
            print(f"== {name}: unexpected failure ({type(exc).__name__}: {exc})\n")
