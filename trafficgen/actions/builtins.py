"""Built-in actions. Selenium pieces are imported lazily inside ``run`` so this
module (and therefore config parsing) stays importable without a browser."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass

from ..browser_helpers import auto_scroll
from ..urlmatch import same_domain
from .base import Action, ActionContext
from .registry import register_action


@dataclass
class ScrollAction(Action):
    type = "scroll"
    dwell: int = 8
    passes: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "ScrollAction":
        return cls(dwell=int(d.get("dwell", d.get("dwell_seconds", 8))),
                   passes=int(d.get("passes", 0)))

    def run(self, ctx: ActionContext) -> None:
        auto_scroll(
            ctx.driver,
            max(1, self.dwell) if self.passes == 0 else self.dwell,
            passes=self.passes,
            report_progress=ctx.report_progress,
            should_stop=ctx.should_stop,
        )


@dataclass
class WaitAction(Action):
    type = "wait"
    seconds: int = 5
    jitter: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "WaitAction":
        return cls(seconds=int(d.get("seconds", d.get("dwell", 5))),
                   jitter=int(d.get("jitter", 0)))

    def run(self, ctx: ActionContext) -> None:
        extra = random.randint(0, self.jitter) if self.jitter > 0 else 0
        total = max(0, self.seconds + extra)
        ctx.report_progress(0.0, "waiting")
        end = time.time() + total
        while time.time() < end:
            if ctx.should_stop():
                return
            time.sleep(min(0.5, max(0.0, end - time.time())))


@dataclass
class ClickRandomLinkAction(Action):
    type = "click_random_link"
    same_origin: bool = True
    dwell: int = 5

    @classmethod
    def from_dict(cls, d: dict) -> "ClickRandomLinkAction":
        return cls(same_origin=bool(d.get("same_origin", True)),
                   dwell=int(d.get("dwell", 5)))

    def run(self, ctx: ActionContext) -> None:
        from selenium.webdriver.common.by import By

        ctx.report_progress(None, "picking link")
        current = ctx.driver.current_url
        try:
            anchors = ctx.driver.find_elements(By.TAG_NAME, "a")
        except Exception:
            return
        candidates = []
        for a in anchors:
            try:
                href = a.get_attribute("href") or ""
            except Exception:
                continue
            if not href.startswith("http"):
                continue
            if self.same_origin and not same_domain(href, current):
                continue
            candidates.append(a)
        if not candidates:
            ctx.log("click_random_link: no eligible links")
            return
        choice = random.choice(candidates)
        try:
            ctx.report_progress(None, "clicking link")
            choice.click()
        except Exception as e:
            ctx.log(f"click_random_link: click failed ({e.__class__.__name__})")
            return
        end = time.time() + max(1, self.dwell)
        while time.time() < end and not ctx.should_stop():
            time.sleep(0.5)


@dataclass
class RandomWalkAction(Action):
    type = "random_walk"
    hops: int = 3
    dwell_per_hop: int = 5
    same_domain_only: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "RandomWalkAction":
        return cls(hops=int(d.get("hops", 3)),
                   dwell_per_hop=int(d.get("dwell_per_hop", d.get("dwell", 5))),
                   same_domain_only=bool(d.get("same_domain", True)))

    def run(self, ctx: ActionContext) -> None:
        from selenium.webdriver.common.by import By

        for hop in range(self.hops):
            if ctx.should_stop():
                return
            ctx.report_progress((hop / self.hops) if self.hops else None,
                                f"random walk {hop + 1}/{self.hops}")
            current = ctx.driver.current_url
            try:
                anchors = ctx.driver.find_elements(By.TAG_NAME, "a")
            except Exception:
                return
            candidates = []
            for a in anchors:
                try:
                    href = a.get_attribute("href") or ""
                except Exception:
                    continue
                if not href.startswith("http"):
                    continue
                if self.same_domain_only and not same_domain(href, current):
                    continue
                candidates.append(href)
            if not candidates:
                ctx.log("random_walk: dead end, stopping")
                return
            target = random.choice(candidates)
            try:
                ctx.driver.get(target)
            except Exception as e:
                ctx.log(f"random_walk: navigation failed ({e.__class__.__name__})")
                return
            end = time.time() + max(1, self.dwell_per_hop)
            while time.time() < end and not ctx.should_stop():
                time.sleep(0.5)


@dataclass
class SearchAction(Action):
    type = "search"
    selector: str = "input[type=search], input[name=q]"
    query: str = ""
    submit: bool = True
    dwell: int = 5

    @classmethod
    def from_dict(cls, d: dict) -> "SearchAction":
        return cls(selector=str(d.get("selector", "input[type=search], input[name=q]")),
                   query=str(d.get("query", "")),
                   submit=bool(d.get("submit", True)),
                   dwell=int(d.get("dwell", 5)))

    def run(self, ctx: ActionContext) -> None:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        ctx.report_progress(None, "searching")
        try:
            box = ctx.driver.find_element(By.CSS_SELECTOR, self.selector)
        except Exception:
            ctx.log(f"search: input not found ({self.selector!r})")
            return
        try:
            box.clear()
            box.send_keys(self.query)
            if self.submit:
                box.send_keys(Keys.RETURN)
        except Exception as e:
            ctx.log(f"search: typing failed ({e.__class__.__name__})")
            return
        end = time.time() + max(1, self.dwell)
        while time.time() < end and not ctx.should_stop():
            time.sleep(0.5)


def _register_all() -> None:
    register_action(ScrollAction.type, ScrollAction.from_dict)
    register_action(WaitAction.type, WaitAction.from_dict)
    register_action(ClickRandomLinkAction.type, ClickRandomLinkAction.from_dict)
    register_action(RandomWalkAction.type, RandomWalkAction.from_dict)
    register_action(SearchAction.type, SearchAction.from_dict)


_register_all()
