// Test fake for ADR-086's `GET /jobs/{id}/image-links`: links each requested asset that `paths` names,
// except those `skip` refuses (a picture the backend left out).
export function imageLinksResponse(url: string, paths: Record<string, string>, skip: (assetId: string) => boolean = () => false): Response {
  const assets = new URLSearchParams(url.split("?")[1]).getAll("asset");
  return Response.json({links: assets.filter(a => paths[a] && !skip(a)).map(a => ({asset_id: a, path: paths[a], url: `https://cdn.test/${paths[a]}`}))});
}
