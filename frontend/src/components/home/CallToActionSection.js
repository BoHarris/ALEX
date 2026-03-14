import { Link } from "react-router-dom";
import { ArrowIcon } from "./HomeIcons";

export default function CallToActionSection() {
  return (
    <section className="relative overflow-hidden rounded-[2.4rem] border border-cyan-300/15 bg-[radial-gradient(circle_at_top_right,rgba(34,211,238,0.2),transparent_28%),linear-gradient(145deg,rgba(6,17,38,0.92),rgba(2,8,23,0.98))] px-6 py-12 shadow-[0_30px_100px_rgba(2,8,23,0.5)] sm:px-10 sm:py-14">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-300/80 to-transparent" />
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-200">Get Started</p>
        <h2 className="mt-4 text-3xl font-semibold tracking-tight text-app sm:text-4xl">Protect Sensitive Data Before It Leaks</h2>
        <p className="mt-5 text-base leading-7 text-app-secondary">
          Run your first privacy scan in seconds and see how ALEX detects and redacts sensitive data automatically.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link to="/register" className="btn-primary-app inline-flex items-center gap-2 text-sm">
            Start Free Scan
            <ArrowIcon />
          </Link>
          <a
            href="https://github.com/BoHarris/ALEX#readme"
            target="_blank"
            rel="noreferrer"
            className="btn-secondary-app inline-flex items-center gap-2 text-sm"
          >
            View Documentation
            <ArrowIcon />
          </a>
        </div>
      </div>
    </section>
  );
}
