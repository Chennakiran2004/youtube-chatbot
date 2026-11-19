const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const form = $('#videoForm');
const videoInput = $('#videoUrl');
const results = $('#results');
const errorMessage = $('#formError');
const toast = $('#toast');
let toastTimer;

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2600);
}

function getYoutubeId(value) {
  let url;
  try { url = new URL(value.trim()); } catch { return null; }
  const host = url.hostname.toLowerCase().replace(/^www\./, '').replace(/^m\./, '');
  if (host === 'youtu.be') return url.pathname.split('/').filter(Boolean)[0] || null;
  if (host === 'youtube.com' || host === 'youtube-nocookie.com') {
    return url.searchParams.get('v') || url.pathname.split('/').filter(Boolean).at(-1) || null;
  }
  return null;
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const id = getYoutubeId(videoInput.value);
  if (!id || !/^[\w-]{11}$/.test(id)) {
    errorMessage.textContent = 'Enter a valid YouTube video link, such as youtube.com/watch?v=…';
    videoInput.focus();
    return;
  }
  errorMessage.textContent = '';
  const cleanUrl = videoInput.value.trim();
  const submit = $('.primary-button', form);
  const processing = $('#processing');
  const stages = $$('.processing-stage');
  submit.disabled = true;
  submit.querySelector('.button-label').textContent = 'Processing…';
  processing.hidden = false;
  results.hidden = true;
  $('#processingTitle').textContent = 'Fetching video transcript…';
  $('#processingDetail').textContent = 'This can take a few seconds.';
  $('#processingPercent').textContent = '';
  $('#progressBar').classList.add('indeterminate');
  $('#progressBar').style.width = '35%';
  stages.forEach((stage, i) => {
    stage.classList.toggle('done', false);
    stage.classList.toggle('current', i === 0);
  });
  try {
    const response = await fetch('/api/video', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: cleanUrl }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not load this video.');

    stages.forEach((stage) => { stage.classList.remove('current'); stage.classList.add('done'); });
    $('#processingTitle').textContent = 'Transcript ready';
    $('#processingDetail').textContent = 'You can now ask questions about the video.';
    $('#processingPercent').textContent = '✓';
    $('#progressBar').classList.remove('indeterminate');
    $('#progressBar').style.width = '100%';
    $('#readyUrl').textContent = `YouTube video · ${data.video_id}`;
    $('#transcriptSummary').textContent = `${data.chunk_count} sections · ${data.transcript_characters.toLocaleString()} characters`;
    $('#transcriptText').textContent = data.transcript_preview;
    processing.hidden = true;
    results.hidden = false;
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    processing.hidden = true;
    errorMessage.textContent = error.message || 'Could not load this video. Check the link and try again.';
  } finally {
    submit.disabled = false;
    submit.querySelector('.button-label').textContent = 'Get transcript';
  }
});

$('#pasteButton').addEventListener('click', async () => {
  try {
    videoInput.value = await navigator.clipboard.readText();
    errorMessage.textContent = '';
    videoInput.focus();
  } catch {
    videoInput.focus();
    showToast('Paste your YouTube link into the field.');
  }
});

$('#changeVideo').addEventListener('click', () => {
  results.hidden = true;
  videoInput.focus();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

$('#toggleTranscript').addEventListener('click', (event) => {
  const transcript = $('#transcriptText');
  transcript.hidden = !transcript.hidden;
  event.currentTarget.innerHTML = transcript.hidden ? 'Show transcript <span>⌄</span>' : 'Hide transcript <span>⌃</span>';
});

async function addChatMessage(question) {
  const content = $('#chatContent');
  const suggestions = $('.suggestions', content);
  if (suggestions) suggestions.remove();
  const user = document.createElement('div');
  user.className = 'chat-line user-line';
  user.textContent = question;
  const answer = document.createElement('div');
  answer.className = 'chat-line answer-line';
  answer.setAttribute('aria-live', 'polite');
  const thinking = document.createElement('span');
  thinking.className = 'typing-dots';
  thinking.innerHTML = '<i></i><i></i><i></i>';
  answer.append(thinking);
  content.append(user, answer);
  content.scrollTop = content.scrollHeight;
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'Could not get an answer.');
    }
    if (!response.body) throw new Error('This browser does not support streamed responses.');
    answer.replaceChildren();
    const cursor = document.createElement('span');
    cursor.className = 'stream-cursor';
    answer.append(cursor);
    const answerText = document.createTextNode('');
    answer.insertBefore(answerText, cursor);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      answerText.data += decoder.decode(value, { stream: true });
      content.scrollTop = content.scrollHeight;
    }
    answerText.data += decoder.decode();
    cursor.remove();
  } catch (error) {
    answer.classList.add('answer-error');
    answer.textContent = error.message || 'Could not reach the chatbot server. Is it running?';
  }
  content.scrollTop = content.scrollHeight;
}

$('#questionForm').addEventListener('submit', (event) => {
  event.preventDefault();
  const input = $('#questionInput');
  const question = input.value.trim();
  if (!question) return;
  addChatMessage(question);
  input.value = '';
  input.style.height = '24px';
});

$('#questionInput').addEventListener('input', (event) => {
  event.target.style.height = 'auto';
  event.target.style.height = `${Math.min(event.target.scrollHeight, 90)}px`;
});

$('.suggestions').addEventListener('click', (event) => {
  const button = event.target.closest('button');
  if (!button) return;
  $('#questionInput').value = button.textContent.trim();
  $('#questionInput').focus();
});
