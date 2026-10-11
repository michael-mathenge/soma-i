import { statSync } from "node:fs";

function isFile(path) {
  if (!path) return false;
  try {
    return statSync(path).isFile();
  } catch {
    return false;
  }
}

export function resolvePython(python, venvPython) {
  if (isFile(python)) return python;
  if (isFile(venvPython)) return venvPython;
  return "py";
}
