/** One moving highlight for a navigation list, shadcn tab list, or exclusive toggle. */
export function slidingIndicator(element: HTMLElement) {
  let frame = 0, disposed = false, initialized = false;
  const items = ':scope > a, :scope > button';
  const active = ':scope > [aria-current="page"], :scope > [data-state="active"], :scope > [aria-pressed="true"]';
  const resize = new ResizeObserver(schedule);
  function observeItems() {
    resize.disconnect();
    resize.observe(element);
    element.querySelectorAll<HTMLElement>(items).forEach(item=>resize.observe(item));
  }
  function measure() {
    frame = 0;
    if (disposed) return;
    const selected = element.querySelector<HTMLElement>(active);
    const bounds = selected?.getBoundingClientRect();
    const visible = bounds && bounds.width > 0 && bounds.height > 0;
    element.dataset.indicatorVisible = String(!!visible);
    if (!visible) return;
    const container = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    // Absolute positioning starts inside the container border. Preserve fractional
    // CSS pixels: offsetLeft/offsetWidth round them and visibly skew narrow pills.
    const x = bounds.left - container.left - parseFloat(style.borderLeftWidth) + element.scrollLeft;
    const y = bounds.top - container.top - parseFloat(style.borderTopWidth) + element.scrollTop;
    element.style.setProperty('--indicator-x', `${x}px`);
    element.style.setProperty('--indicator-y', `${y}px`);
    element.style.setProperty('--indicator-width', `${bounds.width}px`);
    element.style.setProperty('--indicator-height', `${bounds.height}px`);
    if (!initialized) {
      initialized = true;
      frame = requestAnimationFrame(()=>{frame=0;if(!disposed)element.dataset.indicatorReady='true';});
    }
  }
  function schedule() {
    if (!disposed && !frame) frame = requestAnimationFrame(measure);
  }
  const changes = new MutationObserver(records=>{
    if (records.some(record=>record.type==='childList')) observeItems();
    schedule();
  });
  changes.observe(element,{subtree:true,childList:true,attributes:true,attributeFilter:['aria-current','aria-pressed','data-state']});
  observeItems();schedule();
  // Text widths can change after the locally bundled fonts finish loading.
  void document.fonts.ready.then(schedule);
  return {destroy(){disposed=true;cancelAnimationFrame(frame);changes.disconnect();resize.disconnect();}};
}
