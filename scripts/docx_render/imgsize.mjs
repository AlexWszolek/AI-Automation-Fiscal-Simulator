// Minimal PNG dimension reader (IHDR is always the first chunk: width/height at bytes 16/20).
import fs from "fs";

export default function sizeOf(path) {
  const buf = fs.readFileSync(path);
  if (buf.readUInt32BE(0) !== 0x89504e47) throw new Error(`not a PNG: ${path}`);
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}
