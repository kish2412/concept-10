import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#f4f6f8",
        panel: "#ffffff",
        ink: "#10212b",
        muted: "#5d6c74",
        orch: "#1d4ed8",
        util: "#047857",
        spec: "#b45309",
        hil: "#b91c1c"
      },
      boxShadow: {
        card: "0 10px 30px rgba(0, 0, 0, 0.08)"
      },
      keyframes: {
        pulseRing: {
          "0%": { boxShadow: "0 0 0 0 rgba(29, 78, 216, 0.55)" },
          "100%": { boxShadow: "0 0 0 16px rgba(29, 78, 216, 0)" }
        }
      },
      animation: {
        pulseRing: "pulseRing 1.6s ease-out infinite"
      }
    }
  },
  plugins: [],
};

export default config;
