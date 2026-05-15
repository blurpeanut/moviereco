export async function onRequest(context) {
  if (context.request.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
  }

  if (context.request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }

  const apiKey = context.env.OPENAI_API_KEY;
  if (!apiKey) {
    return new Response(JSON.stringify({ error: 'API key not configured' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const { type, data } = await context.request.json();

  let prompt;
  if (type === 'joke') {
    prompt = `You're writing for a movie recommendation app. The user's vibe is "${data.moodLabel}" and they were just recommended "${data.movieTitle}" (${data.genre}, ${data.year}). Write one short, witty, movie-related joke that fits their mood. Just the joke — no intro, no label, no explanation.`;
  } else if (type === 'watchlist') {
    const movieList = data.movies.map(m =>
      `"${m.title}" (${m.year}, ${m.genre || '?'}, IMDb ${m.rating || '?'}${m.watched ? ', watched' : ', unwatched'})`
    ).join('\n');
    const watchedCount = data.movies.filter(m => m.watched).length;
    const total = data.movies.length;
    prompt = `You are a sharp, witty film critic who can read a person's soul through their movie choices. Analyse this watchlist and write a single, clever one-liner that reveals something true and specific about this person's taste — their emotional patterns, the themes they're drawn to, what they're secretly seeking in a film. Go beyond just naming genres. Look for: tonal patterns (dark vs hopeful), era preferences, pacing choices, the mix of watched vs saved. Be insightful, a little poetic, and mildly cheeky. One sentence only. No intro, no label, no quotation marks.

Watchlist (${watchedCount} of ${total} watched):
${movieList}`;
  } else {
    return new Response(JSON.stringify({ error: 'Unknown type' }), { status: 400 });
  }

  const res = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'gpt-4o-mini',
      max_tokens: 120,
      messages: [{ role: 'user', content: prompt }],
    }),
  });

  const result = await res.json();
  const text = result.choices?.[0]?.message?.content?.trim() || '';

  return new Response(JSON.stringify({ text }), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
  });
}
