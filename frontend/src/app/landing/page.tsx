"use client";

import Link from "next/link";
import { EB_Garamond, IBM_Plex_Mono } from "next/font/google";
import { useEffect, useState } from "react";

const garamond = EB_Garamond({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  style: ["normal", "italic"],
  variable: "--font-garamond",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
});

const features = [
  {
    id: "01",
    label: "Import",
    labelColor: "#52b788",
    accent: "#2d6a4f",
    title: "From arXiv to your archive.",
    body: "Paste an arXiv or DOI link, or drag-and-drop a PDF. Metadata is extracted automatically — title, authors, abstract — catalogued and ready.",
  },
  {
    id: "02",
    label: "Organize",
    labelColor: "#f0bc30",
    accent: "#c8901a",
    title: "Status, keywords, search.",
    body: "Move papers through to_read → reading → completed. Tag with keywords. Full-text search across your entire library in milliseconds.",
  },
  {
    id: "03",
    label: "Track",
    labelColor: "#7bb8f0",
    accent: "#2a5a9a",
    title: "Visualize your scholarship.",
    body: "A GitHub-style heatmap reveals your reading activity over the past year. See streaks, top keywords, and recently read papers.",
  },
];

const steps = [
  { num: "I", title: "Import", desc: "Add a paper via arXiv / DOI link or drag-and-drop PDF upload." },
  { num: "II", title: "Read", desc: "Work through your queue. Update status as you progress." },
  { num: "III", title: "Complete", desc: "Mark as done and watch your reading heatmap grow day by day." },
];

const HEATMAP_DATA = Array.from({ length: 52 * 7 }, (_, i) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453123;
  const rand = x - Math.floor(x);
  const week = Math.floor(i / 7);
  const recency = week / 52;
  const threshold = 0.55 - recency * 0.22;
  if (rand < threshold) return 0;
  if (rand < 0.74) return 1;
  if (rand < 0.87) return 2;
  if (rand < 0.94) return 3;
  return 4;
});

