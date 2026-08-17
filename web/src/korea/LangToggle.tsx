// The EN/KR segmented toggle — compact, lives at the top of the rail (app) and the
// content head (presenter/deck). The label strings are the languages' own names, so
// they are not copy slots.
import type { Lang } from './locale'

export function LangToggle({ lang, setLang }: { lang: Lang; setLang: (l: Lang) => void }) {
  return (
    <div className="lang-toggle" role="group" aria-label="Language">
      {(['en', 'ko'] as const).map((l) => (
        <button key={l} type="button"
                className={lang === l ? 'lang-btn active' : 'lang-btn'}
                aria-pressed={lang === l}
                onClick={() => setLang(l)}>
          {l === 'en' ? 'EN' : '한국어'}
        </button>
      ))}
    </div>
  )
}
