import Link from "next/link";

const F = "ui-rounded, -apple-system, system-ui, sans-serif";
const GREEN = "#4CAF7D";

const SETS = [
  {
    slug: "general",
    title: "General",
    desc: "Main App Store screenshots",
    locales: [
      { code: "de", flag: "🇩🇪", label: "DE" },
      { code: "en", flag: "🇬🇧", label: "EN" },
      { code: "fr", flag: "🇫🇷", label: "FR" },
    ],
  },
  {
    slug: "gluten",
    title: "Gluten",
    desc: "Custom Product Page — gluten audience",
    locales: [
      { code: "de", flag: "🇩🇪", label: "DE" },
      { code: "en", flag: "🇬🇧", label: "EN" },
    ],
  },
  {
    slug: "halal",
    title: "Halal",
    desc: "Custom Product Page — halal audience",
    locales: [
      { code: "de", flag: "🇩🇪", label: "DE" },
    ],
  },
];

export default function HubPage() {
  return (
    <div style={{ minHeight: "100vh", background: "#111", padding: "48px 32px", fontFamily: F }}>
      <div style={{ maxWidth: 640, margin: "0 auto" }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#fff", margin: "0 0 6px" }}>
          Screenshots Hub
        </h1>
        <p style={{ fontSize: 13, color: "#555", margin: "0 0 40px" }}>
          App Store screenshot sets · click a locale to open
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {SETS.map(set => (
            <div key={set.slug} style={{
              background: "#1a1a1a",
              border: "1px solid #2a2a2a",
              borderRadius: 12,
              padding: "20px 24px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 16,
            }}>
              <div>
                <p style={{ fontSize: 15, fontWeight: 700, color: "#fff", margin: "0 0 3px" }}>
                  {set.title}
                </p>
                <p style={{ fontSize: 12, color: "#555", margin: 0 }}>
                  {set.desc}
                </p>
              </div>
              <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                {set.locales.map(loc => (
                  <Link
                    key={loc.code}
                    href={`/${set.slug}/${loc.code}`}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 5,
                      background: GREEN,
                      color: "#fff",
                      borderRadius: 7,
                      padding: "6px 14px",
                      fontSize: 13,
                      fontWeight: 600,
                      textDecoration: "none",
                    }}
                  >
                    {loc.flag} {loc.label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
