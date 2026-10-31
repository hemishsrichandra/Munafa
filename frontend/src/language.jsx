import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { useOffline } from './offline/provider';
import * as db from './offline/db';

// Curated UI labels only: never translate invoice contents, money or approval payloads.
const hindi = {
  Today: 'आज',
  'Deliveries & Stock': 'सामान और स्टॉक',
  'Customer Khata': 'ग्राहक उधार',
  More: 'अन्य',
  'Add new bill': 'नया बिल जोड़ें',
  'New bill': 'नया बिल',
  'Customer credit': 'ग्राहक को उधार',
  'Count cash': 'नकद गिनें',
  'Your shop': 'आपकी दुकान',
  'Your shop today': 'आज का हिसाब',
  'Today’s recorded sales': 'आज की दर्ज बिक्री',
  'Money to collect': 'उधार लेना है',
  'Cash in Galla': 'गल्ले में नकद',
  'Open tasks': 'बाकी काम',
  'Offline drafts': 'ऑफ़लाइन मसौदे',
  'No offline drafts': 'कोई ऑफ़लाइन मसौदा नहीं',
  'Interface language': 'ऐप की भाषा',
  'Language preference could not be saved.': 'भाषा की पसंद सहेजी नहीं जा सकी।',
  'Saved bills': 'सहेजे हुए बिल',
  'Products tracked': 'दर्ज सामान',
  'Expiry watch': 'समाप्ति तारीख',
  Bills: 'बिल',
  Stock: 'स्टॉक',
  'Expiry radar': 'समाप्ति तारीख देखें',
  'Review invoice': 'बिल जाँचें',
  Supplier: 'सप्लायर',
  'Invoice reference': 'बिल नंबर',
  'Invoice date': 'बिल की तारीख',
  Description: 'सामान का नाम',
  'Billed quantity': 'बिल में मात्रा',
  Unit: 'इकाई',
  'Unit price (₹)': 'प्रति इकाई कीमत (₹)',
  'Invoice total (₹)': 'बिल की कुल राशि (₹)',
  'Save invoice draft': 'बिल का मसौदा सहेजें',
  'Save purchase on device': 'बिल इस डिवाइस पर सहेजें',
  'Back to saved bills': 'सहेजे हुए बिल देखें',
  'Count delivered items': 'आए सामान की गिनती',
  'Missing items': 'सामान कम आया',
  'Low stock': 'स्टॉक कम है',
  'What the bill says': 'बिल में क्या लिखा है',
  Customers: 'ग्राहक',
  'Sales & spending': 'बिक्री और खर्च',
  'Shop tasks': 'दुकान के काम',
  'Galla Hisab': 'गल्ले का हिसाब',
  'Offer messages': 'ऑफ़र संदेश',
  'Shop settings': 'दुकान की सेटिंग',
  'Gave credit (−)': 'उधार दिया (−)',
  'Received payment (+)': 'पैसा मिला (+)',
  'Money to pay': 'पैसा देना है',
  'Supplier money': 'सप्लायर का हिसाब',
  'Missing Items & Refunds': 'कम सामान और वापसी',
  'Supplier details': 'सप्लायर की जानकारी',
  'Money returned': 'वापस मिला पैसा',
  'Cash & payments': 'नकद और पेमेंट',
  'Cash drawer': 'नकद गल्ला',
  'Sign out': 'साइन आउट',
  'View account history': 'खाते का इतिहास देखें',
  'Needs your attention': 'ध्यान देने वाले काम',
  'Continue current bill': 'मौजूदा बिल जारी रखें',
  'Discard and start new bill': 'बदलाव छोड़कर नया बिल खोलें',
};
Object.assign(hindi, {
  'See bill and counted quantities': 'बिल और दर्ज गिनती देखें',
  'Record money received': 'मिला पैसा दर्ज करें',
  'Offline drafts': 'ऑफ़लाइन मसौदे',
  'Saved on this device': 'इस डिवाइस पर सहेजा गया',
  'Waiting to sync': 'सिंक होने की प्रतीक्षा',
  Syncing: 'सिंक हो रहा है',
  Synced: 'सिंक हो गया',
  'Needs attention': 'ध्यान दें',
  Conflict: 'बदलाव की जाँच करें',
  'Daily records': 'दैनिक हिसाब',
  'Export purchases': 'खरीद के रिकॉर्ड डाउनलोड करें',
  Connections: 'कनेक्शन',
  'Stock planning': 'स्टॉक की योजना',
  'Merchant help & language': 'मदद और भाषा',
  'Check Paytm payments': 'Paytm भुगतान जाँचें',
  'Workflow guide': 'ऐप इस्तेमाल करने की मदद',
  'Manage your business': 'दुकान का प्रबंधन',
});
const Context = createContext({
  locale: 'en',
  t: (value) => value,
  setLocale: () => {},
  ready: true,
  error: '',
});
export const useLanguage = () => useContext(Context);
export function LanguageProvider({ children }) {
  const local = useOffline();
  const [locale, update] = useState('en'),
    [ready, setReady] = useState(false),
    [error, setError] = useState('');
  const selected = useRef(false);
  useEffect(() => {
    let active = true;
    selected.current = false;
    update('en');
    setReady(false);
    db.getRecord('cache', `${local.scope}:ui-language`, local.scope)
      .then((row) => {
        if (
          active &&
          !selected.current &&
          row?.expires_at > Date.now() &&
          ['en', 'hi'].includes(row?.locale)
        )
          update(row.locale);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, [local.scope]);
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);
  async function setLocale(value) {
    if (!['en', 'hi'].includes(value)) return;
    selected.current = true;
    update(value);
    setError('');
    try {
      await db.transaction(['meta', 'cache'], async (stores) => {
        if ((await db.requestValue(stores.meta.get('context')))?.scope !== local.scope)
          throw new Error('Changed session');
        stores.cache.put({
          id: `${local.scope}:ui-language`,
          scope: local.scope,
          locale: value,
          expires_at: Date.now() + 365 * 86400000,
        });
      });
    } catch {
      setError('Language preference could not be saved.');
    }
  }
  return (
    <Context.Provider
      value={{
        locale,
        setLocale,
        ready,
        error,
        t: (value) => (locale === 'hi' ? hindi[value] || value : value),
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function LanguagePicker() {
  const { locale, setLocale, ready, t } = useLanguage();
  return (
    <label className="language-picker">
      <span>{t('Interface language')}</span>
      <select
        aria-label={t('Interface language')}
        value={locale}
        disabled={!ready}
        onChange={(e) => setLocale(e.target.value)}
      >
        <option value="en">English</option>
        <option value="hi">हिन्दी</option>
      </select>
    </label>
  );
}
