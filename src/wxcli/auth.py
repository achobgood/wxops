from __future__ import annotations

import os
import random
import time
import logging
from pathlib import Path

import typer

from wxcli.config import DEFAULT_CONFIG_PATH, get_token
from wxcli.errors import WebexError

# httpx itself (not just this module) is imported lazily, inside the methods
# that actually make a request — `import wxcli.auth` is on main.py's eager
# import path (whoami/switch-org reference get_api/resolve_token/WebexApi/
# WebexSession as module globals so tests can `mock.patch("wxcli.main.X")`),
# so keeping httpx off THIS module's own top level is what keeps it off
# `wxcli --version`/`--help`. `from __future__ import annotations` defers
# the httpx.Response type hints below to strings so they don't need the
# real import at class-definition time either.

logger = logging.getLogger("wxcli")


def _items_of(data, item_key: str) -> list:
    """The record list out of a paged response, whatever wrapper it arrived in.

    Mirrors the extraction the generated commands already do: the declared key,
    then CC's `data`, then a bare top-level array. `resources` is the CC
    bulk-export wrapper (`{totalResources, pageNumber, pageSize, resources}`);
    without it a caller asking for "items" counted 0 records on a page of 6 and
    the truncation note fired on a complete response (`cc-global-vars list`).
    """
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in (item_key, "data", "items", "Resources", "resources"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def _max_pages() -> int:
    try:
        return max(1, int(os.environ.get("WXCLI_MAX_PAGES", DEFAULT_MAX_PAGES)))
    except ValueError:
        return DEFAULT_MAX_PAGES


def _page_cap_reached(pages: int, walker: str) -> bool:
    """Loudly. A silent stop here would hand back a partial answer with no
    error — the exact defect --all was built to remove."""
    if pages < _max_pages():
        return False
    typer.echo(
        f"Error: {walker} stopped after {pages} pages without the server "
        "signalling the end — the results are INCOMPLETE. This usually means "
        "the endpoint ignores its own paging parameter. Narrow the query, or "
        "raise the ceiling with WXCLI_MAX_PAGES=<n>.",
        err=True,
    )
    return True


def _page_fingerprint(items: list) -> str | None:
    """A stable digest of one page's records, or None for an empty page."""
    if not items:
        return None
    import hashlib
    import json
    raw = json.dumps(items, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def _repeated_page(items: list, previous: str | None, position: int, walker: str) -> bool:
    """True — and says so on stderr — when a page repeats the one before it.

    A server that ignores the walker's page parameter answers every request
    with the same full page. The short-page stop never fires on that, so the
    walk used to run to the 1000-page cap, yielding the same records 1000
    times. Stop at the first repeat instead, before yielding it: the records
    already yielded are each unique, and the run is flagged INCOMPLETE.
    """
    if previous is None or _page_fingerprint(items) != previous:
        return False
    typer.echo(
        f"Error: {walker} stopped at page {position}: the server returned exactly "
        "the records of the previous page, so it is ignoring the paging "
        "parameter — the results are INCOMPLETE (only the first page is "
        "real). Fetch without --all and narrow the query instead.",
        err=True,
    )
    return True


# How many records `--offset N` returns on a page-numbered endpoint when neither
# `--limit` nor the endpoint's own page-size flag says. 100 is the declared
# default of 94 of the 113 page-size parameters in the Contact Center spec.
DEFAULT_OFFSET_WINDOW = 100


def _body_says_more(body) -> bool:
    """True when a paged body reports more records than it just returned.

    Contact Center and SCIM send NO `Link` header, so a header-only check is
    blind to 101 of the 210 single-fetch list commands — exactly the ones `--all`
    exists for. Their wrappers do carry a total, under three spellings verified
    against the specs: `totalResources` (CC bulk-export), `totalRecords`/`meta`
    (CC v2/v3) and `totalResults` (SCIM).

    Compares against a total rather than guessing from a full-looking page: a
    page that happens to be exactly full is not evidence, and warning on it
    would fire on every complete small response.
    """
    if not isinstance(body, dict):
        return False
    # A page-numbered body that states its page and page count answers the
    # question exactly. Comparing the collection total with THIS page's count
    # fired on every page after the first, the last one included (`cc-flow list
    # --page 5`: 6 of 56 returned, nothing left, note printed anyway).
    paged = _page_meta(body)
    if paged is not None and paged[1] is not None:
        return paged[0] + 1 < paged[1]
    # CC bulk-export (`{totalResources, pageNumber, pageSize, rel, resources}`)
    # says it outright: `rel` is "next" while pages remain and "last" on the
    # final one. Its `pageNumber` is NOT the page served — live 2026-10-13,
    # cad-variable/bulk-export at pageSize 4 of 9: page=0 -> pageNumber 1,
    # page=1 -> 2, page=2 -> 2 ("last"), no page -> 0 — so it is never read.
    # Comparing the total with this page's count fired on the last page too.
    rel = body.get("rel")
    if rel in ("next", "last") and "totalResources" in body:
        return rel == "next"
    returned = len(_items_of(body, "items"))
    for key in ("totalResources", "totalRecords", "totalResults", "total"):
        total = body.get(key)
        if isinstance(total, bool):
            continue
        if isinstance(total, int) and total > returned:
            return True
    # `pageInfo` is the Flows spelling (cc-flow list with includePagination,
    # cc-flow list-search): {"currentPage", "totalRecords", "pageSize",
    # "totalPages"}. Without it a 10-of-56 first page was silent.
    for wrapper in ("meta", "pageInfo"):
        meta = body.get(wrapper)
        if isinstance(meta, dict):
            for key in ("totalRecords", "totalResources", "total"):
                total = meta.get(key)
                if isinstance(total, int) and not isinstance(total, bool) and total > returned:
                    return True
    return False


def _declared_total(body) -> int | None:
    """The collection total a paged body declares, or None.

    Same spellings `_body_says_more` reads, top-level first, then under the
    `meta` / `pageInfo` wrappers.
    """
    if not isinstance(body, dict):
        return None
    scopes = [body] + [body[w] for w in ("meta", "pageInfo") if isinstance(body.get(w), dict)]
    for scope in scopes:
        for key in ("totalRecords", "totalResources", "totalResults", "total"):
            total = scope.get(key)
            if isinstance(total, int) and not isinstance(total, bool):
                return total
    return None


def _next_page_url(response: "httpx.Response") -> str | None:
    """The `Link: rel="next"` target, or None. Same parse as follow_pagination."""
    for part in response.headers.get("Link", "").split(","):
        part = part.strip()
        if 'rel="next"' in part:
            return part.split(";")[0].strip().strip("<>")
    return None


def _warn_if_more_pages(response: "httpx.Response", params=None) -> None:
    """Say so on stderr when a single fetch left pages on the server.

    211 list commands issue one `rest_get` against an endpoint that pages, and
    used to discard the evidence silently — the command exits 0 and hands back
    a partial answer with nothing indicating it. The display
    layer cannot cover this: `output.print_table`'s "... N more" row needs
    `len(data) > limit`, and on 502 of 503 list commands `--limit` is ALSO the
    API page size, so the row is unreachable exactly where truncation happens.

    This does not change what any command returns — stdout is untouched. It
    only makes the silent case loud, and tells us which commands truncate in
    practice: the count of 211 is a code shape, and the one live probe on
    record found 105 records returned whole from an endpoint whose spec
    declares a default page of 10.

    Two signals, because neither alone is enough. `Link: rel="next"` covers the
    110 link-shaped commands. Contact Center (`page`/`pageSize`) and SCIM
    (`startIndex`/`count`) send NO Link header, so `_body_says_more` reads a
    declared total out of the body instead — that is the other 101. (Corrected
    2026-07-29: this said the CC style was NOT covered. True at 600eb38, fixed
    in 1f584d1; the condition below reads both.)

    Still blind: an endpoint that pages while sending neither a Link header nor
    any total spelling `_body_says_more` knows. `follow_page_param` terminates
    on a short page precisely because some CC wrappers carry no total at all,
    and on those this cannot tell a full page from a final one.
    """
    if os.environ.get("WXCLI_NO_PAGE_WARN"):
        return
    try:
        body = response.json() if response.content else {}
    except Exception:
        return
    if not (_next_page_url(response) or _body_says_more(body)):
        return
    count = len(_items_of(body, "items")) if isinstance(body, (dict, list)) else 0

    # The remedy must be `--offset`, NOT `--limit 0`. On the 210 commands this
    # fires for, `--limit 0` is already the default and does not fetch more —
    # naming it would print a next step that cannot work. `--offset` is the one
    # remedy that exists on EVERY list command: on `max`/`start` endpoints it is
    # `start`, and on page-numbered (Contact Center) endpoints the generated
    # command translates it to `page`/`pageSize` (`fetch_from_offset`). `--page`
    # is NOT named: `cc-tasks list` pages by `page` but its spec declares only
    # `pageSize`, so it has no `--page` flag — the note used to name one.
    shown = f"{count} records returned" if count else "This response was partial"
    nxt = " Re-run with --all to fetch every page"
    offset = _next_offset(response, body, params, count)
    nxt += f", or --offset {offset} for just the next one." if offset else "."
    typer.echo(f"Note: {shown} and the server has more pages.{nxt}", err=True)


def _more_pages_note(count: int, next_offset: int) -> None:
    """The truncation note, for callers that fetched without rest_get."""
    if os.environ.get("WXCLI_NO_PAGE_WARN"):
        return
    typer.echo(
        f"Note: {count} records returned and the server has more pages. Re-run "
        f"with --all to fetch every page, or --offset {next_offset} for just "
        "the next one.",
        err=True,
    )


def _page_meta(body) -> tuple[int, int | None] | None:
    """(current page, total pages or None) from a page-numbered body, else None.

    `pageInfo.currentPage`/`totalPages` on Flows, `meta.page`/`totalPages` on
    the CC v2 config lists.
    """
    if not isinstance(body, dict):
        return None
    for wrapper, key in (("pageInfo", "currentPage"), ("meta", "page")):
        meta = body.get(wrapper)
        if not isinstance(meta, dict):
            continue
        current = meta.get(key)
        if isinstance(current, int) and not isinstance(current, bool):
            pages = meta.get("totalPages")
            ok = isinstance(pages, int) and not isinstance(pages, bool)
            return current, (pages if ok else None)
    return None


def _int_or_none(value) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _page_position(body) -> tuple[int, int | None] | None:
    """(page number, page size or None) a page-numbered body states, else None.

    `pageInfo.currentPage`/`pageSize` (Flows), `meta.page`/`pageSize` (CC v2
    config lists). NOT the bulk-export top-level `pageNumber`, which does not
    track the page served (see `_body_says_more`); those fall back to the
    request's own `page`.
    """
    if not isinstance(body, dict):
        return None
    scopes = [(body.get("pageInfo"), "currentPage"), (body.get("meta"), "page")]
    for scope, key in scopes:
        if not isinstance(scope, dict):
            continue
        current = _int_or_none(scope.get(key))
        if current is not None:
            return current, _int_or_none(scope.get("pageSize")) or None
    return None


_PAGE_SIZE_NAMES = ("pageSize", "size")


def _next_offset(response, body, params, count: int) -> int | None:
    """The absolute `--offset` that fetches the record after this page.

    Page-numbered endpoints: (page + 1) * page size, read from, in order, the
    `page`/`pageSize` of a `Link: rel="next"` URL (`/v1/tasks` sends one), the
    body's own page position, the request's `page`. The page size falls back to
    `count` — the note only fires when more remain, so this page was full.
    Everything else: the request's `start` + `count`, as before.
    """
    from urllib.parse import parse_qs, urlsplit
    params = params or {}
    nxt = _next_page_url(response)
    if nxt:
        query = parse_qs(urlsplit(nxt).query)
        page = _int_or_none((query.get("page") or [None])[0])
        if page is not None:
            size = next((_int_or_none(query[n][0]) for n in _PAGE_SIZE_NAMES
                         if n in query), None)
            return page * (size or count)
    position = _page_position(body)
    if position is None and params.get("page") is not None:
        req_size = next((_int_or_none(params.get(n)) for n in _PAGE_SIZE_NAMES
                         if params.get(n) is not None), None)
        position = (_int_or_none(params.get("page")) or 0, req_size)
    if position is not None:
        return (position[0] + 1) * (position[1] or count)
    start = _int_or_none(params.get("start")) or 0
    return start + count if count else None

# Bounded retry policy. WXCLI_RETRY_MODE=off (or legacy WXCLI_NO_RETRY=1) disables.
DEFAULT_MAX_ATTEMPTS = 4
MAX_RETRY_AFTER_SECONDS = 30
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})

