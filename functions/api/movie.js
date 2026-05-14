export async function onRequest(context) {
  const url = new URL(context.request.url);
  const title = url.searchParams.get('t');

  if (!title) {
    return new Response(JSON.stringify({ Response: 'False', Error: 'No title provided' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const apiKey = context.env.OMDB_KEY;
  const omdbUrl = `https://www.omdbapi.com/?t=${encodeURIComponent(title)}&plot=full&apikey=${apiKey}`;

  const res = await fetch(omdbUrl);
  const data = await res.json();

  return new Response(JSON.stringify(data), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
  });
}
