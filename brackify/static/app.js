const form = document.getElementById('playlist-form');
const bracketEl = document.getElementById('bracket');
const statusEl = document.getElementById('status');
const shareInput = document.getElementById('share-url');
const copyButton = document.getElementById('copy-share');
const bracketId = document.body?.dataset?.bracketId;

let bracketState = [];
let finalWinnerId = null;
let previewAudio = null;
let previewTimeout = null;
let previewButtonRef = null;
let previewUrlRef = null;

if (form) {
  form.addEventListener('submit', handleFormSubmit);
}

if (copyButton && shareInput) {
  copyButton.addEventListener('click', handleCopyLink);
}

if (bracketId) {
  hydrateBracket(bracketId);
}

function setStatus(message) {
  if (statusEl) {
    statusEl.textContent = message;
  }
}

async function handleFormSubmit(event) {
  event.preventDefault();
  setStatus('Building bracket...');

  const payload = {
    playlist: form.playlist.value.trim(),
    order: form.order.value,
    size: parseInt(form.size.value, 10),
  };

  try {
    const res = await fetch('/api/bracket', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || 'Failed to build bracket');
    }

    if (data.share_url) {
      setStatus('Bracket ready! Opening your bracket...');
      window.location.href = data.share_url;
      return;
    }

    setStatus('Bracket ready!');
  } catch (error) {
    setStatus(error.message);
  }
}

async function hydrateBracket(id) {
  setStatus('Loading bracket...');

  try {
    const res = await fetch(`/api/bracket/${encodeURIComponent(id)}`);
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || 'Could not load bracket');
    }

    updateShareLink(data.share_url);
    initializeBracket(data.seeds || []);

    const missing = (data.seeds || []).filter((s) => !s).length;
    if (missing > 0) {
      setStatus(`Only ${data.total_tracks} tracks available. ${missing} slot(s) left empty.`);
    } else {
      setStatus('Bracket ready. Click a song to advance it forward.');
    }
  } catch (error) {
    setStatus(error.message);
    if (bracketEl) {
      bracketEl.innerHTML = '';
    }
  }
}

function updateShareLink(url) {
  if (shareInput && url) {
    shareInput.value = url;
  }
}

function handleCopyLink() {
  if (!shareInput) return;

  navigator.clipboard.writeText(shareInput.value)
    .then(() => {
      copyButton.textContent = 'Copied!';
      setTimeout(() => {
        copyButton.textContent = 'Copy link';
      }, 1600);
    })
    .catch(() => {
      copyButton.textContent = 'Unable to copy';
    });
}

function trackKey(track) {
  return track.track_id || `${track.song_name}-${track.album_name}-${track.artists}`;
}

function initializeBracket(seeds) {
  finalWinnerId = null;
  bracketState = [];

  const matches = chunkMatches(seeds);
  bracketState.push(matches);

  let matchCount = matches.length;
  while (matchCount > 1) {
    matchCount = Math.floor(matchCount / 2);
    bracketState.push(Array.from({length: matchCount}, () => [null, null]));
  }

  renderBracket();
}

function chunkMatches(seeds) {
  if (!seeds || seeds.length === 0) {
    return [];
  }

  return seeds.reduce((acc, _, idx) => {
    if (idx % 2 === 0) {
      acc.push([seeds[idx], seeds[idx + 1] || null]);
    }
    return acc;
  }, []);
}

function clearDownstream(roundIndex, matchIndex) {
  const deeperRound = roundIndex + 1;
  if (!bracketState[deeperRound]) {
    finalWinnerId = null;
    return;
  }

  const deeperMatch = Math.floor(matchIndex / 2);
  bracketState[deeperRound][deeperMatch] = [null, null];
  clearDownstream(deeperRound, deeperMatch);
}

