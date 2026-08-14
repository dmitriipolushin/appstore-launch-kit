"use client";

import React, { useContext, useEffect, useRef, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { toPng } from "html-to-image";
import JSZip from "jszip";

const W_PHONE = 1320;
const H_PHONE = 2868;
const PHONE_SIZES = [
  { label: '6.7"', w: 1284, h: 2778 },
] as const;

const W_IPAD = 2048;
const H_IPAD = 2732;
const IPAD_SIZES = [
  { label: '13"', w: 2048, h: 2732 },
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
const ORANGE = "#E8872A";
const DARK   = "#1A1A1A";
const F      = "ui-rounded, -apple-system, system-ui, sans-serif";

const LABEL_TOP   = H * 0.045;
const HEADLINE_TOP = H * 0.09;
const TEXT_LR     = W * 0.08;

// ── Translations ──────────────────────────────────────────────────────────────
type T = {
  s1: {
    h: string[]; sub: string[];
    productName: string; productBrand: string;
    ingredients: string; additives: string; seedOil: string; noPalmOil: string;
  };
  s2: { features: string[]; phoneScreen?: string };
  s3: {
    h: string[]; sub: string[];
    keto: string; vegan: string; vegetarian: string;
    allergens: string[]; moreDiets: string; andMore: string;
  };
  s4: {
    h: string[]; sub: string[];
    widgetTitle: string;
    flags: Array<{ type: "error" | "warning"; label: string; desc: string; badge?: string }>;
  };
  s5: { h: string[]; sub: string[] };
  s6: {
    h: string[]; sub: string;
    additives: Array<{ color: string; name: string; desc: string }>;
  };
  s7: { h: string[]; sub: string[] };
};

const EN: T = {
  s1: {
    h: ["Scan", "anything."],
    sub: ["In-depth analysis featuring", "ingredients, additives & more."],
    productName: "Ready Salted", productBrand: "Walkers",
    ingredients: "Ingredients", additives: "Additives",
    seedOil: "Seed oil", noPalmOil: "No palm oil",
  },
  s2: { features: ["Scan barcodes", "Track health", "Manage groceries"] },
  s3: {
    h: ["Set dietary", "preferences", "& allergens."],
    sub: ["Quickly see when something", "you scan contains allergens."],
    keto: "Keto", vegan: "Vegan", vegetarian: "Vegetarian",
    allergens: ["Avoid Gluten", "Avoid Fish", "Avoid Milk", "Avoid Peanuts", "Avoid Egg"],
    moreDiets: "+ 6 more diets",
    andMore: "and much more…",
  },
  s4: {
    h: ["Pesticides,", "Microplastic,", "Heavy Metals."],
    sub: ["Understand what you're", "putting into your body."],
    widgetTitle: "Analysis",
    flags: [
      { type: "error",   label: "Heavily processed",      badge: "NOVA 4", desc: "The body doesn't quite know what to do with it — daily exposure adds up." },
      { type: "warning", label: "Pesticide-prone produce", desc: 'High-risk crop · "Dirty 12"' },
      { type: "warning", label: "High sugar content",      desc: "28.4g per 100g" },
    ],
  },
  s5: {
    h: ["Track anxiety,", "sleep & energy."],
    sub: ["See your improvements", "by tracking what matters."],
  },
  s6: {
    h: ["Protect health", "from artificial", "additives."],
    sub: "Read about additives in your food.",
    additives: [
      { color: "#6FCF97", name: "Lactic acid (E270)",           desc: "An acidity regulator" },
      { color: "#6FCF97", name: "Sodium Benzoate (E211)",       desc: "A preservative" },
      { color: ORANGE,    name: "Dicalcium Diphosphate (E540)", desc: "A stabilizer" },
      { color: ORANGE,    name: "Magnesium Gluconate (E580)",   desc: "A stabilizer" },
      { color: RED,       name: "Calcium Propionate (E282)",    desc: "A preservative" },
      { color: RED,       name: "Steviol glycosides (E960)",    desc: "A sweetener" },
    ],
  },
  s7: {
    h: ["Save your", "favourites", "& track them."],
    sub: ["Manage groceries and see", "how processed they are."],
  },
};

const DE: T = {
  s1: {
    h: ["Alles", "scannen."],
    sub: ["Tiefgehende Analyse mit", "Zutaten, Zusatzstoffen & mehr."],
    productName: "Ready Salted", productBrand: "Walkers",
    ingredients: "Zutaten", additives: "Zusatzstoffe",
    seedOil: "Pflanzenöl", noPalmOil: "Kein Palmöl",
  },
  s2: { features: ["Barcodes scannen", "Gesundheit tracken", "Einkäufe verwalten"], phoneScreen: "/screenshots/ss2-result-de.png" },
  s3: {
    h: ["Ernährungs-", "präferenzen &", "Allergene."],
    sub: ["Sofort sehen, ob ein Produkt", "Allergene enthält."],
    keto: "Keto", vegan: "Vegan", vegetarian: "Vegetarisch",
    allergens: ["Glutenfrei", "Fischfrei", "Milchfrei", "Erdnussfrei", "Eierfrei"],
    moreDiets: "+ 6 weitere Diäten",
    andMore: "und vieles mehr…",
  },
  s4: {
    h: ["Pestizide,", "Mikroplastik,", "Schwermetalle."],
    sub: ["Verstehe, was du", "deinem Körper zuführst."],
    widgetTitle: "Analyse",
    flags: [
      { type: "error",   label: "Stark verarbeitet",          badge: "NOVA 4", desc: "Der Körper weiß kaum, was er damit anfangen soll — tägliche Belastung summiert sich." },
      { type: "warning", label: "Pestizidbelastetes Produkt", desc: 'Risikokultur · „Dirty 12"' },
      { type: "warning", label: "Hoher Zuckergehalt",         desc: "28,4g pro 100g" },
    ],
  },
  s5: {
    h: ["Schlaf, Angst", "& Energie tracken."],
    sub: ["Verfolge deine Fortschritte", "bei dem, was zählt."],
  },
  s6: {
    h: ["Keine", "künstlichen", "Zusatzstoffe."],
    sub: "Lerne über Zusatzstoffe in deiner Nahrung.",
    additives: [
      { color: "#6FCF97", name: "Milchsäure (E270)",          desc: "Ein Säureregulator" },
      { color: "#6FCF97", name: "Natriumbenzoat (E211)",      desc: "Ein Konservierungsstoff" },
      { color: ORANGE,    name: "Dicalciumdiphosphat (E540)", desc: "Ein Stabilisator" },
      { color: ORANGE,    name: "Magnesiumgluconat (E580)",   desc: "Ein Stabilisator" },
      { color: RED,       name: "Calciumpropionat (E282)",    desc: "Ein Konservierungsstoff" },
      { color: RED,       name: "Steviolglycoside (E960)",    desc: "Ein Süßungsmittel" },
    ],
  },
  s7: {
    h: ["Favoriten", "speichern &", "verfolgen."],
    sub: ["Einkäufe verwalten und", "den Verarbeitungsgrad sehen."],
  },
};

const FR: T = {
  s1: {
    h: ["Scannez", "tout."],
    sub: ["Analyse complète avec", "ingrédients, additifs & plus."],
    productName: "Ready Salted", productBrand: "Walkers",
    ingredients: "Ingrédients", additives: "Additifs",
    seedOil: "Huile de graine", noPalmOil: "Sans palme",
  },
  s2: { features: ["Scanner les aliments", "Suivre sa santé", "Gérer ses achats"] },
  s3: {
    h: ["Vos préférences", "alimentaires &", "allergènes."],
    sub: ["Voyez rapidement si un produit", "contient des allergènes."],
    keto: "Keto", vegan: "Végane", vegetarian: "Végétarien",
    allergens: ["Éviter le gluten", "Éviter le poisson", "Éviter le lait", "Éviter les arachides", "Éviter les œufs"],
    moreDiets: "+ 6 autres régimes",
    andMore: "et bien plus…",
  },
  s4: {
    h: ["Pesticides,", "Microplastiques,", "Métaux lourds."],
    sub: ["Comprenez ce que vous", "mettez dans votre corps."],
    widgetTitle: "Analyse",
    flags: [
      { type: "error",   label: "Hautement transformé",        badge: "NOVA 4", desc: "L'organisme ne sait pas vraiment quoi en faire — une exposition quotidienne s'accumule." },
      { type: "warning", label: "Produit à risque pesticides", desc: 'Culture à risque · « Dirty 12 »' },
      { type: "warning", label: "Teneur en sucre élevée",      desc: "28,4g pour 100g" },
    ],
  },
  s5: {
    h: ["Suivez anxiété,", "sommeil & énergie."],
    sub: ["Observez vos progrès", "en suivant ce qui compte."],
  },
  s6: {
    h: ["Protégez-vous", "des additifs", "artificiels."],
    sub: "Découvrez les additifs dans votre alimentation.",
    additives: [
      { color: "#6FCF97", name: "Acide lactique (E270)",          desc: "Un régulateur d'acidité" },
      { color: "#6FCF97", name: "Benzoate de sodium (E211)",      desc: "Un conservateur" },
      { color: ORANGE,    name: "Diphosphate dicalcique (E540)",  desc: "Un stabilisant" },
      { color: ORANGE,    name: "Gluconate de magnésium (E580)",  desc: "Un stabilisant" },
      { color: RED,       name: "Propionate de calcium (E282)",   desc: "Un conservateur" },
      { color: RED,       name: "Glycosides de stéviol (E960)",   desc: "Un édulcorant" },
    ],
  },
  s7: {
    h: ["Sauvez vos", "favoris", "& suivez-les."],
    sub: ["Gérez vos achats et voyez", "leur degré de transformation."],
  },
};

const CONTENT: Record<string, T> = { en: EN, de: DE, fr: FR };
const Ctx = React.createContext<T>(EN);

function L({ lines }: { lines: string[] }) {
  return (
    <>
      {lines.map((l, i) =>
        i === 0
          ? <React.Fragment key={i}>{l}</React.Fragment>
          : <React.Fragment key={i}><br />{l}</React.Fragment>
      )}
    </>
  );
}

// ── Phone mockup ──────────────────────────────────────────────────────────────
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

// ── S1 — Hero ─────────────────────────────────────────────────────────────────
function Slide1() {
  const t = useContext(Ctx).s1;
  const IC = W * 0.052;
  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", fontFamily: F, display: "flex", flexDirection: "column", overflow: "hidden" }}>

      <div style={{ padding: `${H * 0.055}px ${TEXT_LR}px 0`, display: "flex", flexDirection: "column", minHeight: H * 0.28, flexShrink: 0 }}>
        <h1 style={{ fontSize: W * 0.135, fontWeight: 800, color: DARK, lineHeight: 0.95, margin: 0 }}>
          <L lines={t.h} />
        </h1>
        <div style={{ flex: 1 }} />
        <p style={{ fontSize: W * 0.062, fontWeight: 500, color: "rgba(0,0,0,0.45)", margin: 0, lineHeight: 1.35 }}>
          <L lines={t.sub} />
        </p>
      </div>

      {/* Scan card */}
      <div style={{
        margin: `${H * 0.026}px ${W * 0.06}px 0`,
        background: "rgba(0,0,0,0.06)", border: "1.5px solid rgba(0,0,0,0.1)",
        borderRadius: W * 0.06, flex: "0 0 auto", height: H * 0.365,
        position: "relative", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden",
      }}>
        <img src="/screenshots/walkers-crisps.png" alt="Walkers Ready Salted"
          style={{ height: "88%", objectFit: "contain", position: "relative", zIndex: 2 }} draggable={false} />
        <div style={{
          position: "absolute", top: "52%", left: 0, right: 0, height: 3, zIndex: 10,
          background: `linear-gradient(90deg, transparent 2%, ${GREEN} 15%, ${GREEN} 85%, transparent 98%)`,
          boxShadow: `0 0 18px 4px rgba(76,175,125,0.5)`,
        }} />
        {[{ top: "10%", left: W * 0.08 }, { top: "10%", right: W * 0.08 }, { bottom: "10%", left: W * 0.08 }, { bottom: "10%", right: W * 0.08 }].map((pos, i) => (
          <div key={i} style={{
            position: "absolute", ...pos, width: W * 0.072, height: W * 0.072, zIndex: 11,
            borderTop: i < 2 ? `3px solid ${GREEN}` : "none",
            borderBottom: i >= 2 ? `3px solid ${GREEN}` : "none",
            borderLeft: i % 2 === 0 ? `3px solid ${GREEN}` : "none",
            borderRight: i % 2 === 1 ? `3px solid ${GREEN}` : "none",
            borderRadius: i === 0 ? "6px 0 0 0" : i === 1 ? "0 6px 0 0" : i === 2 ? "0 0 0 6px" : "0 0 6px 0",
          }} />
        ))}
      </div>

      {/* Product info card */}
      <div style={{
        margin: `${H * 0.022}px ${W * 0.06}px 0`,
        background: "#FDF8F3", border: "1.5px solid rgba(0,0,0,0.09)",
        borderRadius: W * 0.04, padding: `${W * 0.042}px`,
        display: "flex", alignItems: "center", gap: W * 0.03,
      }}>
        <div style={{
          width: W * 0.135, height: W * 0.135, borderRadius: W * 0.022, flexShrink: 0,
          background: "#EDE5DA", overflow: "hidden",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <img src="/screenshots/walkers-crisps.png" alt="Walkers" style={{ width: "90%", height: "90%", objectFit: "contain" }} draggable={false} />
        </div>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: W * 0.048, fontWeight: 700, color: DARK, margin: 0, lineHeight: 1.1 }}>{t.productName}</p>
          <p style={{ fontSize: W * 0.033, color: "rgba(0,0,0,0.4)", margin: `${W * 0.007}px 0 0` }}>{t.productBrand}</p>
        </div>
        <div style={{
          background: RED, borderRadius: W * 0.024,
          padding: `${W * 0.016}px ${W * 0.026}px`,
          display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0,
        }}>
          <span style={{ fontSize: W * 0.062, fontWeight: 900, color: "#fff", lineHeight: 1 }}>29</span>
          <span style={{ fontSize: W * 0.022, color: "rgba(255,255,255,0.7)", lineHeight: 1.2 }}>/100</span>
        </div>
      </div>

      {/* Badges 2×2 */}
      <div style={{ margin: `${H * 0.018}px ${W * 0.06}px 0`, display: "grid", gridTemplateColumns: "1fr 1fr", gap: W * 0.022 }}>
        <div style={{ display: "flex", alignItems: "center", gap: W * 0.018, background: "rgba(0,0,0,0.06)", border: "1.5px solid rgba(0,0,0,0.1)", borderRadius: W * 0.028, padding: `${W * 0.038}px ${W * 0.036}px` }}>
          <span style={{ fontSize: W * 0.065, fontWeight: 900, color: DARK, lineHeight: 1, flexShrink: 0 }}>20</span>
          <span style={{ fontSize: W * 0.038, fontWeight: 500, color: "rgba(0,0,0,0.5)" }}>{t.ingredients}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: W * 0.018, background: "rgba(0,0,0,0.06)", border: "1.5px solid rgba(0,0,0,0.1)", borderRadius: W * 0.028, padding: `${W * 0.038}px ${W * 0.036}px` }}>
          <span style={{ fontSize: W * 0.065, fontWeight: 900, color: RED, lineHeight: 1, flexShrink: 0 }}>4</span>
          <span style={{ fontSize: W * 0.038, fontWeight: 500, color: "rgba(0,0,0,0.5)" }}>{t.additives}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: W * 0.022, background: "rgba(0,0,0,0.06)", border: "1.5px solid rgba(0,0,0,0.1)", borderRadius: W * 0.028, padding: `${W * 0.038}px ${W * 0.036}px` }}>
          <svg width={IC} height={IC} viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
            <path d="M12 3C12 3 6 9.5 6 14a6 6 0 0012 0c0-4.5-6-11-6-11z" fill={ORANGE} />
          </svg>
          <span style={{ fontSize: W * 0.042, fontWeight: 600, color: DARK }}>{t.seedOil}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: W * 0.022, background: "rgba(0,0,0,0.06)", border: "1.5px solid rgba(0,0,0,0.1)", borderRadius: W * 0.028, padding: `${W * 0.038}px ${W * 0.036}px` }}>
          <svg width={IC} height={IC} viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
            <path d="M4 12.5l5 5L20 7" stroke={GREEN} strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span style={{ fontSize: W * 0.042, fontWeight: 600, color: DARK }}>{t.noPalmOil}</span>
        </div>
      </div>

      <div style={{ flex: 1 }} />
    </div>
  );
}

