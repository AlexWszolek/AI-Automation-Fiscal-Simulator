// The EN/KR locale layer for the Korea surfaces. English lives in copy.json (canonical);
// Korean in copy.ko.json (machine placeholder until the diplomats' professional pass,
// which replaces values in that one file). Missing Korean keys FALL BACK to English per
// key, so a partial translation never blanks the page.
//
// Language resolution: ?lang=ko|en wins (shareable links, deck export), then
// localStorage, then English. The chosen language persists and sets <html lang>.
import { useEffect, useState } from 'react'
import en from '../content/copy.json'
import ko from '../content/copy.ko.json'
import { KOREA_PRESETS } from './config'

export type Lang = 'en' | 'ko'
const STORAGE_KEY = 'korea-lang'

function deepMerge<T>(base: T, over: unknown): T {
  if (over === undefined || over === null) return base
  if (Array.isArray(base) && Array.isArray(over)) {
    return base.map((v, i) => (i < over.length ? deepMerge(v, over[i]) : v)) as T
  }
  if (typeof base === 'object' && base !== null && typeof over === 'object') {
    const out: Record<string, unknown> = { ...(base as Record<string, unknown>) }
    for (const [k, v] of Object.entries(over as Record<string, unknown>)) {
      out[k] = k in out ? deepMerge(out[k], v) : v
    }
    return out as T
  }
  return over as T
}

export interface LocalePack {
  KO: any                                        // the korea copy block (merged)
  lever: (gridCopyRef: string) => { label: string; help: string | null }
  group: (title: string) => string
  preset: (key: string) => { name: string; blurb: string }
  shared: { share_heading: string; copy_button: string; copied: string }
}

const EN_SHARED = { share_heading: 'Share this configuration', copy_button: 'Copy',
                    copied: 'Copied!' }

function buildPack(lang: Lang): LocalePack {
  const koreaBlock = lang === 'ko'
    ? deepMerge((en as any).korea, (ko as any).korea)
    : (en as any).korea
  const usLevers = lang === 'ko'
    ? deepMerge((en as any).levers, (ko as any).levers)
    : (en as any).levers
  const groups: Record<string, string> = lang === 'ko' ? (ko as any).groups : {}
  const presets: Record<string, { name: string; blurb: string }> =
    lang === 'ko' ? (ko as any).presets : {}
  const shared = lang === 'ko'
    ? { ...EN_SHARED, ...(ko as any).shared }
    : EN_SHARED
  return {
    KO: koreaBlock,
    lever: (ref: string) => {
      if (ref.startsWith('us:')) return usLevers[ref.slice(3)]
      const kr = (koreaBlock.rail?.levers ?? {})[ref.slice(3)]
      return kr ?? { label: ref, help: null }
    },
    group: (title: string) =>
      title === 'KOREA_AXES' ? String(koreaBlock.rail?.axes_group ?? title)
        : (groups[title] ?? title),
    preset: (key: string) => {
      const p = KOREA_PRESETS.find((x) => x.key === key)
      const base = { name: p?.name ?? key, blurb: p?.blurb ?? '' }
      return { ...base, ...(presets[key] ?? {}) }
    },
    shared,
  }
}

const PACKS: Record<Lang, LocalePack> = { en: buildPack('en'), ko: buildPack('ko') }

export function initialLang(): Lang {
  const q = new URLSearchParams(location.search).get('lang')
  if (q === 'ko' || q === 'en') return q
  const stored = localStorage.getItem(STORAGE_KEY)
  return stored === 'ko' ? 'ko' : 'en'
}

export function useLocale(): { lang: Lang; setLang: (l: Lang) => void; pack: LocalePack } {
  const [lang, setLangState] = useState<Lang>(initialLang)
  useEffect(() => {
    document.documentElement.lang = lang
    localStorage.setItem(STORAGE_KEY, lang)
  }, [lang])
  return { lang, setLang: setLangState, pack: PACKS[lang] }
}

/** Non-hook access for modules that render outside React state (deck export mode). */
export function packFor(lang: Lang): LocalePack {
  return PACKS[lang]
}
