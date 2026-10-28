import { getApprovedBack, CHARACTER_BACK_VARIANTS } from "./cardBacks";

describe("approved TomoForge backs", () => {
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
