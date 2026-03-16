/**
 * Common utilities for the XLM Trading Dashboard.
 */

// Collapsible sections
document.addEventListener('click', function(e) {
  const trigger = e.target.closest('[data-collapse]');
  if (!trigger) return;
  const target = document.getElementById(trigger.dataset.collapse);
  if (!target) return;
  const isOpen = target.style.maxHeight && target.style.maxHeight !== '0px';
  if (isOpen) {
    target.style.maxHeight = '0px';
    target.style.overflow = 'hidden';
    trigger.classList.remove('expanded');
  } else {
    target.style.maxHeight = target.scrollHeight + 'px';
    target.style.overflow = 'visible';
    trigger.classList.add('expanded');
  }
});

// Tab switching (for non-HTMX fallback)
document.addEventListener('click', function(e) {
  const btn = e.target.closest('.tab-btn');
  if (!btn) return;
  const nav = btn.closest('.tab-nav');
  if (!nav) return;
  nav.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
});

// HTMX event: swap active tab button after HTMX navigation
document.body.addEventListener('htmx:afterSwap', function(e) {
  // Update tab buttons based on URL params
  const params = new URLSearchParams(window.location.search);
  const tab = params.get('tab');
  if (tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      const url = new URL(btn.getAttribute('hx-get'), window.location.origin);
      const btnTab = url.searchParams.get('tab');
      btn.classList.toggle('active', btnTab === tab);
    });
  }
});

// Auto-scroll to bottom of thought feed
function scrollToBottom(selector) {
  const el = document.querySelector(selector);
  if (el) el.scrollTop = el.scrollHeight;
}

// HTMX loading indicators
document.body.addEventListener('htmx:beforeRequest', function(e) {
  const target = e.detail.target;
  if (target) target.style.opacity = '0.7';
});

document.body.addEventListener('htmx:afterRequest', function(e) {
  const target = e.detail.target;
  if (target) target.style.opacity = '1';
});