// ── S2 — Features + phone ─────────────────────────────────────────────────────
function Slide2() {
  const t = useContext(Ctx).s2;
  const phoneSrc = t.phoneScreen ?? "/screenshots/ss2-result.png";
  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", overflow: "hidden", fontFamily: F, display: "flex", flexDirection: "column" }}>
      <div style={{ padding: `${H * 0.055}px ${TEXT_LR}px 0`, flexShrink: 0 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: W * 0.044 }}>
          {t.features.map((text, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: W * 0.042 }}>
              <div style={{
                width: W * 0.115, height: W * 0.115, borderRadius: W * 0.026,
                background: GREEN, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
              }}>
                <svg width={W * 0.058} height={W * 0.058} viewBox="0 0 24 24" fill="none">
                  <path d="M4 12l5 5L20 7" stroke="#fff" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <span style={{ fontSize: W * 0.072, fontWeight: 700, color: DARK, lineHeight: 1.1, whiteSpace: "nowrap" }}>{text}</span>
            </div>
          ))}
        </div>
      </div>
      <div style={{ flex: 1, position: "relative" }}>
        <Phone src={phoneSrc} alt="Result"
          style={{ position: "absolute", bottom: 0, left: "50%", transform: "translateX(-50%) translateY(12%)", width: W * 0.84 }} />
      </div>
    </div>
  );
}

