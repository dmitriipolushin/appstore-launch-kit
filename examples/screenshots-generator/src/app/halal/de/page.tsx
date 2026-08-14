"use client";

import { useEffect, useRef, useState } from "react";
import { toPng } from "html-to-image";

const W_PHONE = 1320;
const H_PHONE = 2868;
const PHONE_SIZES = [
  { label: '6.7"', w: 1284, h: 2778 },
  { label: '6.5"', w: 1242, h: 2688 },
] as const;

const W_IPAD = 2048;
const H_IPAD = 2732;
const IPAD_SIZES = [
  { label: '13"', w: 2048, h: 2732 },
  { label: '11"', w: 1668, h: 2388 },
] as const;

type DeviceMode = "iphone" | "ipad";

const W = W_PHONE;
const H = H_PHONE;

const IPAD_SCALE = Math.min(W_IPAD / W_PHONE, H_IPAD / H_PHONE);

const MK_W = 1022;
const MK_H = 2082;
const SC_L = (52 / MK_W) * 100;
const SC_T = (46 / MK_H) * 100;
const SC_W = (918 / MK_W) * 100;
const SC_H = (1990 / MK_H) * 100;
const SC_RX = (126 / 918) * 100;
const SC_RY = (126 / 1990) * 100;

const GREEN = "#4CAF7D";
const RED = "#D9534F";
const DARK = "#1A1A1A";
const F = "ui-rounded, -apple-system, system-ui, sans-serif";

const LABEL_TOP = H * 0.045;
const HEADLINE_TOP = H * 0.09;
const TEXT_LR = W * 0.08;

function Phone({ src, alt, style }: { src: string; alt: string; style?: React.CSSProperties }) {
  return (
    <div style={{ position: "relative", aspectRatio: `${MK_W}/${MK_H}`, ...style }}>
      <img src="/mockup.png" alt="" style={{ display: "block", width: "100%", height: "100%" }} draggable={false} />
      <div style={{
        position: "absolute", zIndex: 10, overflow: "hidden",
        left: `${SC_L}%`, top: `${SC_T}%`, width: `${SC_W}%`, height: `${SC_H}%`,
        borderRadius: `${SC_RX}% / ${SC_RY}%`,
      }}>
        <img src={src} alt={alt} style={{ display: "block", width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }} draggable={false} />
      </div>
    </div>
  );
}

