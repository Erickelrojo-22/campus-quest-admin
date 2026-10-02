import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowDownToLine, Award, Compass, LayoutDashboard, LogOut, MapPin, Menu, Plus, RefreshCw, Settings as SettingsIcon, ShieldCheck, Sparkles, Target, Users as UsersIcon, X } from 'lucide-react';
import { createApiClient, createDemoClient, ApiError } from './services/campus.js';
import { Loading, Modal } from './components/common.jsx';
import Overview from './pages/Overview.jsx';
import Users, { UserProfile } from './pages/Users.jsx';
import Missions, { MissionForm } from './pages/Missions.jsx';
import Points, { PointForm } from './pages/Points.jsx';
import Badges from './pages/Badges.jsx';
import Reports from './pages/Reports.jsx';
import Settings from './pages/Settings.jsx';
import Login from './pages/Login.jsx';
import { initials } from './services/utils.js';

const navigation = [['overview','Resumen',LayoutDashboard],['users','Usuarios',UsersIcon],['missions','Misiones',Target],['points','Puntos del campus',MapPin],['badges','Insignias',Award],['reports','Reportes',ArrowDownToLine]];
const pageInfo={overview:['Cada misión cuenta.','Acompaña a tus estudiantes en su próxima aventura.'],users:['Tu comunidad de exploradores','Cada persona tiene una historia por descubrir.'],missions:['Diseña la próxima aventura','Crea retos que conecten a tus estudiantes con el campus.'],points:['Un campus por descubrir','Gestiona los lugares y códigos QR de tu universidad.'],badges:['Pequeños pasos, grandes logros','Reconocimientos que hacen especial cada descubrimiento.'],reports:['El pulso de tu campus','Conoce la actividad y los logros de tu comunidad.'],settings:['Todo en su lugar','Tu entorno y las herramientas para gestionar el campus.']};
function currentPage() { const value=window.location.hash.slice(1); return Object.hasOwn(pageInfo,value) ? value : 'overview'; }

