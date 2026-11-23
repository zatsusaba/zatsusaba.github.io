(() => {
  const { measurement, section } = document.currentScript.dataset;
  const preferenceKey = 'reader-metrics-consent';
  const actions = new Set(['news_next_article', 'related_article', 'related_video']);
  const disableKey = 'ga-disable-' + measurement;
  let enabled = false;
  let tagLoaded = false;

  const readPreference = () => {
    try { return localStorage.getItem(preferenceKey); } catch { return null; }
  };
  const savePreference = value => {
    try { localStorage.setItem(preferenceKey, value); } catch { /* the choice still applies to this page */ }
  };

  function reportPath(url) {
    const isVideo = url.pathname === '/video.html' || url.hostname === 'www.youtube.com';
    const id = isVideo && url.searchParams.get(url.pathname === '/video.html' ? 'id' : 'v');
    const suffix = id && /^[A-Za-z0-9_-]{11}$/.test(id) ? '?video=' + id : '';
    return (url.origin === location.origin ? '' : url.hostname) + url.pathname + suffix;
  }

  function start() {
    if (enabled) return;
    enabled = true;
    window[disableKey] = false;
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    const pageUrl = new URL(location.href);
    const referrer = document.referrer ? new URL(document.referrer) : null;
    const pageLocation = pageUrl.origin + pageUrl.pathname;
    const pageReferrer = referrer ? referrer.origin + referrer.pathname : '';
    window.gtag('consent', tagLoaded ? 'update' : 'default', {
      analytics_storage: 'granted', ad_storage: 'denied',
      ad_user_data: 'denied', ad_personalization: 'denied',
    });
    if (!tagLoaded) window.gtag('js', new Date());
    window.gtag('config', measurement, {
      allow_google_signals: false, allow_ad_personalization_signals: false,
      send_page_view: false, page_location: pageLocation, page_referrer: pageReferrer,
      cookie_flags: 'SameSite=Lax;Secure',
    });
    window.gtag('event', 'page_view', {
      send_to: measurement, site_section: section,
      page_location: pageLocation, page_referrer: pageReferrer,
      source_path: reportPath(pageUrl),
    });
    if (!tagLoaded) {
      tagLoaded = true;
      const tag = document.createElement('script');
      tag.async = true;
      tag.src = 'https://www.googletagmanager.com/gtag/js?id=' + measurement;
      document.head.append(tag);
    }
  }

  function stop() {
    const hadConsent = enabled || readPreference() === 'allowed';
    enabled = false;
    window[disableKey] = true;
    if (!hadConsent) return;
    for (const name of ['_ga', '_ga_' + measurement.slice(2)]) {
      document.cookie = name + '=; Max-Age=0; Path=/';
      document.cookie = name + '=; Max-Age=0; Path=/; Domain=' + location.hostname;
    }
  }

  function record(event) {
    if (!enabled || readPreference() === 'denied') return;
    const link = event.target instanceof Element && event.target.closest('a[data-reader-action]');
    if (!link || !actions.has(link.dataset.readerAction)) return;
    const destination = new URL(link.href);
    if (destination.origin !== location.origin && destination.hostname !== 'www.youtube.com') return;
    window.gtag('event', link.dataset.readerAction, {
      send_to: measurement, site_section: section,
      source_path: reportPath(new URL(location.href)),
      destination_path: reportPath(destination),
    });
  }

  const preferences = document.createElement('aside');
  preferences.className = 'reader-metrics';
  preferences.setAttribute('aria-label', 'アクセス解析の設定');
  preferences.innerHTML = '<p>記事や動画への案内を改善するため、Google アナリティクスで閲覧とクリックを計測します。 <a href="/privacy/#reader-measurement">詳細</a></p>'
    + '<div><button type="button" data-choice="allowed">許可する</button>'
    + '<button type="button" data-choice="denied">許可しない</button></div>';
  document.body.append(preferences);
  const footer = document.querySelector('footer');
  const settings = document.createElement('button');
  settings.className = 'reader-metrics-settings';
  settings.type = 'button';
  settings.textContent = 'アクセス解析の設定';
  settings.addEventListener('click', () => {
    preferences.hidden = false;
    preferences.querySelector('button').focus();
  });
  footer.append(settings);
  preferences.addEventListener('click', event => {
    const choice = event.target.dataset.choice;
    if (!choice) return;
    if (choice === 'allowed') start();
    else stop();
    savePreference(choice);
    preferences.hidden = true;
    if (preferences.contains(document.activeElement)) settings.focus({preventScroll: true});
  });
  window.addEventListener('storage', event => {
    if (event.key !== preferenceKey) return;
    if (event.newValue === 'allowed') start();
    else stop();
    preferences.hidden = Boolean(event.newValue);
  });
  document.addEventListener('click', record);
  document.addEventListener('auxclick', event => { if (event.button === 1) record(event); });
  const saved = readPreference();
  preferences.hidden = Boolean(saved);
  if (saved === 'allowed') start();
})();