// ── S3 — Dietary preferences & allergens ─────────────────────────────────────
function Toggle({ on }: { on: boolean }) {
  return (
    <div style={{
      width: W * 0.13, height: W * 0.07, borderRadius: W * 0.035,
      background: on ? DARK : "rgba(0,0,0,0.12)", position: "relative", flexShrink: 0,
    }}>
      <div style={{
        position: "absolute", top: W * 0.009,
        [on ? "right" : "left"]: W * 0.009,
        width: W * 0.052, height: W * 0.052,
        borderRadius: "50%", background: "#fff", boxShadow: "0 1px 4px rgba(0,0,0,0.2)",
      }} />
    </div>
  );
}

function Slide3() {
  const t = useContext(Ctx).s3;
  const CARD_W = (W - 2 * W * 0.06 - 2 * W * 0.024) / 3;
  const ICON_SZ = W * 0.15;
  const ICON_SZ_SM = W * 0.13;

  const diets = [
    {
      label: t.keto,
      icon: <svg width={ICON_SZ_SM} height={ICON_SZ_SM} viewBox="0 0 24 24" fill="none">
        <path d="M5 18 Q7 10 12 8 Q17 6 19 9 Q21 12 18 15 Q15 18 12 17 Q9 16 8 18Z" fill={GREEN}/>
        <path d="M15 6 Q18 4 20 6" stroke={GREEN} strokeWidth="2" strokeLinecap="round"/>
      </svg>,
    },
    {
      label: t.vegan, active: true,
      icon: <svg width={ICON_SZ} height={ICON_SZ} viewBox="0 0 24 24" fill="none">
        <rect x="10" y="13" width="4" height="8" rx="2" fill="rgba(255,255,255,0.8)"/>
        <circle cx="8"  cy="10" r="4" fill="rgba(255,255,255,0.85)"/>
        <circle cx="16" cy="10" r="4" fill="rgba(255,255,255,0.85)"/>
        <circle cx="12" cy="8"  r="4.5" fill="#fff"/>
      </svg>,
    },
    {
      label: t.vegetarian,
      icon: <svg width={ICON_SZ_SM} height={ICON_SZ_SM} viewBox="0 0 24 24" fill="none">
        <path d="M12 20 C12 20 5 14 5 9 C5 5 8 3 12 3 C16 3 19 5 19 9 C19 14 12 20 12 20Z" fill={GREEN}/>
        <path d="M12 20 L12 10" stroke={GREEN} strokeWidth="1.5" strokeLinecap="round"/>
      </svg>,
    },
  ];

  const ICON_A = W * 0.055;
  const allergenIcons = [
    <svg key={0} width={ICON_A} height={ICON_A} viewBox="0 0 24 24" fill="none">
      <line x1="12" y1="3" x2="12" y2="21" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      <path d="M9 7 Q6 7 6 10 Q6 13 9 13 Q12 13 12 10" fill="currentColor" opacity="0.8"/>
      <path d="M15 11 Q18 11 18 14 Q18 17 15 17 Q12 17 12 14" fill="currentColor" opacity="0.8"/>
    </svg>,
    <svg key={1} width={ICON_A} height={ICON_A} viewBox="0 0 24 24" fill="none">
      <path d="M3 12 Q7 7 12 7 Q17 7 20 12 Q17 17 12 17 Q7 17 3 12Z" fill="currentColor"/>
      <path d="M19 8 L22 5 M19 16 L22 19" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      <circle cx="8" cy="11" r="1.2" fill="white"/>
    </svg>,
    <svg key={2} width={ICON_A} height={ICON_A} viewBox="0 0 24 24" fill="none">
      <path d="M9 3 h6 l1.5 3.5 H7.5 Z" fill="currentColor"/>
      <rect x="6.5" y="6.5" width="11" height="13.5" rx="2.5" fill="currentColor"/>
    </svg>,
    <svg key={3} width={ICON_A} height={ICON_A} viewBox="0 0 24 24" fill="none">
      <ellipse cx="12" cy="7.5" rx="4.5" ry="5.5" fill="currentColor"/>
      <ellipse cx="12" cy="16.5" rx="4.5" ry="5.5" fill="currentColor"/>
      <line x1="7.5" y1="12" x2="16.5" y2="12" stroke="rgba(0,0,0,0.2)" strokeWidth="1.5"/>
    </svg>,
    <svg key={4} width={ICON_A} height={ICON_A} viewBox="0 0 24 24" fill="none">
      <path d="M12 3 C7.5 3 5 8 5 13 C5 18 8 21 12 21 C16 21 19 18 19 13 C19 8 16.5 3 12 3Z" fill="currentColor"/>
    </svg>,
  ];

  const allergens = t.allergens.map((label, i) => ({ label, on: i < 2, icon: allergenIcons[i] }));

  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", fontFamily: F, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ padding: `${H * 0.055}px ${TEXT_LR}px 0`, display: "flex", flexDirection: "column", minHeight: H * 0.28, flexShrink: 0 }}>
        <h1 style={{ fontSize: W * 0.11, fontWeight: 800, color: DARK, lineHeight: 0.95, margin: 0 }}>
          <L lines={t.h} />
        </h1>
        <div style={{ flex: 1 }} />
        <p style={{ fontSize: W * 0.062, fontWeight: 500, color: "rgba(0,0,0,0.45)", margin: 0, lineHeight: 1.35 }}>
          <L lines={t.sub} />
        </p>
      </div>

      <div style={{ marginTop: H * 0.028, display: "flex", gap: W * 0.024, paddingLeft: W * 0.06, paddingRight: W * 0.06, alignItems: "flex-end" }}>
        {diets.map((d, i) => (
          <div key={i} style={{
            width: CARD_W, height: d.active ? CARD_W * 1.15 : CARD_W * 0.95,
            background: d.active ? GREEN : "rgba(0,0,0,0.05)",
            border: d.active ? "1.5px solid transparent" : "1.5px solid rgba(0,0,0,0.1)",
            borderRadius: W * 0.05,
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            gap: W * 0.022, flexShrink: 0, alignSelf: "flex-end",
          }}>
            {d.icon}
            <span style={{ fontSize: W * 0.038, fontWeight: 700, color: d.active ? "#fff" : "rgba(0,0,0,0.6)", textAlign: "center" }}>
              {d.label}
            </span>
            {d.active && (
              <div style={{ width: W * 0.115, height: W * 0.062, borderRadius: W * 0.031, background: DARK, position: "relative" }}>
                <div style={{ position: "absolute", right: W * 0.008, top: W * 0.008, width: W * 0.046, height: W * 0.046, borderRadius: "50%", background: "#fff" }} />
              </div>
            )}
          </div>
        ))}
      </div>

      <p style={{ margin: `${W * 0.022}px ${TEXT_LR}px 0`, fontSize: W * 0.048, fontWeight: 700, color: "rgba(0,0,0,0.45)" }}>
        {t.moreDiets}
      </p>

      <div style={{ margin: `${H * 0.022}px ${W * 0.06}px 0`, display: "flex", flexDirection: "column", gap: W * 0.02 }}>
        {allergens.map((a, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: W * 0.032,
            background: a.on ? "rgba(76,175,125,0.08)" : "rgba(0,0,0,0.05)",
            border: a.on ? "1.5px solid rgba(76,175,125,0.25)" : "1.5px solid rgba(0,0,0,0.09)",
            borderRadius: W * 0.1, padding: `${W * 0.03}px ${W * 0.04}px`,
          }}>
            <div style={{ color: a.on ? GREEN : "rgba(0,0,0,0.35)", flexShrink: 0, display: "flex" }}>{a.icon}</div>
            <span style={{ flex: 1, fontSize: W * 0.046, fontWeight: 600, color: a.on ? DARK : "rgba(0,0,0,0.5)" }}>{a.label}</span>
            <Toggle on={a.on} />
          </div>
        ))}
        <p style={{ margin: `${W * 0.01}px 0 0 ${W * 0.04}px`, fontSize: W * 0.048, fontWeight: 700, color: "rgba(0,0,0,0.45)" }}>
          {t.andMore}
        </p>
      </div>

      <div style={{ flex: 1 }} />
    </div>
  );
}

