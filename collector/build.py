#!/usr/bin/env python3
"""Wireline Census builder.

Reads the IEEE Xplore records that the adc-census collector keeps on the lab server
(full proceedings and journal issues of the same venues) and writes the wireline transceiver
papers (DSP/ADC-based and analog) to data/papers.json. It makes no API calls and needs no API key.

Usage (run from anywhere; paths are relative to the repo):
  python3 collector/build.py            # rebuild data/papers.json and data/meta.json
  python3 collector/build.py --report   # check venue matching, classification and spec coverage
  python3 collector/build.py --cache DIR

The cache directory is, in order: --cache, $WIRELINE_CENSUS_CACHE, "cache" in collector/venues.json.
Python 3.8+, standard library only.
"""
import argparse
import datetime as dt
import html
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import classify as C  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
PAPERS = os.path.join(DATA, "papers.json")
META = os.path.join(DATA, "meta.json")
CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venues.json")


def log(*a):
    print("[%s]" % dt.datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, obj, compact=False):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if compact:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def iter_cache(cache):
    if not os.path.isdir(cache):
        return
    for fn in os.listdir(cache):
        if fn.endswith(".json"):
            a = load_json(os.path.join(cache, fn), None)
            if a:
                yield a


TEX = [(r"\\Delta", "\u0394"), (r"\\Sigma", "\u03a3"), (r"\\mu", "\u00b5"), (r"\\times", "\u00d7"),
       (r"\\pm", "\u00b1"), (r"\\sim", "~"), (r"\\geq?", "\u2265"), (r"\\leq?", "\u2264"),
       (r"\\Omega", "\u03a9"), (r"\\text\{([^}]*)\}", r"\1"), (r"\\mathrm\{([^}]*)\}", r"\1"),
       (r"\\(?:mathbf|boldsymbol)\{([^}]*)\}", r"\1"),
       # pre-2005 IEEE records spell symbols as /spl mu/, /sup 2/ ...
       (r"/spl (?:mu|micro)/\s*", "\u00b5"), (r"/spl times/", "\u00d7"), (r"/spl Delta/", "\u0394"), (r"/spl Sigma/", "\u03a3"),
       (r"/spl Omega/", "\u03a9"), (r"/spl plusmn/", "\u00b1"), (r"/spl deg/", "\u00b0"), (r"/spl sim/", "~"),
       (r"/spl les/", "\u2264"), (r"/spl ges/", "\u2265"), (r"/sup ([^/]*)/", r"\1"), (r"/sub ([^/]*)/", r"\1"), (r"/spl \w+/", "")]