// ── SS1 — Hero ───────────────────────────────────────────────────────────────
function Slide1() {
  return (
    <div style={{ width: W, height: H, background: GREEN, position: "relative", overflow: "hidden", fontFamily: F }}>
      <div style={{ position: "absolute", top: LABEL_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <p style={{ fontSize: W * 0.038, fontWeight: 700, color: "rgba(255,255,255,0.7)", letterSpacing: "0.08em", textTransform: "uppercase", margin: 0 }}>
          Halal Scanner
        </p>
      </div>
      <div style={{ position: "absolute", top: HEADLINE_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <h1 style={{ fontSize: W * 0.11, fontWeight: 800, color: "#fff", lineHeight: 0.95, margin: 0 }}>
          Ist das<br />wirklich<br />Halal?
        </h1>
        <p style={{ fontSize: W * 0.055, fontWeight: 500, color: "rgba(255,255,255,0.65)", margin: `${W * 0.035}px 0 0`, lineHeight: 1.35 }}>
          Barcode scannen. Halal-Status sofort.
        </p>
      </div>
      <Phone
        src="/screenshots/halal-ss1.png"
        alt="Scanner"
        style={{
          position: "absolute",
          bottom: 0,
          left: "50%",
          transform: "translateX(-50%) translateY(14%)",
          width: W * 0.82,
        }}
      />
      {/* Product card overlay — same style as main/Nutella card */}
      <div style={{
        position: "absolute",
        bottom: H * 0.42,
        left: "50%",
        transform: "translateX(-50%)",
        width: W * 0.56,
        background: "#FDF8F3",
        borderRadius: W * 0.038,
        padding: `${W * 0.038}px`,
        display: "flex",
        alignItems: "center",
        gap: W * 0.028,
        boxShadow: "0 12px 40px rgba(0,0,0,0.22)",
        zIndex: 20,
      }}>
        {/* Thumbnail */}
        <div style={{
          width: W * 0.13,
          height: W * 0.13,
          borderRadius: W * 0.018,
          overflow: "hidden",
          flexShrink: 0,
          background: "#eee",
        }}>
          <img src="/screenshots/halal-ss1.png" alt="Haribo" style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "50% 50%" }} draggable={false} />
        </div>
        {/* Info */}
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: W * 0.042, fontWeight: 700, color: DARK, margin: 0, lineHeight: 1.1 }}>Haribo Goldbären</p>
          <p style={{ fontSize: W * 0.03, color: "rgba(0,0,0,0.4)", margin: `${W * 0.005}px 0 ${W * 0.01}px`, lineHeight: 1 }}>Haribo</p>
          <div style={{ display: "flex", alignItems: "baseline", gap: W * 0.006 }}>
            <span style={{ fontSize: W * 0.085, fontWeight: 900, color: RED, lineHeight: 1 }}>5</span>
            <span style={{ fontSize: W * 0.03, color: "rgba(0,0,0,0.4)", fontWeight: 500 }}>/100</span>
          </div>
          <div style={{
            display: "inline-block",
            marginTop: W * 0.01,
            border: `1.5px solid ${RED}`,
            borderRadius: W * 0.05,
            padding: `${W * 0.007}px ${W * 0.02}px`,
            fontSize: W * 0.028,
            color: RED,
            fontWeight: 600,
          }}>Nicht Halal</div>
        </div>
      </div>
    </div>
  );
}

