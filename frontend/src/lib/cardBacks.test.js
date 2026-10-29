import fs from "fs";
import path from "path";
import { getApprovedBack, CHARACTER_BACK_VARIANTS, APPROVED_BACK_FILES } from "./cardBacks";

describe("approved TomoForge backs", () => {
  it("ships exactly the ten official assets and no unapproved legacy images", () => {
    expect(APPROVED_BACK_FILES).toHaveLength(10);
    expect(new Set(APPROVED_BACK_FILES).size).toBe(10);
    const actualFiles = fs.readdirSync(path.resolve(__dirname, "../../public/dorsi"))
      .filter((name) => /\\.(?:jpg|jpeg|png|webp)$/i.test(name)).sort();
    expect(actualFiles).toEqual(APPROVED_BACK_FILES.map((name) => `${name}.jpg`).sort());
  });

  it("always returns only an official image, even for old or malformed card data", () => {
    ["MONSTER", "  magic_item  ", "", null, "some-removed-category"].forEach((type) => {
      const back = getApprovedBack({ type, back: { style: "runic", color: "#f00", emblem: "skull", variant: "silver" } });
      expect(APPROVED_BACK_FILES).toContain(back.file);
      expect(back.src).toBe(`/dorsi/${back.file}.jpg`);
      expect(back.file).not.toBe("personaggio-argento");
    });
    expect(getApprovedBack({ type: "MONSTER" }).file).toBe("mostro");
    expect(getApprovedBack({ type: "  magic_item  " }).file).toBe("oggetto-magico");
  });

  it.each([
    ["monster", "mostro"], ["class", "classe"], ["subclass", "classe"],
    ["feature", "privilegio"], ["class_feature", "privilegio"],
    ["spell", "incantesimo"], ["feat", "talento"], ["race", "razza"],
    ["subrace", "razza"], ["weapon", "armi-armature"],
    ["armor", "armi-armature"], ["shield", "armi-armature"],
    ["item", "oggetto-magico"], ["magic_item", "oggetto-magico"],
    ["custom", "oggetto-magico"],
  ])("assigns the official %s back automatically", (type, file) => {
    expect(getApprovedBack({ type }).src).toBe(`/dorsi/${file}.jpg`);
  });

  it("keeps the two approved character designs only", () => {
    expect(CHARACTER_BACK_VARIANTS).toHaveLength(2);
    expect(getApprovedBack({ type: "character" }).file).toBe("personaggio-luce");
    expect(getApprovedBack({ type: "character", back: { variant: "silver" } }).file).toBe("personaggio-argento");
  });

  it("ignores deprecated back styles, colors, emblems and motto on saved cards", () => {
    const back = { style: "runic", emblem: "skull", color: "#f00", motto: "Vecchio retro", variant: "silver" };
    expect(getApprovedBack({ type: "monster", back }).file).toBe("mostro");
    expect(getApprovedBack({ type: "character", back }).file).toBe("personaggio-argento");
    expect(getApprovedBack({ type: "character", back: { variant: "runic" } }).file).toBe("personaggio-luce");
  });
});
