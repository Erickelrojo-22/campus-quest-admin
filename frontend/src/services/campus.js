import { createDemoData } from '../data/demo.js';

export class ApiError extends Error {
  constructor(message,status=0) { super(message); this.name='ApiError'; this.status=status; }
}

export function createApiClient(baseUrl='/api/v1',fetcher=globalThis.fetch) {
  const base = baseUrl.replace(/\/$/,'');
  async function request(path,options={}) {
    let response;
    try { response = await fetcher(`${base}${path}`,{ credentials:'include', ...options, headers:{ Accept:'application/json', ...(options.body ? {'Content-Type':'application/json'} : {}), ...options.headers } }); }
    catch { throw new ApiError('No se pudo contactar al servidor. Revisa la conexión e inténtalo de nuevo.'); }
    if (response.status===204) return null;
    let body;
    try { body=await response.json(); }
    catch { throw new ApiError('El servidor no devolvió JSON. Revisa la dirección de la API.',response.status); }
    if (!response.ok) {
      const detail=body.detail;
      const message=Array.isArray(detail) ? detail.map(d => `${d.loc?.slice(1).join('.') || 'Campo'}: ${d.msg}`).join(' · ') : typeof detail==='string' ? detail : 'No se pudo completar la operación.';
      throw new ApiError(message,response.status);
    }
    return body;
  }
  return {
    mode:'api', baseUrl:base,
    me:() => request('/auth/me'),
    login:(correo,contrasena) => request('/auth/login',{method:'POST',body:JSON.stringify({correo,contrasena})}).then(r => r.usuario),
    logout:() => request('/auth/logout',{method:'POST'}),
    async load() {
      const [usuarios,puntos,misiones,progreso] = await Promise.all([request('/usuarios'),request('/puntos'),request('/misiones?incluirArchivadas=true'),request('/progreso')]);
      if (![usuarios,puntos,misiones,progreso].every(Array.isArray)) throw new ApiError('El formato de datos del servidor no corresponde al contrato de Campus Quest.');
      return { usuarios,puntos,misiones,progreso };
    },
    saveMission:(m) => { const {id,...body}=m; return request(`/misiones${id ? `/${id}` : ''}`,{method:id ? 'PUT' : 'POST',body:JSON.stringify(body)}); },
    archiveMission:(id) => request(`/misiones/${id}`,{method:'DELETE'}),
    savePoint:(p) => { const {id,...body}=p; return request(`/puntos${id ? `/${id}` : ''}`,{method:id ? 'PUT' : 'POST',body:JSON.stringify(body)}); },
  };
}

export function createDemoClient() {
  let data=createDemoData();
  const clone=(v) => structuredClone(v);
  return {
    mode:'demo', baseUrl:'',
    me:async () => ({id:0,nombres:'Administrador',rol:'admin'}),
    load:async () => clone(data),
    async saveMission(m) {
      if (!data.puntos.some(p => p.id===m.puntoInteresId)) throw new ApiError('Selecciona un punto existente.',422);
      const old=data.misiones.find(x => x.id===m.id);
      if (old && old.puntoInteresId!==m.puntoInteresId && data.progreso.some(p => p.misionId===m.id)) throw new ApiError('La misión tiene progreso registrado. Conserva su punto de interés.',409);
      const next={...m,id:m.id || Math.max(0,...data.misiones.map(x => x.id))+1};
      data.misiones=m.id ? data.misiones.map(x => x.id===m.id ? next : x) : [...data.misiones,next];
      return clone(next);
    },
    async archiveMission(id) { data.misiones=data.misiones.map(m => m.id===id ? {...m,activa:false} : m); },
    async savePoint(p) {
      const next={...p,codigoQr:p.codigoQr.trim().toUpperCase(),id:p.id || Math.max(0,...data.puntos.map(x => x.id))+1};
      if (data.puntos.some(x => x.id!==p.id && x.codigoQr===next.codigoQr)) throw new ApiError('Este código QR ya pertenece a otro punto.',409);
      data.puntos=p.id ? data.puntos.map(x => x.id===p.id ? next : x) : [...data.puntos,next];
      return clone(next);
    },
    async reset() { data=createDemoData(); },
  };
}
