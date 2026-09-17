from urllib.parse import urljoin, urlsplit

from app.core.exceptions import BadRequestError

SUPPORTED_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def preview_openapi_document(document: dict) -> tuple[str, list[dict]]:
    if not str(document.get("openapi", "")).startswith("3."):
        raise BadRequestError("Only OpenAPI 3.x JSON documents are supported")
    servers = document.get("servers") or []
    base_url = servers[0].get("url") if servers and isinstance(servers[0], dict) else None
    parsed_base = urlsplit(base_url or "")
    if parsed_base.scheme not in {"http", "https"} or not parsed_base.netloc:
        raise BadRequestError("The OpenAPI document needs an absolute HTTP(S) server URL")

    operations: list[dict] = []
    for path, path_item in (document.get("paths") or {}).items():
        if not isinstance(path_item, dict) or "{" in path:
            continue
        for method, operation in path_item.items():
            if method.lower() not in SUPPORTED_METHODS or not isinstance(operation, dict):
                continue
            responses = operation.get("responses") or {}
            success_code = next((int(code) for code in responses if str(code).startswith("2") and str(code).isdigit()), None)
            if success_code is None:
                continue
            operation_id = operation.get("operationId") or f"{method}_{path.strip('/').replace('/', '_') or 'root'}"
            operations.append({
                "operation_id": operation_id,
                "name": operation.get("summary") or operation_id,
                "url": urljoin(base_url.rstrip("/") + "/", path.lstrip("/")),
                "method": method.upper(),
                "expected_status": success_code,
            })
    if not operations:
        raise BadRequestError("No importable operations with a 2xx response were found")
    return document.get("info", {}).get("title") or "Untitled API", operations
