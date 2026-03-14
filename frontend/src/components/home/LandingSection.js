export function LandingSection({ id, eyebrow, title, description, children, className = "" }) {
  return (
    <section id={id} className={`relative ${className}`}>
      {(eyebrow || title || description) ? (
        <div className="mx-auto max-w-3xl text-center">
          {eyebrow ? <p className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-300">{eyebrow}</p> : null}
          {title ? <h2 className="mt-4 text-3xl font-semibold tracking-tight text-app sm:text-4xl">{title}</h2> : null}
          {description ? <p className="mt-4 text-base leading-7 text-app-secondary">{description}</p> : null}
        </div>
      ) : null}
      <div className={title || description || eyebrow ? "mt-10" : ""}>{children}</div>
    </section>
  );
}

export function SurfaceFrame({ children, className = "" }) {
  return <div className={`surface-card ${className}`}>{children}</div>;
}
