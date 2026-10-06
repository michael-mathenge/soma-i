import { readdir, readFile } from 'node:fs/promises'
import { gzipSync } from 'node:zlib'
import { join } from 'node:path'

async function filesIn(path) {
  const found = []
  for (const item of await readdir(path, { withFileTypes: true })) {
    const full = join(path, item.name)
    if (item.isDirectory()) found.push(...await filesIn(full))
    else if (/\.(js|css)$/.test(item.name)) found.push(full)
  }
  return found
}

const files = await filesIn('dist/assets')
let bytes = 0
for (const file of files) bytes += gzipSync(await readFile(file)).length
console.log(`Gzipped JS + CSS: ${(bytes / 1024).toFixed(1)} KB`)
if (bytes >= 200 * 1024) process.exitCode = 1
