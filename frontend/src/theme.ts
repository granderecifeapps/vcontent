import { createTheme, type MantineColorsTuple } from "@mantine/core";

const brand: MantineColorsTuple = [
  "#f7f3ff",
  "#ede7ff",
  "#e0d4ff",
  "#cbb8ff",
  "#b9a1ff",
  "#9a78ff",
  "#7c4dff",
  "#6b3cf0",
  "#5a2de0",
  "#4a22c4",
];

export const theme = createTheme({
  primaryColor: "brand",
  colors: { brand },
  primaryShade: 6,
  fontFamily: "var(--font-inter), Inter, sans-serif",
  headings: {
    fontFamily: "var(--font-outfit), Outfit, sans-serif",
    fontWeight: "600",
  },
  defaultRadius: 12,
  cursorType: "pointer",
  black: "#111114",
  white: "#ffffff",
  components: {
    Button: { defaultProps: { radius: "xl" } },
    Card: {
      defaultProps: { radius: 20, padding: "lg", withBorder: true },
      styles: { root: { borderColor: "#eceaf2", background: "#ffffff" } },
    },
    TextInput: { defaultProps: { radius: "md" } },
    PasswordInput: { defaultProps: { radius: "md" } },
    Textarea: { defaultProps: { radius: "md" } },
    Select: { defaultProps: { radius: "md" } },
    Modal: {
      defaultProps: {
        radius: 20,
        centered: true,
        overlayProps: { backgroundOpacity: 0.35, blur: 3 },
      },
    },
    Paper: { defaultProps: { radius: 20 } },
  },
});
