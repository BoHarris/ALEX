import { Link } from "react-router-dom";

export default function SiteFooter() {
  return (
    <footer className="border-t border-app bg-app/95 px-6 py-10 text-app-secondary">
      <div className="mx-auto grid max-w-7xl gap-6 md:grid-cols-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-app">ALEX</p>
          <p className="mt-3 text-sm leading-6">
            Privacy workflows made practical for teams handling sensitive datasets.
          </p>
        </div>
        <div>
          <p className="text-app text-sm font-semibold uppercase tracking-[0.2em]">Product</p>
          <div className="mt-3 space-y-2 text-sm">
            <Link to="/pricing" className="block hover:text-app">Plans</Link>
            <Link to="/trust" className="block hover:text-app">Trust Center</Link>
            <Link to="/privacy" className="block hover:text-app">Privacy Policy</Link>
            <Link to="/dashboard" className="block hover:text-app">Dashboard</Link>
          </div>
        </div>
        <div>
          <p className="text-app text-sm font-semibold uppercase tracking-[0.2em]">Company</p>
          <div className="mt-3 space-y-2 text-sm">
            <Link to="/about" className="block hover:text-app">About</Link>
            <Link to="/careers" className="block hover:text-app">Careers</Link>
            <a href="mailto:support@alexprivacy.local" className="block hover:text-app">Contact Support</a>
          </div>
        </div>
      </div>
      <p className="text-app-muted mx-auto mt-8 max-w-7xl text-xs">ALEX beta. Security posture and controls continue to evolve through pilot feedback.</p>
    </footer>
  );
}