# Backstop for the offset-walking pagers. They stop on a short page, so a server
# that ignores `page`/`startIndex` and keeps returning a full one never ends —
# the command then hangs until the caller's timeout kills it, which in this
# project's own agent harness means the subagent dies mid-tool-call with no
# output at all. Set far above any real collection: at the default page size
# that is 200,000 records. Override with WXCLI_MAX_PAGES.
DEFAULT_MAX_PAGES = 1000


def _retry_enabled() -> bool:
    if os.environ.get("WXCLI_NO_RETRY"):
        return False
    return os.environ.get("WXCLI_RETRY_MODE", "standard").lower() != "off"


def _max_attempts() -> int:
    try:
        return max(1, int(os.environ.get("WXCLI_MAX_ATTEMPTS", DEFAULT_MAX_ATTEMPTS)))
    except ValueError:
        return DEFAULT_MAX_ATTEMPTS


def _backoff_delay(attempt: int) -> float:
    """Exponential backoff with jitter: attempt 1 -> (0,1], 2 -> (1,2], 3 -> (2,4]."""
    base = 2 ** (attempt - 1)
    lower = base / 2 if attempt > 1 else 0.0
    return lower + random.random() * (base - lower)

# httpx defaults to 5s for connect AND read; Webex list and CDR endpoints
# routinely exceed that. Override per-call or via env.
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 60.0


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


