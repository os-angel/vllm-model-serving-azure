const $ = (id) => document.getElementById(id);
let history = [];
let pending = null;
let controller = null;
let busy = false;

function renderMessage(role, content) {
  const node = document.createElement('article');
  node.className = `message ${role}`;
  const title = document.createElement('strong');
  title.textContent = role === 'user' ? 'Tú' : 'Nemotron';
  const text = document.createElement('p');
  text.textContent = content;
  node.append(title, text);
  $('messages').append(node);
  return text;
}

function redraw() {
  $('messages').replaceChildren();
  for (const message of history) renderMessage(message.role, message.content);
}

function setBusy(value) {
  busy = value;
  for (const id of ['send', 'reset', 'prompt', 'temperature', 'max-tokens', 'reasoning']) $(id).disabled = value;
  $('cancel').hidden = !value;
  $('retry').hidden = value || pending === null;
}

async function checkStatus() {
  try {
    const response = await fetch('/api/status', { signal: AbortSignal.timeout(7000) });
    if (!response.ok) throw new Error();
    const state = await response.json();
    $('service').textContent = state.serving === 'available'
      ? 'Backend disponible · Modelo disponible'
      : 'Backend disponible · Modelo no disponible';
  } catch {
    $('service').textContent = 'No se pudo consultar el backend';
  }
}

async function submit(question) {
  if (busy) return;
  const snapshot = [...history];
  pending = question;
  $('error').textContent = '';
  $('notice').textContent = '';
  redraw();
  renderMessage('user', question);
  const output = renderMessage('assistant', '');
  controller = new AbortController();
  setBusy(true);
  let answer = '';
  let removed = 0;
  let completed = false;
  let terminal = false;
  try {
    const response = await fetch('/api/chat', {
      method: 'POST', signal: controller.signal, headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: [...snapshot, { role: 'user', content: question }],
        temperature: Number($('temperature').value), max_tokens: Number($('max-tokens').value),
        reasoning: $('reasoning').value }),
    });
    if (!response.ok) {
      const problem = await response.json();
      throw new Error(typeof problem.detail === 'string' ? problem.detail : 'Petición inválida.');
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let boundary;
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        if (!frame.startsWith('data: ')) continue;
        const data = JSON.parse(frame.slice(6));
        if (data.type === 'meta') {
          removed = data.removed_turns;
          if (removed) $('notice').textContent = `Se retiraron ${removed} turnos antiguos del contexto enviado.`;
        } else if (data.type === 'delta') {
          answer += data.content;
          output.textContent = answer;
        } else if (data.type === 'done') {
          completed = data.finish_reason === 'stop' && answer.trim().length > 0;
          terminal = true;
        } else if (data.type === 'error') {
          throw new Error(data.message);
        }
      }
      if (done) break;
    }
    if (!terminal || !completed) throw new Error('El stream se interrumpió sin finalizar. Puedes reintentar.');
    history = [...snapshot.slice(removed * 2), { role: 'user', content: question }, { role: 'assistant', content: answer }];
    pending = null;
    $('prompt').value = '';
    // Remove discarded turns from the displayed conversation as well.
    redraw();
  } catch (error) {
    $('error').textContent = error.name === 'AbortError' ? 'Solicitud cancelada. La respuesta parcial no se guardó en el historial.' : error.message;
  } finally {
    controller = null;
    setBusy(false);
    void checkStatus();
  }
}

$('form').addEventListener('submit', (event) => {
  event.preventDefault();
  const question = $('prompt').value.trim();
  if (question) void submit(question);
});
$('retry').addEventListener('click', () => { if (pending !== null) void submit(pending); });
$('cancel').addEventListener('click', () => controller?.abort());
$('reset').addEventListener('click', () => {
  history = []; pending = null; redraw();
  $('prompt').value = ''; $('notice').textContent = ''; $('error').textContent = '';
  setBusy(false);
});
void checkStatus();
setInterval(() => { if (!busy) void checkStatus(); }, 15000);
