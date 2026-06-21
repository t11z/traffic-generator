"""Default handler: run configured actions, else legacy scroll/dwell behaviour."""
from __future__ import annotations

import time

from ..actions import ActionContext
from ..browser_helpers import auto_scroll
from .base import HandlerContext


def default_handler(ctx: HandlerContext) -> None:
    target = ctx.target
    actions = getattr(target, "actions", None)

    if actions:
        act_ctx = ActionContext(
            driver=ctx.driver,
            target=target,
            log=ctx.log,
            report_progress=ctx.report_progress,
            stop_event=ctx.stop_event,
        )
        for action in actions:
            if ctx.should_stop():
                return
            ctx.report_progress(None, getattr(action, "type", "action"))
            action.run(act_ctx)
        return

    # Legacy behaviour: auto-scroll for dwell, or just sleep.
    dwell = max(1, int(getattr(target, "dwell_seconds", 8)))
    if getattr(target, "scroll", True):
        auto_scroll(ctx.driver, dwell, report_progress=ctx.report_progress,
                    should_stop=ctx.should_stop)
    else:
        end = time.time() + dwell
        while time.time() < end and not ctx.should_stop():
            ctx.report_progress(None, "dwell")
            time.sleep(min(0.5, max(0.0, end - time.time())))
