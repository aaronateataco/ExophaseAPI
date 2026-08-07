import {
  useEffect,
  useRef,
  type PointerEvent as ReactPointerEvent,
  type RefObject,
} from 'react';
import {
  scaleTextSizePt,
  setElementFrame,
  translateRootElements,
} from './core/operations';
import type {
  Element as SdmElement,
  Frame,
  SlideDocument,
} from './core/schema';
import {
  HANDLE_CURSORS,
  HANDLE_POS,
  HANDLES,
  moveFrame,
  resizeFrame,
  type Handle,
} from './geometry';

const DRAG_THRESHOLD_PX = 3;

interface Props {
  document: SlideDocument;
  selectedIds: Array<string>;
  scale: number;
  stageRef: RefObject<HTMLDivElement | null>;
  onSelect: (ids: Array<string>) => void;
  onCommit: (document: SlideDocument, selectedIds: Array<string>) => void;
  onHistory: (direction: 'undo' | 'redo') => void;
}

function topLevelIdAt(
  target: EventTarget | null,
  stage: HTMLElement,
): string | null {
  if (!(target instanceof Element)) {
    return null;
  }
  let found: string | null = null;
  let node: Element | null = target.closest('[data-sdm-id]');
  while (node !== null && stage.contains(node)) {
    const id = node.getAttribute('data-sdm-id');
    if (id !== null) {
      found = id;
    }
    node = node.parentElement?.closest('[data-sdm-id]') ?? null;
  }

  return found;
}

function isEditableTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable ||
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA')
  );
}

function isOverlayChrome(target: EventTarget | null): boolean {
  return (
    target instanceof Element && target.closest('[data-sdm-handle]') !== null
  );
}

function sameFrame(left: Frame, right: Frame): boolean {
  return (
    left.x === right.x &&
    left.y === right.y &&
    left.width === right.width &&
    left.height === right.height
  );
}

function textFitFactor(
  stage: HTMLElement | null,
  elementId: string,
): number {
  const element = stage?.querySelector(
    `[data-sdm-id="${CSS.escape(elementId)}"]`,
  );
  const textBody = element?.querySelector('[data-sdm-text-body]');
  if (!(textBody instanceof HTMLElement)) {
    return 1;
  }
  const factor = Number.parseFloat(
    textBody.style.getPropertyValue('--sdm-fit'),
  );

  return Number.isFinite(factor) && factor > 0 && factor < 1 ? factor : 1;
}

function applyDraft(nodes: Array<HTMLElement>, frame: Frame) {
  for (const node of nodes) {
    node.style.left = `${frame.x}px`;
    node.style.top = `${frame.y}px`;
    node.style.width = `${frame.width}px`;
    node.style.height = `${frame.height}px`;
  }
}

