import { createTheme, type MantineColorsTuple } from "@mantine/core";

const brand: MantineColorsTuple = [
  "#fbf6f4",
  "#f6e8e6",
  "#e8c9c8",
  "#d4a3a6",
  "#b96b78",
  "#944555",
  "#7a3040",
  "#642833",
  "#4e1e28",
  "#3b161e",
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
  black: "#2c211c",
  white: "#ffffff",
  components: {
    Button: { defaultProps: { radius: "xl" } },
    Card: {
      defaultProps: { radius: 20, padding: "lg", withBorder: true },
      styles: { root: { borderColor: "#e7ddd2", background: "#ffffff" } },
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
