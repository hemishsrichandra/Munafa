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
import { useSession } from './session';
import { useOffline } from './offline/provider';
import { cacheCases } from './offline/db';
import { OfflineWorkspace } from './offline/Workspace';
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
  const session = useSession();
  const local = useOffline();
  const [deviceWorkspace, setDeviceWorkspace] = useState(false);
  const openIntake = () => (navigator.onLine ? setAdding(true) : setDeviceWorkspace(true));
  const [locale, setLocale] = useState('en');
  const shellLabels = {
    en: { home: 'Home', purchases: 'Purchases', more: 'More' },
    hi: { home: 'होम', purchases: 'खरीदारी', more: 'अधिक' },
    kn: { home: 'ಮುಖಪುಟ', purchases: 'ಖರೀದಿಗಳು', more: 'ಇನ್ನಷ್ಟು' },
  }[locale];
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
      if (!session.offlineUnavailable)
        await cacheCases(local.scope, data).catch((e) => local.setError(e.message));
      setConfig(cfg);
      setError('');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    if (session.offlineAccess) setLoading(false);
    else load();
  }, [session.offlineAccess]);
  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(''), 4500);
      return () => clearTimeout(t);
    }
  }, [toast]);
  useEffect(() => {
    const refresh = () => {
      if (!session.offlineAccess) load();
    };
    window.addEventListener('munafa-server-change', refresh);
    return () => window.removeEventListener('munafa-server-change', refresh);
  }, [session.offlineAccess]);
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
  if (session.offlineAccess) return <OfflineWorkspace standalone />;
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
            <strong>{session.store.name}</strong>
            <span>{session.store.timezone}</span>
          </div>
          {session.store.demo && <span className="demo-tag">DEMO</span>}
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
              <strong>{session.store.name}</strong>
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
          <div className="device-sync-summary">
            <button className="button secondary" onClick={() => setDeviceWorkspace(true)}>
              Drafts &amp; sync
            </button>
            <span>
              {local.operations.filter((o) => o.state !== 'synced').length} waiting / needs
              attention
              {local.status?.last_synced_at
                ? ` · Last synced ${new Date(local.status.last_synced_at).toLocaleTimeString('en-IN')}`
                : ''}
            </span>
          </div>
          {deviceWorkspace ? (
            <OfflineWorkspace
              onClose={() => {
                setDeviceWorkspace(false);
                load();
              }}
              onServerChange={load}
            />
          ) : (
            <>
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
                            overview: 'Daily business brief',
                            more: 'Your workspace',
                            cases: 'Every credit. One place.',
                            suppliers: 'Know where things stand.',
                            insights: 'A clearer picture of recovery.',
                          }[view]
                        }
                      </h1>
                      <p>
                        {
                          {
                            overview:
                              'Your supplier cases and next action, grounded in your ledger.',
                            more: 'Reports, suppliers, language and account controls.',
                            cases: 'From a delivery gap to a documented resolution.',
                            suppliers: 'Supplier balances, open cases and the next conversation.',
                            insights:
                              'Documented credits and refunds, with the evidence behind them.',
                          }[view]
                        }
                      </p>
                    </div>
                    <button
                      className="button primary"
                      disabled={!session.permissions.includes('write')}
                      onClick={openIntake}
                    >
                      {icon(Plus)} Add an invoice
                    </button>
                  </div>
                  {view === 'overview' && (
                    <>
                      <section className="brief-card">
                        <div className="eyebrow">
                          {session.store.demo ? 'SYNTHETIC DEMO LEDGER' : 'YOUR STORE LEDGER'}
                        </div>
                        <h2>
                          {overdue.length
                            ? 'A supplier follow-up needs attention.'
                            : 'Keep your next delivery accounted for.'}
                        </h2>
                        <p>
                          {overdue.length
                            ? `${overdue[0].invoice.supplier}: ${money(overdue[0].remaining_paise)} still awaits verification. Follow up on the recorded promise.`
                            : 'Add a bill and confirm what arrived. A promise remains open until a credit or refund is verified.'}
                        </p>
                        <button
                          className="button primary"
                          disabled={!overdue.length && !session.permissions.includes('write')}
                          onClick={() => (overdue.length ? open(overdue[0]) : setAdding(true))}
                        >
                          {overdue.length ? 'Review follow-up' : 'Check a delivery'}{' '}
                          <ArrowRight size={17} />
                        </button>
                        <small>
                          Based on existing supplier cases. No payment, stock or sales data is
                          connected.
                        </small>
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
                          overdue.length
                            ? 'A quick nudge can go a long way'
                            : 'You’re all caught up'
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
                        {!cases.length && <Empty onAdd={openIntake} />}
                      </section>
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
              {view === 'more' && (
                <section className="panel more-panel">
                  <h2>More from your workspace</h2>
                  <button className="button secondary full" onClick={() => navigate('suppliers')}>
                    Supplier balances <ChevronRight size={18} />
                  </button>
                  <button className="button secondary full" onClick={() => navigate('insights')}>
                    Recovery report and export <ChevronRight size={18} />
                  </button>
                  <button className="button secondary full" onClick={() => setHelp(true)}>
                    Workflow guide <ChevronRight size={18} />
                  </button>
                  <label className="field">
                    Interface language
                    <select value={locale} onChange={(e) => setLocale(e.target.value)}>
                      <option value="en">English</option>
                      <option value="hi">हिन्दी · shell preview</option>
                      <option value="kn">ಕನ್ನಡ · shell preview</option>
                    </select>
                  </label>
                  {locale !== 'en' && (
                    <p className="locale-note">
                      Navigation language preview. Merchant workflow content remains English; full
                      Hindi/Kannada copy has not been reviewed.
                    </p>
                  )}
                  <p>
                    Role: {session.role}.{' '}
                    {session.store.demo
                      ? 'This store contains synthetic demonstration records.'
                      : 'This is your authenticated store.'}
                  </p>
                  <button
                    className="button secondary full"
                    onClick={() => setDeviceWorkspace(true)}
                  >
                    Drafts &amp; sync
                  </button>
                  <button className="button secondary full" onClick={session.logout}>
                    Sign out
                  </button>
                </section>
              )}
            </>
          )}
          <footer>
            <span>
              munafa<span className="brand-dot">.</span> <span className="footer-divider">/</span> A
              business partner beyond payments
            </span>
            <span>
              {session.store.demo ? 'Synthetic demo store' : 'Authenticated merchant store'} · No
              live Paytm connection
            </span>
          </footer>
        </main>
      </div>
      <nav className="bottom-nav" aria-label="Main navigation">
        {[
          ['overview', shellLabels.home, LayoutDashboard],
          ['cases', shellLabels.purchases, ReceiptText],
          ['more', shellLabels.more, CircleHelp],
        ].map(([id, label, Icon]) => (
          <button
            key={id}
            aria-current={
              view === id || (id === 'more' && ['suppliers', 'insights'].includes(view))
                ? 'page'
                : undefined
            }
            onClick={() => navigate(id)}
          >
            <Icon size={21} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
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