// ── S4 — Red Flags ────────────────────────────────────────────────────────────
function Slide4() {
  const t = useContext(Ctx).s4;
  const XSZ = W * 0.058;

  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", overflow: "hidden", fontFamily: F, display: "flex", flexDirection: "column" }}>
      <div style={{ padding: `${H * 0.055}px ${TEXT_LR}px 0`, display: "flex", flexDirection: "column", minHeight: H * 0.28, flexShrink: 0 }}>
        <h1 style={{ fontSize: W * 0.11, fontWeight: 800, color: DARK, lineHeight: 0.95, margin: 0 }}>
          <L lines={t.h} />
        </h1>
        <div style={{ flex: 1 }} />
        <p style={{ fontSize: W * 0.062, fontWeight: 500, color: "rgba(0,0,0,0.45)", margin: 0, lineHeight: 1.35 }}>
          <L lines={t.sub} />
        </p>
      </div>

      <div style={{ flex: 1, position: "relative" }}>
        <Phone src="/screenshots/ss4-redflags.png" alt="Red flags"
          style={{ position: "absolute", bottom: 0, left: "50%", transform: "translateX(-50%) translateY(12%)", width: W * 0.84 }} />

        <div style={{
          position: "absolute", bottom: H * 0.22, left: W * 0.06, right: W * 0.06,
          background: "#FFFFFF", borderRadius: W * 0.045,
          padding: `${W * 0.048}px`,
          boxShadow: "0 8px 36px rgba(0,0,0,0.20)",
          border: "1px solid rgba(0,0,0,0.06)",
          zIndex: 20,
        }}>
          <p style={{ fontSize: W * 0.056, fontWeight: 800, color: DARK, margin: `0 0 ${W * 0.034}px` }}>
            {t.widgetTitle}
          </p>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {t.flags.map((f, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "flex-start", gap: W * 0.028,
                paddingTop: i === 0 ? 0 : W * 0.032,
                paddingBottom: i < t.flags.length - 1 ? W * 0.032 : 0,
                borderBottom: i < t.flags.length - 1 ? "1px solid rgba(0,0,0,0.07)" : "none",
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
                      <path d="M12 2.5L1.5 21h21L12 2.5z" fill={ORANGE} />
                      <path d="M12 9.5v5" stroke="#fff" strokeWidth="2.2" strokeLinecap="round"/>
                      <circle cx="12" cy="17.5" r="1.1" fill="#fff"/>
                    </svg>
                  )}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: W * 0.016, flexWrap: "wrap", marginBottom: W * 0.008 }}>
                    <span style={{ fontSize: W * 0.044, fontWeight: 700, color: DARK, lineHeight: 1.2 }}>{f.label}</span>
                    {f.badge && (
                      <div style={{ background: "rgba(217,83,79,0.1)", borderRadius: W * 0.016, padding: `${W * 0.005}px ${W * 0.016}px` }}>
                        <span style={{ fontSize: W * 0.03, fontWeight: 700, color: RED }}>{f.badge}</span>
                      </div>
                    )}
                  </div>
                  <p style={{ fontSize: W * 0.036, color: "rgba(0,0,0,0.5)", margin: 0, lineHeight: 1.35 }}>{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── S5 — Health tracking ──────────────────────────────────────────────────────
function Slide5() {
  const t = useContext(Ctx).s5;
  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", overflow: "hidden", fontFamily: F, display: "flex", flexDirection: "column" }}>
      <div style={{ padding: `${H * 0.055}px ${TEXT_LR}px 0`, display: "flex", flexDirection: "column", minHeight: H * 0.28, flexShrink: 0 }}>
        <h1 style={{ fontSize: W * 0.11, fontWeight: 800, color: DARK, lineHeight: 0.95, margin: 0 }}>
          <L lines={t.h} />
        </h1>
        <div style={{ flex: 1 }} />
        <p style={{ fontSize: W * 0.062, fontWeight: 500, color: "rgba(0,0,0,0.45)", margin: 0, lineHeight: 1.35 }}>
          <L lines={t.sub} />
        </p>
      </div>
      <div style={{ flex: 1, position: "relative" }}>
        <Phone src="/screenshots/ss4-me.png" alt="Health tracking"
          style={{ position: "absolute", bottom: 0, left: "50%", transform: "translateX(-50%) translateY(12%)", width: W * 0.84 }} />
      </div>
    </div>
  );
}

