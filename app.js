const data = window.SITE_DATA || {};
// Curated cast/format/description remain authoritative; sync adds verified YouTube metadata.
const curated = new Map((data.videos || []).map(v=>[v.id,v]));
for (const v of (window.YOUTUBE_VIDEOS || [])) {
 const old=curated.get(v.id);
 curated.set(v.id, old ? {...v,...old,description:old.description?.trim()?old.description:(v.description||''),genres:(v.genres||[]).length?v.genres:old.genres} : v);
}
// Keep the sync catalog intact; only shorten titles in the site view.
const videoDisplayTitle = title => String(title || '').split(/[#＃](?=[\p{L}\p{N}_])/u)[0].trim() || title;
data.videos=[...curated.values()].map(v=>({...v,title:videoDisplayTitle(v.title)}));
const get = key => Array.isArray(data[key]) ? [...data[key]].sort((a,b)=>String(b.date||'').localeCompare(String(a.date||''))) : [];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const asset = u => /^(?:assets|panels-v2)\/[a-zA-Z0-9_./-]+$/.test(u || '') && !String(u).includes('..') ? esc(u) : '';
const external = u => {try {const x=new URL(u);return x.protocol==='https:'?esc(x.href):''} catch{return ''}};
const detailUrl=(type,id)=>`${type}.html?id=${encodeURIComponent(id)}`;
const extLink=(u,label)=>external(u)?`<a href="${external(u)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`:'';
const image=(src,alt='',cls='')=>asset(src)?`<img class="${cls}" src="${asset(src)}" alt="${esc(alt)}" loading="lazy">`:'';
const fallback=(kind)=>kind==='games'?'<div class="empty-feature"><p class="eyebrow">NEW EXPERIENCE</p><strong>次の冒険は、<br>ここから始まる。</strong><p>ゲームは準備中です。公開をお楽しみに。</p><span class="status">COMING SOON</span></div>':`<div class="empty">${kind==='comics'?'4コマ漫画':kind==='videos'?'動画':'お知らせ'}は準備中です。</div>`;
function card(type,item){
 const id=item.id||''; const validId=type==='videos' && /^[A-Za-z0-9_-]{11}$/.test(id);
 if(type==='videos' && validId){const dest=`video.html?id=${encodeURIComponent(id)}`;return `<article class="card video-card"><a class="video-thumb" href="${dest}" aria-label="${esc(item.title)}の詳細"><img src="https://i.ytimg.com/vi/${id}/mqdefault.jpg" alt="" loading="lazy"></a><h2><a href="${dest}">${esc(item.title)}</a></h2><a href="${dest}">動画を見る →</a></article>`}
 if(type==='comics' && id){const dest=detailUrl('comics',id),src=asset(item.thumbnail)||asset((item.panels||[])[0])||asset(item.imageSquare)||asset(item.image);return `<a class="comic-tile" href="${dest}">${src?`<span class="comic-tile-image"><img src="${src}" alt="" loading="lazy"></span>`:''}<span class="comic-tile-copy"><small>${esc(item.series||'COMICS')}</small><strong>${esc(item.title)}</strong></span></a>`}
 const destComic=type==='comics'&&id?detailUrl(type,id):'';const rawThumb=image(item.image,item.title);const thumb=destComic&&rawThumb?`<a href="${destComic}" class="comic-card-image" aria-label="${esc(item.title)}を読む">${rawThumb}</a>`:rawThumb;let dest=type==='videos'?external(item.url):id?detailUrl(type,id):'';return `<article class="card">${thumb}<small>${esc(item.series||item.format||'')} ${esc(item.date||'')}</small><h2>${esc(item.title)}</h2>${item.description?`<p>${esc(item.description)}</p>`:''}${dest?`<a href="${dest}"${type==='videos'?' target="_blank" rel="noopener noreferrer"':''}>${type==='games'?'詳しく見る':type==='comics'?'漫画を読む':'動画を見る'} →</a>`:''}</article>`;
}
function listing(type, limit){let items=get(type); if(limit)items=items.slice(0,limit);return items.length?`<div class="cards ${type==='videos'?'video-grid':type==='comics'?'comic-grid':''}">${items.map(x=>card(type,x)).join('')}</div>`:fallback(type)}
function related(item){let out=[];if(item.videoId && get('videos').some(v=>v.id===item.videoId))out.push(`<a href="video.html?id=${encodeURIComponent(item.videoId)}">関連動画を見る →</a>`);else if(item.video)out.push(extLink(item.video,'関連動画'));if(item.comicId&&get('comics').some(x=>x.id===item.comicId))out.push(`<a href="${detailUrl('comics',item.comicId)}">関連4コマ →</a>`);return out.filter(Boolean).join('')}
function gameDetail(id){let g=get('games').find(x=>x.id===id);if(!g)return '<div class="empty">作品が見つかりません。 <a href="games.html">一覧へ戻る</a></div>';return `<article class="detail"><a href="games.html">← ゲーム一覧</a><p class="eyebrow">FREE GAME</p><h2>${esc(g.title)}</h2><p class="detail-meta">${esc(g.date||'')}</p>${image(g.image,g.title)}<p>${esc(g.description||'')}</p><p>対応OS：${esc(g.os||'準備中')}</p><div class="detail-actions">${g.download?extLink(g.download,'無料ダウンロード'):'<span class="status">配布準備中</span>'}${related(g)}</div><h3>更新履歴</h3>${Array.isArray(g.updates)&&g.updates.length?g.updates.map(u=>`<p>${esc(u.date)}　${esc(u.text)}</p>`).join(''):'<p>準備中</p>'}</article>`}
function comicDetail(id){let items=get('comics'),i=items.findIndex(x=>x.id===id);if(i<0)return '<div class="empty">作品が見つかりません。 <a href="comics.html">一覧へ戻る</a></div>';let c=items[i],vertical=asset(c.image);return `<article class="comic-reader comic-vertical-reader"><a href="comics.html">← 漫画一覧</a><h2>${esc(c.title)}</h2>${vertical?`<button type="button" class="comic-zoom-open" id="zoom-open" aria-label="漫画を拡大"><img class="comic-vertical-image" src="${vertical}" alt="${esc(c.title)}"></button>`:'<p>漫画画像は準備中です。</p>'}<div class="detail-actions">${related(c)}</div></article>`}
function diaryImage(u){if(asset(u))return asset(u);try{const x=new URL(u);return x.protocol==='https:'&&['yt3.ggpht.com','yt3.googleusercontent.com'].includes(x.hostname)?esc(x.href):''}catch{return ''}}
function diaries(){return get('diary').sort((a,b)=>{if(a.date&&b.date)return b.date.localeCompare(a.date)||Number(b.number||0)-Number(a.number||0);return Number(b.number||0)-Number(a.number||0)})}
function diaryCard(x){const url=`diary.html?id=${encodeURIComponent(x.id)}`,src=diaryImage(x.image);return `<a class="diary-card" href="${url}">${src?`<div class="diary-cover"><img src="${src}" alt="" loading="lazy"></div>`:'<div class="diary-cover diary-empty">IMAGE<br>準備中</div>'}<div class="diary-card-body"><small>DIARY / ${esc(x.date||'投稿日未確認')}</small><h3>${esc(x.title)}</h3><span>記事を読む →</span></div></a>`}
function diaryList(limit){let a=diaries();if(limit)a=a.slice(0,limit);return a.length?`<div class="diary-grid">${a.map(diaryCard).join('')}</div>`:'<div class="empty">雑サバ日記は準備中です。</div>'}
function diaryBody(text){const re=/https:\/\/(?:www\.)?(?:youtube\.com|youtu\.be)\/[A-Za-z0-9_/?=&%#.-]+/g;let out='',last=0,m;const value=String(text||'');while((m=re.exec(value))){out+=esc(value.slice(last,m.index));out+=`<a href="${esc(m[0])}" target="_blank" rel="noopener noreferrer">${esc(m[0])}</a>`;last=m.index+m[0].length}return out+esc(value.slice(last))}
function diaryDetail(id){const d=diaries().find(x=>x.id===id);if(!d)return '<div class="empty">日記が見つかりません。 <a href="diary.html">一覧へ戻る</a></div>';let image=diaryImage(d.image);let links=[];if(d.gameId&&get('games').some(g=>g.id===d.gameId))links.push(`<a href="games.html?id=${encodeURIComponent(d.gameId)}">関連ゲーム →</a>`);return `<article class="diary-detail"><a href="diary.html">← 日記一覧へ戻る</a><p class="eyebrow">ZATSUSABA DIARY</p><h2>${esc(d.title)}</h2><p class="detail-meta">${esc(d.date||'投稿日未確認')}</p>${image?`<img class="diary-detail-image" src="${image}" alt="${esc(d.title)}の投稿画像">`:''}<div class="diary-body">${diaryBody(d.body)}</div><div class="detail-actions">${links.join('')}${extLink(d.postUrl,'YouTubeの投稿でコメントする')}</div><a href="diary.html">← 日記一覧へ戻る</a></article>`}
let page=document.body.dataset.page, el=document.querySelector('#content'), id=new URLSearchParams(location.search).get('id');
if(page==='index'){
 const teaser=data.teaser, target=teaser&&get('videos').find(v=>v.id===teaser.videoId&&/^[A-Za-z0-9_-]{11}$/.test(v.id));
 if(target)document.querySelector('#home-teaser').innerHTML=`<a class="home-teaser" href="video.html?id=${encodeURIComponent(target.id)}"><img src="https://i.ytimg.com/vi/${target.id}/mqdefault.jpg" alt="" loading="lazy"><span class="teaser-play" aria-hidden="true">▶</span><span><small>WATCH THE TEASER</small><strong>${esc(teaser.title||target.title)}</strong></span></a>`;
}
if(page==='games'||page==='comics'){
 const character=new URLSearchParams(location.search).get('character');
 if(id) el.innerHTML=page==='games'?gameDetail(id):comicDetail(id);
 else if(page==='comics' && character){const items=get('comics').filter(x=>Array.isArray(x.characters)&&x.characters.includes(character));const person=get('characters').find(x=>x.id===character);el.innerHTML=`<p>${esc(person?.name||'')}の出演4コマ</p>${items.length?`<div class="cards comic-grid">${items.map(x=>card('comics',x)).join('')}</div>`:'<div class="empty">出演4コマはまだ登録されていません。</div>'}<p><a href="comics.html">すべての4コマを見る →</a></p>`} else el.innerHTML=listing(page);
}
if(page==='videos'){
 const topicOrder=['人間','お金','科学','自然','世界','食べ物','遊び','話題'];
 // Match public playlist names, never infer topics from video titles.
 const playlistTopic=label=>{
  const name=String(label).replace(/【[^】]*】/g,'').trim();
  const aliases={'人間の限界':'人間','食事の秘密':'食べ物','ゲームの秘密':'遊び','遊びで雑学':'遊び','マインクラフト｜雑学サバイバル':'遊び'};
  if(aliases[name])return aliases[name];
  return topicOrder.find(topic=>[topic,topic+'の雑学',topic+'の秘密'].includes(name))||'';
 };
 const videos=get('videos').map(v=>({...v,topics:[...new Set((v.genres||[]).map(playlistTopic).filter(Boolean))]}));
 const synced=new Map((window.YOUTUBE_VIDEOS||[]).map(v=>[v.id,v]));
 const videoKind=v=>{
  const source=synced.get(v.id)||{};
  if(source.durationSeconds>180)return 'video';
  if((source.genres||[]).some(g=>/【Shorts】/i.test(g)||g==='ショート漫画【1話完結】'))return 'short';
  if(!source.formatEvidence)return '';
  if(['ショート漫画','通常Shorts','Shorts','Short MV','切り抜き'].includes(source.format))return 'short';
  if(['長尺動画','長尺漫画','フルMV','長尺'].includes(source.format))return 'video';
  return '';
 };
 let kind='';
 const genres=topicOrder.filter(topic=>videos.some(v=>v.topics.includes(topic)));
 const rawRequested=new URLSearchParams(location.search).get('genre');
 const requested=playlistTopic(rawRequested||'');
 let active=genres.includes(requested)?requested:'';
 let shown=24;
 el.innerHTML='<div class="video-kinds" role="group" aria-label="動画形式"></div><div class="video-filters" role="group" aria-label="テーマで絞り込み"></div><p class="video-count" role="status"></p><div class="cards video-grid"></div><button type="button" class="video-more">もっと見る</button>';
 const filters=el.querySelector('.video-filters'), grid=el.querySelector('.video-grid'), more=el.querySelector('.video-more');
 function renderVideos(){
  const selected=videos.filter(v=>(!active||v.topics.includes(active))&&(!kind||videoKind(v)===kind));
  grid.innerHTML=selected.slice(0,shown).map(v=>card('videos',v)).join('');
  el.querySelector('.video-count').textContent=`${active||'すべて'} · ${selected.length}件（新着順）`;
  more.hidden=shown>=selected.length;
  el.querySelectorAll('.video-kinds button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.kind===kind)));
  filters.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.genre===active)));
 }
 for(const [value,label] of [['','すべて'],['video','動画'],['short','ショート']]){
  const button=document.createElement('button');button.type='button';button.dataset.kind=value;button.textContent=label;
  button.addEventListener('click',()=>{kind=value;shown=24;renderVideos();});el.querySelector('.video-kinds').append(button);
 }
 for(const genre of ['',...genres]){
  const button=document.createElement('button');button.type='button';button.dataset.genre=genre;button.textContent=genre||'すべて';
  button.addEventListener('click',()=>{active=genre;shown=24;const url=new URL(location.href);genre?url.searchParams.set('genre',genre):url.searchParams.delete('genre');history.replaceState(null,'',url);renderVideos();});filters.append(button);
 }
 more.addEventListener('click',()=>{shown+=24;renderVideos();});
 renderVideos();
}
if(page==='video'){
 const video=(/^[A-Za-z0-9_-]{11}$/.test(id) ? curated.get(id) : null);
 if(!video)el.innerHTML='<div class="empty">動画が見つかりません。 <a href="videos.html">動画一覧へ戻る</a></div>';
 else {
  document.title=video.title+' | 雑学サバイバル';
  const recommendations=get('videos').filter(v=>v.id!==video.id).slice(0,3);
  const shortVideo=video.format==='通常Shorts'||video.format==='切り抜き'||video.format==='Short MV';
  el.innerHTML=`<article class="watch-detail"><a href="videos.html">← 動画一覧へ戻る</a><h2>${esc(video.title)}</h2>${location.protocol==='file:'?`<div class="file-warning"><strong>HTTPプレビューで開いてください</strong><p>この画面はファイルを直接開いているため、YouTubeを埋め込むとエラー153になることがあります。フォルダ内の START_PREVIEW.bat から起動するか、下のリンクでYouTubeをご覧ください。</p></div>`:`<div class="player ${shortVideo?'player-short':''}"><iframe src="https://www.youtube.com/embed/${video.id}" title="${esc(video.title)}" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe></div>`}<p class="player-help">再生できない場合は <a href="https://www.youtube.com/watch?v=${video.id}" target="_blank" rel="noopener noreferrer">YouTubeで直接見る ↗</a></p><h3>作品紹介</h3><p>${esc(video.description||'作品紹介は準備中です。')}</p><p><a href="videos.html">← 動画一覧へ戻る</a></p></article><section class="recommendations"><h2>おすすめ動画</h2>${recommendations.length?`<div class="cards video-grid">${recommendations.map(x=>card('videos',x)).join('')}</div>`:'<p>関連動画は準備中です。</p>'}</section>`;
  const canonical = new URL(document.querySelector('link[rel="canonical"]')?.href || 'https://zatsusaba.github.io/video.html');
  canonical.searchParams.set('id', id);
  const canonicalLink=document.createElement('link');
  canonicalLink.rel='canonical';
  canonicalLink.href=canonical.href;
  document.head.append(canonicalLink);
  document.querySelector('meta[property="og:url"]')?.setAttribute('content',canonical.href);
  document.querySelector('meta[property="og:title"]')?.setAttribute('content',video.title);
  document.querySelector('meta[property="og:image"]')?.setAttribute('content','https://i.ytimg.com/vi/'+id+'/hqdefault.jpg');
  const summary = (video.description || video.title).slice(0,160);
  for (const selector of ['meta[name="description"]','meta[property="og:description"]']) {
   document.querySelector(selector)?.setAttribute('content',summary);
  }
  fetch('/video-links.json').then(r=>r.json()).then(index=>{
   if(!index[id]?.length) return;
   const box=document.createElement('section');
   const heading=document.createElement('h3');
   heading.textContent='この動画をもっと読む';
   box.append(heading);
   for(const [url,title] of index[id]){
    const row=document.createElement('p'), anchor=document.createElement('a');
    anchor.href=url; anchor.textContent=title; row.append(anchor); box.append(row);
   }
   el.querySelector('.watch-detail').append(box);
  }).catch(()=>{});
 }
}
if(page==='characters'){
 const target=document.querySelector('#characters-content'),person=get('characters').find(x=>x.id===id);
 if(id&&!person)target.innerHTML='<div class="empty">キャラクターが見つかりません。 <a href="characters.html">一覧へ戻る</a></div>';
 else if(person){target.innerHTML=`<article class="cast-profile"><a class="cast-back" href="characters.html">← キャラクター一覧</a><div class="cast-profile-main"><div class="cast-profile-art">${asset(person.image)?image(person.image,person.name):'<div class="cast-placeholder">VISUAL<br>COMING SOON</div>'}</div><div class="cast-profile-copy"><p class="eyebrow">${esc(person.role||'CHARACTER')}</p><h2>${esc(person.name)}</h2><p class="cast-description">${esc(person.description||'')}</p></div></div></article>`}
 else target.innerHTML=`<div class="cast-grid">${get('characters').map((c,i)=>`<a class="cast-card" href="characters.html?id=${encodeURIComponent(c.id)}"><div class="cast-art">${asset(c.image)?image(c.image,c.name):'<div class="cast-placeholder">VISUAL<br>COMING SOON</div>'}</div><div class="cast-card-copy"><small>${esc(c.role||'CHARACTER')}</small><h2>${esc(c.name)}</h2><p>${esc(c.description||'')}</p></div></a>`).join('')}</div><div class="cast-videos-link"><a class="button red" href="videos.html">動画一覧を見る ↗</a></div>`;
}
if(page==='diary'){
 if(id)el.innerHTML=diaryDetail(id);
 else {const entries=diaries();el.innerHTML=entries.length?`<div class="diary-stream">${entries.map(d=>`<section class="diary-entry" id="diary-${encodeURIComponent(d.id)}">${diaryDetail(d.id).replaceAll('<a href="diary.html">← 日記一覧へ戻る</a>','')}</section>`).join('')}</div>`:'<div class="empty">雑サバ日記は準備中です。</div>'}
}
if(page==='news'){let items=get('news');el.innerHTML=items.length?items.map(n=>`<article class="news-row"><time>${esc(n.date)}</time>　${esc(n.title)}　${extLink(n.url,'詳細')}</article>`).join(''):fallback('news')}
let open=document.querySelector('#zoom-open'),dialog=document.querySelector('#zoom');if(open){open.addEventListener('click',()=>{dialog.querySelector('img').src=open.querySelector('img').src;dialog.querySelector('img').alt=open.querySelector('img').alt;dialog.showModal()})}document.querySelector('#zoom-close').addEventListener('click',()=>dialog.close());

