import { useId, useState } from "react";

const individualCards = [
  {
    title: "Our Privacy Philosophy",
    summary: "Privacy should be understandable. We believe people deserve to know how their data is handled.",
    content: [
      "ALEX is built around the belief that privacy is a fundamental human right.",
      "Many technology platforms collect large amounts of information while making it difficult for people to understand how their data is used. We believe this approach creates confusion and unnecessary risk.",
      "ALEX was designed with a different goal. The platform exists to help organizations identify sensitive information and reduce unnecessary exposure of that information.",
      "Because of this, we try to minimize the amount of data collected, limit how long sensitive data is stored, and provide clear explanations of how information is handled.",
      "Privacy should not require a law degree to understand.",
    ],
  },
  {
    title: "Our Plain Language Commitment",
    summary: "We commit to explaining our privacy practices in clear language.",
    content: [
      "Privacy policies are often written in dense legal or technical language that makes them difficult to understand.",
      "ALEX makes a deliberate effort to avoid overly technical wording whenever possible. Our goal is to explain how the platform works in language that normal people can read and understand.",
      "We believe transparency should be practical, not complicated.",
      "When technical concepts are necessary, we aim to explain them clearly so that users can understand what is happening with their data.",
    ],
  },
  {
    title: "Information We Collect",
    summary: "We collect only the information needed to operate the platform.",
    content: [
      "When you interact with ALEX, we may collect limited information such as:",
    ],
    bullets: [
      "Name",
      "Email address",
      "Account credentials",
      "Activity required to operate the service",
    ],
    trailing: [
      "If you upload files to ALEX for scanning, those files are processed so the platform can detect and redact sensitive information.",
      "We may also collect limited operational information such as timestamps, system logs, and security events. These help us maintain the platform and protect it from misuse.",
    ],
  },
  {
    title: "Information We Do Not Collect",
    summary: "ALEX is designed to avoid unnecessary data collection.",
    content: [
      "ALEX is designed to minimize unnecessary data collection whenever possible.",
      "In general:",
    ],
    bullets: [
      "We do not sell personal information",
      "We do not use uploaded files to train AI models",
      "We do not intentionally collect more information than needed to provide the service",
    ],
    trailing: [
      "Our goal is to reduce the exposure of sensitive information, not increase it.",
    ],
  },
  {
    title: "How Uploaded Files Are Handled",
    summary: "Files are processed so ALEX can detect and redact sensitive information.",
    content: [
      "When a file is uploaded to ALEX, the system analyzes it to detect sensitive information such as personal identifiers or confidential data.",
      "The system may produce:",
    ],
    bullets: [
      "redacted versions of the file",
      "scan summaries",
      "risk reports",
    ],
    trailing: [
      "Access to uploaded files and generated outputs is restricted to authorized users within the account.",
      "ALEX processes files only for the purpose of providing scanning and redaction services.",
    ],
  },
  {
    title: "Data Retention",
    summary: "Data is kept only as long as needed to operate the service.",
    content: [
      "ALEX retains information only for as long as necessary to operate the platform and provide expected features.",
      "Examples of stored information may include:",
    ],
    bullets: [
      "scan results",
      "generated reports",
      "operational system logs",
    ],
    trailing: [
      "Retention policies may evolve as the platform develops additional data management controls.",
      "Our goal is always to minimize unnecessary storage of sensitive information.",
    ],
  },
  {
    title: "Security Practices",
    summary: "We use security controls designed to protect user data.",
    content: [
      "ALEX uses technical and organizational measures designed to protect information processed within the platform.",
      "Examples may include:",
    ],
    bullets: [
      "authentication controls",
      "access restrictions",
      "system monitoring",
      "audit logging",
    ],
    trailing: [
      "These measures help protect the platform and reduce the risk of unauthorized access.",
    ],
  },
  {
    title: "Third-Party Services",
    summary: "Infrastructure providers help operate the platform.",
    content: [
      "Like most online services, ALEX relies on infrastructure providers for services such as hosting, storage, and networking.",
      "These providers help ensure that the platform operates reliably and securely.",
      "ALEX works to choose infrastructure partners that maintain strong security and privacy practices.",
    ],
  },
];

