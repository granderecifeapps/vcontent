export function Logo({ light = false }: { light?: boolean }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span
        style={{
          width: 36,
          height: 36,
          borderRadius: 12,
          background: light ? "#c6a15b" : "#7a3040",
          color: "#fff",
          display: "grid",
          placeItems: "center",
          fontFamily: "var(--font-outfit), Outfit, sans-serif",
          fontWeight: 650,
          letterSpacing: "-0.04em",
        }}
      >
        V
      </span>
      <span>
        <strong style={{ display: "block", fontFamily: "var(--font-outfit), Outfit, sans-serif", letterSpacing: "-0.04em", color: light ? "#f6f1ea" : "#2c211c" }}>
          VContent
        </strong>
        <small style={{ color: light ? "#e4c98a" : "#7a6e66", letterSpacing: "0.12em", textTransform: "uppercase", fontSize: 10 }}>
          Conteúdo
        </small>
      </span>
    </span>
  );
}
