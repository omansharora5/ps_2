import React, { useEffect, useRef, useState } from 'react';
import { ArrowRight, ArrowUpRight, ChevronLeft, ChevronRight, Compass, Globe2, MapPin, Pause, Play, RotateCcw, Search } from 'lucide-react';
import locations from '../shared/locations.json';
import { createEarthScene } from './earth-scene';
import './exploration.css';

export default function EarthExplorer() {
  const host = useRef(null);
  const scene = useRef(null);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(null);
  const [paused, setPaused] = useState(false);
  const [fallback, setFallback] = useState('');
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const matches = locations.filter(place => [place.name, place.state, ...(place.aliases || [])].some(value => value.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())));
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const change = event => setReduced(event.matches);
    media.addEventListener('change', change);
    return () => media.removeEventListener('change', change);
  }, []);
  useEffect(() => {
    if (fallback) return;
    try { scene.current = createEarthScene(host.current, { onFailure: setFallback }); }
    catch { setFallback('3D is unavailable on this device. Place search and coordinates still work.'); }
    return () => { scene.current?.dispose(); scene.current = null; };
  }, [fallback]);
  useEffect(() => { scene.current?.pause(paused); }, [paused]);
  const choose = place => { setSelected(place); setQuery(''); scene.current?.focus(place); };
  return <div className="earth-page">
    <section className="earth-hero" aria-label="Interactive Earth location explorer" onFocusCapture={() => scene.current?.interaction(true)} onBlurCapture={event => { if (!event.currentTarget.contains(event.relatedTarget)) scene.current?.interaction(false); }}>
      <div className="earth-topline"><span><span className="orbital-dot" /> EARTH EXPLORER</span><span>GEOGRAPHY / NOT LIVE WEATHER</span></div>
      <div className="earth-layout">
        <div className="earth-copy"><p className="earth-kicker">A wider view. A local focus.</p><h2>Start with<br />a place.</h2><p className="earth-intro">Explore the Earth, find a city, then follow the evidence behind a forecast.</p>
          <form className="place-search" onSubmit={event => { event.preventDefault(); if (matches.length && query.trim()) choose(matches[0]); }}>
            <label htmlFor="earth-place">Find a supported Indian city</label><div className="search-field"><Search size={19} aria-hidden="true" /><input id="earth-place" type="search" placeholder="Try Patna, Mumbai, Chennai…" value={query} onChange={event => setQuery(event.target.value)} autoComplete="off" aria-describedby="gazetteer-note" /><button type="submit" aria-label="Go to first matching city" disabled={!query.trim() || !matches.length}><ArrowRight size={19} aria-hidden="true" /></button></div>
            <p id="gazetteer-note">{locations.length} places · bundled coordinates · works without geocoding</p>
          </form>
          {query.trim() && <div className="place-results" aria-label="Matching cities">{matches.slice(0, 6).map(place => <button key={place.id} onClick={() => choose(place)}><MapPin size={16} aria-hidden="true" /><span><strong>{place.name}</strong><small>{place.state}</small></span><ArrowUpRight size={16} aria-hidden="true" /></button>)}{!matches.length && <p role="status">No city in the bundled gazetteer matches “{query}”. Try Patna, Mumbai or Chennai.</p>}</div>}
          {!query.trim() && <div className="city-shortcuts" aria-label="Quick city selection">{['patna', 'mumbai', 'chennai'].map(id => locations.find(place => place.id === id)).filter(Boolean).map(place => <button key={place.id} onClick={() => choose(place)}>{place.name}<ArrowUpRight size={13} aria-hidden="true" /></button>)}</div>}
          <div className="earth-selection" aria-live="polite"><span className="earth-selection-label"><MapPin size={15} aria-hidden="true" />{selected ? 'SELECTED PLACE' : 'YOUR POINT OF VIEW'}</span><h3>{selected ? selected.name : 'The Indian subcontinent'}</h3><p>{selected ? `${selected.state}, India` : 'Choose a city to bring it into focus.'}</p>{selected && <div className="coordinate-pair"><span><small>LATITUDE</small>{selected.lat.toFixed(4)}° N</span><span><small>LONGITUDE</small>{selected.lon.toFixed(4)}° E</span></div>}<p className="location-limitation">{selected ? 'Approximate city centre. Selecting this place does not load a local forecast.' : 'A geographic view with a static satellite composite.'}</p>{selected && <a className="coordinate-source" href={selected.source_url} target="_blank" rel="noreferrer">Coordinate source<ArrowUpRight size={13} aria-hidden="true" /></a>}</div>
        </div>
        <div className="earth-stage"><div className="orbital-label"><Compass size={15} aria-hidden="true" /><span>{selected ? `FOCUS / ${selected.name.toUpperCase()}` : 'ORBITAL VIEW / INDIA'}</span></div>
          {fallback ? <div className="earth-fallback" data-testid="earth-fallback"><div className="flat-earth"><img src="/earth/blue-marble.jpg" alt="Static NASA Blue Marble world map" width="2048" height="1024" />{selected && <span className="flat-pin" style={{ left: `${(selected.lon + 180) / 360 * 100}%`, top: `${(90 - selected.lat) / 180 * 100}%` }}><MapPin size={20} aria-hidden="true" /></span>}</div><p>{fallback}</p></div> : <div ref={host} className="earth-canvas" data-testid="earth-scene" />}
          <div className="earth-controls"><button aria-label="Rotate Earth west" onClick={() => { setSelected(null); scene.current?.rotate(-1); }} disabled={Boolean(fallback)}><ChevronLeft size={19} aria-hidden="true" /></button><button onClick={() => setPaused(!paused)} disabled={Boolean(fallback) || reduced} aria-pressed={paused || reduced}>{paused || reduced ? <Play size={16} aria-hidden="true" /> : <Pause size={16} aria-hidden="true" />}{reduced ? 'Reduced motion' : paused ? 'Resume motion' : 'Pause motion'}</button><button aria-label="Rotate Earth east" onClick={() => { setSelected(null); scene.current?.rotate(1); }} disabled={Boolean(fallback)}><ChevronRight size={19} aria-hidden="true" /></button><button aria-label="Reset orbital view" onClick={() => { setSelected(null); setQuery(''); scene.current?.focus(null); }}><RotateCcw size={17} aria-hidden="true" /></button></div>
          <p className="earth-caption">NASA Blue Marble static imagery · Clouds are an animated illustration, not observations.</p>
        </div>
      </div>
      <div className="earth-bottomline"><span><Globe2 size={15} aria-hidden="true" /> Geographical context, with traceable sources.</span><a href="/earth/PROVENANCE.md" target="_blank" rel="noreferrer">Image credits<ArrowUpRight size={14} aria-hidden="true" /></a></div>
    </section>
    <div className="earth-next"><a href="#/image-lab"><span className="step-label">01 / OBSERVE</span><h3>Work with real radar images<ArrowUpRight size={21} aria-hidden="true" /></h3><p>Compare cleaning, segmentation and motion against the measured outcome.</p></a><a href="#/sources"><span className="step-label">02 / TRACE</span><h3>Explore the data collection<ArrowUpRight size={21} aria-hidden="true" /></h3><p>Inspect source files, provenance and what is still needed for training.</p></a></div>
  </div>;
}
