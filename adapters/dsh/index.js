import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { isAbsolute } from 'node:path'
import Schema from '@deepseek-ai/schemastery'
import { defineTool } from '@deepseek-ai/dsh-tools'
import { BUNDLED_SKILL_RANK } from '@deepseek-ai/dsh-skill'
import { callCore } from './bridge.js'

export const name = 'yt-dlp-agent-kit'
export const inject = ['tools', 'skills']
export const Config = Schema.object({
  pythonPath: Schema.string().default(''),
  configPath: Schema.string().default(''),
})

const tools = JSON.parse(await readFile(new URL('./tools.json', import.meta.url), 'utf8'))
const skillURL = new URL('./skills/yt-media/SKILL.md', import.meta.url)

export function apply(ctx, config) {
  const python = config.pythonPath || process.env.YTAGENT_PYTHON || ''
  const configPath = config.configPath || process.env.YTAGENT_CONFIG || ''
  if (!isAbsolute(python) || (configPath && !isAbsolute(configPath))) {
    throw new Error('Set YTAGENT_PYTHON or pythonPath to the installed core Python absolute path; configPath must also be absolute')
  }
  const lifetime = new AbortController()
  ctx.effect(() => () => lifetime.abort())
  for (const tool of tools) {
    const parameters = Object.fromEntries(Object.entries(tool.inputSchema.properties).map(([key, value]) => {
      const parameter = { type: value.type }
      if (tool.inputSchema.required.includes(key)) parameter.required = true
      if (value.enum) parameter.enum = value.enum
      return [key, parameter]
    }))
    ctx.tools.register(defineTool({
      name: tool.name, description: tool.description, parameters,
      output: {
        schema: { type: 'object', properties: {}, additionalProperties: true },
        render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
      },
      execute(args, exec) {
        return callCore(python, configPath, { tool: tool.name, arguments: args },
          AbortSignal.any([exec.signal, lifetime.signal]))
      },
    }))
  }
  const candidate = {
    name: 'yt-media', description: 'Inspect public videos, read subtitles or prepare approved downloads using yt-dlp Agent Kit tools.',
    invocation: { modelInvocable: true, userInvocable: true },
    provider: name, source: 'bundled', rank: BUNDLED_SKILL_RANK,
    resourceBase: { kind: 'directory', path: fileURLToPath(new URL('./skills/yt-media/', import.meta.url)) },
    locator: skillURL,
  }
  ctx.skills.registerProvider(() => ({
    name,
    async list() { return [candidate] },
    async get() { return { ...candidate, content: await readFile(skillURL, 'utf8') } },
  }))
}