const MARQUEE_ITEMS = [
  "Import PDFs", "Organize by Status", "Search Your Library",
  "Track Reading Streaks", "arXiv & DOI Import", "Activity Heatmap",
  "Keyword Tags", "Reading History", "Completion Tracking",
];

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const heatmapColors = ["#151d2e", "#1a3d2c", "#2d6a4f", "#40a06e", "#52c88e"];

  return (
    <div
      className={`${garamond.variable} ${mono.variable}`}
      style={{ fontFamily: "var(--font-garamond)", backgroundColor: "#0b0f1a", color: "#ede8dc", overflowX: "hidden" }}
    >
      <style>{`
        :root {
          --ink: #0b0f1a;
          --ink-2: #0f1520;
          --paper: #f5efe2;
          --forest: #2d6a4f;
          --forest-l: #52b788;
          --amber: #c8901a;
          --amber-l: #f0bc30;
          --mist: rgba(237,232,220,0.06);
          --g: var(--font-garamond);
          --m: var(--font-mono);
        }

        .pb-nav {
          position: fixed; top: 0; left: 0; right: 0; z-index: 100;
          display: flex; align-items: center; justify-content: space-between;
          padding: 0 clamp(1.5rem, 4vw, 3rem); height: 64px;
          transition: background 0.35s ease, border-color 0.35s ease;
        }
        .pb-nav.scrolled {
          background: rgba(11,15,26,0.88);
          backdrop-filter: blur(14px);
          -webkit-backdrop-filter: blur(14px);
          border-bottom: 1px solid rgba(237,232,220,0.09);
        }

        .pb-logo {
          font-family: var(--g); font-size: 1.35rem; font-weight: 700;
          letter-spacing: -0.025em; color: var(--paper); text-decoration: none;
        }
        .pb-logo em { font-style: italic; color: var(--amber-l); }

        .pb-nav-links { display: flex; align-items: center; gap: 1.5rem; }
        .pb-nav-link {
          font-family: var(--m); font-size: 0.72rem; letter-spacing: 0.1em;
          color: rgba(237,232,220,0.55); text-decoration: none; text-transform: uppercase;
          transition: color 0.2s;
        }
        .pb-nav-link:hover { color: var(--paper); }
        .pb-btn {
          font-family: var(--m); font-size: 0.72rem; letter-spacing: 0.07em;
          text-transform: uppercase; text-decoration: none;
          padding: 0.5rem 1.3rem; border-radius: 2px; transition: all 0.22s;
          cursor: pointer; display: inline-block;
        }
        .pb-btn-ghost {
          border: 1px solid rgba(237,232,220,0.28); color: var(--paper); background: transparent;
        }
        .pb-btn-ghost:hover { background: rgba(237,232,220,0.08); border-color: rgba(237,232,220,0.55); }
        .pb-btn-primary {
          background: var(--forest); border: 1px solid var(--forest); color: #fff;
        }
        .pb-btn-primary:hover { background: #3a7c5f; border-color: #3a7c5f; transform: translateY(-1px); }
        .pb-btn-lg { padding: 0.85rem 2.2rem; font-size: 0.78rem; }

        /* Hero */
        .pb-hero {
          min-height: 100vh; display: flex; align-items: center;
          padding: 120px clamp(1.5rem, 4vw, 3rem) 80px;
          position: relative; overflow: hidden;
          background-image:
            radial-gradient(ellipse 70% 55% at 55% 45%, rgba(45,106,79,0.1) 0%, transparent 65%),
            url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32'%3E%3Ccircle cx='0.5' cy='0.5' r='0.5' fill='rgba(237%2C232%2C220%2C0.12)'/%3E%3C/svg%3E");
        }
        .pb-hero-inner {
          max-width: 1240px; margin: 0 auto; width: 100%;
          display: grid; grid-template-columns: 55fr 45fr; gap: 3rem; align-items: center;
        }

        .pb-eyebrow {
          font-family: var(--m); font-size: 0.68rem; letter-spacing: 0.22em;
          text-transform: uppercase; color: var(--forest-l);
          margin-bottom: 1.75rem; display: flex; align-items: center; gap: 0.8rem;
        }
        .pb-eyebrow::before { content: ''; display: block; width: 22px; height: 1px; background: var(--forest-l); }

        .pb-hero-h1 {
          font-family: var(--g); font-size: clamp(3.2rem, 5.5vw, 5.75rem);
          font-weight: 500; line-height: 1.07; letter-spacing: -0.025em;
          color: var(--paper); margin-bottom: 1.75rem;
        }
        .pb-hero-h1 em { font-style: italic; color: var(--amber-l); }

        .pb-hero-sub {
          font-family: var(--g); font-size: 1.12rem; line-height: 1.75;
          color: rgba(237,232,220,0.65); max-width: 500px; margin-bottom: 2.5rem;
        }

        .pb-hero-ctas { display: flex; gap: 1rem; flex-wrap: wrap; }

        /* Floating specimen cards */
        .pb-hero-visual {
          position: relative; height: 500px;
        }
        .pb-specimen {
          position: absolute; width: 278px; padding: 1.4rem 1.6rem;
          background: #f5efe2; border-radius: 2px;
          box-shadow: 0 24px 64px rgba(0,0,0,0.45), 0 4px 16px rgba(0,0,0,0.25);
          color: #1a1a1a;
        }
        .pb-specimen-a {
          top: 30px; left: 10px;
          animation: floatA 7s ease-in-out infinite;
        }
        .pb-specimen-b {
          top: 90px; left: 60px; z-index: 2;
          animation: floatB 6s ease-in-out infinite;
        }
        .pb-specimen-c {
          top: 220px; left: 20px; z-index: 1;
          animation: floatC 8s ease-in-out infinite;
        }

        @keyframes floatA {
          0%, 100% { transform: rotate(-4.5deg) translateY(0px); }
          50% { transform: rotate(-3.5deg) translateY(-8px); }
        }
        @keyframes floatB {
          0%, 100% { transform: rotate(2.5deg) translateY(0px); }
          50% { transform: rotate(3.5deg) translateY(-6px); }
        }
        @keyframes floatC {
          0%, 100% { transform: rotate(-1.5deg) translateY(0px); }
          50% { transform: rotate(-0.5deg) translateY(-5px); }
        }

        .pb-spec-catalog {
          font-family: var(--m); font-size: 0.58rem; letter-spacing: 0.16em;
          text-transform: uppercase; color: var(--forest);
          padding-bottom: 0.45rem; margin-bottom: 0.55rem;
          border-bottom: 1px solid rgba(45,106,79,0.28);
          display: flex; justify-content: space-between; align-items: center;
        }
        .pb-spec-title {
          font-family: var(--g); font-size: 0.92rem; font-weight: 600;
          line-height: 1.4; color: #1c1c1c; margin-bottom: 0.45rem;
        }
        .pb-spec-meta {
          font-family: var(--m); font-size: 0.58rem; color: #777; letter-spacing: 0.04em;
          line-height: 1.5; margin-bottom: 0.85rem;
        }
        .pb-spec-badge {
          font-family: var(--m); font-size: 0.55rem; letter-spacing: 0.1em;
          text-transform: uppercase; padding: 0.2rem 0.55rem;
          border-radius: 1px; display: inline-block;
        }
        .pb-spec-badge.done { background: rgba(45,106,79,0.12); color: #2d6a4f; border: 1px solid rgba(45,106,79,0.3); }
        .pb-spec-badge.reading { background: rgba(200,144,26,0.12); color: #b07818; border: 1px solid rgba(200,144,26,0.3); }
        .pb-spec-badge.queue { background: rgba(90,90,90,0.1); color: #888; border: 1px solid rgba(90,90,90,0.2); }

        /* Marquee */
        .pb-marquee {
          overflow: hidden;
          border-top: 1px solid rgba(237,232,220,0.09);
          border-bottom: 1px solid rgba(237,232,220,0.09);
          padding: 0.95rem 0; background: rgba(255,255,255,0.015);
        }
        .pb-marquee-track {
          display: flex; width: max-content; gap: 3rem;
          animation: marquee 28s linear infinite;
          align-items: center;
        }
        .pb-marquee-item {
          font-family: var(--m); font-size: 0.68rem; letter-spacing: 0.16em;
          text-transform: uppercase; color: rgba(237,232,220,0.38);
          white-space: nowrap;
        }
        .pb-marquee-sep { color: var(--amber); font-size: 0.55rem; opacity: 0.7; }
        @keyframes marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }

        /* Section utility */
        .pb-section-tag {
          font-family: var(--m); font-size: 0.64rem; letter-spacing: 0.22em;
          text-transform: uppercase; color: var(--amber-l);
          margin-bottom: 2.5rem; display: flex; align-items: center; gap: 0.8rem;
        }
        .pb-section-tag::after { content: ''; width: 48px; height: 1px; background: var(--amber-l); }

        /* Features */
        .pb-features { padding: 96px clamp(1.5rem, 4vw, 3rem); }
        .pb-features-inner { max-width: 1240px; margin: 0 auto; }
        .pb-features-grid {
          display: grid; grid-template-columns: repeat(3, 1fr);
          border: 1px solid rgba(237,232,220,0.1);
          background: rgba(237,232,220,0.1);
          gap: 1px;
        }
        .pb-feat {
          background: #0b0f1a; padding: 2.75rem 2.5rem;
          position: relative; overflow: hidden; transition: background 0.28s;
        }
        .pb-feat::before {
          content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
          background: var(--feat-accent); opacity: 0.8;
        }
        .pb-feat:hover { background: #0d1520; }
        .pb-feat-num {
          font-family: var(--m); font-size: 0.62rem; letter-spacing: 0.12em;
          color: rgba(237,232,220,0.25); margin-bottom: 2.25rem;
        }
        .pb-feat-label {
          font-family: var(--m); font-size: 0.62rem; letter-spacing: 0.18em;
          text-transform: uppercase; margin-bottom: 0.75rem;
        }
        .pb-feat-title {
          font-family: var(--g); font-size: 1.42rem; font-weight: 500;
          line-height: 1.3; color: var(--paper); margin-bottom: 1rem;
          letter-spacing: -0.01em;
        }
        .pb-feat-body {
          font-family: var(--g); font-size: 0.96rem; line-height: 1.72;
          color: rgba(237,232,220,0.58);
        }

        /* Stats band */
        .pb-stats {
          background: #0d1420;
          border-top: 1px solid rgba(237,232,220,0.07);
          border-bottom: 1px solid rgba(237,232,220,0.07);
          padding: 3.5rem clamp(1.5rem, 4vw, 3rem);
        }
        .pb-stats-inner {
          max-width: 1240px; margin: 0 auto;
          display: grid; grid-template-columns: repeat(4, 1fr); gap: 2rem;
          text-align: center;
        }
        .pb-stat-n {
          font-family: var(--m); font-size: 2.6rem; font-weight: 500;
          color: var(--amber-l); letter-spacing: -0.04em; line-height: 1;
          margin-bottom: 0.45rem;
        }
        .pb-stat-l {
          font-family: var(--m); font-size: 0.62rem; letter-spacing: 0.16em;
          text-transform: uppercase; color: rgba(237,232,220,0.38);
        }

        /* Process */
        .pb-process { padding: 96px clamp(1.5rem, 4vw, 3rem); }
        .pb-process-inner { max-width: 1240px; margin: 0 auto; }
        .pb-process-h {
          font-family: var(--g); font-size: clamp(2rem, 3.5vw, 3rem);
          font-weight: 500; color: var(--paper); margin-bottom: 4.5rem;
          max-width: 520px; line-height: 1.18;
        }
        .pb-process-h em { font-style: italic; color: var(--forest-l); }

        .pb-steps-row {
          display: grid; grid-template-columns: repeat(3, 1fr); gap: 0;
          position: relative;
        }
        .pb-steps-row::after {
          content: ''; position: absolute;
          top: 27px; left: calc(16.67% - 1px); right: calc(16.67% - 1px);
          height: 1px;
          background: linear-gradient(to right, var(--forest) 0%, rgba(45,106,79,0.35) 100%);
          z-index: 0;
        }
        .pb-step-item { padding: 0 2rem 0 0; }
        .pb-step-circle {
          width: 54px; height: 54px; border-radius: 50%;
          border: 1px solid var(--forest); background: #0b0f1a;
          display: flex; align-items: center; justify-content: center;
          font-family: var(--g); font-style: italic; font-size: 1.15rem;
          font-weight: 600; color: var(--forest-l);
          position: relative; z-index: 1; margin-bottom: 1.5rem;
        }
        .pb-step-title {
          font-family: var(--g); font-size: 1.2rem; font-weight: 600;
          color: var(--paper); margin-bottom: 0.5rem;
        }
        .pb-step-desc {
          font-family: var(--g); font-size: 0.92rem; line-height: 1.65;
          color: rgba(237,232,220,0.48);
        }

        /* Heatmap */
        .pb-activity {
          padding: 96px clamp(1.5rem, 4vw, 3rem);
          background: linear-gradient(160deg, #0b0f1a 0%, #0d1520 60%, #0b0f1a 100%);
          position: relative; overflow: hidden;
        }
        .pb-activity::before {
          content: ''; position: absolute; inset: 0; pointer-events: none;
          background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32'%3E%3Ccircle cx='0.5' cy='0.5' r='0.5' fill='rgba(237%2C232%2C220%2C0.06)'/%3E%3C/svg%3E");
        }
        .pb-activity-inner {
          max-width: 1240px; margin: 0 auto;
          display: grid; grid-template-columns: 1fr 1fr; gap: 4.5rem;
          align-items: center; position: relative; z-index: 1;
        }
        .pb-activity-h {
          font-family: var(--g); font-size: clamp(2rem, 3vw, 2.8rem);
          font-weight: 500; line-height: 1.2; color: var(--paper); margin-bottom: 1.4rem;
        }
        .pb-activity-h em { font-style: italic; color: var(--amber-l); }
        .pb-activity-body {
          font-family: var(--g); font-size: 1rem; line-height: 1.8;
          color: rgba(237,232,220,0.58);
        }
        .pb-hm-card {
          background: #0f1520; border: 1px solid rgba(237,232,220,0.1);
          border-radius: 3px; padding: 1.6rem;
        }
        .pb-hm-header {
          font-family: var(--m); font-size: 0.6rem; letter-spacing: 0.14em;
          text-transform: uppercase; color: rgba(237,232,220,0.3);
          margin-bottom: 1rem; display: flex; justify-content: space-between;
        }
        .pb-hm-grid {
          display: grid; grid-template-columns: repeat(52, 1fr); gap: 2px;
        }
        .pb-hm-cell { aspect-ratio: 1/1; border-radius: 1px; }

        /* CTA */
        .pb-cta {
          padding: 120px clamp(1.5rem, 4vw, 3rem) 100px; text-align: center;
          background: linear-gradient(to bottom, #0d1520, #0b0f1a);
        }
        .pb-cta-eyebrow {
          font-family: var(--m); font-size: 0.64rem; letter-spacing: 0.22em;
          text-transform: uppercase; color: var(--forest-l); margin-bottom: 1.5rem;
        }
        .pb-cta-h {
          font-family: var(--g); font-size: clamp(2.8rem, 5.5vw, 5rem);
          font-weight: 500; color: var(--paper); margin-bottom: 1.5rem;
          letter-spacing: -0.025em; line-height: 1.08;
        }
        .pb-cta-h em { font-style: italic; color: var(--amber-l); }
        .pb-cta-sub {
          font-family: var(--g); font-size: 1.05rem; color: rgba(237,232,220,0.5);
          margin-bottom: 3rem; max-width: 440px;
          margin-left: auto; margin-right: auto; line-height: 1.7;
        }
        .pb-cta-row { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }

        /* Footer */
        .pb-footer {
          border-top: 1px solid rgba(237,232,220,0.08);
          padding: 2rem clamp(1.5rem, 4vw, 3rem);
          display: flex; justify-content: space-between; align-items: center;
          max-width: 1240px; margin: 0 auto;
        }
        .pb-footer-brand {
          font-family: var(--g); font-size: 0.95rem; font-weight: 600;
          color: rgba(237,232,220,0.45); letter-spacing: -0.01em;
        }
        .pb-footer-copy {
          font-family: var(--m); font-size: 0.62rem; letter-spacing: 0.1em;
          color: rgba(237,232,220,0.22); text-transform: uppercase;
        }

        @media (max-width: 900px) {
          .pb-hero-inner { grid-template-columns: 1fr; }
          .pb-hero-visual { display: none; }
          .pb-features-grid { grid-template-columns: 1fr; }
          .pb-stats-inner { grid-template-columns: repeat(2, 1fr); }
          .pb-steps-row { grid-template-columns: 1fr; gap: 2.5rem; }
          .pb-steps-row::after { display: none; }
          .pb-activity-inner { grid-template-columns: 1fr; }
          .pb-nav-links { display: none; }
        }
      `}</style>

      {/* ─── Nav ──────────────────────────────────────────── */}
      <nav className={`pb-nav${scrolled ? " scrolled" : ""}`}>
        <Link href="/" className="pb-logo">
          Paper<em>bubu</em>
        </Link>
        <div className="pb-nav-links">
          <Link href="/login" className="pb-nav-link">Sign in</Link>
          <Link href="/login" className="pb-btn pb-btn-primary">Get started</Link>
        </div>
      </nav>

      {/* ─── Hero ─────────────────────────────────────────── */}
      <section className="pb-hero">
        <div className="pb-hero-inner">
          <div>
            <p className="pb-eyebrow">Research Paper Tracker</p>
            <h1 className="pb-hero-h1">
              Every paper<br />has its <em>place.</em>
            </h1>
            <p className="pb-hero-sub">
              Paperbubu turns your scattered PDF downloads and arXiv links into a living research archive — searchable, trackable, and beautifully organized.
            </p>
            <div className="pb-hero-ctas">
              <Link href="/login" className="pb-btn pb-btn-primary pb-btn-lg">Start for free</Link>
              <a href="#features" className="pb-btn pb-btn-ghost pb-btn-lg">See features</a>
            </div>
          </div>

          <div className="pb-hero-visual">
            <div className="pb-specimen pb-specimen-a">
              <div className="pb-spec-catalog">
                <span>Catalog № PB-0047</span>
                <span>2023</span>
              </div>
              <div className="pb-spec-title">Attention Is All You Need</div>
              <div className="pb-spec-meta">
                Vaswani, Shazeer, Parmar et al.<br />
                NeurIPS 2017 · arXiv:1706.03762
              </div>
              <span className="pb-spec-badge done">Completed</span>
            </div>

            <div className="pb-specimen pb-specimen-b">
              <div className="pb-spec-catalog">
                <span>Catalog № PB-0103</span>
                <span>2024</span>
              </div>
              <div className="pb-spec-title">BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding</div>
              <div className="pb-spec-meta">
                Devlin, Chang, Lee, Toutanova<br />
                NAACL 2019 · arXiv:1810.04805
              </div>
              <span className="pb-spec-badge reading">Reading</span>
            </div>

            <div className="pb-specimen pb-specimen-c">
              <div className="pb-spec-catalog">
                <span>Catalog № PB-0211</span>
                <span>2024</span>
              </div>
              <div className="pb-spec-title">Language Models are Few-Shot Learners</div>
              <div className="pb-spec-meta">
                Brown, Mann, Ryder et al.<br />
                NeurIPS 2020 · arXiv:2005.14165
              </div>
              <span className="pb-spec-badge queue">To read</span>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Marquee ──────────────────────────────────────── */}
      <div className="pb-marquee" aria-hidden>
        <div className="pb-marquee-track">
          {[...MARQUEE_ITEMS, ...MARQUEE_ITEMS].map((item, i) => (
            <span key={i} style={{ display: "contents" }}>
              <span className="pb-marquee-item">{item}</span>
              <span className="pb-marquee-sep">◆</span>
            </span>
          ))}
        </div>
      </div>

      {/* ─── Features ─────────────────────────────────────── */}
      <section id="features" className="pb-features">
        <div className="pb-features-inner">
          <p className="pb-section-tag">Features</p>
          <div className="pb-features-grid">
            {features.map((f) => (
              <div
                key={f.id}
                className="pb-feat"
                style={{ "--feat-accent": f.accent } as React.CSSProperties}
              >
                <div className="pb-feat-num">{f.id}</div>
                <div className="pb-feat-label" style={{ color: f.labelColor }}>{f.label}</div>
                <div className="pb-feat-title">{f.title}</div>
                <div className="pb-feat-body">{f.body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Stats band ───────────────────────────────────── */}
      <div className="pb-stats">
        <div className="pb-stats-inner">
          {[
            { n: "∞", l: "Papers supported" },
            { n: "3", l: "Reading statuses" },
            { n: "365", l: "Days tracked" },
            { n: "100%", l: "Open source" },
          ].map((s) => (
            <div key={s.l}>
              <div className="pb-stat-n">{s.n}</div>
              <div className="pb-stat-l">{s.l}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ─── Process ──────────────────────────────────────── */}
      <section className="pb-process">
        <div className="pb-process-inner">
          <p className="pb-section-tag">Process</p>
          <h2 className="pb-process-h">
            A simple loop that<br /><em>compounds</em> over time.
          </h2>
          <div className="pb-steps-row">
            {steps.map((s) => (
              <div key={s.num} className="pb-step-item">
                <div className="pb-step-circle">{s.num}</div>
                <div className="pb-step-title">{s.title}</div>
                <div className="pb-step-desc">{s.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Activity heatmap ─────────────────────────────── */}
      <section className="pb-activity">
        <div className="pb-activity-inner">
          <div>
            <p className="pb-section-tag">Activity</p>
            <h2 className="pb-activity-h">
              Your scholarship,<br />made <em>visible.</em>
            </h2>
            <p className="pb-activity-body">
              Every completed paper marks a day on your reading heatmap. Watch patterns emerge over the year. Discover when you read most. Build a habit — one paper at a time.
            </p>
          </div>

          <div className="pb-hm-card">
            <div className="pb-hm-header">
              <span>Reading activity · past 52 weeks</span>
              <span style={{ display: "flex", alignItems: "center", gap: "3px" }}>
                <span>Less</span>
                {[0, 1, 2, 3, 4].map((v) => (
                  <span
                    key={v}
                    style={{
                      display: "inline-block", width: "10px", height: "10px",
                      backgroundColor: heatmapColors[v], borderRadius: "1px",
                    }}
                  />
                ))}
                <span>More</span>
              </span>
            </div>
            <div className="pb-hm-grid">
              {HEATMAP_DATA.map((val, i) => (
                <div
                  key={i}
                  className="pb-hm-cell"
                  style={{ backgroundColor: heatmapColors[val] }}
                />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ─── CTA ──────────────────────────────────────────── */}
      <section className="pb-cta">
        <p className="pb-cta-eyebrow">Ready to begin?</p>
        <h2 className="pb-cta-h">
          Begin your<br /><em>catalog.</em>
        </h2>
        <p className="pb-cta-sub">
          Free to use. No credit card required. Start organizing your research today.
        </p>
        <div className="pb-cta-row">
          <Link href="/login" className="pb-btn pb-btn-primary pb-btn-lg">Create an account</Link>
          <Link href="/login" className="pb-btn pb-btn-ghost pb-btn-lg">Sign in</Link>
        </div>
      </section>

      {/* ─── Footer ───────────────────────────────────────── */}
      <footer>
        <div className="pb-footer">
          <span className="pb-footer-brand">Paperbubu</span>
          <span className="pb-footer-copy">
            Research Paper Tracker · {new Date().getFullYear()}
          </span>
        </div>
      </footer>
    </div>
  );
}
