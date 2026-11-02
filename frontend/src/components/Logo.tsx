export function Logo({ light = false }: { light?: boolean }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span
        style={{
          width: 36,
          height: 36,
          borderRadius: 12,
          background: light ? "#7c4dff" : "#7c4dff",
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
        <strong style={{ display: "block", fontFamily: "var(--font-outfit), Outfit, sans-serif", letterSpacing: "-0.04em", color: light ? "#f7f3ff" : "#111114" }}>
          VContent
        </strong>
        <small style={{ color: light ? "#b9a1ff" : "#6f6b78", letterSpacing: "0.12em", textTransform: "uppercase", fontSize: 10 }}>
          Conteúdo
        </small>
      </span>
    </span>
  );
}
