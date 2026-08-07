import { useCallback, useEffect, useRef, useState } from 'react';
import {
  parseWorkspaceToRuntimeMessage,
  SDM_PROTOCOL_VERSION,
  type RuntimeToWorkspaceMessage,
} from './core/protocol';
import type { SlideDocument } from './core/schema';
import {
  clearActiveEditingSlide,
  setActiveEditingSlide,
} from './editingState';

const RUNTIME_CAPABILITIES: Array<string> = ['edit'];

const TRUSTED_WORKSPACE_ORIGINS = new Set([
  'https://replit.com',
  'https://replit-staging.com',
  'https://staging.replit.com',
]);

interface SessionTarget {
  targetWindow: Window;
  origin: string;
  sessionId: string;
}

function isTrustedWorkspaceOrigin(origin: string): boolean {
  if (TRUSTED_WORKSPACE_ORIGINS.has(origin)) {
    return true;
  }

  try {
    const { hostname, protocol } = new URL(origin);

    return (
      (protocol === 'http:' &&
        (hostname === 'localhost' || hostname === '127.0.0.1')) ||
      (protocol === 'https:' &&
        hostname.startsWith('web--') &&
        hostname.endsWith('.z.zergrush.dev'))
    );
  } catch {
    return false;
  }
}

function findAncestorWindow(source: MessageEventSource | null): Window | null {
  if (source === null) {
    return null;
  }
  let ancestor: Window = window;
  while (ancestor.parent !== ancestor) {
    ancestor = ancestor.parent;
    if (source === ancestor) {
      return ancestor;
    }
  }

  return null;
}

function post(session: SessionTarget, message: RuntimeToWorkspaceMessage) {
  session.targetWindow.postMessage(message, session.origin);
}

export function useSdmRuntimeSession({
  slideId,
  document,
  onDocumentReplaced,
}: {
  slideId: string;
  document: SlideDocument | null;
  onDocumentReplaced: (document: SlideDocument) => void;
}): {
  editing: boolean;
  selectedIds: Array<string>;
  select: (ids: Array<string>) => void;
  commit: (document: SlideDocument, selectedIds: Array<string>) => void;
  requestHistory: (direction: 'undo' | 'redo') => void;
} {
  const [editing, setEditing] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Array<string>>([]);
  const documentRef = useRef(document);
  documentRef.current = document;
  const onDocumentReplacedRef = useRef(onDocumentReplaced);
  onDocumentReplacedRef.current = onDocumentReplaced;
  const sessionRef = useRef<SessionTarget | null>(null);
  const revisionRef = useRef(0);
  const authorityReadyRef = useRef(false);
  const historyReadyRef = useRef(false);

  useEffect(() => {
    if (window.parent === window) {
      return;
    }
    window.parent.postMessage(
      {
        type: 'sdm:ready',
        supportedProtocolVersions: [SDM_PROTOCOL_VERSION],
        slideId,
        capabilities: RUNTIME_CAPABILITIES,
      } satisfies RuntimeToWorkspaceMessage,
      '*',
    );
  }, [slideId]);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const result = parseWorkspaceToRuntimeMessage(event.data);
      if (!result.ok) {
        return;
      }
      const message = result.message;
      if (message.slideId !== slideId) {
        return;
      }
      if (message.type === 'sdm:setEditMode') {
        if (message.enabled) {
          const ancestor = findAncestorWindow(event.source);
          const currentDocument = documentRef.current;
          if (
            ancestor === null ||
            currentDocument === null ||
            !isTrustedWorkspaceOrigin(event.origin)
          ) {
            return;
          }
          const session: SessionTarget = {
            targetWindow: ancestor,
            origin: event.origin,
            sessionId: message.sessionId,
          };
          sessionRef.current = session;
          revisionRef.current = 0;
          authorityReadyRef.current = false;
          historyReadyRef.current = false;
          setEditing(false);
          setSelectedIds([]);
          clearActiveEditingSlide(slideId);
          post(session, {
            type: 'sdm:ready',
            supportedProtocolVersions: [SDM_PROTOCOL_VERSION],
            slideId,
            sessionId: session.sessionId,
            capabilities: RUNTIME_CAPABILITIES,
          });
          post(session, {
            type: 'sdm:doc',
            protocolVersion: SDM_PROTOCOL_VERSION,
            slideId,
            sessionId: session.sessionId,
            document: currentDocument,
            selectedIds: [],
          });

          return;
        }
        const session = sessionRef.current;
        if (
          session === null ||
          session.sessionId !== message.sessionId ||
          event.source !== session.targetWindow
        ) {
          return;
        }
        sessionRef.current = null;
        authorityReadyRef.current = false;
        historyReadyRef.current = false;
        setEditing(false);
        setSelectedIds([]);
        clearActiveEditingSlide(slideId);

        return;
      }

      const session = sessionRef.current;
      if (
        session === null ||
        session.sessionId !== message.sessionId ||
        event.source !== session.targetWindow ||
        event.origin !== session.origin
      ) {
        return;
      }
      if (message.type === 'sdm:setDoc') {
        revisionRef.current = message.logicalRevision;
        authorityReadyRef.current = true;
        setSelectedIds(message.selectedIds);
        onDocumentReplacedRef.current(message.document);
        setEditing(true);
        setActiveEditingSlide(slideId);

        return;
      }
      if (message.type === 'sdm:select') {
        setSelectedIds(message.selectedIds);

        return;
      }
      if (message.type === 'sdm:historyReady') {
        historyReadyRef.current = true;
      }
    };
    window.addEventListener('message', handleMessage);

    return () => window.removeEventListener('message', handleMessage);
  }, [slideId]);

  useEffect(
    () => () => {
      if (sessionRef.current !== null) {
        clearActiveEditingSlide(slideId);
      }
    },
    [slideId],
  );

  const select = useCallback(
    (ids: Array<string>) => {
      const session = sessionRef.current;
      if (session === null || !authorityReadyRef.current) {
        return;
      }
      setSelectedIds(ids);
      post(session, {
        type: 'sdm:selectionChanged',
        protocolVersion: SDM_PROTOCOL_VERSION,
        slideId,
        sessionId: session.sessionId,
        selectedIds: ids,
      });
    },
    [slideId],
  );

  const commit = useCallback(
    (nextDocument: SlideDocument, ids: Array<string>) => {
      const session = sessionRef.current;
      if (session === null || !authorityReadyRef.current) {
        return;
      }
      setSelectedIds(ids);
      onDocumentReplacedRef.current(nextDocument);
      post(session, {
        type: 'sdm:committed',
        protocolVersion: SDM_PROTOCOL_VERSION,
        slideId,
        sessionId: session.sessionId,
        baseLogicalRevision: revisionRef.current,
        transactionId: crypto.randomUUID(),
        document: nextDocument,
        selectedIds: ids,
      });
      // Advance optimistically in lockstep with the workspace: accepted
      // commits are not echoed back. If the commit was stale the workspace
      // answers with an authoritative sdm:setDoc that resets this counter.
      revisionRef.current += 1;
    },
    [slideId],
  );

  const requestHistory = useCallback(
    (direction: 'undo' | 'redo') => {
      const session = sessionRef.current;
      if (
        session === null ||
        !authorityReadyRef.current ||
        !historyReadyRef.current
      ) {
        return;
      }
      authorityReadyRef.current = false;
      setEditing(false);
      post(session, {
        type: 'sdm:historyRequest',
        protocolVersion: SDM_PROTOCOL_VERSION,
        slideId,
        sessionId: session.sessionId,
        direction,
      });
    },
    [slideId],
  );

  return { editing, selectedIds, select, commit, requestHistory };
}
