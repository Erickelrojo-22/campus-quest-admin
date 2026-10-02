export const initials=(name) => name.trim().split(/\s+/).slice(0,2).map(n => n[0]).join('').toUpperCase();
export const formatDate=(ms) => new Intl.DateTimeFormat('es-EC',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}).format(ms);
export const byPoints=(a,b) => b.puntajeAcumulado-a.puntajeAcumulado || a.nombres.localeCompare(b.nombres);
export const normalize=(text) => String(text ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
export const matches=(text,search) => normalize(text).includes(normalize(search));
export function csvCell(value) { let s=String(value ?? ''); if (/^[=+@\-\t\r]/.test(s)) s=`'${s}`; return `"${s.replace(/"/g,'""')}"`; }
export function downloadCsv(filename,headers,rows) {
  const blob=new Blob(['\uFEFF'+[headers,...rows].map(row => row.map(csvCell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8;'});
  const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=filename; a.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
}
export function filterPeriod(progreso,days,now=Date.now()) { const cutoff=days ? now-days*86400000 : -Infinity; return progreso.filter(p => p.fechaHora>=cutoff && p.fechaHora<=now); }