// ── S6 — Additives ────────────────────────────────────────────────────────────
function Slide6() {
  const t = useContext(Ctx).s6;
  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", fontFamily: F, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ padding: `${H * 0.055}px ${TEXT_LR}px 0`, display: "flex", flexDirection: "column", minHeight: H * 0.28, flexShrink: 0 }}>
        <h1 style={{ fontSize: W * 0.11, fontWeight: 800, color: DARK, lineHeight: 0.95, margin: 0 }}>
          <L lines={t.h} />
        </h1>
        <div style={{ flex: 1 }} />
        <p style={{ fontSize: W * 0.062, fontWeight: 500, color: "rgba(0,0,0,0.45)", margin: 0, lineHeight: 1.35 }}>
          {t.sub}
        </p>
      </div>
      <div style={{ margin: `${H * 0.028}px ${TEXT_LR}px 0`, display: "flex", flexDirection: "column", gap: W * 0.022 }}>
        {t.additives.map((a, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: W * 0.028,
            background: "rgba(0,0,0,0.04)", borderRadius: W * 0.025,
            padding: `${W * 0.03}px ${W * 0.032}px`,
          }}>
            <div style={{ width: W * 0.028, height: W * 0.028, borderRadius: "50%", background: a.color, flexShrink: 0 }} />
            <div>
              <p style={{ fontSize: W * 0.042, fontWeight: 700, color: DARK, margin: 0 }}>{a.name}</p>
              <p style={{ fontSize: W * 0.034, color: "rgba(0,0,0,0.45)", margin: `${W * 0.006}px 0 0` }}>{a.desc}</p>
            </div>
          </div>
        ))}
      </div>
      <div style={{ flex: 1 }} />
    </div>
  );
}