// ── SS2 — Stat ───────────────────────────────────────────────────────────────
function Slide2() {
  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", position: "relative", overflow: "hidden", fontFamily: F }}>
      <div style={{ position: "absolute", top: LABEL_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <p style={{ fontSize: W * 0.038, fontWeight: 700, color: GREEN, letterSpacing: "0.08em", textTransform: "uppercase", margin: 0 }}>
          Halal bestätigt
        </p>
      </div>
      <div style={{ position: "absolute", top: HEADLINE_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <h1 style={{ fontSize: W * 0.11, fontWeight: 800, color: DARK, lineHeight: 0.95, margin: 0 }}>
          Kein Zweifel<br />mehr.<br />Halal erkannt.
        </h1>
        <p style={{ fontSize: W * 0.055, fontWeight: 500, color: "rgba(0,0,0,0.5)", margin: `${W * 0.035}px 0 0`, lineHeight: 1.35 }}>
          NOVA 1 · Keine Gelatine · 95/100
        </p>
      </div>
      <Phone
        src="/screenshots/halal-fage.png"
        alt="Result"
        style={{
          position: "absolute",
          bottom: 0,
          left: "50%",
          transform: "translateX(-50%) translateY(14%)",
          width: W * 0.82,
        }}
      />
    </div>
  );
}

// ── SS3 — Scan Result ────────────────────────────────────────────────────────
function Slide3() {
  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", position: "relative", overflow: "hidden", fontFamily: F }}>
      <div style={{ position: "absolute", top: LABEL_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: W * 0.012,
          background: "rgba(217,83,79,0.1)", border: `1px solid rgba(217,83,79,0.3)`,
          borderRadius: W * 0.016, padding: `${W * 0.01}px ${W * 0.022}px`,
        }}>
          <span style={{ fontSize: W * 0.035 }}>❌</span>
          <span style={{ fontSize: W * 0.03, fontWeight: 600, color: RED, letterSpacing: "0.06em", textTransform: "uppercase" }}>Haram-Warnung</span>
        </div>
      </div>
      <div style={{ position: "absolute", top: HEADLINE_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <h1 style={{ fontSize: W * 0.1, fontWeight: 800, color: DARK, lineHeight: 0.95, margin: 0 }}>
          Nicht Halal.<br />Versteckte<br />Zutaten<br />gefunden.
        </h1>
        <p style={{ fontSize: W * 0.053, fontWeight: 500, color: "rgba(0,0,0,0.45)", margin: `${W * 0.035}px 0 0`, lineHeight: 1.35 }}>
          Sofort sichtbar. Immer erklärt.
        </p>
      </div>
      <Phone
        src="/screenshots/halal-ss3.png"
        alt="Scan Result"
        style={{
          position: "absolute",
          bottom: 0,
          left: "50%",
          transform: "translateX(-50%) translateY(14%)",
          width: W * 0.82,
        }}
      />
    </div>
  );
}

// ── SS4 — What we check ──────────────────────────────────────────────────────
function Slide4() {
  const items = [
    { dot: "🔴", title: "Gelatine (Schwein)", desc: "In Gummis, Joghurt, Desserts & Kapseln" },
    { dot: "🔴", title: "E120 (Karmin)", desc: "Tierischer Farbstoff — aus Insekten" },
    { dot: "🔴", title: "Alkohol in Aromen", desc: 'Oft nur als \u201eAroma\u201c deklariert' },
    { dot: "🟡", title: "E471 — Emulgator", desc: "Tierisch oder pflanzlich? Wir klären es." },
  ];
  return (
    <div style={{ width: W, height: H, background: GREEN, position: "relative", overflow: "hidden", fontFamily: F }}>
      <div style={{ position: "absolute", top: LABEL_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <p style={{ fontSize: W * 0.038, fontWeight: 700, color: "rgba(255,255,255,0.7)", letterSpacing: "0.08em", textTransform: "uppercase", margin: 0 }}>
          Halal-Schutz
        </p>
      </div>
      <div style={{ position: "absolute", top: HEADLINE_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <h1 style={{ fontSize: W * 0.1, fontWeight: 800, color: "#fff", lineHeight: 0.95, margin: 0 }}>
          Wir prüfen<br />was kein<br />Label zeigt.
        </h1>
        <p style={{ fontSize: W * 0.052, fontWeight: 500, color: "rgba(255,255,255,0.65)", margin: `${W * 0.032}px 0 ${W * 0.052}px`, lineHeight: 1.35 }}>
          Automatisch. Bei jedem Scan.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: W * 0.026 }}>
          {items.map((item, i) => (
            <div key={i} style={{
              background: "rgba(255,255,255,0.15)", borderRadius: W * 0.028,
              padding: `${W * 0.036}px ${W * 0.032}px`, display: "flex", alignItems: "flex-start", gap: W * 0.022,
            }}>
              <span style={{ fontSize: W * 0.048, marginTop: 2, flexShrink: 0 }}>{item.dot}</span>
              <div>
                <p style={{ fontSize: W * 0.05, fontWeight: 700, color: "#fff", margin: 0 }}>{item.title}</p>
                <p style={{ fontSize: W * 0.041, color: "rgba(255,255,255,0.8)", margin: `${W * 0.01}px 0 0`, lineHeight: 1.35 }}>{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── SS5 — Social Proof ───────────────────────────────────────────────────────
function Slide5() {
  const reviews = [
    { name: "Fatima K., München", text: "Endlich weiß ich sofort, ob ein Produkt wirklich halal ist. Unverzichtbar beim Einkaufen!" },
    { name: "Aicha B., Hamburg", text: "Als Mutter möchte ich sicher sein. Diese App gibt mir die Sicherheit, die ich brauche." },
    { name: "Yusuf A., Berlin", text: "Ich scanne alles — Gummibärchen, Joghurt, Wurst. Haram-Zutaten werden sofort erkannt." },
  ];
  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", position: "relative", overflow: "hidden", fontFamily: F }}>
      <div style={{ position: "absolute", top: LABEL_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <p style={{ fontSize: W * 0.038, fontWeight: 700, color: GREEN, letterSpacing: "0.08em", textTransform: "uppercase", margin: 0 }}>
          Nutzerstimmen
        </p>
      </div>
      <div style={{ position: "absolute", top: HEADLINE_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <h1 style={{ fontSize: W * 0.1, fontWeight: 800, color: DARK, lineHeight: 0.95, margin: 0 }}>
          Tausende<br />Muslime<br />vertrauen uns.
        </h1>
        {/* Rating row */}
        <div style={{ display: "flex", alignItems: "center", gap: W * 0.025, margin: `${W * 0.04}px 0 ${W * 0.055}px` }}>
          <div style={{
            display: "flex", alignItems: "center", gap: W * 0.014,
            background: GREEN, borderRadius: W * 0.022,
            padding: `${W * 0.018}px ${W * 0.032}px`,
          }}>
            <span style={{ fontSize: W * 0.05, lineHeight: 1 }}>⭐</span>
            <span style={{ fontSize: W * 0.058, fontWeight: 900, color: "#fff", lineHeight: 1 }}>4.8</span>
          </div>
          <div>
            <p style={{ fontSize: W * 0.036, fontWeight: 700, color: DARK, margin: 0 }}>App Store</p>
            <p style={{ fontSize: W * 0.03, color: "rgba(0,0,0,0.4)", margin: `${W * 0.005}px 0 0` }}>2.400+ Bewertungen</p>
          </div>
        </div>
        {/* Review cards */}
        <div style={{ display: "flex", flexDirection: "column", gap: W * 0.03 }}>
          {reviews.map((r, i) => (
            <div key={i} style={{
              background: "rgba(0,0,0,0.04)", borderRadius: W * 0.028,
              padding: `${W * 0.038}px ${W * 0.04}px`,
            }}>
              <div style={{ display: "flex", gap: W * 0.008, marginBottom: W * 0.014 }}>
                {[0,1,2,3,4].map(s => (
                  <span key={s} style={{ fontSize: W * 0.033, lineHeight: 1 }}>⭐</span>
                ))}
              </div>
              <p style={{ fontSize: W * 0.038, color: DARK, margin: `0 0 ${W * 0.012}px`, lineHeight: 1.4, fontWeight: 500 }}>„{r.text}"</p>
              <p style={{ fontSize: W * 0.03, color: "rgba(0,0,0,0.4)", margin: 0, fontWeight: 600 }}>— {r.name}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── SS6 — CTA ────────────────────────────────────────────────────────────────
function Slide6() {
  const bars = [3, 2, 5, 1, 3, 2, 4, 1, 6, 2, 3, 1, 4, 3, 2, 5, 1, 4, 2, 3, 4, 1, 3, 2];
  return (
    <div style={{ width: W, height: H, background: GREEN, fontFamily: F, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: W * 0.055, marginBottom: H * 0.07 }}>
        <div style={{
          background: "rgba(255,255,255,0.15)", borderRadius: W * 0.025,
          padding: `${W * 0.03}px ${W * 0.05}px`,
          display: "flex", flexDirection: "column", alignItems: "center", gap: W * 0.012,
        }}>
          <div style={{ display: "flex", gap: 3, height: W * 0.09, alignItems: "stretch" }}>
            {bars.map((w, i) => (
              <div key={i} style={{ width: w * 2.5, background: i % 2 === 0 ? "rgba(255,255,255,0.85)" : "transparent", borderRadius: 1 }} />
            ))}
          </div>
          <span style={{ fontSize: W * 0.018, color: "rgba(255,255,255,0.4)", letterSpacing: "0.12em" }}>4 388844 901017</span>
        </div>
        <svg width={W * 0.05} height={W * 0.05} viewBox="0 0 40 40" fill="none">
          <path d="M20 4v28M8 20l12 12 12-12" stroke="#fff" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <div style={{
          width: W * 0.38, height: W * 0.38, borderRadius: "50%",
          background: "rgba(255,255,255,0.15)", border: `${W * 0.006}px solid rgba(255,255,255,0.6)`,
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: W * 0.01,
        }}>
          <span style={{ fontSize: W * 0.1, lineHeight: 1 }}>✅</span>
          <span style={{ fontSize: W * 0.055, fontWeight: 900, color: "#fff", lineHeight: 1 }}>Halal</span>
        </div>
      </div>
      <div style={{ textAlign: "center", padding: `0 ${W * 0.08}px` }}>
        <h1 style={{ fontSize: W * 0.12, fontWeight: 800, color: "#fff", lineHeight: 0.95, margin: 0 }}>
          Scan. Prüf.<br />Iss Halal.
        </h1>
        <p style={{ fontSize: W * 0.055, fontWeight: 500, color: "rgba(255,255,255,0.6)", margin: `${W * 0.04}px 0 0`, lineHeight: 1.35 }}>
          Einfach. Sicher. Richtig.
        </p>
      </div>
    </div>
  );
}

// ── Registry ─────────────────────────────────────────────────────────────────
const SCREENSHOTS = [
  { id: "h1", label: "Hero",    component: Slide1 },
  { id: "h2", label: "Stat",    component: Slide2 },
  { id: "h3", label: "Result",  component: Slide3 },
  { id: "h4", label: "Check",   component: Slide4 },
  { id: "h5", label: "Reviews", component: Slide5 },
  { id: "h6", label: "CTA",     component: Slide6 },
];

function getSlideBg(Cmp: React.ComponentType): string {
  if (Cmp === Slide1 || Cmp === Slide4 || Cmp === Slide6) return GREEN;
  return "#FFFFFF";
}

function Preview({ id, label, Cmp, onExport, device }: {
  id: string; label: string; Cmp: React.ComponentType; onExport: (id: string) => void; device: DeviceMode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const isIPad = device === "ipad";
  const canvasW = isIPad ? W_IPAD : W;
  const canvasH = isIPad ? H_IPAD : H;

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(() => { if (ref.current) setScale(ref.current.getBoundingClientRect().width / canvasW); });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, [canvasW]);

  const inner = isIPad ? (
    <div style={{ width: W_IPAD, height: H_IPAD, background: getSlideBg(Cmp), display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ transform: `scale(${IPAD_SCALE})`, transformOrigin: "center center", width: W, height: H }}>
        <Cmp />
      </div>
    </div>
  ) : (
    <div style={{ width: W, height: H }}><Cmp /></div>
  );

  return (
    <div>
      <div ref={ref} onClick={() => onExport(id)} title="Click to export"
        style={{ width: "100%", aspectRatio: `${canvasW}/${canvasH}`, overflow: "hidden", borderRadius: 10, cursor: "pointer", border: "1px solid rgba(255,255,255,0.1)" }}>
        <div style={{ transform: `scale(${scale})`, transformOrigin: "top left", width: canvasW, height: canvasH }}>
          {inner}
        </div>
      </div>
      <p style={{ textAlign: "center", fontSize: 12, color: "#888", margin: "7px 0 0" }}>
        {SCREENSHOTS.findIndex(s => s.id === id) + 1}. {label}
      </p>
    </div>
  );
}

export default function HalalPage() {
  const [exporting, setExporting] = useState<string | null>(null);
  const [device, setDevice] = useState<DeviceMode>("iphone");
  const offRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const isIPad = device === "ipad";
  const SIZES = isIPad ? IPAD_SIZES : PHONE_SIZES;
  const canvasW = isIPad ? W_IPAD : W;
  const canvasH = isIPad ? H_IPAD : H;

  async function exportOne(id: string) {
    const el = offRefs.current[id];
    if (!el) return;
    setExporting(id);
    try {
      el.style.left = "0px";
      el.style.opacity = "1";
      el.style.zIndex = "-1";

      const imgs = el.querySelectorAll("img");
      await Promise.all(
        Array.from(imgs).map(img =>
          img.complete ? Promise.resolve() : new Promise<void>(r => { img.onload = () => r(); img.onerror = () => r(); })
        )
      );
      await new Promise(r => setTimeout(r, 500));

      for (const size of SIZES) {
        const opts = { width: canvasW, height: canvasH, pixelRatio: size.w / canvasW, cacheBust: true };
        await toPng(el, opts);
        await new Promise(r => setTimeout(r, 200));
        await toPng(el, opts);
        await new Promise(r => setTimeout(r, 200));
        const url = await toPng(el, opts);

        const img = new window.Image();
        await new Promise<void>(r => { img.onload = () => r(); img.src = url; });
        const cv = document.createElement("canvas");
        cv.width = size.w;
        cv.height = size.h;
        cv.getContext("2d")!.drawImage(img, 0, 0, size.w, size.h);
        const idx = SCREENSHOTS.findIndex(s => s.id === id);
        const a = document.createElement("a");
        a.href = cv.toDataURL("image/png");
        const prefix = device === "ipad" ? "ipad" : "iphone";
        a.download = `halal-${prefix}-${String(idx + 1).padStart(2, "0")}-${SCREENSHOTS[idx].label.toLowerCase()}-${size.w}x${size.h}.png`;
        a.click();
        await new Promise(r => setTimeout(r, 400));
      }

      el.style.left = "-9999px";
      el.style.opacity = "";
      el.style.zIndex = "";
    } finally {
      setExporting(null);
    }
  }

  async function exportAll() {
    for (const s of SCREENSHOTS) { await exportOne(s.id); await new Promise(r => setTimeout(r, 500)); }
  }

  const tabStyle = (active: boolean): React.CSSProperties => ({
    background: active ? GREEN : "transparent",
    color: active ? "#fff" : "#888",
    border: active ? "none" : "1px solid #444",
    borderRadius: 8,
    padding: "7px 18px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
  });

  return (
    <div style={{ minHeight: "100vh", background: "#111", padding: "32px 24px", fontFamily: F }}>
      <div style={{ maxWidth: 1440, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: "#fff", margin: "0 0 3px" }}>
              Halal — DE
            </h1>
            <p style={{ fontSize: 12, color: "#666", margin: 0 }}>
              {SCREENSHOTS.length} slides · {device === "ipad" ? "iPad" : "iPhone"} · click to export
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <a href="/" style={{ fontSize: 12, color: "#666", textDecoration: "none", marginRight: 12 }}>← Hub</a>
            <button onClick={() => setDevice("iphone")} style={tabStyle(device === "iphone")}>iPhone</button>
            <button onClick={() => setDevice("ipad")} style={tabStyle(device === "ipad")}>iPad</button>
            <button onClick={exportAll} disabled={!!exporting}
              style={{ background: exporting ? "#333" : GREEN, color: "#fff", border: "none", borderRadius: 8, padding: "9px 20px", fontSize: 13, fontWeight: 600, cursor: exporting ? "not-allowed" : "pointer", marginLeft: 8 }}>
              {exporting ? `${exporting}…` : "Export All"}
            </button>
          </div>
        </div>
        <div key={device} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 20 }}>
          {SCREENSHOTS.map(({ id, label, component: Cmp }) => (
            <Preview key={id} id={id} label={label} Cmp={Cmp} onExport={exportOne} device={device} />
          ))}
        </div>
      </div>
      <div style={{ position: "absolute", top: 0, overflow: "hidden" }}>
        {SCREENSHOTS.map(({ id, component: Cmp }) => (
          <div key={`${device}-${id}`} ref={el => { offRefs.current[id] = el; }}
            style={{ position: "absolute", left: "-9999px", top: 0, width: canvasW, height: canvasH, fontFamily: F }}>
            {isIPad ? (
              <div style={{ width: W_IPAD, height: H_IPAD, background: getSlideBg(Cmp), display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ transform: `scale(${IPAD_SCALE})`, transformOrigin: "center center", width: W, height: H }}>
                  <Cmp />
                </div>
              </div>
            ) : (
              <Cmp />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
