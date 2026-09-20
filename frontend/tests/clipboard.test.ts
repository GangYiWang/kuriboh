import { afterEach, describe, expect, it, vi } from 'vitest'

import { copyText } from '../src/utils/clipboard'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('copyText', () => {
  it('uses the Clipboard API when it is available', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })

    await copyText('account-value')

    expect(writeText).toHaveBeenCalledWith('account-value')
  })

  it('falls back to a selected textarea when Clipboard API access is denied', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('permission denied'))
    const focus = vi.fn()
    const select = vi.fn()
    const setSelectionRange = vi.fn()
    const remove = vi.fn()
    const textarea = {
      value: '',
      readOnly: false,
      style: {},
      focus,
      select,
      setSelectionRange,
      remove,
    } as unknown as HTMLTextAreaElement
    const appendChild = vi.fn()
    const execCommand = vi.fn().mockReturnValue(true)
    const documentStub = {
      createElement: vi.fn().mockReturnValue(textarea),
      body: { appendChild },
      execCommand,
    } as unknown as Document
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    vi.stubGlobal('document', documentStub)

    await copyText('password-value')

    expect(writeText).toHaveBeenCalledWith('password-value')
    expect(textarea.value).toBe('password-value')
    expect(appendChild).toHaveBeenCalledWith(textarea)
    expect(focus).toHaveBeenCalledOnce()
    expect(select).toHaveBeenCalledOnce()
    expect(setSelectionRange).toHaveBeenCalledWith(0, 'password-value'.length)
    expect(execCommand).toHaveBeenCalledWith('copy')
    expect(remove).toHaveBeenCalledOnce()
  })

  it('reports failure when both copy methods are unavailable', async () => {
    const textarea = {
      value: '',
      readOnly: false,
      style: {},
      focus: vi.fn(),
      select: vi.fn(),
      setSelectionRange: vi.fn(),
      remove: vi.fn(),
    } as unknown as HTMLTextAreaElement
    const documentStub = {
      createElement: vi.fn().mockReturnValue(textarea),
      body: { appendChild: vi.fn() },
      execCommand: vi.fn().mockReturnValue(false),
    } as unknown as Document
    vi.stubGlobal('navigator', {})
    vi.stubGlobal('document', documentStub)

    await expect(copyText('value')).rejects.toThrow('COPY_COMMAND_REJECTED')
    expect(textarea.remove).toHaveBeenCalledOnce()
  })
})
