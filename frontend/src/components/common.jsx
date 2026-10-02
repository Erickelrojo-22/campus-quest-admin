import { useEffect, useId, useRef } from 'react';
import { Search, X, Inbox, LoaderCircle } from 'lucide-react';

export function Stat({ icon: Icon, label, value, detail }) { return <div className="stat-card"><div className="stat-top"><span>{label}</span><span className="stat-icon"><Icon size={18}/></span></div><strong>{value}</strong><small>{detail}</small></div>; }
export function Empty({title='Sin resultados',text='Prueba con otra búsqueda o cambia los filtros.'}) { return <div className="empty-state"><Inbox size={30}/><h3>{title}</h3><p>{text}</p></div>; }
export function Loading() { return <div className="empty-state" role="status"><LoaderCircle className="spinner" size={28}/><p>Cargando tu campus…</p></div>; }
export function SearchBox({value,onChange,placeholder='Buscar…'}) { return <label className="search-box"><Search size={17}/><input aria-label={placeholder} placeholder={placeholder} value={value} onChange={e => onChange(e.target.value)}/>{value && <button type="button" onClick={() => onChange('')} aria-label="Limpiar búsqueda"><X size={14}/></button>}</label>; }
export function Badge({children,tone=''}) { return <span className={`status-badge ${tone}`}>{children}</span>; }
export function Modal({title,onClose,children,wide=false,locked=false}) {
  const ref=useRef(null); const titleId=useId();
  useEffect(() => { const el=ref.current; const previous=document.activeElement; el.showModal(); return () => { el.close(); previous?.focus(); }; },[]);
  return <dialog ref={ref} className={`modal ${wide ? 'modal-wide' : ''}`} aria-labelledby={titleId} onCancel={e => { e.preventDefault(); if (!locked) onClose(); }} onClick={e => { if (e.target===ref.current && !locked) onClose(); }}><div className="modal-header"><h2 id={titleId}>{title}</h2><button className="icon-button" aria-label="Cerrar" onClick={onClose} disabled={locked}><X size={20}/></button></div>{children}</dialog>;
}
export function Field({label,children,hint}) { return <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>; }
export function FormError({message}) { return message ? <p className="form-error" role="alert">{message}</p> : null; }