function handlePick(roundIndex, matchIndex, slotIndex) {
  const matchup = bracketState[roundIndex][matchIndex];
  const choice = matchup[slotIndex];
  const opponent = matchup[slotIndex === 0 ? 1 : 0];

  if (!choice) {
    return;
  }

  const nextRoundIndex = roundIndex + 1;
  if (!bracketState[nextRoundIndex]) {
    if (finalWinnerId && trackKey(choice) === finalWinnerId) {
      finalWinnerId = null;
      setStatus('');
      renderBracket();
      return;
    }

    finalWinnerId = trackKey(choice);
    setStatus(`${choice.song_name} wins the bracket!`);
    renderBracket();
    launchConfetti();
    return;
  }

  const targetMatch = Math.floor(matchIndex / 2);
  const targetSlot = matchIndex % 2;
  const existing = bracketState[nextRoundIndex][targetMatch][targetSlot];

  if (existing && trackKey(existing) === trackKey(choice)) {
    bracketState[nextRoundIndex][targetMatch][targetSlot] = null;
    clearDownstream(nextRoundIndex, targetMatch);
    finalWinnerId = null;
    setStatus('');
    renderBracket();
    return;
  }

  if (!opponent) {
    setStatus('Two songs are required for this matchup.');
    return;
  }

  bracketState[nextRoundIndex][targetMatch][targetSlot] = choice;
  clearDownstream(nextRoundIndex, targetMatch);

  setStatus('');
  renderBracket();
}

function renderBracket() {
  if (!bracketEl) return;

  const totalRounds = bracketState.length;
  if (totalRounds === 0) {
    bracketEl.innerHTML = '';
    return;
  }

  const leftColumns = [];
  const rightColumns = [];
  let finalColumn = null;

  bracketState.forEach((round, roundIndex) => {
    const label = roundLabel(roundIndex);
    if (roundIndex === totalRounds - 1) {
      finalColumn = {
        roundIndex,
        label,
        matches: round.map((match, idx) => ({match, matchIndex: idx})),
        final: true,
      };
      return;
    }

    const midpoint = round.length / 2;
    const leftMatches = round.slice(0, midpoint).map((match, idx) => ({match, matchIndex: idx}));
    const rightMatches = round.slice(midpoint).map((match, idx) => ({match, matchIndex: idx + midpoint}));

    leftColumns.push({roundIndex, label, matches: leftMatches});
    rightColumns.unshift({roundIndex, label, matches: rightMatches});
  });

  const columns = [...leftColumns, finalColumn, ...rightColumns].filter(Boolean);
  bracketEl.innerHTML = '';

  columns.forEach((column) => {
    const {roundIndex} = column;

    const roundEl = document.createElement('div');
    roundEl.className = `round${column.final ? ' final' : ''}`;
    roundEl.dataset.roundIndex = roundIndex;

    const labelEl = document.createElement('h3');
    labelEl.textContent = column.final ? 'Final' : column.label;
    roundEl.appendChild(labelEl);

    column.matches.forEach(({match, matchIndex}) => {
      const matchEl = document.createElement('div');
      matchEl.className = 'match';

      match.forEach((slot, slotIndex) => {
        const slotEl = document.createElement('div');
        slotEl.className = 'slot';

        const isClickable = Boolean(slot);
        if (!isClickable) {
          slotEl.classList.add('disabled');
        }

        if (slot) {
          slotEl.appendChild(renderCover(slot));

          const meta = document.createElement('div');
          meta.className = 'meta';
          const title = document.createElement('p');
          title.className = 'song-title';
          title.textContent = slot.song_name;

          const artist = document.createElement('p');
          artist.className = 'song-artist';
          artist.textContent = slot.artists;

          meta.appendChild(title);
          meta.appendChild(artist);
          slotEl.appendChild(meta);

          if (isSelected(roundIndex, matchIndex, slotIndex, slot)) {
            slotEl.classList.add('selected');
          }
        } else {
          const placeholder = document.createElement('p');
          placeholder.className = 'placeholder';
          placeholder.textContent = 'Empty slot';
          slotEl.appendChild(renderCover(null));
          slotEl.appendChild(placeholder);
        }

        slotEl.addEventListener('click', () => handlePick(roundIndex, matchIndex, slotIndex));
        matchEl.appendChild(slotEl);
      });

      roundEl.appendChild(matchEl);
    });

    bracketEl.appendChild(roundEl);
  });

  applyBracketLayout(columns.length);
}

function renderCover(track) {
  const wrapper = document.createElement('div');
  wrapper.className = 'cover-wrapper';

  const img = document.createElement('img');
  img.className = 'cover';
  const fallback = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80"><rect width="80" height="80" rx="12" fill="%23f2f2f2"/><text x="40" y="46" text-anchor="middle" font-size="26" fill="%23888888" font-family="Helvetica, Arial, sans-serif">♪</text></svg>';

  if (track && track.image_url) {
    img.src = track.image_url;
  } else {
    img.src = fallback;
  }

  img.alt = track ? `${track.song_name} cover art` : 'Empty slot';

  wrapper.appendChild(img);

  if (track && track.preview_url) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'preview-button';
    button.title = 'Play 15 second preview';
    button.setAttribute('aria-label', `Play preview of ${track.song_name}`);
    button.textContent = '▶';

    button.addEventListener('click', (event) => {
      event.stopPropagation();
      togglePreview(track.preview_url, button);
    });

    wrapper.appendChild(button);
  }

  return wrapper;
}

