import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const page = () => `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sell Your Property | Everlight Ventures</title>
  <meta name="description" content="Get a cash offer for your property in 24 hours. No fees, no agents, close in 7 days." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js" crossorigin></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:#0a0a14;color:#f0f0f0;-webkit-font-smoothing:antialiased}
    #root{min-height:100vh}
    :root{--navy:#0a0a14;--navy-light:#12121f;--navy-card:#16162a;--gold:#c9a84c;--gold-hover:#dbb85e;--gold-dim:rgba(201,168,76,0.15);--text:#f0f0f0;--text-muted:#8a8a9a;--text-dim:#5a5a6a;--border:#2a2a3a;--radius:12px;--radius-lg:16px}
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel">
    const { useState, useRef, useEffect } = React;

    function useCountUp(target, duration = 2000) {
      const [count, setCount] = useState(0);
      const ref = useRef(null);
      useEffect(() => {
        const observer = new IntersectionObserver(([entry]) => {
          if (entry.isIntersecting) {
            let start = 0;
            const step = target / (duration / 16);
            const timer = setInterval(() => {
              start += step;
              if (start >= target) { setCount(target); clearInterval(timer); }
              else setCount(Math.floor(start));
            }, 16);
            observer.disconnect();
          }
        }, { threshold: 0.3 });
        if (ref.current) observer.observe(ref.current);
        return () => observer.disconnect();
      }, []);
      return [count, ref];
    }

    function GlowButton({ children, onClick, type = "button", style = {} }) {
      const [hover, setHover] = useState(false);
      return (
        <button type={type} onClick={onClick}
          onMouseOver={() => setHover(true)} onMouseOut={() => setHover(false)}
          style={{
            background: 'linear-gradient(135deg, var(--gold), #b8953f)',
            color: '#0a0a14', fontWeight: 700, fontSize: 16, padding: '16px 40px',
            border: 'none', borderRadius: 'var(--radius)', cursor: 'pointer',
            letterSpacing: '0.5px', textTransform: 'uppercase',
            boxShadow: hover ? '0 6px 32px rgba(201,168,76,0.5)' : '0 4px 24px rgba(201,168,76,0.3)',
            transform: hover ? 'translateY(-2px)' : 'translateY(0)',
            transition: 'all 0.2s ease', fontFamily: 'Inter, sans-serif', ...style,
          }}>{children}</button>
      );
    }

    function Card({ children, style = {} }) {
      const [hover, setHover] = useState(false);
      return (
        <div onMouseOver={() => setHover(true)} onMouseOut={() => setHover(false)}
          style={{
            background: 'var(--navy-card)', border: '1px solid ' + (hover ? 'var(--gold)' : 'var(--border)'),
            borderRadius: 'var(--radius-lg)', transition: 'all 0.2s',
            transform: hover ? 'translateY(-4px)' : 'translateY(0)', ...style,
          }}>{children}</div>
      );
    }

    function Header() {
      return (
        <header style={{ background: 'rgba(18,18,31,0.85)', borderBottom: '1px solid var(--border)', padding: '16px 0', position: 'sticky', top: 0, zIndex: 100, backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)' }}>
          <div style={{ maxWidth: 1080, margin: '0 auto', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 34, height: 34, background: 'linear-gradient(135deg, var(--gold), #b8953f)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 18, color: 'var(--navy)' }}>E</div>
              <span style={{ fontWeight: 700, fontSize: 18, letterSpacing: 1 }}>EVERLIGHT <span style={{ color: 'var(--gold)' }}>VENTURES</span></span>
            </div>
            <a href="mailto:rich@everlightventures.io" style={{ color: 'var(--gold)', textDecoration: 'none', fontSize: 14, fontWeight: 500 }}>rich@everlightventures.io</a>
          </div>
        </header>
      );
    }

    function Hero() {
      return (
        <section style={{ textAlign: 'center', padding: '100px 24px 80px', background: 'radial-gradient(ellipse at top, #1a1a3a 0%, var(--navy) 70%)' }}>
          <div style={{ display: 'inline-block', background: 'var(--gold-dim)', border: '1px solid rgba(201,168,76,0.3)', borderRadius: 20, padding: '6px 18px', fontSize: 13, color: 'var(--gold)', fontWeight: 600, marginBottom: 28, letterSpacing: 1 }}>PRIVATE ACQUISITIONS</div>
          <h1 style={{ fontSize: 'clamp(32px, 6vw, 56px)', fontWeight: 800, lineHeight: 1.1, maxWidth: 720, margin: '0 auto 20px' }}>
            Get a <span style={{ color: 'var(--gold)' }}>Cash Offer</span> for Your Property
          </h1>
          <p style={{ fontSize: 'clamp(16px, 2.5vw, 20px)', color: 'var(--text-muted)', maxWidth: 560, margin: '0 auto 40px', lineHeight: 1.6 }}>
            We buy properties as-is for cash. No agents, no fees, no repairs. Close in as little as 7 days.
          </p>
          <GlowButton onClick={() => document.getElementById('form').scrollIntoView({ behavior: 'smooth' })}>Get My Cash Offer</GlowButton>
        </section>
      );
    }

    function Stats() {
      const [v1, r1] = useCountUp(7, 1500);
      const [v2, r2] = useCountUp(100, 2000);
      const [v3, r3] = useCountUp(6, 1000);
      return (
        <section style={{ background: 'var(--navy-light)', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)', padding: '48px 24px' }}>
          <div style={{ maxWidth: 800, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 32, textAlign: 'center' }}>
            {[{v:v1,s:'-Day',l:'Average Close',r:r1},{v:v2,s:'%',l:'Cash Offers',r:r2},{v:v3,s:'',l:'Active Markets',r:r3}].map((d,i) => (
              <div key={i} ref={d.r}>
                <div style={{ fontSize: 42, fontWeight: 800, color: 'var(--gold)' }}>{d.v}{d.s}</div>
                <div style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 4 }}>{d.l}</div>
              </div>
            ))}
          </div>
        </section>
      );
    }

    function Steps() {
      const steps = [
        { num: '01', title: 'Submit Your Property', desc: 'Fill out the form with your property details. Takes 30 seconds. No obligation.' },
        { num: '02', title: 'Receive a Cash Offer', desc: 'Our team reviews your property and delivers a written cash offer within 24 hours.' },
        { num: '03', title: 'Close on Your Timeline', desc: 'Pick your closing date. We handle title, paperwork, and all costs. You get paid.' },
      ];
      return (
        <section style={{ padding: '80px 24px', maxWidth: 1080, margin: '0 auto' }}>
          <h2 style={{ textAlign: 'center', fontSize: 32, fontWeight: 700, marginBottom: 12 }}>How It <span style={{ color: 'var(--gold)' }}>Works</span></h2>
          <div style={{ width: 48, height: 3, background: 'var(--gold)', margin: '0 auto 48px', borderRadius: 2 }}></div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 24 }}>
            {steps.map((s, i) => (
              <Card key={i} style={{ padding: '36px 28px' }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--gold)', marginBottom: 16, letterSpacing: 2 }}>{s.num}</div>
                <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 10 }}>{s.title}</h3>
                <p style={{ fontSize: 14, color: 'var(--text-muted)', lineHeight: 1.6 }}>{s.desc}</p>
              </Card>
            ))}
          </div>
        </section>
      );
    }

    function ContactForm() {
      const [sent, setSent] = useState(false);
      const [form, setForm] = useState({ name: '', email: '', address: '', phone: '' });
      const [loading, setLoading] = useState(false);

      const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
          await fetch('https://jdqqmsmwmbsnlnstyavl.supabase.co/rest/v1/seller_leads', {
            method: 'POST',
            headers: {
              'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww',
              'Content-Type': 'application/json', 'Prefer': 'return=minimal'
            },
            body: JSON.stringify({ name: form.name, email: form.email, property_address: form.address, phone: form.phone, source: 'landing_page' })
          });
        } catch(err) {}
        setLoading(false);
        setSent(true);
      };

      const inputStyle = { width: '100%', padding: '14px 16px', background: 'var(--navy)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text)', fontSize: 15, outline: 'none', transition: 'border-color 0.2s', fontFamily: 'Inter, sans-serif' };

      if (sent) return (
        <section id="form" style={{ padding: '80px 24px', background: 'var(--navy-light)' }}>
          <div style={{ maxWidth: 480, margin: '0 auto', textAlign: 'center', background: 'var(--navy-card)', border: '1px solid var(--gold)', borderRadius: 'var(--radius-lg)', padding: '60px 32px' }}>
            <div style={{ width: 64, height: 64, background: 'var(--gold-dim)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px', fontSize: 28, color: 'var(--gold)' }}>&#10003;</div>
            <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>Request <span style={{ color: 'var(--gold)' }}>Received</span></h2>
            <p style={{ color: 'var(--text-muted)', lineHeight: 1.6 }}>Our acquisitions team will review your property and send a written cash offer within 24 hours.</p>
          </div>
        </section>
      );

      return (
        <section id="form" style={{ padding: '80px 24px', background: 'var(--navy-light)' }}>
          <div style={{ maxWidth: 480, margin: '0 auto', background: 'var(--navy-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '48px 32px' }}>
            <h2 style={{ textAlign: 'center', fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Get Your <span style={{ color: 'var(--gold)' }}>Cash Offer</span></h2>
            <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 14, marginBottom: 32 }}>No fees. No commissions. No obligation.</p>
            <form onSubmit={handleSubmit}>
              {[
                { key: 'name', label: 'Full Name', ph: 'John Smith', type: 'text', req: true },
                { key: 'email', label: 'Email', ph: 'john@email.com', type: 'email', req: true },
                { key: 'address', label: 'Property Address', ph: '123 Main St, Atlanta, GA 30301', type: 'text', req: true },
                { key: 'phone', label: 'Phone', ph: '(555) 123-4567', type: 'tel', req: false },
              ].map(f => (
                <div key={f.key} style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
                    {f.label} {!f.req && <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, color: 'var(--text-dim)' }}>(optional)</span>}
                  </label>
                  <input style={inputStyle} type={f.type} placeholder={f.ph} required={f.req} value={form[f.key]}
                    onChange={e => setForm({...form, [f.key]: e.target.value})}
                    onFocus={e => e.target.style.borderColor = 'var(--gold)'}
                    onBlur={e => e.target.style.borderColor = 'var(--border)'} />
                </div>
              ))}
              <GlowButton type="submit" style={{ width: '100%', opacity: loading ? 0.7 : 1 }}>
                {loading ? 'Submitting...' : 'Get My Cash Offer'}
              </GlowButton>
            </form>
          </div>
        </section>
      );
    }

    function Trust() {
      const cards = [
        { icon: '\\u2705', title: 'Licensed & Insured', desc: 'Fully licensed operation backed by Everlight Logistics LLC.' },
        { icon: '\\u2B50', title: 'Professional Acquisitions', desc: 'Institutional-grade due diligence on every property.' },
        { icon: '\\uD83D\\uDCB0', title: 'Nationwide Portfolio', desc: 'Active acquisitions across 6 major metro markets.' },
        { icon: '\\u23F1', title: '7-Day Close', desc: 'Cash on hand. No bank delays, no financing contingencies.' },
      ];
      const markets = ['Atlanta, GA', 'Dallas, TX', 'Cleveland, OH', 'St. Louis, MO', 'Jacksonville, FL'];
      return (
        <section style={{ padding: '80px 24px', maxWidth: 1080, margin: '0 auto' }}>
          <h2 style={{ textAlign: 'center', fontSize: 32, fontWeight: 700, marginBottom: 12 }}>Why Sellers <span style={{ color: 'var(--gold)' }}>Choose Us</span></h2>
          <div style={{ width: 48, height: 3, background: 'var(--gold)', margin: '0 auto 48px', borderRadius: 2 }}></div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20, marginBottom: 48 }}>
            {cards.map((c, i) => (
              <Card key={i} style={{ padding: '28px 20px', textAlign: 'center' }}>
                <div style={{ fontSize: 28, marginBottom: 12 }}>{c.icon}</div>
                <h4 style={{ fontSize: 15, fontWeight: 700, color: 'var(--gold)', marginBottom: 8 }}>{c.title}</h4>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>{c.desc}</p>
              </Card>
            ))}
          </div>
          <div style={{ textAlign: 'center' }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: 'var(--text-muted)' }}>Currently Serving</h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 10 }}>
              {markets.map((m, i) => (
                <span key={i} style={{ background: 'var(--gold-dim)', border: '1px solid rgba(201,168,76,0.3)', borderRadius: 20, padding: '6px 18px', fontSize: 13, color: 'var(--gold)', fontWeight: 500 }}>{m}</span>
              ))}
            </div>
          </div>
        </section>
      );
    }

    function Footer() {
      return (
        <footer style={{ background: 'var(--navy)', borderTop: '1px solid var(--border)', padding: '40px 24px', textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 12 }}>
            <div style={{ width: 24, height: 24, background: 'linear-gradient(135deg, var(--gold), #b8953f)', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 14, color: 'var(--navy)' }}>E</div>
            <span style={{ fontWeight: 700, fontSize: 14, letterSpacing: 1 }}>EVERLIGHT <span style={{ color: 'var(--gold)' }}>VENTURES</span></span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 4 }}>Everlight Logistics LLC</p>
          <p style={{ fontSize: 13, color: 'var(--text-dim)' }}><a href="mailto:rich@everlightventures.io" style={{ color: 'var(--gold)', textDecoration: 'none' }}>rich@everlightventures.io</a></p>
          <p style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 16 }}>&copy; 2026 Everlight Ventures. All rights reserved.</p>
        </footer>
      );
    }

    function App() {
      return (<><Header /><Hero /><Stats /><Steps /><ContactForm /><Trust /><Footer /></>);
    }

    ReactDOM.createRoot(document.getElementById('root')).render(<App />);
  </script>
</body>
</html>`;

serve((_req: Request) => {
  return new Response(page(), {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "public, max-age=3600",
    },
  });
});
