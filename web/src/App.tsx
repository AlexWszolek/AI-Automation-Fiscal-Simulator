// Phase-1 shell: the two-column layout (lever rail + content column) with the design system
// live. Phase 2 replaces the placeholders with the real preset/lever/metric/chart components.
import grid from './gen/grid.json'
import { dollarsHero, pct } from './lib/format'

export default function App() {
  return (
    <div className="shell">
      <aside className="rail">
        <h3>Scenario</h3>
        <p className="caption">
          {grid.presets.length} presets · {grid.overlays.length} policy responses ·{' '}
          {Object.keys(grid.grid).length} levers (Phase 2 wires the controls)
        </p>
      </aside>
      <main className="content">
        <div className="col">
          <h1>Fiscal Consequences of AI Automation</h1>
          <p className="caption">
            Design-system proof: hero figures {dollarsHero(2674)} and{' '}
            <span className="num">{pct(-29)}</span> render in mono tabular-nums with the true
            minus; this paragraph is the Times New Roman stack on warm near-white.
          </p>
        </div>
      </main>
    </div>
  )
}
