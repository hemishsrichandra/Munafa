import React, { useState, useEffect, useRef } from 'react';
import {
  LayoutDashboard,
  ReceiptText,
  Store,
  ChartNoAxesCombined,
  ArrowUpRight,
  ArrowRight,
  Plus,
  Search,
  Bell,
  ChevronRight,
  CircleHelp,
  Check,
  ShieldCheck,
  Clock3,
  Wallet,
  X,
  Sparkles,
  Download,
  AlertCircle,
  Leaf,
  LoaderCircle,
  CircleCheck,
} from 'lucide-react';
import { api, money, today } from './api';
import { icon, Metric, CaseTable, Empty, Modal } from './components/ui';
import { InvoiceModal } from './components/InvoiceIntake';
import CaseDetail from './components/CaseDetail';
import { Suppliers, Insights } from './components/LedgerViews';

const navs = [
  { id: 'overview', label: 'Overview', Icon: LayoutDashboard },
  { id: 'cases', label: 'Credit cases', Icon: ReceiptText },
  { id: 'suppliers', label: 'Suppliers', Icon: Store },
  { id: 'insights', label: 'Insights', Icon: ChartNoAxesCombined },
];

function App() {
  const [view, setView] = useState('overview'),
    [cases, setCases] = useState([]),
    [selected, setSelected] = useState(null),
    [adding, setAdding] = useState(false);
  const [config, setConfig] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(''),
    [toast, setToast] = useState(''),
    [query, setQuery] = useState(''),
    [filter, setFilter] = useState('all'),
    [help, setHelp] = useState(false);
  async function load() {
    try {
      const [data, cfg] = await Promise.all([api('/cases'), api('/health')]);
      setCases(data);
      setConfig(cfg);
      setError('');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, []);
  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(''), 4500);
      return () => clearTimeout(t);
    }
  }, [toast]);
  const open = (c) => {
    setSelected(c);
    window.scrollTo(0, 0);
  };
  const navigate = (v) => {
    setView(v);
    setSelected(null);
    setQuery('');
    setFilter('all');
  };
  const onUpdate = (c) => {
    setSelected(c);
    setCases((prev) => prev.map((old) => (old.id === c.id ? c : old)));
  };
  const onCreate = (c) => {
    setCases((prev) => [c, ...prev]);
    setAdding(false);
    open(c);
    setToast('Invoice added. Confirm what arrived before approval.');
  };
  const pending = cases.filter((c) => c.status !== 'resolved');
  const overdue = pending.filter((c) => c.follow_up && c.follow_up < today());
  const verified = cases.reduce((a, c) => a + c.recovered_paise, 0);
  const approved = pending.filter((c) => c.approved_version !== null);
  const outstanding = approved.reduce((a, c) => a + c.remaining_paise, 0);
  const matching = cases
    .filter((c) =>
      `${c.invoice.supplier} ${c.invoice.reference} ${c.id}`
        .toLowerCase()
        .includes(query.toLowerCase()),
    )
    .filter(
      (c) =>
        filter === 'all' ||
        (filter === 'open'
          ? c.status !== 'resolved'
          : filter === 'overdue'
            ? c.follow_up && c.follow_up < today() && c.status !== 'resolved'
            : c.status === filter),
    );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate('overview');
          }}
        >
          <span className="brand-mark">
            m<span>↗</span>
          </span>
          <span>
            munafa<span className="brand-dot">.</span>
          </span>
        </a>
        <div className="workspace">
          <span className="store-avatar">{icon(Store, 18)}</span>
          <div>
            <strong>Lakshmi Kirana</strong>
            <span>Indiranagar, Bengaluru</span>
          </div>
          <span className="demo-tag">DEMO</span>
        </div>
        <span className="nav-label">YOUR WORKSPACE</span>
        <nav>
          {navs.map(({ id, label, Icon }) => (
            <button key={id} className={view === id ? 'active' : ''} onClick={() => navigate(id)}>
              {icon(Icon)}
              <span>{label}</span>
              {id === 'cases' && <em>{pending.length}</em>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="trust-card">
            {icon(ShieldCheck, 24)}
            <strong>Every rupee has a trail.</strong>
            <p>
              You review the evidence.
              <br />
              You stay in control.
            </p>
            <button onClick={() => setHelp(true)}>How Munafa works {icon(ArrowUpRight, 14)}</button>
          </div>
          <button className="support" onClick={() => setHelp(true)}>
            {icon(CircleHelp)} Help & demo guide {icon(ArrowUpRight, 15)}
          </button>
          <div className="profile">
            <span className="avatar">LK</span>
            <div>
              <strong>Lakshmi Kirana</strong>
              <span>Merchant workspace</span>
            </div>
            <span className="online-dot" />
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={14} />
            <strong>{selected ? 'Credit cases' : navs.find((n) => n.id === view)?.label}</strong>
            {selected && (
              <>
                <ChevronRight size={14} />
                <span>{selected.invoice.reference}</span>
              </>
            )}
          </div>
          <div className="top-actions">
            <span className="prototype-label">
              <i />
              Hackathon prototype
            </span>
            <button
              className="icon-button notifications"
              aria-label="Show overdue follow-ups"
              onClick={() => {
                navigate('cases');
                setFilter('overdue');
              }}
            >
              {icon(Bell)}
              {overdue.length > 0 && <i />}
            </button>
            <span className="top-avatar">LK</span>
          </div>
        </header>
        <main>
          {error && (
            <div className="error-box">
              {icon(AlertCircle)}
              <span>{error}</span>
              <button onClick={load}>Retry</button>
            </div>
          )}
          {loading ? (
            <div className="loading">{icon(LoaderCircle, 26)} Loading your workspace…</div>
          ) : selected ? (
            <CaseDetail
              key={selected.id}
              c={selected}
              onUpdate={onUpdate}
              back={() => setSelected(null)}
              config={config}
              notify={setToast}
            />
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">
                    {view === 'overview'
                      ? 'A LITTLE CLARITY. A BETTER BUSINESS.'
                      : 'YOUR SUPPLIER CREDIT WORKSPACE'}
                  </div>
                  <h1>
                    {
                      {
                        overview: 'Your money, accounted for.',
                        cases: 'Every credit. One place.',
                        suppliers: 'Know where things stand.',
                        insights: 'A clearer picture of recovery.',
                      }[view]
                    }
                  </h1>
                  <p>
                    {
                      {
                        overview: 'Keep track of what’s owed. Get back to what you do best.',
                        cases: 'From a delivery gap to a documented resolution.',
                        suppliers: 'Supplier balances, open cases and the next conversation.',
                        insights: 'Documented credits and refunds, with the evidence behind them.',
                      }[view]
                    }
                  </p>
                </div>
                <button className="button primary" onClick={() => setAdding(true)}>
                  {icon(Plus)} Add an invoice
                </button>
              </div>
              {view === 'overview' && (
                <>
                  <section className="hero">
                    <div className="hero-copy">
                      <span className="hero-kicker">
                        <i /> YOUR BUSINESS COPILOT
                      </span>
                      <h2>
                        Small gaps shouldn’t
                        <br />
                        become lost money.
                      </h2>
                      <p>
                        Turn a short delivery into a clear, reviewed claim.
                        <br />
                        We’ll help you follow it through.
                      </p>
                      <button onClick={() => setAdding(true)}>
                        Check a delivery {icon(ArrowRight, 17)}
                      </button>
                      <span className="hero-foot">AI reads. Rules calculate. You approve.</span>
                    </div>
                    <div className="hero-art" aria-hidden="true">
                      <div className="orbit orbit-one" />
                      <div className="orbit orbit-two" />
                      <div className="floating-label label-one">
                        <span className="check-round">✓</span> Evidence, all together
                      </div>
                      <div className="bill-illustration">
                        <div className="mini-brand">
                          m<span>↗</span>
                        </div>
                        <span className="bill-caption">DELIVERY CHECK</span>
                        <div className="bill-row">
                          <span>Billed</span>
                          <strong>12 packs</strong>
                        </div>
                        <div className="bill-row">
                          <span>Received</span>
                          <strong>10 packs</strong>
                        </div>
                        <div className="bill-divider" />
                        <div className="bill-total">
                          <span>Amount to review</span>
                          <strong>
                            ₹80<span>.00</span>
                          </strong>
                        </div>
                        <div className="bill-verified">
                          {icon(ShieldCheck, 13)} Merchant confirmed
                        </div>
                      </div>
                      <div className="floating-label label-two">
                        {icon(Leaf, 16)} A little more munafa.
                      </div>
                    </div>
                  </section>
                  <div className="section-caption">
                    <span>AT A GLANCE</span>
                    <span className="muted">All-time ledger · includes synthetic examples</span>
                  </div>
                </>
              )}
              {(view === 'overview' || view === 'insights') && (
                <div className="metrics">
                  <Metric
                    label="Awaiting resolution"
                    value={money(outstanding)}
                    Icon={Wallet}
                    foot={`${approved.length} approved open case${approved.length !== 1 ? 's' : ''}`}
                    tone="green"
                  />
                  <Metric
                    label="Verified recovery"
                    value={money(verified)}
                    Icon={ShieldCheck}
                    foot="Applied credits + received refunds"
                    tone="mint"
                  />
                  <Metric
                    label="Open credit cases"
                    value={pending.length.toString().padStart(2, '0')}
                    Icon={ReceiptText}
                    foot={`${cases.filter((c) => c.status === 'review').length} waiting for your review`}
                    tone="blue"
                  />
                  <Metric
                    label="Follow-ups due"
                    value={overdue.length.toString().padStart(2, '0')}
                    Icon={Clock3}
                    foot={
                      overdue.length ? 'A quick nudge can go a long way' : 'You’re all caught up'
                    }
                    tone="amber"
                    onClick={() => {
                      navigate('cases');
                      setFilter('overdue');
                    }}
                  />
                </div>
              )}
              {view === 'overview' && (
                <div className="overview-lower">
                  <section className="panel case-panel">
                    <div className="panel-heading">
                      <div>
                        <h2>
                          Your credit cases <span>{cases.length}</span>
                        </h2>
                        <p>A promise is a start. A verified credit is the finish.</p>
                      </div>
                      <button className="text-button" onClick={() => navigate('cases')}>
                        View all {icon(ArrowRight, 15)}
                      </button>
                    </div>
                    <CaseTable cases={cases.slice(0, 5)} open={open} />
                    {!cases.length && <Empty onAdd={() => setAdding(true)} />}
                  </section>
                  <aside className="next-panel">
                    <div className="panel-heading">
                      <h2>Next best step</h2>
                      <span className="spark-icon">{icon(Sparkles, 17)}</span>
                    </div>
                    {overdue.length ? (
                      <>
                        <div className="next-icon">{icon(Clock3, 24)}</div>
                        <h3>A credit needs a nudge.</h3>
                        <p>
                          <strong>{overdue[0].invoice.supplier}</strong> promised an adjustment.
                          Your follow-up date has passed.
                        </p>
                        <div className="next-amount">
                          <span>Still to verify</span>
                          <strong>{money(overdue[0].remaining_paise)}</strong>
                        </div>
                        <button className="button secondary full" onClick={() => open(overdue[0])}>
                          Review follow-up {icon(ArrowRight, 16)}
                        </button>
                      </>
                    ) : (
                      <>
                        <div className="next-icon">{icon(ReceiptText, 24)}</div>
                        <h3>Start with your next delivery.</h3>
                        <p>Add a bill, confirm what arrived, and keep the evidence together.</p>
                        <button className="button secondary full" onClick={() => setAdding(true)}>
                          Check a delivery {icon(ArrowRight, 16)}
                        </button>
                      </>
                    )}
                    <div className="tiny-note">
                      {icon(ShieldCheck, 14)} Suggested from your ledger. You decide.
                    </div>
                  </aside>
                </div>
              )}
              {view === 'cases' && (
                <section className="panel">
                  <div className="table-toolbar">
                    <div className="tabs">
                      {[
                        ['all', 'All cases'],
                        ['open', 'Open'],
                        ['review', 'Needs review'],
                        ['resolved', 'Resolved'],
                        ['overdue', 'Overdue'],
                      ].map(([id, label]) => (
                        <button
                          key={id}
                          onClick={() => setFilter(id)}
                          className={filter === id ? 'chosen' : ''}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                    <div className="search-field">
                      {icon(Search, 16)}
                      <input
                        aria-label="Search cases"
                        placeholder="Search supplier or invoice"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                      />
                    </div>
                  </div>
                  <CaseTable cases={matching} open={open} />
                  {!matching.length && (
                    <div className="empty">
                      <ReceiptText />
                      <h3>No cases here yet</h3>
                      <p>Try another filter or add your next invoice.</p>
                    </div>
                  )}
                </section>
              )}
              {view === 'suppliers' && <Suppliers cases={cases} open={open} />}
              {view === 'insights' && (
                <Insights cases={cases} verified={verified} outstanding={outstanding} />
              )}
              {view === 'overview' && (
                <div className="bottom-note">
                  <span className="sarvam-symbol">✳</span>
                  <p>
                    <strong>Made for the way India does business.</strong> Sarvam AI supports
                    invoice understanding and supplier messages in Hindi and Kannada.
                  </p>
                  <button className="text-button" onClick={() => setHelp(true)}>
                    Explore the workflow {icon(ArrowUpRight, 14)}
                  </button>
                </div>
              )}
            </>
          )}
          <footer>
            <span>
              munafa<span className="brand-dot">.</span> <span className="footer-divider">/</span> A
              business partner beyond payments
            </span>
            <span>Synthetic demo data · No live Paytm connection</span>
          </footer>
        </main>
      </div>
      {adding && <InvoiceModal close={() => setAdding(false)} create={onCreate} config={config} />}
      {help && (
        <Modal
          title="A clear path from gap to credit"
          subtitle="Your two-minute Munafa demo guide"
          close={() => setHelp(false)}
        >
          <div className="guide">
            {[
              [
                '01',
                'Add the A-104 sample invoice',
                'A synthetic bill with biscuits, tea and an unclear soap unit.',
              ],
              [
                '02',
                'Confirm the delivery',
                'Enter 10 biscuit packs, 6 tea packs and 24 soap pieces. Set soap to piece on both sides, confirm each unit, and verify delivery and pricing.',
              ],
              [
                '03',
                'Approve the ₹80 evidence',
                'Review the math. Download the evidence or open a supplier message. Confirm sharing only after sending.',
              ],
              [
                '04',
                'Follow through to resolution',
                'Record a supplier promise and date. Load the synthetic next-bill credit, inspect it and confirm it was applied.',
              ],
            ].map(([n, t, p]) => (
              <div key={n}>
                <span>{n}</span>
                <section>
                  <h3>{t}</h3>
                  <p>{p}</p>
                </section>
              </div>
            ))}
            <div className="info-box">
              <Sparkles size={18} />
              <p>
                Sarvam AI: add your server-side key for invoice text/image extraction and
                Hindi/Kannada translation. Without a key, the sample, manual entry and English
                message work in full.
              </p>
            </div>
            <p className="muted">
              This is a local, single-store hackathon prototype. It does not send messages
              automatically or access Paytm data. Voice entry is an optional browser feature.
            </p>
          </div>
        </Modal>
      )}
      {toast && (
        <div className="toast" role="status">
          {icon(CircleCheck, 18)}
          {toast}
          <button onClick={() => setToast('')} aria-label="Dismiss notification">
            <X size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
