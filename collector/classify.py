"""Classification and spec extraction for wireline transceiver papers (with a focus on DSP/ADC-based links).

Pure functions (no network, no files) so they can be unit-tested and re-run over the
cached records whenever the rules change. Abstracts are inputs only; they are never
written to the output.
"""
import re

I = re.IGNORECASE

# ---------------------------------------------------------------- relevance
# the link itself ...
LINK = re.compile(r"transceivers?|receivers?|transmitters?|\bTRX\b|\bTX\b|\bRX\b|SerDes|\bPHY\b|serial (?:link|I/O)|links?\b|"
                  r"\bI/Os?\b|interfaces?|\bCDRs?\b|clock and data recovery|equaliz\w*|\bDFE\b|\bFFE\b|\bCTLE\b|\bMLSD\b|"
                  r"retimers?|repeaters?|drivers?|analog front[- ]ends?|\bAFE\b|sequence detectors?|\bTIAs?\b|transimpedance", I)
# ... in a wireline setting
WIRE = re.compile(r"wireline|feed[- ]?forward equaliz|decision[- ]feedback equaliz|SerDes|\bPAM[- ]?\d|\bNRZ\b|\bDMT\b|multitone|duobinary|Gb/s|Gbps|Gb/s/pin|Tb/s|GBaud|GBd|backplane|"
                  r"chip[- ]to[- ]chip|die[- ]to[- ]die|\bD2D\b|chiplet|serial link|\bCDR\b|clock and data recovery|\bDFE\b|\bFFE\b|"
                  r"\bCTLE\b|\bMLSD\b|copper|cable|PCIe|Ethernet|\bCEI\b|\bUCIe|\bHBM|\bGDDR|\bLPDDR|\bDDR\d|memory interface|"
                  r"optical (?:link|transceiver|receiver|transmitter|interconnect)|\bVCSEL|silicon photonic|co[- ]packaged|"
                  r"inter[- ]?connect|\bUSB\b|DisplayPort|\bHDMI|\bMIPI", I)
# radio links share words like "receiver" and "Gb/s"
WIRELESS = re.compile(r"wireless|\bRF\b|radio|mm-?wave|millimeter|\b[56]G\b|antenna|\bLNA\b|phased[- ]array|beamform|"
                      r"[0-9]\s*GHz (?:band|carrier)|D-band|W-band|E-band|sub-THz|terahertz|THz|\bQAM\b.*wireless|radar|\bBLE\b|Wi-?Fi|UWB|"
                      r"body[- ]channel|\bNFC\b|optical wireless|backscatter|uplink|downlink|baseband|massive|cellular|\bB5G|\b6G|space[- ]time|spatially multiplexed|MIMO systems", I)
NON_PAPER = re.compile(
    r"^(front cover|back cover|table of contents|contents|author index|index|"
    r"call for papers|editorial|guest editorial|reviewers|session \d+ overview|"
    r"(?:tutorials?|short course|evening (?:event|session)|forum|panel)(?=\s*:|\s*$)|"
    r"(ieee )?(transactions|journal) .*information|blank page|copyright)\b", I)
DSP_RX = re.compile(r"ADC[- ]based|DAC[- ]based|DSP[- ]based|\bDSP\b|\bMLSD\b|maximum[- ]likelihood|Viterbi|digital equaliz|"
                    r"digital (?:FFE|DFE|FIR)|ADC/DAC|DAC/ADC|discrete multitone|\bDMT\b|\bOFDM\b|MIMO", I)


def relevance(title, abstract):
    """Return 'core' (a wireline transceiver, receiver, transmitter, CDR or equalizer), 'related' or None."""
    t = title or ""
    if WIRELESS.search(t) and not re.search(r"wireline|SerDes|serial link|backplane|chip[- ]to[- ]chip|die[- ]to[- ]die", t, I):
        return None
    if LINK.search(t) and WIRE.search(t):
        return "core"
    if DSP_RX.search(t) and re.search(r"wireline|SerDes|PAM|NRZ|serial|links?\b|equaliz|\bCDR|backplane|optical", t, I):
        return "core"
    a = abstract or ""
    if re.search(r"wireline|SerDes|serial link", a, I) and LINK.search(t) and not WIRELESS.search(t) and re.search(r"Gb/s|PAM|NRZ", a, I):
        return "related"
    return None


# ------------------------------------------------------------- type / architecture / application
ADC_DAC_RX = re.compile(r"(?:time[- ]based|SAR|time[- ]interleaved|pipelined?|flash|[0-9]+[- ]?b(?:it)?)[- ]ADCs?\b|ADC[- ]based|DAC[- ]based|ADC/DAC|DAC/ADC|ADC[- ]DSP|DSP[- ]DAC|DAC[- ]DSP|\bADC[- ]front[- ]end", I)


