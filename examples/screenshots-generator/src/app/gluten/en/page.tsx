"use client";

import { useEffect, useRef, useState } from "react";
import { toPng } from "html-to-image";
import JSZip from "jszip";

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

const GREEN  = "#4CAF7D";
const RED    = "#D9534F";
const DARK   = "#1A1A1A";
const F      = "ui-rounded, -apple-system, system-ui, sans-serif";

const LABEL_TOP    = H * 0.045;
const HEADLINE_TOP = H * 0.07;
const TEXT_LR      = W * 0.08;

function Phone({ src, alt, style, objectPosition = "top" }: { src: string; alt: string; style?: React.CSSProperties; objectPosition?: string }) {
  return (
    <div style={{ position: "relative", aspectRatio: `${MK_W}/${MK_H}`, ...style }}>
      <img src="/mockup.png" alt="" style={{ display: "block", width: "100%", height: "100%" }} draggable={false} />
      <div style={{
        position: "absolute", zIndex: 10, overflow: "hidden",
        left: `${SC_L}%`, top: `${SC_T}%`, width: `${SC_W}%`, height: `${SC_H}%`,
        borderRadius: `${SC_RX}% / ${SC_RY}%`,
      }}>
        <img src={src} alt={alt} style={{ display: "block", width: "100%", height: "100%", objectFit: "cover", objectPosition }} draggable={false} />
      </div>
    </div>
  );
}

// ── SS1 — Hero ────────────────────────────────────────────────────────────────
function Slide1() {
  return (
    <div style={{ width: W, height: H, background: GREEN, position: "relative", overflow: "hidden", fontFamily: F }}>
      <div style={{ position: "absolute", top: HEADLINE_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <h1 style={{ fontSize: W * 0.11, fontWeight: 800, color: "#fff", lineHeight: 0.95, margin: 0 }}>
          Gluten-Free<br />Scanner. Know<br />before you eat.
        </h1>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: W * 0.022,
          background: "#fff", borderRadius: W * 0.028,
          padding: `${W * 0.022}px ${W * 0.036}px`,
          margin: `${W * 0.04}px 0 0`,
        }}>
          <span style={{ fontSize: W * 0.072, fontWeight: 900, color: GREEN, lineHeight: 1 }}>500,000+</span>
          <span style={{ fontSize: W * 0.038, fontWeight: 600, color: "rgba(0,0,0,0.5)", lineHeight: 1.2 }}>Products<br />checked</span>
        </div>
      </div>
      <Phone
        src="/screenshots/pringles-scan.png"
        alt="Scanner"
        style={{
          position: "absolute",
          bottom: 0,
          left: "50%",
          transform: "translateX(-50%) translateY(14%)",
          width: W * 0.82,
        }}
      />
      {/* Product card */}
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
        <div style={{
          width: W * 0.13, height: W * 0.13,
          borderRadius: W * 0.018, overflow: "hidden", flexShrink: 0, background: "#eee",
        }}>
          <img src="/screenshots/pringles.jpg" alt="Pringles" style={{ width: "100%", height: "100%", objectFit: "cover" }} draggable={false} />
        </div>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: W * 0.042, fontWeight: 700, color: DARK, margin: 0, lineHeight: 1.1 }}>Pringles Original</p>
          <p style={{ fontSize: W * 0.03, color: "rgba(0,0,0,0.4)", margin: `${W * 0.005}px 0 ${W * 0.01}px`, lineHeight: 1 }}>Pringles</p>
          <div style={{ display: "flex", alignItems: "baseline", gap: W * 0.006 }}>
            <span style={{ fontSize: W * 0.085, fontWeight: 900, color: RED, lineHeight: 1 }}>18</span>
            <span style={{ fontSize: W * 0.03, color: "rgba(0,0,0,0.4)", fontWeight: 500 }}>/100</span>
          </div>
          <div style={{
            display: "inline-block", marginTop: W * 0.01,
            border: `1.5px solid ${RED}`, borderRadius: W * 0.05,
            padding: `${W * 0.007}px ${W * 0.02}px`,
            fontSize: W * 0.028, color: RED, fontWeight: 600,
          }}>⚠ Contains Gluten</div>
        </div>
      </div>
    </div>
  );
}

