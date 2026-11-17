/* Shared helpers for the VT football pages. No dependencies. */
(function(){
const NS='http://www.w3.org/2000/svg';
const C={vt:'#a8305a',deep:'#6e1535',orange:'#e5751f',teal:'#1790a8',opp:'#3d84c2',ink:'#1b1a17',ink2:'#54524c',muted:'#85827a',grid:'#e3e0d6',axis:'#c4c0b4',card:'#fbfaf6',
  win:['#ecc9d4','#d48aa3','#a8305a','#6e1535'],loss:['#c9dcee','#8bb4da','#3d84c2','#1d4f85'],tie:'#d6d2c6'};
const s=(tag,attrs,parent,text)=>{const e=document.createElementNS(NS,tag);for(const k in attrs)e.setAttribute(k,attrs[k]);if(text!=null)e.textContent=text;if(parent)parent.appendChild(e);return e};
const h=(tag,attrs,parent,text)=>{const e=document.createElement(tag);for(const k in (attrs||{}))e.setAttribute(k,attrs[k]);if(text!=null)e.textContent=text;if(parent)parent.appendChild(e);return e};
const lin=(d0,d1,r0,r1)=>v=>r0+(v-d0)/(d1-d0||1)*(r1-r0);
function ticks(a,b,n){const span=b-a,step0=Math.pow(10,Math.floor(Math.log10(span/n))),err=span/n/step0;
  const step=step0*(err>=7.5?10:err>=3.5?5:err>=1.5?2:1),out=[];for(let v=Math.ceil(a/step)*step;v<=b+1e-9;v+=step)out.push(+v.toFixed(6));return out}
/* tooltip: rows = [[label,value,color?],...] built with textContent only */
let tipEl;
function tip(x,y,head,rows){
  if(!tipEl){tipEl=h('div',{id:'tip'},document.body)}
  tipEl.replaceChildren();if(head)h('span',{class:'h'},tipEl,head);
  for(const r of rows||[]){const d=h('div',{},tipEl);if(r[2]){const k=h('i',{class:'k'},d);k.style.background=r[2]}h('b',{},d,r[1]);d.appendChild(document.createTextNode(' '+r[0]))}
  tipEl.style.display='block';const w=tipEl.offsetWidth,ht=tipEl.offsetHeight;
  tipEl.style.left=Math.max(6,Math.min(window.innerWidth-w-6,x-w/2))+'px';
  tipEl.style.top=(y-ht-14<6?y+18:y-ht-14)+'px'}
function hideTip(){if(tipEl)tipEl.style.display='none'}
document.addEventListener('scroll',hideTip,{passive:true});
function margeColor(m){if(m===0)return C.tie;const a=Math.abs(m),i=a<=7?0:a<=16?1:a<=27?2:3;return(m>0?C.win:C.loss)[i]}
function marginLegend(el){const L=h('div',{class:'legend'},el);
  [['Lost by 28+',C.loss[3]],['17-27',C.loss[2]],['8-16',C.loss[1]],['1-7',C.loss[0]],['Tie',C.tie],['Won by 1-7',C.win[0]],['8-16',C.win[1]],['17-27',C.win[2]],['28+',C.win[3]]]
  .forEach(([t,c])=>{const sp=h('span',{},L);h('i',{},sp).style.background=c;sp.appendChild(document.createTextNode(t))})}
function legend(el,items){const L=h('div',{class:'legend'},el);items.forEach(([t,c,kind])=>{const sp=h('span',{},L);const i=h('i',{class:kind||''},sp);i.style.background=c;sp.appendChild(document.createTextNode(t))});return L}
const ERAS=[['Beamer',1987,2015],['Fuente',2016,2021],['Pry',2022,2025],['Franklin',2026,2026]];
/* frame: svg with margins, y grid, returns helpers */
function frame(el,o){
  el.replaceChildren();const W=Math.max(300,el.clientWidth||340),H=o.h||230,m=Object.assign({t:22,r:14,b:24,l:34},o.m||{});
  const svg=s('svg',{viewBox:`0 0 ${W} ${H}`,width:W,height:H,role:'img','aria-label':o.label||''},el);
  const y=lin(o.y0,o.y1,o.invert?m.t:H-m.b,o.invert?H-m.b:m.t);
  (o.yTicks||ticks(Math.min(o.y0,o.y1),Math.max(o.y0,o.y1),4)).forEach(v=>{
    s('line',{x1:m.l,x2:W-m.r,y1:y(v),y2:y(v),stroke:v===0&&o.zero?C.axis:C.grid,'stroke-width':1},svg);
    s('text',{x:m.l-6,y:y(v)+4,'text-anchor':'end'},svg,(o.yFmt||String)(v))});
  return{svg,W,H,m,y}}
/* season x-axis shared by line/bar charts: seasons array of ints */
function seasonAxis(f,seasons,o){
  const {svg,W,H,m}=f,n=seasons.length,bw=(W-m.l-m.r)/n,x=i=>m.l+bw*(i+.5);
  seasons.forEach((yr,i)=>{if(yr%5===0)s('text',{x:x(i),y:H-m.b+15,'text-anchor':'middle'},svg,"'"+String(yr).slice(2))});
  if(!o||o.eras!==false)ERAS.forEach(([nm,a,b])=>{const i0=seasons.indexOf(a),i1=seasons.indexOf(b);if(i0<0)return;
    if(i0>0)s('line',{x1:m.l+bw*i0,x2:m.l+bw*i0,y1:m.t-6,y2:H-m.b,stroke:C.axis,'stroke-width':1},svg);
    if(bw*(i1-i0+1)>44)s('text',{x:m.l+bw*i0+4,y:m.t-10,class:'era'},svg,nm)});
  return{x,bw}}
/* crosshair hit layer snapping to season index */
function hit(f,ax,n,cb){
  const {svg,W,H,m}=f,cross=s('line',{y1:m.t-6,y2:H-m.b,stroke:C.ink2,'stroke-width':1,visibility:'hidden'},svg);
  const r=s('rect',{x:m.l,y:0,width:W-m.l-m.r,height:H,fill:'transparent',tabindex:0},svg);
  const move=e=>{const b=svg.getBoundingClientRect(),px=(e.clientX-b.left)*(W/b.width),i=Math.max(0,Math.min(n-1,Math.floor((px-m.l)/ax.bw)));
    cross.setAttribute('x1',ax.x(i));cross.setAttribute('x2',ax.x(i));cross.setAttribute('visibility','visible');
    const t=cb(i);tip(b.left+ax.x(i)*(b.width/W),b.top+m.t*(b.height/H),t[0],t[1])};
  r.addEventListener('pointermove',move);r.addEventListener('pointerdown',move);
  r.addEventListener('pointerleave',()=>{cross.setAttribute('visibility','hidden');hideTip()})}
/* line chart by season. series:[{name,color,values,dash?,dots?}] */
function lines(el,o){
  const all=o.series.flatMap(z=>z.values).filter(v=>v!=null);
  let y0=o.y0!=null?o.y0:Math.min(...all),y1=o.y1!=null?o.y1:Math.max(...all);
  if(o.y0==null&&o.y1==null){const p=(y1-y0)*.08;y0-=p;y1+=p}
  const f=frame(el,Object.assign({},o,{y0,y1})),ax=seasonAxis(f,o.seasons,o);
  if(o.band){const [a,b]=o.band;let d='';a.values.forEach((v,i)=>{if(v!=null&&b.values[i]!=null)d+=(d?'L':'M')+ax.x(i)+','+f.y(v)});
    for(let i=b.values.length-1;i>=0;i--)if(a.values[i]!=null&&b.values[i]!=null)d+='L'+ax.x(i)+','+f.y(b.values[i]);
    s('path',{d:d+'Z',fill:o.bandColor||C.vt,opacity:.1},f.svg)}
  o.series.forEach(z=>{let d='',pen=false;z.values.forEach((v,i)=>{if(v==null){pen=false;return}d+=(pen?'L':'M')+ax.x(i).toFixed(1)+','+f.y(v).toFixed(1);pen=true});
    if(!z.dotsOnly)s('path',{d,fill:'none',stroke:z.color,'stroke-width':z.thin?1.5:2.2,'stroke-linejoin':'round','stroke-linecap':'round'},f.svg);
    if(z.dots||z.dotsOnly)z.values.forEach((v,i)=>{if(v!=null)s('circle',{cx:ax.x(i),cy:f.y(v),r:z.dotsOnly?4:2.6,fill:z.color,stroke:C.card,'stroke-width':1.5},f.svg)})});
  (o.marks||[]).forEach(mk=>{const i=o.seasons.indexOf(mk.s);if(i<0)return;const v=o.series[mk.series||0].values[i];if(v==null)return;
    const yy=f.y(v)+(mk.below?16:-9),xx=ax.x(i),anc=xx>f.W-70?'end':xx<70?'start':'middle';
    s('text',{x:xx,y:yy,'text-anchor':anc,class:'lab'},f.svg,mk.t)});
  hit(f,ax,o.seasons.length,i=>[o.head?o.head(i):String(o.seasons[i]),o.series.filter(z=>z.values[i]!=null).map(z=>[z.name,(o.fmt||String)(z.values[i]),z.color])]);
  return f}
/* vertical bars by season; stacks:[{name,color,values}] drawn up from 0; down:[...] drawn below 0 */
function bars(el,o){
  const up=o.seasons.map((_,i)=>o.stacks.reduce((a,z)=>a+(z.values[i]||0),0)),dn=o.seasons.map((_,i)=>(o.down||[]).reduce((a,z)=>a+(z.values[i]||0),0));
  const y1=o.y1!=null?o.y1:Math.max(...up)*1.08,y0=o.down?-Math.max(...dn)*1.08:0;
  const f=frame(el,Object.assign({zero:true},o,{y0,y1})),ax=seasonAxis(f,o.seasons,o),bw=Math.max(2,ax.bw-2);
  o.seasons.forEach((yr,i)=>{let acc=0;o.stacks.forEach(z=>{const v=z.values[i]||0;if(!v)return;const ya=f.y(acc),yb=f.y(acc+v);
      s('rect',{x:ax.x(i)-bw/2,y:yb+(acc?1:0),width:bw,height:Math.max(0,ya-yb-(acc?1:0)),fill:z.color,rx:1.5},f.svg);acc+=v});
    acc=0;(o.down||[]).forEach(z=>{const v=z.values[i]||0;if(!v)return;const ya=f.y(-acc),yb=f.y(-acc-v);
      s('rect',{x:ax.x(i)-bw/2,y:ya+1,width:bw,height:Math.max(0,yb-ya-1),fill:z.color,rx:1.5},f.svg);acc+=v})});
  (o.overlay||[]).forEach(z=>{let d='',pen=false;z.values.forEach((v,i)=>{if(v==null){pen=false;return}d+=(pen?'L':'M')+ax.x(i)+','+f.y(v);pen=true});
    s('path',{d,fill:'none',stroke:z.color,'stroke-width':2},f.svg)});
  const all=o.stacks.concat(o.down||[],o.overlay||[]);
  hit(f,ax,o.seasons.length,i=>[o.head?o.head(i):String(o.seasons[i]),all.filter(z=>z.values[i]!=null).map(z=>[z.name,(o.fmt||String)(z.values[i]),z.color])]);
  return f}
function table(el,cols,rows,label){
  const d=h('details',{class:'tbl'},el);h('summary',{},d,label||'Show as table');const sc=h('div',{class:'tscroll'},d),t=h('table',{},sc),tr=h('tr',{},h('thead',{},t));
  cols.forEach(c=>h('th',{},tr,c));const tb=h('tbody',{},t);rows.forEach(r=>{const x=h('tr',{},tb);r.forEach(v=>h('td',{},x,v==null?'':String(v)))})}
function nav(active){
  const pages=[['index.html','Every game'],['viz/arc.html','The arc'],['viz/units.html','Offense & defense'],['viz/games.html','Game explorer'],['viz/situations.html','Down & distance'],['viz/opponents.html','Opponents'],['viz/gameday.html','Game day']];
  const root=document.body.dataset.root||'',n=h('nav',{class:'top'});
  pages.forEach(([p,t])=>{const a=h('a',{href:root+p},n,t);if(p===active)a.className='on'});
  document.querySelector('.wrap').prepend(n);const on=n.querySelector('.on');if(on)n.scrollLeft=Math.max(0,on.offsetLeft-60)}
async function load(){const root=document.body.dataset.root||'';const r=await fetch(root+'viz/data/site.json');return r.json()}
function onResize(fn){let w=window.innerWidth,t;window.addEventListener('resize',()=>{if(window.innerWidth===w)return;w=window.innerWidth;clearTimeout(t);t=setTimeout(fn,150)})}
const fmtDate=d=>{const [y,m,dd]=d.split('-');return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m-1]+' '+(+dd)+', '+y};
const gameLine=g=>(g.site==='H'?'vs ':g.site==='A'?'at ':'vs ')+(g.orr?'#'+g.orr+' ':'')+g.o;
const result=g=>(g.vp>g.op?'W ':g.vp<g.op?'L ':'T ')+g.vp+'-'+g.op;
window.VT={C,s,h,lin,ticks,tip,hideTip,margeColor,marginLegend,legend,frame,seasonAxis,hit,lines,bars,table,nav,load,onResize,fmtDate,gameLine,result,ERAS};
})();