def link_type(title, abstract):
    """ADC/DAC-based: the signal is digitized before detection (ADC-based RX) or synthesized by a DAC (DAC-based TX),
    usually with DSP behind it. DSP (no ADC): digital equalization/detection named in the title without an ADC/DAC
    front end. Otherwise analog/mixed-signal. Judged from the title and the first two sentences of the abstract."""
    first = " ".join(re.split(r"(?<=[.!?])\s+", abstract or "")[:2])
    if ADC_DAC_RX.search(title or "") or ADC_DAC_RX.search(first):
        return "ADC/DAC-based"
    if DSP_RX.search(title or "") or DSP_RX.search(first):
        return "DSP (no ADC)"
    return "Analog/mixed-signal"


ARCH_RULES = [
    ("ADC-based RX",     r"ADC[- ]based|ADC/DAC|DAC/ADC|ADC[- ]DSP|time[- ]interleaved (?:SAR )?ADC"),
    ("DAC-based TX",     r"DAC[- ]based|DSP[- ]DAC|DAC/ADC|ADC/DAC|DAC[- ]DSP|SST DAC"),
    ("MLSD",             r"\bMLSD\b|maximum[- ]likelihood|Viterbi|sequence detect"),
    ("DFE",              r"\bDFE\b|decision[- ]feedback"),
    ("FFE",              r"\bFFE\b|feed[- ]?forward equaliz|\bFIR\b"),
    ("CTLE",             r"\bCTLE\b|continuous[- ]time linear equaliz"),
    ("CDR",              r"\bCDR\b|clock and data recovery|baud[- ]rate|Mueller|phase detector"),
    ("Multicarrier/DMT", r"multicarrier|multitone|\bDMT\b|\bOFDM\b"),
    ("Crosstalk/echo cancel", r"crosstalk|echo cancel|\bFEXT|\bNEXT\b|MIMO"),
    ("Clock-forwarded",  r"forwarded[- ]clock|clock[- ]forward|source[- ]synchronous"),
    ("FEC",              r"\bFEC\b|forward error correct|Reed[- ]Solomon|\bKP4\b"),
]
ARCH_RX = [(n, re.compile(p, I)) for n, p in ARCH_RULES]

MOD_RULES = [("NRZ", r"\bNRZ\b|PAM[- ]?2\b"), ("PAM3", r"PAM[- ]?3\b"), ("PAM4", r"PAM[- ]?4\b|\b4[- ]PAM"),
             ("PAM6", r"PAM[- ]?6\b"), ("PAM8", r"PAM[- ]?8\b"), ("Duobinary", r"duo[- ]?binary|Duo[- ]PAM"),
             ("DMT/OFDM", r"\bDMT\b|multitone|\bOFDM\b")]
MOD_RX = [(n, re.compile(p, I)) for n, p in MOD_RULES]


def architectures(title, abstract):
    def scan(text):
        return [n for n, rx in ARCH_RX if rx.search(text or "")]
    tags = scan(title)
    if abstract:
        first = " ".join(re.split(r"(?<=[.!?])\s+", abstract)[:2])
        for t in scan(first):
            if t not in tags:
                tags.append(t)
    return tags


def modulations(title, abstract):
    first = " ".join(re.split(r"(?<=[.!?])\s+", abstract or "")[:2])
    return [n for n, rx in MOD_RX if rx.search(title or "") or rx.search(first)]


APP_RULES = [
    ("Long-reach/backplane", r"long[- ]reach|\bLR\b|backplane|[3-9]\d(?:\.\d)?[- ]?dB[- ](?:channel[- ]|insertion[- ])?loss|loss (?:of |exceeding |over |beyond )?>?\s?[3-9]\d[- ]?dB|copper cable|\bCEI\b|\bKR\b"),
    ("Optical/data center",  r"optical|VCSEL|photonic|data[- ]?center|co[- ]packaged|\bCPO\b|\bLPO\b|PAM4 optical|\b(?:400|800)G\b"),
    ("Die-to-die/chiplet",   r"die[- ]to[- ]die|\bD2D\b|chiplet|\bUCIe|interposer|2\.5[- ]?D|short[- ]reach|\bXSR\b|\bUSR\b"),
    ("Memory interface",     r"\bHBM|\bGDDR|\bLPDDR|\bDDR\d|DRAM|memory interface"),
    ("PCIe/Ethernet/USB",    r"PCIe|PCI Express|Ethernet|\bUSB\b|Thunderbolt"),
    ("Display/automotive",   r"display|\bHDMI|DisplayPort|\bMIPI|automotive|in[- ]vehicle"),
]
APP_RX = [(n, re.compile(p, I)) for n, p in APP_RULES]
CAL_RX = re.compile(r"adaptive|adaptation|calibrat|\bLMS\b|\bSS-LMS\b|background", I)


