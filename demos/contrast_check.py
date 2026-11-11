import pathlib, re, sys
from playwright.sync_api import sync_playwright
url = (pathlib.Path(__file__).resolve().parent / "visualize.html").as_uri()
def lum(rgb):
    vals = [int(x)/255 for x in re.findall(r"\d+", rgb)[:3]]
    f = lambda c: c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4
    r,g,b = [f(v) for v in vals]
    return 0.2126*r+0.7152*g+0.0722*b
def ratio(c1,c2):
    l1,l2 = lum(c1),lum(c2)
    return (max(l1,l2)+0.05)/(min(l1,l2)+0.05)
ok = True
with sync_playwright() as p:
    b = p.chromium.launch()
    for scheme in ("dark","light"):
        pg = b.new_page(color_scheme=scheme)
        pg.goto(url)
        pg.wait_for_selector(".badge.GREEN")
        for sel in (".badge.GREEN",".tabs button.on"):
            el = pg.query_selector(sel)
            c = el.evaluate("e => getComputedStyle(e).color")
            bg = el.evaluate("e => getComputedStyle(e).backgroundColor")
            r = ratio(c,bg)
            passed = r >= 4.5
            ok = ok and passed
            print(f"{scheme:5s} {sel:18s} color={c:18s} bg={bg:18s} contrast={r:.2f} {'PASS' if passed else 'FAIL'}")
        # RED 徽章：经页面自身 ingest/render 注入最小 RED 报告（R9 NEW-5）
        pg.evaluate("ingest('red_probe.json', JSON.stringify({status:'RED'})); render();")
        el = pg.query_selector(".badge.RED")
        c = el.evaluate("e => getComputedStyle(e).color")
        bg = el.evaluate("e => getComputedStyle(e).backgroundColor")
        r = ratio(c,bg)
        passed = r >= 4.5
        ok = ok and passed
        print(f"{scheme:5s} {'.badge.RED':18s} color={c:18s} bg={bg:18s} contrast={r:.2f} {'PASS' if passed else 'FAIL'}")
        pg.close()
    b.close()
print("RESULT:", "ALL PASS (AA)" if ok else "FAIL")
sys.exit(0 if ok else 1)
