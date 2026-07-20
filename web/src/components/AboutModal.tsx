// Share + About (the sidebar footer): the share link with copy button, the About text, and
// the Learn-more dialog — content is the app's, byte-for-byte (content/copy.json).
import { useRef, useState } from 'react'
import copy from '../content/copy.json'
import { Markdown } from '../content/md'

const PROSE = copy.prose as Record<string, string>

export function ShareBox({ queryString }: { queryString: string }) {
  const [copied, setCopied] = useState(false)
  const url = `${location.origin}${location.pathname}${queryString ? `?${queryString}` : ''}`
  return (
    <details className="group">
      <summary>Share this configuration</summary>
      <div className="share-row">
        <input className="num share-url" readOnly value={url} onFocus={(e) => e.target.select()} />
        <button
          className="dl"
          onClick={() => {
            void navigator.clipboard.writeText(url).then(() => {
              setCopied(true)
              setTimeout(() => setCopied(false), 1500)
            })
          }}
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <p className="caption">{PROSE.share_caption}</p>
    </details>
  )
}

export function AboutSection() {
  const dlg = useRef<HTMLDialogElement>(null)
  return (
    <details className="group">
      <summary>About this model</summary>
      <div className="about-body">
        <Markdown text={copy.about as string} />
        <button className="dl" onClick={() => dlg.current?.showModal()}>
          Learn more — the model in 900 words
        </button>
      </div>
      <dialog ref={dlg}>
        <div className="dialog-head">
          <h3>How the model works</h3>
          <button className="dialog-x" aria-label="Close"
                  onClick={() => dlg.current?.close()}>×</button>
        </div>
        <div className="dialog-body">
          <Markdown text={(copy.learn_more as string).replace(/\\\$/g, '$')} />
        </div>
      </dialog>
    </details>
  )
}
