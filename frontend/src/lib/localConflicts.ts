export type ConflictDomain = 'messages' | 'settings' | 'feedEvents' | 'drafts' | 'mediaMetadata';

export type VersionedLocalValue<T> = {
  value: T;
  updatedAt: number;
  deletedAt?: number | null;
  deviceId?: string;
};

export type ConflictResult<T> = {
  winner: VersionedLocalValue<T>;
  strategy: 'server-delete' | 'client-delete' | 'latest-write' | 'merge-settings' | 'append-only';
  conflicted: boolean;
};

function latest<T>(local: VersionedLocalValue<T>, remote: VersionedLocalValue<T>): ConflictResult<T> {
  const winner = local.updatedAt >= remote.updatedAt ? local : remote;
  return { winner, strategy: 'latest-write', conflicted: local.updatedAt !== remote.updatedAt };
}

export function resolveLocalConflict<T extends Record<string, unknown> | string>(
  domain: ConflictDomain,
  local: VersionedLocalValue<T>,
  remote: VersionedLocalValue<T>,
): ConflictResult<T> {
  if (remote.deletedAt && (!local.updatedAt || remote.deletedAt >= local.updatedAt)) {
    return { winner: remote, strategy: 'server-delete', conflicted: true };
  }

  if (local.deletedAt && local.deletedAt >= remote.updatedAt) {
    return { winner: local, strategy: 'client-delete', conflicted: true };
  }

  if (domain === 'settings') {
    const mergedValue = {
      ...(remote.value as Record<string, unknown>),
      ...(local.value as Record<string, unknown>),
    } as T;
    return {
      winner: { ...local, value: mergedValue, updatedAt: Math.max(local.updatedAt, remote.updatedAt) },
      strategy: 'merge-settings',
      conflicted: local.updatedAt !== remote.updatedAt,
    };
  }

  if (domain === 'feedEvents' || domain === 'messages') {
    return {
      winner: local.updatedAt >= remote.updatedAt ? local : remote,
      strategy: 'append-only',
      conflicted: local.updatedAt !== remote.updatedAt,
    };
  }

  return latest(local, remote);
}
