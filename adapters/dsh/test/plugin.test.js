import assert from 'node:assert/strict'
import { test } from 'node:test'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { Context } from '@deepseek-ai/cordis'
import { ToolRuntime } from '@deepseek-ai/dsh-tools'
import { SkillRegistry } from '@deepseek-ai/dsh-skill'
import { SystemPrompt } from '@deepseek-ai/dsh-system-prompt'
import * as plugin from '../index.js'
import { callCore } from '../bridge.js'

test('native DSH registries load all tools and packaged skill, and dispose cleanly', async () => {
  const ctx = new Context()
  await ctx.plugin(SystemPrompt).await()
  await ctx.plugin(ToolRuntime).await()
  await ctx.plugin(SkillRegistry).await()
  const pythonPath = process.env.YTAGENT_TEST_PYTHON || process.execPath
  const fiber = ctx.plugin(plugin, { pythonPath, configPath: '' })
  await fiber.await()
  const names = ctx.tools.schemas().map(t => t.name)
  for (const name of ['video_info', 'video_subtitles', 'video_plan_download', 'video_download']) assert.ok(names.includes(name))
  assert.ok(!names.includes('approve'))
  const summaries = await ctx.skills.list()
  const skill = summaries.find(s => s.name === 'yt-media')
  assert.ok(skill)
  const loaded = await ctx.skills.get('yt-media')
  assert.match(loaded.content, /untrusted source/)
  await fiber.dispose()
  assert.ok(!ctx.tools.schemas().some(t => t.name.startsWith('video_')))
  await ctx.fiber.dispose()
})

test('native bridge invokes the installed core and rejects URL injection', { skip: !process.env.YTAGENT_TEST_PYTHON }, async () => {
  await assert.rejects(callCore(process.env.YTAGENT_TEST_PYTHON, '', {
    tool: 'video_info', arguments: { url: 'file:///etc/passwd' },
  }, new AbortController().signal), /HTTPS/)
})

test('native bridge returns the controlled missing-config diagnostic', { skip: !process.env.YTAGENT_TEST_PYTHON }, async () => {
  const configPath = resolve(process.cwd(), '.cache', `r4-missing-config-${process.pid}-${Date.now()}.json`)
  await assert.rejects(readFile(configPath), { code: 'ENOENT' })
  await assert.rejects(callCore(process.env.YTAGENT_TEST_PYTHON, configPath, {
    tool: 'video_plan_download', arguments: { url: 'https://youtu.be/BaW_jenozKc' },
  }, new AbortController().signal), error => {
    assert.match(error.message, /Configured policy file was not found; ask the operator to check YTAGENT_CONFIG\/configPath/)
    assert.doesNotMatch(error.message, /r4-missing-config|FileNotFoundError|ENOENT/)
    return true
  })
  await assert.rejects(readFile(configPath), { code: 'ENOENT' })
})

test('bridge rejects executable/path injection and pre-cancelled calls', async () => {
  assert.throws(() => callCore('python;evil', '', {}, undefined), /absolute/)
  const controller = new AbortController()
  controller.abort()
  assert.throws(() => callCore(process.execPath, '', {}, controller.signal))
})

test('packaged schema and skill match canonical assets', async () => {
  const root = new URL('../../../', import.meta.url)
  assert.equal(await readFile(new URL('../tools.json', import.meta.url), 'utf8'),
    await readFile(new URL('src/yt_agent/tools.json', root), 'utf8'))
})
