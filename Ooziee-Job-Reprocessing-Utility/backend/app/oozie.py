import requests
from typing import Any, Dict, Optional
from xml.sax.saxutils import escape

from .settings import settings


class OozieClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.timeout = settings.oozie_http_timeout
        self.session = requests.Session()

    def job_info(self, job_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/v2/job/{job_id}"
        r = self.session.get(url, params={"show": "info"}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def rerun(self, job_id: str, conf: Optional[Dict[str, str]] = None, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        if params and "action" in params:
            raise ValueError("params cannot contain reserved key 'action'")

        url = f"{self.base_url}/v2/job/{job_id}"
        q = {"action": "rerun"}
        if params:
            q.update(params)
        headers = {"Content-Type": "application/xml"}
        body = ""
        if conf:
            props = "".join(
                [
                    f"<property><name>{escape(str(k))}</name><value>{escape(str(v))}</value></property>"
                    for k, v in conf.items()
                ]
            )
            body = f"<configuration>{props}</configuration>"
        r = self.session.put(url, params=q, data=body.encode("utf-8"), headers=headers, timeout=self.timeout)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {"status": "submitted"}