// ── SS2 — How it works ────────────────────────────────────────────────────────
function Slide2() {
  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", position: "relative", overflow: "hidden", fontFamily: F }}>
      <div style={{ position: "absolute", top: HEADLINE_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <h1 style={{ fontSize: W * 0.11, fontWeight: 800, color: DARK, lineHeight: 0.95, margin: 0 }}>
          Set once.<br />Protected on<br />every scan.
        </h1>
        <p style={{ fontSize: W * 0.055, fontWeight: 500, color: "rgba(0,0,0,0.5)", margin: `${W * 0.035}px 0 0`, lineHeight: 1.35 }}>
          Personalized to your gluten intolerance.
        </p>
      </div>
      <Phone
        src="/screenshots/ss2-result-en.png"
        alt="Scan"
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

// ── SS3 — Hidden gluten warning ───────────────────────────────────────────────
function Slide3() {
  const flags: Array<{ type: "error" | "warning"; text: string; sub: string; badge?: string }> = [
    { type: "error",   text: "Heavily processed", badge: "NOVA 4", sub: "The body doesn't quite know what to do with it — daily exposure adds up." },
    { type: "error",   text: "Contains gluten",                    sub: "Listed in your allergens." },
    { type: "warning", text: "Pesticide-prone produce",            sub: "Foods in this category often carry pesticide residues — buying organic helps." },
    { type: "warning", text: "Likely raised with antibiotics",     sub: "Conventional meat is often raised with antibiotics — this affects the microbiome and through it your mood." },
  ];
  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", position: "relative", overflow: "hidden", fontFamily: F }}>
      <div style={{ position: "absolute", top: HEADLINE_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <h1 style={{ fontSize: W * 0.11, fontWeight: 800, color: DARK, lineHeight: 0.95, margin: 0 }}>
          Every<br />ingredient.<br />Gluten found.
        </h1>
        <p style={{ fontSize: W * 0.055, fontWeight: 500, color: "rgba(0,0,0,0.45)", margin: `${W * 0.035}px 0 0`, lineHeight: 1.35 }}>
          Even when it hides in the ingredients list.
        </p>
      </div>
      <Phone
        src="/screenshots/ss3-result-en.png"
        alt="Gluten result"
        objectPosition="top"
        style={{
          position: "absolute",
          bottom: 0,
          left: "50%",
          transform: "translateX(-50%) translateY(14%)",
          width: W * 0.82,
        }}
      />
      {/* Analyse widget */}
      <div style={{
        position: "absolute",
        bottom: H * 0.07,
        left: W * 0.06,
        right: W * 0.06,
        background: "#FFFFFF",
        borderRadius: W * 0.045,
        padding: `${W * 0.048}px`,
        boxShadow: "0 8px 36px rgba(0,0,0,0.20)",
        border: "1px solid rgba(0,0,0,0.06)",
        zIndex: 20,
      }}>
        <p style={{ fontSize: W * 0.056, fontWeight: 800, color: DARK, margin: `0 0 ${W * 0.034}px` }}>
          Analysis
        </p>
        <div style={{ display: "flex", flexDirection: "column" }}>
          {flags.map((f, i) => {
            const XSZ = W * 0.058;
            return (
              <div key={i} style={{
                display: "flex", alignItems: "flex-start", gap: W * 0.028,
                paddingTop: i === 0 ? 0 : W * 0.032,
                paddingBottom: i < flags.length - 1 ? W * 0.032 : 0,
                borderBottom: i < flags.length - 1 ? "1px solid rgba(0,0,0,0.07)" : "none",
              }}>
                <div style={{ width: XSZ, height: XSZ, flexShrink: 0, marginTop: W * 0.003 }}>
                  {f.type === "error" ? (
                    <svg width={XSZ} height={XSZ} viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="11" fill={RED} />
                      <path d="M12 7.5v5" stroke="#fff" strokeWidth="2.4" strokeLinecap="round"/>
                      <circle cx="12" cy="16" r="1.2" fill="#fff"/>
                    </svg>
                  ) : (
                    <svg width={XSZ} height={XSZ} viewBox="0 0 24 24" fill="none">
                      <path d="M12 2.5L1.5 21h21L12 2.5z" fill="#E8872A"/>
                      <path d="M12 9.5v5" stroke="#fff" strokeWidth="2.2" strokeLinecap="round"/>
                      <circle cx="12" cy="17.5" r="1.1" fill="#fff"/>
                    </svg>
                  )}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: W * 0.016, flexWrap: "wrap", marginBottom: W * 0.008 }}>
                    <span style={{ fontSize: W * 0.044, fontWeight: 700, color: DARK, lineHeight: 1.2 }}>{f.text}</span>
                    {f.badge && (
                      <div style={{ background: "rgba(217,83,79,0.1)", borderRadius: W * 0.016, padding: `${W * 0.005}px ${W * 0.016}px` }}>
                        <span style={{ fontSize: W * 0.03, fontWeight: 700, color: RED }}>{f.badge}</span>
                      </div>
                    )}
                  </div>
                  <p style={{ fontSize: W * 0.036, color: "rgba(0,0,0,0.5)", margin: 0, lineHeight: 1.35 }}>{f.sub}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── SS4 — Personalization ─────────────────────────────────────────────────────
function Slide4() {
  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", position: "relative", overflow: "hidden", fontFamily: F }}>
      <div style={{ position: "absolute", top: HEADLINE_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <h1 style={{ fontSize: W * 0.11, fontWeight: 800, color: DARK, lineHeight: 0.95, margin: 0 }}>
          All your<br />needs.<br />One profile.
        </h1>
        <p style={{ fontSize: W * 0.055, fontWeight: 500, color: "rgba(0,0,0,0.5)", margin: `${W * 0.035}px 0 0`, lineHeight: 1.35 }}>
          Choose diets and allergens —<br />every scan gets personalized.
        </p>
      </div>
      <Phone
        src="/screenshots/ss4-allergens-en.png"
        alt="Profile"
        objectPosition="top"
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

// ── SS5 — Database ────────────────────────────────────────────────────────────
function Slide5() {
  const rows = [
    { num: "100+",        label: "verified gluten ingredients" },
    { num: "US · UK · CA", label: "products fully covered" },
    { num: "Daily",       label: "new products added" },
  ];
  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", position: "relative", overflow: "hidden", fontFamily: F }}>
      <div style={{ position: "absolute", top: HEADLINE_TOP, left: TEXT_LR, right: TEXT_LR }}>
        <div style={{ marginBottom: W * 0.01 }}>
          <span style={{ fontSize: W * 0.18, fontWeight: 900, color: DARK, lineHeight: 0.9, display: "block" }}>500,000+</span>
          <span style={{ fontSize: W * 0.072, fontWeight: 800, color: DARK, lineHeight: 1, display: "block" }}>Products checked.</span>
        </div>
        <p style={{ fontSize: W * 0.055, fontWeight: 500, color: "rgba(0,0,0,0.45)", margin: `${W * 0.04}px 0 ${W * 0.06}px`, lineHeight: 1.35 }}>
          So you always know<br />what you eat.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: W * 0.026 }}>
          {rows.map((r, i) => (
            <div key={i} style={{
              background: "rgba(0,0,0,0.04)", borderRadius: W * 0.028,
              padding: `${W * 0.036}px ${W * 0.04}px`,
              display: "flex", alignItems: "center", gap: W * 0.032,
            }}>
              <span style={{ fontSize: W * 0.052, fontWeight: 900, color: GREEN, flexShrink: 0, minWidth: W * 0.22 }}>{r.num}</span>
              <span style={{ fontSize: W * 0.042, fontWeight: 500, color: "rgba(0,0,0,0.6)", lineHeight: 1.3 }}>{r.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── SS6 — CTA ─────────────────────────────────────────────────────────────────
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
          <svg width={W * 0.1} height={W * 0.1} viewBox="0 0 48 48" fill="none">
            <path d="M10 25l10 10 18-20" stroke="#fff" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span style={{ fontSize: W * 0.048, fontWeight: 900, color: "#fff", lineHeight: 1.2, textAlign: "center" }}>Gluten{"\n"}Free</span>
        </div>
      </div>
      <div style={{ textAlign: "center", padding: `0 ${W * 0.08}px` }}>
        <h1 style={{ fontSize: W * 0.12, fontWeight: 800, color: "#fff", lineHeight: 0.95, margin: 0 }}>
          Scan. Check.<br />Eat gluten-free.
        </h1>
        <p style={{ fontSize: W * 0.072, fontWeight: 500, color: "rgba(255,255,255,0.6)", margin: `${W * 0.04}px 0 0`, lineHeight: 1.4 }}>
          Simple. Safe. Accurate.<br />100+ ingredients detected.
        </p>
      </div>
    </div>
  );
}

// ── Registry ──────────────────────────────────────────────────────────────────
const SCREENSHOTS = [
  { id: "g1", label: "Hero",     component: Slide1 },
  { id: "g2", label: "How",      component: Slide2 },
  { id: "g3", label: "Analysis", component: Slide3 },
  { id: "g4", label: "Profile",  component: Slide4 },
  { id: "g5", label: "Database", component: Slide5 },
  { id: "g6", label: "CTA",      component: Slide6 },
];

function getSlideBg(Cmp: React.ComponentType): string {
  if (Cmp === Slide1 || Cmp === Slide6) return GREEN;
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

export default function GlutenEnPage() {
  const [exporting, setExporting] = useState<string | null>(null);
  const [device, setDevice] = useState<DeviceMode>("iphone");
  const offRefsIphone = useRef<Record<string, HTMLDivElement | null>>({});
  const offRefsIpad   = useRef<Record<string, HTMLDivElement | null>>({});

  const isIPad = device === "ipad";
  const canvasW = isIPad ? W_IPAD : W;
  const canvasH = isIPad ? H_IPAD : H;

  async function renderToBlobs(
    id: string,
    el: HTMLDivElement,
    deviceLabel: "iphone" | "ipad",
    sizes: ReadonlyArray<{ label: string; w: number; h: number }>,
    cW: number,
    cH: number,
  ): Promise<Array<{ filename: string; blob: Blob }>> {
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

    const idx = SCREENSHOTS.findIndex(s => s.id === id);
    const slideLabel = SCREENSHOTS[idx].label.toLowerCase();
    const slideNum   = String(idx + 1).padStart(2, "0");
    const results: Array<{ filename: string; blob: Blob }> = [];

    for (const size of sizes) {
      const opts = { width: cW, height: cH, pixelRatio: size.w / cW, cacheBust: true };
      await toPng(el, opts);
      await new Promise(r => setTimeout(r, 200));
      await toPng(el, opts);
      await new Promise(r => setTimeout(r, 200));
      const url = await toPng(el, opts);

      const img = new window.Image();
      await new Promise<void>(r => { img.onload = () => r(); img.src = url; });
      const cv = document.createElement("canvas");
      cv.width = size.w; cv.height = size.h;
      cv.getContext("2d")!.drawImage(img, 0, 0, size.w, size.h);

      const blob = await new Promise<Blob>(res => cv.toBlob(b => res(b!), "image/png"));
      results.push({ filename: `${deviceLabel}-en-${slideNum}-${slideLabel}-${size.w}x${size.h}.png`, blob });
      await new Promise(r => setTimeout(r, 200));
    }

    el.style.left = "-9999px";
    el.style.opacity = "";
    el.style.zIndex = "";
    return results;
  }

  async function exportOne(id: string) {
    const refs = isIPad ? offRefsIpad : offRefsIphone;
    const sizes = isIPad ? IPAD_SIZES : PHONE_SIZES;
    const el = refs.current[id];
    if (!el) return;
    setExporting(id);
    try {
      const blobs = await renderToBlobs(id, el, isIPad ? "ipad" : "iphone", sizes, isIPad ? W_IPAD : W, isIPad ? H_IPAD : H);
      for (const { filename, blob } of blobs) {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
        await new Promise(r => setTimeout(r, 400));
      }
    } finally {
      setExporting(null);
    }
  }

  async function exportAll() {
    setExporting("all");
    try {
      const zip = new JSZip();
      const iphoneFolder = zip.folder("iphone")!;
      const ipadFolder   = zip.folder("ipad")!;

      for (const s of SCREENSHOTS) {
        const iphoneEl = offRefsIphone.current[s.id];
        const ipadEl   = offRefsIpad.current[s.id];
        if (iphoneEl) {
          const blobs = await renderToBlobs(s.id, iphoneEl, "iphone", PHONE_SIZES, W, H);
          blobs.forEach(({ filename, blob }) => iphoneFolder.file(filename, blob));
        }
        if (ipadEl) {
          const blobs = await renderToBlobs(s.id, ipadEl, "ipad", IPAD_SIZES, W_IPAD, H_IPAD);
          blobs.forEach(({ filename, blob }) => ipadFolder.file(filename, blob));
        }
      }

      const zipBlob = await zip.generateAsync({ type: "blob", compression: "DEFLATE", compressionOptions: { level: 1 } });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(zipBlob);
      a.download = `gluten-en-${new Date().toISOString().slice(0, 10)}.zip`;
      a.click();
    } finally {
      setExporting(null);
    }
  }

  const tabStyle = (active: boolean): React.CSSProperties => ({
    background: active ? GREEN : "transparent",
    color: active ? "#fff" : "#888",
    border: active ? "none" : "1px solid #444",
    borderRadius: 8, padding: "7px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer",
  });

  return (
    <div style={{ minHeight: "100vh", background: "#111", padding: "32px 24px", fontFamily: F }}>
      <div style={{ maxWidth: 1440, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: "#fff", margin: "0 0 3px" }}>
              Gluten — EN
            </h1>
            <p style={{ fontSize: 12, color: "#666", margin: 0 }}>
              {SCREENSHOTS.length} slides · {device === "ipad" ? "iPad" : "iPhone"} · click to export
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <a href="/" style={{ fontSize: 12, color: "#666", textDecoration: "none", marginRight: 12 }}>← Hub</a>
            <a href="/gluten/de" style={{ fontSize: 12, color: "#888", textDecoration: "none" }}>DE</a>
            <a href="/gluten/en" style={{ fontSize: 12, color: "#fff", fontWeight: 600, textDecoration: "none", background: GREEN, borderRadius: 6, padding: "4px 10px" }}>EN</a>
            <button onClick={() => setDevice("iphone")} style={tabStyle(device === "iphone")}>iPhone</button>
            <button onClick={() => setDevice("ipad")} style={tabStyle(device === "ipad")}>iPad</button>
            <button onClick={exportAll} disabled={!!exporting}
              style={{ background: exporting ? "#333" : GREEN, color: "#fff", border: "none", borderRadius: 8, padding: "9px 20px", fontSize: 13, fontWeight: 600, cursor: exporting ? "not-allowed" : "pointer", marginLeft: 8 }}>
              {exporting === "all" ? "Packing zip…" : exporting ? `${exporting}…` : "Export All"}
            </button>
          </div>
        </div>
        <div key={device} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 20 }}>
          {SCREENSHOTS.map(({ id, label, component: Cmp }) => (
            <Preview key={id} id={id} label={label} Cmp={Cmp} onExport={exportOne} device={device} />
          ))}
        </div>
      </div>
      {/* iPhone off-screen renders */}
      <div style={{ position: "absolute", top: 0, overflow: "hidden" }}>
        {SCREENSHOTS.map(({ id, component: Cmp }) => (
          <div key={`iphone-${id}`} ref={el => { offRefsIphone.current[id] = el; }}
            style={{ position: "absolute", left: "-9999px", top: 0, width: W, height: H, fontFamily: F }}>
            <Cmp />
          </div>
        ))}
      </div>
      {/* iPad off-screen renders */}
      <div style={{ position: "absolute", top: 0, overflow: "hidden" }}>
        {SCREENSHOTS.map(({ id, component: Cmp }) => (
          <div key={`ipad-${id}`} ref={el => { offRefsIpad.current[id] = el; }}
            style={{ position: "absolute", left: "-9999px", top: 0, width: W_IPAD, height: H_IPAD, fontFamily: F }}>
            <div style={{ width: W_IPAD, height: H_IPAD, background: getSlideBg(Cmp), display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ transform: `scale(${IPAD_SCALE})`, transformOrigin: "center center", width: W, height: H }}>
                <Cmp />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
