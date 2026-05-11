function atualizarRelogio() {
  const el = document.getElementById("relogio");
  if (!el) return;
  el.textContent = new Date().toLocaleTimeString("pt-BR", {
    hour: "2-digit", minute: "2-digit", second: "2-digit"
  });
}
setInterval(atualizarRelogio, 1000);
atualizarRelogio();

let _inactivityTimer = null;
function resetInactivity(timeoutMs, callback) {
  clearTimeout(_inactivityTimer);
  _inactivityTimer = setTimeout(callback, timeoutMs);
  ["mousemove", "keydown", "touchstart", "click"].forEach(ev =>
    document.addEventListener(ev, () => {
      clearTimeout(_inactivityTimer);
      _inactivityTimer = setTimeout(callback, timeoutMs);
    }, { passive: true })
  );
}

function triggerFlash() {
  const el = document.getElementById("captureFlash");
  if (!el) return;
  el.classList.add("active");
  setTimeout(() => el.classList.remove("active"), 200);
}

function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content ?? "";
}

async function postJSON(url, data) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
    body: JSON.stringify(data),
  });
  return resp.json();
}
