from __future__ import annotations

from typing import Any, Callable, Optional


def read_ui_hierarchy(
    driver: Any,
    *,
    log: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Return Appium page source (Android UI XML or iOS XCTest XML).

    If the session is focused on a WebView/Chrome context, the source is usually HTML
    (often nearly empty), not the native widget tree. For Settings and most native
    flows, switch to NATIVE_APP first so find_element / get_page_source see real locators.
    """
    try:
        contexts = driver.contexts
        current = driver.current_context
    except Exception as e:
        if log:
            log(f"[page_source_helper] Could not read contexts: {e}")
        contexts, current = [], None

    try:
        if contexts and "NATIVE_APP" in contexts and current != "NATIVE_APP":
            if log:
                log(
                    f"[page_source_helper] context {current!r} -> NATIVE_APP "
                    f"({len(contexts)} context(s))"
                )
            driver.switch_to.context("NATIVE_APP")
    except Exception as e:
        if log:
            log(f"[page_source_helper] Native context switch failed (non-fatal): {e}")

    src = driver.page_source
    if not (src or "").strip() and log:
        log("[page_source_helper] page_source is empty after read; check session health.")
    return src if isinstance(src, str) else ""