// ── S7 — Favourites ───────────────────────────────────────────────────────────
function Slide7() {
  const t = useContext(Ctx).s7;
  return (
    <div style={{ width: W, height: H, background: "#FFFFFF", fontFamily: F, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ padding: `${H * 0.055}px ${TEXT_LR}px 0`, display: "flex", flexDirection: "column", minHeight: H * 0.28, flexShrink: 0 }}>
        <h1 style={{ fontSize: W * 0.11, fontWeight: 800, color: DARK, lineHeight: 0.95, margin: 0 }}>
          <L lines={t.h} />
        </h1>
        <div style={{ flex: 1 }} />
        <p style={{ fontSize: W * 0.062, fontWeight: 500, color: "rgba(0,0,0,0.45)", margin: 0, lineHeight: 1.35 }}>
          <L lines={t.sub} />
        </p>
      </div>
      <div style={{ flex: 1, position: "relative" }}>
        <Phone src="/screenshots/ss7-favourites.png" alt="Favourites"
          style={{ position: "absolute", bottom: 0, left: "50%", transform: "translateX(-50%) translateY(12%)", width: W * 0.84 }} />
      </div>
    </div>
  );
}

// ── Registry ──────────────────────────────────────────────────────────────────
const SCREENSHOTS = [
  { id: "s1", label: "Hero",      component: Slide1 },
  { id: "s2", label: "Features",  component: Slide2 },
  { id: "s3", label: "Allergens", component: Slide3 },
  { id: "s4", label: "Risks",     component: Slide4 },
  { id: "s5", label: "Health",    component: Slide5 },
  { id: "s6", label: "Additives", component: Slide6 },
  { id: "s7", label: "Favorites", component: Slide7 },
];