const organizationCards = [
  {
    title: "Role of ALEX",
    summary: "Organizations control the data they submit.",
    content: [
      "When an organization uses ALEX, the organization controls the data it submits to the platform.",
      "ALEX processes that data in order to provide scanning, detection, and redaction services.",
      "The organization remains responsible for ensuring that the data it submits complies with applicable laws and internal policies.",
    ],
  },
  {
    title: "Data Processing",
    summary: "ALEX processes data only to provide the service.",
    content: [
      "ALEX processes files and datasets submitted by organizations in order to perform the platform’s core functions, including:",
    ],
    bullets: [
      "sensitive data detection",
      "redaction",
      "scan reporting",
      "compliance analysis",
    ],
    trailing: [
      "We do not process organizational data for unrelated purposes.",
    ],
  },
  {
    title: "Access Controls",
    summary: "Access to organizational data is restricted.",
    content: [
      "Organizations control which users can access their data within the platform.",
      "Access to internal operational systems is restricted to authorized personnel when required to maintain the service.",
    ],
  },
  {
    title: "Data Ownership",
    summary: "Organizations retain ownership of their data.",
    content: [
      "Organizations remain the owners of the data they submit to ALEX.",
      "ALEX provides tools that analyze and protect that data but does not claim ownership of customer datasets.",
    ],
  },
];

function PolicyCard({ title, summary, content, bullets = [], trailing = [] }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  return (
    <article className="surface-card overflow-hidden rounded-[1.75rem] border border-app/80 p-6 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <h3 className="text-xl font-semibold text-app">{title}</h3>
          <p className="mt-3 text-sm leading-7 text-app-secondary">{summary}</p>
        </div>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((value) => !value)}
          className="btn-primary-app shrink-0 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
        >
          {open ? "Hide Full Details" : "Read Full Details"}
        </button>
      </div>
      <div
        id={panelId}
        className={`grid transition-[grid-template-rows,opacity] duration-300 ease-out ${open ? "mt-6 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}
      >
        <div className="overflow-hidden">
          <div className="rounded-2xl border border-app bg-app/50 px-5 py-5 text-sm leading-7 text-app-secondary">
            {content.map((paragraph) => (
              <p key={paragraph} className="mb-4 last:mb-0">
                {paragraph}
              </p>
            ))}
            {bullets.length ? (
              <ul className="mb-4 list-disc space-y-2 pl-5">
                {bullets.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
            {trailing.map((paragraph) => (
              <p key={paragraph} className="mb-4 last:mb-0">
                {paragraph}
              </p>
            ))}
          </div>
        </div>
      </div>
    </article>
  );
}

function PolicySection({ eyebrow, title, subtitle, cards }) {
  return (
    <section className="space-y-5">
      <div className="surface-panel rounded-[2rem] p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-app-muted">{eyebrow}</p>
        <h2 className="mt-4 text-3xl font-semibold tracking-tight text-app">{title}</h2>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-app-secondary">{subtitle}</p>
      </div>
      <div className="space-y-4">
        {cards.map((card) => (
          <PolicyCard key={card.title} {...card} />
        ))}
      </div>
    </section>
  );
}

export default function Privacy() {
  return (
    <div className="page-shell px-6 py-12">
      <div className="mx-auto max-w-6xl space-y-8">
        <section className="surface-panel rounded-[2rem] p-10">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-app-muted">Privacy Policy</p>
          <h1 className="mt-4 max-w-4xl text-4xl font-semibold leading-tight text-app sm:text-5xl">
            Privacy information written for people, not just lawyers.
          </h1>
          <p className="mt-5 max-w-3xl text-sm leading-7 text-app-secondary">
            This page explains how ALEX handles information in plain English. Each topic starts with a short summary, and you can expand any card to read the full policy text.
          </p>
        </section>

        <PolicySection
          eyebrow="Section 1"
          title="Privacy for Individuals"
          subtitle="How ALEX handles information when individuals interact with the platform."
          cards={individualCards}
        />

        <PolicySection
          eyebrow="Section 2"
          title="Privacy for Organizations Using ALEX"
          subtitle="How ALEX handles data when businesses use the platform."
          cards={organizationCards}
        />

        <section className="surface-card rounded-[1.75rem] p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-app-muted">Contact</p>
          <h2 className="mt-4 text-2xl font-semibold text-app">Contact</h2>
          <p className="mt-4 text-sm leading-7 text-app-secondary">
            If you have questions about this policy or about how ALEX handles information, you can contact us at:
          </p>
          <p className="mt-4 text-sm font-medium text-app">
            <a href="mailto:privacy@alexprivacy.com" className="underline decoration-cyan-400/60 underline-offset-4 hover:text-app-secondary">
              privacy@alexprivacy.com
            </a>
          </p>
        </section>
      </div>
    </div>
  );
}