def applications(title, abstract):
    text = (title or "") + " " + (abstract or "")
    return [n for n, rx in APP_RX if rx.search(text)]


def has_calibration(title, abstract):
    return bool(CAL_RX.search((title or "") + " " + (abstract or "")))


# ------------------------------------------------------------- spec parsing
NUM = r"(\d+(?:\.\d+)?)"
_SI = {"a": 1e-18, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6,
       "m": 1e-3, "": 1.0, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}
_RNG = r"(?:" + NUM + r"\s*(?:-|–|to|-to-)\s*)?"
RATE_RX = re.compile(r"(?<![\w.])" + _RNG + NUM + r"\s*-?\s*([GT])\s?(?:b/s|bps|b/s/pin|bit/s)\b", I)
EFF_RX = re.compile(NUM + r"\s*-?\s*([fpn])J\s*/\s*(?:b|bit)\b", I)
EFF_MW_RX = re.compile(NUM + r"\s*-?\s*mW\s*/\s*(?:Gb/s|Gbps|Gb)\b", I)      # mW/(Gb/s) = pJ/b
LOSS_RX = [re.compile(r"(?:>|over|up to|beyond|exceeding|of)?\s*" + NUM + r"\s*-?\s*dB(?:[- ](?:channel[- ])?(?:loss|insertion loss|attenuation)| (?:of )?(?:channel )?loss)", I),
           re.compile(r"(?:loss|insertion loss|attenuation)(?: of)?\s*(?:>|over|up to|exceeding)?\s*" + NUM + r"\s*-?\s*dB", I)]
BER_RX = re.compile(r"BER\s*(?:of|<|≤|below|less than|=)?\s*(?:10\s*\^?\s*[−–-]\s*(\d{1,2})|1\s*?[eE][−–-]?(\d{1,2}))", I)
FSADC_RX = re.compile(r"(?<![\w.])" + NUM + r"\s*-?\s*([MG])\s?S/s", I)
RESADC_RX = re.compile(r"(?<![\w.])(\d{1,2})[- ]?(?:b(?:it)?s?)\s+(?:\w+\s+){0,3}?(?:ADC|DAC)", I)
NODE_NM_RX = re.compile(r"(?<![\w.])(\d{1,3})\s*-?\s*nm\b", I)
NODE_UM_RX = re.compile(r"(?<![\w.])(0\.\d{1,3})\s*-?\s*[µμu]m\b", I)
POWER_VAL = NUM + r"\s*-?\s*([nuµμm]?)W\b(?!\s*/)"
POWER_CTX_RX = re.compile(r"(?:consum\w*|dissipat\w*|power(?:\s+consumption)?|draw(?:s|ing)|drains?|burns?)[^.;]{0,40}?" + POWER_VAL, I)
POWER_AFTER_RX = re.compile(POWER_VAL + r"\s*(?:of\s+)?(?:total\s+|overall\s+)?(?:power|consumption|dissipation)", I)
POWER_TITLE_RX = re.compile(POWER_VAL)
AREA_RX = re.compile(NUM + r"\s*-?\s*mm\s*(?:2|²|\^2)", I)
_FIXES = [(re.compile(r"(\d)\.\s(\d)"), r"\1.\2"), (re.compile(r"(\d)\s*-?\s*mu(m|W|A|V|s|J)\b"), r"\1 µ\2"),
          (re.compile(r"([µμ])\s+m\b"), r"\1m"), (re.compile(r"\\?hbox\s*"), ""), (re.compile(r"Gbps", I), "Gb/s")]


def _norm(text):
    for rx, rep in _FIXES:
        text = rx.sub(rep, text)
    return text


def _neg(s):
    return -abs(float(re.sub(r"[−–\s-]", "", s)))


def _vals(rxs, text, conv, lo, hi):
    """Every plausible value (rounded to 3 significant digits for comparison)."""
    out = {}
    for rx in rxs:
        for m in rx.finditer(text or ""):
            try:
                v = conv(m)
            except (ValueError, KeyError):
                continue
            if v is not None and lo <= v <= hi:
                out.setdefault(float("%.3g" % v), v)
    return set(out.values())


def _pick(t, a, cands, best=max):
    """The title's value if it states one, else the abstract's only value; nothing when the abstract lists several."""
    vt, va = cands(t), cands(a)
    if vt:
        return best(vt)
    if len(va) == 1:
        return va.pop()
    return None


def _rate(m):
    return float(m.group(2)) * _SI[m.group(3).upper()]


