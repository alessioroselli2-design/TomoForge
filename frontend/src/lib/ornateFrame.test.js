import { ORNATE_FRAME_SVG, ORNATE_FRAME_URL } from "./ornateFrame";
describe("seamless ornamental frame",()=>{
 it("renders a transparent self-contained vector source with no screenshot overlays or captions",()=>{
   expect(ORNATE_FRAME_SVG).toContain('viewBox="0 0 340 476"');
   expect(ORNATE_FRAME_SVG).toContain('width="331" height="467"');
   expect(ORNATE_FRAME_SVG).not.toContain("<image");
   expect(ORNATE_FRAME_SVG).not.toContain("<text");
   expect(ORNATE_FRAME_SVG).not.toContain("<script");
   expect(ORNATE_FRAME_URL).toMatch(/^data:image\/svg\+xml;charset=utf-8,/);
 });
});
