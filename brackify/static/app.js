const form = document.getElementById('playlist-form');
const bracketEl = document.getElementById('bracket');
const statusEl = document.getElementById('status');

let bracketState = [];
let finalWinnerId = null;

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  statusEl.textContent = 'Building bracket...';

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

    const seeds = data.seeds || [];
    initializeBracket(seeds);

    const missing = seeds.filter((s) => !s).length;
    if (missing > 0) {
      statusEl.textContent = `Only ${data.total_tracks} tracks available. ${missing} slot(s) left empty.`;
    } else {
      statusEl.textContent = 'Bracket ready. Click a song to advance it forward.';
    }
  } catch (error) {
    statusEl.textContent = error.message;
    bracketEl.innerHTML = '';
  }
});

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

  if (!opponent) {
    statusEl.textContent = 'Two songs are required for this matchup.';
    return;
  }

  const nextRoundIndex = roundIndex + 1;
  if (!bracketState[nextRoundIndex]) {
    finalWinnerId = trackKey(choice);
    statusEl.textContent = `${choice.song_name} wins the bracket!`;
    renderBracket();
    return;
  }

  const targetMatch = Math.floor(matchIndex / 2);
  const targetSlot = matchIndex % 2;

  bracketState[nextRoundIndex][targetMatch][targetSlot] = choice;
  clearDownstream(nextRoundIndex, targetMatch);

  statusEl.textContent = '';
  renderBracket();
}

function renderBracket() {
  bracketEl.innerHTML = '';

  bracketState.forEach((round, roundIndex) => {
    const roundEl = document.createElement('div');
    roundEl.className = 'round';

    const label = document.createElement('h3');
    label.textContent = roundLabel(roundIndex);
    roundEl.appendChild(label);

    round.forEach((match, matchIndex) => {
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
          slotEl.appendChild(renderCover(slot.image_url));

          const meta = document.createElement('div');
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
}

function renderCover(url) {
  const img = document.createElement('img');
  img.className = 'cover';
  const fallback = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80"><rect width="80" height="80" rx="12" fill="%2310181f"/><text x="40" y="46" text-anchor="middle" font-size="26" fill="%239da7b1" font-family="Helvetica, Arial, sans-serif">♪</text></svg>';
  img.src = url || fallback;
  img.alt = url ? 'Album cover' : 'Empty slot';
  return img;
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
