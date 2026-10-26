import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: "#0B1220",
          soft: "#1A2332",
          muted: "#3D4A5C",
        },
        mist: {
          DEFAULT: "#E8EEF5",
          light: "#F4F7FB",
        },
        copper: {
          DEFAULT: "#C45C26",
          soft: "#D4784A",
          muted: "#E8A882",
        },
      },
      fontFamily: {
        sans: ["var(--font-ibm-plex-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-ibm-plex-mono)", "ui-monospace", "monospace"],
      },
      backgroundImage: {
        mist: "linear-gradient(160deg, #E8EEF5 0%, #F4F7FB 45%, #E2EAF3 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
