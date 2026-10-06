import { createReadStream, existsSync } from 'node:fs'
import { createServer, request as httpRequest } from 'node:http'
import { extname, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(fileURLToPath(new URL('./dist/', import.meta.url)))
const mimeTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.webmanifest': 'application/manifest+json',
}

createServer((request, response) => {
  if (request.url.startsWith('/api/')) {
    const proxy = httpRequest(
      { hostname: '127.0.0.1', port: 8000, path: request.url, method: request.method, headers: request.headers },
      (upstream) => {
        response.writeHead(upstream.statusCode || 502, upstream.headers)
        upstream.pipe(response)
      },
    )
    proxy.on('error', () => { response.writeHead(502); response.end('API unavailable') })
    request.pipe(proxy)
    return
  }

  let requestedPath = decodeURIComponent(new URL(request.url, 'http://localhost').pathname)
  if (requestedPath === '/') requestedPath = '/index.html'
  const filePath = resolve(root, `.${requestedPath}`)
  if (!filePath.startsWith(root + sep) && filePath !== root) {
    response.writeHead(403).end()
    return
  }
  const finalPath = existsSync(filePath) ? filePath : resolve(root, 'index.html')
  response.writeHead(200, { 'Content-Type': mimeTypes[extname(finalPath)] || 'application/octet-stream' })
  createReadStream(finalPath).pipe(response)
}).listen(4173, '127.0.0.1')
