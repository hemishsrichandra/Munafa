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
import { Commerce } from './components/Commerce';
import { Intelligence } from './components/Intelligence';
import { Preparation } from './components/Preparation';
import { DailyRecords } from './components/DailyRecords';
import { AccountSecurity } from './components/AccountSecurity';
import { DailyRecordsSummary } from './components/DailyRecordsSummary';
import { Integrations } from './components/Integrations';
import { Assistant, CachedHelp } from './components/Assistant';
import { BusinessBrief, Payments } from './components/BusinessBrief';

const navs = [
  { id: 'overview', label: 'Overview', Icon: LayoutDashboard },
  { id: 'purchases', label: 'Purchases & stock', Icon: ReceiptText },
  { id: 'cases', label: 'Missing Items & Refunds', Icon: ReceiptText },
  { id: 'suppliers', label: 'Suppliers', Icon: Store },
  { id: 'insights', label: 'Insights', Icon: ChartNoAxesCombined },
  { id: 'planning', label: 'Stock planning', Icon: Leaf },
  { id: 'more', label: 'More', Icon: CircleHelp },
];

function App() {
  const session = useSession();
  const storeInitials =
    session.store.name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase() || 'M';
  const local = useOffline();
  const [deviceWorkspace, setDeviceWorkspace] = useState(false);
  const openIntake = () => (navigator.onLine ? setAdding(true) : setDeviceWorkspace(true));
  const [locale, setLocale] = useState('en');
  const shellLabels = {
    en: {
      home: 'Today · आज',
      purchases: 'Deliveries & Stock',
      records: 'Customer Khata',
      more: 'More · अन्य',
    },
    hi: { home: 'आज', purchases: 'सामान और स्टॉक', records: 'ग्राहक उधार', more: 'अन्य' },
    kn: {
      home: 'ಇಂದು',
      purchases: 'ಸರಕು ಮತ್ತು ದಾಸ್ತಾನು',
      records: 'ಗ್ರಾಹಕರ ಖಾತೆ',
      more: 'ಇನ್ನಷ್ಟು',
    },
  }[locale];
  const [sourceRoute, setSourceRoute] = useState('');
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
      const [data, cfg, capabilities] = await Promise.all([
        api('/cases'),
        api('/health'),
        api('/assistant/capabilities'),
      ]);
      setCases(data);
      if (!session.offlineUnavailable)
        await cacheCases(local.scope, data).catch((e) => local.setError(e.message));
      setConfig({ ...cfg, sarvam_configured: capabilities.cloud_configured });
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
    window.scrollTo(0, 0);
  };
  async function followSource(route) {
    setSourceRoute(route);
    if (route.startsWith('/cases/')) {
      try {
        const c = await api(route);
        navigate('cases');
        open(c);
      } catch (e) {
        setError(e.message);
      }
    } else if (route.startsWith('/payments/')) navigate('payments');
    else if (route.startsWith('/stock/')) navigate('purchases');
    else if (route.startsWith('/records/')) navigate('records');
  }
  const onUpdate = (c) => {
    setSelected(c);
    setCases((prev) => prev.map((old) => (old.id === c.id ? c : old)));
  };
  const onCreate = (c) => {
    setCases((prev) => [c, ...prev.filter((old) => old.id !== c.id)]);
    setAdding(false);
    open(c);
    setToast(
      c.sample_reused
        ? 'Opened your existing sample. Previous work is saved.'
        : 'Invoice added. Confirm what arrived before approval.',
    );
  };
  const sampleToContinue =
    session.store.demo &&
    cases.find((c) => c.synthetic && c.invoice.reference === 'A-104' && c.status !== 'resolved');
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
  if (session.offlineAccess)
    return (
      <>
        <OfflineWorkspace standalone />
        <CachedHelp />
      </>
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
            {icon(CircleHelp)} Help & support {icon(ArrowUpRight, 15)}
          </button>
          <div className="profile">
            <span className="avatar">{storeInitials}</span>
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
            <strong>
              {selected
                ? 'Missing Items & Refunds'
                : navs.find((n) => n.id === view)?.label ||
                  {
                    assistant: 'Merchant help',
                    payments: 'Check Paytm payments',
                    planning: 'Stock planning',
                    exports: 'Export purchases',
                    connections: 'Connections',
                    records: 'Daily records',
                    more: 'More',
                  }[view]}
            </strong>
            {selected && (
              <>
                <ChevronRight size={14} />
                <span>{selected.invoice.reference}</span>
              </>
            )}
          </div>
          <div className="top-actions">
            {session.store.demo && <span className="demo-tag">Demo store</span>}
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
            <span className="top-avatar">{storeInitials}</span>
          </div>
        </header>
        <main>
          <div className="device-sync-summary">
            <button className="button secondary" onClick={() => setDeviceWorkspace(true)}>
              Saved on Phone
            </button>
            <span>
              {local.operations.filter((o) => o.state !== 'synced').length > 0
                ? `${local.operations.filter((o) => o.state !== 'synced').length} waiting to sync or review`
                : 'All changes saved'}
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
              {view === 'records' ? (
                <DailyRecords initialRoute={sourceRoute} />
              ) : view === 'connections' ? (
                <Integrations />
              ) : view === 'exports' ? (
                <section className="panel partner-screen">
                  <Preparation />
                </section>
              ) : view === 'planning' ? (
                <Intelligence follow={followSource} />
              ) : view === 'assistant' ? (
                <Assistant follow={followSource} />
              ) : view === 'payments' ? (
                <Payments
                  initialId={
                    sourceRoute.startsWith('/payments/')
                      ? sourceRoute.split('/')[2].split('?')[0]
                      : ''
                  }
                />
              ) : view === 'purchases' ? (
                <Commerce
                  initialRoute={sourceRoute}
                  openCase={(c) => {
                    navigate('cases');
                    open(c);
                  }}
                />
              ) : loading ? (
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
                        {view === 'overview' ? 'TODAY' : 'YOUR BUSINESS'}
                      </div>
                      <h1>
                        {
                          {
                            overview: 'Today · आज',
                            more: 'Your shop · आपकी दुकान',
                            cases: 'Missing Items & Refunds',
                            suppliers: 'Suppliers',
                            insights: 'Money returned',
                          }[view]
                        }
                      </h1>
                      <p>
                        {
                          {
                            overview: 'What needs your attention today.',
                            more: 'Reports, suppliers, language and account controls.',
                            cases: 'Check missing goods and track the money your supplier returns.',
                            suppliers: 'Supplier balances, open cases and the next conversation.',
                            insights:
                              'Documented credits and refunds, with the evidence behind them.',
                          }[view]
                        }
                      </p>
                    </div>
                    <button
                      className={sampleToContinue ? 'button secondary' : 'button primary'}
                      disabled={!session.permissions.includes('write')}
                      onClick={() =>
                        sampleToContinue
                          ? followSource(`/cases/${sampleToContinue.id}`)
                          : openIntake()
                      }
                    >
                      {icon(Plus)}{' '}
                      {sampleToContinue ? 'Continue sample invoice' : 'Add New Bill · बिल जोड़ें'}
                    </button>
                  </div>
                  {view === 'overview' && (
                    <>
                      <DailyRecordsSummary
                        openRecords={(route) => followSource(route || '/records/customers')}
                      />
                      <section className="quick-actions" aria-label="Quick shop actions">
                        <button
                          className="button primary"
                          onClick={openIntake}
                          disabled={!session.permissions.includes('write')}
                        >
                          + New Bill <small>सामान आया</small>
                        </button>
                        <button
                          className="button secondary"
                          onClick={() => followSource('/records/new-credit')}
                          disabled={!session.permissions.includes('write')}
                        >
                          + Customer Udhaar <small>उधार दिया</small>
                        </button>
                        <button
                          className="button secondary"
                          onClick={() => followSource('/records/galla')}
                        >
                          Settle Galla <small>गल्ला मिलाओ</small>
                        </button>
                      </section>
                      <BusinessBrief follow={followSource} />
                      <div className="section-caption">
                        <span>AT A GLANCE</span>
                        <span className="muted">
                          All-time supplier ledger ·{' '}
                          {session.store.demo ? 'synthetic demo' : 'your recorded store'}
                        </span>
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
                            <p>Track open claims and confirmed recovery.</p>
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
                </>
              )}
              {view === 'more' && (
                <section className="panel more-panel">
                  <h2>Supplier money · सप्लायर का हिसाब</h2>
                  <button className="button secondary full" onClick={() => navigate('cases')}>
                    Missing Items &amp; Refunds · कम सामान का पैसा
                  </button>
                  <button className="button secondary full" onClick={() => navigate('suppliers')}>
                    Supplier details · सप्लायर
                  </button>
                  <button className="button secondary full" onClick={() => navigate('insights')}>
                    Money returned · वापस मिला पैसा
                  </button>
                  <h2>Cash &amp; payments · गल्ला और पेमेंट</h2>
                  <button
                    className="button secondary full"
                    onClick={() => followSource('/records/galla')}
                  >
                    Galla Hisab (गल्ला हिसाब) / Cash Drawer
                  </button>
                  <button className="button secondary full" onClick={() => navigate('records')}>
                    Daily records
                  </button>
                  <h2>Manage your business</h2>
                  <button className="button secondary full" onClick={() => navigate('exports')}>
                    Export purchases
                  </button>
                  <button className="button secondary full" onClick={() => navigate('connections')}>
                    Connections
                  </button>
                  <button className="button secondary full" onClick={() => navigate('planning')}>
                    Stock planning
                  </button>
                  <button className="button secondary full" onClick={() => navigate('assistant')}>
                    Merchant help & language
                  </button>
                  <button className="button secondary full" onClick={() => navigate('payments')}>
                    Check Paytm payments
                  </button>
                  <button className="button secondary full" onClick={() => navigate('cases')}>
                    Missing Items & Refunds
                  </button>
                  <button className="button secondary full" onClick={() => navigate('suppliers')}>
                    Supplier balances <ChevronRight size={18} />
                  </button>
                  <button className="button secondary full" onClick={() => navigate('insights')}>
                    Money returned and export <ChevronRight size={18} />
                  </button>
                  <button className="button secondary full" onClick={() => setHelp(true)}>
                    Workflow guide <ChevronRight size={18} />
                  </button>
                  <label className="field">
                    Interface language
                    <select value={locale} onChange={(e) => setLocale(e.target.value)}>
                      <option value="en">English</option>
                      <option value="hi">हिन्दी · navigation only</option>
                      <option value="kn">ಕನ್ನಡ · navigation only</option>
                    </select>
                  </label>
                  {locale !== 'en' && (
                    <p className="locale-note">
                      Only navigation labels change. Bills and other workflows remain in English.
                    </p>
                  )}
                  <p>
                    Role: {session.role}.{' '}
                    {session.store.demo ? 'Sample records only.' : 'Your store account.'}
                  </p>
                  <button
                    className="button secondary full"
                    onClick={() => setDeviceWorkspace(true)}
                  >
                    Saved on Phone
                  </button>
                  <AccountSecurity />
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
              {session.store.demo
                ? 'Synthetic demo store · Sample records only'
                : session.store.name}
            </span>
          </footer>
        </main>
      </div>
      <nav className="bottom-nav" aria-label="Main navigation">
        {[
          ['overview', shellLabels.home, LayoutDashboard],
          ['purchases', shellLabels.purchases, ReceiptText],
          ['records', shellLabels.records, Store],
          ['more', shellLabels.more, CircleHelp],
        ].map(([id, label, Icon]) => (
          <button
            key={id}
            aria-current={
              view === id ||
              (id === 'more' &&
                [
                  'suppliers',
                  'insights',
                  'assistant',
                  'payments',
                  'planning',
                  'connections',
                  'exports',
                ].includes(view))
                ? 'page'
                : undefined
            }
            onClick={() => {
              setSourceRoute(id === 'records' ? '/records/customers' : '');
              navigate(id);
              setDeviceWorkspace(false);
            }}
          >
            <Icon size={21} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      {adding && <InvoiceModal close={() => setAdding(false)} create={onCreate} config={config} />}
      {help && (
        <Modal
          title="How supplier claims work"
          subtitle="From checking a bill to confirming recovery."
          close={() => setHelp(false)}
        >
          <div className="guide">
            {[
              [
                '01',
                'Add your invoice',
                'Upload a bill or enter its details. Check quantities, units and prices against the original.',
              ],
              [
                '02',
                'Confirm the delivery',
                'Enter what actually arrived, check each unit and confirm whether delivery is complete.',
              ],
              [
                '03',
                'Review the shortage',
                'Review the math. Download the evidence or open a supplier message. Confirm sharing only after sending.',
              ],
              [
                '04',
                'Follow through to resolution',
                'Track the supplier’s response. Confirm recovery only after a credit is applied or a refund arrives, with matching proof.',
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
            <p className="muted">
              You review every message before sharing. A supplier promise stays open until recovery
              is confirmed.
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
