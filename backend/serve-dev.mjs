import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { existsSync } from 'node:fs'

const here = dirname(fileURLToPath(import.meta.url))
const repo = resolve(here, '..')
const venvPython = resolve(repo, '.venv', 'Scripts', 'python.exe')
const py = process.env.PYTHON || (existsSync(venvPython) ? venvPython : 'py')
const prefix = py === 'py' ? ['-3.12'] : []
const apiPort = process.env.SOMAI_E2E_API_PORT || '8000'
const child = spawn(py, [...prefix, resolve(here, 'manage.py'), 'runserver', `127.0.0.1:${apiPort}`, '--noreload'], { cwd: here, stdio: 'inherit', shell: true })
child.on('exit', (code) => process.exit(code ?? 0))
