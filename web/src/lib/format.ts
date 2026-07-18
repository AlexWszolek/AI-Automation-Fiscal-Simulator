// Number formatting: true minus everywhere, hero-scale abbreviation, exact $B in tables.
export const MINUS = '−'

/** Replace an ASCII hyphen-minus sign with the true minus. */
export function trueMinus(s: string): string {
  return s.replace(/-/g, MINUS)
}

/** 1234.5 -> "1,235" (no sign handling beyond the locale's). */
export function thousands(v: number, digits = 0): string {
  return trueMinus(v.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }))
}

/** Signed figure with explicit + / true − prefix: +7.9, −664. */
export function signed(v: number, digits = 0): string {
  const s = thousands(Math.abs(v), digits)
  return v < 0 ? `${MINUS}${s}` : `+${s}`
}

/** Dollar billions, exact: "$2,674B" / "−$664B". Tables and second-tier metrics. */
export function dollarsB(v: number, digits = 0): string {
  const s = `$${thousands(Math.abs(v), digits)}B`
  return v < 0 ? `${MINUS}${s}` : s
}

/** Hero-scale dollars: abbreviate ≥ $1,000B to trillions — "$2.67T"; below that "$664B". */
export function dollarsHero(v: number): string {
  const a = Math.abs(v)
  const s = a >= 1000 ? `$${(a / 1000).toLocaleString('en-US', {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  })}T` : `$${thousands(a)}B`
  return v < 0 ? `${MINUS}${s}` : s
}

/** Percent with true minus: pct(-29) -> "−29%". */
export function pct(v: number, digits = 0): string {
  return `${trueMinus(v.toLocaleString('en-US', {
    minimumFractionDigits: digits, maximumFractionDigits: digits,
  }))}%`
}
