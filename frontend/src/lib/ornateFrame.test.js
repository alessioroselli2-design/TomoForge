import { ORNATE_FRAME_SVG, ORNATE_FRAME_URL } from "./ornateFrame";
describe("ornate frame asset",()=>{
  it("is a self-contained scalable image for preview, PNG and PDF",()=>{
    expect(ORNATE_FRAME_SVG).toContain('viewBox="0 0 340 476"');
    expect(ORNATE_FRAME_SVG).toContain("linearGradient");
    expect(ORNATE_FRAME_SVG).toContain("outer 12-pixel rail");
    expect(ORNATE_FRAME_SVG).not.toContain("M2 68 C0 39");
    expect(ORNATE_FRAME_SVG).not.toContain("<script");
    expect(ORNATE_FRAME_URL).toMatch(/^data:image\/svg\+xml;charset=utf-8,/);
  });
});
