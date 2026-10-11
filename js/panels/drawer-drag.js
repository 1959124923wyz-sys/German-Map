(() => {
  function create({ drawer, handle, hostSelector = '.mapwrap', margin = 8 }) {
    let drag = null;

    function hostRect() {
      return document.querySelector(hostSelector)?.getBoundingClientRect() || null;
    }

    function clamp(left, top) {
      const host = hostRect();
      const box = drawer.getBoundingClientRect();
      if (!host) return { left, top };
      const maxLeft = Math.max(margin, host.width - box.width - margin);
      const maxTop = Math.max(margin, host.height - box.height - margin);
      return {
        left: Math.max(margin, Math.min(left, maxLeft)),
        top: Math.max(margin, Math.min(top, maxTop)),
      };
    }

    function apply(left, top) {
      const p = clamp(left, top);
      drawer.style.left = p.left + 'px';
      drawer.style.top = p.top + 'px';
      drawer.style.right = 'auto';
      return p;
    }

    function begin(event) {
      if (event.button != null && event.button !== 0) return;
      if (window.matchMedia('(max-width:920px)').matches) return;
      if (event.target.closest('button,select,input,a')) return;
      const host = hostRect();
      const box = drawer.getBoundingClientRect();
      if (!host) return;

      drag = {
        id: event.pointerId,
        dx: event.clientX - box.left,
        dy: event.clientY - box.top,
        hostLeft: host.left,
        hostTop: host.top,
      };
      handle.classList.add('dragging');
      handle.setPointerCapture?.(event.pointerId);
      event.preventDefault();
    }

    function move(event) {
      if (!drag || event.pointerId !== drag.id) return;
      apply(
        event.clientX - drag.hostLeft - drag.dx,
        event.clientY - drag.hostTop - drag.dy
      );
      event.preventDefault();
    }

    function end(event) {
      if (!drag || event.pointerId !== drag.id) return;
      handle.classList.remove('dragging');
      try {
        handle.releasePointerCapture?.(event.pointerId);
      } catch (_) {}
      drag = null;
    }

    function keepInside() {
      // Desktop dragging writes inline left/top/right. Once stacked on mobile,
      // CSS must own the drawer position, even after viewport rotation.
      if (window.matchMedia('(max-width:920px)').matches) {
        drawer.style.removeProperty('left');
        drawer.style.removeProperty('right');
        drawer.style.removeProperty('top');
        return;
      }
      const host = hostRect();
      if (!host) return;
      const box = drawer.getBoundingClientRect();
      apply(box.left - host.left, box.top - host.top);
    }

    function reset(left = 58, top = 12) {
      apply(left, top);
    }

    return Object.freeze({ begin, move, end, clamp, apply, keepInside, reset });
  }

  window.CrimeDrawerDrag = Object.freeze({ create });
})();