def clean(s):
    if not s:
        return ""
    s = re.sub(r"<tex-math[^>]*>", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    for a, b in TEX:
        s = re.sub(a, b, s)
    s = s.replace("$", "").replace("{", "").replace("}", "").replace("\\", "")
    return re.sub(r"\s+", " ", s).strip()


def venue_of(pub_title, venues):
    for v in venues:
        if re.search(v["match"], pub_title or "", re.I):
            return v["name"]
    return None


def build_record(a, venues):
    title = clean(a.get("title"))
    if not title or C.NON_PAPER.search(title):
        return None
    pub = clean(a.get("publication_title"))
    venue = venue_of(pub, venues)
    if not venue:
        return None
    abstract = clean(a.get("abstract"))
    level = C.relevance(title, abstract)
    if not level:
        return None
    specs, src = C.spec_sources(title, abstract)
    if level != "core":     # link only mentioned in the abstract: the numbers may not be the link's
        specs, src = {}, {}
    authors = sorted((a.get("authors") or {}).get("authors") or [], key=lambda x: x.get("author_order") or 0)
    names, orgs, countries = [], [], []
    for au in authors:
        if au.get("full_name"):
            names.append(clean(au["full_name"]))
        affs = au.get("affiliation")
        if isinstance(affs, str):
            affs = [affs]
        for aff in affs or []:
            org, cn = C.org_and_country(clean(aff))
            if org and org not in orgs:
                orgs.append(org)
            if cn and cn not in countries:
                countries.append(cn)
    try:
        year = int(a.get("publication_year"))
    except (TypeError, ValueError):
        year = None
    date = C.parse_month(a.get("publication_date"), year)
    if not year and date[:4].isdigit():
        year = int(date[:4])
    ctype = a.get("content_type") or ""
    return {
        "id": str(a.get("article_number")),
        "doi": a.get("doi") or "",
        "t": title,
        "v": venue,
        "vt": pub,
        "y": year,
        "d": date,
        "au": names,
        "org": orgs[:5],
        "cn": countries,
        "lv": level,
        "ty": C.link_type(title, abstract),
        "mod": C.modulations(title, abstract),
        "ar": C.architectures(title, abstract),
        "ap": C.applications(title, abstract),
        "cal": C.has_calibration(title, abstract),
        "s": specs,
        "src": src,                      # t = title, a = abstract
        "sys": level != "core",
        "x": C.derived(specs),
        "ct": "EA" if "early" in ctype.lower() else ("C" if "conf" in ctype.lower() else "J"),
        "url": a.get("html_url") or ("https://doi.org/" + a["doi"] if a.get("doi") else ""),
        "ins": str(a.get("insert_date") or ""),
    }


def cache_dir(config, arg=None):
    return os.path.expanduser(arg or os.environ.get("WIRELINE_CENSUS_CACHE") or config.get("cache") or "")


def rebuild(config, cache, run_date):
    venues = config["venues"]
    since = config.get("since_year")
    old = {p["id"]: p for p in load_json(PAPERS, [])}
    papers = []
    for a in iter_cache(cache):
        r = build_record(a, venues)
        if not r or (since and r["y"] and r["y"] < since):
            continue
        prev = old.get(r["id"])
        # papers that appear because the adc-census back-catalogue sweep reached an older year are not "new"
        recent = (r["y"] or 0) >= int(run_date[:4]) - 1
        r["first"] = (prev.get("first", "") if prev else run_date) if recent else ""
        papers.append(r)
    if not papers and old:
        raise SystemExit("no wireline papers found in %s - is the adc-census cache there? (keeping the old data)" % cache)
    papers.sort(key=lambda r: (r.get("d") or "", r["id"]), reverse=True)
    changed = [p for p in papers if old.get(p["id"]) != p]
    if not changed and len(papers) == len(old):
        log("no change (%d papers)" % len(papers))
        return load_json(META, {})
    save_json(PAPERS, papers, compact=True)
    by_venue, by_type = {}, {}
    for p in papers:
        if p["lv"] != "core":
            continue
        by_venue[p["v"]] = by_venue.get(p["v"], 0) + 1
        by_type[p["ty"] or "Unspecified"] = by_type.get(p["ty"] or "Unspecified", 0) + 1
    dates = [p["d"] for p in papers if p.get("d")]
    meta = {
        "title": "Wireline Census",
        "source": "IEEE Xplore API (records collected by adc-census)",
        "updated": run_date,
        "coverage_from": "%d-01" % since if since else "",
        "coverage_to": max(dates) if dates else "",
        "total": len(papers),
        "core": sum(1 for p in papers if p["lv"] == "core"),
        "by_venue": by_venue,
        "by_type": by_type,
        "last_run_new": sum(1 for p in papers if p["first"] == run_date and p["id"] not in old) if old else 0,   # the first build adds nothing "new"
    }
    save_json(META, meta)
    log("wrote %d papers (%d core, %d new)" % (len(papers), meta["core"], meta["last_run_new"]))
    return meta


def report(config, cache, sample=15):
    venues = config["venues"]
    papers = load_json(PAPERS, [])
    core = [p for p in papers if p["lv"] == "core"]
    years = sorted({p["y"] for p in core if p.get("y")})
    table = {}
    for p in core:
        table.setdefault(p["v"], {}).setdefault(p["y"], 0)
        table[p["v"]][p["y"]] += 1
    print("core wireline papers by venue and year:")
    show = years[-8:]
    print("  %-8s" % "" + "".join("%6s" % y for y in show) + "   all")
    for v in sorted(table):
        print("  %-8s" % v + "".join("%6d" % table[v].get(y, 0) for y in show) + "%6d" % sum(table[v].values()))
    if core:
        def pct(k):
            return "%d%%" % round(100.0 * sum(1 for p in core if k in p["s"]) / len(core))
        print("\nspec coverage over %d core papers: rate %s, pJ/b %s, loss %s, BER %s, ADC fs %s, ADC bits %s, power %s, node %s, area %s" % (
            len(core), pct("rate"), pct("eff"), pct("loss"), pct("ber"), pct("fsadc"), pct("resadc"), pct("p"), pct("node"), pct("area")))
        print("types: %s" % {t: sum(1 for p in core if p["ty"] == t) for t in ("ADC/DAC-based", "DSP (no ADC)", "Analog/mixed-signal")})
        print("\nrandom core papers:")
        for p in random.Random(0).sample(core, min(sample, len(core))):
            print("  - [%s %s] %s  {%s | %s}" % (p["v"], p["y"], p["t"][:110], p["ty"] or "-", ", ".join(p["ar"]) or "no arch"))
    misses = []
    for a in iter_cache(cache):
        t = clean(a.get("title"))
        if venue_of(clean(a.get("publication_title")), venues) and not C.relevance(t, "") and \
                re.search(r"Gb/s|SerDes|wireline|PAM|\bCDR|equaliz", t, re.I):
            misses.append(t)
    print("\nnot wireline papers by title although they mention Gb/s, SerDes, PAM, CDR or equalizers (%d, first 25):" % len(misses))
    for t in misses[:25]:
        print("  - " + t[:140])
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", help="directory with the cached IEEE records (one JSON file per article)")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    config = load_json(CONFIG, None)
    cache = cache_dir(config, args.cache)
    if not os.path.isdir(cache):
        log("ERROR: cache directory not found: %s" % cache)
        return 2
    os.makedirs(DATA, exist_ok=True)
    if args.report:
        return report(config, cache)
    rebuild(config, cache, dt.date.today().isoformat())
    return 0


if __name__ == "__main__":
    sys.exit(main())
