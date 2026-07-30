// Give Feedback (testers): a sidebar-footer button opening a small dialog that POSTs to
// /api/feedback (message + optional contact + the current share-URL, so a report pins the exact
// configuration being looked at). Degrades gracefully when the compute service is down: the
// text stays in the box and the failure line says so.
//
// COPY NOTE: all strings below are inline UI chrome (the AboutModal convention) and are
// PLACEHOLDERS awaiting the copyedit round — edit freely, nothing else depends on the wording.
import { useRef, useState } from 'react'

type SendState = 'idle' | 'sending' | 'sent' | 'failed'

export function FeedbackSection() {
  const dlg = useRef<HTMLDialogElement>(null)
  const [message, setMessage] = useState('')
  const [contact, setContact] = useState('')
  const [status, setStatus] = useState<SendState>('idle')

  const submit = () => {
    const msg = message.trim()
    if (!msg || status === 'sending') return
    setStatus('sending')
    fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, contact: contact.trim(), url: location.href }),
    })
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status))
        setStatus('sent')
        setMessage('')
      })
      .catch(() => setStatus('failed'))
  }

  return (
    <>
      <button
        className="dl feedback-open"
        onClick={() => {
          setStatus('idle')
          dlg.current?.showModal()
        }}
      >
        Give feedback
      </button>
      <dialog ref={dlg} className="feedback-dialog">
        <div className="dialog-head">
          <h3>Give feedback</h3>
          <button className="dialog-x" aria-label="Close" onClick={() => dlg.current?.close()}>
            ×
          </button>
        </div>
        <div className="dialog-body feedback-body">
          <p className="caption">
            Anything helps — a confusing number, a broken chart, a lever that reads wrong. Your
            current configuration is attached automatically.
          </p>
          <textarea
            className="feedback-text"
            rows={6}
            maxLength={5000}
            placeholder="What did you find?"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <input
            className="feedback-contact"
            type="text"
            maxLength={200}
            placeholder="Email or name (optional, for follow-up)"
            value={contact}
            onChange={(e) => setContact(e.target.value)}
          />
          <div className="feedback-row">
            <button className="dl" disabled={!message.trim() || status === 'sending'} onClick={submit}>
              {status === 'sending' ? 'Sending…' : 'Send'}
            </button>
            {status === 'sent' && <span className="caption">Received — thank you.</span>}
            {status === 'failed' && (
              <span className="caption feedback-fail">
                Could not reach the feedback service — your text is kept here; please try again
                later.
              </span>
            )}
          </div>
        </div>
      </dialog>
    </>
  )
}
