/** Subtle animated cricket backdrop: pitch lines, a drifting ball arc and a slow timeline pulse. Purely decorative. */
export default function HeroBackground() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="pitch-bg absolute inset-0" />
      <div className="stumps-lines absolute inset-0" />
      <svg className="absolute -right-24 top-6 w-[640px] max-w-none animate-drift opacity-60" viewBox="0 0 640 360" fill="none">
        <path d="M20 330C170 40 430 20 620 210" className="stroke-accent" strokeOpacity=".35" strokeWidth="2" strokeDasharray="6 10" />
        <circle cx="620" cy="210" r="14" className="fill-accent" fillOpacity=".9" />
        <path d="M611 200c4 6 4 14 0 20M629 200c-4 6-4 14 0 20" className="stroke-accent-ink" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <svg className="absolute bottom-0 left-0 w-full opacity-40" viewBox="0 0 1200 120" preserveAspectRatio="none" fill="none">
        <path d="M0 80h260l30-34 40 70 34-56 30 20h180l30-30 40 56 30-36h120l30-24 40 50 30-26h280" className="stroke-sky" strokeOpacity=".5" strokeWidth="1.5" />
      </svg>
    </div>
  )
}
