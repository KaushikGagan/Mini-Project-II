"""Narrow internal client for the local Fabric Gateway service."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from flask import current_app

class FabricUnavailable(RuntimeError): pass
class FabricGatewayError(RuntimeError): pass

def _request(method: str, path: str, payload: dict | None = None) -> dict:
    headers = {"Accept": "application/json"}
    if current_app.config.get("FABRIC_GATEWAY_TOKEN"):
        headers["X-Gateway-Token"] = current_app.config["FABRIC_GATEWAY_TOKEN"]
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    req = Request(f"{current_app.config['FABRIC_GATEWAY_URL']}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=current_app.config["FABRIC_GATEWAY_TIMEOUT_SECONDS"]) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try: message = json.loads(error.read().decode("utf-8")).get("error", "Fabric gateway rejected the request.")
        except (ValueError, UnicodeDecodeError): message = "Fabric gateway rejected the request."
        if error.code >= 500: raise FabricUnavailable(message) from error
        raise FabricGatewayError(message) from error
    except (URLError, TimeoutError, OSError) as error:
        raise FabricUnavailable("Fabric gateway is unavailable.") from error

def register_certificate(certificate, administrator):
    return _request("POST", "/v1/certificates/register", {"documentId": certificate.document_id, "sha256Hash": certificate.sha256_hash, "certificateType": certificate.application.certificate_type, "issuer": administrator.employee_id, "issuedAt": certificate.issued_date.isoformat()})
def get_certificate(document_id: str) -> dict:
    return _request("GET", f"/v1/certificates/{quote(document_id, safe='')}")
def verify_certificate(document_id: str, sha256_hash: str) -> dict:
    return _request("POST", f"/v1/certificates/{quote(document_id, safe='')}/verify", {"sha256Hash": sha256_hash})
def update_certificate_status(document_id: str, status: str) -> dict:
    return _request("POST", f"/v1/certificates/{quote(document_id, safe='')}/status", {"status": status})
