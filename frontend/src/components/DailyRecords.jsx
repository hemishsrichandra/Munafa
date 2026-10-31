import React, { useEffect, useState } from 'react';
import { api, money, today } from '../api';
import { MoneyInput } from './MoneyInput';
import { useSession } from '../session';
import { useOffline } from '../offline/provider';
import * as db from '../offline/db';

const labels = {
  opening_due: 'Opening customer due',
  credit_sale: 'Sale on credit',
  cash_sale: 'Paid sale',
  collection: 'Customer payment received',
  expense: 'Expense paid',
  opening_cash: 'Opening cash balance',
  payable: 'Upcoming amount to pay',
  payable_payment: 'Payment of recorded payable',
};
const freshEntry = () => ({
  kind: 'credit_sale',
  reference: '',
  customer_id: '',
  amount_paise: null,
  occurred_on: today(),
  due_on: '',
  category: 'other',
  payment_channel: 'cash',
  note: '',
  target_id: '',
  merchant_confirmed: false,
});
const freshCustomer = () => ({
  name: '',
  reference: '',
  phone: '',
  marketing_consent: false,
  consent_note: '',
});
function Field({ label, children }) {
  return (
    <label className="field">
      {label}
      {children}
    </label>
  );
}
function Text({ label, value, onChange, type = 'text', required = false }) {
  return (
    <Field label={label}>
      <input
        type={type}
        value={value ?? ''}
        required={required}
        onChange={(e) => onChange(e.target.value)}
      />
    </Field>
  );
}
function Check({ children, checked, onChange }) {
  return (
    <label className="check-field">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {children}
    </label>
  );
}