def parse_specs(title, abstract):
    t, a = _norm(title or ""), _norm(abstract or "")
    out = {}

    def put(k, v):
        if v is not None:
            out[k] = v
    put("rate", _pick(t, a, lambda x: _vals([RATE_RX], x, _rate, 1e8, 5e12)))
    put("eff", _pick(t, a, lambda x: _vals([EFF_RX], x, lambda m: float(m.group(1)) * _SI[m.group(2)] / 1e-12, 0.01, 1000)
                     | _vals([EFF_MW_RX], x, lambda m: float(m.group(1)), 0.01, 1000), best=min))
    put("loss", _pick(t, a, lambda x: _vals(LOSS_RX, x, lambda m: float(m.group(1)), 3, 80)))
    put("ber", _pick(t, a, lambda x: _vals([BER_RX], x, lambda m: -int(m.group(1) or m.group(2)), -20, -2), best=min))
    put("fsadc", _pick(t, a, lambda x: _vals([FSADC_RX], x, lambda m: float(m.group(1)) * _SI[m.group(2)], 1e8, 5e11)))
    put("resadc", _pick(t, a, lambda x: _vals([RESADC_RX], x, lambda m: int(m.group(1)), 2, 12)))
    put("node", _pick(t, a, lambda x: _vals([NODE_NM_RX], x, lambda m: int(m.group(1)), 2, 500)
                      or _vals([NODE_UM_RX], x, lambda m: int(round(float(m.group(1)) * 1000)), 10, 1000)))
    put("p", _pick(t, a, lambda x: _vals([POWER_TITLE_RX] if x is t else [POWER_CTX_RX, POWER_AFTER_RX], x,
                                         lambda m: float(m.group(1)) * _SI[m.group(2) or ""], 1e-6, 1e2)))
    put("area", _pick(t, a, lambda x: _vals([AREA_RX], x, lambda m: float(m.group(1)), 1e-4, 1e3)))
    return out


def spec_sources(title, abstract):
    """parse_specs() plus where each value came from: {"key": "t" | "a"}."""
    full = parse_specs(title, abstract)
    only_title = parse_specs(title, "")
    return full, {k: ("t" if only_title.get(k) == v else "a") for k, v in full.items()}


def derived(specs):
    """Energy efficiency P / data rate (pJ/b) when the paper does not state it."""
    if "eff" not in specs and specs.get("p") and specs.get("rate"):
        return {"eff_calc": round(specs["p"] / specs["rate"] / 1e-12, 4)}
    return {}


# ------------------------------------------------------------- affiliations and dates (same rules as adc-census)
ORG_HINT = re.compile(r"universit|institut|college|school|KAIST|POSTECH|UNIST|DGIST|GIST|\bETH\b|EPFL|\bMIT\b|"
                      r"laborator|\blabs?\b|inc\b|ltd|corp|company|co\.|electronics|semiconductor|technolog|"
                      r"research|centre|center|academy|imec|tsmc|samsung|sk hynix|intel|mediatek|qualcomm|"
                      r"apple|google|huawei|broadcom|analog devices|texas instruments|nvidia|\bamd\b|\bibm\b|microsoft", I)


def org_and_country(aff):
    if not aff:
        return None, None
    parts = [p.strip() for p in aff.split(",") if p.strip()]
    if not parts:
        return None, None
    country = re.sub(r"\s+\d[\d\- ]*$", "", parts[-1])
    if re.fullmatch(r"(korea|south korea|republic of korea|korea \(south\))", country, I):
        country = "South Korea"
    elif re.fullmatch(r"(usa|u\.s\.a\.|united states|united states of america|us)", country, I):
        country = "USA"
    elif re.fullmatch(r"(prc|p\.r\. china|people's republic of china)", country, I):
        country = "China"
    org = None
    for p in parts:
        if ORG_HINT.search(p) and not re.match(r"(department|dept|school of|faculty|division)\b", p, I):
            org = p
            break
    if org is None:
        org = parts[1] if len(parts) > 2 else parts[0]
    if len(country) > 30 or re.search(r"\d", country):
        country = None
    return org, country


MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def parse_month(pubdate, year):
    s = (pubdate or "").lower()
    m = re.match(r"((?:19|20)\d{2})-(\d{2})", s)     # ISO dates from Crossref/OpenAlex
    if m:
        return "%s-%s" % m.groups()
    years = re.findall(r"(?:19|20)\d{2}", s)
    y = years[-1] if years else (str(year) if year else None)
    mon = None
    for tok in re.findall(r"[a-z]{3,}", s):
        if tok[:3] in MONTHS:
            mon = MONTHS[tok[:3]]
            break
    if y and mon:
        return "%s-%02d" % (y, mon)
    return y or ""
