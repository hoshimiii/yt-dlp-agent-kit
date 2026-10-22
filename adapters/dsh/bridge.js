import { spawn } from 'node:child_process'
import { isAbsolute } from 'node:path'

export function callCore(python, configPath, request, signal) {
  if (!isAbsolute(python) || (configPath && !isAbsolute(configPath))) {
    throw new Error('Configure an absolute Python executable and optional absolute configPath')
  }
  signal?.throwIfAborted()
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) =>
    ['SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'HOME', 'USERPROFILE', 'LANG', 'LC_ALL'].includes(key.toUpperCase())))
  if (configPath) env.YTAGENT_CONFIG = configPath
  return new Promise((resolve, reject) => {
    const child = spawn(python, ['-I', '-m', 'yt_agent.cli', 'call'], {
      shell: false, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'], env,
    })
    let output = ''
    let size = 0
    let error
    const stop = (message) => {
      error ??= new Error(message)
      child.kill()
    }
    const timer = setTimeout(() => stop('Core deadline exceeded'), 185000)
    const abort = () => stop('Cancelled')
    signal?.addEventListener('abort', abort, { once: true })
    if (signal?.aborted) abort()
    child.stdout.on('data', (chunk) => {
      size += chunk.length
      if (size > 512 * 1024) stop('Core response too large')
      else output += chunk.toString('utf8')
    })
    child.stderr.on('data', (chunk) => {
      size += chunk.length
      if (size > 512 * 1024) stop('Core response too large')
    })
    child.stdin.on('error', () => stop('Cannot send request to core'))
    child.once('error', () => { error ??= new Error('Cannot start configured Python core') })
    child.once('close', (code) => {
      clearTimeout(timer)
      signal?.removeEventListener('abort', abort)
      if (error) return reject(error)
      try {
        const response = JSON.parse(output)
        if (code !== 0 || response.ok !== true || !response.result || typeof response.result !== 'object') {
          // Local core errors are controlled strings; do not return arbitrary child stderr.
          return reject(new Error(code === 1 && response.ok === false ? response.error : 'Invalid core response'))
        }
        resolve(response.result)
      } catch { reject(new Error('Invalid core response')) }
    })
    child.stdin.end(JSON.stringify(request))
  })
}
