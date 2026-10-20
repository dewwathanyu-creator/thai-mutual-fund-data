import { loadFont } from "@remotion/google-fonts/IBMPlexSans";
import { loadFont as loadThai } from "@remotion/google-fonts/IBMPlexSansThai";

export const { fontFamily } = loadFont("normal", { weights: ["400", "500", "600", "700"], subsets: ["latin"] });
export const { fontFamily: thaiFamily } = loadThai("normal", { weights: ["400", "600"], subsets: ["thai", "latin"] });

export const C = {
  navy: "#0a1f44",
  navy2: "#102a5c",
  brand: "#1b4b9b",
  sky: "#9bbfff",
  ink: "#ffffff",
  mute: "rgba(255,255,255,.72)",
  accent: "#ffc857",
};