export function SdmInteractionLayer({
  document,
  selectedIds,
  scale,
  stageRef,
  onSelect,
  onCommit,
  onHistory,
}: Props) {
  const documentRef = useRef(document);
  documentRef.current = document;
  const scaleRef = useRef(scale);
  scaleRef.current = scale;
  const selectedIdsRef = useRef(selectedIds);
  selectedIdsRef.current = selectedIds;
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const onCommitRef = useRef(onCommit);
  onCommitRef.current = onCommit;
  const onHistoryRef = useRef(onHistory);
  onHistoryRef.current = onHistory;
  const overlayRef = useRef<HTMLDivElement>(null);
  const gestureRef = useRef<{
    captureTarget: HTMLElement;
    controller: AbortController;
    elementId: string;
    pointerId: number;
  } | null>(null);

  const draftNodes = (elementId: string): Array<HTMLElement> => {
    const nodes: Array<HTMLElement> = [];
    const stageNode = stageRef.current?.querySelector(
      `[data-sdm-id="${CSS.escape(elementId)}"]`,
    );
    if (stageNode instanceof HTMLElement) {
      nodes.push(stageNode);
    }
    const outlineNode = overlayRef.current?.querySelector(
      `[data-sdm-selection-id="${CSS.escape(elementId)}"]`,
    );
    if (outlineNode instanceof HTMLElement) {
      nodes.push(outlineNode);
    }

    return nodes;
  };

  const endGesture = () => {
    const gesture = gestureRef.current;
    if (gesture === null) {
      return;
    }
    gestureRef.current = null;
    const element = documentRef.current.elements.find(
      (candidate) => candidate.id === gesture.elementId,
    );
    if (element !== undefined) {
      applyDraft(draftNodes(gesture.elementId), element.frame);
    }
    gesture.controller.abort();
    try {
      gesture.captureTarget.releasePointerCapture(gesture.pointerId);
    } catch {}
  };

  const trackGesture = ({
    elementId,
    startEvent,
    startFrame,
    frameAt,
    commitFrame,
  }: {
    elementId: string;
    startEvent: PointerEvent;
    startFrame: Frame;
    frameAt: (dxStage: number, dyStage: number, shiftKey: boolean) => Frame;
    commitFrame: (frame: Frame, fitFactor: number) => void;
  }) => {
    endGesture();
    const captureTarget = stageRef.current;
    if (captureTarget === null) {
      return;
    }
    const controller = new AbortController();
    gestureRef.current = {
      captureTarget,
      controller,
      elementId,
      pointerId: startEvent.pointerId,
    };
    const applyTo = (frame: Frame) => applyDraft(draftNodes(elementId), frame);
    let moved = false;
    let lastFrame = startFrame;

    const onMove = (event: PointerEvent) => {
      if (event.pointerId !== startEvent.pointerId) {
        return;
      }
      const dxClient = event.clientX - startEvent.clientX;
      const dyClient = event.clientY - startEvent.clientY;
      if (!moved && Math.hypot(dxClient, dyClient) < DRAG_THRESHOLD_PX) {
        return;
      }
      moved = true;
      const stageScale = scaleRef.current || 1;
      lastFrame = frameAt(
        dxClient / stageScale,
        dyClient / stageScale,
        event.shiftKey,
      );
      applyTo(lastFrame);
    };

    const finish = (event: PointerEvent) => {
      if (event.pointerId !== startEvent.pointerId) {
        return;
      }
      const shouldCommit = moved && !sameFrame(lastFrame, startFrame);
      const fitFactor = shouldCommit
        ? textFitFactor(stageRef.current, elementId)
        : 1;
      endGesture();
      if (!shouldCommit) {
        return;
      }
      commitFrame(lastFrame, fitFactor);
    };

    const cancel = (event: PointerEvent) => {
      if (event.pointerId !== startEvent.pointerId) {
        return;
      }
      endGesture();
    };

    window.addEventListener('pointermove', onMove, {
      signal: controller.signal,
    });
    window.addEventListener('pointerup', finish, { signal: controller.signal });
    window.addEventListener('pointercancel', cancel, {
      signal: controller.signal,
    });
    captureTarget.addEventListener('lostpointercapture', cancel, {
      signal: controller.signal,
    });
    try {
      captureTarget.setPointerCapture(startEvent.pointerId);
    } catch {}
  };

  const beginDragRef = useRef<
    (event: PointerEvent, element: SdmElement) => void
  >(() => {});
  beginDragRef.current = (event, element) => {
    trackGesture({
      elementId: element.id,
      startEvent: event,
      startFrame: element.frame,
      frameAt: (dx, dy) => moveFrame(element.frame, dx, dy),
      commitFrame: (frame) => {
        onCommitRef.current(
          translateRootElements(
            documentRef.current,
            [element.id],
            frame.x - element.frame.x,
            frame.y - element.frame.y,
          ),
          [element.id],
        );
      },
    });
  };

  const beginResize = (
    event: ReactPointerEvent<HTMLDivElement>,
    element: SdmElement,
    handle: Handle,
  ) => {
    if (event.button !== 0) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    trackGesture({
      elementId: element.id,
      startEvent: event.nativeEvent,
      startFrame: element.frame,
      frameAt: (dx, dy, shiftKey) =>
        resizeFrame(element.frame, handle, dx, dy, shiftKey),
      commitFrame: (frame, fitFactor) => {
        const resized = setElementFrame(
          documentRef.current,
          element.id,
          frame,
        );
        onCommitRef.current(
          scaleTextSizePt(resized, element.id, fitFactor),
          [element.id],
        );
      },
    });
  };

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) {
      return;
    }

    const onPointerDown = (event: PointerEvent) => {
      if (event.button !== 0 || isOverlayChrome(event.target)) {
        return;
      }
      const id = topLevelIdAt(event.target, stage);
      if (id === null) {
        onSelectRef.current([]);

        return;
      }
      const element = documentRef.current.elements.find(
        (candidate) => candidate.id === id,
      );
      if (element === undefined) {
        return;
      }
      event.preventDefault();
      const alreadySelected =
        selectedIdsRef.current.length === 1 && selectedIdsRef.current[0] === id;
      if (!alreadySelected) {
        onSelectRef.current([id]);

        return;
      }
      if (!element.locked) {
        beginDragRef.current(event, element);
      }
    };

    const suppressActions = (event: MouseEvent) => {
      event.preventDefault();
      event.stopPropagation();
    };

    stage.addEventListener('pointerdown', onPointerDown);
    stage.addEventListener('click', suppressActions, true);

    return () => {
      stage.removeEventListener('pointerdown', onPointerDown);
      stage.removeEventListener('click', suppressActions, true);
    };
  }, [stageRef]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) {
        return;
      }
      if ((event.metaKey || event.ctrlKey) && !event.altKey) {
        const key = event.key.toLowerCase();
        if (key === 'z') {
          event.preventDefault();
          onHistoryRef.current(event.shiftKey ? 'redo' : 'undo');

          return;
        }
        if (key === 'y') {
          event.preventDefault();
          onHistoryRef.current('redo');

          return;
        }
      }
      if (event.key === 'Escape' && selectedIdsRef.current.length > 0) {
        onSelectRef.current([]);
      }
    };
    window.addEventListener('keydown', onKeyDown);

    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => () => endGesture(), []);

  const lastDocumentRef = useRef(document);
  useEffect(() => {
    if (lastDocumentRef.current === document) {
      return;
    }
    lastDocumentRef.current = document;
    endGesture();
  });

  const selectedElements = document.elements.filter((element) =>
    selectedIds.includes(element.id),
  );
  const resizeTarget =
    selectedElements.length === 1 &&
    selectedElements[0] !== undefined &&
    !selectedElements[0].locked &&
    selectedElements[0].type !== 'group' &&
    selectedElements[0].type !== 'line' &&
    !selectedElements[0].rotationDeg
      ? selectedElements[0]
      : null;
  const outlineWidth = Math.max(1.5 / (scale || 1), 1);
  const handleSize = 11 / (scale || 1);

  return (
    <div
      ref={overlayRef}
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 1000000,
      }}
    >
      {selectedElements.map((element) => (
        <div
          key={element.id}
          data-sdm-selection-id={element.id}
          style={{
            position: 'absolute',
            left: element.frame.x,
            top: element.frame.y,
            width: element.frame.width,
            height: element.frame.height,
            transform: element.rotationDeg
              ? `rotate(${element.rotationDeg}deg)`
              : undefined,
            transformOrigin: 'center center',
            border: `${outlineWidth}px solid #2563eb`,
            boxSizing: 'border-box',
            pointerEvents: 'none',
          }}
        >
          {resizeTarget === element
            ? HANDLES.map((handle) => (
                <div
                  key={handle}
                  data-sdm-handle={handle}
                  onPointerDown={(handleEvent) =>
                    beginResize(handleEvent, element, handle)
                  }
                  style={{
                    position: 'absolute',
                    left: HANDLE_POS[handle].left,
                    top: HANDLE_POS[handle].top,
                    width: handleSize,
                    height: handleSize,
                    marginLeft: -handleSize / 2,
                    marginTop: -handleSize / 2,
                    background: '#ffffff',
                    border: `${outlineWidth}px solid #2563eb`,
                    borderRadius: 2 / (scale || 1),
                    cursor: HANDLE_CURSORS[handle],
                    pointerEvents: 'auto',
                  }}
                />
              ))
            : null}
        </div>
      ))}
    </div>
  );
}