export function DailyRecords() {
  const local = useOffline();
  const session = useSession(),
    canWrite = session.permissions.includes('write'),
    canApprove = session.permissions.includes('approve'),
    canMessage = session.permissions.includes('messaging');
  const [tab, setTab] = useState('Customers'),
    [data, setData] = useState(null),
    [tasks, setTasks] = useState([]),
    [campaigns, setCampaigns] = useState([]),
    [staff, setStaff] = useState([]);
  const [error, setError] = useState(''),
    [notice, setNotice] = useState(''),
    [busy, setBusy] = useState(false),
    [customer, setCustomer] = useState(freshCustomer),
    [entry, setEntry] = useState(freshEntry),
    [reverse, setReverse] = useState(null),
    [reminder, setReminder] = useState('');
  const [task, setTask] = useState({
    title: '',
    category: 'other',
    due_on: today(),
    assignee_id: '',
    note: '',
  });
  const [campaign, setCampaign] = useState({
    title: '',
    text: '',
    recipient_ids: [],
    merchant_confirmed: false,
  });
  const [horizon, setHorizon] = useState('30');
  const [segment, setSegment] = useState('all');
  async function load() {
    const [d, t, c, s] = await Promise.all([
      api('/records/summary'),
      api('/records/tasks'),
      canMessage ? api('/records/campaigns') : [],
      session.permissions.includes('admin') ? api('/records/staff') : [],
    ]);
    setData(d);
    setTasks(t);
    setCampaigns(c);
    setStaff(s);
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);
  async function run(fn) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await fn();
      if (navigator.onLine) await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const changeEntry = (k, v) => setEntry((x) => ({ ...x, [k]: v, merchant_confirmed: false }));
  const people = data?.customers || [],
    obligations = data?.obligations || [];
  const targetDebts = obligations.filter(
    (d) =>
      d.remaining_paise > 0 &&
      (entry.kind === 'collection'
        ? ['opening_due', 'credit_sale'].includes(d.kind) && d.customer_id === entry.customer_id
        : d.kind === 'payable'),
  );
  const customerName = (id) => people.find((c) => c.id === id)?.name || 'Store / supplier';
  const activeTasks = tasks.filter((t) => t.status === 'open');
  const end = new Date(today() + 'T12:00:00');
  end.setDate(end.getDate() + Number(horizon));
  const endDate = end.toISOString().slice(0, 10);
  const upcoming = obligations.filter(
    (d) => d.remaining_paise > 0 && d.due_on && d.due_on <= endDate,
  );
  const incoming = upcoming
      .filter((d) => d.kind !== 'payable')
      .reduce((n, d) => n + d.remaining_paise, 0),
    outgoing = upcoming
      .filter((d) => d.kind === 'payable')
      .reduce((n, d) => n + d.remaining_paise, 0);
  return (
    <section className="partner-screen daily-records">
      <div className="page-heading">
        <div>
          <div className="eyebrow">YOUR MANUAL RECORDS</div>
          <h1>Daily records</h1>
          <p>Customers, money and daily tasks — reviewed by you.</p>
        </div>
      </div>
      <p className="info-box">
        {session.store.demo ? 'Synthetic demo store. ' : ''}These are merchant-entered records. They
        are not verified bank/POS data. Save financial drafts on this device when disconnected;
        review and queue explicitly from Drafts & sync. Balances change only after server
        acceptance.
      </p>
      <div className="tabs" style={{ flexWrap: 'wrap' }}>
        {['Customers', 'Sales & expenses', 'Tasks', 'Cash outlook', 'Marketing drafts'].map((t) => (
          <button key={t} className={tab === t ? 'chosen' : ''} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>
      {error && (
        <p className="error-box" role="alert">
          {error}
          <button className="text-button" onClick={() => run(load)}>
            Reload
          </button>
        </p>
      )}
      {notice && (
        <p className="info-box" role="status">
          {notice}
        </p>
      )}
      {!data && !error && <p role="status">Loading manual records…</p>}
      <fieldset disabled={busy} style={{ border: 0, padding: 0, minWidth: 0 }}>
        {tab === 'Customers' && (
          <>
            <section className="panel">
              <h2>Customer accounts</h2>
              <p>
                Balances come only from explicit opening dues, credit sales and allocated customer
                payments.
              </p>
              {!people.length && <p>No customers recorded yet.</p>}
              {people.map((p) => (
                <article className="panel" key={p.id}>
                  <h3>{p.name}</h3>
                  <p>
                    {p.reference} · {p.phone || 'No phone recorded'}
                  </p>
                  <p>
                    <strong>{money(p.outstanding_paise)} pending</strong> · {p.recorded_sale_count}{' '}
                    recorded sales
                  </p>
                  <p>
                    Last recorded sale: {p.last_recorded_sale || 'None'}. This does not establish
                    whether the customer visited elsewhere or made unrecorded purchases.
                  </p>
                  <p>
                    Local marketing selection:{' '}
                    {p.marketing_consent ? 'Agreed' : 'Not agreed / withdrawn'}
                  </p>
                  {canWrite && (
                    <button
                      className="button secondary"
                      onClick={() => {
                        setCustomer({ ...p });
                        setReminder('');
                      }}
                    >
                      Edit customer
                    </button>
                  )}{' '}
                  {canMessage && p.outstanding_paise > 0 && (
                    <button
                      className="button secondary"
                      onClick={() =>
                        run(async () => {
                          const r = await api(`/records/customers/${p.id}/reminder`, {
                            method: 'POST',
                          });
                          setReminder(r.text);
                        })
                      }
                    >
                      Prepare payment reminder
                    </button>
                  )}
                </article>
              ))}
              {reminder && (
                <div className="info-box">
                  <h3>Reminder draft — nothing sent</h3>
                  <p>{reminder}</p>
                  <p>
                    Review with the customer before sharing manually. No payment link has been
                    generated.
                  </p>
                </div>
              )}
            </section>
            {canWrite && (
              <form
                className="panel"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(async () => {
                    const body = {
                      name: customer.name,
                      reference: customer.reference,
                      phone: customer.phone,
                      marketing_consent: customer.marketing_consent,
                      consent_note: customer.consent_note,
                    };
                    await api(
                      customer.id ? `/records/customers/${customer.id}` : '/records/customers',
                      {
                        method: customer.id ? 'PATCH' : 'POST',
                        body: customer.id ? { ...body, version: customer.version } : body,
                      },
                    );
                    setCustomer(freshCustomer());
                    setNotice('Customer recorded.');
                  });
                }}
              >
                <h2>{customer.id ? 'Edit customer' : 'Add customer'}</h2>
                <div className="form-grid">
                  <Text
                    label="Customer name"
                    required
                    value={customer.name}
                    onChange={(v) => setCustomer({ ...customer, name: v })}
                  />
                  <Text
                    label="Customer reference"
                    required
                    value={customer.reference}
                    onChange={(v) => setCustomer({ ...customer, reference: v })}
                  />
                  <Text
                    label="Phone (optional)"
                    value={customer.phone}
                    onChange={(v) => setCustomer({ ...customer, phone: v })}
                  />
                </div>
                <Check
                  checked={customer.marketing_consent}
                  onChange={(v) => setCustomer({ ...customer, marketing_consent: v })}
                >
                  Customer agreed to being selected in local promotional drafts
                </Check>
                <Text
                  label="Consent or withdrawal note"
                  value={customer.consent_note}
                  onChange={(v) => setCustomer({ ...customer, consent_note: v })}
                />
                <p>
                  Record the customer's actual choice and date. This does not authorise WhatsApp/API
                  delivery.
                </p>
                <button className="button primary">Save customer</button>{' '}
                {customer.id && (
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() => setCustomer(freshCustomer())}
                  >
                    Cancel editing
                  </button>
                )}
              </form>
            )}
          </>
        )}
        {tab === 'Sales & expenses' && (
          <>
            {canWrite && (
              <form
                className="panel"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(async () => {
                    await api('/records/entries', {
                      method: 'POST',
                      body: {
                        ...entry,
                        customer_id: entry.customer_id || null,
                        target_id: entry.target_id || null,
                        due_on: entry.due_on || null,
                      },
                    });
                    setEntry(freshEntry());
                    setNotice(
                      'Reviewed record saved. Original entries cannot be edited; an owner can reverse a mistake.',
                    );
                  });
                }}
              >
                <h2>Record reviewed activity</h2>
                <p>
                  Choose the payment channel you actually checked. Bank and UPI receipts do not
                  change cash in the drawer. A paid sale is already paid. Choose how the money
                  moved; bank/UPI amounts do not change the cash-drawer balance. A credit sale
                  creates a debt. Customer payments settle only the obligation you choose. Sales
                  here record amounts; stock changes still use the existing reviewed stock-movement
                  workflow.
                </p>
                <div className="form-grid">
                  <Field label="Record type">
                    <select
                      value={entry.kind}
                      onChange={(e) => setEntry({ ...freshEntry(), kind: e.target.value })}
                    >
                      {Object.entries(labels).map(([v, l]) => (
                        <option key={v} value={v}>
                          {l}
                        </option>
                      ))}
                    </select>
                  </Field>
                  {['opening_due', 'credit_sale', 'cash_sale', 'collection'].includes(
                    entry.kind,
                  ) && (
                    <Field label="Customer">
                      <select
                        value={entry.customer_id}
                        required={entry.kind !== 'cash_sale'}
                        onChange={(e) =>
                          setEntry({
                            ...entry,
                            customer_id: e.target.value,
                            target_id: '',
                            merchant_confirmed: false,
                          })
                        }
                      >
                        <option value="">
                          {entry.kind === 'cash_sale' ? 'Walk-in / no customer' : 'Choose customer'}
                        </option>
                        {people.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name} · {p.reference}
                          </option>
                        ))}
                      </select>
                    </Field>
                  )}
                  {['cash_sale', 'collection', 'expense', 'payable_payment'].includes(
                    entry.kind,
                  ) && (
                    <Field label="Payment channel">
                      <select
                        value={entry.payment_channel || 'cash'}
                        onChange={(e) => changeEntry('payment_channel', e.target.value)}
                      >
                        <option value="cash">Cash</option>
                        <option value="bank">Bank (manually checked)</option>
                        <option value="upi">UPI (manually checked)</option>
                        <option value="other">Other noncash (manually checked)</option>
                      </select>
                    </Field>
                  )}
                  <Text
                    label="Unique record reference"
                    required
                    value={entry.reference}
                    onChange={(v) => changeEntry('reference', v)}
                  />
                  <MoneyInput
                    label="Recorded amount (₹)"
                    value={entry.amount_paise}
                    change={(v) => changeEntry('amount_paise', v)}
                  />
                  <Text
                    label="Actual record date"
                    required
                    type="date"
                    value={entry.occurred_on}
                    onChange={(v) => changeEntry('occurred_on', v)}
                  />
                  {['opening_due', 'credit_sale', 'payable'].includes(entry.kind) && (
                    <Text
                      label="Due date (optional)"
                      type="date"
                      value={entry.due_on}
                      onChange={(v) => changeEntry('due_on', v)}
                    />
                  )}
                  {['collection', 'payable_payment'].includes(entry.kind) && (
                    <Field label="Allocate payment to">
                      <select
                        required
                        value={entry.target_id}
                        onChange={(e) => changeEntry('target_id', e.target.value)}
                      >
                        <option value="">Choose open obligation</option>
                        {targetDebts.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.reference} · {money(d.remaining_paise)} remaining
                          </option>
                        ))}
                      </select>
                    </Field>
                  )}
                  {entry.kind === 'expense' && (
                    <Field label="Reviewed expense category">
                      <select
                        value={entry.category}
                        onChange={(e) => changeEntry('category', e.target.value)}
                      >
                        {['stock', 'rent', 'utilities', 'wages', 'transport', 'other'].map((c) => (
                          <option key={c}>{c}</option>
                        ))}
                      </select>
                    </Field>
                  )}
                  <Text
                    label="Source / reason"
                    required
                    value={entry.note}
                    onChange={(v) => changeEntry('note', v)}
                  />
                </div>
                <Check
                  checked={entry.merchant_confirmed}
                  onChange={(v) => setEntry({ ...entry, merchant_confirmed: v })}
                >
                  I checked this entry's type, amount, date and allocation against my source.
                </Check>
                <button
                  className="button primary"
                  disabled={!entry.merchant_confirmed || !navigator.onLine}
                >
                  Save reviewed entry
                </button>{' '}
                <button
                  type="button"
                  className="button secondary"
                  onClick={() =>
                    run(async () => {
                      await db.saveDraft(local.scope, {
                        id: crypto.randomUUID(),
                        kind: 'business_entry',
                        payload: {
                          ...entry,
                          customer_id: entry.customer_id || null,
                          target_id: entry.target_id || null,
                          due_on: entry.due_on || null,
                        },
                      });
                      await local.refresh();
                      setNotice(
                        'Saved on this device. Review and queue from Drafts & sync; balances unchanged.',
                      );
                    })
                  }
                >
                  Save record on device
                </button>
              </form>
            )}
            <section className="panel">
              <h2>Recorded history</h2>
              <p>
                Latest 100 entries. Summary calculations include all records within the stated
                prototype limit; reversals remain visible.
              </p>
              {!data?.entries.length && <p>No activity recorded yet.</p>}
              {data?.entries.map((r) => (
                <article className="panel" key={r.id}>
                  <h3>
                    {labels[r.kind] || 'Reversal'} · {money(r.amount_paise)}
                  </h3>
                  <p>
                    {r.reference} · {r.occurred_on} · {customerName(r.customer_id)} ·{' '}
                    {r.payment_channel}
                  </p>
                  <p>{r.note}</p>
                  {r.reversed && <p>Reversed — retained for history.</p>}
                  {r.target_id && <small>Allocated to source {r.target_id}</small>}
                  {r.reversal_of && <small>Reverses {r.reversal_of}</small>}
                  {canApprove && r.kind !== 'reversal' && !r.reversed && (
                    <button
                      className="button secondary"
                      onClick={() =>
                        setReverse({
                          id: r.id,
                          reference: '',
                          reason: '',
                          merchant_confirmed: false,
                        })
                      }
                    >
                      Correct by reversal
                    </button>
                  )}
                </article>
              ))}
            </section>
            {reverse && (
              <form
                className="panel"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(async () => {
                    await api(`/records/entries/${reverse.id}/reverse`, {
                      method: 'POST',
                      body: {
                        reference: reverse.reference,
                        reason: reverse.reason,
                        merchant_confirmed: reverse.merchant_confirmed,
                      },
                    });
                    setReverse(null);
                    setNotice('Reversal appended; original record retained.');
                  });
                }}
              >
                <h2>Review reversal</h2>
                <p>Source: {reverse.id}. Reverse its allocated payments first if any exist.</p>
                <Text
                  label="Reversal reference"
                  required
                  value={reverse.reference}
                  onChange={(v) =>
                    setReverse({ ...reverse, reference: v, merchant_confirmed: false })
                  }
                />
                <Text
                  label="Correction reason"
                  required
                  value={reverse.reason}
                  onChange={(v) => setReverse({ ...reverse, reason: v, merchant_confirmed: false })}
                />
                <Check
                  checked={reverse.merchant_confirmed}
                  onChange={(v) => setReverse({ ...reverse, merchant_confirmed: v })}
                >
                  I reviewed the original and want to reverse this record.
                </Check>
                <button className="button primary" disabled={!reverse.merchant_confirmed}>
                  Append reversal
                </button>{' '}
                <button type="button" className="button secondary" onClick={() => setReverse(null)}>
                  Cancel reversal
                </button>
              </form>
            )}
          </>
        )}
        {tab === 'Tasks' && (
          <>
            <section className="panel">
              <h2>Daily tasks</h2>
              <p>
                {activeTasks.length} open · {activeTasks.filter((t) => t.due_on < today()).length}{' '}
                overdue. Compliance dates are entered by you or your adviser; no legal deadline is
                inferred.
              </p>
              {!tasks.length && <p>No tasks recorded.</p>}
              {tasks.map((t) => (
                <article className="panel" key={t.id}>
                  <h3>{t.title}</h3>
                  <p>
                    {t.category} · {t.due_on} · {t.status}
                    {t.status === 'open' && t.due_on < today() ? ' · OVERDUE' : ''}
                  </p>
                  <p>{t.note}</p>
                  <small>
                    Assigned to{' '}
                    {staff.find((s) => s.user_id === t.assignee_id)?.username ||
                      (t.assignee_id === session.user_id ? 'you' : t.assignee_id)}
                  </small>
                  {canWrite &&
                    (session.permissions.includes('admin') ||
                      t.assignee_id === session.user_id) && (
                      <button
                        className="button secondary"
                        onClick={() =>
                          run(async () => {
                            await api(`/records/tasks/${t.id}`, {
                              method: 'PATCH',
                              body: {
                                version: t.version,
                                status: t.status === 'done' ? 'open' : 'done',
                              },
                            });
                            setNotice('Task status saved.');
                          })
                        }
                      >
                        {t.status === 'done' ? 'Reopen task' : 'Mark task done'}
                      </button>
                    )}
                </article>
              ))}
            </section>
            {canWrite && (
              <form
                className="panel"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(async () => {
                    await api('/records/tasks', {
                      method: 'POST',
                      body: { ...task, assignee_id: task.assignee_id || null },
                    });
                    setTask({
                      title: '',
                      category: 'other',
                      due_on: today(),
                      assignee_id: '',
                      note: '',
                    });
                    setNotice('Task assigned.');
                  });
                }}
              >
                <h2>Add task or reminder</h2>
                <div className="form-grid">
                  <Text
                    label="Task title"
                    required
                    value={task.title}
                    onChange={(v) => setTask({ ...task, title: v })}
                  />
                  <Text
                    label="Task due date"
                    required
                    type="date"
                    value={task.due_on}
                    onChange={(v) => setTask({ ...task, due_on: v })}
                  />
                  <Field label="Task category">
                    <select
                      value={task.category}
                      onChange={(e) => setTask({ ...task, category: e.target.value })}
                    >
                      {['opening', 'closing', 'followup', 'compliance', 'other'].map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </Field>
                  {staff.length > 0 && (
                    <Field label="Assign to">
                      <select
                        value={task.assignee_id}
                        onChange={(e) => setTask({ ...task, assignee_id: e.target.value })}
                      >
                        <option value="">Me</option>
                        {staff
                          .filter((s) => s.role !== 'viewer')
                          .map((s) => (
                            <option key={s.user_id} value={s.user_id}>
                              {s.username} · {s.role}
                            </option>
                          ))}
                      </select>
                    </Field>
                  )}
                  <Text
                    label="Task note"
                    value={task.note}
                    onChange={(v) => setTask({ ...task, note: v })}
                  />
                </div>
                <button className="button primary">Save task</button>
              </form>
            )}
          </>
        )}
        {tab === 'Cash outlook' && (
          <section className="panel">
            <h2>Manual cash outlook</h2>
            <p>{data?.cash.warning}</p>
            <p>
              Recorded cash:{' '}
              <strong>
                {data?.cash.opening_recorded
                  ? money(data.cash.recorded_balance_paise)
                  : 'Unknown — record an opening cash balance first'}
              </strong>
            </p>
            <p>
              Recorded sales: {money(data?.sales_paise)}. This includes credit sales, which are not
              cash collected.
            </p>
            <Field label="Outlook period">
              <select value={horizon} onChange={(e) => setHorizon(e.target.value)}>
                <option value="7">Next 7 days and overdue</option>
                <option value="30">Next 30 days and overdue</option>
              </select>
            </Field>
            <p>
              Customer obligations due in this window: {money(incoming)}. Payables due:{' '}
              {money(outgoing)}.
            </p>
            {data?.cash.opening_recorded && (
              <p>
                Scenario if all these dues are collected and payables paid:{' '}
                <strong>{money(data.cash.recorded_balance_paise + incoming - outgoing)}</strong>.
                Collections are not guaranteed.
              </p>
            )}
            {obligations
              .filter((d) => d.remaining_paise > 0)
              .map((d) => (
                <p key={d.id}>
                  {d.reference} · {customerName(d.customer_id)} · {money(d.remaining_paise)}{' '}
                  remaining · {d.due_on || 'Due date unknown'}
                  {d.due_on && d.due_on < today() ? ' · overdue' : ''}
                </p>
              ))}
            <h3>Reviewed expenses</h3>
            {Object.entries(data?.expenses_by_category || {}).map(([c, n]) => (
              <p key={c}>
                {c}: {money(n)}
              </p>
            ))}
            <p>
              Missing purchases, unrecorded cash, other bank accounts and obligations are not
              inferred. Paytm connection, loan eligibility and automatic forecasts remain
              unavailable.
            </p>
          </section>
        )}
        {tab === 'Marketing drafts' && (
          <>
            {!canMessage ? (
              <section className="panel">
                <p>Your role can view customer records but cannot prepare marketing drafts.</p>
              </section>
            ) : (
              <>
                <form
                  className="panel"
                  onSubmit={(e) => {
                    e.preventDefault();
                    run(async () => {
                      await api('/records/campaigns', { method: 'POST', body: campaign });
                      setCampaign({
                        title: '',
                        text: '',
                        recipient_ids: [],
                        merchant_confirmed: false,
                      });
                      setNotice('Local campaign draft saved. Nothing sent.');
                    });
                  }}
                >
                  <h2>Local promotional draft</h2>
                  <p>
                    Recipients must have a recorded affirmative choice. No WhatsApp account,
                    delivery API or automatic sending is connected.
                  </p>
                  <Text
                    label="Campaign title"
                    required
                    value={campaign.title}
                    onChange={(v) =>
                      setCampaign({ ...campaign, title: v, merchant_confirmed: false })
                    }
                  />
                  <Field label="Promotion text">
                    <textarea
                      required
                      maxLength={1600}
                      value={campaign.text}
                      onChange={(e) =>
                        setCampaign({
                          ...campaign,
                          text: e.target.value,
                          merchant_confirmed: false,
                        })
                      }
                    />
                  </Field>
                  <h3>Review recipients</h3>
                  <Field label="Recipient activity filter">
                    <select value={segment} onChange={(e) => setSegment(e.target.value)}>
                      <option value="all">All agreed customers</option>
                      <option value="repeat">Two or more recorded sales</option>
                      <option value="quiet">No recorded sale in 30 days</option>
                    </select>
                  </Field>
                  <p>
                    Filters use recorded sales only, not actual visit history. Previously selected
                    recipients remain selected until unchecked.
                  </p>
                  {people
                    .filter(
                      (p) =>
                        p.marketing_consent &&
                        (segment === 'all' ||
                          (segment === 'repeat'
                            ? p.recorded_sale_count >= 2
                            : p.no_recorded_sale_in_30_days)),
                    )
                    .map((p) => (
                      <Check
                        key={p.id}
                        checked={campaign.recipient_ids.includes(p.id)}
                        onChange={(v) =>
                          setCampaign({
                            ...campaign,
                            recipient_ids: v
                              ? [...campaign.recipient_ids, p.id]
                              : campaign.recipient_ids.filter((id) => id !== p.id),
                            merchant_confirmed: false,
                          })
                        }
                      >
                        {p.name} · {p.recorded_sale_count} recorded sales
                      </Check>
                    ))}
                  {!people.some((p) => p.marketing_consent) && (
                    <p>No eligible recipients. Record the customer's choice first.</p>
                  )}
                  <Check
                    checked={campaign.merchant_confirmed}
                    onChange={(v) => setCampaign({ ...campaign, merchant_confirmed: v })}
                  >
                    I reviewed this text and the selected recipients for a local draft.
                  </Check>
                  <button
                    className="button primary"
                    disabled={!campaign.merchant_confirmed || !campaign.recipient_ids.length}
                  >
                    Save campaign draft
                  </button>
                </form>
                <section className="panel">
                  <h2>Saved campaign drafts</h2>
                  {!campaigns.length && <p>No campaigns drafted.</p>}
                  {campaigns.map((c) => (
                    <article className="panel" key={c.id}>
                      <h3>{c.title}</h3>
                      <p style={{ whiteSpace: 'pre-wrap' }}>{c.text}</p>
                      <p>
                        Draft only · {c.currently_eligible_recipient_ids.length} currently eligible
                        recipients. Nothing sent.
                      </p>
                      {c.requires_recipient_review && (
                        <p className="info-box">
                          Consent changed since this draft. Review recipients again before any
                          manual use.
                        </p>
                      )}
                    </article>
                  ))}
                </section>
              </>
            )}
          </>
        )}
      </fieldset>
    </section>
  );
}
