import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import ClassMasterPreview, { CLASS_PREVIEW_FIXTURES } from "./ClassMasterPreview";

jest.mock("@/components/TradingCard",()=>({
  CardFront:({card})=><div data-testid="mock-card-front">
    {card.name} | {card.attributes.dado_vita} | {card.attributes.abilita_primaria}
  </div>,
}));

describe("isolated live class master verification page",()=>{
  it("covers all thirteen classes and uses the real card data shape",()=>{
    expect(CLASS_PREVIEW_FIXTURES).toHaveLength(13);
    expect(new Set(CLASS_PREVIEW_FIXTURES.map(item=>item.name)).size).toBe(13);
    expect(CLASS_PREVIEW_FIXTURES.find(item=>item.name==="Mago").die).toBe("d6");
    expect(CLASS_PREVIEW_FIXTURES.find(item=>item.name==="Barbaro").die).toBe("d12");
  });
  it("switches the visible class without any backend mutation",()=>{
    render(<ClassMasterPreview/>);
    expect(screen.getByTestId("mock-card-front").textContent).toContain("Bardo");
    fireEvent.click(screen.getByRole("button",{name:"Mago"}));
    expect(screen.getByTestId("mock-card-front").textContent).toContain("Mago | d6 | Intelligenza");
    expect(screen.getByText(/nessun login, salvataggio o modifica ai record/)).toBeTruthy();
  });
});
