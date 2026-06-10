"""Interaction tools: click, type, hover, select, keys, wait, evaluate, scroll."""
from __future__ import annotations

from typing import Any

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_click(
        ref: str,
        session_id: str | None = None,
        button: str = "left",
        double: bool = False,
    ) -> str:
        """Click an element by its snapshot ref (e.g. 'e12' or 'f1e36' for iframe elements).
        Returns a fresh snapshot."""
        s = await state.get_engine().ensure_session(session_id)
        await s.click(ref, button=button, double=double)
        return await s.snapshot()

    @mcp.tool()
    async def browser_type(
        ref: str,
        text: str | None = None,
        session_id: str | None = None,
        submit: bool = False,
        clear: bool = True,
        value: str | None = None,
    ) -> str:
        """Type text into a field by ref (top-frame or iframe ref like 'f1e20').
        submit=True presses Enter after. Returns a snapshot.

        Pass the string as `text`. `value` is accepted as an alias for `text` (a common slip,
        since browser_fill_form fields use `value`) so the call doesn't hard-error."""
        typed = text if text is not None else value
        if typed is None:
            return "browser_type error: provide `text` — the string to type into the field."
        s = await state.get_engine().ensure_session(session_id)
        val = await s.type(ref, typed, submit=submit, clear=clear)
        snap = await s.snapshot()
        # Surface the READ-BACK so you can tell whether the value actually landed (controlled inputs
        # silently no-op). If it shows empty/wrong, re-type or use browser_set_input.
        if val is not None and val != typed:
            return f"typed, but field VALUE now reads {val!r} (expected {typed!r}) — re-check / use browser_set_input.\n\n{snap}"
        return snap

    @mcp.tool()
    async def browser_keyboard_type(
        text: str,
        session_id: str | None = None,
        delay: float | None = None,
    ) -> str:
        """Type text into the currently focused element — no ref needed.

        Works on contenteditable rich-text editors (TipTap, Quill, ProseMirror)
        where browser_type / fill() is a no-op. Also the escape hatch when a
        coordinate click focused an iframe field and you need to type into it.
        Pattern: browser_mouse_click(x, y) to focus → browser_keyboard_type(text).
        delay: ms between keystrokes (simulates human typing speed).
        Returns a snapshot."""
        s = await state.get_engine().ensure_session(session_id)
        await s.keyboard_type(text, delay=delay)
        return await s.snapshot()

    @mcp.tool()
    async def browser_fill_form(fields: list[dict], session_id: str | None = None) -> str:
        """Fill multiple fields at once. Each field: {ref, value, submit?, clear?}."""
        s = await state.get_engine().ensure_session(session_id)
        await s.fill_form(fields)
        return await s.snapshot()

    @mcp.tool()
    async def browser_hover(ref: str, session_id: str | None = None) -> str:
        """Hover over an element by ref. Returns a snapshot."""
        s = await state.get_engine().ensure_session(session_id)
        await s.hover(ref)
        return await s.snapshot()

    @mcp.tool()
    async def browser_select_option(
        ref: str,
        values: list[str],
        session_id: str | None = None,
    ) -> str:
        """Select option(s) in a NATIVE <select> by ref (match by value OR visible label). Self-
        verifies and, on a no-match, returns the available option labels. For a CUSTOM / searchable
        dropdown (styled div, role=combobox/listbox — most country-code pickers) this will not work —
        use browser_select_combobox instead. Returns the committed option + a snapshot."""
        s = await state.get_engine().ensure_session(session_id)
        committed = await s.select_option(ref, values)
        return f"selected -> {committed}\n\n{await s.snapshot()}"

    @mcp.tool()
    async def browser_select_combobox(
        ref: str,
        value: str,
        session_id: str | None = None,
        submit_key: str = "Enter",
    ) -> str:
        """Pick `value` from a CUSTOM / searchable dropdown or combobox (country & country-code
        pickers, styled listboxes) where browser_select_option times out. Opens the trigger `ref`,
        types `value` to filter, commits the highlighted option by keyboard (ArrowDown+Enter), then
        VERIFIES the committed value and falls back to clicking the option by visible text. Filter by
        the COUNTRY NAME (e.g. 'Germany'), not a dial code ('49') which matches the wrong row. Returns
        {committed, actual} + a snapshot — if committed=false the selection did NOT take."""
        s = await state.get_engine().ensure_session(session_id)
        res = await s.select_combobox(ref, value, submit_key=submit_key)
        return f"combobox -> {res}\n\n{await s.snapshot()}"

    @mcp.tool()
    async def browser_set_input(ref: str, value: str, session_id: str | None = None) -> str:
        """Set `value` on a FRAMEWORK-CONTROLLED input (React/Vue) via the native value setter +
        input/change events. Use this when browser_type / fill silently leaves the field EMPTY
        (controlled components re-derive value from state and ignore plain typing — e.g. some OTP and
        masked phone inputs). Returns the resulting value + a snapshot."""
        s = await state.get_engine().ensure_session(session_id)
        val = await s.set_input(ref, value)
        return f"set value -> {val!r}\n\n{await s.snapshot()}"

    @mcp.tool()
    async def browser_type_otp(ref: str, code: str, session_id: str | None = None) -> str:
        """Enter an OTP/verification `code` into the field at `ref`, handling MULTI-BOX widgets (one
        <input maxlength=1> per digit that auto-advances) by distributing the digits across the boxes
        via the React-tracked setter — instead of typing the whole code into box 1 (which lands the
        digits in the wrong boxes). Works on a single field too. Returns {boxes, value} (read it back)
        + a snapshot. After this, still SUBMIT (Enter / a Verify button)."""
        s = await state.get_engine().ensure_session(session_id)
        res = await s.type_otp(ref, code)
        return f"otp entered -> {res}\n\n{await s.snapshot()}"

    @mcp.tool()
    async def browser_press_key(key: str, session_id: str | None = None) -> str:
        """Press a keyboard key (e.g. 'Enter', 'Escape', 'ArrowDown', 'Tab'). Returns a snapshot."""
        s = await state.get_engine().ensure_session(session_id)
        await s.press_key(key)
        return await s.snapshot()

    @mcp.tool()
    async def browser_drag(from_ref: str, to_ref: str, session_id: str | None = None) -> str:
        """Drag one element onto another (by refs). Returns a snapshot."""
        s = await state.get_engine().ensure_session(session_id)
        await s.drag(from_ref, to_ref)
        return await s.snapshot()

    @mcp.tool()
    async def browser_file_upload(ref: str, paths: list[str], session_id: str | None = None) -> str:
        """Set files on a file <input> by ref (absolute paths). Returns a snapshot."""
        s = await state.get_engine().ensure_session(session_id)
        await s.upload_files(ref, paths)
        return await s.snapshot()

    @mcp.tool()
    async def browser_handle_dialog(
        accept: bool = True,
        prompt_text: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Accept or dismiss an open JS dialog (alert/confirm/prompt). prompt_text fills
        a prompt() before accepting. Dialogs stay open until handled."""
        s = await state.get_engine().ensure_session(session_id)
        return await s.handle_dialog(accept=accept, prompt_text=prompt_text)

    @mcp.tool()
    async def browser_wait_for(
        session_id: str | None = None,
        text: str | None = None,
        text_gone: str | None = None,
        selector: str | None = None,
        url: str | None = None,
        network_idle: bool = False,
        time: float | None = None,
        timeout_ms: float | None = None,
    ) -> str:
        """Wait for a condition then return a fresh snapshot. Pass exactly one condition:

        text        — text to become visible (searched across all frames including iframes).
        text_gone   — text to disappear.
        selector    — CSS/Playwright selector to become visible.
        url         — URL glob/regex to wait for (SPA client-side navigation).
        network_idle — wait until no network requests for 500ms (SPA render complete).
        time        — wait N seconds unconditionally.
        timeout_ms  — max wait in ms (default 30 000).
        """
        s = await state.get_engine().ensure_session(session_id)
        await s.wait_for(
            text=text, text_gone=text_gone, selector=selector,
            url=url, network_idle=network_idle,
            time=time, timeout_ms=timeout_ms,
        )
        return await s.snapshot()

    @mcp.tool()
    async def browser_evaluate(
        expression: str,
        session_id: str | None = None,
        frame_ref: str | None = None,
    ) -> Any:
        """Evaluate a JS expression or function in the page and return the result.

        frame_ref: run the JS INSIDE a child frame instead of the top document. Accepts
        a frame id ('f1'), an element ref inside the frame ('f1e36'), or an <iframe>
        element ref ('e81'). This works for CROSS-ORIGIN frames too — the code runs in
        the frame's own context (unlike top-frame JS reaching in via contentDocument,
        which the browser blocks). This is the fix for "Permission denied to access
        property document on cross-origin object".
        Examples: 'document.title'  |  '() => window.location.href'
        """
        s = await state.get_engine().ensure_session(session_id)
        result = await s.evaluate(expression, frame_ref=frame_ref)
        if isinstance(result, (str, int, float, bool, type(None), list, dict)):
            return result
        return str(result)

    @mcp.tool()
    async def browser_scroll(
        direction: str = "down",
        amount: int = 300,
        ref: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Scroll the page by pixels in a direction, or scroll an element into view.

        direction: 'up' | 'down' | 'left' | 'right'. amount: pixels (default 300).
        ref: if given, scrolls that element into view (direction/amount ignored).
        Use this to trigger lazy-loaded content or reveal off-screen elements.
        Returns a snapshot."""
        s = await state.get_engine().ensure_session(session_id)
        await s.scroll(direction, amount, ref=ref)
        return await s.snapshot()

    @mcp.tool()
    async def browser_scroll_to_bottom(
        max_scrolls: int = 20,
        wait_ms: int = 500,
        session_id: str | None = None,
    ) -> str:
        """Scroll to the very bottom of the page, pausing to let lazy content load.

        Stops when the page height stops growing (infinite scroll exhausted or real
        bottom reached). max_scrolls: safety cap. wait_ms: pause per step.
        Returns a snapshot of the final state."""
        s = await state.get_engine().ensure_session(session_id)
        steps = await s.scroll_to_bottom(max_scrolls=max_scrolls, wait_ms=wait_ms)
        snap = await s.snapshot()
        return f"scrolled {steps} step(s) to bottom\n\n{snap}"
