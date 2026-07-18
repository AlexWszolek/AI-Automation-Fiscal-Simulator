// A deliberately tiny markdown renderer for the ported prose (About, Learn-more): ####
// headings, paragraphs, **bold**, *italic*, [links](url), - lists, | tables, \n\n breaks.
// Anything fancier belongs in real TSX, not markdown.
import type { ReactNode } from 'react'

function inline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = []
  // links first, then bold, then italics — non-greedy, no nesting
  const parts = text.split(/(\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|\*[^*]+\*)/g)
  parts.forEach((p, i) => {
    const key = `${keyBase}-${i}`
    const link = p.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (link) out.push(<a key={key} href={link[2]} target="_blank" rel="noreferrer">{link[1]}</a>)
    else if (p.startsWith('**') && p.endsWith('**')) out.push(<strong key={key}>{p.slice(2, -2)}</strong>)
    else if (p.startsWith('*') && p.endsWith('*') && p.length > 2) out.push(<em key={key}>{p.slice(1, -1)}</em>)
    else if (p) out.push(p)
  })
  return out
}

export function Markdown({ text }: { text: string }) {
  const blocks = text.split(/\n\s*\n/)
  return (
    <>
      {blocks.map((block, bi) => {
        const b = block.trim()
        if (!b) return null
        if (b.startsWith('####'))
          return <h4 key={bi}>{inline(b.replace(/^#+\s*/, ''), `h${bi}`)}</h4>
        const lines = b.split('\n')
        if (lines.every((l) => l.trim().startsWith('|'))) {
          const rows = lines.map((l) => l.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim()))
          const body = rows.filter((r) => !r.every((c) => /^:?-+:?$/.test(c)))
          const [head, ...rest] = body
          return (
            <div key={bi} className="table-scroll">
              <table className="data-table">
                <thead><tr>{head.map((c, i) => <th key={i}>{inline(c, `t${bi}-${i}`)}</th>)}</tr></thead>
                <tbody>
                  {rest.map((r, ri) => (
                    <tr key={ri}>{r.map((c, ci) => <td key={ci}>{inline(c, `t${bi}-${ri}-${ci}`)}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }
        if (lines.every((l) => /^\s*(-|\d+\.)\s/.test(l))) {
          const ordered = /^\s*\d+\./.test(lines[0])
          const items = lines.map((l, li) => (
            <li key={li}>{inline(l.replace(/^\s*(-|\d+\.)\s*/, ''), `l${bi}-${li}`)}</li>
          ))
          return ordered ? <ol key={bi}>{items}</ol> : <ul key={bi}>{items}</ul>
        }
        return <p key={bi}>{inline(b.replace(/\n/g, ' '), `p${bi}`)}</p>
      })}
    </>
  )
}
