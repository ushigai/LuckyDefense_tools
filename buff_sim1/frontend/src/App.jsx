import React, { useEffect, useMemo, useRef, useState } from "react";

const FPS = 40;
const DURATION_SEC = 300;

function clamp(n, a, b) { return Math.max(a, Math.min(b, n)); }
function fmt(n, d=2){ return Number.isFinite(n) ? n.toFixed(d) : "-"; }
function pct(n){ return `${fmt(n*100,1)}%`; }
function uid(){ return Math.random().toString(16).slice(2) + Date.now().toString(16); }
function formatTimeMMSS(sec){
  const s = Math.max(0, Math.floor(sec));
  const mm = Math.floor(s/60);
  const ss = s%60;
  return `${mm}:${String(ss).padStart(2,"0")}`;
}
function sumSegments(segs){ return (segs||[]).reduce((a,s)=>a+Math.max(0,(s.end-s.start)),0); }
function isActiveAt(segs,t){
  for(const s of (segs||[])){
    if(t < s.start) return false;
    if(t>=s.start && t<s.end) return true;
  }
  return false;
}
function normalize(raw){
  const out = { ...raw };
  out.durationSec = Number(out.durationSec ?? DURATION_SEC);
  out.fps = Number(out.fps ?? FPS);
  out.buffs = out.buffs || {};
  out.buffs.tiger = Array.isArray(out.buffs.tiger) ? out.buffs.tiger : [];
  out.buffs.penguin = Array.isArray(out.buffs.penguin) ? out.buffs.penguin : [];
  out.events = Array.isArray(out.events) ? out.events.map(e => ({ id: uid(), ...e })) : [];
  out.series = Array.isArray(out.series) ? out.series : [];
  return out;
}
async function simulateViaApi(payload){
  const res = await fetch("api/simulate", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload) });
  if(!res.ok){
    const text = await res.text().catch(()=> "");
    throw new Error(`API error ${res.status}: ${text || res.statusText}`);
  }
  return normalize(await res.json());
}
function SegmentsRow({title, subtitle, segments, durationSec, kind, onBarMove, onBarLeave}){
  return (
    <div className="lineItem">
      <div>
        <div className="lineTitle">{title}</div>
        {subtitle ? <div className="lineSub">{subtitle}</div> : null}
      </div>
      <div className="bar" onMouseMove={onBarMove} onMouseLeave={onBarLeave}>
        {segments.map((s)=> {
          const left = (s.start/durationSec)*100;
          const width = ((s.end-s.start)/durationSec)*100;
          return <div key={`${s.start}-${s.end}`} className={`seg ${kind}`} style={{left:`${left}%`, width:`${width}%`}} title={`${fmt(s.start,3)}s→${fmt(s.end,3)}s`} />;
        })}
        {Array.from({length:11}).map((_,i)=>(
          <div key={i} className="tick" style={{left:`${(i/10)*100}%`}} />
        ))}
      </div>
    </div>
  );
}
function EventRow({events, durationSec, onBarMove, onBarLeave}){
  return (
    <div className="lineItem">
      <div>
        <div className="lineTitle">発動イベント</div>
      </div>
      <div className="bar" onMouseMove={onBarMove} onMouseLeave={onBarLeave}>
        {events.map((e)=> {
          const left = (e.t/durationSec)*100;
          return <div key={e.id} className={`eventMark ${e.type}`} style={{left:`${left}%`}} title={`F${e.frame} ${fmt(e.t,3)}s: ${e.label}`} />;
        })}
        {Array.from({length:11}).map((_,i)=>(
          <div key={i} className="tick" style={{left:`${(i/10)*100}%`, opacity:0.35}} />
        ))}
      </div>
    </div>
  );
}
export default function App(){
  const [seed, setSeed] = useState(123456);
  const [refreshMode, setRefreshMode] = useState("refresh");
  const [emitBasicEvents, setEmitBasicEvents] = useState(false);
  const [attackerAS, setAttackerAS] = useState(1.0);
  const [tigerCount, setTigerCount] = useState(1);
  const [penguinCount, setPenguinCount] = useState(1);

  const [result, setResult] = useState(()=> normalize({buffs:{tiger:[],penguin:[]},events:[],series:[]}));
  const [lastPayload, setLastPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);
  const [hover, setHover] = useState(null);

  const eventsByFrame = useMemo(()=> {
    const m = new Map();
    for(const e of result.events){
      if(!m.has(e.frame)) m.set(e.frame, []);
      m.get(e.frame).push(e);
    }
    return m;
  }, [result]);

  const hoverEvents = hover ? (eventsByFrame.get(hover.frame) || []) : [];
  const hoverActive = useMemo(()=> {
    if(!hover) return {tiger:false, penguin:false};
    return { tiger: isActiveAt(result.buffs.tiger, hover.t), penguin: isActiveAt(result.buffs.penguin, hover.t) };
  }, [hover, result]);

  const tigerUptime = useMemo(()=> clamp(sumSegments(result.buffs.tiger)/result.durationSec, 0, 1), [result]);
  const penguinUptime = useMemo(()=> clamp(sumSegments(result.buffs.penguin)/result.durationSec, 0, 1), [result]);
  const eventsForRow = useMemo(()=> result.events.filter(e => ["tiger","penguin","penguin_nothing"].includes(e.type)), [result]);

  const run = async ()=> {
    setLoading(true); setErr(null);
    const payload = {
      seed: Number(seed),
      refreshMode,
      attacker: { attackSpeed: Number(attackerAS) },
      buffers: { tigerCount: Number(tigerCount), penguinCount: Number(penguinCount) },
      emitBasicEvents: !!emitBasicEvents,
    };
    try{
      const r = await simulateViaApi(payload);
      setResult(r);
      setLastPayload(payload);
    }catch(e){
      setErr(String(e?.message || e));
    }finally{
      setLoading(false);
    }
  };

  useEffect(()=> { run(); /* eslint-disable-next-line */ }, []);

  const onBarMove = (ev)=> {
    const r = ev.currentTarget.getBoundingClientRect();
    const x = clamp(ev.clientX - r.left, 0, r.width);
    const p = r.width <= 0 ? 0 : x / r.width;

    // result.durationSec / result.fps に追従（将来的に変更があってもズレないように）
    const dur = Number(result.durationSec ?? DURATION_SEC);
    const fps = Number(result.fps ?? FPS);
    const maxFrame = Math.max(1, Math.floor(dur * fps)) - 1;
    const frame = clamp(Math.floor(p * dur * fps), 0, maxFrame);

    setHover({ frame, t: frame / fps, xPct: p * 100 });
  };

  const onBarLeave = ()=> setHover(null);

  return (
    <div className="container">
      <div className="h1">バフタイムライン</div>
      <div className="sub">左：アタッカー情報 / 右：ホバー情報 / 下：タイムライン</div>

      <div className="grid" style={{marginTop:16}}>
        <div className="card">
          <div className="sideTitle">アタッカー情報</div>

          <div className="controlsGrid">
            <div className="field">
              <div className="lab">seed</div>
              <input type="number" value={seed} onChange={(e)=>setSeed(Number(e.target.value))} />
            </div>

            <div className="field">
              <div className="lab">同一個体の同一バフ</div>
              <select value={refreshMode} onChange={(e)=>setRefreshMode(e.target.value)}>
                <option value="refresh">refresh（残り時間リセット）</option>
                <option value="extend">extend（延長）</option>
              </select>
            </div>

            <div className="field">
              <div className="lab">アタッカー基本攻撃速度</div>
              <input type="number" step="0.1" min="0.1" value={attackerAS} onChange={(e)=>setAttackerAS(Number(e.target.value))} />
            </div>

            <div className="field">
              <div className="lab">虎の師父</div>
              <input type="number" min="0" max="20" value={tigerCount} onChange={(e)=>setTigerCount(Number(e.target.value))} />
            </div>

            <div className="field">
              <div className="lab">ペンギン楽師</div>
              <input type="number" min="0" max="20" value={penguinCount} onChange={(e)=>setPenguinCount(Number(e.target.value))} />
            </div>
          </div>

          <div className="btnRow">
            <button className="btn primary" onClick={run} disabled={loading}>{loading ? "実行中…" : "シミュレーション実行"}</button>
            <button className="btn" onClick={()=>setSeed(Math.floor(Math.random()*2**31))}>seedランダム</button>
          </div>

          <div className="pills" style={{marginTop:10}}>
            <div className="pill"><div className="k">虎 uptime</div><div className="v">{pct(tigerUptime)}</div></div>
            <div className="pill"><div className="k">ペンギン uptime</div><div className="v">{pct(penguinUptime)}</div></div>
            <div className="pill"><div className="k">events</div><div className="v">{String(result.events.length)}</div></div>
          </div>

          <div className="inline">
            <input type="checkbox" checked={emitBasicEvents} onChange={(e)=>setEmitBasicEvents(e.target.checked)} />
            <div>基本攻撃イベントも返す</div>
          </div>
        </div>

        <div className="card sideCard">
          <div className="sideTitle">ホバー情報</div>
          {!hover ? (
            <div className="sideHint">タイムライン上をオンマウスで表示</div>
          ) : (
            <>
              <div className="kv"><div className="k">時刻</div><div className="v">{formatTimeMMSS(hover.t)} ({fmt(hover.t,3)}s)</div></div>
              <div className="kv"><div className="k">フレーム</div><div className="v">F{hover.frame}</div></div>

              <div className="badges">
                <div className="badge"><div className="k">虎バフ</div><div className="v">{hoverActive.tiger ? "ON" : "OFF"}</div></div>
                <div className="badge"><div className="k">ペンギンバフ</div><div className="v">{hoverActive.penguin ? "ON" : "OFF"}</div></div>
              </div>

              <div className="list">
                <div className="k" style={{fontSize:12, color:"var(--muted)", fontWeight:800}}>このフレームのイベント</div>
                {hoverEvents.length === 0 ? (
                  <div className="small" style={{marginTop:6}}>なし</div>
                ) : (
                  <div style={{marginTop:6}}>
                    {hoverEvents.slice(0,10).map(e => <div key={e.id} className="li">• {e.label}</div>)}
                    {hoverEvents.length > 10 ? <div className="small">…（{hoverEvents.length}件）</div> : null}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {err ? <div className="alert" style={{marginTop:12}}><b>APIエラー</b>\n{err}</div> : null}

      <div className="row" style={{marginTop:12}}>
        <div className="lineTitle">タイムライン</div>
        <div className="small">全{formatTimeMMSS(result.durationSec)}（{fmt(result.durationSec,0)}s）</div>
      </div>

      <div className="timelineWrap">
        <div className="hoverZone">{hover ? <div className="hoverLine" style={{left:`${hover.xPct}%`}} /> : null}</div>

        <div className="timelineRows">
          <SegmentsRow
            title="虎の師父"
            subtitle={null}
            segments={result.buffs.tiger}
            durationSec={result.durationSec}
            kind="tiger"
            onBarMove={onBarMove}
            onBarLeave={onBarLeave}
          />
          <SegmentsRow
            title="ペンギン楽師"
            subtitle={null}
            segments={result.buffs.penguin}
            durationSec={result.durationSec}
            kind="penguin"
            onBarMove={onBarMove}
            onBarLeave={onBarLeave}
          />
          <EventRow events={eventsForRow} durationSec={result.durationSec} onBarMove={onBarMove} onBarLeave={onBarLeave} />
        </div>
      </div>

      <div className="card" style={{marginTop:14}}>
        <details>
          <summary className="lineTitle">リクエスト（デバッグ）</summary>
          <pre style={{marginTop:8, padding:10, borderRadius:14, border:"1px solid var(--border)", background:"var(--soft)", overflow:"auto", fontSize:12, lineHeight:1.5}}>
{JSON.stringify(lastPayload || {
  seed: Number(seed),
  refreshMode,
  attacker: { attackSpeed: Number(attackerAS) },
  buffers: { tigerCount: Number(tigerCount), penguinCount: Number(penguinCount) },
  emitBasicEvents: !!emitBasicEvents,
}, null, 2)}
          </pre>
        </details>
      </div>

    </div>
  );
}