function getSlideBg(_Cmp: React.ComponentType): string {
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

const LOCALES = [
  { code: "en", label: "🇬🇧 EN" },
  { code: "de", label: "🇩🇪 DE" },
  { code: "fr", label: "🇫🇷 FR" },
  { code: "es", label: "🇪🇸 ES" },
  { code: "ru", label: "🇷🇺 RU" },
];

export default function Page() {
  const [exporting, setExporting] = useState<string | null>(null);
  const [device, setDevice] = useState<DeviceMode>("iphone");
  const offRefsIphone = useRef<Record<string, HTMLDivElement | null>>({});
  const offRefsIpad   = useRef<Record<string, HTMLDivElement | null>>({});
  const router = useRouter();
  const params = useParams();
  const currentLocale = (Array.isArray(params.locale) ? params.locale[0] : params.locale) ?? "en";
  const content = CONTENT[currentLocale] ?? EN;

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
      results.push({ filename: `${deviceLabel}-${currentLocale}-${slideNum}-${slideLabel}-${size.w}x${size.h}.png`, blob });
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
      a.download = `screenshots-${currentLocale}-${new Date().toISOString().slice(0, 10)}.zip`;
      a.click();
    } finally {
      setExporting(null);
    }
  }

  const F_UI = "ui-rounded, -apple-system, system-ui, sans-serif";

  const tabStyle = (active: boolean): React.CSSProperties => ({
    background: active ? GREEN : "transparent",
    color: active ? "#fff" : "#888",
    border: active ? "none" : "1px solid #444",
    borderRadius: 8, padding: "7px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer",
  });

  return (
    <Ctx.Provider value={content}>
      <div style={{ minHeight: "100vh", background: "#111", padding: "32px 24px", fontFamily: F_UI }}>
        <div style={{ maxWidth: 1440, margin: "0 auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 700, color: "#fff", margin: "0 0 3px" }}>App Store Screenshots — {currentLocale.toUpperCase()}</h1>
              <p style={{ fontSize: 12, color: "#666", margin: 0 }}>{SCREENSHOTS.length} slides · {device === "ipad" ? "iPad" : "iPhone"} · click to export</p>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button onClick={() => setDevice("iphone")} style={tabStyle(device === "iphone")}>iPhone</button>
              <button onClick={() => setDevice("ipad")} style={tabStyle(device === "ipad")}>iPad</button>
              <select
                value={currentLocale}
                onChange={e => router.push(`/general/${e.target.value}`)}
                style={{
                  background: "#222", color: "#fff", border: "1px solid #444",
                  borderRadius: 8, padding: "7px 10px", fontSize: 13, fontWeight: 600,
                  cursor: "pointer", outline: "none", appearance: "none", paddingRight: 28,
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E")`,
                  backgroundRepeat: "no-repeat", backgroundPosition: "right 8px center",
                }}
              >
                {LOCALES.map(l => (
                  <option key={l.code} value={l.code}>{l.label}</option>
                ))}
              </select>
              <button onClick={exportAll} disabled={!!exporting}
                style={{ background: exporting ? "#333" : GREEN, color: "#fff", border: "none", borderRadius: 8, padding: "9px 20px", fontSize: 13, fontWeight: 600, cursor: exporting ? "not-allowed" : "pointer", marginLeft: 8 }}>
                {exporting === "all" ? "Packing zip…" : exporting ? `${exporting}…` : "Export All"}
              </button>
            </div>
          </div>
          <div key={device} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))", gap: 20 }}>
            {SCREENSHOTS.map(({ id, label, component: Cmp }) => (
              <Preview key={id} id={id} label={label} Cmp={Cmp} onExport={exportOne} device={device} />
            ))}
          </div>
        </div>
        {/* iPhone off-screen renders */}
        <div style={{ position: "absolute", top: 0, overflow: "hidden" }}>
          {SCREENSHOTS.map(({ id, component: Cmp }) => (
            <div key={`iphone-${id}`} ref={el => { offRefsIphone.current[id] = el; }}
              style={{ position: "absolute", left: "-9999px", top: 0, width: W, height: H, fontFamily: F_UI }}>
              <Cmp />
            </div>
          ))}
        </div>
        {/* iPad off-screen renders */}
        <div style={{ position: "absolute", top: 0, overflow: "hidden" }}>
          {SCREENSHOTS.map(({ id, component: Cmp }) => (
            <div key={`ipad-${id}`} ref={el => { offRefsIpad.current[id] = el; }}
              style={{ position: "absolute", left: "-9999px", top: 0, width: W_IPAD, height: H_IPAD, fontFamily: F_UI }}>
              <div style={{ width: W_IPAD, height: H_IPAD, background: getSlideBg(Cmp), display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ transform: `scale(${IPAD_SCALE})`, transformOrigin: "center center", width: W, height: H }}>
                  <Cmp />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Ctx.Provider>
  );
}
