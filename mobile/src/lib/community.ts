import { communityRequest } from '../../../shared/community-protocol.ts';
export async function requestCommunity(path: string, body?: unknown, signal?: AbortSignal): Promise<unknown> {
  const base = (process.env.EXPO_PUBLIC_API_URL ?? '').trim();
  if (!/^https?:\/\//i.test(base)) throw new Error('Research API URL is not configured');
  return communityRequest(base, path, body, signal);
}
