// Dumb docspec -> .docx renderer (docx-js). ALL content logic lives in build_report_docx.py;
// this file only maps resolved blocks to Word constructs per the docx skill's rules
// (US Letter, dual table widths in DXA, LevelFormat bullets, TOC over HeadingLevels).
import fs from "fs";
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  Footer, AlignmentType, PageOrientation, LevelFormat, TableOfContents, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageNumber, PageBreak, TabStopType, TabStopPosition,
} = require("docx");
import sizeOf from "./imgsize.mjs";

const [specPath, outPath] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));

const LETTER = { width: 12240, height: 15840 };
const MARGIN = 1440;
const CONTENT = { portrait: 12240 - 2 * MARGIN, landscape: 15840 - 2 * MARGIN };
const HEADINGS = [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2,
                  HeadingLevel.HEADING_3, HeadingLevel.HEADING_4];

const runs = (rs, size) => rs.map(r => new TextRun({
  text: r.s, bold: r.t === "bold", italics: r.t === "italic",
  font: r.t === "code" ? "Consolas" : undefined, size,
}));

function table(b, orientation) {
  const content = CONTENT[orientation];
  const widths = b.col_fracs.map(f => Math.round(f * content));
  widths[widths.length - 1] = content - widths.slice(0, -1).reduce((a, x) => a + x, 0);
  const border = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
  const borders = { top: border, bottom: border, left: border, right: border };
  const sz = (b.font_size || 9) * 2;
  const mkRow = (cells, { header = false, emph = false } = {}) => new TableRow({
    tableHeader: header,
    children: cells.map((c, j) => new TableCell({
      borders, width: { size: widths[j], type: WidthType.DXA },
      shading: header ? { fill: "D9E2F3", type: ShadingType.CLEAR }
        : emph ? { fill: "EFEFEF", type: ShadingType.CLEAR } : undefined,
      margins: { top: 40, bottom: 40, left: 80, right: 80 },
      children: [new Paragraph({
        alignment: j === 0 ? AlignmentType.LEFT : AlignmentType.RIGHT,
        children: [new TextRun({ text: c, bold: header || emph, size: sz })],
      })],
    })),
  });
  const out = [];
  if (b.caption) out.push(new Paragraph({
    style: "Caption", spacing: { before: 160, after: 60 },
    children: [new TextRun({ text: b.caption })],
  }));
  out.push(new Table({
    width: { size: content, type: WidthType.DXA }, columnWidths: widths,
    rows: [mkRow(b.header, { header: true }),
           ...b.rows.map((r, i) => mkRow(r, { emph: b.emph[i] }))],
  }));
  out.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
  return out;
}

function figure(b) {
  const dim = sizeOf(b.path);
  const width = 624;                                    // 6.5" at 96 px/in
  const height = Math.round(width * dim.height / dim.width);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 160 },
      children: [new ImageRun({
        type: "png", data: fs.readFileSync(b.path),
        transformation: { width, height },
        altText: { title: b.caption, description: b.caption, name: b.caption.slice(0, 60) },
      })],
    }),
    new Paragraph({
      style: "Caption", alignment: AlignmentType.CENTER, spacing: { after: 160 },
      children: [new TextRun({ text: b.caption })],
    }),
  ];
}

function blockChildren(blocks, orientation) {
  const out = [];
  for (const b of blocks) {
    if (b.kind === "heading") {
      out.push(new Paragraph({ heading: HEADINGS[b.level - 1],
                               children: [new TextRun(b.text)] }));
    } else if (b.kind === "para") {
      out.push(new Paragraph({ spacing: { after: 120 }, children: runs(b.runs) }));
    } else if (b.kind === "quote") {
      out.push(new Paragraph({
        indent: { left: 540 }, spacing: { after: 120 },
        border: { left: { style: BorderStyle.SINGLE, size: 12, color: "9BB7D4", space: 8 } },
        children: runs(b.runs, 21),
      }));
    } else if (b.kind === "equation") {
      b.lines.forEach((ln, i) => out.push(new Paragraph({
        shading: { fill: "F4F4F4", type: ShadingType.CLEAR },
        spacing: { before: i === 0 ? 120 : 0, after: i === b.lines.length - 1 ? 120 : 0 },
        children: [new TextRun({ text: ln === "" ? " " : ln, font: "Consolas", size: 18 })],
      })));
    } else if (b.kind === "list") {
      b.items.forEach(item => out.push(new Paragraph({
        numbering: { reference: b.ordered ? "numbers" : "bullets", level: 0 },
        spacing: { after: 60 }, children: runs(item),
      })));
    } else if (b.kind === "table") {
      out.push(...table(b, orientation));
    } else if (b.kind === "figure") {
      out.push(...figure(b));
    } else if (b.kind === "toc") {
      out.push(new TableOfContents("Table of Contents",
                                   { hyperlink: true, headingStyleRange: "1-3" }));
      out.push(new Paragraph({ children: [new PageBreak()] }));
    } else if (b.kind === "pagebreak") {
      out.push(new Paragraph({ children: [new PageBreak()] }));
    } else {
      throw new Error(`unknown block kind: ${b.kind}`);
    }
  }
  return out;
}

// split blocks into sections at {{section:...}} directives
const sections = [];
let cur = { orientation: "portrait", blocks: [] };
for (const b of spec.blocks) {
  if (b.kind === "section") {
    if (cur.blocks.length) sections.push(cur);
    cur = { orientation: b.orientation, blocks: [] };
  } else cur.blocks.push(b);
}
if (cur.blocks.length) sections.push(cur);

const footer = new Footer({
  children: [new Paragraph({
    tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
    children: [
      new TextRun({ text: spec.footer, size: 14, color: "666666" }),
      new TextRun({ children: ["\tPage ", PageNumber.CURRENT], size: 14, color: "666666" }),
    ],
  })],
});

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },        // 11pt body
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 320, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 260, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
      { id: "Heading4", name: "Heading 4", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, italics: true, font: "Arial" },
        paragraph: { spacing: { before: 160, after: 100 }, outlineLevel: 3 } },
      { id: "Caption", name: "Caption", basedOn: "Normal",
        run: { size: 18, italics: true, color: "444444" } },
      { id: "Title", name: "Title", basedOn: "Normal",
        run: { size: 44, bold: true }, paragraph: { spacing: { after: 240 } } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  features: { updateFields: true },        // Word refreshes the TOC on open
  sections: sections.map(s => ({
    properties: {
      page: {
        size: { width: LETTER.width, height: LETTER.height,
                ...(s.orientation === "landscape"
                    ? { orientation: PageOrientation.LANDSCAPE } : {}) },
        margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
      },
    },
    footers: { default: footer },
    children: blockChildren(s.blocks, s.orientation),
  })),
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log(`rendered ${sections.length} section(s), ${spec.blocks.length} blocks`);
});
