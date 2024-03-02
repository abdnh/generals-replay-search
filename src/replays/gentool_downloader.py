"""
Example:
scrapy runspider src/replays/gentool_downloader.py -a subpath=zh/2024_02_February/29_Thursday/
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import scrapy
import scrapy.http

WINDOWS_DISALLOWED_CHARS_RE = re.compile(r'[<>:"/\\|?*]')


def strip_invalid_chars(filename: str) -> str:
    return WINDOWS_DISALLOWED_CHARS_RE.sub("", filename)


class GentoolSpider(scrapy.Spider):
    name = "gentool"

    def __init__(
        self,
        name: str | None = None,
        subpath: str = "",
        outdir: str = "data",
        **kwargs: Any,
    ):
        super().__init__(name, **kwargs)
        self.start_urls = [f"https://www.gentool.net/data/{subpath}"]
        path_parts = [p for p in subpath.split("/") if p]
        self.outdir = Path(outdir).joinpath(*path_parts)

    def parse(
        self,
        response: scrapy.http.Response,
        outdir: Path | None = None,
    ):
        if outdir is None:
            outdir = self.outdir
        outdir.mkdir(exist_ok=True, parents=True)
        if not isinstance(response, scrapy.http.HtmlResponse):
            file_path = outdir / str(response.url.split("/")[-1])
            file_path.write_bytes(response.body)
            return
        rows = response.css("tr")[3:-1]
        for row in rows:
            link = next(iter(row.css("a")), None)
            if not link:
                continue
            sub_url = response.urljoin(link.attrib["href"])
            name = link.css("*::text").get()
            if sub_url.endswith("/"):
                subpath = outdir / strip_invalid_chars(name)
            else:
                subpath = outdir
                if not any(sub_url.endswith(s) for s in (".rep", ".txt")):
                    continue
                file_path = subpath / str(sub_url.split("/")[-1])
                if file_path.exists():
                    continue
            yield response.follow(
                sub_url,
                self.parse,
                cb_kwargs={"outdir": subpath},
            )

    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)
        settings.set("CONCURRENT_REQUESTS", 100, priority="spider")
        settings.set("REACTOR_THREADPOOL_MAXSIZE", 20, priority="spider")
        settings.set("COOKIES_ENABLED", False, priority="spider")
