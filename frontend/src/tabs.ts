/** WAI-ARIA tabs: click or arrow keys switch panels; only the selected tab is in the Tab order. */
export function setupTabs(list: HTMLElement, onChange: (panelId: string) => void) {
  const tabs = [...list.querySelectorAll<HTMLButtonElement>('[role="tab"]')];

  const select = (tab: HTMLButtonElement, focus = false) => {
    for (const t of tabs) {
      const on = t === tab;
      t.setAttribute('aria-selected', String(on));
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute('aria-controls')!)!.hidden = !on;
    }
    if (focus) tab.focus();
    onChange(tab.getAttribute('aria-controls')!);
  };

  for (const tab of tabs) tab.addEventListener('click', () => select(tab));
  list.addEventListener('keydown', (e) => {
    const at = tabs.indexOf(document.activeElement as HTMLButtonElement);
    if (at < 0) return;
    const next = { ArrowRight: at + 1, ArrowLeft: at - 1, Home: 0, End: tabs.length - 1 }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    select(tabs[(next + tabs.length) % tabs.length], true);
  });
  return { select: (panelId: string) => select(tabs.find((t) => t.getAttribute('aria-controls') === panelId)!) };
}
