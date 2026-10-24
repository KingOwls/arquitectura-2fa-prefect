const $ = id => document.getElementById(id);
let preToken = '', enrollmentToken = '', lastCode = '', lastStrategy = 'totp';
function status(message, error = false) { $('status').textContent = message; $('status').classList.toggle('error', error); }
async function api(path, body, token) {
  const response = await fetch(path, { method: body ? 'POST' : 'GET', headers: {'Content-Type':'application/json', ...(token ? {Authorization:`Bearer ${token}`} : {})}, ...(body ? {body:JSON.stringify(body)} : {}) });
  const data = await response.json().catch(() => { throw new Error('El servidor no pudo completar la operación. Revisa que Prefect y el backend estén activos.'); });
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Revisa los datos ingresados.');
  return data;
}
async function perform(action) {
  const buttons = [...document.querySelectorAll('button')]; buttons.forEach(b => b.disabled = true);
  try { await action(); } catch (e) { status(e.message, true); } finally { buttons.forEach(b => b.disabled = false); }
}
const credentials = () => ({email:$('email').value,password:$('password').value});
$('identity').onsubmit = e => { e.preventDefault(); perform(async () => {
  const data = await api('/auth/login', credentials()); preToken = data.pre_auth_token; $('password').value = ''; $('vault').hidden = true; $('second').hidden = false;
  status(data.mfa_state === 'ACTIVE' ? 'Contraseña validada. Falta el segundo factor.' : 'Configura y activa 2FA antes de continuar.');
}); };
$('enroll').onclick = () => { if (!$('identity').reportValidity()) return; perform(async () => {
  const data = await api('/auth/enroll/start', credentials()); enrollmentToken = data.enrollment_token; $('password').value = ''; $('seed').value = data.secret; $('qr').src = data.qr_data_url; $('setup').hidden = false; status('PENDING_VERIFICATION: confirma un código de tu app en cinco minutos.');
}); };
$('copy').onclick = () => perform(async () => { await navigator.clipboard.writeText($('seed').value); status('Semilla copiada.'); });
$('activate').onsubmit = e => { e.preventDefault(); perform(async () => {
  const data = await api('/auth/enroll/confirm', {code:$('activation').value}, enrollmentToken); $('setup').hidden = true; $('seed').value = ''; $('qr').removeAttribute('src'); enrollmentToken = ''; $('backups').textContent = data.backup_codes.join('\n'); $('recovery').hidden = false; status(data.message);
}); };
$('hide-backups').onclick = () => { $('backups').textContent = ''; $('recovery').hidden = true; };
$('verify').onsubmit = e => { e.preventDefault(); perform(async () => {
  lastCode = $('otp').value.trim(); lastStrategy = $('strategy').value;
  const data = await api('/auth/verify-2fa', {code:lastCode,strategy:lastStrategy}, preToken);
  const vault = await api('/api/boveda-secreta', null, data.access_token); $('vault-message').textContent = vault.message; $('vault').hidden = false; $('otp').value = '';
  status(data.matched_window === null ? 'Código de respaldo consumido.' : 'Acceso verificado. Ventana: ' + ({'-1':'C-1','0':'C','1':'C+1'}[data.matched_window]));
}); };
$('replay').onclick = () => perform(async () => { if (!lastCode) throw new Error('Primero completa una verificación.'); await api('/auth/verify-2fa', {code:lastCode,strategy:lastStrategy}, preToken); status('Código aceptado; revisa la ventana de 90 segundos del ensayo.', true); });
$('deny').onclick = () => perform(async () => { await api('/api/boveda-secreta', null, preToken); status('Acceso inesperado', true); });
$('logout').onclick = () => location.reload();