export default function App() {
  const configuredMode=import.meta.env.VITE_DATA_MODE || 'demo';
  const client=useMemo(() => configuredMode==='api' ? createApiClient(import.meta.env.VITE_API_BASE_URL || '/api/v1') : createDemoClient(),[configuredMode]);
  const [page,setPage]=useState(currentPage); const [menuOpen,setMenuOpen]=useState(false);
  const [session,setSession]=useState(null); const [booting,setBooting]=useState(true);
  const [data,setData]=useState(null); const [loading,setLoading]=useState(false); const [error,setError]=useState('');
  const [dialog,setDialog]=useState(null); const [busy,setBusy]=useState(false); const [toast,setToast]=useState('');
  const generation=useRef(0);
  const sessionGeneration=useRef(0);
  const handleError=useCallback((e) => { setError(e.message || 'No se pudo completar la operación.'); if (e.status===401) { sessionGeneration.current++; generation.current++; setData(null); setSession(null); setDialog(null); } },[]);
  const reload=useCallback(async () => { const id=++generation.current; setLoading(true); setError(''); try { const next=await client.load(); if (id===generation.current) setData(next); } catch(e) { if (id===generation.current) handleError(e); } finally { if (id===generation.current) setLoading(false); } },[client,handleError]);
  useEffect(() => {
    let cancelled=false;
    async function start() {
      try {
        if (!['api','demo'].includes(configuredMode)) throw new ApiError('VITE_DATA_MODE debe ser api o demo.');
        const user=await client.me();
        if (user.rol!=='admin') throw new ApiError('Tu cuenta no tiene permisos para administrar el campus.',403);
        if (!cancelled) { sessionGeneration.current++; setSession(user); await reload(); }
      } catch(e) { if (!cancelled && e.status!==401) setError(e.message); }
      finally { if (!cancelled) setBooting(false); }
    }
    start(); return () => { cancelled=true; generation.current++; };
  },[client,reload,configuredMode]);
  useEffect(() => { const listener=() => { setPage(currentPage()); setMenuOpen(false); }; window.addEventListener('hashchange',listener); return () => window.removeEventListener('hashchange',listener); },[]);
  useEffect(() => { if (!toast) return; const timer=setTimeout(() => setToast(''),4500); return () => clearTimeout(timer); },[toast]);
  useEffect(() => { const listener=e => { if (e.key==='Escape') setMenuOpen(false); }; window.addEventListener('keydown',listener); return () => window.removeEventListener('keydown',listener); },[]);
  const go=(id) => { window.location.hash=id; setPage(id); setMenuOpen(false); };
  async function login(correo,contrasena) { const user=await client.login(correo,contrasena); if (user.rol!=='admin') { await client.logout(); throw new ApiError('Esta cuenta no tiene acceso al panel de administración.',403); } sessionGeneration.current++; setSession(user); setError(''); await reload(); }
  async function logout() { const version=sessionGeneration.current; try { await client.logout(); if (version!==sessionGeneration.current) return; sessionGeneration.current++; generation.current++; setSession(null); setData(null); setDialog(null); setError(''); } catch(e) { if (version===sessionGeneration.current) handleError(e); } }
  async function save(method,item,message) { const version=sessionGeneration.current; try { await client[method](item); } catch(e) { if (version===sessionGeneration.current && e.status===401) handleError(e); throw e; } if (version!==sessionGeneration.current) return; setDialog(current => current===dialog ? null : current); setToast(message); await reload(); }
  async function archive() { const version=sessionGeneration.current; setBusy(true); try { await save('archiveMission',dialog.item.id,'Misión archivada. El historial se conserva.'); } catch(e) { if (version===sessionGeneration.current) handleError(e); } finally { setBusy(false); } }
  async function restore(m) { const version=sessionGeneration.current; setBusy(true); try { await save('saveMission',{...m,activa:true},'Misión reactivada.'); } catch(e) { if (version===sessionGeneration.current) handleError(e); } finally { setBusy(false); } }
  async function reset() { setBusy(true); try { await client.reset(); setDialog(null); await reload(); setToast('Demostración restablecida.'); } finally { setBusy(false); } }
  if (booting) return <main className="boot-screen"><Compass size={35}/><Loading/></main>;
  if (!session) return <Login onLogin={login} error={error}/>;
  const title=navigation.find(([id]) => id===page)?.[1] || 'Configuración';
  const [heading,subtitle]=pageInfo[page];
  return <div className="app-shell">
    <aside className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`}>
      <a className="brand" href="#overview"><span className="brand-mark"><Compass size={25}/></span><div><strong>Campus Quest<span className="brand-dot">.</span></strong><span>El campus, una aventura</span></div></a>
      <button className="close-sidebar icon-button" onClick={() => setMenuOpen(false)} aria-label="Cerrar menú"><X/></button>
      <div className="workspace"><span className="workspace-logo">U</span><div><strong>Campus universitario</strong><small>Panel de administración</small></div></div>
      <p className="nav-label">TU CAMPUS</p>
      <nav aria-label="Navegación principal">{navigation.map(([id,label,Icon]) => <button key={id} onClick={() => go(id)} className={`nav-item ${page===id ? 'active' : ''}`} aria-current={page===id ? 'page' : undefined}><Icon size={19}/><span>{label}</span>{id==='missions' && data && <b>{data.misiones.filter(m => m.activa).length}</b>}</button>)}</nav>
      <p className="nav-label system-label">ADMINISTRACIÓN</p>
      <button onClick={() => go('settings')} className={`nav-item ${page==='settings' ? 'active' : ''}`}><SettingsIcon size={19}/>Configuración</button>
      <div className="sidebar-footer"><div className="demo-card"><Sparkles size={18}/><strong>{client.mode==='demo' ? 'Explora el MVP' : 'Tu campus, conectado'}</strong><p>{client.mode==='demo' ? 'Prueba las herramientas con datos ficticios. Los cambios se reinician al recargar.' : 'Gestiona tus misiones y acompaña los logros de cada explorador.'}</p><span className="demo-tag"><i/>{client.mode==='demo' ? 'Modo demostración' : 'Servidor FastAPI'}</span></div><div className="profile"><span className="avatar">{initials(session.nombres)}</span><div><strong>{session.nombres}</strong><small>Administrador del campus</small></div>{client.mode==='api' ? <button className="icon-button" onClick={logout} aria-label="Cerrar sesión"><LogOut size={17}/></button> : <ShieldCheck size={18}/>}</div></div>
    </aside>
    {menuOpen && <button className="sidebar-backdrop" aria-label="Cerrar menú" onClick={() => setMenuOpen(false)}/>}
    <main className="main-content"><header className="topbar"><div className="flex items-center gap-4"><button className="menu-button icon-button" onClick={() => setMenuOpen(true)} aria-label="Abrir menú"><Menu/></button><span className="breadcrumbs">Campus Quest <span>/</span> <strong>{title}</strong></span></div><div className="flex items-center gap-4"><span className="top-status"><i/>{client.mode==='demo' ? 'Entorno de demostración' : 'API compartida'}</span><button className="icon-button" aria-label="Actualizar datos" disabled={loading} onClick={reload}><RefreshCw size={17} className={loading ? 'spinner' : ''}/></button></div></header>
      <div className="content"><div className="page-heading"><div><p className="eyebrow">{page==='overview' ? 'BIENVENIDO A TU CAMPUS' : 'GESTIÓN DEL CAMPUS'}</p><h1>{heading}</h1><p className="subtitle">{subtitle}</p></div>{data && ['overview','missions','points'].includes(page) && <button className="primary-button" disabled={busy} onClick={() => setDialog({type:page==='points' ? 'point' : 'mission'})}><Plus size={17}/>{page==='points' ? 'Agregar punto' : 'Crear misión'}</button>}</div>
        {error && <div className="error-banner" role="alert"><span>{error}</span><button onClick={reload}>Reintentar</button></div>}
        {!data ? loading ? <Loading/> : <section className="panel"><p className="muted-copy">Los datos del campus no están disponibles. Usa Reintentar para volver a conectar.</p></section> : <>
          {page==='overview' && <Overview data={data} go={go} onUser={user => setDialog({type:'user',item:user})}/>}
          {page==='users' && <Users data={data} onUser={user => setDialog({type:'user',item:user})}/>}
          {page==='missions' && <Missions data={data} busy={busy} onEdit={m => setDialog({type:'mission',item:m})} onArchive={m => setDialog({type:'archive',item:m})} onRestore={restore}/>}
          {page==='points' && <Points data={data} onEdit={p => setDialog({type:'point',item:p})} notify={setToast}/>}
          {page==='badges' && <Badges data={data}/>}
          {page==='reports' && <Reports data={data}/>}
          {page==='settings' && <Settings mode={client.mode} baseUrl={client.baseUrl} onReset={() => setDialog({type:'reset'})} onRefresh={reload}/>}
        </>}
      </div><footer className="main-footer"><span>Campus Quest · Hecho para explorar</span><span>MVP · {new Date().getFullYear()}</span></footer>
    </main>
    {toast && <div className="toast" role="status"><ShieldCheck size={17}/>{toast}<button onClick={() => setToast('')} aria-label="Cerrar mensaje"><X size={15}/></button></div>}
    {dialog?.type==='user' && data && <UserProfile user={data.usuarios.find(u => u.id===dialog.item.id) || dialog.item} data={data} onClose={() => setDialog(null)}/>}
    {dialog?.type==='mission' && data && <MissionForm mission={dialog.item} points={data.puntos} onClose={() => setDialog(null)} onSave={m => save('saveMission',m,'Misión guardada.')}/>}
    {dialog?.type==='point' && <PointForm point={dialog.item} onClose={() => setDialog(null)} onSave={p => save('savePoint',p,'Punto del campus guardado.')}/>}
    {['archive','reset'].includes(dialog?.type) && <Modal title={dialog.type==='archive' ? 'Archivar misión' : 'Restablecer demostración'} onClose={() => setDialog(null)} locked={busy}><p className="confirm-copy">{dialog.type==='archive' ? `«${dialog.item.titulo}» dejará de estar disponible para nuevas completaciones. Los logros, puntos y el historial se conservarán.` : 'Se restaurarán el catálogo, los usuarios y el progreso ficticios. Los cambios de esta sesión de prueba se perderán.'}</p><div className="modal-actions"><button className="secondary-button" disabled={busy} onClick={() => setDialog(null)}>Cancelar</button><button className="primary-button" disabled={busy} onClick={dialog.type==='archive' ? archive : reset}>{busy ? 'Procesando…' : dialog.type==='archive' ? 'Archivar misión' : 'Restablecer'}</button></div></Modal>}
  </div>;
}