class WebexSession:
    def __init__(self, token: str, connect_timeout: float | None = None,
                 read_timeout: float | None = None):
        import httpx  # deferred — see module docstring note above the imports

        self._token = token
        connect = connect_timeout if connect_timeout is not None else _env_float(
            "WXCLI_CONNECT_TIMEOUT", DEFAULT_CONNECT_TIMEOUT)
        read = read_timeout if read_timeout is not None else _env_float(
            "WXCLI_READ_TIMEOUT", DEFAULT_READ_TIMEOUT)
        self._timeout = httpx.Timeout(read, connect=connect)

    def _headers(self, content_type: str | None = None) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": content_type or "application/json",
        }

    def _request(self, method: str, url: str, json=None, params=None,
                 content_type: str | None = None) -> httpx.Response:
        """Single HTTP path for all verbs: bounded retry on RETRY_STATUSES
        (Retry-After honored on ALL of them, capped at 30s; jittered backoff
        otherwise) + one connect-error retry. WXCLI_RETRY_MODE=off / WXCLI_NO_RETRY=1 disable both."""
        import httpx  # deferred — see module docstring note above the imports

        enabled = _retry_enabled()
        attempts_left = _max_attempts() if enabled else 1
        connect_retries = 1 if enabled else 0
        attempt = 0
        while True:
            attempt += 1
            try:
                response = httpx.request(
                    method, url, headers=self._headers(content_type),
                    json=json, params=params, timeout=self._timeout,
                )
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                if connect_retries:
                    connect_retries -= 1
                    logger.warning("Connect error on %s %s (%s) — retrying once", method, url, e)
                    continue
                raise
            attempts_left -= 1
            if response.status_code in RETRY_STATUSES and attempts_left > 0:
                retry_after = response.headers.get("Retry-After")
                delay = None
                if retry_after:
                    try:
                        delay = min(int(retry_after), MAX_RETRY_AFTER_SECONDS)
                    except ValueError:
                        delay = None
                if delay is None:
                    delay = _backoff_delay(attempt)
                logger.warning("%s on %s %s — retrying in %.1fs",
                               response.status_code, method, url, delay)
                time.sleep(delay)
                continue
            return response

    def _json_or_raise(self, response: httpx.Response) -> dict:
        if not response.is_success:
            body = None
            try:
                body = response.json() if response.content else None
            except ValueError:
                pass
            raise WebexError(response.text, status_code=response.status_code, body=body)
        return response.json() if response.content else {}

    def rest_get(self, url: str, params=None) -> dict:
        response = self._request("GET", url, params=params)
        data = self._json_or_raise(response)
        _warn_if_more_pages(response, params)
        return data

    def rest_put(self, url: str, json=None, params=None) -> dict:
        return self._json_or_raise(self._request("PUT", url, json=json, params=params))

    def rest_post(self, url: str, json=None, params=None) -> dict:
        return self._json_or_raise(self._request("POST", url, json=json, params=params))

    def rest_patch(self, url: str, json=None, params=None, content_type: str | None = None) -> dict:
        return self._json_or_raise(self._request("PATCH", url, json=json, params=params,
                                                 content_type=content_type))

    def rest_delete(self, url: str, json=None, params=None) -> dict:
        # DELETE carries a body on 10 Webex operations: the body is what SCOPES
        # the delete (`supervisorIds`, `phoneNumbers`, `backgroundImages`...).
        # Without it the API rejects the call outright — verified live against
        # /telephony/config/supervisors: 400, errorCode 25024, "Required request
        # body is missing". It does NOT delete everything; those endpoints gate
        # delete-all behind an explicit `deleteAll: true`.
        return self._json_or_raise(self._request("DELETE", url, json=json, params=params))

    def follow_pagination(self, url: str, params=None, item_key: str = "items"):
        while url:
            response = self._request("GET", url, params=params)
            if not response.is_success:
                raise WebexError(response.text, status_code=response.status_code)
            data = response.json() if response.content else {}
            yield from (data.get(item_key, []) if isinstance(data, dict) else [])
            link = response.headers.get("Link", "")
            url = None
            for part in link.split(","):
                part = part.strip()
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip().strip("<>")
                    break
            params = None

    def follow_page_param(self, url: str, params=None, item_key: str = "data",
                          page_param: str = "page", size_param: str = "pageSize",
                          page_size: int = 200, first_page: int = 0):
        """Walk a `page`/`pageSize` collection — Contact Center's shape.

        CC sends no Link header, so follow_pagination cannot see these at all;
        that is 96 of the 210 single-fetch list commands. Termination is on a
        SHORT page rather than a declared total, because the CC wrappers vary
        (`meta`, `totalResources`/`pageNumber`, plain `data`) and a short page is
        the one signal all of them agree on. An exactly-full final page costs one
        extra request that returns empty — correct, just not free. A declared
        total, where the body carries one, can only EXTEND the walk past a short
        page (a server-capped page size), never cut it short.

        `size_param` must be the name the endpoint declares: the Flows endpoints
        take `size`, and a server ignores an unknown `pageSize`, answers with its
        default page, and the short-page stop then ends the walk after page 0.
        The generator passes it whenever the spec spells it differently.
        """
        params = dict(params or {})
        params[size_param] = params.get(size_param) or page_size
        size = int(params[size_param])
        page = int(params.get(page_param) or first_page)
        walked = 0
        seen = 0
        previous = None
        while True:
            params[page_param] = page
            data = self._json_or_raise(self._request("GET", url, params=params))
            items = _items_of(data, item_key)
            if _repeated_page(items, previous, page, "follow_page_param"):
                return
            previous = _page_fingerprint(items)
            yield from items
            seen += len(items)
            if not items:
                return
            if len(items) < size:
                # A short page normally ends the walk. But the CC specs say an
                # over-max size "will automatically adjust ... to the max page
                # size", so a server cap looks exactly like a last page. When
                # the body declares a total we have not reached, keep going;
                # the empty-page stop above still bounds a wrong total.
                total = _declared_total(data)
                if total is None or seen >= total:
                    return
            walked += 1
            if _page_cap_reached(walked, "follow_page_param"):
                return
            page += 1

    def fetch_from_offset(self, url: str, params=None, offset: int = 0, count: int = 0,
                          item_key: str = "data", page_param: str = "page",
                          size_param: str = "pageSize") -> list:
        """`--offset N` on a page-numbered endpoint: records [N, N + count).

        These endpoints ignore `start`, so `--offset` used to re-fetch page 0
        and exit 0 (verified live 2026-10-13 on `cc-flow list`, `cc-queue
        list`). The offset is record-exact whatever the page size: page
        N // size, skip N % size, and continue onto the next page when the
        window spans two. `count` is `--limit`, else the request's own page
        size, else DEFAULT_OFFSET_WINDOW; it is also the page size requested.

        A server that caps the page size below the one asked for would shift
        every page boundary, so a short page whose declared total says more
        records follow re-plans once with the size the server actually serves.
        Prints the same truncation note as rest_get when records remain.
        """
        params = dict(params or {})
        params.pop(page_param, None)
        want = int(count or params.get(size_param) or 0) or DEFAULT_OFFSET_WINDOW
        size = want
        for _ in range(2):
            page, skip = divmod(offset, size)
            params[size_param] = size
            params[page_param] = page
            body = self._json_or_raise(self._request("GET", url, params=params))
            items = _items_of(body, item_key)
            total = _declared_total(body)
            capped = (0 < len(items) < size and total is not None
                      and total > page * size + len(items))
            if not capped:
                break
            size = len(items)
        # One record past the window answers "are there more?" when no total does.
        need = want if total is not None else want + 1
        window = list(items[skip:skip + need])
        if len(window) < need and len(items) == size:
            for item in self.follow_page_param(
                    url, params={**params, page_param: page + 1}, item_key=item_key,
                    page_param=page_param, size_param=size_param, page_size=size):
                window.append(item)
                if len(window) >= need:
                    break
        more = (total > offset + min(len(window), want)) if total is not None \
            else len(window) > want
        window = window[:want]
        if more:
            _more_pages_note(len(window), offset + len(window))
        return window

    def follow_scim(self, url: str, params=None, item_key: str = "Resources",
                    count: int = 100):
        """Walk a SCIM `startIndex`/`count` collection. startIndex is 1-based.

        Terminates on `totalResults` when the server sends it and on a short page
        otherwise, so a server that omits the total still ends.
        """
        params = dict(params or {})
        params["count"] = params.get("count") or count
        size = int(params["count"])
        index = int(params.get("startIndex") or 1)
        walked = 0
        previous = None
        while True:
            params["startIndex"] = index
            data = self._json_or_raise(self._request("GET", url, params=params))
            items = _items_of(data, item_key)
            if _repeated_page(items, previous, index, "follow_scim"):
                return
            previous = _page_fingerprint(items)
            yield from items
            if len(items) < size:
                return
            index += len(items)
            total = data.get("totalResults") if isinstance(data, dict) else None
            if isinstance(total, int) and index > total:
                return
            walked += 1
            if _page_cap_reached(walked, "follow_scim"):
                return


class WebexApi:
    def __init__(self, session: WebexSession):
        self.session = session


def resolve_token(config_path: Path | None = DEFAULT_CONFIG_PATH) -> str | None:
    """Resolve token: WEBEX_ACCESS_TOKEN env → WEBEX_TOKEN env → config file."""
    token = os.environ.get("WEBEX_ACCESS_TOKEN")
    if token:
        return token
    token = os.environ.get("WEBEX_TOKEN")
    if token:
        return token
    if config_path:
        return get_token(config_path)
    return None


def get_api(debug: bool = False, connect_timeout: float | None = None,
            read_timeout: float | None = None) -> WebexApi:
    """Get a configured WebexApi instance, or exit with error."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    token = resolve_token()
    if not token:
        typer.echo("Error: No token found. Run 'wxcli configure' or set WEBEX_ACCESS_TOKEN.", err=True)
        raise typer.Exit(1)

    try:
        api = WebexApi(WebexSession(token, connect_timeout=connect_timeout,
                                    read_timeout=read_timeout))
    except Exception as e:
        typer.echo(f"Error: Failed to initialize API: {e}", err=True)
        raise typer.Exit(1)

    return api