function togglePreview(url, button) {
  if (!url) return;

  const isSameTrack = previewUrlRef === url;
  const isPlaying = previewAudio && !previewAudio.paused;

  if (isSameTrack && isPlaying) {
    stopPreview();
    return;
  }

  stopPreview();

  previewAudio = new Audio(url);
  previewUrlRef = url;
  previewAudio.volume = 0.9;
  previewAudio.addEventListener('ended', stopPreview);

  if (button) {
    previewButtonRef = button;
    setPreviewButtonState(button, true);
  }

  previewAudio.play().catch(() => {
    stopPreview();
  });

  previewTimeout = setTimeout(stopPreview, 15000);
}

function setPreviewButtonState(button, playing) {
  button.textContent = playing ? '❚❚' : '▶';
  button.classList.toggle('is-playing', playing);
  button.setAttribute('aria-pressed', playing ? 'true' : 'false');
}

function stopPreview() {
  if (previewAudio) {
    previewAudio.pause();
    previewAudio = null;
  }

  if (previewTimeout) {
    clearTimeout(previewTimeout);
    previewTimeout = null;
  }

  if (previewButtonRef) {
    setPreviewButtonState(previewButtonRef, false);
    previewButtonRef = null;
  }

  previewUrlRef = null;
}

function isSelected(roundIndex, matchIndex, slotIndex, track) {
  const nextRoundIndex = roundIndex + 1;
  if (!bracketState[nextRoundIndex]) {
    return finalWinnerId !== null && trackKey(track) === finalWinnerId;
  }

  const targetMatch = Math.floor(matchIndex / 2);
  const targetSlot = matchIndex % 2;
  const nextSlot = bracketState[nextRoundIndex][targetMatch][targetSlot];

  return nextSlot && trackKey(nextSlot) === trackKey(track);
}

function roundLabel(roundIndex) {
  if (roundIndex === bracketState.length - 1) {
    return 'Final';
  }

  const startSize = bracketState[0].length * 2;
  const currentSize = startSize / (2 ** roundIndex);
  return `Round of ${currentSize}`;
}

function launchConfetti() {
  const colors = ['#ff6b6b', '#ffd166', '#06d6a0', '#118ab2', '#9b5de5', '#f15bb5'];
  const duration = 1600;
  const end = Date.now() + duration;

  const frame = () => {
    if (Date.now() > end) return;
    createPiece();
    requestAnimationFrame(frame);
  };

  requestAnimationFrame(frame);

  function createPiece() {
    const piece = document.createElement('div');
    piece.className = 'confetti-piece';
    const size = 8 + Math.random() * 6;
    piece.style.width = `${size}px`;
    piece.style.height = `${size * 1.2}px`;
    piece.style.left = `${Math.random() * 100}%`;
    piece.style.background = colors[Math.floor(Math.random() * colors.length)];
    document.body.appendChild(piece);

    const translateY = 500 + Math.random() * 500;
    const rotate = -300 + Math.random() * 600;

    piece.animate([
      {transform: 'translateY(0) rotate(0deg)', opacity: 1},
      {transform: `translateY(${translateY}px) rotate(${rotate}deg)`, opacity: 0.9},
    ], {
      duration: 800 + Math.random() * 400,
      easing: 'ease-out',
    });

    setTimeout(() => piece.remove(), 1400);
  }
}

function applyBracketLayout(roundCount) {
  if (!bracketEl) return;

  bracketEl.style.setProperty('--round-count', roundCount);

  const rounds = Array.from(bracketEl.querySelectorAll('.round'));
  const firstMatch = bracketEl.querySelector('.match');
  const matchHeight = firstMatch?.getBoundingClientRect().height || 0;
  const baseGap = 18;
  const baseStride = matchHeight + baseGap || 1;

  rounds.forEach((roundEl) => {
    const roundIndex = Number.parseInt(roundEl.dataset.roundIndex || '0', 10);
    const stride = baseStride * Math.max(1, 2 ** roundIndex);
    const gap = stride - matchHeight;

    roundEl.style.gap = `${Math.max(gap, baseGap)}px`;
    roundEl.style.marginTop = '0px';
  });
}
