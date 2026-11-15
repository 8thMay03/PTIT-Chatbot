import json, re, sys
sys.path.insert(0, '.')
from measure import NAV_JS, GUEST, USER_LONG, USER_SHORT, BASE
from playwright.sync_api import sync_playwright
widths = sorted(set(list(range(320, 1441, 4)) + [439,440,479,480,519,520,599,600,639,640,767,768,899,900,1099,1100,1199,1200,1319,1320]))
fails, trunc = [], {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for label, s in [("guest", GUEST), ("user-long", USER_LONG), ("user-short", USER_SHORT)]:
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.route(re.compile(r"^http://localhost:5199/api/"), lambda r, q=None, s=s: r.fulfill(status=200, content_type="application/json", body=json.dumps(s)))
        pg = ctx.new_page(); pg.goto(BASE + "/")
        pg.wait_for_function("t => document.querySelector('.lp-nav-actions .lp-btn')?.textContent.includes(t)", arg="Đăng ký" if label == "guest" else "Vào trò chuyện")
        pg.evaluate("document.fonts.ready")
        pg.add_style_tag(content="*, *::before, *::after { transition: none !important; }")
        for w in widths:
            pg.set_viewport_size({"width": w, "height": 900})
            for st in ["top", "scrolled"]:
                pg.evaluate("s => { const n = document.querySelector('.lp-nav'); if (s === 'top') delete n.dataset.navState; else n.dataset.navState = s; }", st)
                pg.wait_for_timeout(30)
                m = pg.evaluate(NAV_JS)
                if not (m["scrollOk"] and not m["overlaps"] and not m["outside"] and not m["footerClipped"]):
                    fails.append((label, w, st, m["overlaps"], m["outside"]))
                if any("brand-name(" in v for v in m["visible"]):
                    trunc.setdefault((label, st), []).append(w)
        ctx.close()
print("widths", len(widths), "fails", len(fails))
for f in fails[:40]: print(f)
for k, v in trunc.items(): print("brand truncated", k, v)
