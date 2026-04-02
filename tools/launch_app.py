import asyncio
from typing import Dict, Any, Optional


async def _adb_launch_android_package(udid: str, package: str, log) -> None:
    """
    When Appium activate_app fails (e.g. YouTube Shell$HomeActivity resolver bug),
    start the app's launcher task via explicit MAIN/LAUNCHER intent, then monkey.
    """
    async def _run(args: list) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out_b, err_b = await proc.communicate()
        return proc.returncode, out_b.decode(errors="replace"), err_b.decode(errors="replace")

    rc, out, err = await _run([
        "adb", "-s", udid, "shell", "am", "start",
        "-a", "android.intent.action.MAIN",
        "-c", "android.intent.category.LAUNCHER",
        "-p", package,
    ])
    combined = f"{out}\n{err}".strip()
    log(f"[launch_app] adb am start rc={rc} output={combined[:500]}")

    if rc != 0 or "error type" in combined.lower() or "unable to resolve intent" in combined.lower():
        rc2, out2, err2 = await _run([
            "adb", "-s", udid, "shell", "monkey", "-p", package,
            "-c", "android.intent.category.LAUNCHER", "1",
        ])
        combined2 = f"{out2}\n{err2}".strip()
        log(f"[launch_app] adb monkey rc={rc2} output={combined2[:500]}")
        if rc2 != 0 or "no activities found" in combined2.lower():
            raise RuntimeError(
                f"adb fallback failed for {package}. am start: {combined}; monkey: {combined2}"
            )


def launch_app_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the launch_app MCP tool.
    Works for both local Appium and cloud providers.
    """

    log = dependencies["log_to_file"]

    @mcp.tool()
    async def launch_app(bundleId: str = "com.android.settings") -> Dict[str, Any]:
        #using a sample bundleID just for testing purposes
        """
        Launch an app using bundleId/package name.
        """

        bundleId = (bundleId or "").strip()
        if not bundleId:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: bundleId/package name cannot be empty."
                }]
            }

        # CHECK SESSION
        if not shared_state.appium_driver:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Appium session not active. Please start a session first."
                }]
            }

        driver = shared_state.appium_driver
        platform = shared_state.current_platform

        # PLATFORM-AWARE VALIDATION
        if platform == "android" and bundleId.startswith("com.apple"):
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Provided bundleId looks like an iOS bundle. Android expects a package name (e.g. com.example.app)."
                }]
            }

        try:
            log(f"[launch_app] Launch request for: {bundleId}")

            # Detect cloud via shared_state (reliable), fallback to URL heuristic
            current_device = shared_state.current_device or {}
            is_cloud = current_device.get("type") == "cloud"

            if not is_cloud:
                executor_url = getattr(driver, "command_executor", None)
                if executor_url:
                    url = getattr(executor_url, "_url", "") or str(executor_url)
                    if any(x in url for x in ["browserstack", "saucelabs", "lambdatest"]):
                        is_cloud = True

            log(f"[launch_app] Cloud environment: {is_cloud}")

            app_state = None

            if not is_cloud:
                try:
                    app_state = driver.query_app_state(bundleId)
                    log(f"[launch_app] App state: {app_state}")
                except Exception as e:
                    log(f"[launch_app] query_app_state not supported: {str(e)}")

            # TERMINATE IF RUNNING
            if app_state and app_state > 1:
                try:
                    log(f"[launch_app] App running (state={app_state}), terminating...")

                    driver.terminate_app(bundleId)

                    log(f"[launch_app] App terminated successfully")

                except Exception as term_error:
                    log(f"[launch_app] Could not terminate app: {str(term_error)}")

            elif is_cloud:
                # On cloud, try terminate anyway (safe attempt)
                try:
                    log("[launch_app] Cloud mode: attempting terminate (best effort)")
                    driver.terminate_app(bundleId)
                except Exception:
                    log("[launch_app] Cloud terminate skipped (not supported)")

            # ACTIVATE APP (MAIN STEP)
            log(f"[launch_app] Activating app: {bundleId}")

            try:
                driver.activate_app(bundleId)
            except Exception as act_err:
                udid: Optional[str] = None
                if shared_state.current_device:
                    udid = shared_state.current_device.get("id")

                if (
                    not is_cloud
                    and shared_state.current_platform == "android"
                    and udid
                ):
                    log(
                        f"[launch_app] activate_app failed ({act_err}); "
                        "using adb MAIN/LAUNCHER fallback..."
                    )
                    await _adb_launch_android_package(udid, bundleId, log)
                else:
                    raise act_err

            log(f"[launch_app] App launched successfully")

            shared_state.action_recorder.record(
                "launch_app",
                {"bundleId": bundleId},
            )

            return {
                "content": [{
                    "type": "text",
                    "text": f"App '{bundleId}' launched successfully (restarted if needed)."
                }]
            }

        except Exception as e:
            log(f"[launch_app] Error launching app {bundleId}: {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error launching app '{bundleId}': {str(e)}"
                }]
            }