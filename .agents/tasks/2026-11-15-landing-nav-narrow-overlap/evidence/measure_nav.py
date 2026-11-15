"""Measure landing nav / auth header layout across viewport widths.

Usage: python measure.py <out_dir> [--shots]
"""
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5199"
WIDTHS = [320, 375, 414, 480, 520, 600, 640, 768, 900, 1024, 1100, 1440]
GUEST = {"authenticated": False, "user": None, "registration_enabled": True}
USER_LONG = {
    "authenticated": True,
    "registration_enabled": True,
    "user": {"id": 1, "email": "sv@stu.ptit.edu.vn", "full_name": "Nguyễn Thị Phương Thảo Anh Đào"},
}
USER_SHORT = {
    "authenticated": True,
    "registration_enabled": True,
    "user": {"id": 1, "email": "sv@stu.ptit.edu.vn", "full_name": "An"},
}

NAV_JS = r"""
() => {
  const sel = [
    '.lp-nav .lp-brand-tile', '.lp-nav .lp-brand-name', '.lp-nav-divider', '.lp-nav-tagline',
    '.lp-nav-links', '.lp-nav-actions .lp-theme-toggle', '.lp-nav-user .lp-avatar',
    '.lp-nav-user-name', '.lp-nav-login', '.lp-nav-actions .lp-btn'
  ];
  const vis = [];
  for (const s of sel) {
    const el = document.querySelector(s);
    if (!el) continue;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (cs.display === 'none' || r.width === 0) continue;
    vis.push({ s, l: r.left, r: r.right, t: r.top, b: r.bottom,
               clipped: el.scrollWidth > el.clientWidth + 0.5 });
  }
  const overlaps = [];
  for (let i = 0; i < vis.length; i++) for (let j = i + 1; j < vis.length; j++) {
    const a = vis[i], b = vis[j];
    if (a.l < b.r - 0.5 && b.l < a.r - 0.5 && a.t < b.b - 0.5 && b.t < a.b - 0.5)
      overlaps.push(a.s + ' x ' + b.s);
  }
  const container = document.querySelector('.lp-nav-inner').getBoundingClientRect();
  const outside = vis.filter(v => v.l < container.left - 0.5 || v.r > container.right + 0.5).map(v => v.s);
  const fb = document.querySelectorAll('.lp-brand-name')[1];
  return {
    scrollOk: document.documentElement.scrollWidth <= window.innerWidth,
    footerClipped: fb.scrollWidth > fb.clientWidth + 0.5,
    overlaps, outside,
    visible: vis.map(v => v.s.replace(/^\.lp-nav(-actions)? /, '') + (v.clipped ? '(…)' : '')),
  };
}
"""

AUTH_JS = r"""
() => {
  const sel = ['.auth-header .lp-brand-tile', '.auth-header .lp-brand-name', '.auth-header .theme-toggle'];
  const vis = sel.map(s => { const el = document.querySelector(s); const r = el.getBoundingClientRect();
    return { s, l: r.left, r: r.right, clipped: el.scrollWidth > el.clientWidth + 0.5 }; });
  const overlaps = [];
  for (let i = 0; i < vis.length; i++) for (let j = i + 1; j < vis.length; j++)
    if (vis[i].l < vis[j].r - 0.5 && vis[j].l < vis[i].r - 0.5) overlaps.push(vis[i].s + ' x ' + vis[j].s);
  return { scrollOk: document.documentElement.scrollWidth <= window.innerWidth, overlaps,
           clipped: vis.filter(v => v.clipped).map(v => v.s) };
}
"""


def main():
    out = Path(sys.argv[1])
    shots = "--shots" in sys.argv
    out.mkdir(parents=True, exist_ok=True)
    results = []
    failures = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in ["light", "dark"]:
            for label, session in [("guest", GUEST), ("user-long", USER_LONG), ("user-short", USER_SHORT)]:
                ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference")
                ctx.add_init_script(f"localStorage.setItem('ptit_chatbot_theme', '{theme}')")
                ctx.route(re.compile(r"^http://localhost:5199/api/auth/me"), lambda route, req=None, s=session: route.fulfill(
                    status=200, content_type="application/json", body=json.dumps(s)))
                ctx.route(re.compile(r"^http://localhost:5199/api/"), lambda route: route.fulfill(status=404, body="{}")
                          if "auth/me" not in route.request.url else route.fallback())
                page = ctx.new_page()
                page.goto(BASE + "/")
                page.wait_for_selector(".lp-nav-actions .lp-btn", state="attached")
                page.evaluate("document.fonts.ready")
                expected_btn = "Đăng ký" if label == "guest" else "Vào trò chuyện"
                page.wait_for_function(
                    "t => document.querySelector('.lp-nav-actions .lp-btn').textContent.includes(t)", arg=expected_btn)
                assert page.evaluate("document.querySelector('.landing-page').classList.contains('motion-ready')")
                for w in WIDTHS:
                    page.set_viewport_size({"width": w, "height": 900})
                    for state in ["top", "scrolled"]:
                        page.evaluate("s => { const n = document.querySelector('.lp-nav'); if (s === 'top') delete n.dataset.navState; else n.dataset.navState = s; }", state)
                        page.wait_for_timeout(700)
                        m = page.evaluate(NAV_JS)
                        ok = m["scrollOk"] and not m["overlaps"] and not m["outside"] and not m["footerClipped"]
                        failures += 0 if ok else 1
                        results.append({"page": "/", "theme": theme, "session": label, "w": w, "state": state, "ok": ok, **m})
                        if shots:
                            page.screenshot(path=str(out / f"landing-{theme}-{label}-{w}-{state}.png"),
                                            clip={"x": 0, "y": 0, "width": w, "height": 110})
                ctx.close()
            for path in ["/login", "/register"]:
                ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
                ctx.add_init_script(f"localStorage.setItem('ptit_chatbot_theme', '{theme}')")
                ctx.route(re.compile(r"^http://localhost:5199/api/"), lambda route: route.fulfill(
                    status=200, content_type="application/json", body=json.dumps(GUEST)))
                page = ctx.new_page()
                page.goto(BASE + path)
                page.wait_for_selector(".auth-header .lp-brand-name", state="attached")
                page.evaluate("document.fonts.ready")
                for w in WIDTHS:
                    page.set_viewport_size({"width": w, "height": 900})
                    page.wait_for_timeout(50)
                    m = page.evaluate(AUTH_JS)
                    ok = m["scrollOk"] and not m["overlaps"] and not m["clipped"]
                    failures += 0 if ok else 1
                    results.append({"page": path, "theme": theme, "w": w, "ok": ok, **m})
                    if shots and w in (320, 480, 768, 1440):
                        page.screenshot(path=str(out / f"auth{path.replace('/', '-')}-{theme}-{w}.png"),
                                        clip={"x": 0, "y": 0, "width": w, "height": 100})
                ctx.close()
        browser.close()
    (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in results:
        if r["page"] == "/":
            print(f"{'OK  ' if r['ok'] else 'FAIL'} / {r['theme']:5} {r['session']:10} {r['w']:5} {r['state']:8} "
                  f"scroll={r['scrollOk']} ftr={r['footerClipped']} ov={r['overlaps']} out={r['outside']} vis={r['visible']}")
        else:
            print(f"{'OK  ' if r['ok'] else 'FAIL'} {r['page']} {r['theme']:5} {r['w']:5} "
                  f"scroll={r['scrollOk']} ov={r['overlaps']} clipped={r['clipped']}")
    print(f"total={len(results)} failures={failures}")


if __name__ == "__main__":
    main()
