import { createSystem, defaultConfig } from "@chakra-ui/react";
import "./fonts.css";

const system = createSystem(defaultConfig, {
  theme: {
    tokens: {
      colors: {
        smu: {
          // Refer to the BI document at the following URL:
          // https://www.sookmyung.ac.kr/kr/intro/ui.do

          // Main Colors
          blue: { value: "#002f87" }, // Sookmyung Royal Blue, Pantone 287C
          lightBlue: { value: "#0072ce" }, // Sookmyung Royal Light Blue, Pantone 285C
          darkGray: { value: "#636569" }, // Sookmyung Dark Gray, Pantone Cool Gray 10C
          smuGray: { value: "#97999b" }, // Sookmyung SMU Gray, Pantone Cool Gray 7C
          // Sub colors
          yellow: { value: "#ffb700" }, // Sookmyung Royal Yellow, Pantone 7549C
          orange: { value: "#ff7c01" }, // Sookmyung Royal Orange, Pantone 152C
          gray: { value: "#d9d9d6" }, // Sookmyung Gray, Pantone Cool Gray 1C
          // Metallic colors
          gold: { value: "#85714d" }, // Sookmyung Gold, Pantone 872C
          silver: { value: "#8a8d8f" }, // Sookmyung Silver, Pantone 877C
        },
      },
      fonts: {
        heading: { value: `"SMUFont", sans-serif` },
        body: { value: `"SMUFont", sans-serif` },
      },
    },
  },
});

export default system;
