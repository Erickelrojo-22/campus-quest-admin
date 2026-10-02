import { useState } from 'react';
import { Award } from 'lucide-react';
import { Badge, Empty, SearchBox } from '../components/common.jsx';
import { matches } from '../services/utils.js';

export default function Badges({data}) {
  const [search,setSearch]=useState('');
  const filtered=data.misiones.filter(m => matches(`${m.insigniaNombre} ${m.titulo}`,search));
  return <><div className="toolbar"><SearchBox value={search} onChange={setSearch} placeholder="Buscar una insignia"/><span className="muted-copy">Un reconocimiento por cada misión</span></div><div className="badge-grid">{filtered.map(m => { const count=data.progreso.filter(p => p.misionId===m.id).length; return <article className="badge-card" key={m.id}><div className="badge-medallion"><span>{m.insigniaEmoji}</span></div><h2>{m.insigniaNombre}</h2><p>{m.titulo}</p><div className="badge-card-bottom"><span><Award size={14}/>{count} {count===1 ? 'obtenida' : 'obtenidas'}</span><Badge tone={m.activa ? '' : 'neutral'}>{m.activa ? `${m.puntos} XP` : 'Archivada'}</Badge></div></article>; })}</div>{!filtered.length && <section className="panel"><Empty/></section>}<p className="result-count">Las insignias se configuran al crear o editar una misión.</p></>;
}
