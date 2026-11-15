"""Kiểm chứng AC-01..AC-03 của task copy-btn-touch-keyboard.

Cần Vite dev server ở :5173; API hội thoại được mock. Chạy: python -I -X utf8 verify_actions.py <thư mục ảnh>
"""
import json, sys
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
OUT = sys.argv[1]
now = datetime.now(timezone.utc).isoformat()
CONVS = {"conversations": [{"id": "c1", "title": "Học bổng KKHT", "created_at": now, "updated_at": now}], "total": 1}
DETAIL = {"id": "c1", "title": "Học bổng KKHT", "messages": [
    {"role": "user", "content": "Điều kiện học bổng?"},
    {"role": "assistant", "content": "Câu trả lời đầy đủ.", "sources": []},
    {"role": "user", "content": "Còn gì nữa?"},
    {"role": "assistant", "content": "Câu trả lời bị dừng", "sources": [], "interrupted": True},
]}

def mock(route):
    url = route.request.url
    if route.request.method == "GET" and "/api/conversations/c1" in url:
        return route.fulfill(json=DETAIL)
    if route.request.method == "GET" and "/api/conversations" in url:
        return route.fulfill(json=CONVS)
    return route.continue_()

def opac(page, sel):
    return page.eval_on_selector_all(sel, "els => els.map(e => getComputedStyle(e).opacity)")

def open_conv(page, mobile):
    page.route(lambda u: u.startswith(BASE + "/api/conversations"), mock)
    page.goto(BASE + "/chat", wait_until="networkidle")
    if mobile:
        page.click(".mobile-menu-btn")
    page.click(".conv-open-btn")
    page.wait_for_selector(".bubble-actions")
    page.wait_for_timeout(600)

res = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    # Desktop with mouse
    page = b.new_context(viewport={"width": 1366, "height": 800}).new_page()
    open_conv(page, False)
    page.evaluate("document.activeElement && document.activeElement.blur()")
    page.mouse.move(5, 790)  # away from everything
    page.wait_for_timeout(400)
    res["desktop_hover_none_query"] = page.evaluate("matchMedia('(hover: none)').matches")
    res["desktop_idle_bubble"] = opac(page, ".bubble-actions")
    res["desktop_idle_conv"] = opac(page, ".conv-actions")
    page.screenshot(path=f"{OUT}/desktop-idle.png")
    page.hover(".message-row.assistant .bubble-wrap >> nth=0")
    page.wait_for_timeout(400)
    res["desktop_hover_bubble"] = opac(page, ".bubble-actions")
    page.screenshot(path=f"{OUT}/desktop-hover.png")
    page.hover(".conv-item")
    page.wait_for_timeout(400)
    res["desktop_hover_conv"] = opac(page, ".conv-actions")
    page.mouse.move(5, 790)
    page.wait_for_timeout(400)
    # Keyboard: focus the element before the first copy button, then Tab into it
    page.evaluate("""() => { const btn = document.querySelector('.message-row.assistant .copy-btn');
        const all = [...document.querySelectorAll('button, a[href], input, textarea, [tabindex]:not([tabindex="-1"])')];
        all[all.indexOf(btn) - 1].focus(); }""")
    page.keyboard.press("Tab")
    page.wait_for_timeout(400)
    res["keyboard_active_is_copy"] = page.evaluate("document.activeElement.classList.contains('copy-btn') && !!document.activeElement.closest('.message-row.assistant')")
    res["keyboard_focus_visible"] = page.evaluate("document.activeElement.matches(':focus-visible')")
    res["keyboard_outline"] = page.evaluate("(() => { const s = getComputedStyle(document.activeElement); return s.outlineStyle + ' ' + s.outlineWidth + ' ' + s.outlineColor; })()")
    res["keyboard_bubble"] = opac(page, ".bubble-actions")
    page.locator(".message-row.assistant .copy-btn").first.scroll_into_view_if_needed()
    page.screenshot(path=f"{OUT}/desktop-keyboard-focus.png")
    # Touch device (hover: none)
    ctx = b.new_context(**p.devices["Pixel 7"])
    page = ctx.new_page()
    open_conv(page, True)
    res["touch_hover_none_query"] = page.evaluate("matchMedia('(hover: none)').matches")
    res["touch_bubble"] = opac(page, ".bubble-actions")
    res["touch_conv"] = opac(page, ".conv-actions")
    page.screenshot(path=f"{OUT}/touch-chat.png")
    page.click(".mobile-menu-btn")
    page.wait_for_timeout(500)
    page.screenshot(path=f"{OUT}/touch-sidebar.png")
    b.close()
print(json.dumps(res, ensure_ascii=False, indent=1))
