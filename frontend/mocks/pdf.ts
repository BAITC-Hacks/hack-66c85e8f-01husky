/** Builds a tiny valid one-page PDF so the mock "Скачать PDF" opens in a viewer. */
export function MINIMAL_PDF(title: string): string {
  const ascii = title.normalize("NFKD").replace(/[^\x20-\x7E]/g, "").trim() || "Meeting";
  const text = `BT /F1 20 Tf 72 740 Td (Kenes AI - protocol draft) Tj 0 -32 Td /F1 12 Tf (${ascii.replace(/[()\\]/g, "")}) Tj 0 -20 Td (Mock export - real file is rendered by backend/services/export.py) Tj ET`;
  const objs = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    `<< /Length ${text.length} >>\nstream\n${text}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let out = "%PDF-1.4\n";
  const offsets: number[] = [];
  objs.forEach((o, i) => {
    offsets.push(out.length);
    out += `${i + 1} 0 obj\n${o}\nendobj\n`;
  });
  const xref = out.length;
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
  out += offsets.map((n) => `${String(n).padStart(10, "0")} 00000 n \n`).join("");
  out += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return out;
}
