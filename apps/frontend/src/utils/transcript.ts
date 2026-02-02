/**
 * Strip content between square brackets so noise markers are not shown.
 * Examples: [typing], [background noise], [cough], [silence], [ ... ]
 * If result is empty or only whitespace, return placeholder (e.g. "…").
 */
export function stripBracketedMarkers(text: string): string {
  if (!text?.trim()) return ''
  const cleaned = text.replace(/\s*\[[^\]]*\]\s*/g, ' ').replace(/\s+/g, ' ').trim()
  return cleaned || '…'
}
